# Deployment Essentials Analysis

## Directory Structure Overview

**477 Python files** (mostly unused dev scripts)
**25 API routes** (TypeScript - actively used)
**1.4GB output/** (extracted PDF JSON files)
**Backups & validated_outputs/** (migration artifacts)

## What You Actually Need

### ESSENTIAL (Must Deploy)
1. **frontend-nextjs/** - Complete Next.js application
2. **PostgreSQL database dump** - All 27 tables
3. **db_config.py** - Database connection configuration

### BACKUPS (Keep Locally, Don't Deploy)
1. **output/** (1.4GB) - MinerU extracted JSON from PDFs
2. **validated_outputs/** - Processing pipeline artifacts  
3. **backups/** - Database migration snapshots
4. **docs/** - Original PDF files (64MB DCPs + 46MB SEPPs)

### MAYBE NEEDED (Analyze Further)
- Python scripts that still run migrations/updates
- Configuration files for data processing

## Next Steps
1. Identify which Python scripts are still actively used
2. Create minimal deployment package
3. Archive development files separately
