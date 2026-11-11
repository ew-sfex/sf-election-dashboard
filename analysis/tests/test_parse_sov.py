"""Parser checks against a miniature Statement of the Vote sheet."""

import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from parse_sov import parse_sov, reconcile  # noqa: E402


def _write_fixture(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"] = "Page: 1 of 1"
    sheet["A2"] = "Measure B"
    sheet["A4"] = "Precinct"
    sheet["B4"] = "Registered \nVoters"
    sheet["C4"] = "Undervotes"
    sheet["E4"] = "Overvotes"
    sheet["F4"] = "Precinct"
    sheet["G4"] = "YES\n "
    sheet["I4"] = "NO\n "
    sheet["K4"] = "Total Votes"

    rows = [
        (5, "Countywide"),
        (6, "Electionwide"),
        (7, "PCT 1101"),
        (8, "Election Day", 10, 0, 0, 4, 1),
        (9, "Vote by Mail", 10, 0, 0, 3, 2),
        (10, "Total", 10, 0, 0, 7, 3),
        (11, "PCT 1102 MB"),
        (12, "Election Day", 5, 0, 0, 0, 1),
        (13, "Vote by Mail", 5, 0, 0, 2, 1),
        (14, "Total", 5, 0, 0, 2, 2),
        (15, "Electionwide - Total", 15, 0, 0, 9, 5),
        (16, "Cumulative"),
        (17, "Cumulative - Total", 0, 0, 0, 0, 0),
        (18, "Countywide - Total", 15, 0, 0, 9, 5),
    ]
    for item in rows:
        row = item[0]
        sheet.cell(row, 1, item[1])
        if len(item) > 2:
            sheet.cell(row, 2, item[2])
            sheet.cell(row, 3, item[3])
            sheet.cell(row, 5, item[4])
            sheet.cell(row, 6, item[1])
            sheet.cell(row, 7, item[5])
            sheet.cell(row, 9, item[6])
    workbook.save(path)


def test_precinct_totals_match_electionwide(tmp_path: Path) -> None:
    path = tmp_path / "sov.xlsx"
    _write_fixture(path)
    precinct, summary = parse_sov(path)

    totals = precinct[(precinct["channel"] == "total") & (precinct["choice"] == "YES")]
    assert list(totals["precinct_id"]) == ["1101", "1102"]
    assert bool(totals.loc[totals["precinct_id"] == "1102", "mail_ballot_precinct"].iloc[0])
    assert int(totals["votes"].sum()) == 9

    mail = precinct[
        (precinct["channel"] == "vote_by_mail")
        & (precinct["precinct_id"] == "1101")
        & (precinct["choice"] == "NO")
    ]
    assert int(mail["votes"].iloc[0]) == 2

    check = reconcile(precinct, summary)
    assert (check["difference"] == 0).all()
    electionwide = summary[(summary["level"] == "electionwide") & (summary["choice"] == "NO")]
    assert int(electionwide["votes"].iloc[0]) == 5
    assert summary["contest"].nunique() == 1


def test_reconcile_flags_a_gap(tmp_path: Path) -> None:
    precinct = pd.DataFrame(
        [
            {
                "contest": "Measure B",
                "choice": "YES",
                "channel": "total",
                "votes": 4,
            }
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "contest": "Measure B",
                "choice": "YES",
                "level": "electionwide",
                "votes": 5,
            },
            {
                "contest": "Measure B",
                "choice": "YES",
                "level": "cumulative",
                "votes": 0,
            },
        ]
    )
    check = reconcile(precinct, summary)
    assert int(check["difference"].iloc[0]) == -1
