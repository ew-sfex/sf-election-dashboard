# Datawrapper files

Produced by `notebooks/export_datawrapper.ipynb`.

## Map

1. Upload `precincts.geojson` as a custom map.
2. Upload `precincts.csv`.
3. Join on `precinct_id`. The id is an integer in both files.
4. Pick one percentage column to color. Percentages are 0–100, one decimal. A blank cell means the precinct had fewer than 50 ballots, or, for `chan_pct`, the precinct is outside CA-11. `turnout_pct` is also blank for precinct 9723, which reports 840 ballots against 772 registered voters on Report 11.

Color columns: `turnout_pct`, `mail_pct`, `hilton_pct`, `chan_pct`, `measure_b_yes_pct`, `measure_d_yes_pct`, `measure_g_yes_pct`, `measure_i_yes_pct`.

The vote columns and the census percentage columns are there for tooltips. Census percentages are filled for every precinct with population, including precincts under 50 ballots.

## Bar charts

`districts.csv` has one row per supervisor district, 1 through 11. `chan_pct` uses only the CA-11 precincts in that district. Supervisor District 11 contributes only 1,784 votes to CA-11, because most of it is in CA-15.
