# NSW Planning Compliance Engine - Startup Instructions

## Quick Start Commands

### **Backend (Python FastAPI)**
```bash
# 1. Activate Python environment
./venv_linux/Scripts/activate # Windows
# OR source venv_linux/bin/activate # Linux

# 2. Start the API server
python api_server.py
```
**Backend runs on:** `http://localhost:8006`

### **Frontend (Static HTML)** 
```bash
# Option 1: Simple HTTP server (recommended)
npx http-server frontend -p 3000 -c-1

# Option 2: Python HTTP server
cd frontend && python -m http.server 3000

# Option 3: Direct file access (may have CORS issues)
start "frontend/index.html"
```
**Frontend runs on:** `http://localhost:3000`

## Complete Startup Sequence

### **First Time Setup (if citations not yet extracted):**
```bash
# Extract full clause citations (one-time setup)
./venv_linux/Scripts/python.exe services/full_clause_extractor.py
```

### **Daily Startup (2 terminals):**

**Terminal 1 - Backend:**
```bash
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"
./venv_linux/Scripts/activate
python api_server.py
```

**Terminal 2 - Frontend:**
```bash
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"
npx http-server frontend -p 3000 -c-1
```

### **Access Application:**
Open browser to: `http://localhost:3000`

## Expected Startup Output

### **Backend Success:**
```
Starting NSW Planning API 
Loaded clause index with 2,955 entries
Loaded document index with 54 documents
Validated system: True
Council setback endpoint available at /calculate-setbacks-council
INFO: Uvicorn running on http://0.0.0.0:8006 (Press CTRL+C to quit)
```

### **Frontend Success:**
```
Starting up http-server, serving ./frontend
Available on:
 http://127.0.0.1:3000
 http://[your-ip]:3000
Hit CTRL-C to stop the server
```

## API Endpoints Available

### **Main Endpoints:**
- `POST /query` - Main planning rules query with full citations
- `POST /property-intelligence-complete` - Complete 4-stack property analysis
- `POST /calculate-setbacks-council` - Authoritative setback calculations

### **Citation Endpoints:**
- `GET /citations/search?q={query}` - Search clause citations
- `GET /citations/clause/{number}` - Get specific clause citation 
- `GET /citations/stats` - Citation system statistics
- `POST /clause-citation` - Connected requirements citations

### **Property Intelligence:**
- `POST /property-dashboard` - NSW Planning Portal integration
- `GET /debug-route-test` - System health check

## Council MVP Features Ready

 **Complete regulatory citations** with full paragraph text 
 **Property intelligence** with zone/height/FSR data 
 **Connected requirements** showing regulatory relationships 
 **Authoritative setback calculations** with council disclaimers 
 **Professional verification flags** for official use 

## Troubleshooting

### **Backend Issues:**
- **Port 8006 in use:** Change port in `api_server.py` line 847
- **Module not found:** Check `./venv_linux/Scripts/activate` ran successfully
- **Citations not loading:** Run `services/full_clause_extractor.py` first

### **Frontend Issues:**
- **CORS errors:** Use `npx http-server` instead of direct file access
- **Port 3000 in use:** Change port: `npx http-server frontend -p 3001`
- **API not connecting:** Verify backend is running on port 8006

### **Citation Issues:**
- **No full citations showing:** Check citation extraction completed
- **Search not working:** Verify `/citations/stats` shows loaded clauses
- **Accordion not opening:** Check browser console for JavaScript errors

## Development Notes

- **Virtual Environment:** Uses `venv_linux` (works on Windows via WSL compatibility)
- **Port Configuration:** Backend 8006, Frontend 3000 (configurable)
- **Data Storage:** Citations stored in `clause_citations/` directory
- **Log Output:** Backend shows detailed citation loading and API requests
- **Hot Reload:** Backend auto-reloads on code changes (if `reload=True` enabled)

## Council Demonstration Ready

The system provides complete regulatory authority with:
- Full DCP clause text with legal language
- NSW Planning Portal integration 
- Professional verification requirements
- Authoritative source citations
- Confidence scoring for reliability

**Ready for Inner West Council MVP demonstration!**