# Datawrapper files

Produced by `notebooks/export_datawrapper.ipynb`.

## Map

1. Upload `precincts.geojson` as a custom map.
2. Upload `precincts.csv`.
3. Join on `precinct_id`. The id is an integer in both files.
4. Pick one percentage column to color. Percentages are 0–100, one decimal. A blank cell means the precinct had fewer than 50 ballots, or, for `chan_pct`, the precinct is outside CA-11. `turnout_pct` is also blank for precinct 9723, which reports 840 ballots against 772 registered voters on Report 11.

Tooltip columns: `neighborhood_name` is a readable neighborhood name. `ca11_status` says whether a precinct is in CA-11, in CA-11 with fewer than 50 ballots, or in CA-15; use it in CA-11 tooltips so CA-15 doesn't read as missing data.

Color columns: `turnout_pct`, `mail_pct`, `hilton_pct`, `chan_pct`, `measure_b_yes_pct`, `measure_d_yes_pct`, `measure_g_yes_pct`, `measure_i_yes_pct`.

The vote columns and the census percentage columns are there for tooltips. Census percentages are filled for every precinct with population, including precincts under 50 ballots.

## Bar charts

`districts.csv` has one row per supervisor district, 1 through 11. Use `district_label` ("District 1") for bar labels. `chan_pct` uses only the CA-11 precincts in that district. Supervisor District 11 contributes only 1,784 votes to CA-11, because most of it is in CA-15.

## Late count

`trend.csv` has one row per summary report (1 and 4 through the latest) with the citywide yes share of Measures B, I, and D, two decimals so Report 5's 49.96 doesn't round to 50. `date_label` is the release date ("Nov. 5"); Reports 1 and 4 both came out on election night and read "Nov. 3, first" and "Nov. 3, last". Datawrapper line charts need numbers or dates on the x-axis, so plot against `report` and put `date_label` in the tooltip and axis note; `label` combines both. Use a line chart with a reference line at 50.

`late_count.csv` has the yes share of Measures B, I, D, and G among votes counted by November 4 (Report 5) and among votes counted since, two decimals so Measure B's 49.96 doesn't read as 50. Use a grouped bar or arrow chart.

## Drafts

Unpublished drafts of the charts in `analysis/REPORTER_MEMO.md` are refreshed by `analysis/refresh_datawrapper.py`. Maps use Datawrapper's built-in San Francisco precincts (2022), joined to `precinct_id` on `Prec_2022`. Upload that id as text. A number-typed column matches nothing on this basemap, and the API does not accept `precincts.geojson`.

For Report 12, update `REPORT_NUMBER` in `analysis/sf2026.py`, regenerate this folder, then run `python analysis/refresh_datawrapper.py`. The script reads `DATAWRAPPER_API_TOKEN` from the environment and does not publish. Chart ids and edit links are in `analysis/datawrapper_charts.json`.
