import re

from country_levels_lib.config import geojson_dir, ne3_dir, wikidata_dir
from country_levels_lib.ne012 import create_adm_iso_map, validate_iso_012
from country_levels_lib.utils import read_json, write_json

fix_iso_3_codes = {
    'UA-43': 'RU-43',
    'UA-40': 'RU-40',
    'NL-SX': 'SX-01',
    'US-PR': 'PR-01',
    'TK-X01~': 'NZ-TK',
    'AU-X04~': 'ATC-01',
}
iso_3_regex = re.compile('[A-Z]{2,3}-[A-Z0-9]{1,3}')


def process_ne3():
    countries = read_json(geojson_dir / 'countries.geojson')['features']
    states = read_json(geojson_dir / 'states.geojson')['features']
    print(f'{len(states)} states')

    adm_iso_map = create_adm_iso_map(countries)
    processed_states = build_states(states, adm_iso_map)
    clean_duplicate_states(processed_states)

    ne3_data = dict()

    for feature in processed_states:
        prop = feature['properties']['_clean']
        state_iso = prop['state_iso']
        state_name = prop['state_name']
        country_iso = prop['country_iso']
        country_name = prop['country_name']
        ne_id = prop['ne_id']
        population = prop['population']
        wikidata_id = prop['wikidata_id']

        ne3_data.setdefault(country_iso, {})

        ne3 = f'ne3:{state_iso}'
        print(f'{country_name}; {state_name}; {ne3}')
        ne3_data[country_iso][ne3] = {
            'name': state_name,
            'ne_id': ne_id,
            'wikidata_id': wikidata_id,
            'population': population,
        }

    for country_iso, country_states in ne3_data.items():
        ne3_dir.mkdir(exist_ok=True, parents=True)
        filename = f'{country_iso.lower()}.json'
        write_json(ne3_dir / filename, country_states, indent=2, sort_keys=True)
        # print(f'{filename} written')


def validate_iso_3(iso_code: str):
    if iso_3_regex.fullmatch(iso_code) is None:
        print(f'wrong level 3 code: {iso_code}')


def build_states(states: list, adm_iso_map: dict):
    wikidata_population = read_json(wikidata_dir / 'population.json')
    wikidata_iso_ne3 = read_json(wikidata_dir / 'iso_ne3.json')

    clean_states = list()

    for feature in states:
        prop = feature['properties']
        for key in prop:
            prop[key.lower()] = prop.pop(key)

        country_name = prop['admin']
        country_iso = adm_iso_map[prop['adm0_a3']]
        validate_iso_012(country_iso)

        state_name = prop['name']
        state_iso = fix_iso_3_codes.get(prop['iso_3166_2'], prop['iso_3166_2'])

        wikidata_id = prop.get('wikidataid')
        wikidata_url = f'https://www.wikidata.org/wiki/{wikidata_id}'
        population = wikidata_population.get(wikidata_id, 0)
        wikidata_iso = wikidata_iso_ne3.get(wikidata_id)

        if wikidata_iso is not None and wikidata_iso != state_iso:
            state_iso = wikidata_iso

        ne_id = prop['ne_id']
        assert type(ne_id) == int

        # skipping minor island
        if prop['featurecla'] == 'Admin-1 minor island':
            continue

        # skipping unnamed places (right now the same as minor islands)
        if state_name is None:
            continue

        if state_iso.startswith('-99-'):
            continue

        # check if state's iso code matches country's iso code
        country_iso_from_state, country_code_from_state = state_iso.split('-')
        if country_iso_from_state != country_iso:
            # print(
            #     f'ci: {country_iso} si:{state_iso} cn:{country_name} sn: {state_name} {wikidata_url}'
            # )
            # country_iso = country_iso_from_state
            state_iso = f'{country_iso}-{country_code_from_state}'

        # clean up state_iso
        state_iso = state_iso.replace('~', '')

        # regex check state_iso
        validate_iso_3(state_iso)

        prop['_clean'] = {
            'country_name': country_name,
            'country_iso': country_iso,
            'state_name': state_name,
            'state_iso': state_iso,
            'ne_id': ne_id,
            'population': population,
            'wikidata_id': wikidata_id,
        }

        clean_states.append(feature)

    return clean_states


def clean_duplicate_states(processed_states: list):
    iso_map = dict()

    # build a dictionary from ne_id: population values
    for state in processed_states:
        prop = state['properties']['_clean']
        state_iso = prop['state_iso']
        ne_id = prop['ne_id']

        iso_map.setdefault(state_iso, {})
        iso_map[state_iso][ne_id] = prop['population']

    # rename those states which found multiple times in the iso_map
    for state in processed_states:
        prop = state['properties']['_clean']
        state_iso = prop['state_iso']

        ne_id = prop['ne_id']

        if state_iso not in iso_map:
            continue

        if len(iso_map[state_iso]) == 1:
            continue

        duplicate_states = iso_map[state_iso]
        sorted_by_population = {
            k: v
            for k, v in sorted(duplicate_states.items(), key=lambda item: item[1], reverse=True)
        }

        # if 1st and 2nd has the same population, rename both
        sorted_by_population_values = list(sorted_by_population.values())
        if sorted_by_population_values[0] == sorted_by_population_values[1]:
            prop['state_iso'] = f'{state_iso}_{ne_id}'

        most_popular_ne_id = list(sorted_by_population.keys())[0]

        # leave the most popular ne_id in the short form
        if ne_id == most_popular_ne_id:
            continue

        prop['state_iso'] = f'{state_iso}_{ne_id}'

    # double check duplicate iso-s
    seen_iso = set()
    for state in processed_states:
        prop = state['properties']['_clean']
        state_iso = prop['state_iso']
        if state_iso in seen_iso:
            print(f'duplicate ISO: {state_iso}')
        seen_iso.add(state_iso)
