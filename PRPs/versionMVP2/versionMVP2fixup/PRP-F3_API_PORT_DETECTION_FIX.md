# PRP-F3: API Port Detection Fix

## Objective
Fix API port detection issues where verification scripts look for port 8000 but server runs on 8006.

## Root Cause Analysis
- Verification scripts hardcoded to check port 8000
- API server actually running on port 8006
- No dynamic port detection mechanism
- Scripts fail with "API not running" when server is operational

## Technical Implementation

### Phase 1: Dynamic Port Detection
```python
def detect_api_port(host="localhost", port_range=(8000, 8010)):
    """Detect which port the API server is running on"""
    import requests

    for port in range(port_range[0], port_range[1] + 1):
        try:
            response = requests.get(f"http://{host}:{port}/health", timeout=2)
            if response.status_code == 200:
                return port
        except:
            continue
    return None
```

### Phase 2: Configuration File Support
```python
# config/api_config.json
{
    "api": {
        "host": "localhost",
        "default_port": 8006,
        "fallback_ports": [8000, 8001, 8002, 8006, 8007, 8008]
    }
}
```

### Phase 3: Environment Variable Support
```bash
export API_PORT=8006
export API_HOST=localhost
```

## Success Criteria
- Scripts automatically detect correct API port
- All verification scripts work with actual API server
- Configuration supports different deployment scenarios
- No hardcoded port dependencies

## Verification Commands
```bash
python verify_f3_api_port_detection.py
```

## Dependencies
- API server running on any port
- Network connectivity to localhost
- requests library available