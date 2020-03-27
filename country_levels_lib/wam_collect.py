import itertools
import json
import re

from country_levels_lib.config import geojson_dir
from country_levels_lib.utils import read_json, osm_url, wikidata_url, write_json
from country_levels_lib.wam_download import wam_geojson_download_dir, wam_data_dir
from country_levels_lib.wikidata_iso import get_osm_iso1_map, get_osm_wd_map, get_osm_iso2_map
from country_levels_lib.wikidata_population import get_population

collected_dir = geojson_dir / 'wam' / 'collected'
iso1_found_path = collected_dir / 'iso1.ndjson'
iso2_found_path = collected_dir / 'iso2.ndjson'

osm_iso1_map = {}
osm_iso2_map = {}
osm_wd_map = {}

iso1_regex = re.compile('[A-Z]{2}')
iso2_regex = re.compile('[A-Z]{2}-[A-Z0-9]{1,3}')


def collect_iso():
    global osm_iso1_map, osm_iso2_map, osm_wd_map

    osm_iso1_map = get_osm_iso1_map()
    osm_iso2_map = get_osm_iso2_map()
    osm_wd_map = get_osm_wd_map()

    geojson_files = (wam_geojson_download_dir).glob(
        '**/*.GeoJson'
    )  # strange capitalization inside zips

    collected_dir.mkdir(parents=True, exist_ok=True)
    iso1_found = open(iso1_found_path, 'w')
    iso2_found = open(iso2_found_path, 'w')

    geojson_files_sorted = sorted(geojson_files, key=lambda p: p.stem, reverse=False)

    wd_ids_collected = set()

    for f in itertools.islice(geojson_files_sorted, None, None):
        print(f.parent.stem, f.stem)
        try:
            features = read_json(f)['features']
        except json.decoder.JSONDecodeError as e:
            print(f'  Error reading {f.stem} {e}')
            continue
        new_wd_ids = add_iso(features, iso1_found, iso2_found)
        wd_ids_collected = wd_ids_collected.union(new_wd_ids)

    write_json(wam_data_dir / 'wd_ids_collected.json', list(wd_ids_collected))

    iso1_found.close()
    iso2_found.close()


def add_iso(features: list, found_iso1_file, found_iso2_file):
    count1 = 0
    count2 = 0

    wd_ids_collected = set()

    for feature in features:
        prop = feature['properties']
        alltags = prop['alltags']

        name = prop['name']
        osm_id = prop['id']

        iso1_from_wd = osm_iso1_map.get(osm_id)
        iso1_from_osm = alltags.get('ISO3166-1')

        iso2_from_wd = osm_iso2_map.get(osm_id)
        iso2_from_osm = alltags.get('ISO3166-2')

        wd_id_from_wd = osm_wd_map.get(osm_id)
        wd_id_from_osm = prop.get('wikidata')

        wd_id = wd_id_from_wd
        if wd_id_from_osm:
            wd_id = wd_id_from_osm

        prop['wikidata_id'] = wd_id
        prop.pop('wikidata', None)

        if wd_id_from_wd and wd_id_from_osm and wd_id_from_wd != wd_id_from_osm:
            print(
                f'  wd_id mismatch: '
                f'{name} '
                f'{osm_url(osm_id)} '
                f'{wikidata_url(wd_id_from_osm)} '
                f'{wikidata_url(wd_id_from_wd)}  '
            )

        if iso1_from_wd or iso1_from_osm:
            # if any of the sources has ISO1, use that
            # many examples in FRA, including FX which is only found in Wikidata
            iso1 = iso1_from_osm
            if iso1_from_wd != iso1_from_osm:
                if iso1_from_wd and iso1_from_osm:
                    print(
                        f'  iso1 mismatch: '
                        f'{name} '
                        f'iso1_from_osm: {iso1_from_osm}  '
                        f'iso1_from_wd: {iso1_from_wd}  '
                        f'{osm_url(osm_id)} '
                        f'{wikidata_url(wd_id_from_osm)}  '
                    )

                if iso1_from_wd:
                    iso1 = iso1_from_wd

            if not validate_iso1(iso1):
                print(
                    f'  iso1 not valid: '
                    f'{name} '
                    f'iso1_from_osm: {iso1_from_osm}  '
                    f'iso1_from_wd: {iso1_from_wd}  '
                    f'{osm_url(osm_id)}  '
                    f'{wikidata_url(wd_id_from_osm)}  '
                )
                continue
            prop['iso1'] = iso1

            geojson_str = json.dumps(feature, ensure_ascii=False, allow_nan=False)
            found_iso1_file.write(geojson_str + '\n')

            wd_ids_collected.add(wd_id)
            count1 += 1

        #
        #
        if iso2_from_wd or iso2_from_osm:

            # if any of the sources has ISO2, use that
            # many examples in FRA, including FX which is only found in Wikidata
            iso2 = iso2_from_osm
            if iso2_from_wd != iso2_from_osm:
                if iso2_from_wd and iso2_from_osm:
                    print(
                        f'  iso2 mismatch: '
                        f'{name} '
                        f'iso2_from_osm: {iso2_from_osm}  '
                        f'iso2_from_wd: {iso2_from_wd}  '
                        f'{osm_url(osm_id)}  '
                        f'{wikidata_url(wd_id_from_osm)}  '
                    )

                if iso2_from_wd:
                    iso2 = iso2_from_wd

            if not validate_iso2(iso2):
                print(
                    f'  iso2 not valid: '
                    f'{name} '
                    f'iso2_from_osm: {iso2_from_osm}  '
                    f'iso2_from_wd: {iso2_from_wd}  '
                    f'{osm_url(osm_id)}  '
                    f'{wikidata_url(wd_id_from_osm)}  '
                )
                continue
            prop['iso2'] = iso2

            geojson_str = json.dumps(feature, ensure_ascii=False, allow_nan=False)
            found_iso2_file.write(geojson_str + '\n')

            wd_ids_collected.add(wd_id)
            count2 += 1

    if count1 or count2:
        print(f'  iso1 collected: {count1}, iso2 collected: {count2}')

    return wd_ids_collected


def save_population():
    all_ids = read_json(wam_data_dir / 'wd_ids_collected.json')
    population_data = get_population(all_ids)
    write_json(wam_data_dir / 'population.json', population_data, indent=2, sort_keys=True)


def validate_iso1(iso_code: str):
    return iso1_regex.fullmatch(iso_code) is not None


def validate_iso2(iso_code: str):
    return iso2_regex.fullmatch(iso_code) is not None
