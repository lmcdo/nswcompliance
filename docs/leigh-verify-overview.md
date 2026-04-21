---
marp: true
theme: default
size: 16:9
paginate: true
style: |
  :root {
    --navy:       #0D1B3E;
    --blue:       #1E4FC2;
    --blue-mid:   #4A7DDF;
    --blue-light: #EEF3FF;
    --text:       #1A1A2A;
    --muted:      #64748B;
    --border:     #DDE4F0;
    --row-alt:    #F7F9FE;
    --red:        #B91C1C;
    --green:      #15803D;
    --accent-bar: 4px solid #1E4FC2;
  }

  /* ── Base slide ─────────────────────────────────── */
  section {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
    font-size: 15.5px;
    line-height: 1.65;
    color: var(--text);
    background: #ffffff;
    padding: 48px 64px 40px;
    border-top: var(--accent-bar);
    box-sizing: border-box;
  }

  /* ── Paginator ──────────────────────────────────── */
  section::after {
    font-size: 11px;
    color: var(--muted);
    bottom: 18px;
    right: 64px;
  }

  /* ── Headings ───────────────────────────────────── */
  h1 {
    font-size: 30px;
    font-weight: 700;
    color: var(--navy);
    line-height: 1.2;
    margin: 0 0 6px;
    letter-spacing: -0.3px;
  }
  h2 {
    font-size: 22px;
    font-weight: 700;
    color: var(--blue);
    margin: 0 0 18px;
    padding-bottom: 10px;
    border-bottom: 2px solid var(--border);
    letter-spacing: -0.2px;
  }
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: var(--navy);
    margin: 16px 0 6px;
  }

  /* ── Body text ──────────────────────────────────── */
  p { margin: 0 0 12px; }
  ul, ol { margin: 0 0 12px; padding-left: 1.4em; }
  li { margin-bottom: 5px; }
  strong { color: var(--navy); }
  em { color: var(--muted); }

  /* ── Blockquote ─────────────────────────────────── */
  blockquote {
    border-left: 4px solid var(--blue-mid);
    background: var(--blue-light);
    margin: 16px 0 0;
    padding: 14px 20px;
    border-radius: 0 6px 6px 0;
    font-size: 15px;
    color: var(--navy);
  }
  blockquote p { margin: 0; }
  blockquote strong { color: var(--blue); }

  /* ── Tables ─────────────────────────────────────── */
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    margin: 0 0 12px;
  }
  thead tr { background: var(--navy); }
  th {
    color: #ffffff;
    font-weight: 600;
    padding: 10px 14px;
    text-align: left;
    letter-spacing: 0.2px;
  }
  td {
    padding: 9px 14px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
  }
  tbody tr:nth-child(even) td { background: var(--row-alt); }
  tbody tr:last-child td { border-bottom: none; }

  /* ── Status badges ──────────────────────────────── */
  .status-bar {
    margin-top: 14px;
    font-size: 13px;
    color: var(--blue);
    font-weight: 600;
    letter-spacing: 0.3px;
  }

  /* ── Cover slide ────────────────────────────────── */
  section.cover {
    background: var(--navy);
    border-top: 4px solid #4A7DDF;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 64px 80px;
  }
  section.cover h1 {
    color: #ffffff;
    font-size: 56px;
    font-weight: 800;
    letter-spacing: -1px;
    margin: 0 0 4px;
    line-height: 1;
  }
  section.cover h2 {
    color: #7BA4E8;
    font-size: 22px;
    font-weight: 400;
    border: none;
    padding: 0;
    margin: 0 0 28px;
    letter-spacing: 0.5px;
  }
  section.cover p {
    color: #A8BFDF;
    font-size: 15px;
    margin: 0 0 4px;
    line-height: 1.5;
  }
  section.cover em { color: #7BA4E8; font-style: normal; }
  section.cover::after { color: transparent; }

  /* ── Divider slide ──────────────────────────────── */
  section.divider {
    background: var(--blue-light);
    border-top: var(--accent-bar);
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  section.divider h2 {
    font-size: 32px;
    border: none;
    padding: 0;
    margin: 0;
    color: var(--navy);
  }
  section.divider p { color: var(--muted); font-size: 17px; margin: 8px 0 0; }

  /* ── Offer slide ────────────────────────────────── */
  section.offer {
    background: var(--blue-light);
    border-top: var(--accent-bar);
  }

  /* ── Gap / tick markers ─────────────────────────── */
  .no  { color: var(--red);   font-weight: 700; }
  .yes { color: var(--green); font-weight: 700; }
---

<!-- _class: cover -->

# Verify
## NSW Property Intelligence

Planning compliance data for every NSW address —
zoning, constraints, DCP controls, satellite analysis.

*For Leigh Caprile — DocuBuild*
*April 2026 — Early access*

---

## The problem your clients face

Pre-DA research is fragmented across six portals.

| What they need | Where it lives today |
|---|---|
| Zone + permitted uses | NSW Planning Portal (often unclear) |
| Development standards | LEP — manual search |
| DCP setbacks, heights, parking | DCP PDF — manual search |
| Flood risk quantified | InfoTrack: **"unknown"** for most properties |
| Biodiversity / riparian constraints | Buried in council GIS, often missed |
| Nearby DA activity | ePlanning portal — no radius search |

> A senior planner spends **2–4 hours** on this before a DA is even scoped. Verify does it in **30 seconds.**

---

## The compliance assessment

Live for **Inner West** (Marrickville, Leichhardt, Ashfield). Portal data for all NSW.

**In one assessment:**
- Zone, height, FSR, lot size — from live LEP
- All SEPP pathways — CDC, BASIX, TOD, Housing SEPP
- DCP provisions filtered by development type (~50–100 relevant provisions)
- Heritage, acid sulfate, key sites — from PostGIS state layer
- Nearby DA activity — 200m radius, last 12 months

**Statement of Environmental Effects (SEE) — in progress**
First-draft SEE structured from the assessment. Gives planners a complete starting point — every relevant provision located, sections pre-organised. Professional judgment stays with the planner.

<p class="status-bar">▸ 3 LGAs deep DCP &nbsp;&nbsp; ▸ All NSW via portal &nbsp;&nbsp; ▸ SEE generation in progress</p>

---

## The spatial layer — what InfoTrack can't tell you

PostGIS database covering **128 NSW LGAs** — every council in the state.

| Layer | What it tells you | InfoTrack / s10.7(2) |
|---|---|---|
| Flood planning area | ARI values (1-in-20 → PMF) for 12 LGAs; named designation for all others | ✗ "unknown" for most |
| Biodiversity sensitivity | BDAR triggered? $15–50k cost, 4–12 month delay | ✗ Not disclosed |
| Riparian land | Waterway setback constraints | ✗ Not disclosed |
| Wetlands | Development highly restricted | ✗ Not disclosed |
| Landslide risk | Geotechnical requirements triggered | ✗ Not disclosed |
| Key sites | Site-specific LEP clause + legislation link | Partial |

This data exists in the NSW state layer. No other tool surfaces it for a specific address at exchange speed.

---

## Satellite analysis — feasibility for every lot

Five products live on the platform. Each answers a specific feasibility question.

| Product | Question answered | Relevant to |
|---|---|---|
| **Granny Flat Feasibility** | Does this lot support a secondary dwelling? Setbacks, area, zone checked. | Builders, investors |
| **Solar Yield** | Roof-level panel yield (kWh/yr), grade A–F, lot-clipped | Solar installers, buyers |
| **Shadow Detector** | Shadow impact on neighbours at equinox/solstice, LEP height compliance | Designers, certifiers |
| **Threat Radar** | DA activity in the council area — what's changing nearby | Investors, builders |
| **Flood Truth** | Sentinel-1 SAR historical inundation — was this lot actually flooded in 2022? | Insurers, buyers |

All five are live and end-to-end tested. April 2026.

---

## Where your clients map to this

| Client type | Primary product | Secondary |
|---|---|---|
| **Builder — pre-DA feasibility** | Verify assessment — zone, DCP controls, SEPP pathways | Granny Flat, Solar Yield |
| **Building certifier** | Verify — compliance check vs DCP/SEPP | Shadow Detector |
| **Town planner** | Verify + SEE generation (in progress) | Full stack |
| **Property acquisition** | Spatial risk table — flood, heritage, biodiversity | Threat Radar |

**The coverage question:** deep DCP is currently Inner West only.

*Which LGAs do your clients work in most? That's what gets built next.*

---

<!-- _class: offer -->

## The offer

**What you get**
- Ongoing early access to the full platform — not a time-limited trial
- Your input shapes which LGAs get deep DCP extraction next
- First-mover pricing: whatever rate you're on when I commercialise is locked

**Revenue share**
Any client you introduce who becomes a paying subscriber — you get a share of their subscription. Terms discussed directly, not in a slide deck.

**What I need from you**
1. Five settled addresses from your recent work — I'll run reports, you compare against what actually happened at settlement
2. Two or three introductions to clients who'd benefit
3. Direct feedback when something's wrong — WhatsApp is fine

This is a partnership, not a sale.

---

## Next steps

**Before our next meeting**
Send me 3–5 settled addresses. I'll have reports ready to review together.

**At the meeting**
1. Walk through one live assessment for an address your clients would recognise
2. Compare report output against what you knew at settlement
3. *Which LGAs matter most for your current pipeline?*

**After the meeting**
Access set up. LGA expansion roadmap updated based on your answer.

---

*Verify — NSW Property Intelligence*
*Decision support for planning professionals. Not a substitute for professional advice or statutory certificates.*
*Early access — April 2026*
