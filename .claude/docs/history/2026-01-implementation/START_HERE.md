# PlotDetect - Start Here

**NSW Planning Compliance Engine**
Multi-layer regulatory analysis: State (SEPP) + Local Law (LEP) + Design Guidelines (DCP)

---

## 🚀 Quick Start (5 minutes)

### 1. Prerequisites
- Node.js 20+
- PostgreSQL 14+ (or Supabase connection)
- Python 3.10+ (for data extraction only)

### 2. Setup
```bash
# Clone and install
git clone <repo-url>
cd compliance-engine
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with your database credentials

# Start development server
npm run dev
# Visit http://localhost:3003
```

### 3. Test It Works
1. Enter any Inner West address: "123 Smith St, Marrickville 2204"
2. See property zone, constraints, and planning controls
3. Click through SEPP, LEP, and DCP tabs

---

## 📚 Key Documentation

### For Developers
1. **README.md** - Full setup, architecture, API endpoints
2. **CLAUDE.md** - Code standards, safety rules, project structure
3. **docs/ARCHITECTURE.md** - System architecture, what works/doesn't
4. **docs/FEATURES_CAPABILITIES.md** - Feature matrix ("Can it do X?")
5. **DB_SCHEMA.md** - Database quick reference

### For Data Work
6. **docs/ENRICHMENT_PROCESS.md** - How to onboard new councils
7. **DB_SCHEMA_RAW.txt** - Full database schema (58 tables)
8. **scripts/** - Core extraction/enrichment scripts

### For Deployment
9. **DEPLOYMENT.md** - Deploy to Vercel (if exists)
10. **NEXT_STEPS.md** - Strategic roadmap, competitive positioning

---

## 🏗️ Architecture at a Glance

```
┌─────────────────────────────────────────────────┐
│  Frontend (Next.js 14)                         │
│  ├─ /assessment - Main assessment interface    │
│  ├─ /api/property - NSW Planning Portal proxy  │
│  ├─ /api/provisions - DCP filtering            │
│  ├─ /api/permissibility - LEP land use         │
│  └─ /api/ai/chat - AI assistant                │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│  Database (Supabase PostgreSQL)                │
│  ├─ regulatory_provisions (46,585 rows)        │
│  ├─ lep_land_use_table                         │
│  ├─ dcp_precinct_boundaries (GeoJSON)          │
│  └─ housing_sepp_standards                     │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│  External APIs                                  │
│  ├─ NSW Planning Portal (property data)        │
│  └─ Google Gemini (AI classification)          │
└─────────────────────────────────────────────────┘
```

---

## 📊 What PlotDetect Does

### ✅ Fully Working
- **Property lookup** - Any NSW address → zone, constraints, precinct
- **DCP provision filtering** - 4-layer model (generic, use-specific, condition, precinct)
- **Permissibility checks** - "Can I build X in this zone?" from LEP land use table
- **AI chat assistant** - 8 question categories with precomputed answers
- **Heritage/flood/bushfire** - Constraint overlay from NSW Planning Portal
- **PDF citations** - Click through to exact DCP pages

### ⚠️ Partially Working
- **Granny flat questions** - Permissibility only, not full DCP synthesis
- **Multi-endpoint synthesis** - Can't combine LEP + DCP + SEPP (yet)
- **Setback requirements** - Shows provisions but not specific numbers

### ❌ Not Yet Built
- **Compliance verification** - Can't check if designs comply
- **CDC eligibility** - Can't determine complying vs DA pathway
- **Lot size calculation** - NSW Portal returns polygon but not area

See **docs/FEATURES_CAPABILITIES.md** for complete feature matrix.

---

## 🗄️ Database Overview

**Total provisions: 46,585**
- 10,008 actionable controls (v2_is_actionable = true)
- 36,577 contextual/guidance provisions

**By source:**
- 35,028 SEPP provisions (State legislation)
- 5,836 Inner West LEP 2022 (Local law)
- 5,721 DCP provisions (Marrickville, Ashfield, Leichhardt)

**Geographic coverage:**
- 102 precincts mapped (GeoJSON boundaries)
- 3 councils: Marrickville (100%), Leichhardt (100%), Ashfield (partial)

See **DB_SCHEMA.md** for table details.

---

## 🎯 Common Tasks

### Add a New API Endpoint
1. Create route: `frontend-nextjs/app/api/your-endpoint/route.ts`
2. Add database query logic
3. Test with: `curl http://localhost:3003/api/your-endpoint`
4. Document in README.md

### Extract New Council Data
1. Read **docs/ENRICHMENT_PROCESS.md** (comprehensive guide)
2. Use scripts in `scripts/` directory
3. Follow 3-stage pipeline: extraction → enrichment → production

### Modify AI Chat Behavior
1. Edit classifier: `frontend-nextjs/lib/ai/classifier.ts`
2. Edit router: `frontend-nextjs/lib/ai/router.ts`
3. Edit formatter: `frontend-nextjs/lib/ai/formatter.ts`
4. Test at `/assessment` page

### Deploy to Production
1. Push to `main` branch
2. Vercel auto-deploys
3. Check: https://verify.plotdetect.com.au

---

## 🚨 Critical Rules (from CLAUDE.md)

1. **NEVER create fake/placeholder data** - If data unavailable, show error
2. **NEVER run queries without WHERE clauses** on main tables
3. **NEVER use `taskkill //IM node.exe`** - Kills Claude Chat server
4. **ALWAYS read DB_SCHEMA.md** before database work
5. **Kill Next.js dev server by PORT only:** `netstat -ano | findstr :3003` then `taskkill /F /PID <PID>`

See **CLAUDE.md** for complete standing rules.

---

## 🆘 Help & Troubleshooting

### Development Server Won't Start
```bash
# Check if port 3003 is in use
netstat -ano | findstr :3003

# Kill the process if needed
taskkill /F /PID <PID>

# Restart
npm run dev
```

### Database Connection Errors
```bash
# Test connection
cd frontend-nextjs
node -e "const { getPool } = require('./lib/database/pool-manager'); getPool().query('SELECT 1').then(() => console.log('OK')).catch(console.error)"
```

### AI Chat Not Working
1. Check Gemini API key in `.env.local`
2. Check rate limits (5 requests/minute)
3. Check browser console for errors
4. Review logs in terminal

---

## 📞 Contact & Resources

- **Issues:** Create issue in GitHub
- **Docs:** See `docs/` directory
- **Historical context:** See `docs/history/` for implementation details
- **Database schema:** `DB_SCHEMA.md` (quick) or `DB_SCHEMA_RAW.txt` (full)

---

**Last Updated:** 2026-02-01
**Next Review:** After major feature release
