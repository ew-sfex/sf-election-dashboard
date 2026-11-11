"""Build precinct tables and maps from the Statement of the Vote.

Outputs land in analysis/output. Raw downloads land in analysis/raw and are
not committed. Run from the repository root:

    python analysis/build_findings.py
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

from parse_sov import parse_sov, parse_summary_xml, reconcile
from sf2026 import (
    MIN_BALLOTS,
    REPORT_FOLDER,
    REPORT_NUMBER,
    census_scatter,
    choropleth,
    district_bars,
    district_lines,
    line_chart,
    screen_measures,
    symmetric_limits,
)

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
    "20261109",
    "20261110",
]
LATEST_SOV = f"{REPORT_FOLDER}/sov.xlsx"
EARLY_SOV = "20261104/sov.xlsx"  # Report 5, the last report with No ahead on Measure B
GEOJSON_URL = "https://data.sfgov.org/api/v3/views/d6x4-hefw/query.geojson?accessType=DOWNLOAD"
CROSSWALK_URL = (
    f"{BASE}/tools/election_data/datasets/2026-11-03/N26_ConsolDistBT_20260817.xlsx"
)
MEASURES_URL = (
    f"{BASE}/tools/election_data/datasets/2026-11-03/CFMJ008_MeasureData.txt"
)
PARTY_URL = f"{BASE}/tools/election_data/registration_by_party.php"



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
        "sov": RAW / f"sov_{REPORT_FOLDER}.xlsx",
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
        correlation = census_scatter(
            subset, xcol_vote, ycol, FIG / filename, title, xlabel, ylabel
        )
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

    # A precinct can report more ballots than registered voters (9723 on Report 11).
    # That rate isn't a turnout, so it is left off the turnout map.
    gdf["turnout_mapped"] = hide_small("turnout", gdf["ballots"]).where(gdf["ballots"] <= gdf["registered"])
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

    screening = screen_measures(gdf, local)
    screening["title"] = screening["contest"].map(titles)
    screening.to_csv(OUT / "measure_screening.csv", index=False)

    choropleth(
        map_gdf,
        "turnout_mapped",
        FIG / "turnout.png",
        "Turnout by precinct",
        "Ballots counted divided by registered voters. Hatched gray precincts cast under 50 ballots or report more ballots than voters.",
        "Turnout",
        "YlGnBu",
        vmin=0.25,
        vmax=0.90,
        districts=districts,
        missing_label="Fewer than 50 ballots, or more ballots than registered voters",
    )
    choropleth(
        map_gdf,
        "mail_mapped",
        FIG / "mail_share.png",
        "Vote-by-mail share of ballots cast",
        "Mail ballots divided by ballots cast. Citywide, mail is about 89% of the count.",
        "Mail share",
        "PuBu",
        vmin=0.35,
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
        f"Votes added between Report 5 (No still ahead) and Report {REPORT_NUMBER}. Precincts with fewer than 30 added votes are hatched gray.",
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
