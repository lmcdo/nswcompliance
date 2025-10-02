# Clean Deployment Package - NSW Planning Compliance Engine

## 🎯 WHAT YOU NEED FOR VERCEL + SUPABASE

### ✅ ESSENTIAL FILES (Deploy These)

**1. Frontend Application (~50MB)**
```
frontend-nextjs/
├── app/                    # All pages and API routes
├── components/             # React components  
├── lib/                    # Database clients, utilities
├── public/                 # Images, icons
├── package.json
├── package-lock.json
├── tsconfig.json
├── next.config.js
├── tailwind.config.ts
└── postcss.config.js
```

**2. Database Export**
```bash
# Create database dump (run locally)
pg_dump -U postgres -d nsw_planning > nsw_planning_production.sql

# File size: ~50-150MB (text data only)
```

**3. Optional: Minimal Python Support**
```
db_config.py               # Connection helper (if you want backup scripts)
requirements.txt           # Python dependencies (if needed)
```

### 🗑️ DO NOT DEPLOY (Keep Local Archives)

**Large Data Files (1.5GB+)**
```
output/                    # 1.4GB - Extracted PDF JSON
docs/                      # 110MB - Original PDFs
validated_outputs/         # Processing artifacts
backups/                   # Database snapshots
```

**Development Scripts (477 Python files)**
```
analyze_*.py              # Data analysis (used during development)
check_*.py                # Database inspection
extract_*.py              # PDF extraction
migrate_*.py              # One-time migrations
test_*.py                 # Testing utilities
verify_*.py               # Verification scripts
```

**Development Directories**
```
analysis/
autoschemakg_*/
lightrag/
PRPs/                     # Documentation
.claude/
.claude_backup/
venv_linux/
__pycache__/
```

## 📋 DEPLOYMENT CHECKLIST

### Step 1: Create Production Database Dump
```bash
# Export current database
pg_dump -U postgres -d nsw_planning -f nsw_planning_production.sql

# Verify dump size
ls -lh nsw_planning_production.sql
# Expected: 50-150MB
```

### Step 2: Prepare Frontend for Deployment
```bash
cd frontend-nextjs

# Install dependencies
npm install

# Test build locally
npm run build

# Expected output: No errors, optimized production build
```

### Step 3: Archive Source Data Locally
```bash
# Create local backup archive (keep separate from deployment)
tar -czf nsw_planning_sources_backup.tar.gz \
  output/ \
  docs/ \
  validated_outputs/ \
  backups/ \
  *.py \
  PRPs/

# Store safely - you may need this for future updates
```

### Step 4: Deploy to Supabase
1. Create Supabase project
2. Copy database connection string
3. Import SQL dump via Supabase SQL Editor
4. Verify tables created: `SELECT COUNT(*) FROM regulatory_provisions`

### Step 5: Deploy to Vercel
1. Push `frontend-nextjs/` to GitHub
2. Import repository in Vercel
3. Add environment variable:
   ```
   DATABASE_URL=postgresql://[supabase-connection-string]
   ```
4. Deploy automatically

## 🧹 CLEANUP RECOMMENDATIONS

### Option A: Minimal Deployment Repo (Recommended)
Create new Git repository with only:
```
frontend-nextjs/
README.md
.gitignore
LICENSE (if applicable)
```

**Benefits:**
- Clean deployment
- Fast CI/CD
- No confusion about unused files

### Option B: Keep Everything (Easier)
Deploy current repo as-is to Vercel

**Vercel will automatically ignore:**
- Python files (not used in build)
- Data directories (via .gitignore)
- Development artifacts

**Benefits:**
- No restructuring needed
- Keep full history
- Vercel build only uses frontend-nextjs/

## 📊 SIZE COMPARISON

**Current Project:**
- Total: ~3-4GB (with all dev files)
- Git repo: ~200MB

**Deployed to Vercel:**
- Build size: ~10MB (Next.js optimized)
- Serverless functions: ~2MB each
- Database: Hosted on Supabase (separate)

**What Vercel Actually Uses:**
- Reads: `frontend-nextjs/` only
- Ignores: Everything else
- Builds: Optimized production bundle

## ✅ RECOMMENDED APPROACH

**DO THIS:**
1. Export database: `pg_dump` → Supabase
2. Push entire repo to GitHub (Vercel ignores unused files)
3. Deploy frontend from `frontend-nextjs/` directory
4. Archive local dev files separately (optional)

**DON'T DO THIS:**
- Try to deploy Python scripts (not needed)
- Upload output/ or docs/ (already processed into DB)
- Delete anything yet (keep backups)

## 🎁 BONUS: Keep Python Scripts for Updates

**If you plan to update data later:**

**Keep These Files:**
```
db_config.py              # Database connection
run_phase*.py             # Data migrations
rollback_phase*.py        # Rollback scripts
requirements.txt          # Python dependencies
```

**Archive These:**
```
All analyze_*.py          # One-time analysis
All check_*.py            # Inspection tools
All test_*.py             # Testing
output/                   # Extracted data (backup)
```

**Run Updates Locally:**
1. Make database changes locally
2. Test thoroughly
3. Export new dump
4. Upload to Supabase
5. Frontend auto-updates (no redeployment needed)

