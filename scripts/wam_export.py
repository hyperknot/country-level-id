#!/usr/bin/env python3
import shutil

from country_levels_lib import wam_export
from country_levels_lib.config import export_dir
from country_levels_lib.fips_utils import get_population_by_state


def main():
    shutil.rmtree(export_dir / 'geojson', ignore_errors=True)

    # for simp in [5, 7, 8]:
    #     wam_export.split_geojson(1, simp, debug=False)
    #     wam_export.split_geojson(2, simp, debug=False)

    wam_export.split_geojson(2, 5, debug=False)


if __name__ == "__main__":
    main()
