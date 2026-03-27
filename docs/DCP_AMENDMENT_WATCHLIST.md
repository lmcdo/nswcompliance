# DCP Amendment Watchlist

Tracks known pending DCP amendments, planning proposals, and future chapters
that are not yet adopted and therefore not in the compliance engine.

**How to use:**
- Check this list when onboarding a new LGA — some items may have since been adopted
- When an item is adopted: remove from this list, run the populate script for the new chapter, and the weekly hash monitor takes over from there
- The existing hash monitor (`r2_monitor.py`) handles post-adoption PDF changes automatically

---

## Pending Amendments

### Ku-ring-gai — DCP Part 14 Local Character Areas
- **Status:** On public exhibition (endorsed at Council meeting 22 July 2025), not yet adopted
- **What it adds:** Enforceable design controls for 8 Local Character Areas (Ridge and Centres, Green Fingers, Western Interface, West Pymble, Northern Plateau, Eastern Interface, Western Slopes, North Turramurra Table)
- **Why it matters:** Once adopted, these 8 areas will need boundary GIS data and a new chapter extraction. Boundaries are not yet published as GIS — will need digitising or council request.
- **Council page to check:** https://www.krg.nsw.gov.au/Development/Planning-controls/Development-Control-Plan
- **Reference:** FOKE submission Sept 2025 confirms exhibition stage. Council meeting GB.11 of 22 Jul 2025.
- **Action when adopted:** Add `section-b-part-14-local-character-areas` chapter to `populate_ku_ring_gai_registry.py`, request GIS boundary data from KRG, georeference from PDF if not available.

---

## Notes on Coverage Gaps (Not Pending — Just Not Yet Onboarded)

These are not pending amendments but known gaps in current coverage:

| LGA | Gap | Action Needed |
|-----|-----|---------------|
| Waverley | 7 precinct boundaries (E1–E7) not yet georeferenced | QGIS — images in `waverley/images/` |
| Woollahra | Residential precinct boundaries (Chapter B1) not yet georeferenced | QGIS — `woollahra/chapter-b1-residential-precincts.pdf` |
| Ku-ring-gai | 15 urban precinct boundaries (14A–14O) not yet georeferenced | QGIS — PNGs in `ku-ring-gai/precinct-maps/` |
| Randwick | Full DCP not yet onboarded | No open GIS data for precincts — QGIS or council request |
| All LGAs | HCA boundaries | Covered by NSW state EPI Heritage layer — no per-council work needed |
