# API Keys and Endpoints Reference

## Current Environment Variables (.env.local)
```
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIzaSyCi5UBAg6X-k6W8v1vv9XEQaML9aQE-w60
OPENAI_API_KEY=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
DEEPSEEK_API_KEY=sk-ec1634592f8a432bb51382a674aa69e7
GEMINI_API_KEY=AIzaSyA2oczqAd3-X2sKlRQ2P-UM-xf_Z0gyfgU
```

## NSW Government Planning APIs (Public - No Auth Required)

### Working Test Endpoints:
```
# Address Lookup
https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address?a=5%20Carlyle%20St%2C%20Wollstonecraft%20NSW%202065%2C%20Australia&noOfRecords=1

# Property Details
https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/lot?propId=775534

# Planning Controls (Critical for our system)
https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id=775534&layers=epi
```

### Test Response Sample (Confirmed Working):
```json
{
    "layerName": "Height of Buildings Map",
    "results": [{
        "Maximum Building Height": "8.5",
        "Units": "m", 
        "Legislative Clause": "Clause 4.3",
        "EPI Name": "North Sydney Local Environmental Plan 2013",
        "LGA Name": "NORTH SYDNEY"
    }]
}
```

## Integration Status:
- ❌ NSW Planning APIs not yet integrated into our system
- ✅ APIs are publicly accessible (no auth required)
- ✅ APIs return exact data we need (height limits, zoning, LEP names)
- 🎯 Ready for integration to solve location-aware filtering

## Next Steps:
1. Test NSW APIs with Ashfield address to confirm data availability
2. Integrate address → propId → planning controls lookup
3. Filter our knowledge base queries by returned LEP/DCP names and zones
4. Replace generic document dumps with precise property-specific answers