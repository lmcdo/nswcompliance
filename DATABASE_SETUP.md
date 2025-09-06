# Database Setup - NSW Planning Compliance Engine

This guide will help you set up the PostgreSQL database required for the PRP-K3 zone-specific setback calculation engine.

## Prerequisites

1. **PostgreSQL 15+** installed and running
   - Windows: Download from https://www.postgresql.org/download/windows/
   - Default port: 5432
   - Default user: `postgres` with password `postgres`

2. **Python 3.8+** with required packages:
   ```bash
   pip install psycopg2-binary
   ```

## Quick Setup

### 1. Clone and Setup Database
```bash
git clone <repo-url>
cd compliance-engine
python setup_database.py
```

This script will:
- ✅ Create `nsw_planning` database
- ✅ Create `zone_setback_rules` table with proper schema
- ✅ Import 48 setback rules with 95% confidence scores
- ✅ Create performance indexes
- ✅ Test the database connection

### 2. Setup Frontend
```bash
cd frontend-nextjs
npm install
cp .env.local.template .env.local
# Edit .env.local with your API keys if needed
npm run dev
```

### 3. Test the System
Visit http://localhost:3007 and search for:
```
38 Pile St, Dulwich Hill NSW 2203, Australia
```

You should see:
- ✅ Property data from NSW Planning API (propId: 1962875, zone: R2)
- ✅ 5 setback rules from PostgreSQL database
- ✅ Side: 0.90m → 1.50m → 2.50m (by height)
- ✅ Front: 4.50m, Rear: 3.00m

## Database Contents

The setup creates a `zone_setback_rules` table with:

- **48 total rules** across 7 zones (R2, B1, B2, B4, etc.)
- **3 councils** (Ashfield, Leichhardt, Marrickville) 
- **High confidence** rules (0.75-0.95) from DCP sources
- **Legal references** to Marrickville DCP 2011, etc.

### Sample Data Structure:
```sql
SELECT * FROM zone_setback_rules WHERE zone = 'R2' LIMIT 1;

rule_id          | MARRICKVILLE_R2_side_0.9m
zone             | R2  
council          | Marrickville
boundary_type    | side
base_value       | 0.90
unit             | metres
confidence       | 0.95
source_document  | Marrickville DCP 2011 - 4.1 Low Density Residential Development
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
netstat -an | findstr :5432

# Test connection manually
psql -U postgres -h localhost -d nsw_planning -c "SELECT COUNT(*) FROM zone_setback_rules;"
```

### Missing Data
```bash
# Re-run setup to reimport data
python setup_database.py
```

### Frontend API Errors
Check that your `.env.local` contains:
```
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=nsw_planning
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
```

## Architecture

```
NSW Planning API → Frontend Hook → PostgreSQL Database → Zone-Specific Results
     ↓                    ↓               ↓                      ↓
  Property Data      Transforms       Queries Rules        Returns Setbacks
  (zone, propId)     API Response     (zone + council)     (with confidence)
```

## Files Overview

- `setup_database.py` - Database creation and data import script
- `database_export.json` - Exported schema and setback rules data  
- `frontend-nextjs/lib/database/client.ts` - PostgreSQL client for API
- `frontend-nextjs/app/api/setbacks/calculate/route.ts` - PRP-K3 calculation API

The system is now ready for zone-specific setback calculations! 🎯