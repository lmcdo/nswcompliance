# PRP: NSW Planning Data Display Fix

## Status: CRITICAL - Data Available But Not Displayed

## Issue
The NSW Planning API is returning complete planning data (11 layers, 4 SEPPs, etc.) to the backend, but the frontend only shows generic counts instead of actual planning instrument names.

## Backend API Calls (Working)
The backend successfully calls:
1. `address` - gets propId 
2. `lot` - gets lot details
3. `layerintersect` - **gets complete planning_controls array with real data**

## Frontend Issue (Broken)
- Backend strips `planning_controls` from basic property intelligence response
- Frontend receives summary data, not raw planning instruments
- User sees "1 identified" instead of "SEPP (Sustainable Buildings) 2022"

## Required Data Structure (SAVED)
See: `nsw_api_sample_response.json` - Contains exact structure with:
- 4 SEPPs with full names
- Key Sites Map: Area 1 + legislative clauses
- Acid Sulfate Soils: Class 5
- R1 General Residential zoning
- FSR 0.5:1 + Area 5 controls
- Lot Size 200 m²

## Solution
**Backend Modification Required:**
1. Modify `/property-intelligence` endpoint to include `planning_controls`
2. Add parameter `include_raw_nsw_data=true` support
3. Return the exact layerintersect response to frontend

**Frontend Ready:**
- Already handles `data.planning_controls` array
- Already parses Special Provisions layer 
- Already displays SEPP names when data is present

## Files
- `NSW_API_WORKFLOW.md` - Complete API workflow documentation
- `nsw_api_sample_response.json` - Exact expected data structure
- Frontend parsing code is ready in `property-service.js`

## Priority: HIGH
User expects to see actual planning instrument names, not generic counts.
The data exists - just needs to be passed through to frontend.