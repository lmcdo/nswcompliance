#!/usr/bin/env python3
"""Look up correct EPI IDs from the NSW Planning Portal API for each LGA."""
import requests
import re

test_addresses = {
    'Woollahra': '10 Ocean St Woollahra',
    'Campbelltown': '10 Queen St Campbelltown',
    'Georges River': '10 Forest Rd Hurstville',
    'Sutherland Shire': '10 Flora St Sutherland',
    'The Hills Shire': '10 Showground Rd Castle Hill',
    'Canada Bay': '10 Great North Rd Five Dock',
    'Fairfield': '10 Smart St Fairfield',
    'Ku-Ring-Gai': '10 Eastern Rd Turramurra',
    'Hornsby': '10 Edgeworth David Ave Hornsby',
    'Parramatta': '10 Church St Parramatta',
    'Randwick': '10 Avoca St Randwick',
    'Strathfield': '10 Albert Rd Strathfield',
    'Camden': '10 John St Camden',
    'Ryde': '10 Blaxland Rd Ryde',
    'Waverley': '10 Bondi Rd Bondi',
    'Sydney': '10 George St Sydney',
    # Also check the ones that returned 200 to confirm IDs
    'Blacktown': '10 Main St Blacktown',
    'Canterbury-Bankstown': '10 Canterbury Rd Canterbury',
    'Cumberland': '10 Church St Lidcombe',
    'Liverpool': '10 Macquarie St Liverpool',
    'Northern Beaches': '10 Pittwater Rd Manly',
    'Penrith': '10 Henry St Penrith',
    'Burwood': '10 Burwood Rd Burwood',
}

import time

for lga, addr in test_addresses.items():
    try:
        addr_enc = addr.replace(' ', '%20')
        r = requests.get(
            f'https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address?a={addr_enc}',
            timeout=10
        )
        results = r.json()
        if not results:
            print(f'{lga}: no address match')
            continue
        if isinstance(results, str):
            print(f'{lga}: API returned string (rate limited?): {results[:100]}')
            time.sleep(3)
            continue
        prop_id = results[0].get('propId') or results[0].get('id')
        time.sleep(1)
        r2 = requests.get(
            f'https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id={prop_id}&layers=epi',
            timeout=15
        )
        data = r2.json()
        if isinstance(data, str):
            print(f'{lga}: layerintersect returned string: {data[:100]}')
            time.sleep(3)
            continue
        for layer in data:
            if layer.get('layerName') == 'Land Zoning Map' and layer.get('results'):
                result = layer['results'][0]
                leg_url = result.get('legislationUrl', '')
                epi_name = result.get('EPI Name', '')
                m = re.search(r'(epi-\d{4}-\d{4})', leg_url)
                epi_id = m.group(1) if m else 'NOT FOUND'
                print(f'{lga}: {epi_id}  |  {epi_name}  |  {leg_url}')
                break
        time.sleep(2)
    except Exception as e:
        print(f'{lga}: ERROR {e}')
        time.sleep(3)
