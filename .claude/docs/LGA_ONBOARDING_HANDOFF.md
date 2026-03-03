# LGA Onboarding — What YOU Need To Do

This is the human-facing checklist. Everything not listed here is done by Claude.
The technical pipeline details are in `LGA_EXTRACTION_RUNBOOK.md`.

---

## Per LGA — Your 4 Steps

### Step 1 — Download the PDFs (15–30 min)

Go to the council's DCP page. Download all chapter PDFs into the right local folder.

| LGA | Your destination folder | Council URL |
|-----|------------------------|-------------|
| Woollahra | `woollahra/` | https://www.woollahra.nsw.gov.au/Building-and-development/Development-rules/dcps-background |
| City of Sydney | `city-of-sydney/` | https://www.cityofsydney.nsw.gov.au/development-control-plans/sydney-dcp-2012 |
| Ku-ring-gai | `ku-ring-gai/` | https://www.krg.nsw.gov.au/Planning-and-development/Planning-policies-and-guidelines/Ku-ring-gai-Development-Control-Plan |

Filenames matter — they must match exactly what the populate script expects.
Tell Claude: "I've downloaded the PDFs for [LGA]" and Claude will check what's expected.

---

### Step 2 — Get the direct PDF download URLs (10 min)

While still on the council website, for **each PDF**:
- Right-click the download link → "Copy Link Address"
- Paste into the `populate_<council>_registry.py` script where you see `<FILL_IN>`

This URL is what the pipeline uses to record where the PDF came from (provenance).
If the council site only has a redirect (no direct .pdf URL), just use the council page URL instead.

Tell Claude: "URLs filled in for [LGA]" and Claude takes over from here.

---

### Step 3 — Open-book QA (20–30 min, after Claude runs extraction)

Claude will run the extraction and then ask you to do this.

1. Claude gives you 10 provision texts from the database — read them on screen
2. Open the actual DCP PDF alongside (the one you downloaded)
3. For each provision, flip to that section in the PDF and answer:
   - Does the extracted text match what's in the PDF? (No missing paragraphs, no garbage lines)
   - Does the section heading match?
   - Are any numeric values readable? (Not garbled like "6 0 0 { m } ^ 2")
4. Note anything that looks wrong — tell Claude and it will fix the config

**You don't need to check every provision — just 10 across different chapters.**

---

### Step 4 — Spot-check the UI (5 min, after Claude deploys)

1. Go to the live site
2. Enter a known address in the LGA (Claude will give you one)
3. Confirm DCP provisions appear in the assessment results
4. For heritage addresses: confirm heritage provisions appear

Done. Move to the next LGA.

---

## What Claude Does (Everything Else)

After you complete Steps 1 and 2:

1. Profiles the PDF structure with `survey_dcp.py` — checks if section headings are detected correctly
2. If not detected: adds manual page ranges to the extraction script
3. Runs populate script — uploads PDFs to R2, inserts chapter registry rows
4. Runs extraction dry-run — checks section counts per chapter
5. Runs full extraction — inserts provisions into database
6. Runs enrichment — tags each provision with layer, topic, site condition
7. Checks enrichment quality (SQL queries — layer distribution, untagged rate)
8. Runs formatting QA (`verify_dcp_formatting.py`) — catches known artifact patterns
9. If artifacts found: adds config entry to `dcp-format-configs.ts` and reruns
10. Asks you for the open-book QA (Step 3 above)
11. Deploys and gives you a test address (Step 4 above)

---

## What Can Go Wrong (And What Happens)

| Problem | Who handles it | What happens |
|---------|---------------|--------------|
| SECTION_RE doesn't detect section headings | Claude | Adds manual page ranges, reruns |
| PDF is scanned (image-based) — no text | You + Claude | Flagged immediately. Need separate OCR or manual entry. |
| Artifact lines in provision text | Claude | Adds config entry, reruns QA |
| Wrong layer/topic tagging | Claude | Fixes enrichment config, reruns enrichment |
| Section counts look wrong (Step 3 QA) | You flag, Claude fixes | Fix page ranges or enrichment config |
| LGA not showing in UI | Claude | Checks `lga-configs/index.ts` aliases |

---

## Waverley — Status (2026-03-04)

Waverley has NOT been extracted yet. What's ready vs what you need to do:

**Fixed (no action needed):**
- Page-range mode is now PRIMARY for Waverley — SECTION_RE is bypassed entirely. The 297 TOC matches issue is resolved.
- All 33 section boundaries verified against the actual PDF (B1–B17, C1–C2, D1–D2, E1–E7, F1–F5). Previously had wrong page offsets (+8 pages off) and was missing B15, E6, E7, F3, F4, F5.

**Still needed (your action — Step 2):**
1. Go to waverley.nsw.gov.au, find the DCP 2022 PDF download link
2. Right-click → Copy Link Address
3. Open `scripts/populate_waverley_registry.py`, find `WAVERLEY_COUNCIL_URL` at the top, replace `<FILL_IN>` with the URL
4. Tell Claude "Waverley URL filled in" — Claude runs the rest

---

## Batch 1 Priority Order

1. Woollahra (10 chapters, relatively clean structure)
2. City of Sydney (6 PDFs, larger)
3. Ku-ring-gai (9 topic-based DCPs)
4. Waverley (needs council URL filled in — see above)
