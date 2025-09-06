# NSW Planning Compliance Engine Frontend

A compact, simple frontend for testing the Ultimate NSW Processor (RagAnything + LightRAG).

## Features

- **Compact UI**: Single page with above-the-fold design
- **Accordion Layout**: Space-efficient results display
- **Real-time Status**: Connection indicator for API server
- **Property Queries**: Address-based planning rule lookups
- **Multiple Query Types**: Height, FSR, setbacks, general rules
- **Source Attribution**: Links to specific planning documents

## Quick Start

### 1. Install Dependencies
```bash
pip install fastapi uvicorn
```

### 2. Start the Server
```bash
python start_server.py
```

### 3. Open Frontend
Navigate to: http://localhost:8000

## API Endpoints

- `GET /` - Frontend interface
- `GET /health` - Server health check
- `POST /query` - Query planning rules
- `GET /docs` - API documentation

## Test Addresses

Try these Inner West addresses:
- 15 Norton Street, Leichhardt NSW 2040
- 45 Liverpool Street, Ashfield NSW 2131  
- 67 Marrickville Road, Marrickville NSW 2204

## Architecture

```
Frontend (HTML/JS) ←→ FastAPI Server ←→ Ultimate NSW Processor
     Port 8000              Python           (RagAnything + LightRAG)
```

## Query Types

- **Height**: Building height limits and exceptions
- **FSR**: Floor Space Ratio requirements
- **Setback**: Boundary setback rules
- **General**: Zoning and general planning controls
- **All**: Comprehensive planning rule summary

## Mock Data Mode

When the Ultimate NSW Processor is not available, the API returns realistic mock data for testing the frontend interface.

## Next Steps

1. Test the frontend interface
2. Integrate with actual Ultimate NSW Processor
3. Add more query types and filters
4. Connect to production planning documents