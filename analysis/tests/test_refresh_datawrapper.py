"""Scale, source line, and blank-precinct labels for the Datawrapper drafts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from refresh_datawrapper import (  # noqa: E402
    BLANK,
    CA15,
    blank_label,
    map_metadata,
    report_number,
    source_line,
    symmetric_limits,
)


def test_source_line_follows_the_report_number():
    assert report_number("REPORT_NUMBER = 11\n") == 11
    assert source_line(11) == "San Francisco Department of Elections, Preliminary Report 11."
    assert source_line(12) == "San Francisco Department of Elections, Preliminary Report 12."


def test_diverging_limits_match_the_memo_rule():
    # 13.1 and 70.1 around 50, in steps of 5, is 10 to 90.
    assert symmetric_limits([13.1, 50, 70.1]) == (10, 90)
    # Measures B and I together reach 16.4, which rounds the half-span up to 35.
    assert symmetric_limits([16.4, 81.4, 23.4, 80.6]) == (15, 85)


def test_precinct_key_stays_text_so_the_basemap_joins():
    # A number-typed precinct_id uploads and then matches nothing on the
    # built-in 2022 precinct basemap. Text joins.
    meta = map_metadata(
        11,
        "Yes share by precinct.",
        "measure_g_yes_pct",
        10,
        90,
        ["#543005", "#f5f5f5", "#01665e"],
        "Yes share",
        "{{ neighborhood_name }}<br>{{ measure_g_yes_pct }}% yes",
        [BLANK],
    )
    assert meta["data"]["column-format"]["precinct_id"]["type"] == "text"
    assert meta["visualize"]["basemap"] == "usa-sanfran-prescincts-2022"
    assert meta["visualize"]["map-key-attr"] == "Prec_2022"
    assert meta["axes"]["keys"] == "precinct_id"


def test_blank_precincts_and_ca15():
    under = {"measure_g_yes_pct": "", "chan_pct": "", "ca11_status": "In CA-11, fewer than 50 ballots"}
    outside = {"measure_g_yes_pct": "34.0", "chan_pct": "", "ca11_status": CA15}
    filled = {"measure_g_yes_pct": "49.6", "chan_pct": "51.2", "ca11_status": "In CA-11"}
    assert blank_label(under, "measure_g_yes_pct", chan=False) == BLANK
    assert blank_label(filled, "measure_g_yes_pct", chan=False) == ""
    assert blank_label(outside, "chan_pct", chan=True) == CA15
    assert blank_label(under, "chan_pct", chan=True) == BLANK
    assert blank_label(filled, "chan_pct", chan=True) == ""
