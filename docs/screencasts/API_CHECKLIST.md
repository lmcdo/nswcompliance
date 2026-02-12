# Screencast API Testing Checklist

## MANDATORY: Test ALL endpoints for each screencast address

### Core Property & Planning Data
- [ ] `/api/property` - Planning Portal data (zone, FSR, height, BASIX, heritage, former council)
- [ ] `/api/provisions/for-property` - DCP provisions filtered by zone/council/heritage

### CDC Pathway
- [ ] `/api/cdc/preliminary-check` - CDC eligibility with blockers
- [ ] `/api/cdc/compliance-check` - Detailed CDC compliance
- [ ] `/api/cdc/setback-check` - CDC setback requirements

### SEPP Requirements
- [ ] `/api/sepp/structured-requirements` - SEPP structured requirements (POST)
- [ ] `/api/housing-sepp/eligibility` - Housing SEPP eligibility
- [ ] `/api/sepp/full-text` - SEPP full text provisions

### LEP Controls
- [ ] `/api/lep/provisions` - LEP provisions for zone/council
- [ ] `/api/lep/full-text` - LEP full text

### Heritage
- [ ] `/api/heritage/hca-check` - Heritage Conservation Area check
- [ ] Heritage provisions in `/api/provisions/for-property?heritage=true&hca=...`

### ADG (Apartment Design Guide)
- [ ] `/api/adg/requirements` - ADG requirements if applicable
- [ ] `/api/adg/summary` - ADG summary
- [ ] `/api/setbacks/adg` - ADG setback requirements

### TOD (Transit Oriented Development)
- [ ] `/api/tod/transport-autocomplete` - Nearby transport infrastructure
- [ ] `/api/tod/parking-rates` - TOD parking rate variations
- [ ] `/api/tod/parking-calculator` - TOD parking calculations

### Precinct Controls
- [ ] `/api/precinct/match` - Precinct identification
- [ ] `/api/precinct/provisions` - Precinct-specific provisions
- [ ] `/api/compliance/precinct-requirements` - Precinct requirements

### Environmental Controls
- [ ] `/api/environmental/anef` - Aircraft noise (ANEF) data if applicable

### Additional Checks
- [ ] `/api/permissibility/check` - Land use permissibility
- [ ] `/api/compliance/constraints` - All planning constraints summary

## Testing Process

1. **List endpoints** - Identify which endpoints are relevant for the address/use case
2. **Test each endpoint** - Execute API call, capture response
3. **Document results** - Record provision counts, key data, any errors
4. **Include in screencast** - Update "Production Checklist" section with ALL tested endpoints
5. **Verify data accuracy** - Cross-check API responses with what's shown in screencast

## Example: Certifier Screencast (Heritage Property)

Address: 10 Railway Parade, Summer Hill NSW 2130

✅ `/api/property` - Zone R2, Heritage HCA, FSR 0.5:1, 531 sqm
✅ `/api/provisions/for-property?heritage=true` - 707 provisions (306 heritage)
✅ `/api/cdc/preliminary-check` - CDC blocked (heritage)
✅ `/api/heritage/hca-check` - North Summer Hill HCA
✅ `/api/housing-sepp/eligibility` - SEPP Housing CDC exclusions
✅ `/api/lep/provisions` - LEP Clause 5.10 heritage requirements
✅ `/api/sepp/structured-requirements` - BASIX, sustainability requirements
✅ `/api/tod/transport-autocomplete` - Nearest transport (if showing TOD)
⏭️ `/api/adg/requirements` - N/A (single dwelling, not apartments)
⏭️ `/api/precinct/provisions` - N/A or tested if precinct-specific controls exist

## Notes

- **POST endpoints** require request body - document required parameters
- **Optional endpoints** - mark as N/A if not applicable to use case
- **Error handling** - document if endpoint returns errors (explain why)
- **Cache timing** - note if data is cached vs live
