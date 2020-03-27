import re
from pprint import pprint

from country_levels_lib.config import geojson_dir, id_dir, wikidata_dir
from country_levels_lib.utils import read_json, write_json


fix_iso_0_codes = {'FRA': 'FR', 'NOR': 'NO'}
iso_012_regex = re.compile('[A-Z]{2,3}')


def process_ne012():
    countries = read_json(geojson_dir / 'countries.geojson')['features']
    print(f'{len(countries)} countries')

    units = read_json(geojson_dir / 'units.geojson')['features']
    print(f'{len(units)} units')

    subunits = read_json(geojson_dir / 'subunits.geojson')['features']
    print(f'{len(subunits)} subunits')

    wikidata_population = read_json(wikidata_dir / 'population.json')

    adm_iso_map = create_adm_iso_map(countries)
    levels = dict()

    for feature in countries:
        prop = feature['properties']
        for key in prop:
            prop[key.lower()] = prop.pop(key)

        country_name = prop['admin']
        country_iso = adm_iso_map[prop['adm0_a3']]
        validate_iso_012(country_iso)

        ne_id = prop['ne_id']
        assert type(ne_id) == int

        wikidata_id = prop.get('wikidataid')
        population = calculate_population(prop, wikidata_population)

        ne0 = f'ne0:{country_iso}'

        levels.setdefault(
            ne0,
            {
                'name': country_name,
                'ne_id': ne_id,
                'wikidata_id': wikidata_id,
                'population': population,
                'sub1': {},
            },
        )

    for feature in units:
        prop = feature['properties']
        for key in prop:
            prop[key.lower()] = prop.pop(key)

        country_iso = adm_iso_map[prop['adm0_a3']]
        validate_iso_012(country_iso)

        unit_name = prop['geounit']
        unit_iso = prop['gu_a3']
        validate_iso_012(unit_iso)

        ne_id = prop['ne_id']
        assert type(ne_id) == int

        wikidata_id = prop.get('wikidataid')
        population = calculate_population(prop, wikidata_population)

        ne0 = f'ne0:{country_iso}'
        ne1 = f'ne1:{unit_iso}'

        sub1 = levels[ne0]['sub1']
        sub1.setdefault(
            ne1,
            {
                'name': unit_name,
                'ne_id': ne_id,
                'wikidata_id': wikidata_id,
                'population': population,
                'sub2': {},
            },
        )

    for feature in subunits:
        prop = feature['properties']
        for key in prop:
            prop[key.lower()] = prop.pop(key)

        country_iso = adm_iso_map[prop['adm0_a3']]
        validate_iso_012(country_iso)

        unit_iso = prop['gu_a3']
        validate_iso_012(unit_iso)

        subunit_name = prop['subunit']
        subunit_iso = prop['su_a3']
        validate_iso_012(subunit_iso)

        ne_id = prop['ne_id']
        assert type(ne_id) == int

        wikidata_id = prop.get('wikidataid')
        population = calculate_population(prop, wikidata_population)

        ne0 = f'ne0:{country_iso}'
        ne1 = f'ne1:{unit_iso}'
        ne2 = f'ne2:{subunit_iso}'

        sub1 = levels[ne0]['sub1']
        sub2 = sub1[ne1]['sub2']
        sub2.setdefault(
            ne2,
            {
                'name': subunit_name,
                'ne_id': ne_id,
                'wikidata_id': wikidata_id,
                'population': population,
            },
        )

    cleanup_sub2(levels)
    cleanup_sub1(levels)
    one_to_one_fix(levels)

    id_dir.mkdir(exist_ok=True, parents=True)
    write_json(id_dir / 'ne012.json', levels, indent=2, sort_keys=True)


def create_adm_iso_map(countries: list):
    """
    maps adm0_a3 values to iso_a2 where possible
    """
    adm_iso_map = {}
    for feature in countries:
        prop = feature['properties']
        for key in prop:
            prop[key.lower()] = prop.pop(key)

        # country_name = prop['admin']
        iso = prop['iso_a2']
        if iso == '-99':
            # print(country_name, prop['iso_a2'], prop['adm0_a3'])
            iso = prop['adm0_a3']

        adm = prop['adm0_a3']
        if adm in adm_iso_map:
            raise ValueError(f'adm exists: {adm}')
        adm_iso_map[adm] = iso

    # manual fixing
    adm_iso_map = dict(adm_iso_map, **fix_iso_0_codes)

    return adm_iso_map


def validate_iso_012(iso_code: str):
    if iso_012_regex.fullmatch(iso_code) is None:
        print(f'wrong level 1 code: {iso_code}')


def cleanup_sub2(levels: dict):
    for sub_country, country_data in levels.items():
        for data1 in country_data['sub1'].values():
            if len(data1['sub2']) == 1:
                del data1['sub2']


def cleanup_sub1(levels: dict):
    for sub_country, country_data in levels.items():
        sub1 = country_data['sub1']

        if len(sub1) != 1:
            continue

        # we know there is only one element in the dict now
        sub1_first = list(sub1.values())[0]
        if 'sub2' not in sub1_first:
            del country_data['sub1']


def one_to_one_fix(levels: dict):
    """
    Cleans up the levels dict so that id* <> ne_id codes are uniqe and can be mapped one-to-one
    This is needed because many ne1-s are duplicates of ne0 polygons.
    """

    ne_id_map = dict()
    ne_name_map = dict()

    for ne0, ne0_data in levels.items():
        ne_id = ne0_data['ne_id']

        ne_id_map[ne_id] = ne0
        ne_name_map[ne_id] = ne0_data['name']

        if 'sub1' not in ne0_data:
            continue
        sub1 = ne0_data['sub1']

        for ne1 in list(sub1.keys()):
            ne1_data = sub1[ne1]
            ne_id = ne1_data['ne_id']

            if ne_id in ne_id_map and len(sub1) == 1:
                if ne1_data['name'] != ne_name_map[ne_id]:
                    print(f'Differing name ne0 <> ne1 {ne1_data["name"]} {ne_name_map[ne_id]}')
                sub1[ne_id_map[ne_id]] = sub1.pop(ne1)
            else:
                ne_id_map[ne_id] = ne1
                ne_name_map[ne_id] = ne1_data['name']


def calculate_population(prop, wikidata_population):
    wikidata_id = prop.get('wikidataid')
    wikidata_url = f'https://www.wikidata.org/wiki/{wikidata_id}'

    population_prop = prop.get('pop_est')
    population_wiki = wikidata_population.get(wikidata_id)

    if population_prop and not population_wiki:
        return population_prop

    if population_wiki and not population_prop:
        return population_wiki

    if not population_prop and not population_wiki:
        return 0

    ratio = population_prop / population_wiki

    # if ratio is reasonable, use that (I manually checked most)
    if ratio < 4:
        return population_wiki
    else:
        # print(
        #     f'{prop["admin"]} {prop["name"]} {prop["ne_id"]} {population_prop} {population_wiki} {ratio:.1f} {wikidata_url}'
        # )
        return population_prop
