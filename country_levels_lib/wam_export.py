import shutil

from country_levels_lib.config import geojson_dir, export_dir
from country_levels_lib.utils import read_json, osm_url, write_json
from country_levels_lib.wam_download import wam_data_dir
from country_levels_lib.wam_collect import validate_iso1, validate_iso2

wam_geojson_simp_dir = geojson_dir / 'wam' / 'simp'


def export_wam():
    shutil.rmtree(export_dir / 'geojson', ignore_errors=True)

    for simp in [5, 7, 8]:
        split_geojson(1, simp, debug=False)
        split_geojson(2, simp, debug=False)


def split_geojson(iso_level: int, simp_level, *, debug: bool = False):
    assert iso_level in [1, 2]

    print(f'Splitting iso{iso_level} to level: q{simp_level}')
    file_path = wam_geojson_simp_dir / f'iso{iso_level}-{simp_level}.geojson'

    features = read_json(file_path)['features']
    features_sorted = sorted(features, key=lambda i: i['properties']['admin_level'])

    level_subdir = export_dir / 'geojson' / f'q{simp_level}' / f'iso{iso_level}'
    level_subdir.mkdir(parents=True)

    population_map = read_json(wam_data_dir / 'population.json')

    json_data = dict()
    seen = dict()

    for feature in features_sorted:
        prop = feature['properties']
        alltags = prop['alltags']

        name = prop.pop('name')
        osm_id = int(prop.pop('id'))
        iso = prop.pop(f'iso{iso_level}')
        admin_level = int(prop.pop('admin_level'))
        wikidata_id = prop.pop('wikidata_id', None)
        countrylevel_id = f'iso{iso_level}:{iso}'
        population = population_map.get(wikidata_id)

        wikipedia_from_prop = prop.pop('wikipedia', None)
        wikipedia_from_alltags = alltags.pop('wikipedia', None)
        if (
            wikipedia_from_prop
            and wikipedia_from_alltags
            and wikipedia_from_prop != wikipedia_from_alltags
        ):
            print(wikipedia_from_prop, wikipedia_from_alltags)
        wikipedia_id = wikipedia_from_alltags
        if wikipedia_from_prop:
            wikipedia_id = wikipedia_from_prop

        del feature['bbox']

        for key in ['boundary', 'note', 'rpath', 'srid', 'timestamp']:
            prop.pop(key, None)

        for key in [
            'ISO3166-1',
            'ISO3166-1:alpha2',
            'ISO3166-1:numeric',
            'ISO3166-2',
            'ISO3166-2:alpha2',
            'ISO3166-2:numeric',
            'land_area',
            'wikidata',
        ]:
            alltags.pop(key, None)

        seen.setdefault(iso, list())
        if seen[iso] and not debug:
            # print(f'  duplicate {iso}, skipping')
            continue

        new_prop = {
            'name': name,
            f'iso{iso_level}': iso,
            'admin_level': admin_level,
            'osm_id': osm_id,
            'wikidata_id': wikidata_id,
            'wikipedia_id': wikipedia_id,
            'population': population,
            'countrylevel_id': countrylevel_id,
            'osm_data': prop,
        }
        new_prop_without_osm_data = {k: v for k, v in new_prop.items() if k != 'osm_data'}
        feature['properties'] = new_prop

        seen[iso].append(new_prop_without_osm_data)
        json_data[iso] = new_prop_without_osm_data

        if iso_level == 1:
            if not validate_iso1(iso):
                print(f'invalid iso1: {iso}')
                continue

            write_json(level_subdir / f'{iso}.geojson', feature)
            json_data[iso]['geojson_path'] = f'iso1/{iso}.geojson'

        else:
            if not validate_iso2(iso):
                print(f'invalid iso2: {iso}')
                continue

            iso2_start, iso2_end = iso.split('-')

            iso2_subdir = level_subdir / iso2_start
            iso2_subdir.mkdir(exist_ok=True)

            write_json(level_subdir / iso2_start / f'{iso}.geojson', feature)
            json_data[iso]['geojson_path'] = f'iso2/{iso2_start}/{iso}.geojson'

    if simp_level == 5:
        write_json(export_dir / f'iso{iso_level}.json', json_data, indent=2, sort_keys=True)

    #
    #
    if debug:  # debug duplicates, fixed by sorting by admin_level
        debug_dir = geojson_dir / 'wam' / 'debug' / f'iso{iso_level}'
        shutil.rmtree(debug_dir, ignore_errors=True)
        debug_dir.mkdir(parents=True)

        # choose lowest admin level from available ones
        for iso, iso_matches in seen.items():
            if len(iso_matches) != 1:
                matches_sorted = sorted(iso_matches, key=lambda i: i['admin_level'])

                print(f'duplicate iso{iso_level}: {iso}')
                for match in matches_sorted:
                    name = match['name']
                    osm_id = match['osm_id']
                    url = osm_url(osm_id)
                    admin_level = match['admin_level']
                    print(f'  {name} {admin_level} {url}')

                    # file_path = debug_dir / f'{iso} {admin_level} {osm_id}.geojson'
                    # write_json(file_path, match)
