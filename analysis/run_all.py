"""Build the precinct tables, maps, and census join.

    python analysis/run_all.py
"""

from apportion_census import main as census_main
from build_findings import main as build_main
from build_findings import write_census_charts


def main() -> None:
    build_main()
    census_main()
    write_census_charts()


if __name__ == "__main__":
    main()
