"""Assemble the sf-2026-drive folder and its zip from analysis/output.

Run after run_all.py, from the repository root:

    python analysis/build_drive.py

FINDINGS.md, the figures it shows, the notebook's source files, and the
measure screen are copied from the analysis. The Datawrapper files are
rewritten by running the folder's own notebook. The hand-written READMEs and
the notebook itself are left alone.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
REPO = ROOT.parent
DRIVE = REPO / "sf-2026-drive"
ZIP_PATH = REPO / "sf-2026-drive.zip"

SOURCE_FILES = ["precinct_results.csv", "census_precinct.csv", "precincts.geojson"]
TABLE_FILES = ["measure_screening.csv"]
# Fixed so an unchanged folder rebuilds to an identical zip.
ZIP_TIMESTAMP = (2026, 11, 8, 16, 0, 0)


def drive_findings() -> str:
    text = (ROOT / "FINDINGS.md").read_text(encoding="utf-8")
    text = text.replace("](output/figures/", "](figures/")
    for name in TABLE_FILES:
        text = text.replace(f"`output/{name}`", f"`tables/{name}`")
    return text


def referenced_paths(text: str) -> list[str]:
    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    code_paths = [p for p in re.findall(r"`([^`\s]+/[^`\s]+)`", text)]
    return images + code_paths


def run_notebook() -> None:
    notebook = json.loads((DRIVE / "notebooks" / "export_datawrapper.ipynb").read_text())
    code = "\n\n".join(
        "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"
    )
    previous = Path.cwd()
    os.chdir(DRIVE / "notebooks")
    try:
        exec(compile(code, "export_datawrapper.ipynb", "exec"), {"__name__": "__notebook__"})
    finally:
        os.chdir(previous)


def write_zip() -> None:
    files = sorted(p for p in DRIVE.rglob("*") if p.is_file())
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(str(path.relative_to(REPO)), date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def main() -> None:
    findings = drive_findings()
    (DRIVE / "FINDINGS.md").write_text(findings, encoding="utf-8")

    figures = DRIVE / "figures"
    if figures.exists():
        shutil.rmtree(figures)
    figures.mkdir()
    for image in re.findall(r"!\[[^\]]*\]\(figures/([^)]+)\)", findings):
        shutil.copy2(OUT / "figures" / image, figures / image)

    for name in SOURCE_FILES:
        shutil.copy2(OUT / name, DRIVE / "source" / name)
    (DRIVE / "tables").mkdir(exist_ok=True)
    for name in TABLE_FILES:
        shutil.copy2(OUT / name, DRIVE / "tables" / name)

    missing = [p for p in referenced_paths(findings) if not (DRIVE / p).exists()]
    if missing:
        raise SystemExit(f"FINDINGS.md in the Drive folder points to files it does not have: {missing}")

    run_notebook()
    write_zip()
    print(f"{DRIVE.relative_to(REPO)} and {ZIP_PATH.name} rebuilt")


if __name__ == "__main__":
    main()
