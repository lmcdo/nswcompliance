#!/usr/bin/env python3
"""Test actual API call like the frontend makes"""

import requests
import json

# Real property example: 45 Norton Street, Leichhardt
# Zone: R2, Heritage: false, Precinct: None

api_url = 'http://localhost:3003/api/provisions/for-property'

params = {
    'groupBy': 'toc',
    'former_council': 'Leichhardt',
    'zone': 'R2',
    'heritage': 'false',
    # No precinct_id - not in distinctive neighbourhood
}

print('=' * 70)
print('ACTUAL API CALL TEST')
print('=' * 70)
print(f'\nEndpoint: {api_url}')
print(f'Parameters:')
for k, v in params.items():
    print(f'  {k}: {v}')

print('\n--- Making API request... ---')

try:
    response = requests.get(api_url, params=params, timeout=30)

    print(f'\nStatus Code: {response.status_code}')

    if response.status_code == 200:
        data = response.json()

        if data.get('success'):
            summary = data['data']['summary']

            print('\n' + '=' * 70)
            print('API RESPONSE SUMMARY')
            print('=' * 70)
            print(f'\nTotal provisions returned: {summary["total_provisions"]:,}')
            print(f'\nBreakdown by layer:')
            print(f'  Layer 1 (Generic):       {summary["layer_1_generic"]:,}')
            print(f'  Layer 2 (Use-specific):  {summary["layer_2_use_specific"]:,}')
            print(f'  Layer 3 (Condition):     {summary["layer_3_condition"]:,}')
            print(f'  Layer 4 (Precinct):      {summary["layer_4_precinct"]:,}')

            # Get topic breakdown
            by_topic = data['data']['by_topic']
            print(f'\n--- PROVISIONS BY TOPIC (top 15) ---')
            topic_counts = [(topic, len(provisions)) for topic, provisions in by_topic.items()]
            topic_counts.sort(key=lambda x: x[1], reverse=True)

            for topic, count in topic_counts[:15]:
                print(f'  {topic}: {count:,}')

            # Get TOC structure
            by_toc = data['data']['by_toc']
            print(f'\n--- PROVISIONS BY DCP PART (TOC structure) ---')
            toc_counts = [(part, part_data['provision_count']) for part, part_data in by_toc.items()]
            toc_counts.sort(key=lambda x: x[1], reverse=True)

            for part, count in toc_counts[:10]:
                print(f'  {part}: {count:,}')

            # Meta info
            meta = data.get('meta', {})
            print(f'\n--- API METADATA ---')
            print(f'  Response time: {meta.get("response_time_ms")}ms')
            print(f'  API version: {meta.get("api_version")}')
            print(f'  Dev type approach: {meta.get("dev_type_approach")}')

            # Check if dev_type was used
            if meta.get('dev_type_hierarchy'):
                print(f'\n  Dev type filtering: YES')
                print(f'    Selected: {meta["dev_type_hierarchy"]["selected"]}')
                print(f'    Expanded: {meta["dev_type_hierarchy"]["expanded_hierarchy"]}')
            else:
                print(f'\n  Dev type filtering: NO (not provided by frontend)')

        else:
            print(f'\nAPI returned error: {data.get("error")}')
            print(f'Details: {data.get("details")}')
    else:
        print(f'\nHTTP Error: {response.status_code}')
        print(f'Response: {response.text[:500]}')

except requests.exceptions.ConnectionError:
    print('\n[ERROR] Could not connect to API')
    print('Is the Next.js dev server running on port 3003?')
    print('Run: cd frontend-nextjs && npm run dev')

except Exception as e:
    print(f'\n[ERROR] {e}')
