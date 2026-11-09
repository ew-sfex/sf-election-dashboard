# Precinct findings, November 3, 2026

Preliminary Statement of the Vote, Report 9, published November 8, 2026 at 5:00 p.m. Phoenix (4:00 p.m. Pacific). Certification is due December 3. Every figure is stamped with that report. Citywide totals below are San Francisco votes only.

The precinct map is the right one. DataSF’s 2022 precinct shapes have 514 polygons, and all 514 match the Statement of the Vote. Supervisor district and congressional district come from the Department of Elections crosswalk of August 17, 2026, not from the older district fields on the shapes. Angel Island and Alameda Island are zero-voter boundary precincts. They stay in the data file and are left off the maps. Treasure Island stays on the maps. Precinct totals plus the cumulative bucket match the electionwide totals with a difference of zero, and the cumulative bucket for Measure B is zero, so every counted ballot is already in a precinct.

## Party registration is citywide only

The 2026 results index does not publish registration by precinct and party. The citywide page, saved in `output/citywide_party.csv`, lists 541,778 registered voters: 337,357 Democratic, 40,457 Republican, and 141,468 no party preference or unknown. That total is not the 535,608 registered voters on the Statement of the Vote, and the page is a live file, so it is a different vintage. It is recorded and not mapped.

## Turnout

342,844 ballots counted out of 535,608 registered, 64.01 percent. Mail ballots are 304,904 of those, 88.93 percent, and election-day ballots are 37,940. Among precincts with at least 50 ballots, turnout runs from 47.8 percent at the 10th percentile to 66.1 percent at the median and 76.2 percent at the 90th. The map is higher in the north, the center, and the west, and lower in the southeast. Four precincts have no ballots counted. Six have fewer than 50, and those are gray on the rate maps.

`output/figures/turnout.png`, `output/figures/mail_share.png`.

## Governor, inside the city

Xavier Becerra 280,594, Steve Hilton 50,784. Hilton’s share of the two-candidate vote is 15.3 percent. This is the San Francisco county vote. Among precincts with at least 50 ballots, Hilton’s share runs from 6.8 percent to 15.4 percent to 25.4 percent at the 10th, 50th, and 90th percentiles. The higher shares are on the west side and in the south. Supervisor District 4 is 23.7 percent Hilton and District 11 is 20.9 percent. District 8 is 7.5 percent and District 5 is 9.9 percent.

The demographic companion is the Asian share of the 2020 population. Across 498 precincts with at least 50 ballots and group quarters under a quarter of the population, Hilton’s share rises with the non-Hispanic Asian share (Pearson r = 0.70). That is a precinct pattern. It does not say how Asian residents voted.

`output/figures/governor_hilton.png`, `output/figures/governor_by_district.png`, `output/figures/governor_vs_asian.png`.

## CA-11

Scott Wiener 157,394 (53.6 percent), Connie Chan 136,435 (46.4 percent). Both are Democrats, so the map uses a purple-orange scale rather than red and blue. The district is 453 of 514 precincts on the 2026 crosswalk. The southwest of the city, which is in CA-15, is gray. Chan’s precinct shares, among those with at least 50 ballots, run from 35.2 percent to 46.8 percent to 59.0 percent. She is ahead in the Sunset and the Richmond. Wiener is ahead through the center and the northern neighborhoods. On the District 11 precincts only, Chan’s vote-weighted share is 58.9 percent in supervisor District 4 and 51.0 percent in District 1, against 37.2 percent in District 8 and 37.5 percent in District 2. District 11 contributes only about 1,700 votes to this race, because most of that supervisor district sits in CA-15.

Chan’s share also rises with the non-Hispanic Asian share of the precinct (r = 0.55, 438 precincts). It is lower where the non-Hispanic white share is higher (r = −0.70) and where the bachelor’s-degree share is higher (r = −0.63). Those three move together geographically. The chart shows the Asian relationship.

`output/figures/ca11_chan.png`, `output/figures/ca11_by_district.png`, `output/figures/ca11_vs_asian.png`.

## Measure B flipped after November 4

Establishing a Municipal Finance Corporation and a Public Bank. Yes share of Yes plus No:

| Report | Ballots counted | Yes | No | Yes share |
| --- | ---: | ---: | ---: | ---: |
| 1 | 154,364 | 69,434 | 73,858 | 48.5% |
| 4 | 185,032 | 85,175 | 85,805 | 49.8% |
| 5 (Nov. 4) | 206,320 | 95,222 | 95,366 | 49.96% |
| 6 (Nov. 5) | 256,382 | 120,900 | 115,401 | 51.2% |
| 7 | 307,917 | 146,415 | 137,078 | 51.6% |
| 8 | 332,467 | 158,565 | 147,159 | 51.9% |
| 9 (Nov. 8) | 342,844 | 164,430 | 149,904 | 52.3% |

Report 5 is the last report with No ahead, by 144 votes. Rounded to one decimal that 49.96 percent prints as 50.0, which is why the chart keeps two decimals there. The lead changed between the November 4 report and the November 5 report. Reports 2 and 3 were not available for this pull. From Report 5 to Report 9 the added Yes and No votes were 69,208 and 54,538, which is 55.9 percent yes. No precinct lost votes between those two reports.

On the current map the yes vote is stronger in the center and the east and weaker on the west side. The east-west correlation of the precinct yes share with easting is 0.35. Vote-weighted supervisor-district shares run from 41.0 percent in District 2 and 45.2 percent in District 7 to 62.1 percent in District 5 and 64.1 percent in District 9, a 23-point spread. The ballots counted after November 4 are greener than the early count, including in parts of the west, and the late map is still browner in the Richmond and parts of the Sunset.

Precincts with a larger Hispanic share of the 2020 population voted yes at a higher rate (r = 0.55). Precincts with a larger renter share did too (r = 0.44), and precincts with a larger share of households at $150,000 or more voted yes at a lower rate (r = −0.45). Foreign-born share barely moves with Measure B (r = 0.07). Same ecological limit as above.

`output/figures/measure_b_trend.png`, `output/figures/measure_b_yes.png`, `output/figures/measure_b_ballots_after_nov4.png`, `output/figures/measure_b_by_district.png`, `output/figures/measure_b_vs_hispanic.png`, `output/figures/measure_b_vs_renters.png`.

## The other local measures that stood out

The screen is in `output/measure_screening.csv`. A measure besides B is mapped when the citywide yes share is within 5 points of 50, or when the east-west correlation is at least 0.5 in absolute value. Supervisor-district spreads of 18 to 28 points are ordinary in this city, so spread alone did not earn a map.

Measure G, allowing private vehicles on the Great Highway in Sunset Dunes Park, lost: 110,545 yes and 210,437 no, 34.4 percent yes. It is the sharpest east-west split of the local measures (r = −0.52). The ocean side voted yes at a much higher rate than the center of the city. District 1 is 49.8 percent yes and District 4 is 49.6 percent. District 8 is 21.3 percent and District 5 is 22.6 percent. The yes share rises with the non-Hispanic Asian share of the precinct (r = 0.67) and falls with the renter share (r = −0.52).

Measure I, changes to the real property transfer tax, is close: 150,595 yes and 163,542 no, 47.9 percent yes. District 9 is 58.9 percent yes and District 2 is 37.1 percent. The east-west correlation is 0.32.

Measure D, changes to the ballot measure process, is the other one inside five points of 50 percent: 175,442 yes and 146,680 no, 54.5 percent yes. It does not split east-west (r = 0.01). It does split north-south. The precinct yes share rises with latitude (r = 0.37): the north side is greener and the south side is paler.

`output/figures/measure_g_yes.png`, `output/figures/measure_g_vs_asian.png`, `output/figures/measure_i_yes.png`, `output/figures/measure_d_yes.png`.

## Census, and how a block becomes a precinct

2020 population assigned to precincts is 873,965, which is the census count for the county. Of 5,986 blocks, 33 are split by a precinct line, and those hold 3,007 people, 0.3 percent of the city. On every block that was not split, the Census internal point falls in the same precinct as the land-area majority. Race, Hispanic origin, voting-age population, group quarters, and housing are summed from the blocks. Education, tenure, and income are ACS 2020–2024 block-group counts, spread by voting-age population or by occupied housing units. Nativity is the tract table, because this summary file does not publish it for block groups. Foreign born, naturalized citizens plus non-citizens, is 34 percent of the ACS population. Bachelor’s degree or higher is 60 percent of adults 25 and older. Renters are 62 percent of occupied housing units. Households at $150,000 or more are 48 percent.

Turnout rises with the bachelor’s share (r = 0.80) and with the non-Hispanic white share (r = 0.79), and it is lower where the foreign-born share is higher (r = −0.63). The chart is the education relationship. Group-quarters precincts, 25 percent or more of the 2020 population, are left off the scatters so a jail or a dorm does not read as a neighborhood.

`output/census_precinct.csv`, `output/census_qc.json`, `output/figures/turnout_vs_bachelors.png`.
