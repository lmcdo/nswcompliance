---
globs:
  - "services/**"
  - "enrichment/**"
  - "src/**"
  - "scripts/**"
---

# Regulatory Data — Never Hardcode

- **NEVER hardcode NSW planning regulatory data** — no zone permitted uses, no SEPP standards, no DCP controls, no infrastructure contribution rates, no parking rates, no setbacks
- All values from: Planning Portal API (`layerintersect`, `zone_full`, `legislation_url`), PostGIS `spatial_overlays`, or extracted provisions with `source_ref` + `effective_date`
- **Why:** LEPs are amended regularly. A hardcoded table is wrong within months.
- If the API doesn't return what you need: surface `legislation_url` and direct the user to the source
- If you see a hardcoded regulatory lookup table anywhere: flag it and replace before shipping
