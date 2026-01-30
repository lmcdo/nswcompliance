# Zod Validation Examples

## Overview
This document shows example requests and responses for the 8 validated routes.

---

## 1. `/api/compliance/enhanced` (POST)

### Valid Request
```json
{
  "address": "45 Liverpool Street, Ashfield NSW 2131",
  "zone": "R2",
  "developmentType": "dual_occupancy",
  "lga": "Inner West",
  "includeHeritage": true
}
```

### Invalid Request (Missing Required Field)
```json
{
  "zone": "R2",
  "developmentType": "dual_occupancy"
}
```

**Response (400):**
```json
{
  "success": false,
  "error": "Invalid request data",
  "details": [
    "address: Address must be at least 5 characters"
  ]
}
```

---

## 2. `/api/property` (GET)

### Valid Request
```
GET /api/property?address=45 Liverpool Street, Ashfield NSW 2131&includeConstraints=true
```

### Invalid Request (Address Too Short)
```
GET /api/property?address=123
```

**Response (400):**
```json
{
  "success": false,
  "error": "Invalid request data",
  "details": [
    "address: Address must be at least 5 characters"
  ],
  "example": "/api/property?address=3 Wilkinson Ln, Telopea NSW 2117"
}
```

---

## 3. `/api/capacity/calculate` (POST)

### Valid Request
```json
{
  "lotSize": 450,
  "frontage": 15,
  "zone": "R2",
  "fsr": 0.6,
  "heightLimit": 9.5,
  "developmentType": "dual_occupancy"
}
```

### Invalid Request (Negative Lot Size)
```json
{
  "lotSize": -100,
  "frontage": 15,
  "zone": "R2"
}
```

**Response (400):**
```json
{
  "success": false,
  "error": "Invalid request data",
  "details": [
    "lotSize: Lot size must be positive"
  ]
}
```

---

## 4. `/api/provisions` (GET)

### Valid Request
```
GET /api/provisions?q=setback&documentType=DCP&zone=R2&limit=20
```

### Invalid Request (Query Too Short)
```
GET /api/provisions?q=s
```

**Response (400):**
```json
{
  "success": false,
  "error": "Invalid request data",
  "details": [
    "query: Search query must be at least 2 characters"
  ]
}
```

---

## 5. `/api/compliance/live-check` (POST)

### Valid Request
```json
{
  "address": "45 Liverpool Street, Ashfield NSW 2131",
  "developmentType": "dual_occupancy",
  "includeReasons": true
}
```

### Invalid Request (Invalid Development Type)
```json
{
  "address": "45 Liverpool Street, Ashfield NSW 2131",
  "developmentType": "not_a_real_type"
}
```

**Response (400):**
```json
{
  "success": false,
  "error": "Invalid request data",
  "details": [
    "developmentType: Invalid enum value. Expected 'dwelling_house' | 'dual_occupancy' | ..."
  ]
}
```

---

## 6. `/api/permissibility/check` (POST)

### Valid Request
```json
{
  "address": "45 Liverpool Street, Ashfield NSW 2131",
  "zone": "R2",
  "developmentType": "dual_occupancy",
  "lga": "Inner West",
  "lotSize": 450
}
```

### Invalid Request (Invalid Zone Format)
```json
{
  "address": "45 Liverpool Street, Ashfield NSW 2131",
  "zone": "invalid-zone-123",
  "developmentType": "dual_occupancy"
}
```

**Response (400):**
```json
{
  "success": false,
  "error": "Invalid request data",
  "details": [
    "zone: Zone must be uppercase alphanumeric (e.g., R1, B4, RE1)"
  ]
}
```

---

## 7. `/api/housing-sepp/eligibility` (POST)

### Valid Request
```json
{
  "address": "45 Liverpool Street, Ashfield NSW 2131",
  "zone": "R2",
  "lotSize": 450,
  "developmentType": "manor_house",
  "lga": "Inner West"
}
```

### Invalid Request (Wrong Development Type)
```json
{
  "address": "45 Liverpool Street, Ashfield NSW 2131",
  "zone": "R2",
  "lotSize": 450,
  "developmentType": "dwelling_house"
}
```

**Response (400):**
```json
{
  "success": false,
  "error": "Invalid request data",
  "details": [
    "developmentType: Invalid enum value. Expected 'manor_house' | 'terrace_house' | 'dual_occupancy' | 'multi_dwelling_housing'"
  ]
}
```

---

## 8. `/api/precinct/provisions` (POST)

### Valid Request
```json
{
  "precinctId": "29_",
  "zone": "R2",
  "limit": 50
}
```

### Invalid Request (Invalid Limit)
```json
{
  "precinctId": "29_",
  "limit": 200
}
```

**Response (400):**
```json
{
  "success": false,
  "error": "Invalid request data",
  "details": [
    "limit: Number must be less than or equal to 100"
  ]
}
```

---

## Testing with cURL

### Test Invalid Address (Too Short)
```bash
curl -X POST http://localhost:3000/api/compliance/enhanced \
  -H "Content-Type: application/json" \
  -d '{"address": "123", "zone": "R2", "developmentType": "dual_occupancy", "lga": "Inner West"}'
```

Expected: 400 error with validation message

### Test Invalid Zone Format
```bash
curl -X POST http://localhost:3000/api/permissibility/check \
  -H "Content-Type: application/json" \
  -d '{"address": "45 Liverpool St, Ashfield", "zone": "invalid123", "developmentType": "dual_occupancy"}'
```

Expected: 400 error with zone format message

### Test Missing Required Field
```bash
curl -X GET "http://localhost:3000/api/property?includeConstraints=true"
```

Expected: 400 error with "address parameter required" message

---

## Benefits Demonstrated

1. **Clear Error Messages**: Users know exactly what went wrong
2. **Prevents Bad Data**: Invalid requests never reach business logic
3. **Type Safety**: All fields are properly typed and validated
4. **Consistent Format**: All validation errors follow same structure
5. **Developer Friendly**: Easy to debug with detailed error paths

---

## Next Steps

To test validation in your application:

1. Start the development server:
   ```bash
   npm run dev
   ```

2. Make test requests with invalid data using:
   - Postman
   - cURL
   - Your frontend application

3. Verify that:
   - Invalid requests return 400
   - Error messages are clear and specific
   - Valid requests work as expected
