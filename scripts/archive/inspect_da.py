import json
data = json.load(open(r'C:/Users/lawre/AppData/Local/Temp/da_sample.json'))
for a in data['Application']:
    print('Keys:', list(a.keys()))
    print('DevType:', a.get('DevelopmentType'))
    print('Description:', a.get('Description'))
    print('Proposal:', a.get('Proposal'))
    print()
    break
