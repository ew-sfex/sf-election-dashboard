"""Shared code for the SF 2026 precinct findings.

build_findings.py draws the memo's figures with these functions, and the
section notebooks in sf-2026-drive/notebooks/ use the same functions on the
files in sf-2026-drive/source/. build_drive.py copies this file into that
folder as notebooks/sf2026.py. Edit this copy, not the one in the Drive folder.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter

MIN_BALLOTS = 50
MAX_GROUP_QUARTERS = 0.25
PROJECTED_CRS = 26910
# The Statement of the Vote report every table, figure, and notebook uses.
REPORT_NUMBER = 11
REPORT_FOLDER = "20261110"
REPORT_RELEASED = "November 10, 2026, 5:00 p.m. Phoenix / 4:00 p.m. Pacific"
SOURCE = (
    "San Francisco Department of Elections, Preliminary Statement of the Vote, "
    f"Report {REPORT_NUMBER} ({REPORT_RELEASED}). "
    "Precincts: DataSF Election Precincts, defined 2022."
)
CENSUS_SHARES = {
    "nh_asian_share": "Non-Hispanic Asian",
    "nh_white_share": "Non-Hispanic white",
    "hispanic_share": "Hispanic",
    "ba_share": "Bachelor's degree or higher",
    "renter_share": "Renters",
    "hh_150k_share": "Households at $150,000+",
    "foreign_born_share": "Foreign born",
}


# Charts. build_findings.py saves them to a path; a notebook leaves path out and they show inline.


def _finish(fig, path: Path | None, **save) -> None:
    if path is None:
        plt.show()
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=160, **save)
    plt.close(fig)


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
    path: Path | None,
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
    projected = gdf.to_crs(PROJECTED_CRS)
    colored = projected[projected[column].notna()]
    low, high = colored[column].min(), colored[column].max()
    # A value past the color bar would print in the end color and read as that value.
    if low < vmin or high > vmax:
        name = path.name if path is not None else title
        raise ValueError(
            f"{name}: values run {low:.3f}–{high:.3f}, outside the color scale {vmin}–{vmax}"
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
        districts.to_crs(PROJECTED_CRS).boundary.plot(ax=ax, color="#222222", linewidth=0.65)
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
    _finish(fig, path)


def line_chart(trend: pd.DataFrame, path: Path | None) -> None:
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
        f"Yes share of counted Yes and No votes. San Francisco Department of Elections summary reports 1 and 4–{max(reports)}. "
        "Reports 2 and 3 were not available for this pull.",
        fontsize=6.5,
        color="#666666",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    _finish(fig, path)


LATE_COUNT_MEASURES = {"Measure B": "#1b7837", "Measure I": "#5aae61", "Measure D": "#762a83"}


def late_count_chart(trend: pd.DataFrame, path: Path | None) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.axhline(50, color="#999999", linewidth=0.8, linestyle="--")
    reports = None
    for contest, color in LATE_COUNT_MEASURES.items():
        table = measure_trend(trend, contest)
        reports = list(table.index)
        ax.plot(reports, table["yes_pct"], color=color, marker="o", linewidth=2)
        last = table.iloc[-1]
        ax.annotate(
            f"{contest} {last['yes_pct']:.1f}%",
            (reports[-1], last["yes_pct"]),
            textcoords="offset points",
            xytext=(8, -3),
            fontsize=8.5,
            color=color,
        )
    ballots = measure_trend(trend, "Measure B")["ballots_counted"]
    ax.axvline(5.5, color="#bbbbbb", linewidth=0.8)
    ax.text(5.55, 60.6, "Counted after November 4 →", fontsize=7.5, color="#666666", va="top")
    ax.set_xticks(reports)
    ax.set_xticklabels([f"Report {r}\n{int(ballots.loc[r]) / 1000:.0f}k" for r in reports], fontsize=7.5)
    ax.set_xlim(min(reports) - 0.3, max(reports) + 2.2)
    ax.set_ylim(42, 61)
    ax.set_ylabel("Yes share of Yes + No (%)")
    ax.set_title(
        "Late ballots raised the yes share on Measures B and I and lowered it on Measure D",
        loc="left",
        fontsize=11.5,
        color="#1a1a1a",
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.text(
        0.01,
        0.01,
        f"Citywide yes share of counted Yes and No votes on each report, with ballots counted. San Francisco Department of Elections "
        f"summary reports 1 and 4–{max(reports)}.\nReports 2 and 3 were not available for this pull.",
        fontsize=6.5,
        color="#666666",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    _finish(fig, path)


def district_bars(
    frame: pd.DataFrame,
    column: str,
    path: Path | None,
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
    _finish(fig, path)
    return grouped


def census_scatter(
    subset: pd.DataFrame,
    share: str,
    census: str,
    path: Path | None,
    title: str,
    xlabel: str,
    ylabel: str,
) -> float:
    """Vote share (0–1) against a census share (0–1), both drawn as percent. Returns Pearson r."""
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    sizes = (subset["ballots"] / subset["ballots"].max()) * 180 + 12
    ax.scatter(
        subset[census] * 100,
        subset[share] * 100,
        s=sizes,
        c="#1f4e79",
        alpha=0.75,
        linewidths=0,
    )
    correlation = subset[share].corr(subset[census])
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
    _finish(fig, path)
    return float(correlation)


def screen_measures(gdf: gpd.GeoDataFrame, contests: list[str]) -> pd.DataFrame:
    rows = []
    projected = gdf.to_crs(PROJECTED_CRS)
    projected["easting"] = projected.geometry.centroid.x
    for contest in contests:
        slug = re.sub(r"[^a-z0-9]+", "_", contest.lower()).strip("_")
        yes_col = f"{slug}__yes"
        no_col = f"{slug}__no"
        if yes_col not in gdf.columns:
            continue
        eligible = projected[(projected[yes_col] + projected[no_col]) >= MIN_BALLOTS].copy()
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


# Notebook helpers. Every one reads only the files in the Drive folder's source/.


def load(root: Path) -> gpd.GeoDataFrame:
    """Precinct shapes and results from source/, joined to the census table."""
    source = Path(root) / "source"
    gdf = gpd.read_file(source / "precincts.geojson")
    census = pd.read_csv(source / "census_precinct.csv")
    gdf["precinct_id"] = gdf["precinct_id"].astype(int)
    for column in ("Supervisorial", "Congressional", "Assembly"):
        gdf[column] = gdf[column].astype("Int64")
    gdf = gdf.merge(census, on="precinct_id", how="left", suffixes=("", "_census"))
    projected = gdf.to_crs(PROJECTED_CRS).geometry.centroid
    gdf["easting"] = projected.x
    gdf["northing"] = projected.y
    return gdf


def read_json(root: Path, name: str):
    return json.loads((Path(root) / "source" / name).read_text(encoding="utf-8"))


def two_way(frame: pd.DataFrame, named: str, other: str) -> tuple[pd.Series, pd.Series]:
    """The named side's share of the two-way vote, and the two-way vote itself."""
    votes = frame[named].fillna(0) + frame[other].fillna(0)
    return frame[named] / votes.where(votes > 0), votes


def local_measures(frame: pd.DataFrame) -> list[str]:
    columns = [c for c in frame.columns if c.startswith("measure_") and c.endswith("__yes")]
    return sorted("Measure " + c[len("measure_") : -len("__yes")].upper() for c in columns)


def by_neighborhood(frame: pd.DataFrame, named: str, other: str) -> pd.Series:
    grouped = frame.groupby("Neighborhood")[[named, other]].sum()
    votes = grouped[named] + grouped[other]
    return (100 * grouped[named] / votes.where(votes > 0)).dropna()


def citywide(frame: pd.DataFrame, named: str, other: str) -> dict:
    a, b = frame[named].sum(), frame[other].sum()
    return {named: int(a), other: int(b), "share_pct": float(100 * a / (a + b)), "margin": int(a - b)}


def percentile_range(share: pd.Series, keep: pd.Series) -> list[float]:
    """10th, 50th, and 90th percentile of a precinct share, in percent."""
    return [100 * share[keep].quantile(q) for q in (0.1, 0.5, 0.9)]


def by_district(frame: pd.DataFrame, named: str, other: str) -> pd.Series:
    """Vote-weighted share of the named side for each supervisor district, in percent."""
    grouped = frame.groupby("Supervisorial")[[named, other]].sum()
    return 100 * grouped[named] / (grouped[named] + grouped[other])


def census_frame(frame: pd.DataFrame) -> pd.Series:
    """Precincts used for census comparisons: enough ballots, mostly household population."""
    return (frame["ballots"] >= MIN_BALLOTS) & (frame["gq_share"].fillna(0) < MAX_GROUP_QUARTERS)


def census_correlations(frame: pd.DataFrame, share: pd.Series, keep: pd.Series) -> pd.Series:
    rows = {label: share[keep].corr(frame.loc[keep, column]) for column, label in CENSUS_SHARES.items()}
    return pd.Series(rows, name="r").round(2)


def _census_rows(frame: pd.DataFrame, share: pd.Series, keep: pd.Series, columns: list[str]) -> pd.DataFrame:
    """Precincts in keep with a share and the named census columns."""
    subset = frame.loc[keep, list(columns)].copy()
    subset["_share"] = share.reindex(subset.index)
    return subset.dropna()


def column_correlation(
    frame: pd.DataFrame, share: pd.Series, keep: pd.Series, left: str, right: str
) -> float:
    """Pearson r of two census columns, on the precincts used for a share correlation."""
    subset = _census_rows(frame, share, keep, [left, right])
    return float(subset[left].corr(subset[right]))


def partial_correlation(
    frame: pd.DataFrame, share: pd.Series, keep: pd.Series, column: str, control: str
) -> float:
    """Correlation of a census column with the share after a linear control.

    The rows are the census comparison set with a non-missing share. This is how the
    governor section checks that the foreign-born and white correlations are the
    Asian-share pattern.
    """
    subset = _census_rows(frame, share, keep, [column, control])

    def residuals(target: pd.Series, control_values: pd.Series) -> pd.Series:
        centered = control_values - control_values.mean()
        slope = (centered * (target - target.mean())).sum() / (centered ** 2).sum()
        intercept = target.mean() - slope * control_values.mean()
        return target - (intercept + slope * control_values)

    controlled = subset[control]
    return float(residuals(subset["_share"], controlled).corr(residuals(subset[column], controlled)))


def geography_correlations(frame: pd.DataFrame, share: pd.Series, keep: pd.Series) -> pd.Series:
    """Correlation of a precinct share with east-west and north-south position."""
    return pd.Series(
        {
            "east-west (easting)": share[keep].corr(frame.loc[keep, "easting"]),
            "north-south (latitude)": share[keep].corr(frame.loc[keep, "northing"]),
        },
        name="r",
    ).round(2)


def late_count(frame: pd.DataFrame, slug: str, min_added: int = 30) -> dict:
    """Yes share of the votes counted through Report 5 (November 4) and of the votes counted since.

    A precinct is compared when it had at least MIN_BALLOTS votes on the measure by
    Report 5 and at least min_added votes on it since.
    """
    yes, no = frame[f"{slug}__yes"].fillna(0), frame[f"{slug}__no"].fillna(0)
    yes_early, no_early = frame[f"{slug}__yes_r5"].fillna(0), frame[f"{slug}__no_r5"].fillna(0)
    yes_late, no_late = yes - yes_early, no - no_early
    early, late = yes_early + no_early, yes_late + no_late
    compared = (early >= MIN_BALLOTS) & (late >= min_added)
    shift = 100 * (yes_late / late.where(late > 0) - yes_early / early.where(early > 0))
    return {
        "early_yes_pct": float(100 * yes_early.sum() / early.sum()),
        "late_yes_pct": float(100 * yes_late.sum() / late.sum()),
        "late_votes": int(late.sum()),
        "precincts_compared": int(compared.sum()),
        "precincts_more_yes": int((shift[compared] > 0).sum()),
        "precincts_less_yes": int((shift[compared] < 0).sum()),
        "median_shift_points": float(shift[compared].median()),
    }


def measure_trend(trend: pd.DataFrame, contest: str) -> pd.DataFrame:
    """A measure's citywide count on each summary report, with the yes share of the votes each report added."""
    table = (
        trend[trend["contest"] == contest]
        .pivot_table(index=["report", "folder", "ballots_counted"], columns="choice", values="votes")
        .reset_index()
        .sort_values("report")
        .set_index("report")
    )
    table["yes_pct"] = 100 * table["YES"] / (table["YES"] + table["NO"])
    table["margin"] = table["YES"] - table["NO"]
    added = table[["YES", "NO"]].diff()
    table["added_yes_pct"] = 100 * added["YES"] / (added["YES"] + added["NO"])
    table["ballots_added"] = table["ballots_counted"].diff()
    return table


def on_map(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """The precincts the maps draw: every one with registered voters."""
    return frame[frame["registered"].fillna(0) > 0].copy()


def rate_map(
    frame: gpd.GeoDataFrame,
    share: pd.Series,
    votes: pd.Series,
    title: str,
    subtitle: str,
    cbar_label: str,
    cmap: str = "BrBG",
    diverging: bool = True,
    limits: tuple[float, float] | None = None,
    keep: pd.Series | None = None,
    missing_label: str = "Fewer than 50 ballots",
) -> None:
    """Draw a precinct share the way the memo's maps do."""
    show = votes.fillna(0) >= MIN_BALLOTS
    if keep is not None:
        show = show & keep.fillna(False)
    mapped = on_map(frame.assign(_mapped=share.where(show)))
    if limits is None:
        limits = symmetric_limits(mapped["_mapped"])
    choropleth(
        mapped,
        "_mapped",
        None,
        title,
        subtitle,
        cbar_label,
        cmap,
        *limits,
        vcenter=0.5 if diverging else None,
        districts=district_lines(mapped),
        missing_label=missing_label,
    )


class MemoCheck:
    """Each number the memo quotes, next to the value computed here."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def number(self, claim: str, memo: float, computed: float, digits: int = 1) -> None:
        rounded = round(float(computed), digits)
        self.rows.append(
            {
                "claim": claim,
                "memo": f"{memo:,.{digits}f}",
                "computed": f"{rounded:,.{digits}f}",
                "matches": math.isclose(rounded, memo, abs_tol=10 ** -(digits + 3)),
            }
        )

    def fact(self, claim: str, memo: str, computed, holds: bool) -> None:
        self.rows.append({"claim": claim, "memo": memo, "computed": str(computed), "matches": bool(holds)})

    def report(self) -> pd.DataFrame:
        table = pd.DataFrame(self.rows)
        table["matches"] = table["matches"].map({True: "yes", False: "NO"})
        misses = table[table["matches"] == "NO"]
        with pd.option_context("display.max_rows", None, "display.max_colwidth", 90):
            try:
                from IPython.display import display

                display(table)
            except ImportError:
                print(table.to_string(index=False))
        if len(misses):
            raise AssertionError(
                f"{len(misses)} of {len(table)} memo numbers do not match the data: "
                + "; ".join(misses["claim"])
            )
        print(f"All {len(table)} numbers checked match the memo.")
        return table
