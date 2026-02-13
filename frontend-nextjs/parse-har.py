import json

with open(r'C:\Users\lawre\Downloads\verify.plotdetect.com.au.har', 'r', encoding='utf-8') as f:
    har = json.load(f)

for entry in har['log']['entries']:
    if 'for-property' in entry['request']['url']:
        response_text = entry['response']['content'].get('text', '')
        if response_text and '78649' in response_text:
            data = json.loads(response_text)
            # Search in by_topic heritage provisions
            heritage = data.get('data', {}).get('by_topic', {}).get('heritage', {})
            for topic, provisions in heritage.items():
                for prov in provisions:
                    if prov.get('id') == 78649:
                        print(f'Found ID 78649 in topic "{topic}":')
                        print(f'  pdf_page: {prov.get("pdf_page")}')
                        print(f'  pdf_printed_page: {prov.get("pdf_printed_page")}')
                        break
