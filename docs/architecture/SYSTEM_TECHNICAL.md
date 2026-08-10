# What the system is, technically

**Measured 2026-08-09 against `origin/main` at `af7982a8`.** Every number and every arrow
below has a row in [VERIFICATION.md](VERIFICATION.md) giving the query or the file and line
that produced it. If you want to check one, start there — it is written for a reader who
assumes I am wrong.

Three diagrams. The first two split the system the way it actually divides — **what gets stored**
and **what gets served**. The third follows a single address all the way through, because "trace
one lookup end to end" is the question a reviewer actually asks.

Older architecture notes exist at `docs/ARCHITECTURE.md` and `.claude/docs/ARCHITECTURE.md`.
**Both are stale and should not be used** — see the note at the foot of this page.

---

## 1. What gets stored

Three sources, four intake paths, one database. This half runs on a schedule — or, in one case,
does not.

```mermaid
flowchart LR
  subgraph SRC["Outside data"]
    S1["Planning Portal<br/>ePlanning API"]
    S2["NSW ArcGIS<br/>mapprod1/2/3"]
    S4["Council DCP PDFs<br/>no API exists"]
  end

  subgraph ING["Getting it in"]
    I1["Map layer sync<br/>manual, no schedule"]
    I2["DCP watch + extract<br/>a human approves<br/>before anything lands"]
    I3["Certificate + DA ingest<br/>774 runs in 7 days"]
    I4["Cloudflare R2<br/>PDF store"]
  end

  subgraph DB["Supabase Postgres + PostGIS · 117 tables"]
    D1["spatial_overlays<br/>1,088,573 · 25 layers"]
    D2["nsw_cadastre_lots<br/>3,220,617"]
    D3["lot_search_index<br/>3,126,418 pre-joined"]
    D4["certificates<br/>181,737 · 128 councils"]
    D5["applications<br/>62,016 · 128 councils"]
    D6["regulatory_provisions<br/>55,696 · 19,957 served"]
    D7["dcp_setback_controls<br/>1,071 · 30 councils"]
    D8["lep_land_use_table<br/>18,196 · 26 councils"]
    D10["cdc_lot_link<br/>181,750 · 98.1% matched"]
  end

  S2 --> I1
  S1 --> I1
  S4 --> I2
  S1 --> I3
  I1 --> D1
  I2 --> I4
  I2 --> D6
  I2 --> D7
  I3 --> D4
  I3 --> D5
  D1 --> D3
  D2 --> D3
  D4 --> D10
  D2 --> D10
  D1 ~~~ D8

  classDef src fill:#e8f0fe,stroke:#3b6fb6,color:#10233d
  classDef ing fill:#fff3e0,stroke:#c77700,color:#3d2a10
  classDef db fill:#e9f7ef,stroke:#2e7d52,color:#102a1c
  class S1,S2,S4 src
  class I1,I2,I3,I4 ing
  class D1,D2,D3,D4,D5,D6,D7,D8,D10 db
```

`cdc_lot_link` was added on 2026-08-10 and is the only box on this diagram that is derived from
two others rather than ingested. It ties each certificate to the lot its coordinates fall inside,
which is what turns "what got approved at this address" into "what got approved on lots like this
one". 178,259 of 181,750 matched — 98.1%.

---

## 2. What gets served

The other half. Note that several sources appear here and **not** in the diagram above — they are
called live, per request, and never stored.

```mermaid
flowchart LR
  subgraph LIVE["Called live, never stored"]
    L1["Planning Portal<br/>ePlanning API"]
    L2["Google Solar API"]
    L3["Satellite imagery<br/>Sentinel-2 Element84<br/>Sentinel-1 ASF"]
    L4["BoM · RFS · Valuer Gen<br/>Sydney Water · legislation"]
  end

  subgraph STORE["From the database"]
    D1["spatial_overlays"]
    D3["lot_search_index"]
    D4["certificates + applications"]
    D6["regulatory_provisions"]
    D7["dcp_setback_controls"]
    D9["property_reports<br/>981 runs"]
  end

  subgraph SVC["Python · 76 modules"]
    V4["Rules engine"]
    V5["lot_search +<br/>constraint arithmetic"]
    V1["Screening pipelines<br/>shadow flood solar<br/>bushfire granny<br/>no imagery"]
    V6["pre_da_history +<br/>drawdown_verify<br/>the only imagery users"]
    V2["intelligence_brief.py<br/>4,357 lines"]
    V3["conveyancing.py<br/>13 fetchers"]
  end

  subgraph API["APIs"]
    A1["FastAPI<br/>20 routers"]
    A2["Next.js<br/>140 routes"]
    A3["Trigger.dev"]
  end

  subgraph UI["Seen by a person · 123 pages"]
    F1["10 report pages"]
    F2["Property profile<br/>+ compliance UI"]
    F3["3 internal review pages"]
  end

  D1 --> V4
  D6 --> V4
  D7 --> V4
  D3 --> V5
  D4 --> V2
  L2 --> V1
  L4 --> V1
  L3 --> V6
  V1 --> D9
  V4 --> V2
  V4 --> V3
  V5 --> V2

  V1 --> A1
  V2 --> A1
  V3 --> A1
  V4 --> A1
  V5 --> A1
  V6 --> A1
  A1 --> A2
  A2 --> F1
  A2 --> F2
  A2 --> F3

  L1 -.->|"no Python in the path"| A2
  A2 -.-> A3
  A3 -.->|"UNVERIFIED — sibling repo"| A1

  classDef src fill:#e8f0fe,stroke:#3b6fb6,color:#10233d
  classDef db fill:#e9f7ef,stroke:#2e7d52,color:#102a1c
  classDef svc fill:#f3e8fd,stroke:#7b4fbe,color:#241038
  classDef api fill:#fdeaea,stroke:#c0504d,color:#3d1414
  classDef ui fill:#fdf6e3,stroke:#9a7500,color:#3d3210
  classDef unver fill:#f0f0f0,stroke:#888,color:#333,stroke-dasharray:4 3
  class L1,L2,L3,L4 src
  class D1,D3,D4,D6,D7,D9 db
  class V1,V2,V3,V4,V5,V6 svc
  class A1,A2 api
  class A3 unver
  class F1,F2,F3 ui
```

**Three things worth noticing on those pictures.**

The dotted line from the Planning Portal to the browser layer is a real edge, not decoration. The
Next.js layer talks to the government API **directly**, with no Python in the path —
`frontend-nextjs/lib/nsw-planning-portal.ts` holds nineteen of those calls in one file. Anyone
assuming all data flows through the Python backend has the shape wrong.

The Trigger.dev hop is drawn dashed and labelled **UNVERIFIED** on purpose. I can point at the
Next.js code that calls it. I cannot point at what it calls next, because those task definitions
live in a different repository that is not in this one. So I have not drawn a line I cannot show you.

**Only two modules touch satellite imagery**, and they are not the ones you would guess.
`pre_da_history.py` pulls Sentinel-2 from Element84, and `drawdown_verify.py` pulls Sentinel-1
through the Alaska Satellite Facility. Shadow, flood, solar, bushfire and granny flat use none.
I nearly drew that edge wrongly: a plain search for "sentinel" across `services/` matches five
more files, but in `bushfire_prescreen.py`, `cdc_screen.py` and `solar_yield.py` the word means
a *sentinel value* — a programming term with nothing to do with satellites. Opening each file
was the difference between a true diagram and a plausible one.

`dcp_setback_controls` is small — 1,071 rows — and it is the one box on these diagrams that
nobody else has. Everything else on the data row is either public, purchasable, or reproducible
by anyone with the same eight years. That table holds numbers pulled out of council PDFs as
numbers, each stored next to the exact sentence it came from.

---

## 3. One address, end to end

This is what happens when someone types an address into the property profile page. It is the
shortest complete path through the system, and the one to walk if you are checking whether the
diagrams above are honest.

```mermaid
flowchart TD
  U1["Someone types an address"] --> U2["/api/property/profile<br/>rate limited, 20 per minute"]
  U2 --> U3["searchProperty<br/>address to propId"]
  U3 --> P1["NSW Planning Portal<br/>ePlanningApi"]
  P1 --> U4["getPlanningLayers<br/>zone · height · floor space · heritage"]
  U4 --> U5["getLotGeometry<br/>the lot outline"]
  U5 --> U6["calculateLotDimensions<br/>width, depth, area from the polygon"]
  U6 --> U7["Profile page renders"]

  U7 --> R1["User opens a report<br/>e.g. shadow"]
  R1 --> R2["Next.js /api/satellite/shadow"]
  R2 --> R3["FastAPI POST /pipeline/shadow"]
  R3 --> R4["shadow_model.py<br/>sun position and shadow geometry"]
  R4 --> R5["Row written to property_reports"]
  R5 --> R6["PDF built, stored in R2"]
  R6 --> R7["Report page or PDF download"]

  U3 -.->|"if the portal is down there is<br/>no stored fallback — lookup fails"| X1["No result"]

  classDef step fill:#e8f0fe,stroke:#3b6fb6,color:#10233d
  classDef ext fill:#fff3e0,stroke:#c77700,color:#3d2a10
  classDef out fill:#e9f7ef,stroke:#2e7d52,color:#102a1c
  classDef bad fill:#f0f0f0,stroke:#888,color:#333,stroke-dasharray:4 3
  class U1,U2,U3,U4,U5,U6,R1,R2,R3,R4 step
  class P1 ext
  class U7,R5,R6,R7 out
  class X1 bad
```

The important detail in that diagram is the dotted line at the bottom. Zone, height and floor
space ratio are fetched **live from the government portal on every lookup**. They are not served
from our database. That is why they have been reliable, and it is also why a portal outage is a
total outage for that page.

---

## 4. Where the data stops

Counts alone flatter the system, so here is the other half, measured the same day.

| Thing | Measured | The limit |
|---|---|---|
| Mapped shapes | 1,088,573 across 25 layers | A snapshot, not a feed. Last sync ran between 13 April and 8 July 2026, by hand. |
| Layer coverage | Uneven | Zoning 128 councils, heritage 127, lot size 127 — but floor space 65, height 75, landslide 6. |
| Bushfire and fire history | 263,276 shapes | **No currency date at all.** Their age is unknown, not merely old. |
| Numeric DCP controls | 1,071 rows, 989 live | About 36 per council. Thin, and it is the true size of the defensible surface. |
| Controls with a machine-followable link back to the clause | **42 of 1,071** | The other 1,029 have the sentence and the clause reference, but no join. |
| Controls with a date they came into force | **365 of 1,071** | For 706 we cannot state when the control started applying. |
| DCP clause corpus | 55,696 rows, 19,957 served | Only 2,069 carry a number. The arithmetic surface is ~2,000 clauses plus the 1,071 controls — not 55,696. |
| Development applications | 62,016 | Determinations run from **23 May 2025**, not 2018. Only the certificates go back to 2018. |
| Stored report runs | 981 | There is no identity column on that table. These are runs, not customers. |

---

## 5. A note on the older architecture docs

`docs/ARCHITECTURE.md` (dated 2026-05-02) and `.claude/docs/ARCHITECTURE.md` (2026-01-30) both
open with "47,818 provisions." That number is the row count of `document_id_backup` — a backup
table. The live figure is 55,696 rows of which 19,957 are served. Both files also list endpoints
that have since moved.

I have left them in place rather than deleting them, and this file supersedes them. If you are
reading them for anything load-bearing, stop and use this one.
