# Precinct findings for the November 3, 2026 election

Tables and maps for a post-election memo. This folder does not feed the live results page.

```bash
pip install -r analysis/requirements.txt
python analysis/run_all.py
```

Raw downloads go in `analysis/raw/` and are not committed. Tables and figures land in `analysis/output/`.

## Sources

- Statement of the Vote, Preliminary Report 9 (November 8, 2026, 4:00 p.m. Pacific), plus Report 5 (November 4) for the Measure B comparison. Citywide trend uses summary reports 1 and 4 through 9.
- Precinct shapes: DataSF “Election Precincts — Current, Defined 2022” (`d6x4-hefw`). 514 polygons, one per reporting precinct. The join on precinct number is exact.
- District and neighborhood names: Department of Elections crosswalk `N26_ConsolDistBT_20260817.xlsx` (August 17, 2026). Use this, not the 2022 district fields on the shapes, for congressional and supervisor district.
- Angel Island (`9904`) and Alameda Island (`9903`) are zero-voter boundary precincts. They stay in the data file and are left off the maps.
- Party: the Department’s citywide registration-by-party page. It is not a precinct file, and its total does not match the 535,608 registered voters on the Statement of the Vote. No precinct party map is produced.
- 2020 PL 94-171 for race, Hispanic origin, voting-age population, group quarters, and housing, on 2020 census blocks.
- ACS 2020–2024 five-year tables: block-group B15003 (education), B25003 (tenure), and B19001 (income). B05001 (nativity) is a tract table in this summary file. Foreign born is naturalized citizens plus non-citizens.

## How a tract number becomes a precinct number

Blocks nest in block groups and tracts by GEOID. The spatial join is block to precinct. Each block is placed with the Census internal point. If at least 95% of the block’s land area is in one precinct, the whole block goes there. If a precinct line cuts the block, the block is split by land area. The run writes the share of population that needed a split to `output/census_qc.json`.

Race, Hispanic origin, voting-age population, group quarters, and housing are summed from the blocks. Education is spread with 2020 voting-age population as the weight, because the block file has no population age 25 and over. Tenure and income are spread with occupied housing units. Nativity is spread from the tract with total population. Rates are summed numerators over summed denominators.

These are precinct descriptions, not statements about how a demographic group voted. ACS figures move with the parent block group’s margin of error. `ba_cv` on each precinct is the coefficient of variation of the bachelor’s-or-higher count in the block group that contributes the most 2020 population.

## Figures

Report 9, unless a filename says otherwise. Precincts under 50 ballots are gray on rate maps.

- `turnout.png`, `mail_share.png`
- `governor_hilton.png`, `governor_by_district.png` — San Francisco votes only
- `ca11_chan.png`, `ca11_by_district.png` — District 11 precincts only
- `measure_b_yes.png`, `measure_b_by_district.png`, `measure_b_trend.png`, `measure_b_ballots_after_nov4.png`
- `measure_g_yes.png`, `measure_i_yes.png`, `measure_d_yes.png` — the other local measures that are either close or sharply east-west
- Census scatters, after `apportion_census.py`: Measure B against renters and against Hispanic share, CA-11 against Asian share, the governor’s race against Asian share, Measure G against Asian share, turnout against bachelor’s degrees
