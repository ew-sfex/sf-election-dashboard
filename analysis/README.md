# Precinct findings for the November 3, 2026 election

Tables and maps for a post-election memo. This folder does not feed the live results page.

```bash
pip install -r analysis/requirements.txt
python analysis/run_all.py
```

Raw downloads go in `analysis/raw/` and are not committed. Tables and figures land in `analysis/output/`. The last step, `build_drive.py`, copies the findings note, its figures, the source tables, and `sf2026.py` into `sf-2026-drive/`. It then writes and runs one Colab notebook per memo section (`build_notebooks.py`), reruns the Datawrapper export notebook, and rebuilds `sf-2026-drive.zip`. Each section notebook checks every number its section quotes, so the build stops if `FINDINGS.md` and the data disagree. When you change a number in the note, change it in `build_notebooks.py` too. Edit `analysis/FINDINGS.md` and `analysis/sf2026.py`, not the copies in the Drive folder.

## Sources

- Statement of the Vote, Preliminary Report 11 (November 10, 2026, 4:00 p.m. Pacific), plus Report 5 (November 4) for the Measure B comparison. Citywide trend uses summary reports 1 and 4 through 11. To move to a later report, change `REPORT_NUMBER`, `REPORT_FOLDER`, and `REPORT_RELEASED` in `sf2026.py`, add the folder to `SUMMARY_FOLDERS` in `build_findings.py`, and rerun. The section notebooks then list every memo number that moved.
- Precinct shapes: DataSF “Election Precincts — Current, Defined 2022” (`d6x4-hefw`). 514 polygons, one per reporting precinct. The join on precinct number is exact.
- District and neighborhood names: Department of Elections crosswalk `N26_ConsolDistBT_20260817.xlsx` (August 17, 2026). Use this, not the 2022 district fields on the shapes, for congressional and supervisor district.
- Four precincts have no registered voters: Angel Island (`9904`), Alameda Island (`9903`), and two small inland precincts, `9901` (Outer Mission) and `9902` (Portola). They stay in the data file and are left off the maps.
- Party: the Department’s citywide registration-by-party page. It is not a precinct file, and its total does not match the 535,608 registered voters on the Statement of the Vote. No precinct party map is produced.
- 2020 PL 94-171 for race, Hispanic origin, voting-age population, group quarters, and housing, on 2020 census blocks.
- ACS 2020–2024 five-year tables: block-group B15003 (education), B25003 (tenure), and B19001 (income). B05001 (nativity) is a tract table in this summary file. Foreign born is naturalized citizens plus non-citizens.

## How a tract number becomes a precinct number

Blocks nest in block groups and tracts by GEOID. The spatial join is block to precinct. Each block is placed with the Census internal point. If at least 95% of the block’s land area is in one precinct, the whole block goes there. If a precinct line cuts the block, the block is split by land area. The run writes the share of population that needed a split to `output/census_qc.json`.

Race, Hispanic origin, voting-age population, group quarters, and housing are summed from the blocks. Education is spread with 2020 voting-age population as the weight, because the block file has no population age 25 and over. Tenure and income are spread with occupied housing units. Nativity is spread from the tract with total population. Rates are summed numerators over summed denominators.

These are precinct descriptions, not statements about how a demographic group voted. ACS figures move with the parent block group’s margin of error. `ba_cv` on each precinct is the coefficient of variation of the bachelor’s-or-higher count in the block group that contributes the most 2020 population.

## Figures

Report 11, unless a filename says otherwise. Precincts under 50 ballots are hatched gray on rate maps. Precinct 9723 reports more ballots than registered voters on Report 11 and is left off the turnout map. Each diverging map’s color scale is set evenly around 50% and wide enough to hold every precinct, and the build fails if a value falls past the end of any color bar.

- `turnout.png`, `mail_share.png`
- `governor_hilton.png`, `governor_by_district.png` — San Francisco votes only
- `ca11_chan.png`, `ca11_by_district.png` — CA-11 precincts only
- `measure_b_yes.png`, `measure_b_by_district.png`. `measure_b_trend.png` and `measure_b_ballots_after_nov4.png` are the canvass path for that one measure
- `measure_g_yes.png`, `measure_i_yes.png`, `measure_d_yes.png` — the other local measures that are either close or sharply east-west
- Census scatters, after `apportion_census.py`: Measure B against renters and against Hispanic share, CA-11 against Asian share, the governor’s race against Asian share, Measure G against Asian share, turnout against bachelor’s degrees
