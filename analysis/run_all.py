"""Build the precinct tables, maps, census join, and the sf-2026-drive folder.

    python analysis/run_all.py
"""

from apportion_census import main as census_main
from build_drive import main as drive_main
from build_findings import main as build_main
from build_findings import write_census_charts


def main() -> None:
    build_main()
    census_main()
    write_census_charts()
    drive_main()


if __name__ == "__main__":
    main()
