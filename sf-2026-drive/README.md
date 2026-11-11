# SF 2026 precinct findings

This is the folder to review, then upload to Google Drive yourself. Nothing here has been uploaded.

Upload the whole folder and keep its layout: the notebooks find their data in the `source/` folder next to `notebooks/`. Renaming the folder or putting it inside another Drive folder is fine. Each notebook mounts Drive and finds it.

- `REPORTER_MEMO.md` is the short version for reporters: the top findings, safe and unsafe wording, and the charts to build. Every number in it is also in `FINDINGS.md`, and the build stops if one isn't.
- `FINDINGS.md` is the full findings note, with the maps in `figures/`. The notebooks check every number in it.
- `notebooks/` has one Colab notebook per section of the note, and the Datawrapper export.
- `source/` is the data every notebook reads: precinct results, census characteristics, precinct shapes, and the citywide checks.
- `tables/measure_screening.csv` is the screen behind “Where the other local measures sit” in the findings note.
- `datawrapper/` is the export notebook's output: one precinct CSV, one supervisor-district CSV, a precinct GeoJSON, and two late-count CSVs for the line and bar charts.

## Notebooks

Open a notebook in Colab and choose Runtime → Run all. The first cell mounts Drive and loads `notebooks/sf2026.py`, the shared code that also drew the figures in `figures/`. Nothing is downloaded. Each section notebook starts with that section's text from the note, computes everything it says, and draws its maps and charts. The last cell lists every number the section quotes next to the computed value, and stops with an error if any differ.

| Notebook | Memo section |
| --- | --- |
| `01_data_turnout_and_census.ipynb` | The opening: data checks, precincts left off the maps, party registration, turnout and mail, census assignment |
| `02_governor.ipynb` | Governor, inside the city |
| `03_ca11.ipynb` | CA-11 |
| `04_measure_b.ipynb` | Measure B, including the November 4 report |
| `05_measure_g.ipynb` | Measure G |
| `06_measure_i.ipynb` | Measure I |
| `07_measure_d.ipynb` | Measure D |
| `08_other_local_measures.ipynb` | Where the other local measures sit |
| `09_late_count.ipynb` | The late count: votes counted by November 4 and since, report by report, and what it would take to flip Measure I |
| `export_datawrapper.ipynb` | Writes the files in `datawrapper/` |

## Datawrapper

Run `notebooks/export_datawrapper.ipynb` to rewrite the files in `datawrapper/`. In Datawrapper, upload `datawrapper/precincts.geojson` as the map and match it to `datawrapper/precincts.csv` on `precinct_id`. Use `datawrapper/districts.csv` for the supervisor-district bar charts, and `datawrapper/trend.csv` and `datawrapper/late_count.csv` for the late-count charts. Details are in `datawrapper/README.md`.
