"""Write and run one Colab notebook per section of the findings note.

build_drive.py calls this after it fills sf-2026-drive/source/. Each notebook
reads only that folder's source/ files and notebooks/sf2026.py, so the whole
folder can be moved to Google Drive and run there. Each one ends with a table
of every number its memo section quotes next to the value it computes, and
fails if any differ, so a build stops when the note and the data disagree.
"""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

import nbformat
from nbclient import NotebookClient

SETUP = '''\
# Run this cell first. It finds the sf-2026-drive folder (on Google Drive in Colab, or on
# this computer) and loads the shared code in notebooks/sf2026.py.
import subprocess
import sys
from pathlib import Path

try:
    import geopandas  # noqa: F401
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "geopandas"], check=True)

FOLDER_NAME = "sf-2026-drive"


def is_root(path: Path) -> bool:
    return (path / "source" / "precinct_results.csv").exists() and (path / "notebooks" / "sf2026.py").exists()


def find_root() -> Path:
    here = Path.cwd().resolve()
    for candidate in [here, *here.parents]:
        if is_root(candidate):
            return candidate
    try:
        from google.colab import drive
    except ImportError:
        raise FileNotFoundError("Open this notebook from inside the sf-2026-drive folder.")
    drive.mount("/content/drive")
    bases = [Path("/content/drive/MyDrive"), Path("/content/drive/Shareddrives")]
    for base in bases:
        if is_root(base / FOLDER_NAME):
            return base / FOLDER_NAME
    for base in bases:
        if base.exists():
            for helper in base.rglob("sf2026.py"):
                if is_root(helper.parent.parent):
                    return helper.parent.parent
    raise FileNotFoundError(
        f"Could not find the {FOLDER_NAME} folder on Drive. If you renamed it, set FOLDER_NAME above."
    )


ROOT = find_root()
sys.path.insert(0, str(ROOT / "notebooks"))
import pandas as pd
import sf2026 as sf

pd.set_option("display.float_format", lambda value: f"{value:,.2f}")
data = sf.load(ROOT)
check = sf.MemoCheck()
print(f"Using the {ROOT.name} folder: {len(data)} precincts")
'''

REPORT = "check.report();"

INTRO = (
    "Every number below is computed from the files in `source/`. Run the setup cell first, "
    "then the rest in order (Runtime → Run all). The last cell lists each number the memo "
    "section quotes next to the value computed here, and stops with an error if any differ."
)


def code(text: str) -> tuple[str, str]:
    return ("code", dedent(text).strip())


def md(text: str) -> tuple[str, str]:
    return ("markdown", dedent(text).strip())


def two_way_section(named: str, other: str, label: str) -> str:
    return f'''
    share, votes = sf.two_way(data, "{named}", "{other}")
    enough = data["ballots"] >= sf.MIN_BALLOTS
    districts = sf.by_district(data, "{named}", "{other}")
    print("Precinct range, 10th / 50th / 90th percentile:", [round(v, 1) for v in sf.percentile_range(share, enough)])
    districts.round(1).to_frame("{label}, percent")
    '''


def _inline(text: str) -> str:
    """Indent a generated block to sit inside a code() template, whose lines start at 16 spaces."""
    return text.replace("\n", "\n" + " " * 16)


def district_checks(prefix: str, values: dict[int, float]) -> str:
    lines = [f'check.number("{prefix}, District {d}", {v}, districts[{d}])' for d, v in values.items()]
    return _inline("\n".join(lines))


def spread_check(high: int, low: int, value: float) -> str:
    return _inline(dedent(
        f'''
        check.fact("Highest and lowest district", "District {high} and District {low}",
                   f"District {{districts.idxmax()}} and District {{districts.idxmin()}}",
                   (districts.idxmax(), districts.idxmin()) == ({high}, {low}))
        check.number("Spread from District {low} to District {high}, points", {value}, districts.max() - districts.min())
        '''
    ).strip())


def range_check(low: float, mid: float, high: float, keep: str = "enough") -> str:
    return _inline(dedent(
        f'''
        for name, memo, value in zip(["10th", "50th", "90th"], [{low}, {mid}, {high}], sf.percentile_range(share, {keep})):
            check.number(f"Precinct share, {{name}} percentile", memo, value)
        '''
    ).strip())


def census_checks(values: dict[str, float], keep: str = "sf.census_frame(data)") -> str:
    lines = [f"r = sf.census_correlations(data, share, {keep})", "display(r.to_frame())"]
    lines += [f'check.number("Correlation with {k}", {v}, r["{k}"], 2)' for k, v in values.items()]
    return _inline("\n".join(lines))


def measure_notebook(letter: str, title: str, cells: list[tuple[str, str]]) -> dict:
    slug = f"measure_{letter.lower()}"
    return {
        "file": f"{title}.ipynb",
        "heading": f"Measure {letter}",
        "cells": [
            md("## Citywide result"),
            code(
                f'''
                city = sf.citywide(data, "{slug}__yes", "{slug}__no")
                city
                '''
            ),
            md("## Precinct and supervisor-district geography"),
            code(two_way_section(f"{slug}__yes", f"{slug}__no", "Yes share")),
            *cells,
        ],
    }


NOTEBOOKS = [
    {
        "file": "01_data_turnout_and_census.ipynb",
        "heading": None,
        "title": "Data, turnout, and census",
        "cells": [
            md(
                """
                ## The precinct data

                The shapes, the Statement of the Vote, and the citywide totals have to agree before
                anything else is worth reading. `reconciliation.csv` is the check the analysis ran
                against the full Statement of the Vote workbook. The second table below repeats it
                here for the featured contests, using only the files in `source/`.
                """
            ),
            code(
                """
                results = pd.read_csv(ROOT / "source" / "precinct_results.csv")
                reconciliation = pd.read_csv(ROOT / "source" / "reconciliation.csv")
                shapes, rows = set(data["precinct_id"]), set(results["precinct_id"])
                check.number("Precinct polygons", 514, len(data), 0)
                check.fact("Polygons matched to the Statement of the Vote", "all 514",
                           f"{len(shapes & rows)} matched, {len(shapes ^ rows)} unmatched",
                           shapes == rows and len(shapes) == 514)
                check.number("Largest gap between precinct sums and citywide totals, all contests",
                             0, reconciliation["difference"].abs().max(), 0)
                reconciliation.head()
                """
            ),
            code(
                """
                trend = pd.read_csv(ROOT / "source" / "citywide_trend.csv")
                report9 = trend[trend["report"] == trend["report"].max()]
                contests = {
                    "hilton": ("GOVERNOR", "STEVE HILTON"),
                    "becerra": ("GOVERNOR", "XAVIER BECERRA"),
                    "chan": ("UNITED STATES REPRESENTATIVE, DISTRICT 11", "CONNIE CHAN"),
                    "wiener": ("UNITED STATES REPRESENTATIVE, DISTRICT 11", "SCOTT WIENER"),
                }
                for measure in sf.local_measures(data):
                    slug = measure.lower().replace(" ", "_")
                    contests[f"{slug}__yes"] = (measure, "YES")
                    contests[f"{slug}__no"] = (measure, "NO")
                rows = []
                for column, (contest, choice) in contests.items():
                    official = report9[(report9["contest"] == contest) & (report9["choice"] == choice)]["votes"].sum()
                    rows.append({"column": column, "precinct sum": int(data[column].sum()), "citywide report": int(official)})
                sums = pd.DataFrame(rows)
                sums["difference"] = sums["precinct sum"] - sums["citywide report"]
                check.number("Largest gap for the featured contests, from source/ alone", 0, sums["difference"].abs().max(), 0)
                sums
                """
            ),
            md("## Precincts left off the maps"),
            code(
                """
                zero = data.loc[data["registered"].fillna(0) == 0, ["precinct_id", "Neighborhood", "Supervisorial"]]
                check.fact("Precincts with no registered voters", "9901, 9902, 9903, 9904",
                           ", ".join(str(i) for i in sorted(zero["precinct_id"])),
                           set(zero["precinct_id"]) == {9901, 9902, 9903, 9904})
                zero
                """
            ),
            md(
                """
                ## Party registration

                The Department's registration-by-party page is citywide only, and it is a different
                vintage from the Statement of the Vote.
                """
            ),
            code(
                """
                party = pd.read_csv(ROOT / "source" / "citywide_party.csv").set_index("group")["registered"]
                check.number("Registered voters, party page", 541778, party["Total Registration"], 0)
                check.number("Democratic", 337357, party["Democratic"], 0)
                check.number("Republican", 40457, party["Republican"], 0)
                check.number("No party preference or unknown", 141468, party["No Party Preference/Unknown"], 0)
                check.number("Registered voters, Statement of the Vote", 535608, data["registered"].sum(), 0)
                party.to_frame()
                """
            ),
            md("## Turnout and mail"),
            code(
                """
                ballots, registered, mail = data["ballots"].sum(), data["registered"].sum(), data["mail_ballots"].sum()
                check.number("Turnout, percent", 64.01, 100 * ballots / registered, 2)
                check.number("Ballots counted", 342844, ballots, 0)
                check.number("Mail ballots", 304904, mail, 0)
                check.number("Mail share, percent", 88.93, 100 * mail / ballots, 2)
                check.number("Election-day ballots", 37940, ballots - mail, 0)

                share = data["ballots"] / data["registered"].where(data["registered"] > 0)
                enough = data["ballots"] >= sf.MIN_BALLOTS
                for name, memo, value in zip(["10th", "50th", "90th"], [47.8, 66.1, 76.2], sf.percentile_range(share, enough)):
                    check.number(f"Precinct turnout, {name} percentile", memo, value)

                grouped = data.groupby("Supervisorial")[["ballots", "registered"]].sum()
                (100 * grouped["ballots"] / grouped["registered"]).round(1).to_frame("Turnout by supervisor district, percent")
                """
            ),
            code(
                """
                sf.rate_map(data, share, data["ballots"], "Turnout by precinct",
                            "Ballots counted divided by registered voters. Precincts under 50 ballots are hatched gray.",
                            "Turnout", cmap="YlGnBu", diverging=False, limits=(0.25, 0.85))
                """
            ),
            code(
                f"""
                {census_checks({"Bachelor's degree or higher": 0.80, "Non-Hispanic white": 0.79})}
                keep = sf.census_frame(data)
                sf.census_scatter(data[keep].assign(share=share[keep]), "share", "ba_share", None,
                                  "Turnout and bachelor’s degrees", "Bachelor’s degree or higher, share of adults 25+", "Turnout (%)");
                """
            ),
            md(
                """
                ## Census characteristics

                Assigning census blocks to precincts happens upstream, in the analysis, because it needs
                the block shapes. `census_qc.json` is its record. The citywide shares are recomputed here
                from `census_precinct.csv`.
                """
            ),
            code(
                """
                census = pd.read_csv(ROOT / "source" / "census_precinct.csv")
                qc = sf.read_json(ROOT, "census_qc.json")
                check.number("People in the 2020 county count", 873965, census["pop"].sum(), 0)
                check.number("People assigned to a precinct", 873965, qc["population_assigned"], 0)
                check.number("Blocks a precinct line cuts", 33, qc["blocks_split"], 0)
                check.number("Population in those blocks, percent", 0.3, 100 * qc["split_population_share"], 1)
                check.number("Other blocks where internal point and land area disagree", 0,
                             qc["unsplit_blocks_where_internal_point_disagrees"], 0)
                check.number("Bachelor's degree or higher, percent of adults 25+", 60, 100 * census["ba_plus"].sum() / census["b15003_e001"].sum(), 0)
                check.number("Renters, percent of occupied units", 62, 100 * census["b25003_e003"].sum() / census["b25003_e001"].sum(), 0)
                check.number("Foreign born, percent", 34, 100 * census["foreign_born"].sum() / census["b05001_e001"].sum(), 0)
                check.number("Households at $150,000 or more, percent", 48, 100 * census["hh_150k"].sum() / census["b19001_e001"].sum(), 0)
                qc
                """
            ),
        ],
    },
    {
        "file": "02_governor.ipynb",
        "heading": "Governor, inside the city",
        "cells": [
            md("## Citywide result"),
            code(
                """
                city = sf.citywide(data, "hilton", "becerra")
                check.number("Becerra votes", 280594, city["becerra"], 0)
                check.number("Hilton votes", 50784, city["hilton"], 0)
                check.number("Hilton share of the two-candidate vote, percent", 15.3, city["share_pct"])
                city
                """
            ),
            md("## Precinct and supervisor-district geography"),
            code(two_way_section("hilton", "becerra", "Hilton share")),
            code(
                f"""
                {range_check(6.8, 15.4, 25.4)}
                {district_checks("Hilton share", {4: 23.7, 11: 20.9, 2: 18.5, 7: 17.4, 8: 7.5, 9: 9.8, 5: 9.9})}
                {spread_check(4, 8, 16.2)}
                """
            ),
            code(
                """
                sf.rate_map(data, share, votes, "Governor: Steve Hilton's share inside San Francisco",
                            "Share of the Hilton + Becerra vote. This is the San Francisco county vote, not the state result.",
                            "Hilton share", cmap="OrRd", diverging=False, limits=(0.0, 0.40))
                sf.district_bars(data.assign(weight=votes, share=share), "share", None,
                                 "Hilton share of the two-candidate vote, by supervisor district", "Hilton share (%)", reference=None);
                """
            ),
            md("## Census comparison"),
            code(
                f"""
                {census_checks({"Non-Hispanic Asian": 0.70, "Foreign born": 0.54, "Non-Hispanic white": -0.45, "Renters": -0.40})}
                keep = sf.census_frame(data)
                sf.census_scatter(data[keep].assign(share=share[keep]), "share", "nh_asian_share", None,
                                  "Governor and Asian population", "Non-Hispanic Asian share of 2020 population",
                                  "Steve Hilton share of the two-candidate vote (%)");
                """
            ),
        ],
    },
    {
        "file": "03_ca11.ipynb",
        "heading": "CA-11",
        "cells": [
            md("## Citywide result and the district line"),
            code(
                """
                in_ca11 = data["Congressional"] == 11
                city = sf.citywide(data, "wiener", "chan")
                check.number("Wiener votes", 157394, city["wiener"], 0)
                check.number("Wiener share, percent", 53.6, city["share_pct"])
                check.number("Chan votes", 136435, city["chan"], 0)
                check.number("Chan share, percent", 46.4, 100 - city["share_pct"])
                check.number("Precincts in CA-11", 453, in_ca11.sum(), 0)
                check.number("Precincts in CA-15", 61, (data["Congressional"] == 15).sum(), 0)
                city
                """
            ),
            code(
                """
                ca15 = data[data["Congressional"] == 15]["Neighborhood"].value_counts()
                band = ["EXCELSIOR", "OUTER MISSION", "OCEANVIEW/MERCED/INGLESIDE", "PORTOLA", "VISITACION VALLEY"]
                check.number("CA-15 precincts in the five southern neighborhoods", 56, ca15.reindex(band).fillna(0).sum(), 0)
                check.fact("The other CA-15 precincts", "around McLaren Park and in Bayview",
                           dict(ca15.drop(band, errors="ignore")),
                           set(ca15.drop(band, errors="ignore").index) <= {"MCLAREN PARK", "BAYVIEW HUNTERS POINT"})
                lake = data[data["Neighborhood"] == "LAKESHORE"]
                check.fact("Lake Merced corner (Lakeshore precincts) is in CA-11", "all in CA-11",
                           f"{(lake['Congressional'] == 11).sum()} of {len(lake)}", bool((lake["Congressional"] == 11).all()))
                ca15.to_frame("CA-15 precincts")
                """
            ),
            md("## Precinct and supervisor-district geography, CA-11 precincts only"),
            code(
                """
                share, votes = sf.two_way(data, "chan", "wiener")
                enough = (data["ballots"] >= sf.MIN_BALLOTS) & in_ca11
                ca11 = data[in_ca11]
                districts = sf.by_district(ca11, "chan", "wiener")
                neighborhoods = sf.by_neighborhood(ca11, "chan", "wiener").sort_values(ascending=False)
                display(neighborhoods.round(1).to_frame("Chan share by neighborhood, percent"))
                districts.round(1).to_frame("Chan share by supervisor district, percent")
                """
            ),
            code(
                f"""
                {range_check(35.2, 46.8, 59.0)}
                chan_leads = ["SUNSET/PARKSIDE", "OUTER RICHMOND", "MISSION", "BAYVIEW HUNTERS POINT", "CHINATOWN"]
                wiener_leads = ["INNER RICHMOND", "CASTRO/UPPER MARKET", "NOE VALLEY", "MARINA", "PACIFIC HEIGHTS"]
                check.fact("Chan leads", ", ".join(chan_leads), neighborhoods[chan_leads].round(1).tolist(), bool((neighborhoods[chan_leads] > 50).all()))
                check.fact("Wiener leads", ", ".join(wiener_leads), neighborhoods[wiener_leads].round(1).tolist(), bool((neighborhoods[wiener_leads] < 50).all()))
                {district_checks("Chan share", {4: 58.9, 9: 53.2, 1: 51.0, 8: 37.2, 2: 37.5, 11: 58.2})}
                sd11 = ca11[ca11["Supervisorial"] == 11]
                check.number("Supervisor District 11 votes in this race", 1745, sd11["chan"].sum() + sd11["wiener"].sum(), 0)
                """
            ),
            code(
                """
                sf.rate_map(data, share, votes, "CA-11: Connie Chan's share of the two-candidate vote",
                            "Scott Wiener and Connie Chan, both Democrats. Hatched gray precincts are in CA-15 or cast under 50 ballots.",
                            "Chan share", cmap="PuOr", keep=in_ca11, missing_label="In CA-15, or fewer than 50 ballots")
                sf.district_bars(ca11.assign(weight=votes[in_ca11], share=share[in_ca11]), "share", None,
                                 "CA-11: Chan share by supervisor district (CA-11 precincts only)",
                                 "Chan share of the two-candidate vote (%)");
                """
            ),
            md("## Census comparison, CA-11 precincts only"),
            code(
                f"""
                keep = sf.census_frame(data) & in_ca11
                {census_checks({"Non-Hispanic white": -0.70, "Bachelor's degree or higher": -0.63, "Non-Hispanic Asian": 0.55, "Foreign born": 0.48}, keep="keep")}
                sf.census_scatter(data[keep].assign(share=share[keep]), "share", "nh_asian_share", None,
                                  "CA-11 and Asian population", "Non-Hispanic Asian share of 2020 population",
                                  "Connie Chan share of the two-candidate vote (%)");
                """
            ),
        ],
    },
    measure_notebook(
        "B",
        "04_measure_b",
        [
            code(
                f"""
                check.number("Yes votes", 164430, city["measure_b__yes"], 0)
                check.number("No votes", 149904, city["measure_b__no"], 0)
                check.number("Yes share, percent", 52.3, city["share_pct"])
                {range_check(39.4, 53.1, 65.3)}
                {district_checks("Yes share", {9: 64.1, 5: 62.1, 10: 55.4, 8: 54.0, 2: 41.0, 7: 45.2, 4: 45.8})}
                {spread_check(9, 2, 23.1)}
                """
            ),
            code(
                """
                sf.rate_map(data, share, votes, "Measure B: yes share",
                            "Establishing A Municipal Finance Corporation And A Public Bank. Hatched gray precincts cast fewer than 50 ballots.",
                            "Yes share")
                sf.district_bars(data.assign(weight=votes, share=share), "share", None,
                                 "Measure B yes share, by supervisor district", "Yes share (%)");
                """
            ),
            md("## The November 4 report"),
            code(
                """
                trend = pd.read_csv(ROOT / "source" / "citywide_trend.csv")
                b = trend[trend["contest"] == "Measure B"].pivot_table(index=["report", "folder"], columns="choice", values="votes")
                b["yes_pct"] = 100 * b["YES"] / (b["YES"] + b["NO"])
                nov4 = b.xs("20261104", level="folder").iloc[0]
                check.number("No lead on the November 4 report, votes", 144, nov4["NO"] - nov4["YES"], 0)
                check.number("Yes share on the November 4 report, percent", 49.96, nov4["yes_pct"], 2)
                sf.line_chart(trend, None)
                b
                """
            ),
            md("## Census comparison"),
            code(
                f"""
                {census_checks({"Hispanic": 0.55, "Renters": 0.44, "Households at $150,000+": -0.44, "Foreign born": 0.07})}
                keep = sf.census_frame(data)
                subset = data[keep].assign(share=share[keep])
                sf.census_scatter(subset, "share", "hispanic_share", None, "Measure B and Hispanic population",
                                  "Hispanic share of 2020 population", "Measure B yes share (%)")
                sf.census_scatter(subset, "share", "renter_share", None, "Measure B and renters",
                                  "Renter share of occupied housing units", "Measure B yes share (%)");
                """
            ),
        ],
    ),
    measure_notebook(
        "G",
        "05_measure_g",
        [
            code(
                f"""
                check.number("Yes votes", 110545, city["measure_g__yes"], 0)
                check.number("No votes", 210437, city["measure_g__no"], 0)
                check.number("Yes share, percent", 34.4, city["share_pct"])
                {range_check(18.9, 33.8, 51.6)}
                {district_checks("Yes share", {1: 49.8, 4: 49.6, 11: 45.2, 7: 40.2, 8: 21.3, 5: 22.6, 6: 25.1})}
                {spread_check(1, 8, 28.5)}
                """
            ),
            md("## The widest range, and the east-west split"),
            code(
                """
                featured = {"Governor (Hilton)": ("hilton", "becerra", None), "CA-11 (Chan)": ("chan", "wiener", 11)}
                featured.update({m: (f"measure_{m[-1].lower()}__yes", f"measure_{m[-1].lower()}__no", None)
                                 for m in ["Measure B", "Measure G", "Measure I", "Measure D"]})
                ranges = {}
                for name, (named, other, district) in featured.items():
                    contest_share, _ = sf.two_way(data, named, other)
                    keep = data["ballots"] >= sf.MIN_BALLOTS
                    if district:
                        keep = keep & (data["Congressional"] == district)
                    low, _mid, high = sf.percentile_range(contest_share, keep)
                    ranges[name] = high - low
                ranges = pd.Series(ranges, name="10th to 90th percentile, points").sort_values(ascending=False)
                check.fact("Widest precinct range of the six contests", "Measure G", ranges.idxmax(), ranges.idxmax() == "Measure G")

                geography = sf.geography_correlations(data, share, votes >= sf.MIN_BALLOTS)
                check.number("Correlation with easting", -0.52, geography["east-west (easting)"], 2)
                check.number("Correlation with latitude", -0.37, geography["north-south (latitude)"], 2)
                screen = sf.screen_measures(data, sf.local_measures(data)).set_index("contest")
                sharp = screen.index[screen["east_west_r"].abs() >= 0.5].tolist()
                check.fact("The one local measure with an east-west correlation of 0.5 or more", "Measure G", sharp, sharp == ["Measure G"])
                display(ranges.to_frame())
                geography.to_frame()
                """
            ),
            code(
                """
                sf.rate_map(data, share, votes, "Measure G: yes share",
                            "Allowing Private Vehicles On The Great Highway In Sunset Dunes Park. Hatched gray precincts cast fewer than 50 ballots.",
                            "Yes share")
                """
            ),
            md("## Census comparison"),
            code(
                f"""
                {census_checks({"Non-Hispanic Asian": 0.67, "Foreign born": 0.46, "Renters": -0.52, "Non-Hispanic white": -0.52})}
                keep = sf.census_frame(data)
                sf.census_scatter(data[keep].assign(share=share[keep]), "share", "nh_asian_share", None,
                                  "Measure G and Asian population", "Non-Hispanic Asian share of 2020 population", "Measure G yes share (%)");
                """
            ),
        ],
    ),
    measure_notebook(
        "I",
        "06_measure_i",
        [
            code(
                f"""
                check.number("Yes votes", 150595, city["measure_i__yes"], 0)
                check.number("No votes", 163542, city["measure_i__no"], 0)
                check.number("Yes share, percent", 47.9, city["share_pct"])
                check.number("No lead, votes", 12947, -city["margin"], 0)
                {range_check(35.1, 48.9, 60.8)}
                {district_checks("Yes share", {9: 58.9, 5: 57.6, 6: 50.7, 10: 50.6, 2: 37.1, 7: 40.4, 4: 43.4})}
                {spread_check(9, 2, 21.8)}
                """
            ),
            md("## Next to Measure B"),
            code(
                """
                b_share, _ = sf.two_way(data, "measure_b__yes", "measure_b__no")
                enough = data["ballots"] >= sf.MIN_BALLOTS
                side_by_side = pd.DataFrame({"Measure B": sf.by_district(data, "measure_b__yes", "measure_b__no"), "Measure I": districts})
                side_by_side["B minus I, points"] = side_by_side["Measure B"] - side_by_side["Measure I"]
                print("Precinct correlation of the B and I yes shares:", round(b_share[enough].corr(share[enough]), 2))
                side_by_side.round(1)
                """
            ),
            code(
                """
                sf.rate_map(data, share, votes, "Measure I: yes share",
                            "Changes To Real Property Transfer Tax. Hatched gray precincts cast fewer than 50 ballots.", "Yes share")
                """
            ),
            md("## Census comparison"),
            code(
                f"""
                {census_checks({"Hispanic": 0.50, "Renters": 0.48, "Households at $150,000+": -0.49})}
                """
            ),
        ],
    ),
    measure_notebook(
        "D",
        "07_measure_d",
        [
            code(
                f"""
                check.number("Yes votes", 175442, city["measure_d__yes"], 0)
                check.number("No votes", 146680, city["measure_d__no"], 0)
                check.number("Yes share, percent", 54.5, city["share_pct"])
                {range_check(43.7, 51.7, 67.2)}
                geography = sf.geography_correlations(data, share, votes >= sf.MIN_BALLOTS)
                check.number("Correlation with easting", 0.01, geography["east-west (easting)"], 2)
                check.number("Correlation with latitude", 0.37, geography["north-south (latitude)"], 2)
                {district_checks("Yes share", {2: 67.7, 6: 58.7, 8: 58.5, 7: 58.2, 9: 44.6, 11: 48.1, 4: 48.9, 5: 49.4})}
                under = sorted(districts.index[districts < 50])
                check.fact("Districts under half", "4, 5, 9, 11", under, under == [4, 5, 9, 11])
                {spread_check(2, 9, 23.0)}
                geography.to_frame()
                """
            ),
            md("## Neighborhoods in the districts the memo names"),
            code(
                """
                named = data[data["Supervisorial"].isin([4, 5, 9, 11])]
                (named.groupby("Supervisorial")["Neighborhood"]
                      .agg(lambda n: ", ".join(f"{k.title()} ({v})" for k, v in n.value_counts().items()))
                      .to_frame("Neighborhoods (precincts)"))
                """
            ),
            code(
                """
                sf.rate_map(data, share, votes, "Measure D: yes share",
                            "Changes To Ballot Measure Process. Hatched gray precincts cast fewer than 50 ballots.", "Yes share")
                """
            ),
            md("## Census comparison"),
            code(
                f"""
                {census_checks({"Non-Hispanic white": 0.58, "Bachelor's degree or higher": 0.55, "Hispanic": -0.53, "Households at $150,000+": 0.46})}
                """
            ),
        ],
    ),
    {
        "file": "08_other_local_measures.ipynb",
        "heading": "Where the other local measures sit",
        "cells": [
            md(
                """
                ## The screen

                A local measure gets a map when its citywide yes share is within 5 points of 50, or
                when its precinct yes share has an east-west correlation of 0.5 or more (either sign).
                The correlation uses precincts with at least 50 votes on the measure.
                """
            ),
            code(
                """
                titles = sf.read_json(ROOT, "measure_titles.json")
                screen = sf.screen_measures(data, sf.local_measures(data)).set_index("contest")
                screen["title"] = screen.index.map(titles)
                screen["mapped"] = ((screen["yes_pct"] - 50).abs() <= 5) | (screen["east_west_r"].abs() >= 0.5)
                mapped = sorted(screen.index[screen["mapped"]])
                check.fact("Measures that earn a map", "B, D, G, I", mapped,
                           mapped == ["Measure B", "Measure D", "Measure G", "Measure I"])
                check.number("Smallest supervisor-district spread, points", 18.2, screen["district_spread_points"].min())
                check.number("Largest supervisor-district spread, points", 28.5, screen["district_spread_points"].max())
                screen[["title", "yes_pct", "east_west_r", "district_spread_points", "mapped"]]
                """
            ),
            code(
                """
                table = {"A": (68.2, -0.06), "C": (81.7, 0.46), "E": (64.0, -0.03), "F": (59.7, -0.05),
                         "H": (74.3, 0.37), "J": (80.9, 0.35), "RTM": (79.0, 0.42)}
                for letter, (yes_pct, east_west) in table.items():
                    row = screen.loc[f"Measure {letter}"]
                    check.number(f"Measure {letter} yes share, percent", yes_pct, row["yes_pct"])
                    check.number(f"Measure {letter} east-west r", east_west, row["east_west_r"], 2)
                    check.fact(f"Measure {letter} passed", "passed", f"{row['yes_pct']:.1f}% yes", row["yes_pct"] > 50)
                """
            ),
        ],
    },
]


def memo_section(findings: str, heading: str | None) -> tuple[str, str]:
    """The memo's title (or section heading) and its paragraphs, without the figure lines."""
    title = re.search(r"^# (.+)$", findings, flags=re.M).group(1)
    if heading is None:
        body = findings.split("\n## ", 1)[0].split("\n", 1)[1]
    else:
        match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", findings, flags=re.M | re.S)
        if match is None:
            raise KeyError(f"FINDINGS.md has no section '## {heading}'")
        body = match.group(1)
        title = heading
    paragraphs = [
        p.strip()
        for p in body.strip().split("\n\n")
        if p.strip() and not p.strip().startswith("![")
    ]
    return title, "\n>\n".join("> " + p.replace("\n", "\n> ") for p in paragraphs)


def build_notebook(spec: dict, findings: str):
    heading, quote = memo_section(findings, spec["heading"])
    title = spec.get("title", heading)
    cells = [
        nbformat.v4.new_markdown_cell(f"# {title}\n\nFrom `FINDINGS.md`:\n\n{quote}\n\n{INTRO}"),
        nbformat.v4.new_code_cell(SETUP.strip()),
    ]
    for kind, text in spec["cells"]:
        maker = nbformat.v4.new_code_cell if kind == "code" else nbformat.v4.new_markdown_cell
        cells.append(maker(text))
    cells.append(nbformat.v4.new_markdown_cell("## Numbers the memo quotes"))
    cells.append(nbformat.v4.new_code_cell(REPORT))
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata = {
        "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
        "language_info": {"name": "python"},
        "colab": {"provenance": []},
    }
    return notebook


def build(drive: Path, findings_path: Path) -> list[Path]:
    findings = findings_path.read_text(encoding="utf-8")
    folder = drive / "notebooks"
    written = []
    for spec in NOTEBOOKS:
        notebook = build_notebook(spec, findings)
        NotebookClient(
            notebook,
            timeout=600,
            kernel_name="python3",
            record_timing=False,
            resources={"metadata": {"path": str(folder)}},
        ).execute()
        # Fixed ids so an unchanged notebook rebuilds to an identical file.
        for number, cell in enumerate(notebook.cells):
            cell["id"] = f"cell-{number:02d}"
            cell.get("metadata", {}).pop("execution", None)
        path = folder / spec["file"]
        nbformat.write(notebook, path)
        written.append(path)
        print("ran", path.name)
    return written
