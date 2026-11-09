# SF 2026 precinct findings

This is the folder to review, then upload to Google Drive yourself. Nothing here has been uploaded.

After it is on Drive, open `notebooks/export_datawrapper.ipynb` in Colab. The notebook reads the files in `source/` and writes the Datawrapper files into `datawrapper/`.

- `FINDINGS.md` is the findings note, with the maps in `figures/`.
- `source/` is the precinct-level input: results, census characteristics, and the precinct shapes.
- `tables/measure_screening.csv` is the screen behind “Where the other local measures sit” in the findings note.
- `datawrapper/` is the output: one precinct CSV, one supervisor-district CSV, and a precinct GeoJSON.

In Datawrapper, upload `datawrapper/precincts.geojson` as the map and match it to `datawrapper/precincts.csv` on `precinct_id`. Use `datawrapper/districts.csv` for the supervisor-district bar charts. Details are in `datawrapper/README.md`.
