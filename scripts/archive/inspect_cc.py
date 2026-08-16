import json

data = json.load(open(r'C:/Users/lawre/AppData/Local/Temp/cc_results.json'))
print('Total:', data['TotalCount'])
a = data['Application'][0]
print('Keys:', list(a.keys()))
loc = a.get('Location', [{}])[0]
print('Address:', loc.get('FullAddress'))
print('X:', loc.get('X'), 'Y:', loc.get('Y'))
print('Lodged:', a.get('LodgementDate'))
print('Determined:', a.get('DeterminationDate'))
print('Builder:', a.get('BuilderLegalName'))
print('RelatedApplications:', a.get('RelatedApplications'))
print('DevelopmentType:', a.get('DevelopmentType'))
