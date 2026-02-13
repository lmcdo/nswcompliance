import json

with open(r'C:\Users\lawre\Downloads\verify.plotdetect.com.au.har', 'r', encoding='utf-8') as f:
    har = json.load(f)

for entry in har['log']['entries']:
    if 'for-property' in entry['request']['url']:
        response_text = entry['response']['content'].get('text', '')
        if response_text:
            data = json.loads(response_text)
            heritage = data.get('data', {}).get('by_topic', {}).get('heritage', {})
            print('Heritage topics in HAR response:')
            for topic, provs in heritage.items():
                print(f'  {topic}: {len(provs)} provisions')
                if provs and topic.lower() == 'roof':
                    print(f'    First: ID {provs[0].get("id")}')
            break
