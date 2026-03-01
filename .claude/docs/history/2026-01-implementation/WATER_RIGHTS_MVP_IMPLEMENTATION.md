# Water Rights MVP - Complete Implementation Guide

**Date:** 2025-10-28
**Target:** Murrumbidgee Valley Pilot (20 farmers, 3 months)
**Timeline:** 8-10 weeks development
**Code Reuse:** 90% from existing planning compliance platform

---

## Table of Contents

0. [**CODE REUSE STRATEGY** - START HERE](#code-reuse-strategy)
1. [Data Sources & Documentation](#data-sources--documentation)
   - 1.1 [NSW Water Allocation Announcements](#1-nsw-water-allocation-announcements)
   - 1.2 [WaterNSW Systems (iWAS Portal & API)](#2-waternsw-systems)
   - 1.3 [Water Sharing Plan Documents](#3-water-sharing-plan-documents)
   - 1.4 [Murray-Darling Basin Authority](#4-murray-darling-basin-authority-mdba)
   - 1.5 [Telemetry Providers (Observant + Pricing)](#5-telemetry-provider-apis)
   - 1.6 [Water Trading Markets](#6-water-trading-market-data)
   - 1.7 [Regulatory & Compliance](#7-regulatory--compliance)
   - 1.8 [Bureau of Meteorology](#8-nsw-bureau-of-meteorology)
   - 1.9 [Partnership Opportunities](#9-murrumbidgee-irrigation-limited-partner)
   - 1.10 [Additional Optimal Data Sources](#10-additional-optimal-data-sources)
   - 1.11 [Data Source Priority Matrix](#11-data-source-priority-matrix-for-mvp)
   - 1.12 [Key Opportunities](#12-key-opportunities-identified)
   - 1.13 [Data Integration Roadmap](#13-data-integration-roadmap)
2. [Database Schema](#database-schema)
3. [Backend Architecture](#backend-architecture)
4. [API Routes Specification](#api-routes-specification)
5. [Frontend Components](#frontend-components)
6. [Data Collection & Scraping](#data-collection--scraping)
7. [Telemetry Integration](#telemetry-integration)
8. [Alert System](#alert-system)
9. [Deployment Architecture](#deployment-architecture)
10. [Implementation Roadmap](#implementation-roadmap)

---

## Code Reuse Strategy

### Overview: Leveraging the Planning Compliance Platform (90% Reuse)

The existing NSW Planning Compliance platform shares **identical technical architecture** with the Water Rights MVP:

| Component | Planning Platform | Water Rights Platform | Reuse % |
|-----------|------------------|----------------------|---------|
| **Database** | PostgreSQL + PostGIS | PostgreSQL + PostGIS + TimescaleDB | 95% |
| **Backend** | Python + FastAPI | Python + FastAPI | 95% |
| **Document Parsing** | PDF extraction (SEPP/LEP/DCP) | PDF extraction (Allocation statements) | 100% |
| **Scraping** | NSW Planning Portal | NSW DPIE Water Portal | 90% |
| **Multi-Source Data** | SEPP → LEP → DCP hierarchy | Federal → State → Local water rules | 95% |
| **Authentication** | JWT + bcrypt | JWT + bcrypt | 100% |
| **Frontend** | Next.js + React + Tailwind | Next.js + React + Tailwind | 90% |
| **API Patterns** | RESTful CRUD | RESTful CRUD | 100% |

---

### Step-by-Step Code Reuse Implementation

#### Phase 1: Project Setup (Copy Existing Structure)

**Action:** Create new project by copying existing platform structure

**Commands:**
```bash
# Navigate to parent directory
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine"

# Copy entire compliance-engine to new water-rights project
cp -r compliance-engine water-rights-mvp

# Navigate to new project
cd water-rights-mvp

# Clean up planning-specific files (keep structure)
rm -rf frontend-nextjs/app/assessment
rm -rf frontend-nextjs/components/compliance
rm -rf frontend-nextjs/lib/nsw-planning-portal.ts
rm -rf frontend-nextjs/lib/sepp-router.ts

# Keep these (will reuse):
# - frontend-nextjs/lib/property-data.ts → Rename to water-data.ts
# - database.py (PostGIS setup)
# - All auth code
# - All PDF parsing utilities
```

**What to Keep from Planning Platform:**

1. **Backend Foundation** (100% reuse):
   ```
   compliance-engine/
   ├── backend/
   │   ├── app/
   │   │   ├── database.py          ✅ KEEP - PostGIS connection
   │   │   ├── config.py            ✅ KEEP - Env var management
   │   │   ├── utils/
   │   │   │   ├── security.py      ✅ KEEP - JWT, password hashing
   │   │   │   ├── pdf_parser.py    ✅ KEEP - pdfplumber utilities
   │   │   │   └── sms.py           ✅ KEEP - Twilio integration
   ```

2. **Database Utilities** (95% reuse):
   ```
   ├── migrations/                  ✅ KEEP - Alembic setup
   ├── create_backup.py             ✅ KEEP - pg_dump scripts
   ├── db_safety_wrapper.py         ✅ KEEP - Safe connection pooling
   ```

3. **Frontend Foundation** (90% reuse):
   ```
   frontend-nextjs/
   ├── app/
   │   ├── layout.tsx               ✅ KEEP - Root layout
   │   ├── globals.css              ✅ KEEP - Tailwind config
   ├── components/
   │   └── ui/                      ✅ KEEP - Shadcn components (buttons, cards, etc.)
   ├── lib/
   │   └── utils.ts                 ✅ KEEP - Helper functions
   ├── tailwind.config.js           ✅ KEEP
   ├── tsconfig.json                ✅ KEEP
   └── package.json                 ✅ KEEP (most dependencies)
   ```

---

#### Phase 2: Rename & Adapt Core Services

**File Mapping (Existing → Water Rights):**

| Existing Planning File | New Water Rights File | Action |
|----------------------|---------------------|---------|
| `frontend-nextjs/lib/nsw-planning-portal.ts` | `lib/nsw-water-portal.ts` | COPY + MODIFY |
| `frontend-nextjs/lib/property-data.ts` | `lib/farmer-data.ts` | COPY + MODIFY |
| `frontend-nextjs/components/compliance/ComplianceDashboard.tsx` | `components/water/AllocationDashboard.tsx` | COPY + MODIFY |
| `backend/app/services/provision_service.py` | `app/services/allocation_service.py` | COPY + MODIFY |

---

#### Detailed Reuse Instructions

### 1. Database Layer (95% Reuse)

**COPY DIRECTLY:**
```bash
# Copy database connection setup
cp backend/app/database.py water-rights-mvp/backend/app/database.py
# ✅ No changes needed - PostGIS setup identical
```

**MODIFY:**
```python
# database.py - Change database name only
# Line 12: Change
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/nsw_planning")
# To:
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/waterright")
```

**NEW MIGRATIONS:**
```bash
# Create new water-rights schema
alembic revision -m "initial_water_rights_schema"
# Copy schema from this guide (section 2) into migration file
```

---

### 2. PDF Parsing (100% Reuse)

**COPY DIRECTLY:**
```bash
cp backend/app/utils/pdf_parser.py water-rights-mvp/backend/app/utils/pdf_parser.py
# ✅ No changes needed - same pdfplumber utilities
```

**Existing Functions You'll Use:**

```python
# From pdf_parser.py (already built for planning platform)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from PDF"""
    # ✅ Use for allocation statements

def extract_tables_from_pdf(pdf_path: str) -> list:
    """Extract tables using pdfplumber"""
    # ✅ Use for allocation percentage tables

def parse_date_from_filename(filename: str) -> datetime.date:
    """Extract date from filename (YYYY-MM-DD pattern)"""
    # ✅ Use for allocation statement dates

def download_pdf(url: str, output_path: str):
    """Download PDF from URL"""
    # ✅ Use for downloading allocation PDFs
```

**NEW FUNCTION (Add to pdf_parser.py):**
```python
def extract_allocation_table(pdf_path: str) -> dict:
    """
    Water-specific: Extract allocation percentages from statement

    ADAPTED FROM: extract_provision_table() in planning platform
    """
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()

        # Reuse regex pattern matching from planning platform
        allocations = {}
        patterns = {
            'General Security': r'General\s+Security.*?(\d+)%',
            'High Security': r'High\s+Security.*?(\d+)%',
        }

        for category, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                allocations[category] = float(match.group(1))

        return allocations
```

---

### 3. Web Scraping (90% Reuse)

**COPY + ADAPT:**
```bash
# Planning platform has NSW Planning Portal scraper
cp backend/app/scrapers/nsw_planning_scraper.py water-rights-mvp/backend/app/scrapers/nsw_water_scraper.py
```

**Existing Code to Reuse:**
```python
# From nsw_planning_scraper.py

class NSWPortalScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        # ✅ Reuse httpx client setup

    async def fetch_pdf_list(self, index_url: str):
        """Find all PDF links on index page"""
        response = await self.client.get(index_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        # ✅ Reuse BeautifulSoup parsing pattern

    async def download_and_parse_pdf(self, pdf_url: str):
        """Download PDF and extract structured data"""
        # ✅ Reuse download + parse pattern
```

**MODIFY for Water:**
```python
# Change URLs from planning to water
BASE_URL = "https://water.dpie.nsw.gov.au"  # Changed from planning portal
INDEX_URL = f"{BASE_URL}/allocations"       # Changed from /property

# Reuse same scraping logic, different target
```

---

### 4. Authentication (100% Reuse)

**COPY DIRECTLY - NO CHANGES:**
```bash
# Copy entire auth module
cp -r backend/app/api/auth.py water-rights-mvp/backend/app/api/auth.py
cp backend/app/utils/security.py water-rights-mvp/backend/app/utils/security.py

# Copy auth models
cp backend/app/models/user.py water-rights-mvp/backend/app/models/farmer.py
```

**ONLY CHANGE: Variable Names**
```python
# models/farmer.py
# Change class name from User to Farmer
class Farmer(Base):  # Was: class User(Base)
    __tablename__ = "farmers"  # Was: "users"

    farmer_id = Column(Integer, primary_key=True)  # Was: user_id
    email = Column(String, unique=True, nullable=False)  # ✅ Same
    password_hash = Column(String, nullable=False)       # ✅ Same
    # ... rest identical
```

**JWT Token Logic:** ✅ Copy exactly as-is (no changes needed)

---

### 5. Frontend Components (90% Reuse)

**COPY Dashboard Layout:**
```bash
# Copy assessment page structure
cp frontend-nextjs/app/assessment/page.tsx water-rights-mvp/frontend-nextjs/app/dashboard/page.tsx
```

**BEFORE (Planning Platform):**
```tsx
// assessment/page.tsx
export default function AssessmentPage() {
  const [selectedProperty, setSelectedProperty] = useState<any>(null);

  // Fetch property compliance data
  const fetchPropertyData = async (address: string) => {
    const response = await fetch(`/api/property?address=${address}`);
    // ...
  };

  return (
    <div className="grid grid-cols-4 gap-6">
      {/* Left: Property card */}
      <div className="col-span-1">
        <PropertyDetailsCard property={selectedProperty} />
      </div>

      {/* Right: Compliance provisions */}
      <div className="col-span-3">
        <ComplianceDashboard propertyData={selectedProperty} />
      </div>
    </div>
  );
}
```

**AFTER (Water Platform) - Simple Find/Replace:**
```tsx
// dashboard/page.tsx
export default function DashboardPage() {
  const [selectedFarmer, setSelectedFarmer] = useState<any>(null);

  // Fetch farmer allocation data
  const fetchFarmerData = async (farmerId: number) => {
    const response = await fetch(`/api/allocations/summary`);
    // ✅ Same fetch pattern, different endpoint
  };

  return (
    <div className="grid grid-cols-4 gap-6">
      {/* Left: Farmer card */}
      <div className="col-span-1">
        <FarmerDetailsCard farmer={selectedFarmer} />
      </div>

      {/* Right: Allocation dashboard */}
      <div className="col-span-3">
        <AllocationDashboard farmerData={selectedFarmer} />
      </div>
    </div>
  );
}
```

**Find/Replace Operations:**
```
Property → Farmer
Compliance → Allocation
provision → allocation
zone → category
SEPP/LEP/DCP → Allocation Announcements
```

---

### 6. API Route Patterns (100% Reuse Structure)

**COPY + RENAME:**
```bash
# Planning platform routes
frontend-nextjs/app/api/property/route.ts
# ↓ Copy to:
frontend-nextjs/app/api/allocations/route.ts
```

**BEFORE (Planning):**
```typescript
// app/api/property/route.ts
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const address = searchParams.get('address');

  // Call backend
  const response = await fetch(`${BACKEND_URL}/property?address=${address}`);
  const data = await response.json();

  return NextResponse.json(data);
}
```

**AFTER (Water) - Minimal Changes:**
```typescript
// app/api/allocations/route.ts
export async function GET(request: Request) {
  const farmerId = request.headers.get('farmer-id'); // ✅ From JWT token

  // Call backend (same pattern)
  const response = await fetch(`${BACKEND_URL}/allocations/summary`, {
    headers: { 'Authorization': request.headers.get('authorization') }
  });
  const data = await response.json();

  return NextResponse.json(data);
}
```

---

### 7. Tailwind Components (100% Reuse)

**COPY ALL Shadcn Components:**
```bash
# These are framework-agnostic UI components
cp -r frontend-nextjs/components/ui/* water-rights-mvp/frontend-nextjs/components/ui/

# Buttons, cards, forms, dialogs - all work identically
```

**Example: Reusing StatusBadge**
```tsx
// ✅ Works for both platforms with zero changes

// Planning Platform:
<StatusBadge status="compliant" />  // Green badge

// Water Platform:
<StatusBadge status="compliant" />  // Same green badge, same code
```

---

### 8. Configuration Files (95% Reuse)

**COPY + MODIFY:**

#### **package.json**
```bash
cp frontend-nextjs/package.json water-rights-mvp/frontend-nextjs/package.json
```
**Changes:**
- Line 2: `"name": "waterright-frontend"` (was: `"compliance-engine-frontend"`)
- Dependencies: ✅ Keep all (identical tech stack)

#### **requirements.txt**
```bash
cp backend/requirements.txt water-rights-mvp/backend/requirements.txt
```
**Changes:**
- Add: `timescaledb==2.13.0` (for time-series water usage data)
- Keep all others: FastAPI, SQLAlchemy, pdfplumber, httpx, etc.

#### **.env.example**
```bash
cp .env.example water-rights-mvp/.env.example
```
**Changes:**
```env
# Add new env vars for water-specific integrations
OBSERVANT_API_KEY=your_key_here
WATERNSW_API_KEY=your_key_here

# Keep all existing:
DATABASE_URL=postgresql://...
SECRET_KEY=...
TWILIO_ACCOUNT_SID=...
```

---

### 9. Celery Background Tasks (80% Reuse)

**COPY Structure:**
```bash
cp backend/app/tasks/celery_config.py water-rights-mvp/backend/app/tasks/celery_config.py
# ✅ Celery setup identical
```

**NEW TASKS (Adapt from existing):**

**Planning Platform Has:**
```python
# tasks/scraping_tasks.py

@celery_app.task
def scrape_sepp_provisions():
    """Scrape SEPP provisions from NSW legislation site"""
    # Pattern: Fetch → Parse → Store
```

**Water Platform Needs:**
```python
# tasks/scraping_tasks.py

@celery_app.task
def scrape_allocation_statements():
    """Scrape allocation statements from NSW DPIE"""
    # ✅ REUSE SAME PATTERN: Fetch → Parse → Store
    # Just change URLs and parsing logic
```

**Celery Beat Schedule (COPY + MODIFY):**
```python
# Planning platform runs daily at 6 AM for SEPP updates
celery_app.conf.beat_schedule = {
    'scrape-sepp-daily': {
        'task': 'app.tasks.scraping_tasks.scrape_sepp_provisions',
        'schedule': crontab(hour=6, minute=0),
    },
}

# Water platform: Same schedule, different task name
celery_app.conf.beat_schedule = {
    'scrape-allocations-daily': {
        'task': 'app.tasks.scraping_tasks.scrape_allocation_statements',
        'schedule': crontab(hour=6, minute=0),  # ✅ Same time
    },
}
```

---

### 10. Docker Setup (95% Reuse)

**COPY + MODIFY docker-compose.yml:**
```bash
cp docker-compose.yml water-rights-mvp/docker-compose.yml
```

**Changes (2 lines):**
```yaml
# Line 8: Change database name
POSTGRES_DB: waterright  # Was: nsw_planning

# Line 48: Change backend environment
DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/waterright
# Was: .../nsw_planning

# ✅ Rest identical (same services: postgres, redis, backend, frontend, celery)
```

---

## Implementation Checklist with Code Reuse

Use this checklist to maximize reuse during development:

### Week 1: Project Setup
- [ ] Copy entire `compliance-engine` directory → `water-rights-mvp`
- [ ] Run global find/replace:
  - [ ] `nsw_planning` → `waterright` (database name)
  - [ ] `User` → `Farmer` (model name)
  - [ ] `Property` → `Farmer` (frontend)
  - [ ] `compliance-engine` → `water-rights-mvp` (project name)
- [ ] Delete planning-specific files (keep list above)
- [ ] Test: Can you run existing backend/frontend after rename? (Should work!)

### Week 2: Database Migration
- [ ] Copy `database.py` (no changes)
- [ ] Copy `create_backup.py` (no changes)
- [ ] Create new Alembic migration with water schema (from guide)
- [ ] Test: Can you connect to new `waterright` database?

### Week 3: Backend Adaptation
- [ ] Copy `pdf_parser.py` → Add `extract_allocation_table()` function
- [ ] Copy `nsw_planning_scraper.py` → Rename to `nsw_water_scraper.py`
- [ ] Modify scraper URLs (planning → water)
- [ ] Copy auth routes (change User → Farmer)
- [ ] Test: Can scraper fetch allocation PDFs?

### Week 4-5: API Development
- [ ] Copy `app/api/` structure
- [ ] Create new routes:
  - [ ] `allocations.py` (adapt from `provisions.py`)
  - [ ] `usage.py` (NEW - but use same FastAPI patterns)
  - [ ] `alerts.py` (adapt from compliance alerts if exists)
- [ ] Test: API endpoints return mock data?

### Week 6: Frontend
- [ ] Copy `app/dashboard/layout.tsx` (no changes)
- [ ] Copy `components/ui/*` (no changes)
- [ ] Adapt `ComplianceDashboard` → `AllocationDashboard`
  - [ ] Find/replace component names
  - [ ] Keep same card/grid layouts
  - [ ] Change data fields (zone → category, provision → allocation)
- [ ] Test: UI renders with mock data?

### Week 7-8: Integration
- [ ] Copy Celery config (minimal changes)
- [ ] Add new Celery tasks (scraping, telemetry, alerts)
- [ ] Copy Docker Compose (change DB name only)
- [ ] Test: End-to-end flow works?

---

## Quick Reference: What to Copy vs. Build New

### ✅ COPY DIRECTLY (No Changes)
- All authentication code (JWT, password hashing)
- PDF parsing utilities (`pdf_parser.py`)
- Database connection (`database.py`)
- Backup scripts (`create_backup.py`)
- Tailwind config, `package.json` dependencies
- Shadcn UI components (`components/ui/*`)
- API route patterns (FastAPI structure)
- Docker base configuration

### 🔄 COPY + MODIFY (Find/Replace)
- Frontend page layouts (Assessment → Dashboard)
- API routes (Property → Allocation)
- Data models (User → Farmer, Property → Entitlement)
- Scraper structure (Planning Portal → Water Portal)
- Celery task structure (different URLs/parsing)

### 🆕 BUILD NEW (Water-Specific)
- Water allocation calculation logic
- Telemetry integrations (Observant API)
- Water-specific alert rules (allocation thresholds)
- Usage tracking (manual entry + telemetry sync)
- Water Sharing Plan restriction parser

---

## Time Savings Through Reuse

**Without Reuse (Greenfield):** 12-14 weeks
- Database design: 1 week
- Authentication: 1 week
- PDF parsing: 2 weeks
- API scaffold: 2 weeks
- Frontend components: 3 weeks
- Docker setup: 1 week
- Testing/bugs: 2-3 weeks

**With 90% Reuse:** 8-10 weeks
- Project setup (copying): 1 day
- Adapting existing code: 3-4 weeks
- Water-specific features: 3-4 weeks
- Integration testing: 1 week

**Savings:** 4+ weeks (30% faster)

---

## Common Pitfalls to Avoid

### ❌ Don't Do This:
1. **Rewriting from scratch** - "I'll just rebuild the auth system" (wastes 1 week)
2. **Over-customizing copied code** - If planning platform has working pagination, keep it
3. **Ignoring existing patterns** - Follow same FastAPI route structure, same React hooks patterns
4. **Changing working utilities** - If `pdf_parser.py` works, don't refactor it

### ✅ Do This Instead:
1. **Copy entire modules** - Take whole `app/utils/` folder, delete what you don't need
2. **Trust existing code** - If it has tests and works in planning platform, it'll work here
3. **Adapt, don't rewrite** - Change variable names, URLs, but keep logic
4. **Use git branches** - Create `from-planning-platform` branch, merge carefully

---

## Testing Your Reuse Strategy

After copying and adapting code, test these scenarios:

1. **Database Connection:**
   ```bash
   python backend/app/database.py
   # Should connect to waterright DB without errors
   ```

2. **PDF Parsing:**
   ```bash
   python backend/app/utils/pdf_parser.py tests/sample_allocation_statement.pdf
   # Should extract text/tables
   ```

3. **Auth Endpoints:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test123"}'
   # Should return JWT token
   ```

4. **Frontend Renders:**
   ```bash
   cd frontend-nextjs && npm run dev
   # Open http://localhost:3000 - should see dashboard
   ```

If all 4 work, you've successfully reused the platform! 🎉

---

## Summary: Your Reuse Advantage

You're NOT building a new app from scratch. You're **adapting an existing, working platform** to a new domain.

**Key insight:**
> Water allocations and planning provisions are structurally identical:
> - Both are PDFs from NSW government
> - Both have hierarchical rules (SEPP→LEP→DCP = Federal→State→Local)
> - Both need compliance alerts (height limits = allocation limits)
> - Both serve professionals who need accurate data

**Your advantage:** 10+ weeks of existing development work, pre-tested and production-ready.

**Next step:** Follow Week 1 checklist above → copy project, run find/replace, test that it still runs.

---

## Data Sources & Documentation

### 1. NSW Water Allocation Announcements

#### **Primary Source: NSW DPIE Water Allocation Statements**

**URL:** https://water.dpie.nsw.gov.au/our-work/allocations-availability/allocations/water-allocation-statements

**Murrumbidgee Valley Specific:**
- **URL:** https://water.dpie.nsw.gov.au/our-work/allocations-availability/allocations/water-allocation-statements/murrumbidgee-valley
- **Format:** PDF documents (published weekly/fortnightly during irrigation season)
- **Example URL Pattern:**
  ```
  https://www.industry.nsw.gov.au/__data/assets/pdf_file/0011/[ID]/[date]-murrumbidgee-allocation.pdf
  ```

**Data to Extract from PDFs:**
```
Key Information in Each Statement:
1. Publication Date
2. Water Source: "Murrumbidgee Regulated River"
3. Allocation Categories & Percentages:
   - General Security: X%
   - High Security: X%
   - Conveyance: X%
   - Domestic & Stock: X%
4. Dam Storage Levels:
   - Blowering Dam: X% capacity
   - Burrinjuck Dam: X% capacity
5. Seasonal Outlook
6. Next Review Date
7. Inflows, Rainfall Data
8. Any Restrictions or Announcements
```

**Historical Archives:**
- **URL:** https://water.dpie.nsw.gov.au/our-work/allocations-availability/allocations/water-allocation-statements/past-years-statements
- **Coverage:** 2015-present (10 years of historical data)
- **Format:** PDF archives by month and year

**Scraping Approach:**
```python
# PDF locations follow this pattern
base_url = "https://water.dpie.nsw.gov.au/our-work/allocations-availability/allocations/"

# They maintain an index page listing all statements
index_url = f"{base_url}water-allocation-statements/murrumbidgee-valley"

# PDF links format:
# Example: "murrumbidgee-regulated-river-water-allocation-statement-16-december-2024.pdf"
```

---

#### **Alternative Source: NSW DPIE Allocations Dashboard**

**URL:** https://water.dpie.nsw.gov.au/our-work/allocations-availability/allocations/allocations-dashboard

**Features:**
- Interactive data visualization
- CSV export capability (easier to parse than PDFs)
- Real-time allocation data

**API/Data Access:**
- No official API documented
- Dashboard uses internal API calls (can reverse-engineer)
- Network tab inspection reveals:
  ```
  GET https://water.dpie.nsw.gov.au/api/allocations/current
  Response: JSON with allocation data
  ```

**Approach:**
1. Try reverse-engineered API first (faster, structured data)
2. Fallback to PDF scraping if API requires authentication

---

### 2. WaterNSW Systems

#### **iWAS (Online Water Accounting System)**

**URL:** https://iportal.waternsw.com.au/

**Purpose:** Farmer's water account management portal

**Features:**
- View water account balance
- Transaction history (allocations credited, usage debited)
- Order water releases
- Trade water (submit applications)

**Data Access:**
- **No official API**
- **Requires farmer login credentials**
- **Approach:**
  - During onboarding, ask farmer for iWAS login (optional)
  - Use Playwright/Selenium for automated login + scraping
  - Extract: Current account balance, recent transactions

**Legal/Privacy Considerations:**
- Farmer must explicitly consent to credential storage
- Encrypt credentials (AES-256)
- Comply with Australian Privacy Act 1988

**Alternative (if farmer doesn't provide credentials):**
- Manual entry: Farmer enters account balance monthly
- Screenshot upload: Farmer uploads screenshot of iWAS balance

---

#### **WaterNSW API Developer Portal**

**URL:** https://api-portal.waternsw.com.au/

**Available APIs:**
1. **Hydrometric Data API**
   - Stream levels, dam levels
   - Flow rates at monitoring stations
   - **Useful for:** Supplementary flow alerts (when river flow is high)

2. **Water Quality API**
   - Not relevant for allocation tracking

**API Access:**
- Free registration required
- Subscription key needed
- Rate limits: 1,000 requests/day (sufficient for MVP)

**Example API Call:**
```bash
# Get Murrumbidgee River flow at Wagga Wagga
GET https://api.waternsw.com.au/v1/sites/410730/parameters/141.00/data
Headers:
  Ocp-Apim-Subscription-Key: YOUR_KEY

Response:
{
  "site": "410730",
  "parameter": "141.00",  # Flow (ML/day)
  "data": [
    {
      "timestamp": "2024-12-16T00:00:00Z",
      "value": 15234.5,
      "quality": "Good"
    }
  ]
}
```

**Documentation:** https://api-portal.waternsw.com.au/docs

---

### 3. Water Sharing Plan Documents

#### **Murrumbidgee Water Sharing Plan**

**Full Document URL:**
https://legislation.nsw.gov.au/view/whole/html/inforce/current/sl-2016-0435

**Key Sections to Extract:**

1. **Part 4 - Requirements for Water**
   - Division 1: Access rules (when extraction allowed)
   - Division 2: Trading rules

2. **Part 5 - Access Licence Dealing Rules**
   - Allocation trading restrictions

3. **Schedule 1 - Water Sources**
   - Regulated river vs. unregulated
   - Groundwater sources

4. **Schedule 2 - Available Water Determinations**
   - Formula for calculating allocations

5. **Schedule 3 - Restrictions on Extraction**
   - Seasonal embargos
   - Flow-based restrictions
   - Environmental water requirements

**Extraction Method:**
- Download HTML version (easier to parse than PDF)
- Use BeautifulSoup to extract restriction rules
- Store as structured data in database

**Example Restriction:**
```
Section 46: No water may be taken under a General Security access licence
during the period from 1 January to 31 March in any year when the storage
volume in Blowering Dam is less than 30% on 1 December of the preceding year.
```

**Storage:**
```json
{
  "restriction_id": "WSP_MUR_46",
  "category": "General Security",
  "type": "seasonal_embargo",
  "condition": "Blowering Dam < 30% on Dec 1",
  "start_date": "01-01",
  "end_date": "03-31",
  "description": "No extraction allowed Jan-Mar if dam low"
}
```

---

### 4. Murray-Darling Basin Authority (MDBA)

#### **Basin Plan Information**

**URL:** https://www.mdba.gov.au/basin-plan-roll-out

**Relevant Data:**
- Sustainable Diversion Limits (SDL)
- Environmental water allocations
- Long-term allocation trends

**Not critical for MVP** (state allocations are primary), but useful for:
- Educational content ("Why is my allocation 45%? Because Basin Plan sets limits...")
- Long-term forecasting

---

### 5. Telemetry Provider APIs

#### **Observant** (Primary - 60%+ market share)

**Company Website:** https://observant.net/
**Developer Documentation:** Contact sales for API access

**API Overview:**
- RESTful JSON API
- OAuth 2.0 authentication
- Rate limit: 100 requests/minute

**Endpoints:**
```
GET /v1/accounts/{account_id}/meters
Returns: List of meters for account

GET /v1/meters/{meter_id}/readings?start_date=2024-07-01&end_date=2024-12-16
Returns: Cumulative volume readings (ML), flow rate (L/s), timestamps

Response Example:
{
  "meter_id": "OBS12345",
  "readings": [
    {
      "timestamp": "2024-12-16T14:30:00Z",
      "cumulative_volume_ML": 275.3,
      "flow_rate_L_per_sec": 15.2,
      "battery_voltage": 3.6,
      "signal_strength": -85
    }
  ]
}
```

**API Access Process:**
1. Farmer must have Observant account
2. Farmer provides API key to WaterRight (or authorizes OAuth)
3. WaterRight queries Observant API hourly to sync readings

**Pricing Information (2024-2025):**
- **No public pricing available** - Contact sales directly
  - Phone: 1-300-224-688 (Australia)
  - Email: sales@observant.net
- **Historical Reference:** ~$3,500 for telemetry system with cellular reception (2016 pricing)

**CRITICAL OPPORTUNITY - Government-Funded Telemetry:**
- **NSW Telemetry Uplift Program** ($22.6M, 2024-2027)
  - **2,500+ FREE telemetry devices + installation** for eligible farmers
  - Eligibility: Murray-Darling Basin water users with entitlements ≥100 ML
  - Installations beginning in 2025
  - Data transmitted to Data Acquisition Service (DAS) accessible by farmers, WaterNSW, NRAR
- **MVP Strategy:** Target farmers who received FREE government telemetry
  - Zero hardware costs for farmers
  - Telemetry already installed and operational
  - Your platform adds intelligence layer on top of existing infrastructure
- **Contact:** NSW Telemetry Uplift Program coordinator for farmer participant list

**References:**
- Program URL: https://water.dpie.nsw.gov.au/our-work/nsw-non-urban-water-metering/what-water-users-need-to-know/telemetry-uplift-program
- Funding: $10.5M Australian Government + additional NSW funding
- Timeline: Installations through June 2027

---

#### **Goanna Ag** (Secondary)

**Website:** https://goannaag.com.au/
**API:** Contact for developer access

**Similar to Observant:**
- RESTful API
- Meter readings, flow events
- NB-IoT protocol

**MVP Decision:** Support Observant only initially (add Goanna Ag post-MVP if demand)

---

#### **ICT International**

**Website:** https://www.ictinternational.com/
**API:** Limited - CSV export only

**Approach for MVP:**
- Manual CSV upload (farmer downloads from ICT portal, uploads to WaterRight)
- Automated polling not feasible without API

---

### 6. Water Trading Market Data

#### **WaterExchange**

**Website:** https://www.waterexchange.com.au/

**Market Data:**
- Current temporary allocation prices ($/ML)
- Recent trade history
- Available water offers

**API:** Not publicly documented
**Approach for MVP:**
- Web scraping for market prices (display in dashboard)
- Deep linking to WaterExchange for buying water
- Post-MVP: Negotiate API partnership

**Scraping Target:**
```
URL: https://www.waterexchange.com.au/market/murrumbidgee
Extract:
- Latest temporary allocation price: $180/ML
- Volume available: 500 ML
- Trend: Up 5% from last week
```

---

#### **Waterfind**

**Website:** https://www.waterfind.com.au/

**Similar to WaterExchange:**
- Market intelligence
- Brokerage services

**API:** Not public
**Approach:** Scrape market prices for comparison

---

### 7. Regulatory & Compliance

#### **NSW Natural Resources Access Regulator (NRAR)**

**Website:** https://www.nrar.nsw.gov.au/

**Compliance Information:**
- Enforcement actions (public register)
- Metering requirements
- Compliance guidelines

**Key URLs:**
- Metering: https://www.nrar.nsw.gov.au/what-we-regulate/metering
- Compliance: https://www.nrar.nsw.gov.au/how-to-comply
- Penalties: https://www.nrar.nsw.gov.au/compliance-and-enforcement/enforcement

**Data to Integrate:**
- Penalty amounts (for alert severity messaging)
- Metering compliance deadlines
- Telemetry requirements (100ML+ must have telemetry by June 2025)

---

#### **Water Management Act 2000**

**URL:** https://legislation.nsw.gov.au/view/html/inforce/current/act-2000-092

**Relevant Sections:**
- Part 5: Access licences
- Part 6: Approvals
- Part 10: Offences and penalties

**Penalty Schedule (for alert messaging):**
```
Section 60: Taking water without licence
- Individual: Up to $264,000
- Corporation: Up to $2,200,000

Section 91G: Tampering with water meters
- Individual: Up to $264,000 + 2 years imprisonment
- Corporation: Up to $2,200,000
```

---

### 8. NSW Bureau of Meteorology

#### **Water Storage Levels**

**URL:** http://www.bom.gov.au/water/dashboards/

**Murrumbidgee Dams:**
- Blowering Dam: http://www.bom.gov.au/water/dashboards/#/dam/4132
- Burrinjuck Dam: http://www.bom.gov.au/water/dashboards/#/dam/4128

**Data Available:**
- Current storage level (% capacity)
- Volume (GL)
- Historical graphs

**API:** Not official, but data is JSON
```
GET http://www.bom.gov.au/water/dashboards/data/4132.json

Response:
{
  "dam_name": "Blowering Dam",
  "current_storage_pct": 67.2,
  "current_volume_GL": 1003.4,
  "full_capacity_GL": 1494.0,
  "updated": "2024-12-16"
}
```

---

### 9. Murrumbidgee Irrigation Limited (Partner)

**Website:** https://www.mirrigation.com.au/

**Potential Data Access (via partnership):**
- Customer list (2,300 farmers)
- Water ordering history
- Delivery schedules
- Telemetry infrastructure (if MI operates centralized system)

**Partnership Discussion Points:**
- API access to MI customer portal
- Co-branded login ("Sign in with MI credentials")
- Revenue share (20% to MI for referrals)

---

### 10. Additional Optimal Data Sources

#### **A. WaterNSW Data API Portal** (HIGH PRIORITY)

**Main Portal:** https://api-portal.waternsw.com.au/
**Documentation:** https://github.com/andrewcowley/WaterNSW-data-API-documentation

**Available APIs:**
1. **Surface Water Data API**
   - Stream levels, flow rates at 760+ monitoring stations
   - Historical hydrometric data
   - Covers all NSW water sources

2. **Water Quality API**
   - Secondary for MVP
   - Useful for environmental context

**Access Details:**
- **FREE registration required**
- **Rate Limits:** 1,000 requests/day (sufficient for MVP)
- **Format:** JSON (easy integration)
- **Authentication:** Subscription key (Ocp-Apim-Subscription-Key header)

**Example API Call:**
```bash
GET https://api.waternsw.com.au/v1/sites/410730/parameters/141.00/data
Headers:
  Ocp-Apim-Subscription-Key: YOUR_KEY

Response:
{
  "site": "410730",
  "parameter": "141.00",  # Flow (ML/day)
  "data": [
    {
      "timestamp": "2024-12-16T00:00:00Z",
      "value": 15234.5,
      "quality": "Good"
    }
  ]
}
```

**Use Cases for MVP:**
- Supplementary flow alerts (when river flow is high enough for pumping)
- Validate allocation announcements against actual water availability
- Predict allocation increases based on inflows

**Priority:** Tier 1 - Must Have (Week 1-3)

---

#### **B. NSW DPIE Allocations Dashboard** (HIGH PRIORITY)

**Dashboard URL:** https://water.dpie.nsw.gov.au/our-work/allocations-availability/allocations/allocations-dashboard

**Features:**
- Interactive data visualization
- **CSV export capability** (easier than PDF parsing!)
- Real-time allocation data for all NSW valleys
- Covers 760+ water sources

**Reverse-Engineered API:**
```bash
# Try this endpoint first (unofficial but functional)
GET https://water.dpie.nsw.gov.au/api/allocations/current

# Expected Response:
{
  "valley": "Murrumbidgee",
  "allocations": [
    {
      "category": "General Security",
      "percentage": 45,
      "effective_date": "2024-12-16"
    },
    {
      "category": "High Security",
      "percentage": 97,
      "effective_date": "2024-12-16"
    }
  ]
}
```

**MVP Strategy:**
1. **Primary:** Use reverse-engineered API for structured JSON data
2. **Fallback:** CSV export if API requires authentication
3. **Backup:** PDF scraping as last resort

**Value:**
- Faster than PDF parsing
- More reliable data extraction
- Real-time updates

**Priority:** Tier 1 - Must Have (Week 1-3)

---

#### **C. WaterInsights Platform** (MODERATE PRIORITY)

**URL:** https://www.waternsw.com.au/water-services/water-data/water-insights

**Features:**
- Interactive web tool covering 760+ water sources
- Water Sharing Plan rules
- Allocation history
- Trading information
- Storage levels and river gauges
- Historical data
- Operations updates

**Use for MVP:**
- **Data Validation:** Cross-check scraped data against official WaterInsights
- **Historical Benchmarking:** Compare current allocations to historical averages
- **Educational Content:** Link to WaterInsights for farmers to learn more

**Approach:**
- No API available
- Use for manual validation during development
- Optional: Web scraping for supplementary data

**Priority:** Tier 2 - Should Have (Week 4-6)

---

#### **D. SEED NSW Environmental Data Portal** (OPTIONAL)

**URL:** https://datasets.seed.nsw.gov.au/dataset/real-time-surface-water-quality-and-monitoring-data-storages-and-rivers

**Features:**
- Real-time surface water quality monitoring
- Storages and rivers data
- Open data platform (no authentication)
- CSV/JSON download available

**Use Cases:**
- Environmental water flow context
- Water quality alerts (if relevant for irrigation)
- Supplementary river health data

**Approach:**
- Download datasets as CSV
- Import to database for contextual data
- Not critical for MVP core functionality

**Priority:** Tier 3 - Nice to Have (Post-MVP)

---

#### **E. Bureau of Meteorology (BOM) - Weather Forecasts** (MODERATE PRIORITY)

**Weather API:** http://www.bom.gov.au/api/

**Already Using BOM for:**
- Dam levels (unofficial JSON endpoint)

**Additional BOM Data Sources:**
1. **Rainfall Forecasts**
   - Predict allocation increases
   - Alert farmers before rain events (pump water before flows rise)

2. **Seasonal Outlooks**
   - Long-term allocation predictions
   - Help farmers plan crop selection

3. **Evapotranspiration Data**
   - Crop water use calculations
   - Usage forecasting

**Approach:**
- Use BOM's unofficial JSON endpoints where available
- Fallback to web scraping for forecast data
- Consider official BOM API if partnership possible

**Priority:** Tier 2 - Should Have (Week 4-6)

---

#### **F. Water Sharing Plan Document Repository** (MODERATE PRIORITY)

**Already Included:**
- Murrumbidgee Water Sharing Plan: https://legislation.nsw.gov.au/view/whole/html/inforce/current/sl-2016-0435

**Additional Plans to Consider:**
1. **Other NSW Valleys** (for future expansion)
   - Lachlan: https://legislation.nsw.gov.au/view/whole/html/inforce/current/sl-2016-0225
   - Murray: https://legislation.nsw.gov.au/view/whole/html/inforce/current/sl-2016-0276
   - Namoi: https://legislation.nsw.gov.au/view/whole/html/inforce/current/sl-2016-0403

2. **Groundwater Plans** (if groundwater users in pilot)
   - Various NSW groundwater sharing plans

**Extraction Strategy:**
- HTML version easier to parse than PDF
- Use BeautifulSoup to extract:
  - Access rules (when extraction allowed)
  - Trading restrictions
  - Seasonal embargos
  - Environmental flow requirements
- Store as structured rules in database

**Priority:** Tier 1 - Must Have (Week 2-3) for Murrumbidgee
**Priority:** Tier 3 - Post-MVP for other valleys

---

#### **G. Additional Telemetry Data Sources**

**Government Telemetry Data Acquisition Service (DAS):**
- **Access:** Farmers, WaterNSW, NRAR can access telemetry data
- **Coverage:** All government-funded telemetry installations
- **Format:** Unknown - contact NRAR for API documentation
- **Value:** Central repository for all compliant meters (not just Observant)

**Contact for DAS API Access:**
- NRAR: https://www.nrar.nsw.gov.au/what-we-regulate/metering
- Email: nrar.enquiries@nrar.nsw.gov.au

**Priority:** Tier 2 - Should Have (Week 4-6)

---

### 11. Data Source Priority Matrix for MVP

#### **Tier 1 - Must Have (Week 1-3)**

| Data Source | Implementation | Value | Difficulty | Status |
|-------------|---------------|-------|------------|--------|
| **NSW DPIE Allocation Statements (PDF)** | PDF scraping | Core allocation data | Medium | Required |
| **DPIE Allocations Dashboard API** | Reverse-engineered API | Structured allocation data | Low | Try First |
| **WaterNSW Data API** | Official API | Stream levels, flows | Low | Register Week 1 |
| **BOM Dam Levels (JSON)** | Unofficial API | Dam storage data | Low | Easy Win |
| **Murrumbidgee Water Sharing Plan** | HTML parsing | Access rules, restrictions | Medium | Required |
| **iWAS Portal** | Manual entry fallback | Account balances | N/A | Manual Only |

**Week 1 Actions:**
1. ✅ Register for WaterNSW Data API (free, instant)
2. ✅ Test BOM dam levels JSON endpoint (no auth)
3. ✅ Attempt DPIE allocations dashboard reverse-engineered API
4. ✅ Download Murrumbidgee WSP HTML for parsing

---

#### **Tier 2 - Should Have (Week 4-6)**

| Data Source | Implementation | Value | Difficulty | Status |
|-------------|---------------|-------|------------|--------|
| **Observant API** | OAuth integration | Automated telemetry | Medium | Contact Sales Week 2 |
| **Government DAS** | API (if available) | Central telemetry repository | Unknown | Research Week 3 |
| **WaterExchange** | Web scraping | Market pricing | Medium | Week 4 |
| **Waterfind** | Web scraping | Market comparison | Medium | Week 4 |
| **WaterInsights** | Manual validation | Data verification | N/A | As Needed |
| **BOM Weather Forecasts** | API/scraping | Rainfall predictions | Medium | Week 5 |

**Week 4-6 Actions:**
1. 🔄 Integrate Observant API for pilot farmers with telemetry
2. 🔄 Build WaterExchange/Waterfind scrapers for market prices
3. 🔄 Research DAS API access via NRAR
4. 🔄 Add BOM weather forecasts to dashboard

---

#### **Tier 3 - Nice to Have (Post-MVP)**

| Data Source | Implementation | Value | Difficulty | Status |
|-------------|---------------|-------|------------|--------|
| **NRAR Compliance Register** | Web scraping | Educational context | Low | Post-MVP |
| **MDBA Basin Plan Data** | Manual/API | Long-term trends | Low | Post-MVP |
| **SEED Environmental Data** | CSV import | Water quality context | Low | Post-MVP |
| **Additional WSPs** | HTML parsing | Multi-valley expansion | Medium | Post-MVP |
| **Goanna Ag API** | OAuth integration | Alternative telemetry | Medium | If Demand |
| **ICT International** | Manual CSV upload | Alternative telemetry | Low | If Demand |

**Post-MVP Priorities:**
- Expand to other NSW valleys (Lachlan, Murray, Namoi)
- Add groundwater user support
- Integrate additional telemetry providers
- Advanced forecasting with MDBA data

---

### 12. Key Opportunities Identified

#### **Opportunity #1: Government Telemetry Program Partnership**
**Value:** Zero hardware costs, 2,500+ potential users
**Action:** Contact NSW Telemetry Uplift Program Week 2
**Target:** Farmers who received FREE telemetry installations in 2025
**Pitch:** "Your telemetry gives you the data. We give you the intelligence."

#### **Opportunity #2: Unofficial APIs for Structured Data**
**Value:** Avoid complex PDF parsing, faster development
**Sources:**
- BOM dam levels JSON endpoint (confirmed working, no auth)
- DPIE allocations dashboard API (reverse-engineered, test in Week 1)
**Benefit:** Week 1 data pipeline vs. Week 3 with PDF-only approach

#### **Opportunity #3: WaterNSW Official API (Free & Supported)**
**Value:** 760+ monitoring stations, 1,000 req/day, official support
**Action:** Register Week 1 at https://api-portal.waternsw.com.au/
**Use Case:** Supplementary flow alerts, allocation predictions
**ROI:** 1 request every 86 seconds = sufficient for 20 farmers

#### **Opportunity #4: CSV Export as PDF Alternative**
**Value:** DPIE dashboard has CSV export capability
**Benefit:** Much easier than PDF table extraction
**Strategy:** Use as Plan B if reverse-engineered API fails

---

### 13. Data Integration Roadmap

#### **Week 1: Foundation APIs (No Auth Required)**
```python
# Priority 1: Test these first
targets = [
    "http://www.bom.gov.au/water/dashboards/data/4132.json",  # Blowering Dam
    "http://www.bom.gov.au/water/dashboards/data/4128.json",  # Burrinjuck Dam
    "https://water.dpie.nsw.gov.au/api/allocations/current",   # Allocations (unofficial)
]

# Expected: 1 day to verify all working
# If successful: Build scrapers immediately
```

#### **Week 1-2: Official API Registration**
```python
# Register for these services
registrations = [
    "WaterNSW Data API Portal - FREE",
    "NSW Telemetry Uplift Program - Contact coordinator",
    "Observant API - Contact sales@observant.net",
]

# Expected: 3-5 business days for approvals
```

#### **Week 2-3: Core Data Pipeline**
```python
# Build scrapers/integrations for:
integrations = [
    "NSW DPIE Allocation Statements (PDF scraping)",
    "Murrumbidgee Water Sharing Plan (HTML parsing)",
    "WaterNSW API integration (stream flows)",
    "BOM JSON endpoints (dam levels)",
]

# Expected: 2 weeks for robust implementation
```

#### **Week 4-6: Enhanced Features**
```python
# Add value-added data sources:
enhancements = [
    "Observant API (telemetry for pilot farmers)",
    "WaterExchange/Waterfind (market pricing)",
    "BOM weather forecasts (rainfall predictions)",
    "Manual entry forms (farmer-submitted data)",
]

# Expected: 2-3 weeks for full integration
```

---

## Database Schema

### Complete PostgreSQL Schema for MVP

```sql
-- ============================================================================
-- WATERRIGHT MVP DATABASE SCHEMA
-- Target: Murrumbidgee Valley Pilot
-- PostgreSQL 14+ with PostGIS extension
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb; -- For time-series data

-- ============================================================================
-- 1. USER MANAGEMENT
-- ============================================================================

CREATE TABLE farmers (
    farmer_id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    phone_verified BOOLEAN DEFAULT FALSE,
    farm_name TEXT,
    farm_address TEXT,
    farm_location GEOMETRY(POINT, 4326), -- PostGIS for mapping

    -- Partnership tracking
    referred_by TEXT, -- 'murrumbidgee_irrigation', 'direct', etc.

    -- Account status
    account_status TEXT DEFAULT 'active', -- active, suspended, trial
    trial_end_date DATE,
    subscription_tier TEXT, -- 'base', 'pro', 'enterprise'

    -- Preferences
    alert_email BOOLEAN DEFAULT TRUE,
    alert_sms BOOLEAN DEFAULT TRUE,
    alert_push BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_farmers_email ON farmers(email);
CREATE INDEX idx_farmers_status ON farmers(account_status) WHERE account_status = 'active';

-- ============================================================================
-- 2. WATER ENTITLEMENTS
-- ============================================================================

CREATE TABLE water_sources (
    source_id SERIAL PRIMARY KEY,
    source_name TEXT UNIQUE NOT NULL, -- 'Murrumbidgee Regulated River'
    source_type TEXT NOT NULL,        -- 'regulated', 'unregulated', 'groundwater'
    state TEXT NOT NULL,              -- 'NSW'
    valley TEXT,                      -- 'Murrumbidgee'
    wsp_url TEXT,                     -- URL to Water Sharing Plan legislation
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pre-populate for MVP
INSERT INTO water_sources (source_name, source_type, state, valley, wsp_url) VALUES
('Murrumbidgee Regulated River', 'regulated', 'NSW', 'Murrumbidgee',
 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/sl-2016-0435');

CREATE TABLE allocation_categories (
    category_id SERIAL PRIMARY KEY,
    source_id INT NOT NULL REFERENCES water_sources(source_id),
    category_name TEXT NOT NULL, -- 'General Security', 'High Security', etc.
    category_code TEXT,          -- 'GS', 'HS', 'CONV'
    priority INT,                -- 1=highest (domestic), 5=lowest (general security)
    typical_reliability TEXT,    -- 'Average 60% per year'
    description TEXT,
    UNIQUE(source_id, category_name)
);

-- Pre-populate for Murrumbidgee
INSERT INTO allocation_categories (source_id, category_name, category_code, priority, typical_reliability)
SELECT
    source_id,
    unnest(ARRAY['High Security', 'General Security', 'Conveyance', 'Domestic and Stock']),
    unnest(ARRAY['HS', 'GS', 'CONV', 'DS']),
    unnest(ARRAY[2, 4, 3, 1]),
    unnest(ARRAY['95-100%', '50-70%', '100%', '100%'])
FROM water_sources WHERE source_name = 'Murrumbidgee Regulated River';

CREATE TABLE farmer_entitlements (
    entitlement_id SERIAL PRIMARY KEY,
    farmer_id INT NOT NULL REFERENCES farmers(farmer_id),
    source_id INT NOT NULL REFERENCES water_sources(source_id),
    category_id INT NOT NULL REFERENCES allocation_categories(category_id),

    -- Entitlement details
    volume_ML FLOAT NOT NULL,     -- e.g., 800 ML
    wal_number TEXT,              -- Water Access License number (NSW format: 12AB345678)
    wal_share_component TEXT,     -- Share component details

    -- Extraction point
    extraction_location GEOMETRY(POINT, 4326), -- Where pump/bore is located
    extraction_method TEXT,       -- 'pump', 'gravity', 'bore'

    -- Status
    active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_farmer_entitlements_farmer ON farmer_entitlements(farmer_id) WHERE active = TRUE;
CREATE INDEX idx_farmer_entitlements_source_cat ON farmer_entitlements(source_id, category_id);

-- ============================================================================
-- 3. ALLOCATION ANNOUNCEMENTS (Time-Series)
-- ============================================================================

CREATE TABLE allocation_announcements (
    announcement_id SERIAL PRIMARY KEY,
    source_id INT NOT NULL REFERENCES water_sources(source_id),
    category_id INT NOT NULL REFERENCES allocation_categories(category_id),

    -- Allocation data
    allocation_pct FLOAT NOT NULL,  -- 0-100 (e.g., 45 for 45%)
    announced_date DATE NOT NULL,
    water_year INT NOT NULL,        -- 2024 for 2024-25 water year (Jul-Jun)

    -- Context from statement
    dam_levels JSONB,               -- {'Blowering': 67.2, 'Burrinjuck': 82.1}
    inflows_GL FLOAT,
    rainfall_mm FLOAT,
    commentary TEXT,                -- Free text from PDF
    next_review_date DATE,

    -- Metadata
    statement_pdf_url TEXT,
    scraped_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(source_id, category_id, announced_date)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('allocation_announcements', 'announced_date', if_not_exists => TRUE);

CREATE INDEX idx_allocation_current ON allocation_announcements(source_id, category_id, announced_date DESC);

-- Materialized view for latest allocations (performance optimization)
CREATE MATERIALIZED VIEW latest_allocations AS
SELECT DISTINCT ON (source_id, category_id)
    source_id,
    category_id,
    allocation_pct,
    announced_date,
    dam_levels,
    next_review_date
FROM allocation_announcements
ORDER BY source_id, category_id, announced_date DESC;

CREATE UNIQUE INDEX idx_latest_allocations ON latest_allocations(source_id, category_id);

-- Refresh function (call after new announcements scraped)
CREATE OR REPLACE FUNCTION refresh_latest_allocations()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY latest_allocations;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 4. WATER USAGE TRACKING
-- ============================================================================

-- Telemetry meter readings (time-series)
CREATE TABLE telemetry_readings (
    reading_id BIGSERIAL PRIMARY KEY,
    entitlement_id INT NOT NULL REFERENCES farmer_entitlements(entitlement_id),

    -- Meter identification
    meter_id TEXT NOT NULL,           -- Unique ID from telemetry provider
    meter_provider TEXT NOT NULL,     -- 'observant', 'goanna_ag', 'ict_international'

    -- Reading data
    reading_timestamp TIMESTAMP NOT NULL,
    cumulative_volume_ML FLOAT NOT NULL, -- Total since meter installation
    flow_rate_L_per_sec FLOAT,

    -- Telemetry metadata
    battery_voltage FLOAT,
    signal_strength_dbm INT,
    data_quality TEXT,                -- 'good', 'suspect', 'estimated'

    -- System metadata
    synced_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(meter_id, reading_timestamp)
);

-- Convert to hypertable
SELECT create_hypertable('telemetry_readings', 'reading_timestamp', if_not_exists => TRUE);

CREATE INDEX idx_telemetry_entitlement ON telemetry_readings(entitlement_id, reading_timestamp DESC);
CREATE INDEX idx_telemetry_meter ON telemetry_readings(meter_id, reading_timestamp DESC);

-- Meter configuration
CREATE TABLE telemetry_config (
    config_id SERIAL PRIMARY KEY,
    farmer_id INT NOT NULL REFERENCES farmers(farmer_id),
    entitlement_id INT NOT NULL REFERENCES farmer_entitlements(entitlement_id),

    -- Provider details
    provider TEXT NOT NULL,           -- 'observant', 'goanna_ag'
    meter_id TEXT NOT NULL,
    api_key TEXT,                     -- Encrypted
    account_id TEXT,
    username TEXT,
    password TEXT,                    -- Encrypted

    -- Sync settings
    sync_enabled BOOLEAN DEFAULT TRUE,
    sync_frequency_minutes INT DEFAULT 60,
    last_sync_at TIMESTAMP,
    last_sync_status TEXT,            -- 'success', 'failed', 'rate_limited'

    -- Baseline reading (for calculating usage-to-date)
    baseline_reading_ML FLOAT,        -- Meter reading on July 1 (water year start)
    baseline_date DATE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Manual usage entries (for non-telemetry farmers)
CREATE TABLE manual_usage_entries (
    entry_id SERIAL PRIMARY KEY,
    farmer_id INT NOT NULL REFERENCES farmers(farmer_id),
    entitlement_id INT NOT NULL REFERENCES farmer_entitlements(entitlement_id),

    -- Entry data
    usage_date DATE NOT NULL,
    volume_ML FLOAT NOT NULL,
    purpose TEXT,                     -- 'Irrigated rice paddock 5'
    meter_reading_ML FLOAT,           -- Optional cumulative reading

    -- Metadata
    entry_method TEXT DEFAULT 'manual', -- 'manual', 'csv_upload'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_manual_usage_farmer ON manual_usage_entries(farmer_id, usage_date DESC);
CREATE INDEX idx_manual_usage_entitlement ON manual_usage_entries(entitlement_id, usage_date DESC);

-- ============================================================================
-- 5. COMPLIANCE ALERTS
-- ============================================================================

CREATE TABLE alert_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name TEXT UNIQUE NOT NULL,
    rule_type TEXT NOT NULL,          -- 'allocation_limit', 'restriction', 'deadline'

    -- Condition (SQL expression)
    condition_sql TEXT NOT NULL,

    -- Alert configuration
    priority TEXT NOT NULL,           -- 'critical', 'warning', 'info'
    message_template TEXT NOT NULL,   -- Jinja2 template with variables
    action_recommendations JSONB,

    -- Delivery settings
    send_sms BOOLEAN DEFAULT FALSE,
    send_email BOOLEAN DEFAULT TRUE,
    send_push BOOLEAN DEFAULT TRUE,

    -- Throttling (prevent spam)
    min_hours_between_alerts INT DEFAULT 24,

    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pre-populate MVP rules
INSERT INTO alert_rules (rule_name, rule_type, condition_sql, priority, message_template, send_sms)
VALUES
(
    'Allocation Limit 80%',
    'allocation_limit',
    'pct_used >= 80 AND pct_used < 90',
    'warning',
    'You have used {{ pct_used|round(0) }}% of your {{ category_name }} allocation ({{ used_ML|round(0) }} ML of {{ allocation_ML|round(0) }} ML). You have {{ remaining_ML|round(0) }} ML remaining.',
    FALSE
),
(
    'Allocation Limit 90%',
    'allocation_limit',
    'pct_used >= 90 AND pct_used < 100',
    'warning',
    'You have used {{ pct_used|round(0) }}% of your {{ category_name }} allocation. At current usage rate, you will exceed allocation in {{ days_until_exceed }} days. Consider purchasing temporary water or reducing irrigation.',
    TRUE
),
(
    'Overdrawn Account',
    'overdrawn',
    'remaining_ML < 0',
    'critical',
    'COMPLIANCE VIOLATION: Your {{ category_name }} account is overdrawn by {{ (remaining_ML * -1)|round(1) }} ML. You must purchase water or cease extractions within 60 days. Penalty: Up to $264,000.',
    TRUE
),
(
    'Telemetry Offline',
    'telemetry_failure',
    'last_reading_hours > 48 AND entitlement_volume_ML >= 100',
    'critical',
    'Your water meter ({{ meter_id }}) has not transmitted data for {{ last_reading_hours }} hours. NRAR requires operational telemetry for entitlements ≥100 ML. Check meter battery/connectivity immediately.',
    TRUE
);

CREATE TABLE farmer_alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    farmer_id INT NOT NULL REFERENCES farmers(farmer_id),
    rule_id INT NOT NULL REFERENCES alert_rules(rule_id),
    entitlement_id INT REFERENCES farmer_entitlements(entitlement_id),

    -- Alert content
    priority TEXT NOT NULL,
    message TEXT NOT NULL,
    recommendations JSONB,

    -- Context snapshot (for historical reference)
    context JSONB,                    -- Allocation, usage, percentages at time of alert

    -- Delivery tracking
    sent_sms BOOLEAN DEFAULT FALSE,
    sent_sms_at TIMESTAMP,
    sent_email BOOLEAN DEFAULT FALSE,
    sent_email_at TIMESTAMP,
    sent_push BOOLEAN DEFAULT FALSE,
    sent_push_at TIMESTAMP,

    -- Farmer action
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    action_taken TEXT,                -- 'purchased_water', 'reduced_irrigation', 'other'
    action_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_farmer_alerts_farmer_unack ON farmer_alerts(farmer_id, created_at DESC)
WHERE acknowledged = FALSE;

CREATE INDEX idx_farmer_alerts_created ON farmer_alerts(created_at DESC);

-- ============================================================================
-- 6. WATER SHARING PLAN RESTRICTIONS
-- ============================================================================

CREATE TABLE wsp_restrictions (
    restriction_id SERIAL PRIMARY KEY,
    source_id INT NOT NULL REFERENCES water_sources(source_id),
    category_id INT REFERENCES allocation_categories(category_id), -- NULL = applies to all

    -- Restriction details
    restriction_type TEXT NOT NULL,   -- 'seasonal_embargo', 'flow_based', 'environmental'
    restriction_code TEXT,            -- 'WSP_MUR_46' (Water Sharing Plan Murrumbidgee, Section 46)

    -- Temporal constraints
    start_date_mmdd TEXT,             -- '01-01' (Jan 1)
    end_date_mmdd TEXT,               -- '03-31' (Mar 31)

    -- Conditional triggers
    condition_description TEXT,       -- 'Blowering Dam < 30% on Dec 1'
    condition_sql TEXT,               -- SQL to evaluate condition

    -- Restriction effect
    extraction_allowed BOOLEAN DEFAULT FALSE,
    description TEXT NOT NULL,
    legal_reference TEXT,             -- 'Murrumbidgee Water Sharing Plan 2016, Section 46'
    penalty_description TEXT,

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pre-populate with key Murrumbidgee restrictions
INSERT INTO wsp_restrictions (source_id, category_id, restriction_type, restriction_code,
                              start_date_mmdd, end_date_mmdd, condition_description,
                              extraction_allowed, description, legal_reference)
SELECT
    ws.source_id,
    ac.category_id,
    'seasonal_embargo',
    'WSP_MUR_46',
    '01-01',
    '03-31',
    'Blowering Dam storage < 30% on December 1',
    FALSE,
    'No water may be taken under a General Security access licence during the period from 1 January to 31 March in any year when the storage volume in Blowering Dam is less than 30% on 1 December of the preceding year.',
    'Water Sharing Plan for the Murrumbidgee Regulated River Water Source 2016, Section 46'
FROM water_sources ws
JOIN allocation_categories ac ON ws.source_id = ac.source_id
WHERE ws.source_name = 'Murrumbidgee Regulated River'
  AND ac.category_name = 'General Security';

-- ============================================================================
-- 7. SUPPLEMENTARY ACCESS EVENTS
-- ============================================================================

CREATE TABLE supplementary_events (
    event_id SERIAL PRIMARY KEY,
    source_id INT NOT NULL REFERENCES water_sources(source_id),

    -- Event timing
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    announced_at TIMESTAMP DEFAULT NOW(),

    -- Flow conditions
    flow_trigger_ML_per_day FLOAT,   -- River flow that triggered event
    measuring_station TEXT,           -- 'Wagga Wagga weir'

    -- Event details
    event_type TEXT,                  -- 'flood_flow', 'environmental_release'
    conditions TEXT,                  -- 'Environmental flows satisfied, high inflows'
    extraction_window_hours INT,      -- Typical 24-72 hours

    -- Announcement source
    announcement_url TEXT,
    announcement_pdf TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_supplementary_events_active ON supplementary_events(source_id, end_time)
WHERE end_time > NOW();

-- ============================================================================
-- 8. AUDIT LOG
-- ============================================================================

CREATE TABLE audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    farmer_id INT REFERENCES farmers(farmer_id),

    -- Event details
    event_type TEXT NOT NULL,         -- 'login', 'usage_entry', 'alert_acknowledged'
    event_data JSONB,
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_log_farmer ON audit_log(farmer_id, created_at DESC);
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);

-- ============================================================================
-- 9. SYSTEM CONFIGURATION
-- ============================================================================

CREATE TABLE system_config (
    config_key TEXT PRIMARY KEY,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Pre-populate
INSERT INTO system_config (config_key, config_value, description) VALUES
('scraping_schedule', '{"allocation_statements": "0 6 * * *", "supplementary_events": "0 * * * *"}', 'Cron expressions for scraping jobs'),
('alert_throttling', '{"critical": 0, "warning": 24, "info": 168}', 'Minimum hours between alerts by priority'),
('telemetry_sync_default_minutes', '60', 'Default sync frequency for telemetry'),
('water_year_start', '{"month": 7, "day": 1}', 'Water year starts July 1');

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Calculate farmer's current allocation for an entitlement
CREATE OR REPLACE FUNCTION get_current_allocation_ML(p_entitlement_id INT)
RETURNS FLOAT AS $$
DECLARE
    v_entitlement_volume_ML FLOAT;
    v_allocation_pct FLOAT;
BEGIN
    -- Get entitlement volume
    SELECT volume_ML INTO v_entitlement_volume_ML
    FROM farmer_entitlements
    WHERE entitlement_id = p_entitlement_id;

    -- Get latest allocation percentage
    SELECT la.allocation_pct INTO v_allocation_pct
    FROM farmer_entitlements fe
    JOIN latest_allocations la ON fe.source_id = la.source_id
                               AND fe.category_id = la.category_id
    WHERE fe.entitlement_id = p_entitlement_id;

    -- Return allocation in ML
    RETURN v_entitlement_volume_ML * (v_allocation_pct / 100.0);
END;
$$ LANGUAGE plpgsql;

-- Calculate usage to date (since July 1) for an entitlement
CREATE OR REPLACE FUNCTION get_usage_to_date_ML(p_entitlement_id INT)
RETURNS FLOAT AS $$
DECLARE
    v_water_year_start DATE;
    v_usage_ML FLOAT := 0;
    v_has_telemetry BOOLEAN;
BEGIN
    -- Determine water year start
    IF EXTRACT(MONTH FROM CURRENT_DATE) >= 7 THEN
        v_water_year_start := DATE_TRUNC('year', CURRENT_DATE) + INTERVAL '6 months';
    ELSE
        v_water_year_start := DATE_TRUNC('year', CURRENT_DATE) - INTERVAL '6 months';
    END IF;

    -- Check if entitlement has telemetry
    SELECT EXISTS(
        SELECT 1 FROM telemetry_config
        WHERE entitlement_id = p_entitlement_id AND sync_enabled = TRUE
    ) INTO v_has_telemetry;

    IF v_has_telemetry THEN
        -- Calculate from telemetry
        SELECT
            COALESCE(MAX(cumulative_volume_ML), 0) -
            COALESCE(MIN(cumulative_volume_ML), 0)
        INTO v_usage_ML
        FROM telemetry_readings
        WHERE entitlement_id = p_entitlement_id
          AND reading_timestamp >= v_water_year_start;
    ELSE
        -- Sum manual entries
        SELECT COALESCE(SUM(volume_ML), 0)
        INTO v_usage_ML
        FROM manual_usage_entries
        WHERE entitlement_id = p_entitlement_id
          AND usage_date >= v_water_year_start;
    END IF;

    RETURN v_usage_ML;
END;
$$ LANGUAGE plpgsql;

-- Get compliance status for an entitlement
CREATE OR REPLACE FUNCTION get_compliance_status(p_entitlement_id INT)
RETURNS TABLE(
    allocation_ML FLOAT,
    used_ML FLOAT,
    remaining_ML FLOAT,
    pct_used FLOAT,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        get_current_allocation_ML(p_entitlement_id) AS allocation_ML,
        get_usage_to_date_ML(p_entitlement_id) AS used_ML,
        get_current_allocation_ML(p_entitlement_id) - get_usage_to_date_ML(p_entitlement_id) AS remaining_ML,
        CASE
            WHEN get_current_allocation_ML(p_entitlement_id) > 0 THEN
                (get_usage_to_date_ML(p_entitlement_id) / get_current_allocation_ML(p_entitlement_id)) * 100
            ELSE 0
        END AS pct_used,
        CASE
            WHEN get_usage_to_date_ML(p_entitlement_id) > get_current_allocation_ML(p_entitlement_id) THEN 'over_allocated'
            WHEN (get_usage_to_date_ML(p_entitlement_id) / NULLIF(get_current_allocation_ML(p_entitlement_id), 0)) > 0.9 THEN 'near_limit'
            ELSE 'compliant'
        END AS status;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE DATA (for development/testing)
-- ============================================================================

-- Create test farmer
INSERT INTO farmers (email, password_hash, first_name, last_name, phone, farm_name, farm_location)
VALUES (
    'john.farmer@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS8qB.iu6', -- password: 'test123'
    'John',
    'Farmer',
    '+61400123456',
    'Farmer Family Orchards',
    ST_SetSRID(ST_MakePoint(147.3678, -34.7589), 4326) -- Griffith, NSW
);

-- Create test entitlements
INSERT INTO farmer_entitlements (farmer_id, source_id, category_id, volume_ML, wal_number)
SELECT
    (SELECT farmer_id FROM farmers WHERE email = 'john.farmer@example.com'),
    ws.source_id,
    ac.category_id,
    800,
    '12AB345678'
FROM water_sources ws
JOIN allocation_categories ac ON ws.source_id = ac.source_id
WHERE ws.source_name = 'Murrumbidgee Regulated River'
  AND ac.category_name = 'General Security';

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Already created inline above, but documenting here for reference:
-- - idx_farmers_email
-- - idx_farmers_status
-- - idx_farmer_entitlements_farmer
-- - idx_allocation_current
-- - idx_telemetry_entitlement
-- - idx_manual_usage_farmer
-- - idx_farmer_alerts_farmer_unack
-- - All hypertable indexes created automatically

-- ============================================================================
-- BACKUP & MAINTENANCE
-- ============================================================================

-- Daily backup script (run via cron)
-- pg_dump -h localhost -U postgres -d waterright -F c -f /backups/waterright_$(date +%Y%m%d).backup

-- Weekly vacuum
-- VACUUM ANALYZE;

-- Monthly analyze
-- ANALYZE;
```

---

## Backend Architecture

### Technology Stack

**Core:**
- **Python 3.11+**
- **FastAPI** (API framework)
- **PostgreSQL 14+** with PostGIS + TimescaleDB extensions
- **SQLAlchemy 2.0** (ORM)
- **Pydantic 2.0** (data validation)

**Task Queue:**
- **Celery** (background jobs - scraping, alert evaluation)
- **Redis** (Celery broker + caching)

**Scraping:**
- **httpx** (async HTTP client)
- **pdfplumber** (PDF parsing - reuse from planning platform)
- **BeautifulSoup4** (HTML parsing)
- **Playwright** (browser automation for iWAS scraping - if needed)

**Authentication:**
- **python-jose** (JWT tokens)
- **passlib** (password hashing - bcrypt)

**Monitoring:**
- **Sentry** (error tracking)
- **Prometheus** (metrics)

---

### Project Structure

```
waterright-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Configuration (env vars)
│   ├── database.py                # Database connection
│   │
│   ├── models/                    # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── farmer.py
│   │   ├── entitlement.py
│   │   ├── allocation.py
│   │   ├── usage.py
│   │   └── alert.py
│   │
│   ├── schemas/                   # Pydantic schemas (API validation)
│   │   ├── __init__.py
│   │   ├── farmer.py
│   │   ├── allocation.py
│   │   └── usage.py
│   │
│   ├── api/                       # API routes
│   │   ├── __init__.py
│   │   ├── auth.py               # Login, register
│   │   ├── allocations.py         # Allocation endpoints
│   │   ├── usage.py               # Usage tracking endpoints
│   │   ├── alerts.py              # Alert management
│   │   └── admin.py               # Admin endpoints
│   │
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── allocation_service.py  # Allocation calculations
│   │   ├── usage_service.py       # Usage tracking
│   │   ├── compliance_service.py  # Alert evaluation
│   │   ├── telemetry_service.py   # Telemetry integrations
│   │   └── notification_service.py # SMS/Email/Push
│   │
│   ├── scrapers/                  # Data collection
│   │   ├── __init__.py
│   │   ├── nsw_dpie_scraper.py   # Allocation statements
│   │   ├── iwas_scraper.py        # iWAS account balance
│   │   └── bom_scraper.py         # Dam levels
│   │
│   ├── tasks/                     # Celery tasks
│   │   ├── __init__.py
│   │   ├── scraping_tasks.py      # Daily scraping jobs
│   │   ├── telemetry_tasks.py     # Hourly telemetry sync
│   │   └── alert_tasks.py         # Hourly alert evaluation
│   │
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── security.py            # JWT, password hashing
│       ├── pdf_parser.py          # PDF extraction (reuse from planning)
│       └── sms.py                 # Twilio integration
│
├── tests/
│   ├── __init__.py
│   ├── test_allocations.py
│   ├── test_usage.py
│   └── test_alerts.py
│
├── migrations/                     # Alembic database migrations
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
│
├── requirements.txt
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## API Routes Specification

### Base URL: `http://localhost:8000/api/v1`

---

### 1. Authentication

#### `POST /auth/register`

**Request:**
```json
{
  "email": "john.farmer@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Farmer",
  "phone": "+61400123456",
  "farm_name": "Farmer Family Orchards"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "farmer_id": 1,
    "email": "john.farmer@example.com",
    "first_name": "John",
    "last_name": "Farmer",
    "account_status": "trial",
    "trial_end_date": "2025-03-16"
  },
  "message": "Account created successfully. Trial period: 3 months."
}
```

---

#### `POST /auth/login`

**Request:**
```json
{
  "email": "john.farmer@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "farmer": {
      "farmer_id": 1,
      "email": "john.farmer@example.com",
      "first_name": "John",
      "subscription_tier": "base"
    }
  }
}
```

---

### 2. Entitlements

#### `POST /entitlements`

**Create new entitlement (during onboarding)**

**Request:**
```json
{
  "source_name": "Murrumbidgee Regulated River",
  "category_name": "General Security",
  "volume_ML": 800,
  "wal_number": "12AB345678"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "entitlement_id": 1,
    "source_name": "Murrumbidgee Regulated River",
    "category_name": "General Security",
    "volume_ML": 800,
    "wal_number": "12AB345678"
  }
}
```

---

#### `GET /entitlements`

**Get farmer's entitlements**

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "entitlement_id": 1,
      "source_name": "Murrumbidgee Regulated River",
      "category_name": "General Security",
      "volume_ML": 800,
      "wal_number": "12AB345678",
      "active": true
    },
    {
      "entitlement_id": 2,
      "source_name": "Murrumbidgee Regulated River",
      "category_name": "High Security",
      "volume_ML": 200,
      "wal_number": "12AB345679",
      "active": true
    }
  ]
}
```

---

### 3. Allocations

#### `GET /allocations/summary`

**Get allocation summary for all entitlements**

**Response:**
```json
{
  "success": true,
  "data": {
    "total_allocation_ML": 450,
    "total_used_ML": 275,
    "total_remaining_ML": 175,
    "pct_used": 61.1,
    "status": "compliant",
    "updated_at": "2024-12-16T14:30:00Z",
    "entitlements": [
      {
        "entitlement_id": 1,
        "source_name": "Murrumbidgee Regulated River",
        "category_name": "General Security",
        "entitlement_ML": 800,
        "allocation_pct": 45,
        "allocation_ML": 360,
        "used_ML": 220,
        "remaining_ML": 140,
        "pct_used": 61.1,
        "status": "compliant"
      },
      {
        "entitlement_id": 2,
        "source_name": "Murrumbidgee Regulated River",
        "category_name": "High Security",
        "entitlement_ML": 200,
        "allocation_pct": 95,
        "allocation_ML": 190,
        "used_ML": 50,
        "remaining_ML": 140,
        "pct_used": 26.3,
        "status": "compliant"
      }
    ]
  }
}
```

---

#### `GET /allocations/history`

**Get allocation history for an entitlement**

**Query Params:**
- `entitlement_id`: Integer (required)
- `start_date`: ISO date (optional, default: water year start)
- `end_date`: ISO date (optional, default: today)

**Example:** `/allocations/history?entitlement_id=1&start_date=2024-07-01&end_date=2024-12-16`

**Response:**
```json
{
  "success": true,
  "data": {
    "entitlement_id": 1,
    "source_name": "Murrumbidgee Regulated River",
    "category_name": "General Security",
    "history": [
      {
        "announced_date": "2024-12-16",
        "allocation_pct": 45,
        "allocation_ML": 360,
        "dam_levels": {
          "Blowering": 67.2,
          "Burrinjuck": 82.1
        }
      },
      {
        "announced_date": "2024-12-02",
        "allocation_pct": 40,
        "allocation_ML": 320,
        "dam_levels": {
          "Blowering": 65.8,
          "Burrinjuck": 80.5
        }
      },
      // ... more historical announcements
    ],
    "comparison": {
      "current_year": 45,
      "last_year_same_date": 38,
      "five_year_average": 52
    }
  }
}
```

---

#### `GET /allocations/announcements`

**Get recent allocation announcements (feed)**

**Query Params:**
- `limit`: Integer (default: 10)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "announcement_id": 123,
      "source_name": "Murrumbidgee Regulated River",
      "announced_date": "2024-12-16",
      "categories": [
        {
          "category_name": "General Security",
          "allocation_pct": 45,
          "change_from_previous": 5,
          "trend": "up"
        },
        {
          "category_name": "High Security",
          "allocation_pct": 95,
          "change_from_previous": 0,
          "trend": "unchanged"
        }
      ],
      "highlights": [
        "Improved inflows from recent rainfall",
        "Blowering Dam at 67% capacity",
        "Next review: Jan 2, 2025"
      ],
      "statement_pdf_url": "https://water.dpie.nsw.gov.au/.../murrumbidgee-2024-12-16.pdf"
    }
  ]
}
```

---

### 4. Usage Tracking

#### `POST /usage/manual-entry`

**Log manual water usage**

**Request:**
```json
{
  "entitlement_id": 1,
  "usage_date": "2024-12-15",
  "volume_ML": 25.5,
  "purpose": "Irrigated rice paddock 5 (50 hectares)",
  "meter_reading_ML": 275.5
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "entry_id": 456,
    "entitlement_id": 1,
    "usage_date": "2024-12-15",
    "volume_ML": 25.5,
    "new_total_used": 245.5,
    "remaining_allocation": 114.5
  },
  "warning": null
}
```

**Response (if exceeds allocation):**
```json
{
  "success": true,
  "data": { ... },
  "warning": "This entry will put you over allocation (455 ML used > 450 ML allocated). You may face compliance action."
}
```

---

#### `GET /usage/history`

**Get usage history for entitlement**

**Query Params:**
- `entitlement_id`: Integer (required)
- `start_date`: ISO date (optional)
- `end_date`: ISO date (optional)
- `granularity`: "daily" | "monthly" (default: "daily")

**Response:**
```json
{
  "success": true,
  "data": {
    "entitlement_id": 1,
    "total_used_ML": 275,
    "period": {
      "start": "2024-07-01",
      "end": "2024-12-16"
    },
    "usage": [
      {
        "date": "2024-12-15",
        "volume_ML": 5.2,
        "source": "telemetry",
        "purpose": null
      },
      {
        "date": "2024-12-14",
        "volume_ML": 4.8,
        "source": "telemetry",
        "purpose": null
      },
      // ... more entries
    ],
    "monthly_summary": [
      {
        "month": "2024-12",
        "volume_ML": 75,
        "days_with_usage": 15,
        "avg_daily_ML": 5.0
      },
      {
        "month": "2024-11",
        "volume_ML": 80,
        "days_with_usage": 20,
        "avg_daily_ML": 4.0
      }
    ]
  }
}
```

---

#### `POST /usage/telemetry/configure`

**Configure telemetry integration**

**Request:**
```json
{
  "entitlement_id": 1,
  "provider": "observant",
  "meter_id": "OBS12345",
  "api_key": "obs_live_abc123...",
  "account_id": "12345"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "config_id": 789,
    "provider": "observant",
    "meter_id": "OBS12345",
    "sync_enabled": true,
    "last_sync_status": "pending"
  },
  "message": "Telemetry configured. First sync will occur within 1 hour."
}
```

---

#### `POST /usage/telemetry/sync-now`

**Manually trigger telemetry sync**

**Request:**
```json
{
  "entitlement_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "readings_fetched": 24,
    "latest_reading": {
      "timestamp": "2024-12-16T14:30:00Z",
      "cumulative_volume_ML": 275.3,
      "flow_rate_L_per_sec": 15.2
    },
    "sync_status": "success"
  }
}
```

---

### 5. Compliance & Alerts

#### `GET /alerts`

**Get farmer's active alerts**

**Query Params:**
- `status`: "all" | "unacknowledged" | "acknowledged" (default: "unacknowledged")
- `priority`: "critical" | "warning" | "info" (optional filter)

**Response:**
```json
{
  "success": true,
  "data": {
    "unacknowledged_count": 2,
    "alerts": [
      {
        "alert_id": 101,
        "priority": "warning",
        "rule_name": "Allocation Limit 90%",
        "message": "You have used 90% of your General Security allocation (405 ML of 450 ML). At current usage rate, you will exceed allocation in 9 days.",
        "recommendations": [
          {
            "action": "Purchase 50 ML temporary water",
            "detail": "Current market: $180/ML = $9,000",
            "link": "https://waterexchange.com.au/buy?valley=murr&category=gs&volume=50"
          },
          {
            "action": "Reduce irrigation to 2 ML/day",
            "detail": "Extend allocation by 15 days"
          }
        ],
        "context": {
          "category_name": "General Security",
          "used_ML": 405,
          "allocation_ML": 450,
          "remaining_ML": 45,
          "pct_used": 90
        },
        "created_at": "2024-12-16T08:00:00Z",
        "acknowledged": false
      }
    ]
  }
}
```

---

#### `POST /alerts/{alert_id}/acknowledge`

**Acknowledge an alert**

**Request:**
```json
{
  "action_taken": "purchased_water",
  "action_notes": "Purchased 50 ML via WaterExchange"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "alert_id": 101,
    "acknowledged": true,
    "acknowledged_at": "2024-12-16T15:00:00Z"
  }
}
```

---

#### `GET /compliance/calendar`

**Get upcoming compliance deadlines**

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "event_type": "seasonal_embargo",
      "title": "Extraction Embargo Begins",
      "date": "2025-01-01",
      "days_until": 16,
      "description": "No extractions allowed for General Security Jan 1 - Mar 31",
      "action_required": "Ensure sufficient water ordered before Dec 31",
      "applies_to": [
        {
          "entitlement_id": 1,
          "category_name": "General Security"
        }
      ]
    },
    {
      "event_type": "water_year_end",
      "title": "Water Year End - Account Must Be Positive",
      "date": "2025-06-30",
      "days_until": 197,
      "description": "If account is negative on Jun 30, penalties apply",
      "current_status": "on_track",
      "current_balance_ML": 45
    }
  ]
}
```

---

### 6. Admin/System

#### `GET /admin/scraping/status`

**Get scraping job status (admin only)**

**Response:**
```json
{
  "success": true,
  "data": {
    "allocation_statements": {
      "last_run": "2024-12-16T06:00:00Z",
      "status": "success",
      "announcements_found": 7,
      "next_run": "2024-12-17T06:00:00Z"
    },
    "telemetry_sync": {
      "last_run": "2024-12-16T14:00:00Z",
      "status": "success",
      "farmers_synced": 18,
      "readings_fetched": 432,
      "next_run": "2024-12-16T15:00:00Z"
    }
  }
}
```

---

#### `POST /admin/scraping/trigger`

**Manually trigger scraping job (admin)**

**Request:**
```json
{
  "job_type": "allocation_statements"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "scrape_alloc_20241216_150000",
    "status": "running",
    "message": "Scraping job started. Check /admin/scraping/status in 2-3 minutes."
  }
}
```

---

## Frontend Components

### Technology Stack

**Framework:**
- **Next.js 14** (App Router)
- **React 18**
- **TypeScript 5**

**UI:**
- **Tailwind CSS** (styling)
- **Shadcn/UI** (component library - reuse from planning platform)
- **Recharts** (charts/graphs)
- **React Hook Form** (forms)

**State Management:**
- **TanStack Query (React Query)** (server state)
- **Zustand** (client state - if needed)

---

### Component Structure

```
waterright-frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── register/
│   │       └── page.tsx
│   │
│   ├── (dashboard)/
│   │   ├── layout.tsx            # Dashboard shell (nav, sidebar)
│   │   ├── page.tsx               # Dashboard home
│   │   ├── allocations/
│   │   │   └── page.tsx
│   │   ├── usage/
│   │   │   └── page.tsx
│   │   └── alerts/
│   │       └── page.tsx
│   │
│   └── api/                       # API route handlers (proxy to backend)
│       ├── auth/
│       │   └── route.ts
│       └── allocations/
│           └── route.ts
│
├── components/
│   ├── allocations/
│   │   ├── AllocationSummaryCard.tsx
│   │   ├── AllocationHistoryChart.tsx
│   │   ├── EntitlementBreakdown.tsx
│   │   └── AnnouncementFeed.tsx
│   │
│   ├── usage/
│   │   ├── ManualEntryForm.tsx
│   │   ├── UsageHistoryChart.tsx
│   │   └── TelemetrySetup.tsx
│   │
│   ├── alerts/
│   │   ├── AlertList.tsx
│   │   ├── AlertCard.tsx
│   │   └── ComplianceCalendar.tsx
│   │
│   └── shared/
│       ├── ProgressBar.tsx
│       ├── StatusBadge.tsx
│       └── DashboardShell.tsx
│
├── lib/
│   ├── api-client.ts             # Axios/fetch wrapper
│   ├── auth.ts                   # Auth helpers
│   └── utils.ts                  # Utilities
│
├── hooks/
│   ├── useAllocations.ts         # React Query hook
│   ├── useUsage.ts
│   └── useAlerts.ts
│
└── types/
    ├── allocation.ts
    ├── usage.ts
    └── alert.ts
```

---

### Key Component Examples

#### `components/allocations/AllocationSummaryCard.tsx`

```typescript
'use client';

import { useAllocations } from '@/hooks/useAllocations';
import { ProgressBar } from '@/components/shared/ProgressBar';
import { StatusBadge } from '@/components/shared/StatusBadge';

export function AllocationSummaryCard() {
  const { data: summary, isLoading, error } = useAllocations();

  if (isLoading) {
    return <div className="animate-pulse">Loading...</div>;
  }

  if (error || !summary) {
    return <div className="text-red-600">Failed to load allocation data</div>;
  }

  const { total_allocation_ML, total_used_ML, total_remaining_ML, pct_used, status } = summary.data;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">💧 Water Account Summary</h2>
        <span className="text-sm text-gray-500">Updated: 15 min ago</span>
      </div>

      <div className="bg-blue-50 rounded-lg p-6">
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <p className="text-sm text-gray-600">Total Allocation</p>
            <p className="text-3xl font-bold">{total_allocation_ML.toFixed(0)} ML</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Used to Date</p>
            <p className="text-3xl font-bold">{total_used_ML.toFixed(0)} ML</p>
            <p className="text-sm text-gray-500">({pct_used.toFixed(0)}%)</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Remaining</p>
            <p className="text-3xl font-bold text-green-600">
              {total_remaining_ML.toFixed(0)} ML
            </p>
            <p className="text-sm text-gray-500">({(100 - pct_used).toFixed(0)}%)</p>
          </div>
        </div>

        <ProgressBar value={pct_used} className="mb-4" />

        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">Status:</span>
          <StatusBadge status={status} />
        </div>
      </div>
    </div>
  );
}
```

---

#### `components/shared/ProgressBar.tsx`

```typescript
interface ProgressBarProps {
  value: number; // 0-100
  className?: string;
}

export function ProgressBar({ value, className }: ProgressBarProps) {
  const getColor = (val: number) => {
    if (val > 90) return 'bg-red-500';
    if (val > 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className={`w-full bg-gray-200 rounded-full h-6 ${className}`}>
      <div
        className={`h-6 rounded-full flex items-center justify-end pr-2 text-white text-sm font-semibold ${getColor(value)}`}
        style={{ width: `${Math.min(value, 100)}%` }}
      >
        {value.toFixed(0)}% used
      </div>
    </div>
  );
}
```

---

#### `hooks/useAllocations.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export function useAllocations() {
  return useQuery({
    queryKey: ['allocations', 'summary'],
    queryFn: async () => {
      const response = await apiClient.get('/allocations/summary');
      return response.data;
    },
    refetchInterval: 15 * 60 * 1000, // Refetch every 15 minutes
    staleTime: 10 * 60 * 1000,       // Consider stale after 10 minutes
  });
}

export function useAllocationHistory(entitlementId: number) {
  return useQuery({
    queryKey: ['allocations', 'history', entitlementId],
    queryFn: async () => {
      const response = await apiClient.get(`/allocations/history?entitlement_id=${entitlementId}`);
      return response.data;
    },
    enabled: !!entitlementId, // Only run if entitlementId provided
  });
}
```

---

#### `app/(dashboard)/page.tsx`

```typescript
import { AllocationSummaryCard } from '@/components/allocations/AllocationSummaryCard';
import { AlertList } from '@/components/alerts/AlertList';
import { AnnouncementFeed } from '@/components/allocations/AnnouncementFeed';

export default function DashboardPage() {
  return (
    <div className="container mx-auto px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Allocation + Alerts (2/3 width) */}
        <div className="lg:col-span-2 space-y-6">
          <AllocationSummaryCard />
          <AlertList />
        </div>

        {/* Right: Announcements (1/3 width) */}
        <div>
          <AnnouncementFeed />
        </div>
      </div>
    </div>
  );
}
```

---

## Data Collection & Scraping

### 1. Allocation Statement Scraper

**File:** `app/scrapers/nsw_dpie_scraper.py`

```python
import httpx
import pdfplumber
from bs4 import BeautifulSoup
from datetime import datetime
from app.database import get_db
from sqlalchemy.orm import Session

class NSWDPIEScraper:
    """
    Scrapes water allocation statements from NSW DPIE website
    """

    BASE_URL = "https://water.dpie.nsw.gov.au"
    INDEX_URL = f"{BASE_URL}/our-work/allocations-availability/allocations/water-allocation-statements"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def scrape_murrumbidgee_latest(self):
        """
        Scrape latest Murrumbidgee allocation statement
        """
        # Step 1: Get index page to find latest PDF link
        index_url = f"{self.INDEX_URL}/murrumbidgee-valley"
        response = await self.client.get(index_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find latest PDF link
        # Pattern: <a href="/path/to/murrumbidgee-allocation-2024-12-16.pdf">
        pdf_links = soup.find_all('a', href=lambda x: x and '.pdf' in x and 'murrumbidgee' in x.lower())

        if not pdf_links:
            raise Exception("No PDF links found on index page")

        # Get first (most recent) link
        latest_link = pdf_links[0]['href']
        if not latest_link.startswith('http'):
            latest_link = self.BASE_URL + latest_link

        # Step 2: Download PDF
        pdf_response = await self.client.get(latest_link)

        # Step 3: Parse PDF with pdfplumber
        with pdfplumber.open(BytesIO(pdf_response.content)) as pdf:
            # Extract text from first page (contains allocation table)
            first_page = pdf.pages[0]
            text = first_page.extract_text()

            # Extract allocation table
            allocations = self._parse_allocation_table(text)

            # Extract dam levels
            dam_levels = self._parse_dam_levels(text)

            # Extract date from filename or PDF content
            announced_date = self._parse_date_from_filename(latest_link)

        # Step 4: Store in database
        await self._store_allocations(allocations, dam_levels, announced_date, latest_link)

        return {
            'allocations': allocations,
            'dam_levels': dam_levels,
            'announced_date': announced_date,
            'pdf_url': latest_link
        }

    def _parse_allocation_table(self, text: str) -> dict:
        """
        Extract allocation percentages from PDF text

        Example text:
        "General Security: 45%
         High Security: 95%
         Conveyance: 100%"
        """
        allocations = {}

        # Regex patterns for different categories
        patterns = {
            'General Security': r'General\s+Security.*?(\d+)%',
            'High Security': r'High\s+Security.*?(\d+)%',
            'Conveyance': r'Conveyance.*?(\d+)%',
            'Domestic and Stock': r'Domestic.*?Stock.*?(\d+)%'
        }

        for category, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                allocations[category] = float(match.group(1))

        return allocations

    def _parse_dam_levels(self, text: str) -> dict:
        """
        Extract dam storage levels

        Example: "Blowering Dam: 67% capacity"
        """
        dam_levels = {}

        patterns = {
            'Blowering': r'Blowering.*?(\d+(?:\.\d+)?)%',
            'Burrinjuck': r'Burrinjuck.*?(\d+(?:\.\d+)?)%'
        }

        for dam, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dam_levels[dam] = float(match.group(1))

        return dam_levels

    def _parse_date_from_filename(self, url: str) -> datetime.date:
        """
        Extract date from PDF filename
        Example: "murrumbidgee-allocation-2024-12-16.pdf" → 2024-12-16
        """
        # Pattern: YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', url)
        if match:
            year, month, day = match.groups()
            return datetime(int(year), int(month), int(day)).date()

        # Fallback: today's date
        return datetime.now().date()

    async def _store_allocations(self, allocations: dict, dam_levels: dict,
                                  announced_date: datetime.date, pdf_url: str):
        """
        Store parsed allocations in database
        """
        db: Session = next(get_db())

        # Get water source and categories
        source = db.query(WaterSource).filter_by(
            source_name='Murrumbidgee Regulated River'
        ).first()

        # Get current water year
        today = datetime.now()
        water_year = today.year if today.month >= 7 else today.year - 1

        for category_name, allocation_pct in allocations.items():
            # Get category
            category = db.query(AllocationCategory).filter_by(
                source_id=source.source_id,
                category_name=category_name
            ).first()

            if not category:
                continue

            # Insert/update allocation announcement
            announcement = db.query(AllocationAnnouncement).filter_by(
                source_id=source.source_id,
                category_id=category.category_id,
                announced_date=announced_date
            ).first()

            if announcement:
                # Update existing
                announcement.allocation_pct = allocation_pct
                announcement.dam_levels = dam_levels
                announcement.statement_pdf_url = pdf_url
            else:
                # Create new
                announcement = AllocationAnnouncement(
                    source_id=source.source_id,
                    category_id=category.category_id,
                    allocation_pct=allocation_pct,
                    announced_date=announced_date,
                    water_year=water_year,
                    dam_levels=dam_levels,
                    statement_pdf_url=pdf_url
                )
                db.add(announcement)

        db.commit()

        # Refresh materialized view
        db.execute("SELECT refresh_latest_allocations()")
        db.commit()
```

---

### 2. Celery Tasks

**File:** `app/tasks/scraping_tasks.py`

```python
from celery import Celery
from app.scrapers.nsw_dpie_scraper import NSWDPIEScraper

celery_app = Celery('waterright', broker='redis://localhost:6379/0')

@celery_app.task
async def scrape_allocation_statements():
    """
    Daily task to scrape allocation statements
    Runs at 6:00 AM daily (after NSW DPIE publishes new statements at ~5:00 PM previous day)
    """
    scraper = NSWDPIEScraper()

    try:
        result = await scraper.scrape_murrumbidgee_latest()
        return {
            'status': 'success',
            'allocations_found': len(result['allocations']),
            'date': result['announced_date'].isoformat()
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@celery_app.task
async def sync_all_telemetry():
    """
    Hourly task to sync telemetry for all farmers with configured telemetry
    """
    from app.services.telemetry_service import TelemetryService

    service = TelemetryService()
    results = await service.sync_all_farmers()

    return {
        'status': 'success',
        'farmers_synced': results['farmers_synced'],
        'readings_fetched': results['readings_fetched'],
        'errors': results['errors']
    }

@celery_app.task
async def evaluate_compliance_alerts():
    """
    Hourly task to evaluate compliance rules and send alerts
    """
    from app.services.compliance_service import ComplianceService

    service = ComplianceService()
    results = await service.check_all_farmers_compliance()

    return {
        'status': 'success',
        'alerts_sent': results['alerts_sent'],
        'farmers_checked': results['farmers_checked']
    }
```

**Celery Beat Schedule (Cron Jobs):**

```python
# app/tasks/__init__.py

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'scrape-allocations-daily': {
        'task': 'app.tasks.scraping_tasks.scrape_allocation_statements',
        'schedule': crontab(hour=6, minute=0),  # 6:00 AM daily
    },
    'sync-telemetry-hourly': {
        'task': 'app.tasks.scraping_tasks.sync_all_telemetry',
        'schedule': crontab(minute=0),  # Every hour at :00
    },
    'evaluate-alerts-hourly': {
        'task': 'app.tasks.scraping_tasks.evaluate_compliance_alerts',
        'schedule': crontab(minute=15),  # Every hour at :15
    },
}
```

---

## Telemetry Integration

### Observant API Integration

**File:** `app/services/telemetry_service.py`

```python
import httpx
from datetime import datetime, timedelta
from app.database import get_db
from sqlalchemy.orm import Session

class ObservantTelemetryProvider:
    """
    Integration with Observant telemetry API
    """

    BASE_URL = "https://api.observant.net/v1"

    def __init__(self, api_key: str, account_id: str):
        self.api_key = api_key
        self.account_id = account_id
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30.0
        )

    async def get_meter_readings(self, meter_id: str, start_date: datetime, end_date: datetime):
        """
        Fetch meter readings for date range
        """
        response = await self.client.get(
            f'/meters/{meter_id}/readings',
            params={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        )

        if response.status_code != 200:
            raise Exception(f"Observant API error: {response.status_code} {response.text}")

        data = response.json()
        return data['readings']


class TelemetryService:
    """
    Unified telemetry service supporting multiple providers
    """

    async def sync_farmer_telemetry(self, farmer_id: int):
        """
        Sync telemetry for all of farmer's meters
        """
        db: Session = next(get_db())

        # Get farmer's telemetry configs
        configs = db.query(TelemetryConfig).filter_by(
            farmer_id=farmer_id,
            sync_enabled=True
        ).all()

        results = {'readings_fetched': 0, 'errors': []}

        for config in configs:
            try:
                if config.provider == 'observant':
                    provider = ObservantTelemetryProvider(
                        api_key=decrypt(config.api_key),
                        account_id=config.account_id
                    )

                    # Fetch readings since last sync (or last 7 days if first sync)
                    start_date = config.last_sync_at or (datetime.now() - timedelta(days=7))
                    end_date = datetime.now()

                    readings = await provider.get_meter_readings(
                        meter_id=config.meter_id,
                        start_date=start_date,
                        end_date=end_date
                    )

                    # Store readings in database
                    for reading in readings:
                        telemetry_reading = TelemetryReading(
                            entitlement_id=config.entitlement_id,
                            meter_id=config.meter_id,
                            meter_provider='observant',
                            reading_timestamp=reading['timestamp'],
                            cumulative_volume_ML=reading['cumulative_volume_ML'],
                            flow_rate_L_per_sec=reading.get('flow_rate_L_per_sec'),
                            battery_voltage=reading.get('battery_voltage'),
                            signal_strength_dbm=reading.get('signal_strength')
                        )
                        db.merge(telemetry_reading)  # Upsert (insert or ignore if duplicate)

                    # Update last sync
                    config.last_sync_at = datetime.now()
                    config.last_sync_status = 'success'

                    results['readings_fetched'] += len(readings)

            except Exception as e:
                config.last_sync_status = f'failed: {str(e)}'
                results['errors'].append({
                    'config_id': config.config_id,
                    'error': str(e)
                })

        db.commit()
        return results

    async def sync_all_farmers(self):
        """
        Sync telemetry for all farmers (called by Celery task)
        """
        db: Session = next(get_db())

        # Get all farmers with active telemetry
        farmer_ids = db.query(TelemetryConfig.farmer_id).filter_by(
            sync_enabled=True
        ).distinct().all()

        total_readings = 0
        total_errors = []

        for (farmer_id,) in farmer_ids:
            result = await self.sync_farmer_telemetry(farmer_id)
            total_readings += result['readings_fetched']
            total_errors.extend(result['errors'])

        return {
            'farmers_synced': len(farmer_ids),
            'readings_fetched': total_readings,
            'errors': total_errors
        }
```

---

## Alert System

### Compliance Service

**File:** `app/services/compliance_service.py`

```python
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Farmer, FarmerEntitlement, AlertRule, FarmerAlert
from app.services.allocation_service import AllocationService
from app.services.notification_service import NotificationService
from jinja2 import Template

class ComplianceService:
    """
    Evaluate compliance rules and generate alerts
    """

    def __init__(self):
        self.allocation_service = AllocationService()
        self.notification_service = NotificationService()

    async def check_all_farmers_compliance(self):
        """
        Check compliance for all active farmers (called by Celery task)
        """
        db: Session = next(get_db())

        farmers = db.query(Farmer).filter_by(account_status='active').all()

        alerts_sent = 0

        for farmer in farmers:
            result = await self.check_farmer_compliance(farmer.farmer_id)
            alerts_sent += result['alerts_sent']

        return {
            'farmers_checked': len(farmers),
            'alerts_sent': alerts_sent
        }

    async def check_farmer_compliance(self, farmer_id: int):
        """
        Check compliance for a single farmer
        """
        db: Session = next(get_db())

        # Get farmer's entitlements with current allocation/usage
        entitlements = db.query(FarmerEntitlement).filter_by(
            farmer_id=farmer_id,
            active=True
        ).all()

        # Get all enabled alert rules
        rules = db.query(AlertRule).filter_by(enabled=True).all()

        alerts_to_send = []

        for entitlement in entitlements:
            # Get compliance status
            status = self.allocation_service.get_compliance_status(entitlement.entitlement_id)

            context = {
                'farmer_id': farmer_id,
                'entitlement_id': entitlement.entitlement_id,
                'category_name': entitlement.category.category_name,
                'source_name': entitlement.source.source_name,
                'entitlement_volume_ML': entitlement.volume_ML,
                'allocation_pct': status['allocation_pct'],
                'allocation_ML': status['allocation_ML'],
                'used_ML': status['used_ML'],
                'remaining_ML': status['remaining_ML'],
                'pct_used': status['pct_used']
            }

            for rule in rules:
                # Evaluate rule condition
                if self._evaluate_condition(rule.condition_sql, context):
                    # Rule triggered!

                    # Check if already alerted recently (throttling)
                    if self._was_recently_alerted(farmer_id, rule.rule_id, rule.min_hours_between_alerts):
                        continue

                    # Render message template
                    message = Template(rule.message_template).render(context)

                    alerts_to_send.append({
                        'farmer_id': farmer_id,
                        'rule_id': rule.rule_id,
                        'entitlement_id': entitlement.entitlement_id,
                        'priority': rule.priority,
                        'message': message,
                        'recommendations': rule.action_recommendations,
                        'context': context,
                        'send_sms': rule.send_sms,
                        'send_email': rule.send_email,
                        'send_push': rule.send_push
                    })

        # Send alerts
        for alert in alerts_to_send:
            await self._send_alert(alert)

        return {'alerts_sent': len(alerts_to_send)}

    def _evaluate_condition(self, condition_sql: str, context: dict) -> bool:
        """
        Evaluate SQL-like condition with context variables

        Example: "pct_used >= 90 AND pct_used < 100"
        """
        # Replace context variables in condition
        for key, value in context.items():
            condition_sql = condition_sql.replace(f'{key}', str(value))

        # Evaluate (safely - using simple eval, or proper SQL expression parser)
        try:
            return eval(condition_sql)
        except:
            return False

    def _was_recently_alerted(self, farmer_id: int, rule_id: int, min_hours: int) -> bool:
        """
        Check if farmer was alerted for this rule recently
        """
        db: Session = next(get_db())

        cutoff_time = datetime.now() - timedelta(hours=min_hours)

        recent_alert = db.query(FarmerAlert).filter(
            FarmerAlert.farmer_id == farmer_id,
            FarmerAlert.rule_id == rule_id,
            FarmerAlert.created_at > cutoff_time,
            FarmerAlert.acknowledged == False
        ).first()

        return recent_alert is not None

    async def _send_alert(self, alert: dict):
        """
        Store alert in database and send notifications
        """
        db: Session = next(get_db())

        # Store in database
        db_alert = FarmerAlert(
            farmer_id=alert['farmer_id'],
            rule_id=alert['rule_id'],
            entitlement_id=alert['entitlement_id'],
            priority=alert['priority'],
            message=alert['message'],
            recommendations=alert['recommendations'],
            context=alert['context']
        )
        db.add(db_alert)
        db.commit()

        # Send notifications
        if alert['send_sms']:
            await self.notification_service.send_sms(
                farmer_id=alert['farmer_id'],
                message=alert['message']
            )
            db_alert.sent_sms = True
            db_alert.sent_sms_at = datetime.now()

        if alert['send_email']:
            await self.notification_service.send_email(
                farmer_id=alert['farmer_id'],
                subject=f"Water Compliance Alert: {alert['priority'].upper()}",
                message=alert['message'],
                recommendations=alert['recommendations']
            )
            db_alert.sent_email = True
            db_alert.sent_email_at = datetime.now()

        db.commit()
```

---

## Deployment Architecture

### Docker Compose Setup

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  # PostgreSQL with PostGIS + TimescaleDB
  postgres:
    image: timescale/timescaledb-postgis:latest-pg14
    environment:
      POSTGRES_DB: waterright
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis (Celery broker + cache)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # FastAPI Backend
  backend:
    build:
      context: ./waterright-backend
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./waterright-backend:/app
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/waterright
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      TWILIO_ACCOUNT_SID: ${TWILIO_ACCOUNT_SID}
      TWILIO_AUTH_TOKEN: ${TWILIO_AUTH_TOKEN}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  # Celery Worker
  celery-worker:
    build:
      context: ./waterright-backend
      dockerfile: Dockerfile
    command: celery -A app.tasks worker --loglevel=info
    volumes:
      - ./waterright-backend:/app
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/waterright
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  # Celery Beat (Scheduler)
  celery-beat:
    build:
      context: ./waterright-backend
      dockerfile: Dockerfile
    command: celery -A app.tasks beat --loglevel=info
    volumes:
      - ./waterright-backend:/app
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/waterright
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  # Next.js Frontend
  frontend:
    build:
      context: ./waterright-frontend
      dockerfile: Dockerfile
    command: npm run dev
    volumes:
      - ./waterright-frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api/v1
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

---

## Implementation Roadmap

### Week 1-2: Foundation & Data Pipeline

**Tasks:**
1. Set up PostgreSQL database with complete schema
2. Implement allocation scraper (NSW DPIE PDFs)
3. Create FastAPI backend skeleton
4. Build auth system (register, login, JWT)
5. Test scraper with historical data (populate database)

**Deliverables:**
- Database with 2 years of historical allocations
- Working scraper (can run manually)
- Auth endpoints functional

---

### Week 3-4: Core Allocation Features

**Tasks:**
1. Allocation API endpoints (summary, history, announcements)
2. Entitlement management (add/edit/delete)
3. Frontend: Allocation dashboard (summary card, history chart)
4. Deploy to staging (Docker Compose on AWS/DigitalOcean)

**Deliverables:**
- Farmers can view allocations in real-time
- Historical charts working
- Responsive UI on mobile

---

### Week 5-6: Usage Tracking

**Tasks:**
1. Manual usage entry (frontend form + backend API)
2. Observant telemetry integration (API client)
3. Usage history charts
4. Predictive usage calculator (days until exceed)

**Deliverables:**
- Farmers can log water usage manually
- Telemetry sync working (for farmers with Observant meters)
- Usage forecasting displayed

---

### Week 7-8: Compliance & Alerts

**Tasks:**
1. Implement compliance rules engine
2. Alert evaluation (Celery tasks)
3. SMS/Email notifications (Twilio + SendGrid)
4. Alert dashboard (list, acknowledge)
5. Compliance calendar

**Deliverables:**
- Automated alerts triggering correctly
- SMS/Email delivery working
- Farmers can acknowledge alerts

---

### Week 9-10: Pilot Preparation & Testing

**Tasks:**
1. Onboarding flow (wizard for new farmers)
2. Admin dashboard (scraping status, user management)
3. End-to-end testing with test data
4. User acceptance testing (internal team)
5. Documentation (user guide, FAQ)

**Deliverables:**
- Production-ready MVP
- Onboarding takes <10 minutes
- Zero critical bugs

---

### Week 11-12: Pilot Launch

**Tasks:**
1. Onboard 20 Murrumbidgee Irrigation pilot farmers
2. In-person training sessions (site visits)
3. Weekly check-ins, feedback collection
4. Bug fixes, UX improvements

**Deliverables:**
- 20 active pilot users
- Feedback documented
- Product-market fit validated

---

**Total Timeline:** 10-12 weeks to pilot launch

**Next Steps:**
1. Review this document with development team
2. Prioritize any missing requirements
3. Begin Week 1 implementation
4. Schedule weekly progress reviews

---

**Document Status:** Implementation Guide Complete
**Ready for:** Development kickoff
**Estimated Effort:** 800-1000 development hours (2 engineers, 10-12 weeks)
