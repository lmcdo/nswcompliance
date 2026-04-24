---
marp: true
theme: default
size: 16:9
paginate: true
html: true
style: |
  :root {
    --navy:    #0D1B3E;
    --blue:    #1E4FC2;
    --blue-m:  #4A7DDF;
    --blue-l:  #EEF3FF;
    --blue-p:  #F5F8FF;
    --text:    #1A1A2A;
    --muted:   #64748B;
    --border:  #DDE4F0;
    --row-alt: #F7F9FE;
    --red:     #DC2626;
    --red-l:   #FEF2F2;
    --amber:   #D97706;
    --amber-l: #FFFBEB;
    --green:   #059669;
    --green-l: #F0FDF4;
    --teal:    #0891B2;
    --teal-l:  #ECFEFF;
    --purple:  #7C3AED;
    --purple-l:#F5F3FF;
    --orange:  #EA580C;
    --orange-l:#FFF7ED;
  }

  section {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 15px;
    line-height: 1.6;
    color: var(--text);
    background: #ffffff;
    padding: 40px 58px 34px;
    border-top: none;
    box-sizing: border-box;
    position: relative;
  }
  /* Left accent bar instead of top border */
  section::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 5px;
    background: linear-gradient(180deg, var(--blue) 0%, var(--blue-m) 100%);
  }
  section::after { font-size: 11px; color: var(--muted); bottom: 14px; right: 56px; }

  h1 { font-size: 27px; font-weight: 700; color: var(--navy); margin: 0 0 4px; letter-spacing: -0.4px; line-height: 1.2; }
  h2 { font-size: 20px; font-weight: 800; color: var(--navy); margin: 0 0 18px; padding-bottom: 0; border-bottom: none; letter-spacing: -0.3px; position: relative; }
  h2::after { content: ''; display: block; width: 36px; height: 3px; background: var(--blue); border-radius: 2px; margin-top: 6px; }
  h3 { font-size: 11px; font-weight: 700; color: var(--muted); margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0.8px; }

  p { margin: 0 0 10px; }
  ul, ol { margin: 0 0 10px; padding-left: 1.4em; }
  li { margin-bottom: 5px; }
  strong { color: var(--navy); }
  em { color: var(--muted); }

  /* Tables */
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin: 0 0 12px; }
  thead tr { background: var(--navy); }
  th { color: #fff; font-weight: 600; padding: 10px 14px; text-align: left; font-size: 12px; letter-spacing: 0.3px; }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }
  tbody tr:nth-child(even) td { background: var(--row-alt); }
  tbody tr:last-child td { border-bottom: none; }

  .no      { color: var(--red);   font-weight: 700; }
  .yes     { color: var(--green); font-weight: 700; }
  .partial { color: var(--amber); font-weight: 600; }

  /* LGA pill tags */
  .lga-pill {
    display: inline-block;
    background: var(--blue-l);
    color: var(--blue);
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid #C4D4F5;
    margin: 2px 3px 2px 0;
    letter-spacing: 0.2px;
  }

  /* Cards */
  .card { background: white; border: 1.5px solid var(--border); border-radius: 10px; padding: 18px 20px; box-sizing: border-box; }
  .card-hl { background: white; border: 2px solid var(--blue); border-top: 4px solid var(--blue); border-radius: 10px; padding: 18px 20px; box-sizing: border-box; }

  /* Product cards — each with its own accent */
  .prod { background: white; border: 1.5px solid var(--border); border-radius: 10px; padding: 14px 16px; box-sizing: border-box; }
  .prod-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.7px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
  .prod-label::before { content: ''; display: inline-block; width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .prod.green { border-top: 3px solid var(--green); }
  .prod.green .prod-label { color: var(--green); }
  .prod.green .prod-label::before { background: var(--green); }
  .prod.teal  { border-top: 3px solid var(--teal); }
  .prod.teal  .prod-label { color: var(--teal); }
  .prod.teal  .prod-label::before { background: var(--teal); }
  .prod.amber { border-top: 3px solid var(--amber); }
  .prod.amber .prod-label { color: var(--amber); }
  .prod.amber .prod-label::before { background: var(--amber); }
  .prod.purple { border-top: 3px solid var(--purple); }
  .prod.purple .prod-label { color: var(--purple); }
  .prod.purple .prod-label::before { background: var(--purple); }
  .prod.orange { border-top: 3px solid var(--orange); }
  .prod.orange .prod-label { color: var(--orange); }
  .prod.orange .prod-label::before { background: var(--orange); }

  /* Step circles */
  .step-num {
    display: inline-flex; width: 30px; height: 30px; border-radius: 50%;
    background: var(--blue); color: white; font-weight: 800; font-size: 14px;
    align-items: center; justify-content: center; margin-bottom: 10px;
  }

  /* Cover */
  section.cover {
    background: var(--navy);
    display: flex; flex-direction: column; justify-content: center;
    padding: 52px 72px;
    overflow: hidden;
  }
  section.cover::before { display: none; }
  section.cover::after  { color: transparent; }
  /* Decorative circle */
  section.cover .deco {
    position: absolute;
    right: -80px; top: -80px;
    width: 420px; height: 420px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(74,125,223,0.18) 0%, transparent 70%);
    pointer-events: none;
  }
  section.cover h1 { color: #fff; font-size: 68px; font-weight: 800; letter-spacing: -2.5px; margin: 0 0 4px; line-height: 1; }
  section.cover h2 { color: #7BA4E8; font-size: 20px; font-weight: 400; margin: 0 0 28px; letter-spacing: 0.4px; }
  section.cover h2::after { display: none; }
  section.cover p { color: #A8BFDF; font-size: 14.5px; margin: 0 0 4px; }
  section.cover em { color: #7BA4E8; font-style: normal; }
  section.cover strong { color: white; }

  /* Offer slide */
  section.offer { background: var(--blue-p); }
  section.offer::before { background: linear-gradient(180deg, var(--blue) 0%, var(--blue-m) 100%); }

  /* Closing */
  section.closing {
    background: var(--navy);
    display: flex; flex-direction: column; justify-content: center;
    padding: 56px 72px;
  }
  section.closing::before { display: none; }
  section.closing::after  { color: transparent; }
  section.closing p  { color: #A8BFDF; font-size: 15px; margin: 0 0 6px; }
  section.closing em { color: #7BA4E8; font-style: normal; }
---

<!-- _class: cover -->

<div class="deco"></div>

<div style="display: grid; grid-template-columns: 1fr 200px; gap: 52px; align-items: center; width: 100%; position: relative; z-index: 1;">
<div>

# Verify
## NSW Property Intelligence

Site feasibility for residential builders —<br>zone, setbacks, SEPP pathways, constraints.

*For Leigh Caprile — DocuBuild*
*April 2026 — Early access*

</div>
<div style="display: flex; flex-direction: column; gap: 12px;">

<div style="border: 1px solid rgba(122,164,232,0.35); border-radius: 12px; padding: 16px 18px; text-align: center; background: rgba(255,255,255,0.04);">
<div style="font-size: 44px; font-weight: 800; color: #7BA4E8; line-height: 1; letter-spacing: -1px;">30s</div>
<div style="font-size: 11px; color: #6E92C4; margin-top: 4px; letter-spacing: 0.3px; text-transform: uppercase;">per site check</div>
</div>

<div style="border: 1px solid rgba(122,164,232,0.35); border-radius: 12px; padding: 16px 18px; text-align: center; background: rgba(255,255,255,0.04);">
<div style="font-size: 44px; font-weight: 800; color: #7BA4E8; line-height: 1; letter-spacing: -1px;">128</div>
<div style="font-size: 11px; color: #6E92C4; margin-top: 4px; letter-spacing: 0.3px; text-transform: uppercase;">LGAs spatial risk</div>
</div>

<div style="border: 1px solid rgba(122,164,232,0.35); border-radius: 12px; padding: 16px 18px; text-align: center; background: rgba(255,255,255,0.04);">
<div style="font-size: 44px; font-weight: 800; color: #7BA4E8; line-height: 1; letter-spacing: -1px;">13</div>
<div style="font-size: 11px; color: #6E92C4; margin-top: 4px; letter-spacing: 0.3px; text-transform: uppercase;">Sydney LGAs setbacks</div>
</div>

</div>
</div>

---

## Before your builders commit to a site

<div style="display: grid; grid-template-columns: 1fr 210px; gap: 28px; align-items: start;">
<div>

<p style="font-size: 14px; color: var(--muted); margin-bottom: 12px;">Most site constraints surface <strong style="color:var(--red);">after</strong> the builder has committed. That's when they're expensive.</p>

| What they need to know | Cost of finding out late |
|---|---|
| Zone — what can be built? CDC or DA pathway? | DA when CDC was available — 6–12 months added |
| DCP setbacks — does the design fit? | Redesign after CC is submitted |
| Biodiversity constraint on the lot? | BDAR = $15–50k, 4–12 month delay |
| Flood planning area designation? | <span class="no">InfoTrack "unknown" for most addresses</span> |
| Heritage or key site overlay? | Site-specific LEP clause changes everything |

</div>
<div>

<div style="background: linear-gradient(135deg, var(--green-l) 0%, #DCFCE7 100%); border: 1.5px solid #86EFAC; border-radius: 12px; padding: 20px 16px; text-align: center;">
<div style="font-size: 11px; color: var(--green); font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Verify surfaces this</div>
<div style="font-size: 48px; font-weight: 800; color: var(--green); line-height: 1; letter-spacing: -1px;">30s</div>
<div style="font-size: 13px; color: #374151; margin-top: 10px; line-height: 1.4;"><strong>Before they sign.</strong><br><span style="color:var(--muted);">Not after.</span></div>
</div>

</div>
</div>

---

## What Verify returns — any NSW address

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 4px;">
<div>

**One address, 30 seconds:**

- Zone + permitted uses — live LEP, all NSW
- SEPP pathway — CDC, DA, Housing Code, BASIX, TOD: which applies and why
- **Numeric DCP setbacks** — front, side, rear for dwelling house + secondary dwelling
- Spatial constraints — flood, biodiversity, riparian, heritage, key sites
- Nearby DA activity — 200m radius, last 12 months

<div style="margin-top: 14px; display: flex; flex-wrap: wrap; gap: 6px;">
<span style="background:var(--navy); color:white; font-size:11px; font-weight:600; padding:4px 12px; border-radius:20px;">Zone / SEPP → All NSW</span>
<span style="background:var(--blue); color:white; font-size:11px; font-weight:600; padding:4px 12px; border-radius:20px;">Setbacks → 13 Sydney LGAs</span>
<span style="background:var(--teal); color:white; font-size:11px; font-weight:600; padding:4px 12px; border-radius:20px;">Spatial risk → 128 LGAs</span>
</div>

</div>
<div>

<div style="background: var(--blue-l); border: 1.5px solid #C4D4F5; border-radius: 10px; padding: 16px 18px;">
<div style="font-size: 11px; font-weight: 700; color: var(--blue); text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 10px;">DCP setbacks extracted for</div>
<div style="display: flex; flex-wrap: wrap;">
<span class="lga-pill">Ashfield</span>
<span class="lga-pill">Blacktown</span>
<span class="lga-pill">Campbelltown</span>
<span class="lga-pill">Canterbury-Bankstown</span>
<span class="lga-pill">Cumberland</span>
<span class="lga-pill">Hornsby</span>
<span class="lga-pill">Ku-ring-gai</span>
<span class="lga-pill">Liverpool</span>
<span class="lga-pill">Marrickville</span>
<span class="lga-pill">Northern Beaches</span>
<span class="lga-pill">Penrith</span>
<span class="lga-pill">Waverley</span>
<span class="lga-pill">Woollahra</span>
</div>
<div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #C4D4F5; font-size: 12px; color: var(--blue);">
New LGAs added in days. Tell me where your builders are working.
</div>
</div>

</div>
</div>

---

## The spatial layer — what InfoTrack can't tell you

<p style="font-size: 13.5px; color: var(--muted); margin: -12px 0 14px;">PostGIS database — 128 NSW LGAs. Every council in the state. Surfaces constraints InfoTrack marks as "unknown."</p>

| Layer | What it tells you | InfoTrack / s10.7(2) |
|---|---|---|
| Flood planning area | ARI values (1-in-20 → PMF) for 12 LGAs; named designation for all others | <span class="no">✗ "unknown" for most</span> |
| Biodiversity sensitivity | BDAR triggered? $15–50k cost, 4–12 month delay | <span class="no">✗ Not disclosed</span> |
| Riparian land | Waterway setback constraints | <span class="no">✗ Not disclosed</span> |
| Wetlands | Development highly restricted | <span class="no">✗ Not disclosed</span> |
| Landslide risk | Geotechnical requirements triggered | <span class="no">✗ Not disclosed</span> |
| Key sites | Site-specific LEP clause + legislation link | <span class="partial">Partial</span> |

<div style="margin-top: 14px; background: var(--navy); border-radius: 8px; padding: 12px 18px; color: white; font-size: 13.5px;">
This data exists in the NSW state layer. <strong>No other tool surfaces it per-address before a builder commits to a site.</strong>
</div>

---

## Five satellite analyses — alongside Verify

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px;">

<div class="prod green">
<div class="prod-label">Granny Flat Feasibility</div>
<p style="font-size: 13px; margin-bottom: 4px;">Does this lot support a secondary dwelling? Zone, setbacks, area — checked against DCP and SEPP Housing 2021 simultaneously.</p>
<span style="font-size: 11.5px; color: var(--muted);">Builders scoping Class 1 residential sites</span>
</div>

<div class="prod teal">
<div class="prod-label">Flood Truth</div>
<p style="font-size: 13px; margin-bottom: 4px;">Sentinel-1 SAR satellite data — was this lot actually inundated in 2022? Not a flood zone label. Actual historical flooding.</p>
<span style="font-size: 11.5px; color: var(--muted);">Builders, insurers, OC risk assessment</span>
</div>

<div class="prod amber">
<div class="prod-label">Threat Radar</div>
<p style="font-size: 13px; margin-bottom: 4px;">DA activity in the council area — what's being approved nearby and what's changing in the market.</p>
<span style="font-size: 11.5px; color: var(--muted);">Developers scoping new sites</span>
</div>

<div class="prod purple">
<div class="prod-label">Shadow Detector</div>
<p style="font-size: 13px; margin-bottom: 4px;">Shadow impact on neighbours at equinox/solstice. LEP height compliance check.</p>
<span style="font-size: 11.5px; color: var(--muted);">Designers, building certifiers</span>
</div>

<div class="prod orange" style="grid-column: span 2;">
<div class="prod-label">Solar Yield</div>
<p style="font-size: 13px; margin-bottom: 4px;">Roof-level panel yield (kWh/yr), grade A–F, lot-clipped. Quantified, not estimated — adds tangible value to a site assessment.</p>
<span style="font-size: 11.5px; color: var(--muted);">Buyers, builders adding value to a site</span>
</div>

</div>

---

## Verify + DocuBuild — the full project lifecycle

<div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 0; margin-top: 14px; align-items: stretch;">

<div style="background: var(--blue-l); border: 1.5px solid #C4D4F5; border-radius: 10px 0 0 10px; padding: 20px 22px;">
<div style="font-size: 11px; font-weight: 700; color: var(--blue); text-transform: uppercase; letter-spacing: 0.7px; margin-bottom: 12px;">Verify — before the project starts</div>
<ul style="font-size: 13.5px; margin: 0; padding-left: 1.3em;">
<li>Zone — what can be built here?</li>
<li>SEPP pathway — CDC or full DA?</li>
<li>Numeric setbacks — does the design fit?</li>
<li>Spatial risk — flood, biodiversity, heritage</li>
<li>Granny flat feasibility</li>
</ul>
<div style="margin-top: 12px; font-size: 12.5px; color: var(--blue); font-style: italic;">Site cleared → proceed with confidence.<br>Site flagged → don't find out mid-project.</div>
</div>

<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 0 14px; background: white; border-top: 1.5px solid var(--border); border-bottom: 1.5px solid var(--border);">
<div style="font-size: 22px; color: var(--muted);">→</div>
<div style="font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; text-align: center; line-height: 1.3;">Consent<br>granted</div>
</div>

<div style="background: #F8F9FA; border: 1.5px solid var(--border); border-radius: 0 10px 10px 0; padding: 20px 22px;">
<div style="font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.7px; margin-bottom: 12px;">DocuBuild — after approval</div>
<ul style="font-size: 13.5px; margin: 0; padding-left: 1.3em; color: var(--text);">
<li>CC documentation and hold points</li>
<li>QA evidence capture during construction</li>
<li>OC handover — complete and compliant</li>
<li>O&M package for the building owner</li>
</ul>
<div style="margin-top: 12px; font-size: 12.5px; color: var(--muted); font-style: italic;">The last 10% of the project.<br>Handled properly.</div>
</div>

</div>

<div style="margin-top: 16px; background: var(--navy); border-radius: 8px; padding: 13px 22px; color: white; font-size: 14px; text-align: center;">
Your builders use DocuBuild to close out the current project. <strong>Verify is for the next one they're already scoping.</strong>
</div>

---

<!-- _class: offer -->

## The offer

<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-top: 10px;">

<div class="card">
<h3>What you get</h3>
<ul style="font-size: 13.5px;">
<li>Full access — Verify + all five satellite products, ongoing</li>
<li>Your builders' LGAs shape what gets expanded next</li>
<li>First-mover pricing locked at commercialisation</li>
</ul>
</div>

<div class="card-hl">
<h3 style="color: var(--blue);">Revenue share</h3>
<p style="font-size: 13.5px;">Any builder client you introduce who becomes a paying subscriber — <strong>you earn a share of their subscription.</strong></p>
<p style="font-size: 12.5px; color: var(--muted); margin: 0;">Discussed directly. Not in a slide deck.</p>
</div>

<div class="card">
<h3>What I need from you</h3>
<ol style="font-size: 13.5px;">
<li>Run it on a few addresses from projects you've managed — tell me if it looks right</li>
<li>Introduce it to one or two builders when you're comfortable</li>
<li>Direct feedback — WhatsApp is fine</li>
</ol>
</div>

</div>

<div style="margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
<div style="background: var(--green-l); border-left: 3px solid var(--green); border-radius: 0 8px 8px 0; padding: 10px 16px; font-size: 13px; color: #065F46;">
<strong>For you:</strong> a tool your builder clients find genuinely useful, with upside when they pay for it.
</div>
<div style="background: var(--blue-l); border-left: 3px solid var(--blue); border-radius: 0 8px 8px 0; padding: 10px 16px; font-size: 13px; color: var(--navy);">
<strong>For me:</strong> real usage from residential builders, and feedback from someone who knows this work.
</div>
</div>

---

## Next steps

<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; margin-top: 14px;">

<div class="card">
<div class="step-num">1</div>
<h3>You run it</h3>
<p style="font-size: 13.5px;">I'll set you up with access. Run Verify on a handful of addresses from your projects — ones where you know the outcome. See if it looks right.</p>
</div>

<div class="card-hl">
<div class="step-num">2</div>
<h3>We walk through it</h3>
<ul style="font-size: 13.5px;">
<li>Live assessment on an address your builders would recognise</li>
<li>Compare what Verify shows against what you know</li>
<li style="color: var(--muted); font-style: italic;">Which LGAs are your builders working in?</li>
</ul>
</div>

<div class="card">
<div class="step-num">3</div>
<h3>Your clients benefit</h3>
<p style="font-size: 13.5px;">Once you're comfortable, introduce it to one builder. I set them up. When they eventually pay, you earn from that.</p>
</div>

</div>

<div style="margin-top: 16px; background: var(--blue-l); border-radius: 8px; padding: 12px 20px; display: flex; gap: 12px; align-items: center;">
<div style="width: 8px; height: 8px; border-radius: 50%; background: var(--blue); flex-shrink: 0;"></div>
<p style="margin: 0; font-size: 13px; color: var(--navy);">No pressure, no timeline. You decide when you're confident enough to share it. WhatsApp or email — whatever's easiest.</p>
</div>

---

<!-- _class: closing -->

<div>

*Verify — NSW Property Intelligence*

*Decision support for builders, certifiers, and planning professionals.*
*Not a substitute for professional advice or statutory certificates.*

*Early access — April 2026*

</div>
