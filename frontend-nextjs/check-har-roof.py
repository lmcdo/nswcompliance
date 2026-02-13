import json

with open(r'C:\Users\lawre\Downloads\verify.plotdetect.com.au.har', 'r', encoding='utf-8') as f:
    har = json.load(f)

for entry in har['log']['entries']:
    if 'for-property' in entry['request']['url']:
        response_text = entry['response']['content'].get('text', '')
        if response_text:
            data = json.loads(response_text)
            # Check by_topic heritage roof
            heritage = data.get('data', {}).get('by_topic', {}).get('heritage', {})
            roof_provs = heritage.get('roof', [])
            if roof_provs:
                print(f'Found {len(roof_provs)} Roof provisions in HAR response')
                first = roof_provs[0]
                print(f'First Roof provision:')
                print(f'  ID: {first.get("id")}')
                print(f'  pdf_page: {first.get("pdf_page")}')
                print(f'  pdf_printed_page: {first.get("pdf_printed_page")}')
                print(f'  Has pdf_printed_page field: {"pdf_printed_page" in first}')
            else:
                print('No roof provisions found')
            break
