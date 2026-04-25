---
marp: true
theme: gaia
size: 16:9
paginate: true
html: true
style: |
  :root {
    --color-background: #ffffff;
    --color-foreground: #111827;
    --color-highlight: #1E4FC2;
    --color-dimmed: #6B7280;
  }

  section {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 22px;
    padding: 52px 64px;
    background: #ffffff;
    color: #111827;
    line-height: 1.55;
  }
  section::after {
    font-size: 13px;
    color: #9CA3AF;
  }

  h1 {
    font-size: 44px;
    font-weight: 800;
    color: #111827;
    line-height: 1.1;
    letter-spacing: -1px;
    margin: 0 0 12px;
  }
  h2 {
    font-size: 34px;
    font-weight: 800;
    color: #111827;
    letter-spacing: -0.5px;
    margin: 0 0 28px;
    line-height: 1.15;
  }
  h3 {
    font-size: 13px;
    font-weight: 700;
    color: #1E4FC2;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 0 0 10px;
  }

  p { margin: 0 0 12px; }
  ul, ol { margin: 0 0 12px; padding-left: 1.3em; }
  li { margin-bottom: 7px; }
  strong { color: #111827; font-weight: 700; }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 17px;
    margin: 0;
  }
  thead tr { background: #111827; }
  th { color: #fff; font-weight: 600; padding: 10px 16px; text-align: left; font-size: 13px; letter-spacing: 0.3px; }
  td { padding: 9px 16px; border-bottom: 1px solid #E5E7EB; vertical-align: top; }
  tbody tr:nth-child(even) td { background: #F9FAFB; }
  tbody tr:last-child td { border-bottom: none; }

  .stat {
    font-size: 64px;
    font-weight: 800;
    color: #1E4FC2;
    line-height: 1;
    letter-spacing: -2px;
  }
  .stat-label {
    font-size: 15px;
    color: #6B7280;
    margin-top: 4px;
    font-weight: 500;
  }

  .pill {
    display: inline-block;
    background: #EEF3FF;
    color: #1E4FC2;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    margin: 2px 4px 2px 0;
  }
  .pill-dark {
    display: inline-block;
    background: #111827;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    margin: 2px 4px 2px 0;
  }
  .pill-green {
    display: inline-block;
    background: #F0FDF4;
    color: #059669;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    margin: 2px 4px 2px 0;
  }

  .row { display: flex; gap: 24px; margin-top: 4px; }
  .col { flex: 1; }

  /* Cover */
  section.cover {
    background: #111827;
    color: #ffffff;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 60px 72px;
  }
  section.cover::after { color: transparent; }
  section.cover::before { display: none; }
  section.cover h1 { color: #ffffff; font-size: 56px; margin: 0 0 10px; }
  section.cover p { color: #9CA3AF; font-size: 18px; margin: 0 0 6px; }
  section.cover em { color: #60A5FA; font-style: normal; }
  section.cover strong { color: #ffffff; }

  /* Dark section */
  section.dark {
    background: #111827;
    color: #F9FAFB;
  }
  section.dark h2 { color: #F9FAFB; }
  section.dark h3 { color: #60A5FA; }
  section.dark p { color: #D1D5DB; }
  section.dark li { color: #D1D5DB; }
  section.dark strong { color: #ffffff; }
  section.dark .stat { color: #60A5FA; }
  section.dark .stat-label { color: #6B7280; }

  /* Big number accent slide */
  section.accent {
    background: #1E4FC2;
    color: #ffffff;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  section.accent::after { color: rgba(255,255,255,0.4); }
  section.accent h2 { color: #ffffff; font-size: 42px; }
  section.accent p { color: rgba(255,255,255,0.75); font-size: 20px; }

  /* Need slide */
  section.need {
    background: #F9FAFB;
  }
---

<!-- _class: cover -->

<div style="margin-bottom: 48px;">
<div style="font-size: 13px; font-weight: 700; color: #4B5563; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 20px;">PlotDetect — Lawrence McD, Solo Founder</div>

# NSW Planning Intelligence
## Machine-readable compliance for every address

**What it is:** The infrastructure layer that makes NSW planning rules — DCP provisions, SEPP pathways, spatial constraints — queryable at address level, in real time.

*Stone & Chalk — April 2026*

</div>

---

## The problem

<div class="row">
<div class="col">

NSW planning compliance is fragmented across hundreds of councils, thousands of document pages, and five separate portals — none of which talk to each other.

**The cost is paid by everyone in the system:**

- A town planner spends 2–4 hours on pre-DA research before a DA is even scoped
- A conveyancer can't get a quantified flood risk for most Sydney addresses — InfoTrack says "unknown"
- A builder discovers a biodiversity constraint **after** committing to a site — $15–50k, 4–12 months

</div>
<div class="col" style="display: flex; flex-direction: column; gap: 16px; justify-content: center;">

<div style="border-left: 4px solid #1E4FC2; padding: 14px 18px; background: #F8FAFF;">
<div class="stat">47K</div>
<div class="stat-label">DCP provisions extracted — machine-readable</div>
</div>

<div style="border-left: 4px solid #059669; padding: 14px 18px; background: #F0FDF4;">
<div style="font-size: 36px; font-weight: 800; color: #059669; letter-spacing: -1px; line-height: 1;">128 LGAs</div>
<div class="stat-label">Spatial overlay coverage — every NSW council</div>
</div>

</div>
</div>

---

## What I've built — the four-layer stack

<p style="font-size: 17px; color: #6B7280; margin-bottom: 20px;">The only tool that connects all four layers in a single address query.</p>

| Layer | What Verify does | Competition |
|---|---|---|
| **1. Spatial overlay** | Flood, biodiversity, heritage, acid sulfate — PostGIS, 128 LGAs | InfoTrack: "unknown" for most |
| **2. SEPP** | CDC eligibility, Housing Code pathway, BASIX, TOD, affordability | PropCode: strong here |
| **3. LEP** | Zone, FSR, height, lot size — live NSW Planning Portal | LandChecker: display only |
| **4. DCP** | 47K provisions, dev-type filtered, 13 Sydney LGAs numeric setbacks | Nobody at this depth |

<div style="margin-top: 18px; padding: 14px 20px; background: #111827; border-radius: 8px; color: white; font-size: 16px;">
PropCode has layers 2+3. LandChecker has spatial display. <strong>Nobody has all four with provision-level DCP depth and PostGIS spatial resolution.</strong>
</div>

---

## Platform — three tiers, one engine

<div class="row" style="gap: 20px; margin-top: 8px;">

<div style="flex: 1; border-top: 4px solid #111827; padding: 18px 0 0;">
<h3>Tier 1 — Planning</h3>
<p style="font-size: 16px;">Town planners, architects, developers</p>
<ul style="font-size: 15px;">
<li>DCP provision browser, filtered by dev type</li>
<li>SEPP/LEP compliance check</li>
<li>SEE document generation <em style="font-size:13px;">(in progress)</em></li>
<li>DA mode — structured assessment</li>
</ul>
<div style="margin-top: 10px;"><span class="pill-dark">$99–149/mo</span></div>
</div>

<div style="flex: 1; border-top: 4px solid #1E4FC2; padding: 18px 0 0;">
<h3>Tier 2 — Transaction</h3>
<p style="font-size: 16px;">Conveyancers, property solicitors</p>
<ul style="font-size: 15px;">
<li>GIS overlay report — flood, biodiversity, heritage</li>
<li>DCP risk flags pre-settlement</li>
<li>CC/OC gap detection</li>
<li>194K NSW settlements/year addressable</li>
</ul>
<div style="margin-top: 10px;"><span class="pill">$49–79/report</span></div>
</div>

<div style="flex: 1; border-top: 4px solid #059669; padding: 18px 0 0;">
<h3>Tier 3 — Spatial</h3>
<p style="font-size: 16px;">Builders, investors, solar installers</p>
<ul style="font-size: 15px;">
<li>5 satellite analysis products — live</li>
<li>Granny flat feasibility, flood truth</li>
<li>Solar yield, shadow, DA activity</li>
<li>Any NSW address, 30 seconds</li>
</ul>
<div style="margin-top: 10px;"><span class="pill-green">$15–80/report</span></div>
</div>

</div>

---

## 5 satellite analysis products — live

<div style="display: flex; gap: 14px; margin-top: 10px;">

<div style="flex: 1; border-top: 4px solid #059669; padding: 14px 14px 12px; background: #F0FDF4;">
<div style="font-size: 13px; font-weight: 800; color: #059669; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;"><strong>Granny Flat Feasibility</strong></div>
<div style="font-size: 13px; color: #374151;">SEPP H2021 eligibility + DCP setbacks + lot coverage — 13 Sydney LGAs, numeric</div>
<div style="font-size: 12px; color: #6B7280; margin-top: 5px;">Builders, investors</div>
</div>

<div style="flex: 1; border-top: 4px solid #0891B2; padding: 14px 14px 12px; background: #ECFEFF;">
<div style="font-size: 13px; font-weight: 800; color: #0891B2; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;"><strong>Solar Yield</strong></div>
<div style="font-size: 13px; color: #374151;">Roof plane detection, annual kWh yield, panel count, grade — Sentinel-2 + DSM</div>
<div style="font-size: 12px; color: #6B7280; margin-top: 5px;">Solar installers, homeowners</div>
</div>

<div style="flex: 1; border-top: 4px solid #7C3AED; padding: 14px 14px 12px; background: #F5F3FF;">
<div style="font-size: 13px; font-weight: 800; color: #7C3AED; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;"><strong>Shadow Analysis</strong></div>
<div style="font-size: 13px; color: #374151;">Overshadowing — equinox + solstice, DCP winter sun compliance</div>
<div style="font-size: 12px; color: #6B7280; margin-top: 5px;">Planners, architects</div>
</div>

<div style="flex: 1; border-top: 4px solid #D97706; padding: 14px 14px 12px; background: #FFFBEB;">
<div style="font-size: 13px; font-weight: 800; color: #D97706; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;"><strong>Threat Radar</strong></div>
<div style="font-size: 13px; color: #374151;">DA activity heatmap — approvals, refusals, development pressure within 500m</div>
<div style="font-size: 12px; color: #6B7280; margin-top: 5px;">Buyer's agents, investors</div>
</div>

<div style="flex: 1; border-top: 4px solid #DC2626; padding: 14px 14px 12px; background: #FEF2F2;">
<div style="font-size: 13px; font-weight: 800; color: #DC2626; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;"><strong>Flood Truth</strong></div>
<div style="font-size: 13px; color: #374151;">Quantified ARI flood probability — 12 LGAs with council data. InfoTrack says "unknown".</div>
<div style="font-size: 12px; color: #6B7280; margin-top: 5px;">Conveyancers, buyers</div>
</div>

</div>

<div style="margin-top: 16px; padding: 12px 20px; background: #111827; border-radius: 6px; color: #fff; font-size: 15px;">
Any NSW address — 30-second turnaround — PDF report — satellite data processed server-side, no GIS skill required &nbsp;<strong style="color: #60A5FA;">$15–80/report</strong>
</div>

---

<!-- _class: dark -->

## What's been built — solo, in ~12 months

<div class="row" style="gap: 40px; margin-top: 8px;">
<div class="col">

**Infrastructure**
- Supabase PostgreSQL — 47K+ provisions, 42 tables
- PostGIS — 128 LGA spatial overlays, 11 layer types
- Python ETL — DCP ingestion, provision + setback extraction
- Railway FastAPI — satellite backend, deployed
- Next.js frontend — Vercel, live

**Data**
- DCP provisions: 3 LGAs full depth (Inner West)
- Numeric setbacks: 13 Sydney LGAs
- Spatial risk: 128 NSW LGAs

</div>
<div class="col">

**Products live**
- Verify — full compliance assessment, all NSW
- 5 satellite analyses — Granny Flat, Solar Yield, Shadow, Threat Radar, Flood Truth
- Conveyancing spatial risk report
- DCP monitoring (VerifyOpsBot)

**Stack**
<span class="pill">Next.js</span> <span class="pill">Python</span> <span class="pill">Supabase</span> <span class="pill">PostGIS</span> <span class="pill">Sentinel-1 SAR</span> <span class="pill">Railway</span>

**Stage:** Pre-revenue. Zero paying users — zero marketing to date.

</div>
</div>

---

## Next product — construction loan drawdown verification

<div class="row" style="gap: 24px; font-size: 15px;">
<div class="col">

<p style="margin-bottom: 8px;">The other 5 products use planning APIs, spatial overlays, and optical imagery — well-documented, buildable by any GIS developer. Drawdown requires <strong>SAR signal processing</strong> — a distinct engineering discipline.</p>

<ul style="margin: 0; padding-left: 1.2em;">
<li><strong>SAR is complex-valued</strong> (amplitude + phase) — standard image analysis doesn't apply</li>
<li><strong>SLC coherence</strong> — sub-pixel co-registration of image pairs, coherence estimation over time</li>
<li><strong>Stage signatures</strong> — slab, frame, lock-up, fit-out each disturb radar return differently</li>
<li><strong>Noise rejection</strong> — rain, vegetation, neighbours all degrade coherence; needs temporal filtering</li>
<li><strong>HyP3 (NASA ASF)</strong> — free cloud InSAR, but construction lending interpretation is non-trivial</li>
</ul>

</div>
<div class="col" style="display: flex; flex-direction: column; gap: 10px; justify-content: center;">

<div style="background: #F8FAFF; border-left: 4px solid #1E4FC2; padding: 11px 14px;">
<div style="font-size: 12px; font-weight: 700; color: #1E4FC2; text-transform: uppercase; letter-spacing: 0.5px;">Unit economics</div>
<div style="font-size: 20px; font-weight: 800; color: #111827; margin: 3px 0;">$20 vs $300–500</div>
<div style="font-size: 12px; color: #6B7280;">Lender saves $1,000–2,500 per loan. 10–15× cost reduction.</div>
</div>

<div style="background: #F0FDF4; border-left: 4px solid #059669; padding: 11px 14px;">
<div style="font-size: 12px; font-weight: 700; color: #059669; text-transform: uppercase; letter-spacing: 0.5px;">AU pilot market</div>
<div style="font-size: 20px; font-weight: 800; color: #111827; margin: 3px 0;">Zero competition</div>
<div style="font-size: 12px; color: #6B7280;">All lenders use human inspectors. Model is globally replicable.</div>
</div>

<div style="background: #FFF7ED; border-left: 4px solid #EA580C; padding: 11px 14px;">
<div style="font-size: 12px; font-weight: 700; color: #EA580C; text-transform: uppercase; letter-spacing: 0.5px;">First target</div>
<div style="font-size: 16px; font-weight: 700; color: #111827; margin: 3px 0;">Pepper Money</div>
<div style="font-size: 12px; color: #6B7280;">Already adopted Fortiro for doc fraud. CRO: Michael Vainauskas. Same risk logic.</div>
</div>

</div>
</div>

---

## What I'm looking for

<div class="row" style="gap: 24px; margin-top: 8px;">

<div style="flex: 1; border-top: 3px solid #1E4FC2; padding: 16px 0 0;">
<h3>Programs</h3>
<ul style="font-size: 16px;">
<li>Early-stage deep tech / govtech accelerator</li>
<li>R&D support or grant facilitation</li>
<li>Founder peer community — proptech, govtech, spatial</li>
<li>Legal / commercialisation support</li>
</ul>
</div>

<div style="flex: 1; border-top: 3px solid #059669; padding: 16px 0 0;">
<h3>Connections</h3>
<ul style="font-size: 16px;">
<li>NSW government — Department of Planning, AI Solutions Panel</li>
<li>Non-bank lenders for construction drawdown pilot</li>
<li>Town planning firms for Verify pilot</li>
<li>Matched co-funding partners (ETCF, R&D Tax)</li>
</ul>
</div>

<div style="flex: 1; border-top: 3px solid #F59E0B; padding: 16px 0 0;">
<h3>Capital</h3>
<ul style="font-size: 16px;">
<li>Seed / pre-seed investor introductions</li>
<li>Grant navigation — ETCF, Accelerating Commercialisation</li>
<li>NSW AI Solutions Panel pathway</li>
<li>Not raising yet — but want to understand the landscape</li>
</ul>
</div>

</div>

<div style="margin-top: 20px; padding: 14px 20px; background: #F9FAFB; border-left: 4px solid #1E4FC2; font-size: 16px;">
<strong>The most useful thing today:</strong> who else in this community is working in proptech, govtech, or spatial data — and what programs exist for solo technical founders at this stage?
</div>

---

<!-- _class: cover -->

<div style="margin-bottom: 48px;">
<div style="font-size: 13px; font-weight: 700; color: #4B5563; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 20px;">PlotDetect</div>

## The moat is the data depth.
## PropCode has SEPP and LEP.
## Nobody has all four layers with DCP granularity.

*lawrence@plotdetect.com.au*
*verify.plotdetect.com.au*

</div>
