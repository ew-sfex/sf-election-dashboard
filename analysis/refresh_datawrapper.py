#!/usr/bin/env python3
"""Refresh the unpublished Datawrapper drafts for the precinct findings.

The drafts live in the SF Examiner workspace, in a folder named
"SF 2026 precinct findings". The script creates them the first time and
uploads new data on later runs. It never publishes.

Maps use Datawrapper's built-in "USA » San Francisco » Precincts (2022)"
basemap (usa-sanfran-prescincts-2022), joined on Prec_2022 = precinct_id.
The API rejects a GeoJSON upload, and that basemap already matches every
precinct in the file except 9904 Angel Island, which has no voters.

Report 12, expected November 17: point the analysis at the new report,
regenerate sf-2026-drive/datawrapper/, then run this again. The source
line follows REPORT_NUMBER in analysis/sf2026.py, and the diverging map
scales are recomputed from the CSVs so a new extreme is not clipped.

    export DATAWRAPPER_API_TOKEN=...   # do not commit it or pass it as an argument
    python analysis/refresh_datawrapper.py

The token is read from the environment and is never printed.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "sf-2026-drive" / "datawrapper"
STATE = ROOT / "analysis" / "datawrapper_charts.json"
SF2026 = ROOT / "analysis" / "sf2026.py"
API = "https://api.datawrapper.de/v3"
TEAM_ID = "TmK4eKmz"
FOLDER_NAME = "SF 2026 precinct findings"
BASEMAP = "usa-sanfran-prescincts-2022"
MAP_KEY = "Prec_2022"
NOTE = "Results are preliminary."
BLANK = "Fewer than 50 ballots."
CA15 = "In CA-15"
EDIT = "https://app.datawrapper.de/chart/{id}/visualize"

# ColorBrewer BrBG and PuOr, the same ramps the map renderer ships.
# Index 5 sits at the center of the scale.
BRBG = [
    "#543005",
    "#8c510a",
    "#bf812d",
    "#d8b365",
    "#f6e8c3",
    "#f5f5f5",
    "#c7eae5",
    "#80cdc1",
    "#35978f",
    "#01665e",
    "#003c30",
]
PUOR = [
    "#7f3b08",
    "#b35806",
    "#e08214",
    "#fdb863",
    "#fee0b6",
    "#f7f7f7",
    "#d8daeb",
    "#b2abd2",
    "#8073ac",
    "#542788",
    "#2d004b",
]

# Titles are the finding sentences in analysis/REPORTER_MEMO.md.
TITLES = {
    "trend": "The late count changed the local measures.",
    "late": "The late count changed the local measures.",
    "measure_g": "Measure G lost even on the ocean side.",
    "chan": "CA-11 split the west side from the north.",
    "hilton": "Hilton ran strongest in the west and south.",
    "measure_b": "Measures B and I drew on the same parts of the city.",
    "measure_i": "Measures B and I drew on the same parts of the city.",
    "measure_d": "Measure D split north and south, not east and west.",
}


def report_number(source: str | None = None) -> int:
    text = source if source is not None else SF2026.read_text()
    match = re.search(r"^REPORT_NUMBER\s*=\s*(\d+)", text, re.M)
    if not match:
        raise SystemExit(f"REPORT_NUMBER is missing from {SF2026}")
    return int(match.group(1))


def source_line(number: int) -> str:
    return f"San Francisco Department of Elections, Preliminary Report {number}."


def symmetric_limits(values: list[float], center: float = 50.0, step: float = 5.0) -> tuple[float, float]:
    """Same rule as sf2026.symmetric_limits, on the 0–100 scale the CSVs use."""
    if not values:
        raise ValueError("no values for a color scale")
    spread = max(abs(value - center) for value in values)
    half = math.ceil(round(spread / step, 9)) * step
    return round(center - half, 2), round(center + half, 2)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def numbers(rows: list[dict[str, str]], column: str) -> list[float]:
    return [float(row[column]) for row in rows if row[column] != ""]


def write_csv(rows: list[dict[str, str]], fieldnames: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in fieldnames})
    return buffer.getvalue()


def axis_note(trend: list[dict[str, str]]) -> str:
    pairs = [f"{row['report']} = {row['date_label']}" for row in trend]
    return "Horizontal axis is the report number. " + "; ".join(pairs) + "."


def blank_label(row: dict[str, str], column: str, chan: bool) -> str:
    if row[column] != "":
        return ""
    if chan and row["ca11_status"] == CA15:
        return CA15
    return BLANK


def palette_stops(colors: list[str]) -> list[dict[str, float | str]]:
    last = len(colors) - 1
    return [{"color": color, "position": index / last} for index, color in enumerate(colors)]


def colorscale(colors: list[str], low: float, high: float) -> dict:
    return {
        "map": {},
        "mode": "continuous",
        "stops": "equidistant",
        "colors": palette_stops(colors),
        "palette": 0,
        "rangeMin": str(low),
        "rangeMax": str(high),
        "rangeCenter": "50",
        "stopCount": 5,
        "customStops": [None, 50, None, "", "", "", "", "", ""],
        "categoryOrder": [],
        "interpolation": "equidistant",
        "categoryLabels": {},
    }


def color_legend(title: str) -> dict:
    return {
        "color": {
            "size": 210,
            "title": title,
            "labels": "ranges",
            "enabled": True,
            "offsetX": 0,
            "offsetY": 0,
            "reverse": False,
            "labelMax": "high",
            "labelMin": "low",
            "position": "above",
            "hideItems": [],
            "interactive": False,
            "labelCenter": "medium",
            "labelFormat": "0",
            "orientation": "horizontal",
            "customLabels": [],
            "titleEnabled": True,
        },
        "pattern": {
            "size": 210,
            "title": "",
            "enabled": True,
            "offsetX": 0,
            "offsetY": 0,
            "position": "above",
            "interactive": False,
            "orientation": "horizontal",
            "titleEnabled": False,
            "useColorLegendPosition": True,
        },
        "combined": {"orientation": "horizontal"},
    }


def pattern_map(labels: list[str]) -> dict:
    mapped = {
        label: {"label": label, "type": "diagonal-up", "width": 1.2, "gap": 4}
        for label in labels
    }
    return {
        "enabled": True,
        "opacity": 70,
        "colorType": "auto-contrast",
        "order": labels,
        "map": mapped,
    }


def tooltip(title: str, body: str) -> dict:
    return {"enabled": True, "sticky": True, "title": title, "body": body}


class Datawrapper:
    def __init__(self, token: str) -> None:
        self.token = token

    def request(self, method: str, path: str, payload: dict | list | bytes | str | None = None, content_type: str | None = None) -> tuple[int, bytes]:
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        body = None
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload).encode()
            headers["Content-Type"] = content_type or "application/json"
        elif isinstance(payload, str):
            body = payload.encode()
            headers["Content-Type"] = content_type or "text/plain"
        elif isinstance(payload, bytes):
            body = payload
            if content_type:
                headers["Content-Type"] = content_type
        request = urllib.request.Request(API + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise SystemExit(f"{method} {path} failed ({error.code}): {detail[:500]}") from None

    def json(self, method: str, path: str, payload: dict | None = None) -> dict:
        status, raw = self.request(method, path, payload)
        if not raw:
            return {"_status": status}
        return json.loads(raw)

    def folders(self) -> list[dict]:
        listing = self.json("GET", "/folders")["list"]
        team = next(item for item in listing if item.get("id") == TEAM_ID)
        found: list[dict] = []

        def walk(nodes: list[dict]) -> None:
            for node in nodes:
                found.append(node)
                walk(node.get("folders") or [])

        walk(team.get("folders") or [])
        return found

    def ensure_folder(self, state: dict) -> int:
        if state.get("folderId"):
            return int(state["folderId"])
        for folder in self.folders():
            if folder.get("name") == FOLDER_NAME:
                return int(folder["id"])
        created = self.json(
            "POST",
            "/folders",
            {"name": FOLDER_NAME, "organizationId": TEAM_ID},
        )
        if "id" not in created:
            created = self.json("POST", "/folders", {"name": FOLDER_NAME, "teamId": TEAM_ID})
        if "id" not in created:
            raise SystemExit(f"Could not create the folder. Response keys: {sorted(created)}")
        return int(created["id"])

    def ensure_chart(self, state: dict, key: str, chart_type: str, folder_id: int) -> str:
        charts = state.setdefault("charts", {})
        existing = charts.get(key, {}).get("id")
        if existing:
            chart = self.json("GET", f"/charts/{existing}")
            if chart.get("publishedAt"):
                raise SystemExit(f"{key} ({existing}) is published. This script does not publish or edit published charts.")
            return existing
        created = self.json(
            "POST",
            "/charts",
            {
                "title": TITLES[key],
                "type": chart_type,
                "organizationId": TEAM_ID,
                "folderId": folder_id,
                "language": "en-US",
                "theme": "datawrapper",
            },
        )
        return created["id"]


def describe(number: int, intro: str) -> dict:
    return {
        "source-name": source_line(number),
        "source-url": "",
        "intro": intro,
        "byline": "",
        "aria-description": "",
        "number-format": "-",
        "number-divisor": 0,
        "number-append": "",
        "number-prepend": "",
        "hide-title": False,
    }


def column_format(name: str, kind: str, number_format: str = "0.0", append: str = "") -> dict:
    if kind == "text":
        return {"type": "text", "ignore": False}
    return {
        "type": "number",
        "ignore": False,
        "number-format": number_format,
        "number-append": append,
        "number-prepend": "",
        "number-divisor": 0,
    }


def base_metadata(number: int, intro: str, visualize: dict, axes: dict, formats: dict) -> dict:
    return {
        "describe": describe(number, intro),
        "annotate": {"notes": NOTE},
        "visualize": visualize,
        "axes": axes,
        "data": {
            "transpose": False,
            "vertical-header": True,
            "horizontal-header": True,
            "column-format": formats,
        },
    }


def map_metadata(number: int, intro: str, column: str, low: float, high: float, colors: list[str], legend: str, body: str, pattern_labels: list[str]) -> dict:
    visualize = {
        "basemap": BASEMAP,
        "basemapProjection": "geoAzimuthalEqualArea",
        "map-key-attr": MAP_KEY,
        "map-type-set": True,
        "chart-type-set": True,
        "zoomable": True,
        "hide-empty-regions": False,
        "map-padding": 8,
        "max-map-height": 560,
        "colorscale": colorscale(colors, low, high),
        "legends": color_legend(legend),
        "patterns": pattern_map(pattern_labels),
        "tooltip": tooltip("{{ neighborhood_name }}", body),
    }
    # The 2022 basemap key is numeric, but a number-typed column does not join.
    # A text column does: the renderer coerces both sides with Number().
    formats = {
        "precinct_id": {"type": "text", "ignore": False},
        column: column_format(column, "number", "0.0", ""),
        "neighborhood_name": column_format("neighborhood_name", "text"),
        "ca11_status": column_format("ca11_status", "text"),
        "blank_label": column_format("blank_label", "text"),
    }
    axes = {"keys": "precinct_id", "values": column, "pattern": "blank_label"}
    return base_metadata(number, intro, visualize, axes, formats)


def chart_plan(number: int) -> list[dict]:
    precincts = read_csv(DATA / "precincts.csv")
    trend = read_csv(DATA / "trend.csv")
    late = read_csv(DATA / "late_count.csv")
    districts = read_csv(DATA / "districts.csv")
    b_and_i = symmetric_limits(numbers(precincts, "measure_b_yes_pct") + numbers(precincts, "measure_i_yes_pct"))
    scales = {
        "measure_g_yes_pct": symmetric_limits(numbers(precincts, "measure_g_yes_pct")),
        "measure_d_yes_pct": symmetric_limits(numbers(precincts, "measure_d_yes_pct")),
        "chan_pct": symmetric_limits(numbers(precincts, "chan_pct")),
        "measure_b_yes_pct": b_and_i,
        "measure_i_yes_pct": b_and_i,
    }

    def map_csv(column: str, chan: bool) -> str:
        prepared = []
        for row in precincts:
            prepared.append({**row, "blank_label": blank_label(row, column, chan)})
        return write_csv(prepared, list(precincts[0]) + ["blank_label"])

    trend_csv = write_csv(
        [
            {
                "report": row["report"],
                "date_label": row["date_label"],
                "Measure B": row["measure_b_yes_pct"],
                "Measure I": row["measure_i_yes_pct"],
                "Measure D": row["measure_d_yes_pct"],
            }
            for row in trend
        ],
        ["report", "date_label", "Measure B", "Measure I", "Measure D"],
    )
    late_csv = write_csv(
        [
            {
                "measure": row["measure"],
                "Counted by Nov. 4": row["counted_by_nov_4_yes_pct"],
                "Counted since": row["counted_since_yes_pct"],
            }
            for row in late
        ],
        ["measure", "Counted by Nov. 4", "Counted since"],
    )
    hilton_rows = sorted(districts, key=lambda row: float(row["hilton_pct"]), reverse=True)
    hilton_csv = write_csv(
        [{"district_label": row["district_label"], "hilton_pct": row["hilton_pct"]} for row in hilton_rows],
        ["district_label", "hilton_pct"],
    )

    def one_map(key: str, column: str, intro: str, legend: str, body: str, colors: list[str], chan: bool = False) -> dict:
        low, high = scales[column]
        labels = [CA15, BLANK] if chan else [BLANK]
        return {
            "key": key,
            "type": "d3-maps-choropleth",
            "csv": map_csv(column, chan),
            "metadata": map_metadata(number, intro, column, low, high, colors, legend, body, labels),
        }

    line_formats = {
        "report": column_format("report", "number", "0", ""),
        "date_label": column_format("date_label", "text"),
        "Measure B": column_format("Measure B", "number", "0.00", "%"),
        "Measure I": column_format("Measure I", "number", "0.00", "%"),
        "Measure D": column_format("Measure D", "number", "0.00", "%"),
    }
    line_visualize = {
        "interpolation": "linear",
        "scale-y": "linear",
        "y-grid": "on",
        "x-grid": "off",
        "y-grid-format": "0.00",
        "y-grid-labels": "auto",
        "y-grid-label-align": "left",
        "show-tooltips": True,
        "tooltip-number-format": "0.00",
        "label-colors": True,
        "connector-lines": True,
        "plotHeightMode": "fixed",
        "plotHeightFixed": 320,
        "custom-range-y": ["40", "70"],
        "lines": {
            "Measure B": {"color": "#1b7837", "width": "style2"},
            "Measure I": {"color": "#5aae61", "width": "style2"},
            "Measure D": {"color": "#762a83", "width": "style2"},
        },
        "range-annotations": [
            {
                "type": "y",
                "display": "line",
                "y0": 50,
                "y1": 50,
                "color": "#6e6e6e",
                "opacity": 80,
                "strokeWidth": 1,
                "strokeType": "dashed",
                "label": {
                    "text": "50%",
                    "align": "right",
                    "valign": "top",
                    "color": "#6e6e6e",
                    "bold": False,
                    "italic": False,
                    "size": 11,
                    "uppercase": False,
                    "outline": False,
                },
            }
        ],
        "tooltip": tooltip(
            "{{ date_label }}",
            "Report {{ report }}<br>Measure B: {{ measure_b }}%<br>Measure I: {{ measure_i }}%<br>Measure D: {{ measure_d }}%",
        ),
    }
    arrow_formats = {
        "measure": column_format("measure", "text"),
        "Counted by Nov. 4": column_format("Counted by Nov. 4", "number", "0.00", "%"),
        "Counted since": column_format("Counted since", "number", "0.00", "%"),
    }
    return [
        {
            "key": "trend",
            "type": "d3-lines",
            "csv": trend_csv,
            "metadata": base_metadata(
                number,
                axis_note(trend),
                line_visualize,
                {"x": "report"},
                line_formats,
            ),
        },
        {
            "key": "late",
            "type": "d3-arrow-plot",
            "csv": late_csv,
            "metadata": base_metadata(
                number,
                "Yes share of votes counted by November 4, and of votes counted since.",
                {
                    "thick-arrows": True,
                    "show-arrow-key": True,
                    "y-grid": "on",
                    "reverse-order": False,
                    "value-label-format": "0.00",
                    "range-extent": "nice",
                    "sort-range": {"by": "end", "enabled": False},
                    "replace-flags": "off",
                },
                {"labels": "measure", "start": "Counted by Nov. 4", "end": "Counted since"},
                arrow_formats,
            ),
        },
        one_map(
            "measure_g",
            "measure_g_yes_pct",
            "Yes share by precinct.",
            "Yes share",
            "{{ measure_g_yes_pct }}% yes",
            BRBG,
        ),
        one_map(
            "chan",
            "chan_pct",
            "Connie Chan's share of the two-candidate vote. CA-15 precincts are marked In CA-15.",
            "Chan share",
            "{{ ca11_status }}<br>{{ IF(ISNULL(chan_pct), \"\", FORMAT(chan_pct, \"0.0\") & \"% Chan\") }}",
            PUOR,
            chan=True,
        ),
        {
            "key": "hilton",
            "type": "d3-bars",
            "csv": hilton_csv,
            "metadata": base_metadata(
                number,
                "Share of the Hilton–Becerra vote inside San Francisco, by supervisor district.",
                {
                    "sort-bars": False,
                    "reverse-order": False,
                    "show-value-labels": "always",
                    "value-label-format": "0.0",
                    "value-label-alignment": "right",
                    "thick": True,
                    "base-color": "#1f4e79",
                    "background": False,
                    "force-grid": False,
                    "label-alignment": "left",
                },
                {"labels": "district_label", "bars": "hilton_pct"},
                {
                    "district_label": column_format("district_label", "text"),
                    "hilton_pct": column_format("hilton_pct", "number", "0.0", "%"),
                },
            ),
        },
        one_map(
            "measure_b",
            "measure_b_yes_pct",
            "Measure B yes share by precinct, on the same scale as Measure I.",
            "Yes share",
            "{{ measure_b_yes_pct }}% yes",
            BRBG,
        ),
        one_map(
            "measure_i",
            "measure_i_yes_pct",
            "Measure I yes share by precinct, on the same scale as Measure B.",
            "Yes share",
            "{{ measure_i_yes_pct }}% yes",
            BRBG,
        ),
        one_map(
            "measure_d",
            "measure_d_yes_pct",
            "Yes share by precinct.",
            "Yes share",
            "{{ measure_d_yes_pct }}% yes",
            BRBG,
        ),
    ]


def check_chart(key: str, chart: dict, number: int) -> None:
    if chart.get("publishedAt"):
        raise SystemExit(f"{key} was published. Stopping.")
    if chart.get("organizationId") != TEAM_ID:
        raise SystemExit(f"{key} is not in the SF Examiner workspace.")
    metadata = chart["metadata"]
    if metadata["describe"]["source-name"] != source_line(number):
        raise SystemExit(f"{key} source line is {metadata['describe']['source-name']!r}")
    if metadata["annotate"]["notes"] != NOTE:
        raise SystemExit(f"{key} note is {metadata['annotate']['notes']!r}")
    if chart["title"] != TITLES[key]:
        raise SystemExit(f"{key} title is {chart['title']!r}")
    if chart["type"] == "d3-maps-choropleth":
        visualize = metadata["visualize"]
        if visualize.get("basemap") != BASEMAP or visualize.get("map-key-attr") != MAP_KEY:
            raise SystemExit(f"{key} basemap is {visualize.get('basemap')} / {visualize.get('map-key-attr')}")
        if metadata["axes"].get("values") in {"turnout_pct", "mail_pct"}:
            raise SystemExit(f"{key} is a turnout or mail map.")
        body = visualize.get("tooltip", {}).get("body", "") + visualize.get("tooltip", {}).get("title", "")
        if "neighborhood_name" not in body and "neighborhood_name" not in visualize.get("tooltip", {}).get("title", ""):
            raise SystemExit(f"{key} tooltip does not include neighborhood_name")
    if chart["type"] == "d3-lines":
        lines = metadata["visualize"].get("range-annotations") or []
        if not any(item.get("y0") == 50 and item.get("y1") == 50 for item in lines):
            raise SystemExit("The line chart has no reference line at 50.")
    if chart["type"] in {"d3-scatter-plot", "d3-maps-symbols"}:
        raise SystemExit(f"{key} is a scatter or symbol map.")


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2) + "\n")


def refresh(client: Datawrapper | None = None) -> dict:
    token = os.environ.get("DATAWRAPPER_API_TOKEN", "")
    if client is None:
        if not token:
            raise SystemExit("DATAWRAPPER_API_TOKEN is not set.")
        client = Datawrapper(token)
    number = report_number()
    state = json.loads(STATE.read_text()) if STATE.exists() else {"folderId": None, "charts": {}}
    folder_id = client.ensure_folder(state)
    state["folderId"] = folder_id
    state["folderName"] = FOLDER_NAME
    state["organizationId"] = TEAM_ID
    state["basemap"] = BASEMAP
    state["reportNumber"] = number
    save_state(state)

    for spec in chart_plan(number):
        key = spec["key"]
        chart_id = client.ensure_chart(state, key, spec["type"], folder_id)
        client.request("PUT", f"/charts/{chart_id}/data", spec["csv"], "text/csv")
        client.json(
            "PATCH",
            f"/charts/{chart_id}",
            {
                "title": TITLES[key],
                "folderId": folder_id,
                "organizationId": TEAM_ID,
                "lastEditStep": 4,
                "metadata": spec["metadata"],
            },
        )
        chart = client.json("GET", f"/charts/{chart_id}")
        check_chart(key, chart, number)
        state["charts"][key] = {
            "id": chart_id,
            "title": TITLES[key],
            "type": spec["type"],
            "editUrl": EDIT.format(id=chart_id),
        }
        save_state(state)
        print(f"{key}\t{chart_id}\t{EDIT.format(id=chart_id)}", flush=True)
    return state


def main() -> None:
    refresh()


if __name__ == "__main__":
    main()
