"""Assign 2020 census blocks to 2026 precincts and spread ACS counts onto them.

Block-to-tract (and block-to-block-group) is the GEOID, not a spatial join.
The spatial join is block to precinct:

- An interior point (the Census internal point) is tested against the precincts.
- A block that lies almost entirely in one precinct stays with that precinct.
- A block a precinct line actually cuts is split by land area.

Race, Hispanic origin, voting-age population, group quarters, and housing come
from the 2020 PL 94-171 file and are summed. Education, tenure, and household
income come from ACS 2020–2024 five-year block-group tables. Nativity comes
from the tract table, because this summary file does not publish B05001 for
block groups. Counts are spread in proportion to a matching 2020 block weight.

    python analysis/apportion_census.py
"""

from __future__ import annotations

import json
import re
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw" / "census"
OUT = ROOT / "output"
UA = "Mozilla/5.0 (compatible; sf-election-findings/1.0)"
CRS = 26910
SPLIT_THRESHOLD = 0.95

PL_ZIP = "https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/California/ca2020.pl.zip"
BLOCK_ZIP = "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/06_CALIFORNIA/06075/tl_2020_06075_tabblock20.zip"
ACS_BASE = "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData"
ACS_TABLES = {
    "b15003": ["E001", "M001", "E022", "M022", "E023", "M023", "E024", "M024", "E025", "M025"],
    "b25003": ["E001", "M001", "E002", "M002", "E003", "M003"],
    "b19001": ["E001", "M001", "E016", "M016", "E017", "M017"],
}
# B05001 is published for tracts in this summary file, not block groups.
# Foreign born is naturalized citizens (E005) plus non-citizens (E006).
TRACT_TABLES = {
    "b05001": ["E001", "E005", "E006"],
}


def _download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=300) as response:
        dest.write_bytes(response.read())


def _coord_indexes(parts: list[str]) -> tuple[int, int]:
    indexes = [i for i, value in enumerate(parts) if re.match(r"^[+-]\d+\.\d+$", value)]
    return indexes[0], indexes[0] - 2, indexes[0] - 1


def load_pl_blocks(zip_path: Path) -> pd.DataFrame:
    """SF block population from the 2020 PL 94-171 pipe files."""
    archive = zipfile.ZipFile(zip_path)
    records = []
    logrecnos = set()
    with archive.open("cageo2020.pl") as handle:
        for raw in handle:
            parts = raw.decode("latin1").rstrip("\n").split("|")
            if len(parts) < 10 or parts[2] != "750" or "US06075" not in parts[8]:
                continue
            _lat, pop_i, hu_i = _coord_indexes(parts)
            geoid = parts[9]
            logrecno = parts[7]
            logrecnos.add(logrecno)
            records.append(
                {
                    "geoid": geoid,
                    "logrecno": logrecno,
                    "pop": int(parts[pop_i] or 0),
                    "housing_units": int(parts[hu_i] or 0),
                }
            )
    geo = pd.DataFrame(records).set_index("logrecno")

    def stream(filename: str) -> dict[str, list[str]]:
        found = {}
        with archive.open(filename) as handle:
            for raw in handle:
                parts = raw.decode("latin1").rstrip("\n").split("|")
                logrecno = parts[4]
                if logrecno in logrecnos:
                    found[logrecno] = [value.strip() for value in parts[5:]]
        return found

    file1 = stream("ca000012020.pl")
    file2 = stream("ca000022020.pl")
    file3 = stream("ca000032020.pl")
    rows = []
    for logrecno, row in geo.iterrows():
        p2 = file1[logrecno]
        p4 = file2[logrecno]
        p5 = file3[logrecno]
        nh_other = (
            int(p2[73])
            - int(p2[75])
            - int(p2[76])
            - int(p2[78])
            - int(p2[81])
        )
        rows.append(
            {
                "geoid": row["geoid"],
                "pop": int(p2[0]),
                "hispanic": int(p2[72]),
                "nh_white": int(p2[75]),
                "nh_black": int(p2[76]),
                "nh_asian": int(p2[78]),
                "nh_other": nh_other,
                "vap": int(p4[0]),
                "vap_hispanic": int(p4[72]),
                "vap_nh_white": int(p4[75]),
                "vap_nh_black": int(p4[76]),
                "vap_nh_asian": int(p4[78]),
                "occupied_hu": int(p4[145]),
                "housing_units_pl": int(p4[144]),
                "gq": int(p5[0]),
                "housing_units_geo": int(row["housing_units"]),
                "pop_geo": int(row["pop"]),
            }
        )
    frame = pd.DataFrame(rows)
    if int(frame["pop"].sum()) != 873965:
        raise SystemExit(f"SF block population summed to {int(frame['pop'].sum())}, expected 873,965")
    if not (frame["pop"] == frame["pop_geo"]).all():
        raise SystemExit("PL total population does not match the geographic header")
    return frame


def load_acs(raw_dir: Path, tables: dict[str, list[str]], prefix: str, id_name: str) -> pd.DataFrame:
    frames = []
    for table, cells in tables.items():
        path = raw_dir / f"acsdt5y2024-{table}.dat"
        header = path.read_text(encoding="utf-8", errors="replace").splitlines()[0].split("|")
        wanted = ["GEO_ID"] + [f"{table.upper()}_{cell}" for cell in cells]
        lookup = {name: index for index, name in enumerate(header)}
        indexes = []
        for name in wanted:
            if name not in lookup:
                raise SystemExit(f"{path.name} is missing {name}")
            indexes.append(lookup[name])
        rows = []
        with path.open(encoding="utf-8", errors="replace") as handle:
            next(handle)
            for line in handle:
                if not line.startswith(prefix):
                    continue
                parts = line.rstrip("\n").split("|")
                values = [parts[indexes[0]]]
                for index in indexes[1:]:
                    text = parts[index]
                    try:
                        values.append(int(text))
                    except ValueError:
                        values.append(0)
                rows.append(values)
        piece = pd.DataFrame(rows, columns=["GEO_ID"] + [f"{table}_{cell.lower()}" for cell in cells])
        # "1500000US" and "1400000US" are both 9 characters. What follows is the GEOID.
        piece[id_name] = piece["GEO_ID"].str.slice(9)
        piece = piece.drop(columns="GEO_ID")
        frames.append(piece)
    merged = frames[0]
    for piece in frames[1:]:
        merged = merged.merge(piece, on=id_name, how="outer")
    return merged


def _moe_sum(columns: pd.DataFrame) -> pd.Series:
    return columns.pow(2).sum(axis=1).pow(0.5)


def block_to_precinct(blocks: gpd.GeoDataFrame, precincts: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict]:
    blocks = blocks.to_crs(CRS)
    precincts = precincts.to_crs(CRS)[["precinct_id", "geometry"]]
    points = gpd.GeoDataFrame(
        {"geoid": blocks["geoid"].values},
        geometry=gpd.points_from_xy(blocks["INTPTLON20"].astype(float), blocks["INTPTLAT20"].astype(float)),
        crs=4269,
    ).to_crs(CRS)
    pointed = gpd.sjoin(points, precincts, how="left", predicate="within")
    pointed = pointed.drop_duplicates("geoid")
    point_precinct = pointed.set_index("geoid")["precinct_id"]

    land = blocks[blocks["ALAND20"].astype(int) > 0][["geoid", "geometry"]].copy()
    pieces = gpd.overlay(land, precincts, how="intersection", keep_geom_type=False)
    pieces["area"] = pieces.geometry.area
    pieces = pieces[pieces["area"] > 0]
    pieces["share"] = pieces["area"] / pieces.groupby("geoid")["area"].transform("sum")
    rows = []
    split_ids = []
    majority_rows = []
    for geoid, part in pieces.groupby("geoid"):
        top_index = part["share"].idxmax()
        top_share = float(part.loc[top_index, "share"])
        winner = part.loc[top_index, "precinct_id"]
        majority_rows.append({"geoid": geoid, "majority_precinct": winner, "majority_share": top_share})
        if top_share >= SPLIT_THRESHOLD:
            rows.append({"geoid": geoid, "precinct_id": winner, "share": 1.0})
        else:
            split_ids.append(geoid)
            for _, sliver in part.iterrows():
                rows.append(
                    {
                        "geoid": geoid,
                        "precinct_id": sliver["precinct_id"],
                        "share": float(sliver["share"]),
                    }
                )
    allocation = pd.DataFrame(rows)
    majority = pd.DataFrame(majority_rows)
    missing = set(blocks.loc[blocks["pop"] > 0, "geoid"]) - set(allocation["geoid"])
    for geoid in missing:
        precinct_id = point_precinct.get(geoid)
        if pd.notna(precinct_id):
            allocation = pd.concat(
                [allocation, pd.DataFrame([{"geoid": geoid, "precinct_id": precinct_id, "share": 1.0}])],
                ignore_index=True,
            )
    compared = majority.copy()
    compared["point_precinct"] = compared["geoid"].map(point_precinct)
    unsplit = compared[compared["majority_share"] >= SPLIT_THRESHOLD]
    disagree = unsplit[
        unsplit["point_precinct"].notna() & (unsplit["point_precinct"] != unsplit["majority_precinct"])
    ]
    pop = blocks.set_index("geoid")["pop"]
    split_pop = int(pop.reindex(split_ids).fillna(0).sum())
    disagree_pop = int(pop.reindex(disagree["geoid"]).fillna(0).sum())
    assigned_pop = int(
        allocation.merge(blocks[["geoid", "pop"]], on="geoid", how="left")
        .assign(allocated=lambda frame: frame["pop"] * frame["share"])["allocated"]
        .sum()
    )
    qc = {
        "blocks": int(len(blocks)),
        "blocks_split": int(len(split_ids)),
        "population_in_split_blocks": split_pop,
        "population_total": int(pop.sum()),
        "population_assigned": assigned_pop,
        "split_population_share": split_pop / int(pop.sum()) if int(pop.sum()) else None,
        "unsplit_blocks_where_internal_point_disagrees": int(len(disagree)),
        "population_where_internal_point_disagrees": disagree_pop,
    }
    return allocation, qc


def apportion(
    blocks: pd.DataFrame, allocation: pd.DataFrame, acs: pd.DataFrame, nativity: pd.DataFrame
) -> pd.DataFrame:
    weighted = blocks.copy()
    weighted["bg"] = weighted["geoid"].str[:12]
    weighted["tract"] = weighted["geoid"].str[:11]
    for weight, source, parent_key in (
        ("w_vap", "vap", "bg"),
        ("w_hu", "occupied_hu", "bg"),
        ("w_pop", "pop", "tract"),
    ):
        parent = weighted.groupby(parent_key)[source].transform("sum")
        weighted[weight] = weighted[source] / parent.where(parent > 0)
    work = weighted.merge(allocation, on="geoid", how="inner")
    acs_counts = [
        "b15003_e001",
        "b15003_e022",
        "b15003_e023",
        "b15003_e024",
        "b15003_e025",
        "b25003_e001",
        "b25003_e002",
        "b25003_e003",
        "b19001_e001",
        "b19001_e016",
        "b19001_e017",
    ]
    acs_moes = [
        "b15003_m001",
        "b15003_m022",
        "b15003_m023",
        "b15003_m024",
        "b15003_m025",
        "b25003_m001",
        "b25003_m003",
        "b19001_m001",
        "b19001_m016",
        "b19001_m017",
    ]
    nativity_counts = ["b05001_e001", "b05001_e005", "b05001_e006"]
    work = work.merge(acs[["bg"] + acs_counts + acs_moes], on="bg", how="left")
    work = work.merge(nativity[["tract"] + nativity_counts], on="tract", how="left")
    for weight, columns in (
        ("w_vap", ["b15003_e001", "b15003_e022", "b15003_e023", "b15003_e024", "b15003_e025"]),
        ("w_hu", ["b25003_e001", "b25003_e002", "b25003_e003", "b19001_e001", "b19001_e016", "b19001_e017"]),
        ("w_pop", nativity_counts),
    ):
        for column in columns:
            work[column] = work[column].fillna(0) * work[weight].fillna(0) * work["share"]

    direct = [
        "pop",
        "hispanic",
        "nh_white",
        "nh_black",
        "nh_asian",
        "nh_other",
        "vap",
        "vap_hispanic",
        "vap_nh_white",
        "vap_nh_black",
        "vap_nh_asian",
        "occupied_hu",
        "housing_units_pl",
        "gq",
    ]
    for column in direct:
        work[column] = work[column] * work["share"]

    # Parent CV of the bachelor's-or-higher count, carried from the block group
    # that contributes the most 2020 population in the precinct.
    edu_est = (
        acs["b15003_e022"] + acs["b15003_e023"] + acs["b15003_e024"] + acs["b15003_e025"]
    )
    edu_moe = _moe_sum(acs[["b15003_m022", "b15003_m023", "b15003_m024", "b15003_m025"]])
    acs = acs.copy()
    acs["ba_cv"] = (edu_moe / 1.645) / edu_est.where(edu_est > 0)
    dominant = (
        work.sort_values("pop", ascending=False)
        .groupby("precinct_id", as_index=False)
        .first()[["precinct_id", "bg"]]
    )
    dominant = dominant.merge(acs[["bg", "ba_cv"]], on="bg", how="left")

    grouped = work.groupby("precinct_id", as_index=False)[direct + acs_counts + nativity_counts].sum()
    grouped = grouped.merge(dominant[["precinct_id", "ba_cv"]], on="precinct_id", how="left")
    grouped["ba_plus"] = (
        grouped["b15003_e022"] + grouped["b15003_e023"] + grouped["b15003_e024"] + grouped["b15003_e025"]
    )
    grouped["hh_150k"] = grouped["b19001_e016"] + grouped["b19001_e017"]
    grouped["nh_asian_share"] = grouped["nh_asian"] / grouped["pop"].where(grouped["pop"] > 0)
    grouped["nh_white_share"] = grouped["nh_white"] / grouped["pop"].where(grouped["pop"] > 0)
    grouped["hispanic_share"] = grouped["hispanic"] / grouped["pop"].where(grouped["pop"] > 0)
    grouped["ba_share"] = grouped["ba_plus"] / grouped["b15003_e001"].where(grouped["b15003_e001"] > 0)
    grouped["renter_share"] = grouped["b25003_e003"] / grouped["b25003_e001"].where(grouped["b25003_e001"] > 0)
    grouped["hh_150k_share"] = grouped["hh_150k"] / grouped["b19001_e001"].where(grouped["b19001_e001"] > 0)
    grouped["foreign_born"] = grouped["b05001_e005"] + grouped["b05001_e006"]
    grouped["foreign_born_share"] = grouped["foreign_born"] / grouped["b05001_e001"].where(grouped["b05001_e001"] > 0)
    grouped["gq_share"] = grouped["gq"] / grouped["pop"].where(grouped["pop"] > 0)
    return grouped


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    _download(PL_ZIP, RAW / "ca2020.pl.zip")
    _download(BLOCK_ZIP, RAW / "tl_2020_06075_tabblock20.zip")
    for table in (*ACS_TABLES, *TRACT_TABLES):
        _download(f"{ACS_BASE}/acsdt5y2024-{table}.dat", RAW / f"acsdt5y2024-{table}.dat")

    pl = load_pl_blocks(RAW / "ca2020.pl.zip")
    acs = load_acs(RAW, ACS_TABLES, "1500000US06075", "bg")
    nativity = load_acs(RAW, TRACT_TABLES, "1400000US06075", "tract")
    blocks = gpd.read_file(RAW / "tl_2020_06075_tabblock20.zip")
    blocks = blocks.merge(pl, left_on="GEOID20", right_on="geoid", how="left")
    blocks["pop"] = blocks["pop"].fillna(0)
    precincts = gpd.read_file(OUT / "precincts.geojson")
    precincts["precinct_id"] = precincts["precinct_id"].astype(str)
    allocation, qc = block_to_precinct(blocks, precincts)
    census = apportion(blocks.drop(columns="geometry"), allocation, acs, nativity)
    census.to_csv(OUT / "census_precinct.csv", index=False)
    (OUT / "census_qc.json").write_text(json.dumps(qc, indent=2))
    print(json.dumps(qc, indent=2))
    print(
        "pop",
        round(census["pop"].sum()),
        "ba share",
        round(census["ba_plus"].sum() / census["b15003_e001"].sum(), 3),
        "renter",
        round(census["b25003_e003"].sum() / census["b25003_e001"].sum(), 3),
        "foreign born",
        round(census["foreign_born"].sum() / census["b05001_e001"].sum(), 3),
    )


if __name__ == "__main__":
    main()
