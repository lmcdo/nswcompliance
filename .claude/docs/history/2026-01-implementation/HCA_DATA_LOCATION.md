# Heritage Conservation Area (HCA) Data - File Locations

## Project Data (In Repository)

### Inner West HCA Data (Active)
- **Location**: PostgreSQL database `nsw_planning.heritage_conservation_areas`
- **Records**: 2,039 Inner West HCAs
- **Size**: ~2MB
- **Usage**: Active queries via API endpoints
- **Script**: `download_inner_west_hca.py`

## Full NSW HCA Data (Archive)

### Complete NSW Dataset
- **Location**: `../nsw_hca_complete_20251011.geojson` (parent folder)
- **Records**: 10,000 HCAs (API limit, partial NSW data)
- **Size**: 37MB
- **Purpose**: Archive/backup, not used in production
- **Note**: Does NOT include Inner West (hit API limit before Inner West data)

**Why separate?**
- Keep project folder clean
- Full NSW data not needed for Inner West-focused app
- Prevents confusion between active (Inner West) and archived (full NSW) data

## To Re-download Inner West Data

```bash
cd "C:\Users\lawre\downloads\solvyra\projects\compliance engine\compliance-engine"
python download_inner_west_hca.py
```

This will:
1. Download 2,039 Inner West HCAs from NSW SEED Portal
2. Clear existing Inner West data in database
3. Import fresh data with spatial indexes
4. Verify import (including Lackey Street HCA check)

## To Download Other LGAs

Modify `download_inner_west_hca.py` and change:
```python
params = {
    'where': "LGA_NAME='SYDNEY'",  # Change LGA name here
    ...
}
```

Available LGAs in NSW SEED data:
- SYDNEY, NEWCASTLE, WAVERLEY, MOSMAN, WOLLONGONG, ORANGE, etc.

## Database Connection

All scripts use safe database wrapper:
```python
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Your queries here
```

## Data Update Frequency

NSW SEED Portal updates: **Weekly**

Recommended sync: **Monthly** (sufficient for planning purposes)
