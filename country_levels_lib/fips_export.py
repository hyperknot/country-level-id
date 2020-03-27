import shutil

from country_levels_lib.config import geojson_dir, export_dir
from country_levels_lib.fips_utils import get_state_codes, get_county_data
from country_levels_lib.utils import read_json, write_json

fips_geojson_dir = geojson_dir / 'fips'


quality_map = {
    5: '20m',
    7: '5m',
    8: '500k',
}


def export_fips():
    for quality in quality_map:
        process_fips_quality(quality)

    export_county_json()


def process_fips_quality(quality):
    assert quality in [5, 7, 8]

    print(f'Processing FIPS county GeoJSON {quality_map[quality]}')

    features = read_json(fips_geojson_dir / f'counties_{quality_map[quality]}.geojson')['features']

    counties_by_str = get_county_data()[1]

    states_by_code = get_state_codes()[0]

    geojson_export_dir = export_dir / 'geojson' / f'q{quality}' / 'fips'
    shutil.rmtree(geojson_export_dir, ignore_errors=True)

    new_features = list()
    json_data = dict()

    count = 0
    for feature in features:
        prop = feature['properties']
        full_code_str = prop['GEOID']
        state_code = int(prop['STATEFP'])
        county_code = int(prop['COUNTYFP'])

        # skip minor islands without state code found in 500k dataset
        if state_code not in states_by_code:
            continue

        county_data = counties_by_str[full_code_str]

        assert county_data['county_code'] == county_code
        assert county_data['state_code'] == state_code

        name = county_data['name']
        population = county_data['population']

        countrylevel_id = f'fips:{full_code_str}'

        for key in ['NAME', 'GEOID', 'STATEFP', 'COUNTYFP']:
            del prop[key]

        new_prop = {
            'name': name,
            'fips': full_code_str,
            'state_code': state_code,
            'county_code': county_code,
            'population': population,
            'countrylevel_id': countrylevel_id,
            'census_data': prop,
        }
        feature['properties'] = new_prop
        new_features.append(feature)

        state_code_str = full_code_str[:2]
        state_subdir = geojson_export_dir / state_code_str
        state_subdir.mkdir(parents=True, exist_ok=True)
        write_json(state_subdir / f'{full_code_str}.geojson', feature)
        count += 1

        json_data[full_code_str] = {k: v for k, v in new_prop.items() if k != 'census_data'}
        json_data[full_code_str]['geojson_path'] = f'fips/{state_code_str}/{full_code_str}.geojson'

    write_json(
        export_dir / 'geojson' / f'q{quality}' / 'fips_all.geojson',
        {"type": "FeatureCollection", "features": new_features},
    )

    if quality == 5:  # only write the file once
        write_json(export_dir / f'fips.json', json_data, indent=2, sort_keys=True)

    assert count == len(counties_by_str)
    print(f'  {count} GeoJSON processed')


def export_county_json():
    counties_by_str = get_county_data()[0]
    fips_subdir = export_dir / 'fips'
    fips_subdir.mkdir(parents=True, exist_ok=True)
    write_json(fips_subdir / 'counties_population.json', counties_by_str, indent=2, sort_keys=True)
