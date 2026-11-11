"""Parse a San Francisco Statement of the Vote workbook.

The Department publishes the SOV as one printed worksheet per contest. Each
precinct is a block of Election Day, Vote by Mail, and Total rows. Countywide
totals sit on the rows labeled "Electionwide - Total", "Cumulative - Total",
and "Countywide - Total".
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

CHANNEL_MAP = {
    "Election Day": "election_day",
    "Vote by Mail": "vote_by_mail",
    "Total": "total",
}
SUMMARY_LEVELS = {
    "Electionwide - Total": "electionwide",
    "Cumulative - Total": "cumulative",
    "Countywide - Total": "countywide",
}
HEADER_SKIP = {
    "precinct",
    "registered voters",
    "undervotes",
    "overvotes",
    "total votes",
    "voters cast",
    "% turnout",
}
PARTY_RE = re.compile(r"\(([A-Z]{2,5})\)\s*$")
PRECINCT_RE = re.compile(r"(\d+)")


def _clean(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\n", " ").split())


def _header_key(value) -> str:
    return _clean(value).lower()


def _as_int(value) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(round(value))
    text = str(value).replace(",", "").strip()
    if not text or text.endswith("%") or text.upper() == "N/A":
        return 0
    try:
        return int(round(float(text)))
    except ValueError:
        return 0


def _split_choice(raw: str) -> tuple[str, str]:
    match = PARTY_RE.search(raw)
    if not match:
        return raw, ""
    return raw[: match.start()].strip(), match.group(1)


def _precinct_id(label: str) -> str:
    match = PRECINCT_RE.search(label)
    if not match:
        raise ValueError(f"Precinct label has no number: {label!r}")
    return match.group(1)


def _contest_title(rows: list[tuple]) -> str:
    """Contest name sits in column A. The corner timestamp is not a contest."""
    for row in rows[:6]:
        if not row or not isinstance(row[0], str):
            continue
        text = _clean(row[0])
        if not text or text.startswith("Page:") or text.startswith("City and County"):
            continue
        if _header_key(text) in HEADER_SKIP or text in {"Precinct", "Countywide", "Electionwide", "Cumulative"}:
            continue
        return text
    return ""


def _header_map(row: tuple) -> dict:
    """Column index to field name. Candidate columns keep their display name."""
    fields: dict[int, str] = {}
    for index, value in enumerate(row):
        key = _header_key(value)
        if not key or key in HEADER_SKIP:
            continue
        if key == "registered voters":
            fields[index] = "registered"
        else:
            fields[index] = _clean(value)
    # Registered and the structural columns are detected by key, even when the
    # skip set above dropped them. Re-scan for the numeric structural columns.
    for index, value in enumerate(row):
        key = _header_key(value)
        if key == "registered voters":
            fields[index] = "registered"
        elif key == "undervotes":
            fields[index] = "undervotes"
        elif key == "overvotes":
            fields[index] = "overvotes"
        elif key == "voters cast":
            fields[index] = "Ballots cast"
    return fields


def _find_header(rows: list[tuple]) -> tuple[int, dict] | None:
    for index, row in enumerate(rows[:8]):
        keys = {_header_key(value) for value in row}
        if "precinct" in keys and ("registered voters" in keys or "voters cast" in keys):
            return index, _header_map(row)
    return None


def _rows(path: Path) -> list[tuple[str, list[tuple]]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheets = []
    try:
        for name in workbook.sheetnames:
            worksheet = workbook[name]
            sheets.append((name, list(worksheet.iter_rows(values_only=True))))
    finally:
        workbook.close()
    return sheets


def parse_sov(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return precinct rows and countywide summary rows in long form."""
    path = Path(path)
    precinct_records: list[dict] = []
    summary_records: list[dict] = []

    for _sheet, rows in _rows(path):
        found = _find_header(rows)
        if found is None:
            continue
        _header_index, fields = found
        contest = _contest_title(rows) or "Turnout"
        choices = [name for name in fields.values() if name not in {"registered", "undervotes", "overvotes"}]
        if not choices:
            continue
        current: str | None = None
        for row in rows:
            label = _clean(row[0]) if row else ""
            if not label or label.startswith("Page:"):
                continue
            if label in CHANNEL_MAP and current:
                channel = CHANNEL_MAP[label]
                base = {
                    "contest": contest,
                    "precinct_id": _precinct_id(current),
                    "precinct_label": current,
                    "mail_ballot_precinct": "MB" in current.upper(),
                    "channel": channel,
                    "registered": _as_int(_field(row, fields, "registered")),
                    "undervotes": _as_int(_field(row, fields, "undervotes")),
                    "overvotes": _as_int(_field(row, fields, "overvotes")),
                }
                for index, name in fields.items():
                    if name in {"registered", "undervotes", "overvotes"}:
                        continue
                    choice, party = _split_choice(name)
                    precinct_records.append(
                        {
                            **base,
                            "choice": choice,
                            "party": party,
                            "votes": _as_int(row[index] if index < len(row) else None),
                        }
                    )
                continue
            if label.upper().startswith("PCT "):
                current = label
                continue
            if label in SUMMARY_LEVELS:
                current = None
                level = SUMMARY_LEVELS[label]
                base = {
                    "contest": contest,
                    "level": level,
                    "registered": _as_int(_field(row, fields, "registered")),
                    "undervotes": _as_int(_field(row, fields, "undervotes")),
                    "overvotes": _as_int(_field(row, fields, "overvotes")),
                }
                for index, name in fields.items():
                    if name in {"registered", "undervotes", "overvotes"}:
                        continue
                    choice, party = _split_choice(name)
                    summary_records.append(
                        {
                            **base,
                            "choice": choice,
                            "party": party,
                            "votes": _as_int(row[index] if index < len(row) else None),
                        }
                    )
                continue
            current = None

    precinct = pd.DataFrame(precinct_records)
    summary = pd.DataFrame(summary_records)
    return precinct, summary


def _field(row: tuple, fields: dict, name: str):
    for index, field_name in fields.items():
        if field_name == name and index < len(row):
            return row[index]
    return None


def parse_summary_xml(path: str | Path) -> tuple[pd.DataFrame, dict]:
    """Citywide candidate totals from one summary.xml report."""
    root = ET.parse(path).getroot()
    title = root.find(".//{*}Title/{*}Report")
    report_line = ""
    if title is not None:
        lines = [line.strip() for line in title.get("Textbox8", "").replace("\r", "").split("\n") if line.strip()]
        report_line = lines[-1] if lines else ""
    match = re.search(r"(\d+)\s*$", report_line)
    report = int(match.group(1)) if match else None
    elector = root.find(".//{*}electorGroupId2")
    ballots = int((elector.get("ballots3") or "0").replace(",", "")) if elector is not None else 0
    records = []
    for group in root.findall(".//{*}ContestIdGroup"):
        contest = _clean(group.get("contestId"))
        if not contest:
            continue
        for node in group.findall(".//{*}chGroup"):
            choice_raw = ""
            votes = None
            for element in node.iter():
                tag = element.tag.split("}")[-1]
                if tag == "candidateNameTextBox4" and element.get("candidateNameTextBox4"):
                    choice_raw = _clean(element.get("candidateNameTextBox4"))
                if tag == "Textbox13" and element.get("vot8") is not None:
                    votes = _as_int(element.get("vot8"))
            if not choice_raw or votes is None:
                continue
            choice, party = _split_choice(choice_raw)
            records.append(
                {
                    "contest": contest,
                    "choice": choice,
                    "party": party,
                    "votes": votes,
                }
            )
    frame = pd.DataFrame(records)
    return frame, {"report": report, "report_line": report_line, "ballots": ballots}


def reconcile(precinct: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    """Compare the sum of precinct totals with the electionwide total.

    Cumulative ballots are reported separately. They are not inside the
    precinct sum. A zero difference means every electionwide vote is on a
    precinct row.
    """
    precinct_totals = (
        precinct[precinct["channel"] == "total"]
        .groupby(["contest", "choice"], as_index=False)["votes"]
        .sum()
        .rename(columns={"votes": "precinct_votes"})
    )
    electionwide = summary[summary["level"] == "electionwide"][
        ["contest", "choice", "votes"]
    ].rename(columns={"votes": "electionwide_votes"})
    cumulative = summary[summary["level"] == "cumulative"][
        ["contest", "choice", "votes"]
    ].rename(columns={"votes": "cumulative_votes"})
    merged = precinct_totals.merge(electionwide, on=["contest", "choice"], how="outer")
    merged = merged.merge(cumulative, on=["contest", "choice"], how="left")
    for column in ("precinct_votes", "electionwide_votes", "cumulative_votes"):
        merged[column] = merged[column].fillna(0).astype(int)
    merged["difference"] = (
        merged["precinct_votes"] + merged["cumulative_votes"] - merged["electionwide_votes"]
    )
    return merged.sort_values(["contest", "choice"]).reset_index(drop=True)
