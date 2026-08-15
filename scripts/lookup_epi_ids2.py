#!/usr/bin/env python3
"""Look up remaining EPI IDs."""
import requests, re, time

addresses = {
    'Woollahra': '100 Queen St Woollahra',
    'Campbelltown': '100 Queen St Campbelltown',
    'Ryde': '100 Blaxland Rd Ryde',
    'Waverley': '100 Bondi Rd Bondi',
    'Sydney': '100 George St Sydney',
}

for lga, addr in addresses.items():
    try:
        time.sleep(3)
        addr_enc = addr.replace(' ', '%20')
        r = requests.get(
            f'https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address?a={addr_enc}',
            timeout=10
        )
        results = r.json()
        if isinstance(results, str):
            print(f'{lga}: rate limited: {results[:80]}')
            continue
        if not results:
            print(f'{lga}: no match')
            continue
        prop_id = results[0].get('propId') or results[0].get('id')
        time.sleep(2)
        r2 = requests.get(
            f'https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id={prop_id}&layers=epi',
            timeout=15
        )
        data = r2.json()
        if isinstance(data, str):
            print(f'{lga}: layerintersect rate limited: {data[:80]}')
            continue
        for layer in data:
            if layer.get('layerName') == 'Land Zoning Map' and layer.get('results'):
                result = layer['results'][0]
                leg_url = result.get('legislationUrl', '')
                epi_name = result.get('EPI Name', '')
                m = re.search(r'(epi-\d{4}-\d{4})', leg_url)
                if not m:
                    # Try old format EPI/YYYY/NNN
                    m2 = re.search(r'EPI/(\d{4})/(\d+)', leg_url)
                    if m2:
                        epi_id = f'epi-{m2.group(1)}-{int(m2.group(2)):04d}'
                    else:
                        epi_id = 'NOT FOUND'
                else:
                    epi_id = m.group(1)
                print(f'{lga}: {epi_id}  |  {epi_name}  |  {leg_url}')
                break
    except Exception as e:
        print(f'{lga}: ERROR {e}')
