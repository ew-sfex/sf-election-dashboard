# Source files

These are the inputs the Colab notebooks read.

- `precinct_results.csv` — one row per precinct. Report 9 of the Statement of the Vote, joined to the August 17, 2026 district crosswalk.
- `census_precinct.csv` — 2020 census counts and ACS 2020–2024 characteristics apportioned to those precincts.
- `precincts.geojson` — the 514 precinct shapes, WGS84, with the same results columns.
- `citywide_trend.csv` — citywide totals from summary reports 1 and 4 through 9. The precinct sums are checked against Report 9, and Measure B's November 4 numbers come from Report 5.
- `reconciliation.csv` — precinct sums against the electionwide totals for every contest in the Statement of the Vote workbook.
- `citywide_party.csv` — the Department's citywide registration-by-party page.
- `census_qc.json` — the record of how census blocks were assigned to precincts.
- `measure_titles.json` — the ballot title of each local measure.

The raw Statement of the Vote workbook and the census download are upstream of these files. They are large and are not in this folder.
