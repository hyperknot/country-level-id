from country_levels_lib.config import (
    id_dir,
    geojson_dir,
    ne3_dir,
    export_geojson_dir,
)
from country_levels_lib.utils import read_json, write_json

simp_map = {
    5: 'small',
    7: 'medium',
    8: 'high',
    0: 'full',
}


def export_ne0(simp: int):
    levels = read_json(id_dir / 'ne012.json')
    simp_str = f'-{simp}' if simp else ''
    countries = read_json(geojson_dir / f'countries{simp_str}.geojson')['features']

    features_by_id = {}

    for feature in countries:
        prop = feature['properties']
        for key in prop:
            prop[key.lower()] = prop.pop(key)
        ne_id = prop['ne_id']
        features_by_id[ne_id] = feature

    for ne0, ne0_data in levels.items():
        ne_id = ne0_data['ne_id']
        feature_data = features_by_id[ne_id]
        fix_props(feature_data, ne0_data, ne0)

        filename = ne0[4:].lower()
        export_subdir = export_geojson_dir / f'{simp_map[simp]}' / 'ne0'
        export_path = export_subdir / f'{filename}.geojson'

        export_subdir.mkdir(exist_ok=True, parents=True)
        write_json(export_path, feature_data)

    print(f'{len(countries)} ne0 GeoJSONs exported, simplification: {simp}')


def export_ne1(simp: int):
    levels = read_json(id_dir / 'ne012.json')
    simp_str = f'-{simp}' if simp else ''
    units = read_json(geojson_dir / f'units{simp_str}.geojson')['features']

    features_by_id = {}

    for feature in units:
        prop = feature['properties']
        for key in prop:
            prop[key.lower()] = prop.pop(key)
        ne_id = prop['ne_id']
        features_by_id[ne_id] = feature

    counter = 0
    for ne0, ne0_data in levels.items():
        if 'sub1' not in ne0_data:
            continue

        sub1 = ne0_data['sub1']
        for ne1, ne1_data in sub1.items():
            ne_id = ne1_data['ne_id']
            feature_data = features_by_id[ne_id]
            fix_props(feature_data, ne1_data, ne1)

            # skip one-to-one fixed polygons
            if ne1[:3] == 'ne0':
                continue

            filename = ne1[4:].lower()
            export_subdir = export_geojson_dir / f'{simp_map[simp]}' / 'ne1'
            export_path = export_subdir / f'{filename}.geojson'

            export_subdir.mkdir(exist_ok=True, parents=True)
            write_json(export_path, feature_data)

            counter += 1

    print(f'{counter} ne1 GeoJSONs exported, simplification: {simp}')


def export_ne2(simp: int):
    levels = read_json(id_dir / 'ne012.json')
    simp_str = f'-{simp}' if simp else ''
    subunits = read_json(geojson_dir / f'subunits{simp_str}.geojson')['features']

    features_by_id = {}

    for feature in subunits:
        prop = feature['properties']
        for key in prop:
            prop[key.lower()] = prop.pop(key)
        ne_id = prop['ne_id']
        features_by_id[ne_id] = feature

    counter = 0
    for ne0, ne0_data in levels.items():
        if 'sub1' not in ne0_data:
            continue

        sub1 = ne0_data['sub1']
        for ne1, ne1_data in sub1.items():
            if 'sub2' not in ne1_data:
                continue

            sub2 = ne1_data['sub2']
            for ne2, ne2_data in sub2.items():
                ne_id = ne2_data['ne_id']
                feature_data = features_by_id[ne_id]
                fix_props(feature_data, ne2_data, ne2)

                filename = ne2[4:].lower()
                export_subdir = export_geojson_dir / f'{simp_map[simp]}' / 'ne2'
                export_path = export_subdir / f'{filename}.geojson'

                export_subdir.mkdir(exist_ok=True, parents=True)
                write_json(export_path, feature_data)

                counter += 1

    print(f'{counter} ne2 GeoJSONs exported, simplification: {simp}')


def export_ne3(simp: int):
    simp_str = f'-{simp}' if simp else ''
    states = read_json(geojson_dir / f'states{simp_str}.geojson')['features']

    features_by_id = {}

    for feature in states:
        prop = feature['properties']
        for key in prop:
            prop[key.lower()] = prop.pop(key)
        ne_id = prop['ne_id']
        features_by_id[ne_id] = feature

    country_jsons = ne3_dir.glob('*.json')
    for country_json in country_jsons:
        country_code = country_json.stem
        country_level_3 = read_json(country_json)

        for ne3, ne3_data in country_level_3.items():
            ne_id = ne3_data['ne_id']
            feature_data = features_by_id[ne_id]
            fix_props(feature_data, ne3_data, ne3)

            ne3_start, ne3_end = ne3.split(':')[1].split('-')
            assert ne3_start.lower() == country_code

            export_subdir = export_geojson_dir / f'{simp_map[simp]}' / 'ne3' / country_code
            export_path = export_subdir / f'{ne3_end.lower()}.geojson'

            export_subdir.mkdir(exist_ok=True, parents=True)
            write_json(export_path, feature_data)

    print(f'{len(states)} ne3 GeoJSONs exported, simplification: {simp}')


def fix_props(feature_data: dict, id_data: dict, cl_id: str):
    """
    Fix wrong Natural Earth data in GeoJSONs by substituting them from fixed datasets
    """
    prop = feature_data['properties']
    prop.pop('pop_est', None)
    prop.pop('pop_year', None)
    prop.pop('wikidataid', None)

    prop['population'] = id_data['population']
    prop['wikidata_id'] = id_data['wikidata_id']

    # add country level id as cl_ids
    prop['cl_id'] = cl_id
