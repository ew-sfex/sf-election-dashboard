"""Build precinct tables and maps from the Statement of the Vote.

Outputs land in analysis/output. Raw downloads land in analysis/raw and are
not committed. Run from the repository root:

    python analysis/build_findings.py
"""

from __future__ import annotations

import json
import math
import re
import urllib.request
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter

from parse_sov import parse_sov, parse_summary_xml, reconcile

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "output"
FIG = OUT / "figures"
BASE = "https://www.sfelections.org"
UA = "Mozilla/5.0 (compatible; sf-election-findings/1.0)"

SUMMARY_FOLDERS = [
    "20261103_1",
    "20261103_4",
    "20261104",
    "20261105",
    "20261106",
    "20261107",
    "20261108",
]
LATEST_SOV = "20261108/sov.xlsx"
EARLY_SOV = "20261104/sov.xlsx"  # Report 5, the last report with No ahead on Measure B
GEOJSON_URL = "https://data.sfgov.org/api/v3/views/d6x4-hefw/query.geojson?accessType=DOWNLOAD"
CROSSWALK_URL = (
    f"{BASE}/tools/election_data/datasets/2026-11-03/N26_ConsolDistBT_20260817.xlsx"
)
MEASURES_URL = (
    f"{BASE}/tools/election_data/datasets/2026-11-03/CFMJ008_MeasureData.txt"
)
PARTY_URL = f"{BASE}/tools/election_data/registration_by_party.php"

MIN_BALLOTS = 50
SOURCE = (
    "San Francisco Department of Elections, Preliminary Statement of the Vote, "
    "Report 9 (November 8, 2026, 5:00 p.m. Phoenix / 4:00 p.m. Pacific). "
    "Precincts: DataSF Election Precincts, defined 2022."
)


def _download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=180) as response:
        dest.write_bytes(response.read())


def fetch_inputs() -> dict[str, Path]:
    RAW.mkdir(parents=True, exist_ok=True)
    paths = {
        "sov": RAW / "sov_20261108.xlsx",
        "sov_early": RAW / "sov_20261104.xlsx",
        "geo": RAW / "precincts.geojson",
        "crosswalk": RAW / "precinct_crosswalk.xlsx",
        "measures": RAW / "measures.txt",
        "party": RAW / "registration_by_party.html",
    }
    _download(f"{BASE}/results/20261103/data/{LATEST_SOV}", paths["sov"])
    _download(f"{BASE}/results/20261103/data/{EARLY_SOV}", paths["sov_early"])
    _download(GEOJSON_URL, paths["geo"])
    _download(CROSSWALK_URL, paths["crosswalk"])
    _download(MEASURES_URL, paths["measures"])
    _download(PARTY_URL, paths["party"])
    summaries = []
    for folder in SUMMARY_FOLDERS:
        dest = RAW / f"summary_{folder}.xml"
        _download(f"{BASE}/results/20261103/data/{folder}/summary.xml", dest)
        summaries.append(dest)
    paths["summaries"] = summaries
    return paths


def measure_titles(path: Path) -> dict[str, str]:
    text = path.read_bytes().decode("utf-16")
    titles = {}
    for line in text.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        designation = parts[1].strip()
        title = parts[2].strip()
        if designation and title:
            titles[f"Measure {designation}"] = title
    return titles


def citywide_party(path: Path) -> pd.DataFrame:
    html = path.read_text(encoding="utf-8", errors="replace")
    rows = re.findall(
        r"<tr>\s*<td[^>]*>\s*([^<]+?)\s*</td>\s*<td[^>]*>\s*([\d,]+)\s*</td>",
        html,
        flags=re.I,
    )
    if not rows:
        rows = re.findall(r">([A-Za-z][^<]{2,40})</(?:td|th)>\s*<td[^>]*>\s*([\d,]+)", html)
    frame = pd.DataFrame(rows, columns=["group", "registered"])
    frame["group"] = frame["group"].str.strip()
    frame["registered"] = frame["registered"].str.replace(",", "", regex=False).astype(int)
    return frame.drop_duplicates("group")


def _pivot_contest(precinct: pd.DataFrame, contest: str, channel: str = "total") -> pd.DataFrame:
    subset = precinct[(precinct["contest"] == contest) & (precinct["channel"] == channel)]
    if subset.empty:
        raise KeyError(contest)
    wide = subset.pivot_table(
        index="precinct_id", columns="choice", values="votes", aggfunc="sum"
    )
    wide["registered"] = subset.groupby("precinct_id")["registered"].max()
    return wide.reset_index()


def _share(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    out = numerator / denominator
    return out.where(denominator > 0)


def load_precincts(geo_path: Path, crosswalk_path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(geo_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf["precinct_id"] = gdf["prec_2022"].astype(str)
    cross = pd.read_excel(crosswalk_path)
    cross["precinct_id"] = cross["VotingPrecinctID"].astype(int).astype(str)
    keep = [
        "precinct_id",
        "VotingPrecinctName",
        "MailBallotPrecinct",
        "Congressional",
        "Supervisorial",
        "Assembly",
        "Neighborhood",
    ]
    gdf = gdf.merge(cross[keep], on="precinct_id", how="left")
    gdf["Congressional"] = gdf["Congressional"].astype("Int64")
    gdf["Supervisorial"] = gdf["Supervisorial"].astype("Int64")
    return gdf


def district_lines(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gdf.dissolve(by="Supervisorial", as_index=False)


def symmetric_limits(values: pd.Series, center: float = 0.5, step: float = 0.05) -> tuple[float, float]:
    """Diverging-scale limits, equal on both sides of center, that hold every value."""
    spread = (values.dropna() - center).abs().max()
    half = math.ceil(round(spread / step, 9)) * step
    return round(center - half, 2), round(center + half, 2)


def choropleth(
    gdf: gpd.GeoDataFrame,
    column: str,
    path: Path,
    title: str,
    subtitle: str,
    cbar_label: str,
    cmap: str,
    vmin: float,
    vmax: float,
    vcenter: float | None = None,
    districts: gpd.GeoDataFrame | None = None,
    missing_label: str = "Fewer than 50 ballots",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    projected = gdf.to_crs(26910)
    colored = projected[projected[column].notna()]
    low, high = colored[column].min(), colored[column].max()
    # A value past the color bar would print in the end color and read as that value.
    if low < vmin or high > vmax:
        raise ValueError(
            f"{path.name}: values run {low:.3f}–{high:.3f}, outside the color scale {vmin}–{vmax}"
        )
    fig, ax = plt.subplots(figsize=(8.2, 8.8))
    # Hatched so a precinct with no rate can't be mistaken for one near the scale's light middle.
    projected.plot(ax=ax, facecolor="#d4d4d4", edgecolor="#a6a6a6", hatch="//////", linewidth=0)
    projected.plot(ax=ax, facecolor="none", edgecolor="white", linewidth=0.12)
    if vcenter is None:
        norm = Normalize(vmin=vmin, vmax=vmax)
    else:
        norm = TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)
    colored.plot(
        ax=ax,
        column=column,
        cmap=cmap,
        norm=norm,
        edgecolor="white",
        linewidth=0.12,
        legend=False,
    )
    if districts is not None:
        districts.to_crs(26910).boundary.plot(ax=ax, color="#222222", linewidth=0.65)
    mappable = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    colorbar = fig.colorbar(mappable, ax=ax, fraction=0.033, pad=0.01)
    if vmax <= 1.5:
        colorbar.ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    colorbar.set_label(cbar_label)
    if len(colored) < len(projected):
        ax.legend(
            handles=[
                Patch(facecolor="#d4d4d4", edgecolor="#a6a6a6", hatch="//////", label=missing_label)
            ],
            loc="lower left",
            frameon=False,
            fontsize=8,
        )
    ax.set_axis_off()
    fig.suptitle(title, x=0.02, ha="left", fontsize=13, color="#1a1a1a")
    ax.set_title(subtitle, loc="left", fontsize=8.5, color="#444444", pad=8)
    fig.text(0.02, 0.012, SOURCE, fontsize=6.5, color="#666666", ha="left", wrap=True)
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def line_chart(trend: pd.DataFrame, path: Path) -> None:
    measure = trend[trend["contest"] == "Measure B"].copy()
    yes = measure[measure["choice"] == "YES"].set_index("report")["votes"]
    no = measure[measure["choice"] == "NO"].set_index("report")["votes"]
    reports = sorted(yes.index)
    percent = [100 * yes[r] / (yes[r] + no[r]) for r in reports]
    ballots = (
        measure.drop_duplicates("report").set_index("report").loc[reports, "ballots_counted"]
    )
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.axhline(50, color="#999999", linewidth=0.8, linestyle="--")
    ax.plot(reports, percent, color="#1f4e79", marker="o", linewidth=2)
    for report, value in zip(reports, percent):
        # Report 5 was 49.96% and still a No lead. One decimal would print 50.0%.
        text = f"{value:.2f}%" if abs(value - 50) < 0.15 else f"{value:.1f}%"
        ax.annotate(
            text,
            (report, value),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8,
            color="#1a1a1a",
        )
    labels = [f"Report {r}\n{int(ballots.loc[r]) / 1000:.0f}k" for r in reports]
    ax.set_xticks(reports)
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylabel("Yes share of Yes + No (%)")
    ax.set_ylim(46, 56)
    ax.set_title(
        "Measure B crossed 50% between the November 4 and November 5 reports",
        loc="left",
        fontsize=12,
        color="#1a1a1a",
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.text(
        0.01,
        0.01,
        "Yes share of counted Yes and No votes. San Francisco Department of Elections summary reports 1 and 4–9. "
        "Reports 2 and 3 were not available for this pull.",
        fontsize=6.5,
        color="#666666",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def district_bars(
    frame: pd.DataFrame,
    column: str,
    path: Path,
    title: str,
    xlabel: str,
    reference: float | None = 50,
) -> pd.DataFrame:
    rows = []
    for district, part in frame.dropna(subset=["Supervisorial"]).groupby("Supervisorial"):
        weight = part["weight"].sum()
        if weight <= 0:
            continue
        rows.append(
            {
                "district": int(district),
                "share": 100 * part[column].mul(part["weight"]).sum() / weight,
                "weight": weight,
            }
        )
    grouped = pd.DataFrame(rows).sort_values("district")
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.barh(
        [f"District {d}" for d in grouped["district"]],
        grouped["share"],
        color="#1f4e79",
    )
    if reference is not None:
        ax.axvline(reference, color="#999999", linewidth=0.8, linestyle="--")
    ax.set_xlabel(xlabel)
    ax.set_title(title, loc="left", fontsize=12, color="#1a1a1a")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return grouped


def _screen_measures(gdf: gpd.GeoDataFrame, contests: list[str]) -> pd.DataFrame:
    rows = []
    projected = gdf.to_crs(26910)
    projected["easting"] = projected.geometry.centroid.x
    for contest in contests:
        slug = re.sub(r"[^a-z0-9]+", "_", contest.lower()).strip("_")
        yes_col = f"{slug}__yes"
        no_col = f"{slug}__no"
        if yes_col not in gdf.columns:
            continue
        eligible = projected[(projected[yes_col] + projected[no_col]) >= MIN_BALLOTS].copy()
        yes = eligible[yes_col].sum()
        no = eligible[no_col].sum()
        # Citywide figures should include small precincts too.
        yes_all = projected[yes_col].sum()
        no_all = projected[no_col].sum()
        eligible["share"] = eligible[yes_col] / (eligible[yes_col] + eligible[no_col])
        correlation = eligible["share"].corr(eligible["easting"])
        district_shares = []
        for _district, part in eligible.groupby("Supervisorial"):
            votes = part[yes_col].sum() + part[no_col].sum()
            if votes < 500:
                continue
            district_shares.append(100 * part[yes_col].sum() / votes)
        spread = (max(district_shares) - min(district_shares)) if district_shares else 0
        yes_pct = 100 * yes_all / (yes_all + no_all) if (yes_all + no_all) else None
        rows.append(
            {
                "contest": contest,
                "yes": int(yes_all),
                "no": int(no_all),
                "yes_pct": yes_pct,
                "margin_points": (yes_pct - 50) * 2 if yes_pct is not None else None,
                "district_spread_points": spread,
                "east_west_r": correlation,
                "precincts_in_correlation": int(len(eligible)),
            }
        )
    return pd.DataFrame(rows).sort_values("contest")


def write_census_charts() -> None:
    """Scatters of precinct vote shares against apportioned census characteristics."""
    votes_path = OUT / "precincts.geojson"
    census_path = OUT / "census_precinct.csv"
    if not votes_path.exists() or not census_path.exists():
        return
    gdf = gpd.read_file(votes_path)
    census = pd.read_csv(census_path, dtype={"precinct_id": str})
    gdf["precinct_id"] = gdf["precinct_id"].astype(str)
    gdf = gdf.merge(census, on="precinct_id", how="left", suffixes=("", "_census"))
    pairs = [
        (
            "measure_b_yes_share",
            "renter_share",
            "measure_b_vs_renters.png",
            "Measure B and renters",
            "Renter share of occupied housing units",
            "Measure B yes share (%)",
        ),
        (
            "measure_b_yes_share",
            "hispanic_share",
            "measure_b_vs_hispanic.png",
            "Measure B and Hispanic population",
            "Hispanic share of 2020 population",
            "Measure B yes share (%)",
        ),
        (
            "chan_share",
            "nh_asian_share",
            "ca11_vs_asian.png",
            "CA-11 and Asian population",
            "Non-Hispanic Asian share of 2020 population",
            "Connie Chan share of the two-candidate vote (%)",
        ),
        (
            "hilton_share",
            "nh_asian_share",
            "governor_vs_asian.png",
            "Governor and Asian population",
            "Non-Hispanic Asian share of 2020 population",
            "Steve Hilton share of the two-candidate vote (%)",
        ),
        (
            "measure_g_yes_share",
            "nh_asian_share",
            "measure_g_vs_asian.png",
            "Measure G and Asian population",
            "Non-Hispanic Asian share of 2020 population",
            "Measure G yes share (%)",
        ),
        (
            "turnout",
            "ba_share",
            "turnout_vs_bachelors.png",
            "Turnout and bachelor’s degrees",
            "Bachelor’s degree or higher, share of adults 25+",
            "Turnout (%)",
        ),
    ]
    notes = []
    usable = gdf[(gdf["ballots"] >= MIN_BALLOTS) & (gdf["gq_share"].fillna(0) < 0.25)].copy()
    for xcol_vote, ycol, filename, title, xlabel, ylabel in pairs:
        # vote columns are 0-1 shares. Chart them as percent on the y axis.
        subset = usable.dropna(subset=[xcol_vote, ycol]).copy()
        if "chan_share" in xcol_vote:
            subset = subset[subset["Congressional"] == 11]
        if subset.empty:
            continue
        fig, ax = plt.subplots(figsize=(7.2, 5.2))
        sizes = (subset["ballots"] / subset["ballots"].max()) * 180 + 12
        ax.scatter(
            subset[ycol] * 100,
            subset[xcol_vote] * 100,
            s=sizes,
            c="#1f4e79",
            alpha=0.75,
            linewidths=0,
        )
        correlation = subset[xcol_vote].corr(subset[ycol])
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left", fontsize=12)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.text(
            0.01,
            0.01,
            f"Precincts with at least {MIN_BALLOTS} ballots and group quarters under 25% of population. "
            f"Dot size is ballots cast. Pearson r = {correlation:.2f}.\n"
            "These are precinct patterns, not individual votes.",
            fontsize=7,
            color="#666666",
        )
        fig.tight_layout(rect=(0, 0.08, 1, 1))
        fig.savefig(FIG / filename, dpi=160)
        plt.close(fig)
        notes.append({"chart": filename, "r": round(float(correlation), 3), "n": int(len(subset))})
    (OUT / "census_chart_correlations.json").write_text(json.dumps(notes, indent=2))


def main() -> None:
    plt.rcParams["font.family"] = "DejaVu Sans"
    paths = fetch_inputs()
    FIG.mkdir(parents=True, exist_ok=True)
    titles = measure_titles(paths["measures"])
    party = citywide_party(paths["party"])
    party.to_csv(OUT / "citywide_party.csv", index=False)

    precinct, summary = parse_sov(paths["sov"])
    early, _early_summary = parse_sov(paths["sov_early"])
    check = reconcile(precinct, summary)
    check.to_csv(OUT / "reconciliation.csv", index=False)
    if not (check["difference"] == 0).all():
        bad = check[check["difference"] != 0]
        raise SystemExit(f"Precinct sums do not match electionwide totals:\n{bad.head(20)}")

    totals = precinct[precinct["channel"] == "total"][
        ["contest", "precinct_id", "mail_ballot_precinct", "choice", "party", "registered", "votes"]
    ]
    totals.to_csv(OUT / "precinct_choice_totals.csv", index=False)

    trend_frames = []
    for summary_path in paths["summaries"]:
        frame, meta = parse_summary_xml(summary_path)
        frame["folder"] = summary_path.stem.replace("summary_", "")
        frame["report"] = meta["report"]
        frame["ballots_counted"] = meta["ballots"]
        trend_frames.append(frame)
    trend = pd.concat(trend_frames, ignore_index=True)
    trend.to_csv(OUT / "citywide_trend.csv", index=False)
    line_chart(trend, FIG / "measure_b_trend.png")

    gdf = load_precincts(paths["geo"], paths["crosswalk"])

    turnout = _pivot_contest(precinct, "Turnout")
    mail = _pivot_contest(precinct, "Turnout", channel="vote_by_mail")
    turnout = turnout.merge(
        mail[["precinct_id", "Ballots cast"]].rename(columns={"Ballots cast": "mail_ballots"}),
        on="precinct_id",
        how="left",
    )
    turnout = turnout.rename(columns={"Ballots cast": "ballots"})
    gdf = gdf.merge(turnout[["precinct_id", "ballots", "mail_ballots", "registered"]], on="precinct_id", how="left")
    gdf["turnout"] = _share(gdf["ballots"], gdf["registered"])
    gdf["mail_share"] = _share(gdf["mail_ballots"], gdf["ballots"])

    joins = {
        "GOVERNOR": ("STEVE HILTON", "XAVIER BECERRA", "hilton", "becerra"),
        "UNITED STATES REPRESENTATIVE, DISTRICT 11": ("CONNIE CHAN", "SCOTT WIENER", "chan", "wiener"),
    }
    for contest, (left, right, left_name, right_name) in joins.items():
        wide = _pivot_contest(precinct, contest).rename(columns={left: left_name, right: right_name})
        gdf = gdf.merge(wide[["precinct_id", left_name, right_name]], on="precinct_id", how="left")
        gdf[f"{left_name}_share"] = _share(
            gdf[left_name], gdf[left_name].fillna(0) + gdf[right_name].fillna(0)
        )

    local = sorted(c for c in precinct["contest"].unique() if str(c).startswith("Measure "))
    for contest in local:
        wide = _pivot_contest(precinct, contest)
        slug = re.sub(r"[^a-z0-9]+", "_", contest.lower()).strip("_")
        wide = wide.rename(columns={"YES": f"{slug}__yes", "NO": f"{slug}__no"})
        gdf = gdf.merge(wide[["precinct_id", f"{slug}__yes", f"{slug}__no"]], on="precinct_id", how="left")
        gdf[f"{slug}_yes_share"] = _share(
            gdf[f"{slug}__yes"], gdf[f"{slug}__yes"].fillna(0) + gdf[f"{slug}__no"].fillna(0)
        )

    early_b = _pivot_contest(early, "Measure B").rename(columns={"YES": "yes_r5", "NO": "no_r5"})
    gdf = gdf.merge(early_b[["precinct_id", "yes_r5", "no_r5"]], on="precinct_id", how="left")
    gdf["yes_added"] = gdf["measure_b__yes"].fillna(0) - gdf["yes_r5"].fillna(0)
    gdf["no_added"] = gdf["measure_b__no"].fillna(0) - gdf["no_r5"].fillna(0)
    gdf["added_ballots"] = gdf["yes_added"] + gdf["no_added"]
    gdf["added_yes_share"] = _share(gdf["yes_added"], gdf["added_ballots"])

    def hide_small(column: str, ballots: pd.Series, mask: pd.Series | None = None) -> pd.Series:
        show = ballots.fillna(0) >= MIN_BALLOTS
        if mask is not None:
            show = show & mask.fillna(False)
        return gdf[column].where(show)

    gdf["turnout_mapped"] = hide_small("turnout", gdf["ballots"])
    gdf["mail_mapped"] = hide_small("mail_share", gdf["ballots"])
    gdf["hilton_mapped"] = hide_small("hilton_share", gdf["hilton"].fillna(0) + gdf["becerra"].fillna(0))
    in_ca11 = gdf["Congressional"] == 11
    gdf["chan_mapped"] = hide_small(
        "chan_share", gdf["chan"].fillna(0) + gdf["wiener"].fillna(0), in_ca11
    )
    gdf["measure_b_mapped"] = hide_small(
        "measure_b_yes_share", gdf["measure_b__yes"].fillna(0) + gdf["measure_b__no"].fillna(0)
    )
    gdf["added_mapped"] = gdf["added_yes_share"].where(gdf["added_ballots"] >= 30)
    # Four precincts have no registered voters: Angel Island (9904), Alameda
    # Island (9903), and two small inland ones in Outer Mission (9901) and
    # Portola (9902). They stay in the data file and come off the maps; the
    # islands would otherwise shrink the city.
    map_gdf = gdf[gdf["registered"].fillna(0) > 0].copy()
    districts = district_lines(map_gdf)

    screening = _screen_measures(gdf, local)
    screening["title"] = screening["contest"].map(titles)
    screening.to_csv(OUT / "measure_screening.csv", index=False)

    choropleth(
        map_gdf,
        "turnout_mapped",
        FIG / "turnout.png",
        "Turnout by precinct",
        "Ballots counted divided by registered voters. Precincts under 50 ballots are hatched gray.",
        "Turnout",
        "YlGnBu",
        vmin=0.25,
        vmax=0.85,
        districts=districts,
    )
    choropleth(
        map_gdf,
        "mail_mapped",
        FIG / "mail_share.png",
        "Vote-by-mail share of ballots cast",
        "Mail ballots divided by ballots cast. Citywide, mail is about 89% of the count.",
        "Mail share",
        "PuBu",
        vmin=0.55,
        vmax=1.0,
        districts=districts,
    )
    choropleth(
        map_gdf,
        "hilton_mapped",
        FIG / "governor_hilton.png",
        "Governor: Steve Hilton's share inside San Francisco",
        "Share of the Hilton + Becerra vote. This is the San Francisco county vote, not the state result.",
        "Hilton share",
        "OrRd",
        vmin=0.0,
        vmax=0.40,
        districts=districts,
    )
    choropleth(
        map_gdf,
        "chan_mapped",
        FIG / "ca11_chan.png",
        "CA-11: Connie Chan's share of the two-candidate vote",
        "Scott Wiener and Connie Chan, both Democrats. Hatched gray precincts are in CA-15 or cast under 50 ballots.",
        "Chan share",
        "PuOr",
        *symmetric_limits(gdf["chan_mapped"]),
        vcenter=0.50,
        districts=districts,
        missing_label="In CA-15, or fewer than 50 ballots",
    )
    choropleth(
        map_gdf,
        "measure_b_mapped",
        FIG / "measure_b_yes.png",
        "Measure B: yes share",
        f"{titles.get('Measure B', 'Measure B')}. Hatched gray precincts cast fewer than 50 ballots.",
        "Yes share",
        "BrBG",
        *symmetric_limits(gdf["measure_b_mapped"]),
        vcenter=0.50,
        districts=districts,
    )
    choropleth(
        map_gdf,
        "added_mapped",
        FIG / "measure_b_ballots_after_nov4.png",
        "Measure B: yes share of ballots counted after November 4",
        "Votes added between Report 5 (No still ahead) and Report 9. Precincts with fewer than 30 added votes are hatched gray.",
        "Yes share of added votes",
        "BrBG",
        *symmetric_limits(gdf["added_mapped"]),
        vcenter=0.50,
        districts=districts,
        missing_label="Fewer than 30 added votes",
    )

    # Every local measure varies by supervisor district. Map the close ones and
    # the one with a strong east-west break. The full comparison stays in the CSV.
    extra = screening[
        (screening["contest"] != "Measure B")
        & (
            (screening["yes_pct"].sub(50).abs() <= 5)
            | (screening["east_west_r"].abs() >= 0.5)
        )
    ]
    for contest in extra["contest"]:
        slug = re.sub(r"[^a-z0-9]+", "_", contest.lower()).strip("_")
        column = f"{slug}_yes_share"
        gdf[f"{slug}_mapped"] = hide_small(
            column, gdf[f"{slug}__yes"].fillna(0) + gdf[f"{slug}__no"].fillna(0)
        )
        map_gdf[f"{slug}_mapped"] = gdf[f"{slug}_mapped"]
        choropleth(
            map_gdf,
            f"{slug}_mapped",
            FIG / f"{slug}_yes.png",
            f"{contest}: yes share",
            f"{titles.get(contest, contest)}. Hatched gray precincts cast fewer than 50 ballots.",
            "Yes share",
            "BrBG",
            *symmetric_limits(gdf[f"{slug}_mapped"]),
            vcenter=0.50,
            districts=districts,
        )

    # District bar charts use ballot weights.
    bar_frame = gdf.copy()
    bar_frame["weight"] = bar_frame["hilton"].fillna(0) + bar_frame["becerra"].fillna(0)
    bar_frame["hilton_share_pct_input"] = bar_frame["hilton_share"]
    district_bars(
        bar_frame.assign(weight=bar_frame["weight"]),
        "hilton_share",
        FIG / "governor_by_district.png",
        "Hilton share of the two-candidate vote, by supervisor district",
        "Hilton share (%)",
        reference=None,
    )
    ca_frame = gdf[gdf["Congressional"] == 11].copy()
    ca_frame["weight"] = ca_frame["chan"].fillna(0) + ca_frame["wiener"].fillna(0)
    district_bars(
        ca_frame,
        "chan_share",
        FIG / "ca11_by_district.png",
        "CA-11: Chan share by supervisor district (CA-11 precincts only)",
        "Chan share of the two-candidate vote (%)",
    )
    b_frame = gdf.copy()
    b_frame["weight"] = b_frame["measure_b__yes"].fillna(0) + b_frame["measure_b__no"].fillna(0)
    district_bars(
        b_frame,
        "measure_b_yes_share",
        FIG / "measure_b_by_district.png",
        "Measure B yes share, by supervisor district",
        "Yes share (%)",
    )

    unmatched_votes = sorted(set(totals["precinct_id"]) - set(gdf["precinct_id"]))
    unmatched_shapes = sorted(set(gdf["precinct_id"]) - set(totals["precinct_id"]))
    qc = {
        "precinct_shapes": int(len(gdf)),
        "sov_precincts": int(totals["precinct_id"].nunique()),
        "shapes_missing_from_sov": unmatched_shapes,
        "sov_precincts_missing_a_shape": unmatched_votes,
        "reconciliation_max_abs_difference": int(check["difference"].abs().max()),
        "cumulative_votes_measure_b": int(
            summary[
                (summary["contest"] == "Measure B")
                & (summary["level"] == "cumulative")
                & (summary["choice"] == "YES")
            ]["votes"].sum()
            + summary[
                (summary["contest"] == "Measure B")
                & (summary["level"] == "cumulative")
                & (summary["choice"] == "NO")
            ]["votes"].sum()
        ),
        "negative_added_precincts": int((gdf["added_ballots"] < 0).sum()),
    }
    (OUT / "join_qc.json").write_text(json.dumps(qc, indent=2))

    keep_cols = [
        "precinct_id",
        "prec_2022",
        "VotingPrecinctName",
        "Neighborhood",
        "Supervisorial",
        "Congressional",
        "Assembly",
        "MailBallotPrecinct",
        "registered",
        "ballots",
        "mail_ballots",
        "turnout",
        "mail_share",
        "hilton",
        "becerra",
        "hilton_share",
        "chan",
        "wiener",
        "chan_share",
        "measure_b__yes",
        "measure_b__no",
        "measure_b_yes_share",
        "yes_added",
        "no_added",
        "added_ballots",
        "added_yes_share",
        "geometry",
    ]
    extra_cols = [c for c in gdf.columns if c.endswith("_yes_share") or c.endswith("__yes") or c.endswith("__no")]
    export_cols = list(dict.fromkeys(keep_cols + extra_cols))
    gdf[export_cols].to_file(OUT / "precincts.geojson", driver="GeoJSON")
    gdf.drop(columns="geometry")[ [c for c in export_cols if c != "geometry"] ].to_csv(
        OUT / "precinct_results.csv", index=False
    )
    (OUT / "measure_titles.json").write_text(json.dumps(titles, indent=2))
    print(json.dumps(qc, indent=2))
    print(screening.to_string(index=False))
    print("party rows", len(party))


if __name__ == "__main__":
    main()
