# Data Quality Tracker

**Purpose:** Track data quality issues systematically across Claude sessions.

**Last Updated:** 2026-08-15
**Session:** DQ-54 fixed (#930) and the ledger made executable — `.claude/dq_checks.json` + `scripts/dq_check.py` now enforce every status in BOTH directions, so a row cannot claim fixed while broken, nor sit open after it has quietly been fixed.

> **Statuses here are enforced, not asserted.** `python scripts/dq_check.py` runs each row's check and fails if a status disagrees with reality. **31 of 79 rows carry a real check** (2026-08-15, was 4 of 55); the other 48 carry an explicit `check: null` plus a reason, and that gap is printed on every run rather than counted as coverage. Adding a row without an entry in `dq_checks.json` fails the coverage test.
>
> **Of the 48 without a check, only ONE is open** — DQ-58, whose stated reason was tested against the schema on 2026-08-15 and found correct. The other 47 are already fixed, accepted, or not defects. So the gap is not undone work; it is **38 fixed rows that cannot prove they stayed fixed**, which is a regression risk, not a backlog.
>
> **The ratchets no longer mark their own homework (2026-08-15).** Every cap used to live in the file it policed, so raising the bar was a one-line edit that passed. Two practices now compare against `origin/main`: a cap may **fall, never rise**, and a row that is **new or newly `fixed` must carry a check** — that one names the offending row rather than counting, because the old message admitted it "cannot tell WHICH row is new". The enforcement is itself tested (`tests/test_dq_ratchet_enforcement.py`, 18 tests, mutation-verified: stubbing both functions to `return []` kills 5 of them). A guard with no test is the thing this ledger exists to stop.

---

## Quick Status

| Issue | Status | Priority |
|-------|--------|----------|
| DQ-127: **The 'Data currency' panel lists every council's LEP under any property.** `InstrumentCurrency` on /assessment calls `/api/instrument-currency?council=<c>`, which returns `WHERE ic.council = $1 OR ic.council IS NULL` -- and `instrument_currency` holds **138 LEP rows across 23 councils (Waverley's own among them) with council NULL**, so 'statewide' includes Bayside, Blacktown, Burwood ... (Waverley: 158 rows, each LEP repeated up to 7 times by repeated verification runs). The panel's status dot takes the WORST verified date across all of them, so a property's currency is coloured by other councils' LEPs. Found 2026-10-04 while fixing DQ-123. | 🔴 Open until deployed — `python scripts/dq_probe_app_defects.py --id DQ-127` = 22 other councils' LEPs listed for a Waverley property on production (exit 1). **Route fixed 2026-10-04:** council NULL still means statewide for SEPPs; an LEP is shown only for the council `instrument_registry.council` names (or, where that is NULL -- inner_west_lep_2022 -- the slug its key starts with), or that council's `lga_registry.parent_lga` (marrickville/leichhardt/ashfield -> inner_west), one row per instrument at its latest check. The query run read-only against production gives waverley 4 rows (was 158), marrickville 4 incl. inner_west_lep_2022, city_of_sydney 3 (no LEP row exists for it, so none is shown). No data was changed. | P2 — the currency status shown for a property reflects instruments that do not apply to it |
| DQ-126: **Woollahra D5 rows are tagged by the chapter's INTERNAL numbering and fall through.** Chapter D5 (Double Bay Centre) numbers its own sections A2.x, so rows headed '# A2.5.3 Built form south of Kiaora Lane' resolve to Part 'A2' in the `parts` path of ApplicabilityTagger, find no entry, strip to 'A', find none, and land on no_config -- although document_id says chapter_d5. 21 of D5's served scope keys (9 dev type, 12 zone) are no_config this way. The document_id fallback only runs when NO section code is found; it should arguably win when the code found belongs to a different chapter than the document. Not fixed: it changes tagging for every `parts` council and needs a retag. | ✅ **FIXED 2026-10-04.** `python scripts/dq_probe_app_defects.py --id DQ-126` reads **0** (exit 0). Code: #1211 -- when a row's document names a chapter and the heading's code belongs to another chapter, the document's chapter wins. Retag applied from a worktree at merged origin/main 1ad5e3ed: `retag_applicability_slug_docids.py --councils woollahra --apply --expect-narrowings 16`; 6,836 rows restamped, 236 values changed, 16 served rows narrowed ALL -> E1, all `chapter_d5_double_bay_centre`. All 54 served D5 rows now read ['E1'] config_specific. Backup table `regulatory_provisions_dq33_backup_20261004_195239`; rollback: `UPDATE regulatory_provisions t SET v2_applicable_zones = b.v2_applicable_zones, v2_applicable_dev_types = b.v2_applicable_dev_types, v2_zone_source = b.v2_zone_source, v2_dev_type_source = b.v2_dev_type_source FROM regulatory_provisions_dq33_backup_20261004_195239 b WHERE t.id = b.id;`. Waverley, Northern Beaches and Parramatta dry runs were unchanged; Parramatta's 178 no_config keys are a different family and stay outside this row. Previously read 13. | P2 — rules for one centre are served to every zone and development type in the municipality |
| DQ-125: **Raw HTML table markup is served as rule text.** Waverley C2's first provision (page 191) ends 'CONTENTS --- **Table 1** (Page 202) <table> <thead> <tr> <th>Zoning</th> ...' -- the extractor's table markup is shown to the reader as literal tags, and the table it encodes is mostly empty cells. | ✅ **FIXED 2026-10-04 by rendering the tables, not deleting them.** Measured first: **1,064** served rules held **2,538** tables, every one closed, with no tag but table/thead/tbody/tr/th/td and no script, image, link or handler anywhere. The cells are the council's values (a Waverley side-setback table: Ground 0.9m, Second 1.5m), so stripping tags would have split values from their row labels, and a re-extraction was a 15-council pipeline run for a display defect. `lib/provision-tables.ts` parses rows and cells into strings that React renders as a `<table>` -- nothing is injected as HTML; collapsed previews and the PDF export write the same rows as `cell | cell` text. Every view on the provisions path printed the markup literally before (screen list, collapsed preview, PDF); the six `dangerouslySetInnerHTML` views elsewhere already rendered it as HTML. ⚠ **The check changed with the fix:** a row count of `<table` could never clear without deleting the council's values, so `--id DQ-125` now goes red when a served-path renderer stops handling tables (forced on the PDF renderer: exit 1) or a served rule holds a `<table>` without `</table>` (reads **0**). Previously read 1,064 served rules. | P3 — unreadable text in a served rule; no value is wrong, but the table's content is lost |
| DQ-124: **'The full chapter text for this council is not loaded yet' is printed above 279 provisions of chapter text.** Waverley, 60 Hall Street, Bondi Beach, 2026-10-04: the sentence sits under the DCP Numeric Controls panel while the DCP Structure panel lists 279 provisions across A1-F5. | ✅ **FIXED 2026-10-04.** `python scripts/dq_probe_app_defects.py --id DQ-124` exits 0. `DcpStructuredControls` takes `chapterTextLoaded`; `ProvisionsByTocStructure` passes it where the controls sit beneath loaded chapter text, so the 'full chapter text ... not loaded yet' note appears only in the no-text fallback. Previously read unconditional. | P3 — contradictory copy; tells the reader the text they are looking at does not exist |
| DQ-123: **Waverley's page names two different plans at once.** On 60 Hall Street, Bondi Beach (2026-10-04) the DCP tab header reads 'Waverley DCP 2012 · Monitored weekly · Last verified 29 June 2026 · Currency data overdue -- weekly check has not run recently', while the numeric controls underneath say 'Source: Waverley DCP 2022' and the structure panel is 'Waverley DCP 2022'. Either the header reads a stale registry/currency row or the label is hardcoded; not traced. | ✅ **FIXED 2026-10-04.** `python scripts/dq_probe_app_defects.py --id DQ-123` exits 0: the hardcoded `councilDcpNames` table is gone. `/api/provisions/for-property` now returns `meta.dcp_currency.dcp_names` -- the registry's own `dcp_name` for the chapters the served rules come from, most rules first -- and the currency line prints those. Measured against the registry that day, the old table was wrong for 8 councils (bayside 2023 vs 2022, campbelltown 2018 vs Campbelltown (Sustainable City) DCP 2015, georges_river 2022 vs 2021, hornsby 2013 vs 2024, northern_beaches 'Northern Beaches DCP 2022' vs Warringah DCP 2011, randwick 2013 vs 2025, strathfield 2005 vs 2026, waverley 2012 vs 2022); parramatta and ku_ring_gai were not wrong, only less specific ('(Amendment 4)', '2024'). The Waverley and Randwick FAQs in `lib/lga-data/verify-lgas.ts` now name DCP 2022 and DCP 2025. Previously read 8 councils. Seen alongside: `/api/instrument-currency` lists every council's LEP -- logged as DQ-127. ⚠ Ku-ring-gai's registry carries two spellings ('Ku-ring-gai DCP 2024', 'Ku-ring-gai DCP'), so a property served from both shows both. | P2 — a reader is told the plan is a decade old and its currency check has lapsed, beside rules from the current plan |
| DQ-122: **The property lookup returns a DIFFERENT property from the address asked for.** Found 2026-10-04 on verify.plotdetect.com.au/assessment while checking Woollahra zones, then confirmed against the server directly, so it is not browser timing: `GET /api/property?address=700 New South Head Rd, Rose Bay NSW 2029` returns `data.address = 893 NEW SOUTH HEAD ROAD ROSE BAY 2029` (R2, 946 m2). In the UI the address box held the right address after a 6 s wait and the page still sent that exact string; the server picked the other lot. A second case compounds it: Google Places resolves the suggestion '235 New South Head Road, Edgecliff' to '235 New South Head Rd, Point Piper NSW 2027' (wrong suburb), and the server then returns `582 NEW SOUTH HEAD ROAD POINT PIPER 2027` -- a different number, where it should have said not found. Both failures are on New South Head Road, which runs through several suburbs; 7 of 9 lookups that day resolved correctly, including unit and range addresses (SHOP 24A 203-233, 674-680). Route: frontend-nextjs/app/api/property/[address]/route.ts and whatever it calls to match an address to a lot -- not yet read. | ✅ **FIXED 2026-10-04 (#1213, live the same evening).** `python scripts/dq_probe_app_defects.py --id DQ-122` exits 0 against production: every address returns itself, or a 404 saying not found where the NSW address register has no such address -- '700 New South Head Rd, Rose Bay' now answers 'No property matching ... was found'. Cause: `searchProperty` scored the Portal's fuzzy candidates on postcode and street words and never compared the house number; the valuation fallback took any candidate. Now a candidate must match the street number (or a range holding it), street name and type, and the postcode -- or, without one, the suburb; an address with no number matches nothing. A Portal outage (429, timeout) is a service error, never 'not found'. Measured on 224 real lookups across 14 suburbs, with and without postcodes: every address found itself. Previously read 3 of 6. | P1 — every control, zone and DCP rule on the page belongs to another property, and nothing on screen says so |
| DQ-121: **Every scope_evidence quote was checked for EXISTENCE and never for TRUTH.** DQ-115 requires a declared applicability key to carry the council's own sentence as data, and it counts the string. It cannot tell a transcription from an invention, so ~160 quotes across `enrichment/config` rested entirely on whoever typed them — a HARD FILTER on what a property is shown (`for-property/route.ts:1012` and `:1222`) resting on words nobody had verified. This row asks the fidelity gate's question of the config instead: are these words in that document? ⚠ **The first run found three real errors.** Warringah section A.6 was misquoted as placing the built-form controls in "Part C, D and E" when it reads "contained in Part B Built Form Controls" — and a conclusion had been built on the misquote, namely that A.6 omits Part B. The same re-read surfaced an exclusion nobody had recorded: "the provisions of Part B Built Form Controls do not apply to those areas of land specified in Part G, except for land identified in Part G10". And two Campbelltown quotes cannot be verified contiguously at all, because the PDF's text layer interleaves an adjacent column into the sentence. ⚠ **It found two bugs in itself first** — `loose()` stripped accents instead of folding them, so a PDF printing "café" could never match a config spelling it "cafe"; and the span extractor harvested any long quoted run, asserting our own prose split on an apostrophe against the PDF and demanding that section headings quoted precisely because they are ABSENT be present. A probe that cries wolf gets switched off, so its precision is what `tests/test_dq_probe_scope_evidence_fidelity.py` covers. | 🔴 **OPEN.** `python scripts/dq_probe_scope_evidence_fidelity.py`. Reports **47 spans OK and 0 MISSING** across campbelltown, warringah, waverley and wollongong after the corrections; the remaining population is UNPARSED — evidence that asserts a scope but marks no `verbatim:`, so nothing can check it. Clears when every entry carrying evidence marks a checkable quotation and every span is found. ⚠ **`requires` is the fetched-PDF cache** (`.cache/scope_pdfs`), so a machine that has never run the fetch reports UNKNOWN rather than red — DQ-32's precedent, where could-not-look read as found-something and turned main red on 2026-08-12. **UNRESOLVED is not a pass either**: city_of_sydney section-1/2/5/6 carry `r2_public_pdf_url` NULL, so their quotes cannot be checked at all. NOT a per-PR gate — the first run fetches ~111 PDFs, the same reason `verify_extraction_fidelity.py` is not one. | P1 — a hard filter on a real address resting on a sentence nobody verified |
| DQ-120: **Sydney DCP 2012 says it does not cover eight areas, and we serve it there anyway.** Section 1 clause 1.4 page 4: the plan applies to 'the land identified in Figure 1.1 ... where the City of Sydney is the consent authority'. Figure 1.1 page 5 excludes **Barangaroo, Bays Precinct/Wentworth Park, Harold Park, Redfern/Waterloo, Various Sites (South Sydney), Green Square Town Centre, Moore Park Showground and Glebe (Affordable Housing)** — each keeps its own plan. We serve by COUNCIL, so a Green Square property is shown Sydney DCP 2012 controls that do not bind it, and the plan that does is absent. Measured 2026-10-03: **zero** documents match any of the eight. ⚠ **Why a row and not a fix** — the exclusion is a MAPPED BOUNDARY and no column carries it: `v2_applicable_zones` is a zone list, `v2_precinct_id` holds locality-statement clause numbers like `2.1.1` rather than place extents, and inventing boundaries breaks the standing rule against guessing real-world geography. | 🔴 **OPEN — reads 8 of 8.** `python scripts/dq_probe_live.py --id DQ-120`. Clears as each area's own plan is ingested, or when the Figure 1.1 boundary is acquired. **It cannot be cleared by editing `city_of_sydney_config.py`** — no key there can express a mapped boundary. | P1 — wrong plan's rules on a real address, and the right plan missing |
| DQ-119: **A chapter's own contents page said the reader missed its sections, and nothing ever counted it.** `ai_extractor.coverage_gap()` has scored every extraction for months and `dcp_extract_changed` stamps the verdict onto each queue row as a `suspect_reason`. **The gap was never the check — it was that nothing aggregated it.** So `ashfield/chapter-a-miscellaneous` could record **15 of 15 TOC sections missing** and keep serving an older extraction with no one told. Registered 2026-10-03, reads **7**: ashfield chapter-a-miscellaneous (15/15), chapter-c-sustainability (21/21), chapter-f-dev-category (11/11), chapter-b-public-domain (TOC unreadable), canterbury_bankstown chapter-11-2-undercliffe-bridge-precinct (unreadable), northern_beaches warringah-dcp-2011-full (unreadable), woollahra chapter-d5-double-bay-centre (43/54). ⚠ **Three design choices, each because the obvious version is wrong.** (1) **Latest verdict per chapter** — counting every queue row keeps reporting a fault a later read already cleared, which is exactly `woollahra/chapter-b3-general-development`. (2) **Served, not queued** — a `coverage_fail` in a queue nobody approved harms no reader; tying the count to `regulatory_provisions` is the same correction DQ-97 needed on 2026-09-10, when its population turned out to be one an operator could **drain** without repairing anything. (3) **`coverage_unknown` counts** — "we could not read the contents page" is the third state, not a pass, and omitting it would make this row green on exactly the documents nobody can verify. ⚠ **Not DQ-118**, which is reserved for per-council hub-scrape liveness (whether a council *published* something new) and is named as such by DQ-117. | 🔴 **OPEN — reads 7.** `python scripts/dq_probe_live.py --id DQ-119`. Clears by re-reading each chapter until `coverage_gap()` is satisfied, or by recording why its contents page cannot be parsed. **It does not clear by approving the queue** — the count reads the latest verdict per chapter whatever its status. | P1 — these chapters are live to readers while their own contents page says sections are missing |
| DQ-117: **Nothing proves the DCP source sweep is still running, and every freshness verdict in this ledger depends on it.** ⚠ Registered believing the sweep had *stopped*; it had not — it is FORTNIGHTLY and was mid-cycle. The row is a live liveness watch, not an incident. Registered 2026-09-28. LIVENESS, not data quality — DQ-69's missing sibling for the OTHER monitor. `r2_monitor` writes `url_last_checked` on all four of its paths, so only an actual sweep moves it and a code edit cannot satisfy this row. **Why it matters more than its own number:** `content_hash` has exactly one writer, the sweep, so when the sweep stops BOTH sides of DQ-70's comparison freeze together and DQ-70 cannot go red. Twelve days of no DCP change detection read as healthy on every dashboard, in every check, and in the alert stream — whose silence *was* the outage. ⚠ **The first draft of this row measured `max(url_last_checked)` fleet-wide and would have read 0 the day it was installed.** Six Wollongong chapters were first checked on 2026-09-24 as part of onboarding, which moved the fleet maximum to four days ago while 499 of 514 chapters sat at 2026-09-15. A fleet-wide `max()` goes green as soon as ANY council is touched, which is the exact silent-pass shape this row exists to remove. It measures the **median** instead: a sweep moves all 514 rows, and no onboarding of a handful can. NULLs sort as `-infinity` rather than being dropped, and an empty registry reads **1**, because a check that reads clean when its population vanishes is not a check. ⚠ **Not the discovery check** — this asks whether the sweep ran, not whether a council published something new; hashing known URLs structurally cannot see a new document. That is DQ-118's question. | ✅ **FIXED 2026-09-28 — and the fix was to the CHECK, not the pipeline.** `python scripts/dq_probe_live.py --id DQ-117` reads **0**. ⚠⚠ **This row was opened on a wrong premise and that correction is the row.** It shipped with a **10-day** window because the opening prompt stated the cron was *“weekly Mon 02:00 UTC”*. `railway.dcp-monitor.toml` in this repo says `cronSchedule = "0 2 1,15 * *"` — **fortnightly, the 1st and 15th at 02:00 UTC**. So the sweep's last run on 2026-09-15 was **12 days into a 14-day cycle, not a 12-day outage**, the next run is due 2026-10-01, and a 10-day window would have read RED on a perfectly healthy schedule every cycle for ever — which destroys the one thing a ledger row is for. Window corrected to **17 days**, the longest healthy gap (15 Jan → 1 Feb). **What survives unchanged: the median rather than `max()`**, which was a real defect in the drafted query and is independent of the window — six wollongong chapters first checked on 2026-09-24 moved a fleet `max()` to four days ago while 499 chapters sat 13 days old, so `max()` reads green mid-outage at any window. ⚠ The toml is the DECLARED schedule, not the live one: `scripts/check_railway_cron_drift.py` exists because on 2026-09-10 six of eight services ran a schedule different from their file and four had no cron at all. If it reports `dcp-monitor` drifting, this window is wrong again | P1 — while this reads 1, every "unchanged since extraction" verdict in this ledger describes the last sweep date, not today |
| DQ-105: **8 of 14 serving councils have NO applicability config, and DQ-33's global floor is too coarse to notice.** Opened 2026-09-23 while answering "does this session's work cover future LGAs?". **Mostly yes, and this is the exception.** Everything judging TEXT is universal — `classify_row_fidelity` takes no council argument, so reversed text (DQ-104), garbled glyphs, junk refs and emptied provisions are caught for any council from its first extraction, and the fidelity gate grades every row against its own source page. The applicability config is **the one onboarding step nothing can derive**: a hand-written file recording which zones and development types each chapter binds, read from that chapter's own Application section. ⚠ **Why DQ-33 misses it:** DQ-33 is one global count against a floor of 1,158; measured the same day it read **924**, i.e. **234 rows of headroom** — a newly onboarded council could publish 234 rules applying to every development type and nothing would go red. A total hides a per-council regression, and what it hides here is exactly the non-automatic step. **Counts COUNCILS, not rows**, because how many of a council's rows fall through depends on whether the text regex happened to match, which moves on every re-extraction. | 🔴 Open — REOPENED 2026-10-04: the probe reads **1** — cumberland now serves **3** rows whose development type is `no_config` → ALL (ids 104720, 104729, 104732, all `cumberland-dcp-part-b-residential`), so the WATCHED exception below no longer holds. Red on origin/main 00e2bb75 as well, i.e. a data change, most likely the 09:22 retag (#1206); not traced further. The fix is DQ-107's, not a config. Previously: 🟢 Fixed 2026-09-24 — `python scripts/dq_probe_unchecked_rows.py --id DQ-105` = **0** (was 7 on 2026-09-23). Configs written for campbelltown, blacktown, penrith, hornsby, georges_river, northern_beaches and **parramatta** (the largest: 616 served, 344 falling through, now 55). ⚠ **cumberland is WATCHED, not configured, and that is deliberate**: its DCP Part B is FIVE separate sub-parts sharing ONE document_id — each carries its own "1.1 Land to which this Part applies" naming a different scope ("all residential development types except for single dwelling house development", low rise dual occupancy, residential flat building, boarding house, and dwelling house + secondary dwelling) — and their section codes COLLIDE, every sub-part having a 1.1 and a 2.4. Neither key the tagger uses, document_id nor section code, can separate them, so one entry would mis-scope four of the five. Its 29 rows are scoped correctly from their own prose and **0 fall through**. The real defect is the document registration, not the absent config. The exception is COMPUTED from `fallthrough == 0`, never a named allowlist, so cumberland is counted again the moment one row falls through — pinned by `tests/test_dq105_watched_councils.py`, which also asserts no council name appears in the probe's executable logic. Forced to fail: unregistering the parramatta config makes the count rise to 1 (341 rows) . ⚠ **The probe got its own question wrong twice**, both times by asking something adjacent to what the TAGGER asks: it first compared `source_council` to the config registry (the tagger keys on `document_id`, so Inner West — the most deeply configured council in the product — was reported as having none, on 11 rows that are Marrickville and Ashfield plans carrying the parent slug); then it resolved with an EMPTY provision text (Waverley and Woollahra key on a section code read out of the text, so Waverley was reported as unconfigured while serving 392 rows with zero fallthrough). Now resolved per ROW with that row's own text; both corrections pinned as tests | P2 — a control that governs one development type is shown for every type; noise rather than a hidden control, but it is the unaudited state DQ-33 exists to remove |
| DQ-110: **A provision keyed to a zone that exists in NSW but NOT in that council.** Registered 2026-09-24. **This check already existed and already failed** — `scripts/validate_zone_code_validity.py` has run in the post-commit completeness report for months, but nothing in the ledger asked it, so its verdict reached no gate. Same shape as DQ-106, found the same way. ⚠ **Not a duplicate of DQ-30**, which asks a narrower question: DQ-30 names the codes NSW RETIRED in 2022 (B1–B8) and passes anything outside that list; this asks whether a code exists in THIS council's land-use table. They disagree on exactly one row and both are right. | 🟢 Fixed 2026-10-04 — `python scripts/validate_zone_code_validity.py` reads PASSED (INVALID 0, UNVERIFIABLE 240) on production, cleared by #1206. UNVERIFIABLE rows have no ground truth and are not a pass. Previously: exited non-zero: **1 row**, id **122333**, canterbury_bankstown, zone **R5** — a current NSW zone that Canterbury-Bankstown's LEP does not contain, so the row can never match a lookup for the property it claims to govern. Surfaced when `sync_v2_to_supabase.py`'s new pre-write gate refused on it the same day. Ground truth for the check was extended to 28 councils on 2026-09-24 (Wollongong 27 zones, Newcastle 19) after the scraper was repaired | P2 — one row, silently unreachable rather than visibly wrong |
| DQ-113: **A served rule's page link opens a page that does not hold the rule.** Registered 2026-09-26. The AI reader stored the first page of its 12-page chunk for every rule it returned (`scripts/ai_extractor.py`, `a + 1`). Full probe over all 237 served chapter PDFs: 45% of 17,489 served rules linked to the wrong page, 21 of a 108-row sample while their clause number was `proven` -- the citation proof uses the stored page only as a search hint. Councils also print their own page numbers as text ("B5", "14-117"), which the integer `pdf_printed_page` cannot hold. | ✅ Fixed 2026-09-27 — `python scripts/dcp_page_repair.py --check` exit 0: 10,515 links moved, 5,939 already right; 1,035 show "page not located" (715 printed in several places, 217 too short, 103 whose stored text is not in the PDF). Reader places each rule on its own page; the repair runs after every publish. | P1 — a citation that opens the wrong page |
| DQ-114: **4,374 served scope keys read ALL because nobody decided them, and no check counted it.** Registered 2026-09-27. This is the row DQ-33's own note asked for — it ends *"SEPARATE AND LARGER: ... that gap is not counted here and needs its own row"*. **The list of non-decisions is the schema's own, not this row's opinion:** migration 062 documents on the column that `config_specific`, `config_all` and `text_regex` are trustworthy assertions while `config_silent`, `no_config`, `no_document_id` and `filtered_to_all` are undetermined, and NULL means *"tagged before provenance existed (origin unknown, NOT a pass)"*. `no_config` is DQ-33's and DQ-105's; the rest are this row's. ⚠ **`filtered_to_all` was missed on the first write and added before this row was ever committed** — 43 served zone keys nothing else counts, which would have let the check go green with them undetermined. `config_silent` is the dangerous one, because it reads as finished: the council is "configured", its words are in the config file as a comment, and the key nobody decided resolves to ALL — so the rule is served to every development type on the authority of an omission. Counted **per key, not per row**: the suppression in `tag_with_provenance` is per-ENTRY, so an entry naming dev types while omitting zones is silent on zones alone, and counting rows would let a whole column go undecided without the number moving. ⚠ **Not DQ-103**, which is the subset whose own text carries discarded evidence — code can fix that; what remains here needs a person to read the chapter. | 🔴 Open — `python scripts/dq_probe_live.py --id DQ-114` reads **4,374** key-decisions on 2026-09-27: dev types 2,859 `config_silent` + 36 untagged; zones 1,400 `config_silent` + 43 `filtered_to_all` + 36 untagged; DQ-103 accounts for 1,021 of them. Concentrated in waverley (257), wollongong chapter_b1_residential (584 rows, 100% silent), campbelltown part 3 (152), city_of_sydney (every section — its config declares **0** scope keys across 7 entries). **It can reach zero**: a chapter that states no scope of its own inherits the plan's stated scope, which is itself a quotable decision (Wollongong A1 s5, *"This plan applies to all lands within the Wollongong LGA"*). Silent is never the honest answer — only "not read yet" | P1 — 25% of served rules are shown to projects their own chapter may not reach |
| DQ-115: **Every applicability decision we have is justified by a Python comment, which no machine can read.** Registered 2026-09-27. The configs are written properly — each entry quotes the chapter's own scope sentence beside it — but as a COMMENT. So the authority for 69% of served rules (12,011 rows on `config_all`) cannot be read by the checks, by the review page, or by the property page that has to tell someone why a rule is on their list. **This row exists to stop DQ-114 being gamed:** DQ-114 alone is clearable by typing `["ALL"]` across 193 keys, which would take both counts down while making every served answer worse — the exact shape of "the config file was written, so it was called done". The fix is a `scope_evidence` dict keyed by the field it justifies, so a declared key without its sentence is countable rather than merely absent. Counts DECLARED keys only; an omitted key is DQ-114's population. | 🟢 Fixed 2026-10-04 (#1209) — `python scripts/dq_probe_applicability_config.py --id DQ-115` = **0** (was 193 on 2026-09-27, 47 on 2026-10-04 morning). Every declaration carries the council's sentence; DQ-121 reads 0 MISSING for woollahra, canterbury-bankstown and parramatta. Previously read **193 of 193** declared keys with no evidence, across 13 distinct configs (aliases de-duplicated by identity, not by name, or one missing sentence would count twice). Needs no database. Largest: canterbury-bankstown 85, woollahra 50, warringah 14, parramatta 12. The probe also reads a `sections` bucket **no config uses yet** — Wollongong B1 states no scope of its own while its sections 4/5/6 each cover a different development type, so the decision for 584 served rows belongs one level down from the chapter | P1 — makes the other half enforceable, and feeds the "why is this rule here" line on the property page |
| DQ-116: **A section the council has repealed is served as a live control, with a page number and a quote.** Registered 2026-09-27. The DOCUMENT-level guard already exists and works — `dcp_extract_changed.detect_repealed_stamp` hard-rejects a PDF whose front matter carries an archive stamp, which is what shipped 20 of 23 Woollahra chapters as repealed content before the 2026-07-29 re-source. It cannot see this shape, because **there is nothing wrong with the document**: the chapter is in force and a section inside it has since been repealed and marked in place. ⚠ **Counted by POSITION, not vocabulary.** Of 68 served rows carrying repeal wording, **67 are correct to serve**: `(a) (Repealed) (b) not have an area more than 25 m2` is how NSW legislation is drafted — the repealed paragraph stays, marked, so the surviving paragraphs keep their lettering, and deleting it would renumber the council's own clause. The mark means "repealed" in both shapes; where it sits says whose repeal it is. The same lesson defeated the document-level rule's first version, which flagged a heritage chapter's sentence about a **lighthouse** ("This was later replaced by a number of lighthouses"). Reuses that module's detector rather than restating the pattern — two copies of a rule is how two thresholds start disagreeing. | ✅ **FIXED 2026-09-27** (contained) — `python scripts/dq_probe_unchecked_rows.py --id DQ-116` now reads **0**. It read **2** when opened the same day. (1) **woollahra B3.3 Floorplate** — ⚠⚠ **A "correction" claiming the harm ran the other way was posted and then WITHDRAWN the same day — it had read a stale PDF tracked in this repo (`woollahra/chapter-b3-general-development.pdf`, 3,477,944 bytes, 105 pages) instead of the R2 object `r2_current_path` names (`v1.4-2026-09-15`, 2,973,719 bytes, 101 pages). Verified against the real source: page 21 reads *"B3.3 Floorplate (Repealed)"* and *"This section was repealed by Woollahra Development Control Plan 2015 (Amendment 36) on 21 August 2026"*, and the contents page lists it as repealed. The ORIGINAL finding stands — the row is faithful, the section is repealed, and 121802 is correctly superseded. 542 PDFs are tracked in this repo and any can be stale the same way; the authority is the R2 object, never a repo copy.** CORRECTED 2026-09-27 by reading the source PDF; the first diagnosis read `provision_text` and reported the database as if it were the law.** The council's current chapter (`v1.4-2026-09-15`, 105 pages) has B3.3 **alive** on page 21 with a real control — the floorplate applies to development other than dwelling houses, semi-detached dwellings, secondary dwellings and dual occupancies in R2, and the maximum total floorplate is the buildable area **× 1.65**. The word "repeal" appears **zero times in all 105 pages**. Two rows exist: id **121802** carries that live text, last modified 2026-09-15 (the PDF's own version date), `is_current=FALSE`; id **127014** carries "(Repealed)", last modified **2026-09-18**, `version_count=1`, `is_current=TRUE`. A run on 18 September wrote text **that is not in the source document** and superseded a live binding control with it. **We are hiding a live control, not serving a dead one** — no served woollahra row carries the 1.65 factor. ⚠ **The registry makes this invisible:** `provisions_extracted_from_hash` **equals** `content_hash` (`114475891aa8740d`), so the row asserts it came from the current PDF and provably did not — **hash equality is not provenance**. Likely origin is an archived edition (every file in `woollahra/v1.3-2026-09-01/` carries a "Repealed by" stamp), i.e. the failure `detect_repealed_stamp` exists to prevent, three weeks ago; whether its 4-page window missed the stamp or that run bypassed the guard is **NOT established** and needs its own investigation. (2) **nsw_statewide 3.29** (SEPP Industry and Employment 2021, signage), carrying *"This section is repealed at the end of 30 June 2023"* — a sunset clause, and whether it governs the section it sits in or was bundled from a neighbour needs a **person** to read the instrument; the probe reports the quote and never deletes a row **Repaired** by `scripts/repair_dq116_repealed_sections_served.py --apply`: `v2_is_actionable = FALSE` on both rows, backup `data/db_rollback_backups/regulatory_provisions_pre_dq116_repeal_2026-09-27_1328.csv`. Nothing deleted, no text edited — both keep their wording, page and version history and stop being served. ⚠ **CONTAINED, NOT DURABLY FIXED:** `detect_repealed_section` is not wired into the write path, so the next extraction of any chapter can put another one in; DQ-116 reads the live served set, so a new one surfaces at once. Product decision behind it (user, 2026-09-27): a "this control has been removed" notice does not belong in a property report. | P1 — a repealed control served with a citation is the most convincing way to be wrong |
| DQ-112: **A served chapter is missing a page of rules its source prints.** The AI reader skipped pages inside batches that returned something, so the chunk-loss guard (a batch returning nothing) never fired. Found 2026-09-25: the Warringah re-read skipped 21 of 226 pages and the commit's section-loss guard refused it. Live example: Canterbury-Bankstown 11-11 prints 'a minimum of 21% of the site area is to be provided as deep soil'; it is not served. | 🔴 Open — `python scripts/dq_probe_pages_left_out.py`: Canterbury-Bankstown alone 8 chapters / 50 pages. Reader fixed to count and re-read skipped pages (branch fix/skipped-pages); the listed chapters need re-reading. | P1 — rules printed by the council are absent from what we serve |
| DQ-111: **A served provision cites a section code its own source never prints.** Registered 2026-09-24. The fidelity gate proves a row's WORDS and strips its code numbers before checking (`ground_row`, `code_nums`), so an invented clause number serves green. Text genuine, citation invented: it looks checkable and is not. Worst case is the extraction prompt's own example string `C4.9` served as a citation. | 🔴 Open — `python scripts/dq_probe_section_code_not_in_source.py`: **1,302 of 14,083** judged served rows (9.25%), all 231 source PDFs read incl. the 139 MB one. 969 invented numbering · 317 letter prefix added to a printed number · 16 prompt example `C4.9`. ashfield 858, leichhardt 258, northern_beaches 168, 4 others 18. 426 rows not judged by declared reason (bare-integer section, or no clause number). Replaces the plan's 5.6% sample figure. **Superseded the same day:** the "printed anywhere" bar was too low; the probe now runs the gate's proof (`scripts/citation_proof.py`) — nearest printed heading above the rule. Re-measured 4,741 of 14,083 (33.7%) not proven: 2,517 wrong or unprinted section, 2,145 item label not the council's, 78 wording not in source; plus 248 imprecise. **2026-09-25, checker corrected both ways (branch fix/picture-labels):** Leichhardt prints control labels as pictures (read now: +238 proven), and the label check accepted ANY label between heading and rule (474 of 517 shifted labels passed; now 3). Same data, `python scripts/dq_probe_section_code_not_in_source.py`: **4,841 -> 4,686 of 15,137 (30.96%)** not proven; 83 newly refused, sampled as wrong labels the loose check passed. | P1 — >2% affected; which way to serve the failing rows is the user's decision (plan §3) |
| DQ-109: **One PDF, several live registry rows, none saying which pages are theirs — each would extract the WHOLE file.** Opened 2026-09-24 while investigating whether cumberland's split belongs at the pipeline level. **It does: this is not a cumberland oddity.** The extractor takes whatever PDF a registry row points at and extracts all of it — its query selects `r2_current_path` and never `page_start`/`page_end` — so several rows on one file with no ranges produce **one complete copy of the document per row**, live and served. **The chapter names show it was an abandoned attempt at the documented onboarding default:** burwood registers `part-4-residential`, `s4-landscaping` and `s4-table-4-parking` all at `part-4-residential.pdf`; fairfield registers `chapter-5-dwelling-houses`, `landscaping-controls` and `parking-controls` at one file. That is exactly `docs/DCP_SCOPE_CONFIG_REFERENCE.md`'s rule — roughly six topic chapters, not the whole DCP — recorded by someone who expected slicing to exist. | 🔴 Open — `python scripts/dq_probe_unchecked_rows.py --id DQ-109` = **4**, exit 1: bayside (3 rows), burwood (3), fairfield (3), camden (2). **11 rows, 0 extracted** — the only reason no duplicate exists; flipping `needs_extraction` on any one is enough. Northern Beaches is the near-miss: 4 active rows on one PDF, one extracted at 1,772 provisions and three dormant at zero. ⚠ **The obvious fix is wrong:** `page_start`/`page_end` already carry THREE meanings and 135 rows use them for something else — 121 as a page COUNT (start at 1), 14 as "content begins after front matter" (ashfield `chapter-e1-heritage` p3–392 with 348 provisions, `waverley-dcp-2022` p12–473 with 602). Slicing on them blindly changes extraction for **2,717 live provisions**. Slice only when a PDF is SHARED by more than one active row — derivable from data already held, no migration, and it leaves every row that owns its PDF untouched | P1 — a duplicate council is served silently; nothing today would stop it |
| DQ-108: **A structured numeric rule whose own words are not in its own provision.** Opened 2026-09-24 while verifying the formulate stage before running it on 13,909 rows. `v2_extracted_rules` stores a `raw_match` — the exact phrase the number was read from — and that phrase must be IN the provision it came from. **The mechanism is not a bad regex:** the stage is FILL-BLANKS-ONLY, which is what makes it safe to schedule, and the same property means a rule **outlives the text it was derived from**. Re-read a chapter, replace the provision's text, and the rules stay exactly as they were, now describing a page that no longer says it. Nothing recomputes them and nothing compares them. | 🟢 Fixed 2026-09-24 — `python scripts/dq_probe_unchecked_rows.py --id DQ-108` = **0** (was 3). **Fixed at the mechanism, not the row:** the sweep now selects STALE rules as well as blank ones, so a rule whose phrase no longer appears in its provision is re-derived from the CURRENT text — which is what takes it out of the set. Provision 40278's three invented parking rules were replaced by one qualitative rule matching its real text. ⚠ `btrim` is load-bearing: normalising runs of whitespace without trimming the ends made the SQL match **6** rows where the Python probe finds **1** — five healthy rows the sweep could never clear, re-derived on every run forever. The SQL and the Python check are two implementations of one rule and a real-DB test asserts they agree. Originally all 3 were on provision **40278**, whose text is "(e), (f) (Repealed) (g) the minimum internal area, if any, specified in the Apartment Design Guide for the type of residential development," and which carries rules for **4, 5 and 1 parking spaces** at `extraction_confidence: high`. "parking space" does not occur in it once; the row is current and actionable. The **new** extractions are clean by contrast: 3,506 numeric rules, 0 ungrounded. **Two traps the detector had to avoid, both measured:** comparing an unflattened `raw_match` against flattened text accuses **44** healthy rules whose phrase spans a line break; demanding the stored VALUE appear literally fails **18** correct unit conversions (`600mm` stored as `0.6` m — the trap named in `feedback-verify-the-derivation-not-the-digits`). It checks the PHRASE, normalised both sides | P1 — an invented control, served, marked high confidence. Same class as the invented citations DQ-101 exists for |
| DQ-107: **A registered document that is really several plans, so one section code means two different things.** Opened 2026-09-24. **This is the gate an LGA must pass before an applicability config can be written for it at all**, which is why it is general and not a cumberland special case. A config is keyed on a `document_id` or on a section code read out of the provision text; both assume the code identifies ONE thing. Where a document is several plans concatenated, the same code appears under each with a different scope and **no entry is true of all of them** — whatever is declared mis-scopes the rest. Found when DQ-105 reached 0 with cumberland WATCHED rather than configured; without this check that finding would have rested in a code comment, which is not a fix. **Precision measured, not assumed:** same code with any differing heading text = **1,180** pairs (ordinary provision splitting, noise); differing scope SENTENCES = **35**; scopes naming **disjoint development types** = **1**. The 35 are mostly complementary statements about one plan — woollahra pairs "all land within the Woollahra municipality" with "development that requires development consent", both true at once — or the same sentence read twice with HTML table debris from extraction. | 🔴 Open — `python scripts/dq_probe_unchecked_rows.py --id DQ-107` = **1**, exit 1. cumberland section 1.1 carries 4 scopes naming boarding_house, dual_occupancy, dwelling_house and residential_flat_building. **Reachable:** excluding cumberland's rows takes the count to **0**, so this is not permanently red. ⚠ **BUT THE OBVIOUS FIX WOULD CAUSE AN INCIDENT, verified 2026-09-24:** adding one registry row per sub-part, all pointing at the same PDF, makes EACH of them extract the WHOLE document — `dcp_extract_changed.py`'s registry query selects `r2_current_path` and never `page_start`/`page_end`, so five rows over Cumberland's 54-page Part B would produce **five duplicate sets of every provision**. A real split needs EITHER page-range support in the extractor, OR the PDF physically split in R2, which moves every page number and breaks the page links — the exact thing the northern_beaches and parramatta configs were designed to avoid. Sequence the extractor change first. | P2 — no control is currently wrong (all 29 cumberland rows are scoped correctly from their own prose and 0 fall through); the cost is that the council cannot be configured, and the next LGA registered the same way would hit the same wall silently |
| DQ-106: **Every gate on retired zone codes ran AFTER the write, so the only thing that caught one was a person reading a dry run.** Opened 2026-09-24 in answer to "no automated check would have stopped it — make it automated". `v2_applicable_zones` is a HARD filter on the served answer (`for-property/route.ts:1012`): a row survives only if the column is NULL, holds `'ALL'`, or overlaps the query, so naming a RETIRED code does not produce a wrong field on a page — it DELETES that provision from every answer for the SUCCESSOR zone, with no error anywhere. **DQ-30 has forbidden this for months and is green**; it checks the TABLE, in the post-commit completeness report, after the rows are live. **Two live writers had never been wired to it.** `retag_applicability_slug_docids.py` was one keystroke from narrowing 34 served Warringah rows onto B1/B2/B5/B6/B7 — Warringah DCP 2011 predates the 2022 employment-zone reform and still names those codes, so the tagger read them straight out of the plan text. Grepping for other writers the next day found `sync_v2_to_supabase.py` UPDATEing the column across ~48.8k rows behind nothing but `input("Continue? (yes/no): ")` — and that script's `get_local_connection()` resolves to **production on both ends**, because `.env` overrides its `localhost` defaults; on a machine where `PG*` is unset the same command instead reads a stale local mirror holding **200 rows with retired B/IN codes**. Same file, same command, two different payloads depending on a dotfile. **Fixing callers one at a time leaves the hole open for the next caller**, so the check asserts the property over the whole tree: the set of files that ASSIGN the column is a subset of the set that consults an LGA land-use table. | 🟢 Fixed 2026-09-24 — `python -m pytest tests/test_every_zone_writer_consults_ground_truth.py -q` = 8 passed, 3 writers detected (`enrichment/pipeline.py`, the retag, the sync), 0 offenders. **Both halves forced to fail rather than assumed:** removing `valid_zones=` from the retag makes its own `retired_zone_codes` gate report **68 rows** and `--apply` exit 2 with no backup table created; adding a throwaway blind writer under `scripts/` turns this check red, and removing it green again. The detector was itself wrong twice first — it read the two `scripts/fixes/DQ7_*.py` as writers when they only name the column in a `WHERE` clause and write `v2_applicable_dev_types`, and it missed the retag entirely because that builds `UPDATE {TABLE}` from a module constant. Narrowed to ASSIGNMENT of the column; both mistakes pinned as confusable negatives | P1 — silent deletion from the served set, and the class of accident that put 578 bad rows live on 2026-09-09 |
| DQ-104: **Served provisions whose text was read BACKWARDS — and a human was being asked to adjudicate a number inside one.** Found 2026-09-23 from a screenshot of the live review queue: the row under review read `kcabtes m0.2` (setback, mirrored) beside `nimm0.4 xamm0.41` and `OOMBATHROOM`, and the UI asked whether 0.41 was correct. **There is no judgement to make about mirrored text**, and the question should never have reached a person. A PDF laid out right-to-left in places — usually inside a figure or a table — returns whole words reversed. **Nothing detected it**: `_AUTO_REJECT_REASONS` held `garbled_glyphs`, `junk_ref` and `emptied_by_strip`, so the row became `pending` instead of being rejected for a re-read, against §5.2's own rule that a row which cannot be PROVEN is rejected and the chapter retries. Now detected at enqueue **and** counted live, because the enqueue gate cannot reach what is already served. ⚠ **The detector is evidence-based, not a substring probe** — the obvious version matched 40 served rows of which **35 were false positives** (`nimm`, `xamm` inside ordinary words); shipping that as an auto-REJECT would have discarded real controls. A token counts only when its own reversal is a word this domain uses and the token itself is not, and only when **two distinct** such tokens appear in one provision. Vocabulary imported from `dcp_extract_changed` so gate and probe cannot drift. **Distinct from DQ-78** (runs of single letters): neither sees the other — DQ-78 read 34 the same day. | 🔴 Open — measured 2026-09-23, `python scripts/dq_probe_unchecked_rows.py --id DQ-104` = **27** (city_of_sydney, canterbury_bankstown, ku_ring_gai) | P2 — the served text is not the council's text, but the affected rows are predominantly figure labels rather than numeric controls |
| DQ-102: **A DCP chapter can be registered, extracted and served with no applicability config entry, and nothing counts it.** Found 2026-09-23 while writing the Canterbury-Bankstown and Campbelltown entries. `ApplicabilityTagger._get_config_driven` returns None when a council's config has no key matching the document_id, and `tag_with_provenance` then falls through to the text regex. A regex hit is recorded as `text_regex`, which `TRUSTED_ALL_SOURCES` treats as a DECISION — so the chapter that nobody onboarded reads as decided. **DQ-33 cannot see this**: it counts `v2_dev_type_source = 'no_config'`, and a row only reaches `no_config` when the config missed it AND its own text yielded nothing either, so the gap is visible exactly in the chapters whose provisions happen to be free of zone and development-type words. Measured **138 served rows across 25 documents**: woollahra (chapter d5 double bay centre, f2 educational establishments, f4 telecommunications), ku_ring_gai (the `section_b part_14x` local-centre and site-specific parts), canterbury_bankstown (10.6 commercial land uses, 10.8 telecommunications, 11.2 undercliffe bridge, 11.6 potts hill, 3.3 waste management, 1.1 introduction) and city_of_sydney. **Deliberately not fixed in the same change**: each entry has to be written from its own chapter's Application section, and guessing one to clear a count is the behaviour DQ-33 exists to refuse. | 🔴 Open — measured 2026-09-23, `python scripts/dq_probe_applicability_config.py --id DQ-102` = **138** | P2 — the scope served is evidence-based rather than absent, and the direction is not systematically harmful; the defect is that an un-onboarded chapter is indistinguishable from an onboarded one |
| DQ-103: **`config_silent` throws away the row's own text evidence, because one decided key silences the other.** Found 2026-09-23. `tag_with_provenance` guards text extraction with `if text and not config`, so a config entry that matched suppresses the regex for BOTH applicability keys — including one the entry deliberately omitted. `config_silent` is defined in `ApplicabilityTagger._resolve` as "an entry matched but omitted this key … Nobody decided this", so suppressing evidence on its account is a non-decision overruling data the row actually carries, and the row is then served as universal on no authority — the same unauditable `['ALL']` DQ-33 was opened for. **Widened the same day, before it had ever run green**: the first version counted DEV TYPES only, and the suppression is per-ENTRY not per-key, so an entry that names dev types and omits zones discards the row's zone evidence identically and went uncounted — the check could have read zero with the defect fully present on the other column. Caught by the Sol cross-review at the push gate. Counting both keys took it **500 → 744 served rows across 27 documents**, concentrated in waverley (257), campbelltown part 3 (111) and the five city_of_sydney sections. The probe runs the TAGGER over the served corpus rather than reading the stored column, deliberately: the defect is in the tagger, not in any one stored row. The row ends up `ALL`, so **nothing is hidden from anyone** — which is why this is P3 and not P1. Not called "safe": an inapplicable control shown to a property is still a wrong answer, and naming the direction safe is how a row like this gets deprioritised forever. **Not fixed alongside the two new configs**: the guard is shared by all six config-driven councils, so lifting it re-tags waverley, woollahra, city_of_sydney and ku_ring_gai in the same breath and every narrowing that produces needs adjudicating against its own chapter first. | 🔴 Open — measured 2026-09-23, `python scripts/dq_probe_applicability_config.py --id DQ-103` = **744** | P3 — loses precision, never hides a control |
| DQ-90: **CANTERBURY-BANKSTOWN'S ENTIRE DCP TEXT CORPUS IS EMPTY — 0 of 68 active chapters serve a single provision.** Scoped from the 374/371-chapter finding flagged in the previous session: **374** = active chapters registry-wide never successfully extracted (`last_extracted_at IS NULL`); **371** = active chapters currently serving zero provisions — a close but distinct base (3 chapters were never extracted yet carry a current provision via the chapter_key alias-map recovery, PR ad1249a3). **97 is derived from the 371 base, not 374**: 271 of 371 turned out benign on inspection — **247 are `is_spatial=TRUE`** (genuine map sheets, e.g. `sheet-015-...-height-in-storeys-map`, never meant to carry text) and **24 are `is_inert=TRUE`** (covers, tables of contents, guidance manuals) — 271 of 371 legitimately need no extraction, and 3 more are already correctly flagged `needs_extraction`. **That leaves 97 real, silent gaps** (371−247−24−3=97; the same subtraction from 374 gives 100, a different number — quoting 97 as "of the 374" would be wrong) — registered, substantive, ordinary DCP chapters (parking, landscaping, residential, traffic) with zero served content and nobody tracking them as a to-do. **54 of the 97 are one council: Canterbury-Bankstown.** Checked precisely: CB has 68 active chapters total, 14 legitimately spatial/inert, and of the remaining 54, **every single one serves zero provisions** — chapter-2-2-flood-risk-management, chapter-3-2-parking, chapter-3-3-waste-management, chapter-2-3-tree-management, chapter-1-1-introduction-and-administration among them, all correctly identified as `dcp_name='Canterbury-Bankstown DCP 2023'` (the current, in-force plan — not a stale superseded registration), most with `r2_current_path` already populated (the PDF was successfully fetched), registered 2026-05-11 — nearly four months with the source in hand and never extracted. ⚠ **Narrower than "CB has zero DCP data"**: `dcp_setback_controls` (the separate numeric-controls surface, per `frontend-nextjs/COMPONENT_MAP.md`'s own "do not conflate the two" warning) has **67 current CB rows** — the numeric setback/parking tab works. It is specifically the DCP tab's TEXT/TOC provisions view (`regulatory_provisions`) that is empty for this council. The remaining **43 of the 97** are thin, scattered 1-3-chapter gaps across **20** other councils/instruments (northern_beaches 3, fairfield 3, liverpool 3, wingecarribee 3, burwood 3, sutherland_shire 3, strathfield 3, bayside 3, canada_bay 3, camden 2, randwick 2, waverley 2, ryde 2, state 2 [Apartment Design Guide chapters, not a data error], inner_west 1, the_hills 1, the_hills_shire 1, parramatta 1, leichhardt 1, cumberland 1) — consistent with the normal handful of stragglers any multi-council pipeline carries, not investigated further here. **UPDATE 2026-09-05: investigated, and acted on — the "why" is answered.** The extraction script (`scripts/dcp_extract_changed.py`) only ever touches a chapter with `needs_extraction = TRUE` — checked the source directly (line 1694), no bypass flag exists. Canterbury-Bankstown's 54 chapters were registered with that flag left `FALSE`, so the pipeline's own scheduled sweep has silently skipped them for four months by design, not by accident. **Fixed that part**: with explicit user authorization, backed up the 54 rows' full state first, then flipped `needs_extraction = TRUE` on exactly those 54 (verified count both before and after the write, 54/54). **UPDATE 2026-09-05, later same day: 39 of the 54 committed for real.** After the review-and-fidelity-check work recorded in DQ-95, ran `scripts/dcp_extract_changed.py --council canterbury_bankstown --chapter <key>` per-chapter for the 39 chapters cleared of both chapter-level extraction bugs and provision-level fidelity flags. All 39 returned `[OK] Inserted N provisions (full replace)`, zero ABORT/SKIP/ERROR. Verified live, not just from the run log: `regulatory_provisions` now carries **189** current rows for `source_council='canterbury_bankstown'` across exactly **39** distinct `source_chapter_key` values — matching the commit list precisely. Spot-checked several committed chapters' provision text directly (e.g. chapter-8-3-hume-highway): coherent, correctly formatted DCP clauses, not garbage. The remaining 15 (2 chapters with no PDF ever fetched + 13 held back — the original 11 scanner-flagged, only 1 of which is manually confirmed, plus 2 more manually confirmed during DQ-95's provision-level fidelity review) correctly remain `needs_extraction=TRUE`, tracked in DQ-95. See DQ-95 for the full before/after and the exact exclusion list. | 🔴 Open — measured 2026-09-05, `dcp_chapter_registry` WHERE `is_active AND NOT is_spatial AND NOT is_inert AND NOT needs_extraction` AND no currently-served provision exists = **45** (verified live 2026-09-05, corrected from a previously-reported 43 — the 39 newly-committed chapters were never in this count, once `needs_extraction` was TRUE for them, and the 13 held-back chapters stay `needs_extraction=TRUE` so are excluded by design; the +2 vs the earlier 43 is `cb-dcp-2023-ch5-1-bankstown`/`ch5-2-canterbury`, correctly reverted back to `needs_extraction=FALSE` — they now legitimately match this query's definition, even though DQ-95's own note explains why they are not part of the real gap: their setback standards are already served from `dcp_setback_controls`, not this table) | P2 — downgraded from P1: 39 of 54 chapters are now live and serving real content; the remaining 13 (not counted here, since they're still queued) are a bounded, named, tracked residual, not an invisible corpus |
| DQ-91: **A live API endpoint silently drops its audit record — the write fails, the response still says success.** Found in `ce-verified-capability-statement-2026-08.md` §4 item 11 via the schema-contract gate's baseline (`scripts/schema_contract_baseline.json`), which accepts 4 table references as known-invalid so the gate can be enforced today — "accepted" there means "not blocking CI", not "fixed", and none of the 4 had a DQ row or a live check before this. The one that matters: `drawdown_verify_audits` (construction-loan drawdown verification — satellite radar evidence that a claimed build stage really happened, logged for a lender's records) has never existed as a table, `migrations/033_drawdown_verify_audits.sql` was written to create it and never run against production, and `services/drawdown_verify.py` — a live router registered in `services/compliance_api_server.py`, the actual uvicorn entrypoint — wraps the insert in a bare `except Exception` that logs the DB error and returns `status="submitted"` to the caller anyway. So a caller can be told a verification was recorded when it was not, with nothing telling anyone. No frontend caller was found in this repo for the endpoint (grepped 2026-09-04), so today's blast radius is probably low — but "no caller found" is not the same as measured traffic. The other 3 tables (`basix_provisions`, `sepp_provisions`, `special_provisions_registry`) are in the deployed Python import graph per the baseline's own reachability trace; not individually re-verified for silent-swallow behaviour here. **CAVEAT (Sol cross-review, 2026-09-04): this check proves table existence only, not that the insert actually succeeds once the table exists — a schema mismatch or a permissions grant could still let the same bare `except` swallow the failure with this probe reading clean.** **UPDATE 2026-09-04: the CODE-LEVEL lie is fixed** (see `fix/dq-91-drawdown-audit-failclosed` — `submit_drawdown_verify` now raises HTTP 500 instead of swallowing the failure and returning a fake `submitted`; regression-tested by forcing the old code to fail the new tests via `git stash` before restoring the fix). **The ROOT gap stays open**: the table still does not exist in production. Running `migrations/033_drawdown_verify_audits.sql` was attempted this session and BLOCKED by the auto-mode classifier as a production DDL write requiring explicit approval. **UPDATE 2 2026-09-04 (explicit user authorization): migration 033 run against production.** Verified live: 19 columns / 3 indexes matching the migration exactly. Full end-to-end proof: a real row was inserted via `_insert_audit()`, read back via `_get_audit()` with matching fields, deleted, table confirmed at 0 rows after. `tests/test_drawdown_verify_real_db.py` rewritten to match (4 tests, all passing against real production). **Still declared open** — the probe covers 4 tables and now reads **3, not 0** (the other 3 are unrelated dead-ish code paths, not fully re-verified this session). **UPDATE 2026-09-05: the other 3 WERE individually re-verified, and it was worse than "unrelated dead-ish code".** the (now-deleted) `enhanced_compliance_api` module's BASIX branch caught the guaranteed query failure on `basix_provisions` and **fabricated a plausible-looking result** — hardcoded "BASIX requirements apply for Climate Zone X" text with a hardcoded 90% confidence badge — rendered live on an unauthenticated public page, `/authoritative`. The special-provisions branch (`sepp_provisions`, `special_provisions_registry`) silently dropped hazard/heritage/SEPP checks with no error at all, indistinguishable on-screen from "checked, none apply". A **third** instance of the exact same pattern surfaced while tracing reachability: `frontend-nextjs/app/api/assessment/version-compliance/route.ts` spawns the same CLI with flags its own `argparse` never defines — a guaranteed failure — and its fallback path fabricates a fake "compliant" verdict citing a made-up "LEP Clause 2.3" on every call. That route had zero real callers (grepped repo-wide) but was still live and publicly reachable. **Fixed by deletion, not migration**, per explicit user instruction ("if there is no existing tables then scrap that url... we dont want it"): no real BASIX/SEPP source data exists to populate these tables honestly, so the code that fabricated or hid the gap was removed outright rather than patched to fail more carefully. Deleted from `services/`: the `enhanced_compliance_api`, `basix_compliance_checker`, `special_provisions_processor`, `special_provisions_integration` and `sepp_quantitative_extractor` modules. Deleted from `frontend-nextjs/`: `app/authoritative/`, `app/api/authoritative/`, `app/ui-test/`, `app/api/assessment/version-compliance/`, and the `AuthoritativeComplianceDisplay`, `EnhancedComplianceCheck`, `ComplianceChecklist` (under `components/compliance/`), `compliance-checklist` and `assessment-panel` components. The `/compliance` route removed from `services/compliance_api_server.py` (file kept — shared by other live routers). `schema_contract_baseline.json` shrunk **9 → 6** (verified via `python scripts/validate_schema_contract.py` — PASSED, no new invalid references). Full suite re-run clean: 4967 passed, 2 skipped, 0 failed. | 🔴 Open — measured 2026-09-05, `python scripts/dq_probe_live.py --id DQ-91` = **3** (drawdown_verify_audits fixed and no longer counted; the other 3 tables still do not exist, but as of this fix, zero deployed code references them — the risk this row tracks, a live service silently lying about one of these tables, is closed for all 4; their continued absence is now an unbuilt-feature fact, not a danger). **Split 2026-09-05 (Sol cross-review): see DQ-94** — DQ-91's count aggregates 4 tables, so a coincidence (drawdown_verify_audits dropped the same moment one of the other 3 gets created) would leave this count unchanged and hide a real regression. DQ-94 checks drawdown_verify_audits alone and is the row that actually guards against that. | P1 — CRITICAL by this repo's own definition: a silent production write failure |
| DQ-94: **drawdown_verify_audits, split out of DQ-91's aggregate count into its own dedicated, zero-tolerance check.** Sol cross-review (2026-09-05, on the branch that closed DQ-91's other 3 tables by deletion): DQ-91's probe sums 4 table-existence checks into one number. That number staying at "3" cannot distinguish "the 3 expected-absent tables, unchanged" from "2 expected-absent tables plus a fresh, real regression on drawdown_verify_audits" — a coincidence at the wrong moment (someone creates one of the 3 unbuilt tables the same day drawdown_verify_audits is accidentally dropped) would leave DQ-91's count reading exactly the same and nobody would look. This row checks drawdown_verify_audits BY NAME, alone — it can never be masked by what happens to the other 3. | ✅ Fixed — measured 2026-09-05, `python scripts/dq_probe_live.py --id DQ-94` = **0** (table exists; migration 033 ran against production 2026-09-04, insert/read/delete round-trip proven through the real functions, code fails closed) | P1 — this is now the row that actually guards the audit write path; DQ-91 stays as the informational aggregate |
| DQ-95: **Canterbury-Bankstown DCP extraction attempted for real, 2026-09-05 — 11 of 52 processed chapters flagged by the artifact scanner, not 52.** Acting on DQ-90: flipped `needs_extraction=TRUE` on the 54 registered-but-never-queued chapters (explicit user authorization, 54 rows backed up first, count verified 54/54), then ran `scripts/dcp_extract_changed.py --council canterbury_bankstown --review` repeatedly — memory-only, zero database writes. **First read was wrong**: the CLI's "52 chapter(s) flagged SUSPECT" banner is a crude PRE-extraction page-geometry heuristic that never looks at the actual output, and it was mistaken here for a measure of extraction quality. The review file's own separate, POST-extraction "CHAPTERS WITH EXTRACTION BUGS" summary is a better signal, and it lists **11** of the 52 processed chapters (2 of 54 have no PDF at all yet); **29 of 52 have zero artifacts detected**, the remaining 12 carry minor, under-threshold artifacts. **Sol cross-review (2026-09-05, HIGH, real) caught a second over-claim in the same finding**: only **1** of the 11 (`chapter-7-5-canterbury-local-centre`) was actually opened and manually confirmed — real corruption, a page number bled into a heading, `bare_page_numbers` at 261% of the provision count. The other 10 are flagged BY THE SCANNER, not independently checked — the scanner's own false-positive rate on this council has not been established, the same way the preflight banner's was. Do not read "11" as "11 confirmed"; it is "11 flagged, 1 verified." **Also tested and reverted**: this repo already has a working geometric two-column reader (commit `53b0c8ee`, proven on ashfield/marrickville/city_of_sydney/hornsby). Adding `canterbury_bankstown` to it and re-running the full 52-chapter batch produced the **identical** 11-chapter flagged list and 2 *fewer* clean chapters (27 vs 29) — the existing fix does not transfer here and may make it marginally worse. (A single-chapter spot check had first suggested it helped; that chapter turned out to already be clean in the untouched baseline too — the error was not checking the baseline before crediting the edit.) Nothing was committed to production at that point either way. **UPDATE 2026-09-05, later same day: 39 chapters committed for real, 15 held back.** Per the user's direction, sampled 33 of the 91 individual provisions the pipeline's own deterministic fidelity gate (`scripts/dcp_fidelity_gate.py`, no LLM — grades each queued provision against its source PDF page) had flagged for human review on the `--review` run: covered the worst chapter (7-5, all 17 of its flags) and a spread of 7 chapters with only 1-2 flags each. Confirmed a real, evidence-backed split: chapter-7-5's flags are genuine structural defects (a table-of-contents block and an Acknowledgment-of-Country boilerplate page captured as if they were numbered clauses); everywhere else sampled, the flag is the checker's own page-matching limitation — the provision text reads correctly, it just cites a clause/figure number that lives on a different page than the one the checker locked onto. Found 2 new, narrow exceptions outside the original 11-chapter list: `chapter-7-2-city-west` row `1_6` (a setback-figure table extracted as a jumble of numbers) and `chapter-9-1-general-requirements` row `M5` (a road-network map legend captured as a provision). **Mechanical finding that shaped the exclusion**: the actual commit code path (`extract_chapter()` with `review=False`) is entirely separate from the `--review`/fidelity-gate path — it never reads `dcp_review_queue.fidelity_status` and has no way to exclude a single provision, only a whole chapter (its own gates are count_drop/regeneration_artifact/map_change/restructure, none of which catch this class of defect). So the two newly-found bad rows meant holding back their WHOLE chapters, not just those rows — a more conservative outcome than originally scoped, not a looser one. Final exclusion list (15 of 54): the original 11 (`chapter-7-5-canterbury-local-centre`, `chapter-3-4-sustainable-development`, `chapter-2-2-flood-risk-management`, `chapter-6-2-bankstown-city-centre`, `chapter-4-3-heritage-conservation-areas`, `chapter-11-14-riverwood-estate`, `chapter-7-6-belmore-and-lakemba`, `chapter-11-12-445-canterbury-road`, `chapter-11-9-revesby-hospital`, `chapter-11-13-former-wsu-campus-milperra`, `chapter-1-1-introduction-and-administration`) + `chapter-7-2-city-west` + `chapter-9-1-general-requirements` + the 2 chapters with no PDF ever fetched (`cb-dcp-2023-ch5-1-bankstown`, `cb-dcp-2023-ch5-2-canterbury`). Committed the other 39 one chapter at a time via `--chapter`, verified live: **189** provisions now current across exactly those 39 `source_chapter_key` values, zero ABORT/SKIP/ERROR in the run log, spot-checked provision text reads as coherent DCP clauses. **CORRECTION 2026-09-05, later same day**: the 2 `cb-dcp-2023-ch5-*` chapters were wrongly included in that 15-chapter exclusion list — checked their registry rows directly: different naming convention, registered a different day (2026-04-21 vs the other 52's 2026-05-11), `r2_current_path` was never set, and their own `notes` column says their setback standards were already manually extracted into `dcp_setback_controls` months ago. They were `needs_extraction=FALSE` before this session touched anything and are now reverted back to that correct state (verified before/after: both TRUE→FALSE, exactly 2 rows). The real exclusion list is **13**, not 15: the original 11 + 2 found during the fidelity review. **REAL EXTRACTOR FIX STARTED 2026-09-05**: root-caused chapter-7-5's `1.1`/`2.1`/`5.1` contamination by running the real extractor against the real 122-page PDF (not assumed) and printing every section it produced. Found the existing TOC-page guard (`_toc_hits >= 5`, catches the chapter's FULL table of contents) doesn't fire on a section's own "SECTION N" mini-TOC divider page (3-4 entries, e.g. page 5's "SECTION 1 INTRODUCTION 1.1...1.2...1.3..."), so that divider text was captured as the opening paragraph of the next section instead of being suppressed. Fixed by extending the guard with a second, narrower signal (`is_toc_or_divider_page()`, `scripts/dcp_extract_changed.py`): a literal "SECTION N" line near the top of the page plus 2+ section-code matches. Verified live: `2.1` and `5.1` now start with clean real content (mini-TOC gone); `1.1`'s mini-TOC is also gone, but the page underneath is a garbled map (a SEPARATE, harder, explicitly out-of-scope defect — scrambled single-character map/legend text that section_re occasionally mismatches onto, seen in sections `1`, `2.30`, `22.50`, `13`, `P3`, `P8`, `P9` — named as follow-up, not silently dropped). Full-batch regression check: re-ran `--all --review` across all 39 already-COMMITTED chapters — 0 new artifact-scan bugs, and exactly 1 real, correct change: `chapter-11-15-marco-avenue`'s already-LIVE `2.1` provision (currently serving "2.1 Objectives 8 / SECTION 2 / BUILT FORM AND / DESIGN / 2.1 Objectives 8" — 100% divider junk, no real content) would be correctly REMOVED by a re-commit, not replaced with something else — confirmed by diff, not assumed. Two further corrections followed on cross-review before merge: Sol (HIGH, confidence 0.98) caught the first version of this fix suppressing heading detection but still silently absorbing divider text into whichever section was already open, corrupting two previously-clean sections (1.2, 4.6) — fixed by discarding divider-page text outright instead; Sol also caught the ledger overstating that all 13 held-back chapters share one defect class, when only 3 have any verified defect at all (chapter-7-5, chapter-7-2, chapter-9-1) and the rest are unverified scanner flags — corrected. **RECOMMITTED 2026-09-05**: re-ran `--chapter chapter-11-15-marco-avenue --all` using the merged, corrected fix. Verified live: the junk `2.1` provision is gone (1 removed) and `1.1`'s divider prefix is gone too (1 updated) — `1.1` still carries a residual map-label artifact, the same separate garbled-map class as chapter-7-5, not claimed to be solved here. Backed up the 5 pre-recommit rows first. 11 new tests (`tests/test_section_divider_guard.py`), full suite green. | 🟢 Fixed 2026-09-25 -- chapter-6-2 re-read, page-checked and committed; no canterbury_bankstown chapter left queued-and-never-read. Was: (was open) Open — `python scripts/dq_probe_live.py --id DQ-95` = **13** (down from 54; corrected from a previously-reported 15) — the exact, named, immutable exclusion list above, not a vague residual | P3 — the bulk of this council (39 of 54 chapters, 189 provisions) is live and serving real content; of the 13 remaining, only 3 have a verified defect at all — chapter-7-5 (garbled map/key-site pages, the divider contamination is already fixed), chapter-7-2 (a jumbled setback-figure table) and chapter-9-1 (a map legend mis-captured as a provision) — the other 10 are unverified scanner flags that need individual review before any fix, not the same one, is assigned to them |
| DQ-96: **housing_sepp_standards rows a KNOWN legislative amendment should have staled, but never did — plus a second, independent gap in the code that would have served them silently even if it had.** Found investigating DQ-88 2026-09-05. The W3 auto-stale mechanism (#839, shipped 2026-07-29) stamps `stale_since`/`stale_reason` on standards rows the moment it detects an instrument's version change — but only on a fresh `needs_review` FALSE→TRUE transition, with no backfill for an instrument already flagged when the feature shipped. `sepp_housing_2021`'s own detected change is dated 2026-04-24, before #839 existed — checked live: 33 `housing_sepp_standards` rows (+2 tied to SEPP E&C 2008) predate both the amendment and the feature, and still read `stale_since IS NULL` today, serving as current with zero notice, 4+ months after a real, detected amendment. **Independently confirmed by reading the code, not assumed**: `services/cdc_screen.py` already reads `stale_since`/`stale_reason` from `cdc_eligibility_standards` and renders a notice (pinned by `tests/test_sepp_auto_stale.py::TestCdcEngineNotice`) — the equivalent path for Housing-SEPP eligibility, `services/housing_sepp_eligibility.py`, never selected those two columns from `housing_sepp_standards` at all. Every CDC/ADG-eligibility answer this engine computed would have served a stale standard with no surfaced warning even on a correctly-fired stamp. **FIXED same session** (branch `chore/dq90-cb-triage-and-commit`): `_fetch_standards_grouped()` now reads both columns (latest wins, paired with its own reason — Sol #839's exact finding on `cdc_screen.py`, replicated and avoided here); `FormEligibility` carries them through `services/upzoning_check.py`'s existing `dataclasses.asdict()` serialization with no further wiring. 4 new tests, full suite green. **NOT fixed, and it is a judgement call per instrument, not a script** (DQ-88's own standing note): the 35 pre-existing rows still need someone to read what actually changed on legislation.nsw.gov.au and either update the standard or dismiss the flag via `scripts/update_instrument_provisions.py`. | ✅ Fixed 2026-09-14 — `dq_probe_live.py --id DQ-96` = **0** (was 35). `scripts/legislation_monitor.py` now runs `backfill_stale_for_flagged_instruments` on every pass, stamping rows stored before an already-flagged instrument's change, dated from that change; run once against production: exactly ids 1-33 (SEPP Housing, 2026-05-15) and 36, 45 (E&C Codes, 2026-06-08). Found on the way: the fresh-change path's `ILIKE '%housing%'` beside a `%s` parameter raised in psycopg2, so the next real SEPP Housing or E&C change would have been logged as an error with no notice — escaped. **The legislative review itself stays open under DQ-88**; no page renders the notice yet (API only). | P2 — not wrong values, a missing notice that the source law changed; real but narrower than a served-data defect |
| DQ-92: **9,121 of 9,461 pending review-queue rows carry a suspect-extractor-bug TAG — that is a triage signal, not a confirmed classification.** Answers a question raised in session: how much of the backlog duplicates a known extractor problem rather than being distinct human review volume? `count_drop` (the re-extract finds far fewer provisions than the approved baseline): 5,479 rows / 28 chapters. `preflight_two_column` (two-column PDF text getting interleaved): 3,642 rows / 85 chapters. Together: **9,121 of 9,461 (96.4%)** carry one of these two tags; **340 do not.** **TWO ROUNDS of Sol cross-review both caught the same overclaim** in earlier drafts of this row, so this is stated precisely: a `suspect_reason` tag is a SIGNATURE the extractor writes about itself, not an independently confirmed defect. The fix proven to actually correct `count_drop` (documented in `memory/project-dcp-review-queue-is-a-bug-report-2026-08.md`: a TOC-page-detection guard over-suppressing real body pages, plus a one-heading-per-page limit) covers **1 of the 28 tagged chapters** (`marrickville/part2-s11-fencing`, 2026-08-14) — the other 27, and all 85 `preflight_two_column` chapters, are **unchecked per-chapter**. A chapter with a genuine DCP amendment that legitimately removed provisions would earn the identical `count_drop` tag, and nothing here can tell the two apart. **Use this split as a triage-prioritisation signal only** — do not exclude the 9,121 from review planning on the tag alone, and do not call the remaining 340 a confirmed-clean set: DQ-71 (source-quote verification, still 0.06% coverage) applies to all of it regardless of this tag. `scripts/dcp_extract_changed.py:2969` deletes **pending** rows for a chapter on every re-extract and inserts fresh, so once a chapter IS confirmed and fixed, its tagged rows are expected to clear themselves rather than need hand-triage. | 🟢 Fixed 2026-09-25 -- backlog replaced by the DQ-111 AI re-reads; 0 pending tagged rows (the detector itself is still wrong, plan s4). Was: (was open) Open — measured 2026-09-04, `python scripts/dq_probe_live.py --id DQ-92` = **9,121** of 9,461 pending carry one of the two tags | P2 — a triage signal that inflates the visible backlog number; not itself proof of which rows are safe to defer |
| DQ-93: **inner-west/marrickville is 14.8% NULL on `v2_topic`, above the 10% threshold the project's own coverage test already sets for it — found live, by nothing else than actually running a real-DB test file nobody had run.** Not a new defect: a pre-existing one surfaced 2026-09-04 while wiring `tests/test_drawdown_verify_real_db.py` into CI (DQ-91/DQ-92). `tests/test_lga_coverage.py` already has a parametrised check (`test_no_null_v2_topic`, per-council thresholds in `ONBOARDED_LGAS`) that would have caught this the moment it happened — except the file carries `@pytest.mark.database`, is deselected by `pytest.ini`'s default `addopts`, needs `PYTEST_REAL_DB=1` to run for real, and **nothing in this repo has ever invoked it** — the identical root cause as DQ-91/DQ-92, on a different file. **Not investigated further here**: why marrickville drifted specifically, or whether other `ONBOARDED_LGAS` entries are also currently red — only this one parametrised case was actually observed this session. `tests/test_lga_coverage.py` is deliberately **not** wired into CI as part of the same change that fixed DQ-91/DQ-92's own gap — doing that today would fail every future PR on a defect this session did not cause. Fixing the data (re-running topic classification for this council) is a deliberate follow-up. | 🔴 Open — measured 2026-09-04, `pytest -m database -o addopts= tests/test_lga_coverage.py::TestLgaProvisionCoverage::test_no_null_v2_topic -k marrickville` fails: **14.8% (583/3,934) vs a 10% threshold** | P2 — a served-data gap on a live council, found by coincidence rather than by design; the design gap (nothing runs this file) is the bigger issue |
| DQ-97: **The "short garbled fragments" symptom flagged after DQ-92's marrickville fix is NOT one bug, and not the two the follow-up prompt started with — a per-chapter real-geometry census found at least five distinct mechanisms behind one coarse regex.** Marrickville's vertical stacked-glyph margin label (PR #1050) fixed marrickville but a coarse symptom-only rescan (any pending row with a run of ≥6 whitespace tokens ≤2 chars) still flagged 523 rows / 47 chapters / 9 councils on 2026-09-06; re-extracting all 47 confirmed the mistake this row exists to correct — 40 of them didn't move, because they share the visual symptom but not the cause. **Re-censused live 2026-09-06: 519 rows / 44 chapters** (marrickville's own 7 dropped to 6 residual). Opened the actual flagged PDF pages with `pdfplumber.extract_words()` for every chapter rather than trusting the regex. Found: **(1) CONFIRMED FALSE POSITIVES** — genuine content, no defect — in marrickville (all 6 residual rows: an Rw noise-insulation table, a flood-risk percentage list, ordinary Title Case prose), blacktown (a flood-risk X/N land-use compatibility matrix), city_of_sydney (3 of 5 rows: clean prose; a 4th is an acoustic-criteria Hz/dB table), and ku_ring_gai's three site-plan/contour chapters (RL elevation labels + compass points off a site diagram). **(2) CONFIRMED NEW, UNFIXED CAUSE — dominant**: **woollahra, ~410 of 424 flagged rows across 21 of 22 chapters**, carries a "Repealed by [instrument] Amendment No. X on [date]" stamp whose characters extract in REVERSED x-order (upright glyphs, decreasing position, not rotated) — decodes cleanly when reversed, e.g. `d e l a e p e R 23` → `Repealed by...`, `... o N t n` → `...No.13 on 12 October 2020`. This is a THIRD mechanism, distinct from both marrickville's stacked-vertical-glyph label and canterbury_bankstown's original word-splitting diagnosis — refines DQ-89's 2026-09-01 `preflight_two_column`/`schema_fail` tagging of these same 22 Woollahra chapters into an actual root cause. **(3) CONFIRMED NEW CAUSE**: woollahra/chapter-c2-woollahra-hca and chapter-f1-child-care-centres additionally carry a running-title word-splitting defect (`WOOLLAHRAHERITAGECONSERVATIONAREADCP` glued from single-letter tokens) — same `extract_words`-tolerance family as canterbury_bankstown/chapter-11-15-marco-avenue's original finding. **(4) CONFIRMED NEW CAUSE**: canterbury_bankstown/chapter-7-6-belmore-and-lakemba (~18 of 21 rows) carries a locality-map label interleave — street/station names (Lakemba Street, Belmore Station, Wangee Road) from a rotated map graphic merging character-by-character under simple top-to-bottom/left-to-right sort; root mechanism not yet pinned down. 3 of that chapter's rows (pages 126/128/130) already match `find_vertical_margin_label_band` on the CURRENT code — i.e. they are STALE pending rows a bare re-extraction would clear, not a live gap in the existing PR #1050 fix. **(5) CONFIRMED COVERAGE GAP in an existing guard**: ku_ring_gai/section-a-part-6-multi-dwelling carries a doubled-glyph phrase (`PPeedddeess...ttrriiaann` = "Pedestrian" with every letter printed twice) that `strip_garbled_header_lines` does not catch, because that guard only strips a whole LINE dominated (>60%) by doubling, and this phrase sits mid-paragraph. **Not yet root-caused** (low volume, 1-2 rows each): ashfield's literal underscore fill-blanks, one ku_ring_gai partial character interleave, canterbury_bankstown/chapter-2-2-flood-risk-management's reversed-order table headers ("Critical Uses"/"Sensitive Uses" — same reversed-order family as (2)?, unconfirmed) and chapter-7-2-city-west's undecodable-glyph replacement characters. **70% of the 519 flagged rows (365) carry `fidelity_status='grounded'`** — the existing per-row review-queue safety net does NOT flag them as suspect, so a reviewer would see ordinary-looking approvable text. Full per-chapter table: `~/.claude/plans/ce-margin-artifact-census-2026-09-06.md`. **NO FIX DECIDED OR WRITTEN** — this row records the census result only. The meta-lesson it exists to correct: a symptom-matching regex finds candidates, not causes, and one confirmed example never generalises to a whole council without checking. **UPDATE 2026-09-07: Woollahra's stamp (cause 2) fixed for the rows that actually mattered — via AI extraction, not a new geometric detector.** The July 2026 architecture decision (`~/.claude/plans/ce-ai-extraction-decision-2026-07.md`) names THIS EXACT Woollahra stamp as the case that killed hand-tuned PDF geometry as a strategy; a new bespoke detector was prototyped this session, empirically validated against real fixtures, then **abandoned** on that basis rather than shipped — the decided, already-proven-on-marrickville (DQ-92) fix is AI extraction, which sidesteps the geometry problem instead of pattern-matching it. Before spending any API budget: checked which of the 22 flagged Woollahra chapters actually SERVE corrupted text to real users (`is_current` rows, not the pending backlog) — only **3 of 22** do (chapter-c2-woollahra-hca 1 row, chapter-b3-general-development 4 rows, chapter-d5-double-bay-centre 1 row); the other 19 chapters' flagged rows sit only in the never-approved review-queue backlog, never served, and were correctly left untouched. Re-ran AI extraction (`AI_EXTRACTION=1 AI_MODEL=sonnet`, memory-only `--review`, no auto-commit) on exactly those 3: **0 `has_margin_artifact` hits in the fresh output for all 3**, confirming the stamp defect itself is gone. c2 is clean (534 rows, 90%+ fidelity-grounded). b3 and d5 additionally surfaced a real, separate `coverage_fail` (4/11 and 43/54 TOC sections missing) — not the corruption defect, an unrelated extraction-completeness gap (likely an `AI_CHUNK_PAGES` chunk-boundary effect) — **not resolved, not approved**. All 3 sit pending at `https://verify.plotdetect.com.au/internal/dcp-review` awaiting a human review before anything commits to `regulatory_provisions`. Backup of all 742 pre-extraction Woollahra pending rows: `data/db_rollback_backups/dcp_review_queue_woollahra_pre_ai_extraction_2026-09-06.json`. Causes (1) [duplicate marrickville-style], (3) map-label interleave, (4) [duplicate — see (3) above, canterbury_bankstown], (5) ku_ring_gai doubled-glyph gap remain untouched. **UPDATE 2026-09-10 — the check went green without anything being fixed, and that is the entry.** This probe counted `dcp_review_queue WHERE status='pending'`. On 2026-09-09 the review backlog was cleared in a single night — **8,875 rows approved** — and the count fell **574 → 0**, so the ratchet reported *"declared OPEN but the check PASSES — it appears to be fixed"*. Nothing was fixed. The rows were approved **out of the queue and into production**: 578 landed in the served set. The check was watching a population an operator can **drain** without repairing anything, and it went green by the defect moving downstream — `feedback-a-check-can-watch-the-field-the-fix-abandoned` and `feedback-audit-rows-are-not-live-claims` in one event. Re-pointed at `is_current AND v2_is_actionable`, where it reads **530**. ⚠ **What the clearance actually did to live data, measured on those 578 rows with the stronger DQ-78 signature rather than the coarse regex:** **0** rows at single-letter-token fraction ≥0.20; **2** in 0.10–0.20 (ids **122374** riverwood-estate, **122379** marco-avenue — both canterbury_bankstown map-label interleave); **2** carrying private-use glyphs (**122970** woollahra definitions, **122386** canterbury_bankstown croydon-street). Of those, **only 122374 is new** — 122379 replaced a byte-identical predecessor, so it re-committed a pre-existing defect rather than creating one. **So the clearance did not mass-corrupt the served set** — it moved a small number of known-bad rows across the line and blinded this metric. The second was invisible from CI until the ratchet's open-but-passing direction caught it, which is the direction that exists for exactly this. | 🔴 Open — **re-pointed 2026-09-10 at the SERVED set**, `python scripts/dq_probe_live.py --id DQ-97` = **530** (was a pending-queue count of 574, which fell to **0** on 2026-09-09 when the backlog was approved, not fixed) — still a triage count, not a defect count, but it now measures **exposure** | P2 — the woollahra stamp's LIVE impact (the only rows real users could see) is now 0 rows across all 3 previously-affected chapters, pending human approval; the ~400 backlog rows in the other 19 chapters were never served and remain low urgency |
| DQ-98: ⚠ **DIAGNOSIS CORRECTED 2026-09-10 — this was never an oversized-PDF problem, and the chunked split was never built.** Measured: pdfplumber caches every page's parsed objects for the life of the PDF object and nothing dropped them, so memory climbed across the **whole batch**, not just the big file — a **4.3MB** ashfield chapter peaked at **611 MB** and left 214 MB resident; three chapters in one process peaked at 1,361 MB holding 628 MB afterwards. The 139MB chapter was simply the first to cross the ceiling. **Two specific errors in the text below:** it names `_maybe_toc_override()` and `_extract_sequential()` as the two full passes, but `_maybe_toc_override` only runs for `TOC_DRIVEN_COUNCILS` = {woollahra, leichhardt} — for canterbury_bankstown the second pass is `_maybe_route_via_ocr()`; and "recurred 3 more nights running" cannot be right for what was then a **weekly** cron (the Railway schedule was wrong too — fixed the same day). **What shipped (PR #1073):** release each page after reading it (`flush_cache` **and** the textmap lru_cache — both needed, measured separately at 626 MB and 1,325 MB versus 1,356 MB with neither and **426 MB with both**), and run the PDF work in its own process so a SIGKILL cannot take the batch down. Output proven **byte-identical** to the previous code on three real chapters covering both extraction paths (same sha256 over sections and over tables) — which is why this was chosen over the split, whose cut point is a real correctness risk for a clause straddling it. **The 30MB guard is REMOVED and must not return:** peak memory does not track file size — ku_ring_gai/section-b-part-14e is 35MB → **726 MB** while canterbury_bankstown/chapter-7-6 is 139MB → **440 MB**. Five of the seven were extracted locally to confirm; the two city_of_sydney chapters have no R2 URL and are untested, which is exactly the case process isolation exists to survive. **The probe changed too, and that is half the lesson** — it counted chapters over 30MB, so it could never reach 0 while large councils exist ([[feedback-a-check-can-watch-the-field-the-fix-abandoned]]); it now counts large chapters never extracted. ORIGINAL TEXT BELOW, KEPT FOR THE RECORD AND WRONG IN THE PLACES NAMED ABOVE: **The scheduled production extraction job gets OOM-killed on oversized council DCP PDFs — confirmed live, not hypothetical.** Railway's `dcp-extract` run on 2026-09-06 03:21 UTC crashed with `exit code -9` (SIGKILL, consistent with an OOM kill) partway through `canterbury_bankstown/chapter-7-6-belmore-and-lakemba` (139,006,750 bytes, 142 pages, two-column layout) — its OCR fallback failed first (`Read timed out (read timeout=120)`) before the raw text-layer pass that then ran out of memory. **Root cause traced in `scripts/dcp_extract_changed.py`**: `_maybe_toc_override()` opens the PDF and builds a list of every page's cleaned text, then (when that doesn't override) `_extract_sequential()` opens the SAME PDF again and does a second full page-by-page pass — each pass accumulates pdfplumber's per-page objects (char/line/table/image data) for the whole document's lifetime, tolerable for a normal few-MB chapter, not for a 139MB one. **Corroborating evidence from a separate session's own work, not just the production log**: `canterbury_bankstown/chapter-6-2-bankstown-city-centre` is the same council's second-largest chapter (117,829,367 bytes) and has not been re-extracted since, so it carries the identical unconfirmed risk; `ku_ring_gai/section-b-part-14e-lindfield-local-centre` (35,405,674 bytes) was one of three ku_ring_gai chapters that reproducibly could not complete the much lighter-weight `dcp_fidelity_gate.py` grading pass within 300s across two independent attempts, while `ashfield/chapter-d-precinct-guidelines` (20,607,908 bytes) graded a full 638-row chapter without issue in the same session — large file size is a real but imprecise proxy (page count, two-column layout, and embedded raster map/diagram images likely matter as much as raw bytes, per the `[preflight] TWO-COLUMN` warnings visible in the production log for every large chapter). **PROPOSED FIX DIRECTION, not built**: detect an oversized PDF ahead of extraction and split it into smaller physical PDFs (`pypdf`/`pikepdf` page-range slicing — cheap IO-level copy, no content parsing) before running the existing per-chapter pipeline on each chunk, bounding peak memory to one chunk instead of the whole document. Chosen over upgrading Railway's container memory because a memory-ceiling fix does not scale with future, larger PDFs (this project's own DCPs keep growing via amendment) while a chunking fix does. **The real design risk, named before any code is written**: a clause can legitimately straddle a chunk boundary — this session's own DQ-97 work fixed several defects caused by exactly this shape of problem one level down in the pipeline (the fidelity checker) — so a correct split needs overlapping chunk boundaries and de-duplication when stitching results back together, not a naive even cut. User explicitly chose to register this now and build it as separate follow-up work rather than pause other in-progress work to design it immediately. **UPDATE 2026-09-09**: recurred 3 more nights running (2026-09-08/09, all exit -9) and turned out worse than first understood — `extract_chapter()` had no size check at all, so the OOM kill took the WHOLE process down mid-batch, not just the oversized chapter: all 47 chapters queued that night failed, not only canterbury_bankstown's. Fixed a NARROWER problem (not this ticket's fix) in `fix/dcp-extract-oversized-pdf-guard`: a 30MB size guard skips the oversized chapter before pdfplumber ever opens it, so the OTHER ~40 chapters in the same batch still complete; the skip is recorded to `dcp_chapter_registry.last_suspect_alert_key/_at` and sends one Telegram alert per distinct (content_hash, size), deduped so an unchanged oversized file doesn't re-alert every night. **This is a stability guard, not the fix** — DQ-98 stays open. Sol cross-review on that PR added a real refinement to the fix direction above: compressed PDF byte size does not bound pdfplumber's DECODED memory use, so a file under 30MB with pathological compression or many content-stream objects could still OOM the batch — the guard is a fast-path filter on the common case (large raw bytes), not a memory bound; the actual fix needs either the chunking approach above OR per-chapter subprocess isolation with an enforced memory limit (Sol's alternative suggestion), not a byte-size check alone. | 🔴 Open — **the fix shipped 2026-09-10 and it is not the one this row proposed**; `python scripts/dq_probe_oversized_pdf_oom_risk.py` = **3** (was 7) and the probe now counts large chapters that have NEVER extracted, so unlike the old size count it **can** reach 0. Stays open until a production run proves it — everything below was measured on a dev machine | P2 — loud, not silent (the job crash alerts via the existing Telegram pipeline, and 2026-09-09's stability guard adds a second, chapter-specific alert) and bounded to specific large chapters, but those specific chapters can never be kept current via the automated pipeline until this is fixed |
| DQ-99: **Precinct-scoped control rows are served to the whole LGA — the `applicability` column exists, has a CHECK constraint naming `precinct_specific`, and nothing reads it.** Found 2026-09-12 while deciding whether to accept precinct-scoped corner-setback and private-open-space proposals: the question "does anything honour scope?" was checked rather than assumed. **The single guarded read is `scripts/conveyancing_db.fetch_dcp_setbacks`**, which every surface proxies through `frontend-nextjs/lib/dcp-controls-client.ts` (by its own header comment, "the ONE module allowed to source those rows"). Its guard stack is `lga`, `is_current` and `(needs_review IS NULL OR needs_review = FALSE)`. **`applicability` is selected and passed through — the TS interface even comments "passed through unchanged — consumers must never fabricate a plausible value in its place" — but it is never filtered, partitioned or flagged on.** So a row whose own condition says it applies to one subdivision is returned for every address in the council, distinguishable from a general control only by reading prose. **7 rows are affected and all 7 pass the served guard** (`python scripts/dq_probe_precinct_rows_served_lga_wide.py`): `ashfield` front_setback **4.0m** (Haberfield Yasmar Estate subdivision, C105); `leichhardt` front_setback **1.0m** twice (Birchgrove and Balmain *neighbourhood minimums*, both with "prevailing setback takes precedence" in the condition); `ryde` car_parking ×4 (Macquarie Park Corridor rates, and 3 of those 4 carry `value_min = NULL`, so they are separately unusable). **The direction is what makes it P2 rather than cosmetic**: a precinct control is typically MORE PERMISSIVE than the council's general rule — that is often why the precinct exists — so the consumer reads the smallest number in the column and builds to it. Leichhardt's general front setback is several times 1.0m. **Same shape as DQ-40**, which is why `secondary_street_setback` exists at all (20 rows served a 2-4m secondary setback as the 4.5-6m primary): there a wrong control_type carried a number out of context, here a wrong scope does. **The fix is NOT to delete the rows** — a precinct control is real regulatory data and is correct inside its precinct. It is for the guarded read to carry scope: either exclude `precinct_specific` from the LGA-wide answer, or return it marked so a surface can render it as scoped. Registered, not fixed; no row has been touched. **Consequence already applied**: every precinct-scoped proposal in the 2026-09-12 extraction run was rejected rather than stored with an `applicability` qualifier, because marking scope in a column no consumer reads does not contain the scope. | ✅ Fixed 2026-09-14 — `fetch_dcp_setbacks` skips `precinct_specific` rows (no precinct to match them against); the probe asks that function for its verdict = **0**. Rows kept. Consequence: ashfield's only front setback was the Yasmar Estate rule, so the triple-setback council count 22 → 21 | P2 — silent and in the permissive direction (a user is shown a smaller setback than the rule), but bounded to 7 rows across 3 councils and every one carries its true scope in its own `condition` text |
| DQ-89: **29 chapters across Woollahra (22) and Ku-ring-gai (7) went SUSPECT in one run, right after Woollahra's council host migrated every chapter's URL — and 30 of the 31 total flagged chapters have NO served-data impact, but the 31st does.** All 31 carry `needs_extraction=True` while `is_active` is still **True on every one**. ⚠ **CORRECTION (Sol cross-review, before merge): "no served-data impact" was asserted for all 31 without checking whether a prior accepted extraction actually exists — it does not, for one.** Verified live: 30 of 31 have `last_extracted_at` set AND a currently-served (`is_current=True`) provision — the review queue is genuinely holding last-known-good content for those, not the broken re-extraction. **The exception is `hornsby/part-1-general`** (one of the 2 pre-existing, older-flagged chapters, not part of today's 29): `last_extracted_at IS NULL` and it has **zero** currently-served provisions — `is_active=True` here means "registered", not "serving content". This chapter has never had a successful extraction; the gap is real, not merely a stale-but-fine copy. Markers on the 29 new ones: mostly `preflight_two_column` (interleave likely — the DQ-78 failure shape, at a scale ~4x larger than DQ-78's own 111), plus 2 `schema_fail` (woollahra chapter-c2-woollahra-hca 43/80 provisions with artifacts, chapter-f1-child-care-centres 5/11) and 1 `count_drop` (chapter-e1-parking-access, 39 extracted vs 65 baseline). The other pre-existing item, city_of_sydney/section-3-general-provisions, DOES have a served provision (part of the 30) — only hornsby is the served-content gap. Both pre-existing rows are timestamped **2026-08-15**, three weeks before the 29's **2026-09-01** timestamp — different councils, different cause, already a known standing item, not to be conflated with today's spike. **Checked and ruled benign, same session:** Canterbury-Bankstown's "53 removed from hub" alert the same day is discovery-list noise (68 active chapters, 0 flagged) — no served chapter affected. Waverley's HTTP 403 hub-scrape failure the same day is an existing month-old gap (last successful check 2026-07-29), not a new break. **Not investigated yet**: whether Woollahra's migrated PDFs are a genuine new two-column typeset (a real layout change, needing DQ-78's remedy: layout-aware extraction at the source, not exclusion) or a scraper/rendering artifact of the migration itself — that needs someone to actually open the new PDFs, which was deliberately NOT done here to avoid guessing at a fix before reading the source. | 🔴 Open — measured 2026-09-01/02, `dcp_chapter_registry` WHERE `is_active AND needs_extraction AND last_suspect_alert_key IS NOT NULL` = **31** (29 new + 2 pre-existing unrelated); of these, **30 carry a currently-served provision, 1 (hornsby/part-1-general) serves nothing** | P2 for the 30 (backlog needing DQ-78-style per-row care); **P1 for hornsby/part-1-general specifically — a registered chapter serving zero content** |
| DQ-88: **7 high-traffic SEPP/LEP instruments currently sit on `needs_review`, unactioned — but only 3 of the 7 back any served content at all.** Split out of DQ-69 2026-09-01 — that row is about whether the legislation monitor RUNS (fixed); this is about whether a human clears what it FLAGS, which is a different failure mode and was being hidden inside DQ-69's headline. Measured live: `instrument_registry` WHERE `is_active AND needs_review` = **7**, all `check_failures = 0` (the monitor saw something and correctly refused to auto-apply it, not a fetch error). ⚠ **CORRECTED 2026-09-05, checked not assumed**: this row previously claimed "SEPP (Housing) 2021 alone backs 241 served provisions" — checked live: `v2_marker ILIKE '%housing%'/'%sepp%'` = 0 rows, `document_id`-linked `regulatory_provisions` = 12, `ref_number` text match = 1. None come close to 241; that figure traces to an UNRELATED "241-row zone repair" elsewhere in this tracker (a DQ-30-adjacent DCP part-key fix), almost certainly copied in by mistake. **Also corrected**: of the 7 named instruments, 4 — Canterbury-Bankstown LEP 2023, City of Parramatta LEP 2023, Sutherland Shire LEP 2015, The Hills LEP 2019 — have **zero rows in `documents`** by name, type, or any pattern (checked, not assumed). Nothing was ever extracted from their text, so nothing served can be citing a superseded version of them; their zoning/numeric standards are served live from the Planning Portal API, not stored text, per this repo's own regulatory-data rule. DQ-88's real scope is **3 instruments**: Inner West LEP 2022, SEPP (Exempt and Complying Development Codes) 2008, SEPP (Housing) 2021 — respectively backing 58, 17 and (via `housing_sepp_standards`, the real table, not `regulatory_provisions`) up to 45 rows of served content. ⚠ **Cannot currently prove these are the SAME 7 the 2026-08-14 measurement named** — the count matches, but `updated_at` is bumped by every monitor run whether or not `needs_review` actually changed that run, so it cannot distinguish "flagged three weeks ago, ignored since" from "cleared and re-flagged on new amendments this week". Sol cross-review caught this claim being asserted without the query to back it (2026-09-01) — recorded honestly rather than fixed by asserting harder. Closing this needs a `needs_review_since` timestamp that only moves on a false→true transition, not on every run. **See DQ-96**: investigating this row surfaced a real, separate silent-failure bug in the `housing_sepp_standards` staleness pipeline, now registered and partly fixed. **Not yet done**: open each of the 3 real instruments, read what the monitor detected, and either apply the change or dismiss the flag with a reason via `scripts/update_instrument_provisions.py` — this is a judgement call per instrument, not a script. | ✅ Fixed 2026-09-15 — all 7 read as in-force text diffs; stored text refreshed with version history (95 rows across Codes SEPP, Inner West LEP, Housing SEPP, I&E SEPP), The Hills R4 rows added, 22 Housing SEPP standards re-verified; `dq_probe_live.py --id DQ-88` = 0. 13 Housing SEPP standards remain stale-flagged as wrong for other reasons | P1 — up to 7 SEPP/LEP instruments backing served clauses may be citing superseded law |
| DQ-83: **A stored length must equal the number and unit in the text it came from — and the value the product does SUMS with is the one nothing was checking.** Two of seventeen patterns in `numeric_extractor` listed `m` before `mm`, so `600 mm` recorded **600 METRES**. #968 fixed the reader and recorded the stored values as out of scope: *"they stay wrong until a re-extraction runs."* ⚠ **Measured 2026-08-17 across EVERY version: 1,101 checkable rules, ALL consistent, 0 misreads.** The 21 known bad values lived in `dcp_setback_controls` and were repaired there; this column either never took them or was already re-derived. **So the re-derivation that sentence implies would have rewritten 19,957 rows to fix nothing, and is not being done.** CURRENT-AIM's *"sixth instance of: right check, scoped to one slice"* closes by SCOPE, not repair. ⚠ **The first version of this check was wrong:** comparing the stored *unit* against the unit in the text flagged 29 rows and every one was a legitimate conversion (`350mm wide` → `0.35 m`). A flag list where most entries are fine trains you to ignore it. The discriminating test is arithmetic — convert both sides to metres — so a conversion agrees and a misread cannot. **Coverage is stated, not implied:** only **432 of 8,340** served rules carry both a value and the text, and the run prints that denominator so a future run over zero rows cannot read as a pass. | ✅ Fixed 2026-08-17 — `check_extracted_rule_units.py` = **0** of 432 checkable | P1 |
| DQ-82: **DATABASE DOWN RENDERS AS "NOT HERITAGE LISTED" — 4 of 6 serve-path fetchers answer a constraint question while unable to look.** Measured 2026-08-15 against a connection whose `cursor()` raises. ✅ Refuse correctly: `fetch_dcp_setbacks`, `fetch_tax_thresholds` (both `None`). ⚠ Answer anyway: **`fetch_heritage_postgis` returns `{'has_heritage': False}`** — the sharp one — plus `fetch_lep_clauses`, `fetch_nearby_das`, `fetch_sepp_housing_standards`, all returning `[]`. **Why the caller cannot save you:** `services/conveyancing.py` wraps each fetch in try/except and sets `_failed[name] = False` on the **success** path; a fetcher that swallows its own exception returns **normally**, so the `except` never fires and the system records a *successful* check that found nothing. This is the three-state failure the compliance testing framework puts **first**, and it is live. **THE GUARD IS REFLECTIVE, NOT A LIST** — `tests/test_serve_path_fails_closed.py` discovers fetchers by inspecting the module, so one added next month is covered the day it is written and nobody need remember the file exists. That is what separates it from the hand-written per-module fail-closed tests already in `tests/`. **Ratcheted, not hard-zero**, because a guard that breaks the build on 4 pre-existing violations is switched off within a week. **Falsifiability proven by mutation:** unlisting a fail-open fetcher fails 2 tests; listing an already-correct one fails 1, since a repaired fetcher must be *released*, not left as amnesty. Carries a control case so a green run cannot mean "zero fetchers examined". ✅ **FIXED 4 → 0 the same day.** All four now **re-raise** after rolling back. **Raise, not return `None`** — because the caller sets `_failed[name] = False` on the *success* path, and returning `None` still returns *normally*, so the flag would read "did not fail" and the system would **still** record a successful check that found nothing. Raising makes the caller's existing `except` fire and the flag correctly stay True, with **no caller change** at the three serve-path sites. One published contract preserved: `get_sepp_standard_value` documents "Never raises", so it absorbs the error and returns `None` — already its "no value available" answer. Two batch callers now propagate (`build_lot_search_index.py:753`, `constraint_arithmetic.py:1252`) and that is intended: failing loudly beats indexing a lot against no SEPP standards. **The baseline is now EMPTY, which is stronger than the ratchet it replaced** — no grandfathered set left to hide in, so any future fetcher that answers anyway fails the build on day one. The release rule was **observed firing** on the way: with the four repaired but still listed, `test_baseline_may_only_shrink` FAILED and named all four rather than leaving them as standing amnesty. | ✅ Fixed 2026-08-15 — 0 of 6 | P1 |
| DQ-81: **THE NSW PLANNING PORTAL IS ITSELF A STALE SOURCE — and `_plan_as_at` ranks it FIRST.** Confirmed against the councils on 2026-08-15, not inferred: the portal reports **Marrickville DCP 2011 "as amended 9 September 2022"** — that is **Amendment No. 15**. Inner West Council's own page lists **Amendment No. 18, in force 31 July 2025**, with No. 16 (1 Apr 2023) and No. 17 (12 Dec 2023) in between. It reports the Comprehensive Inner West DCP 2016 (Ashfield) at that *same* 2022 date while that plan's own chapters are published **Mar-2023 and Apr-2024**. ⚠ **Our own registry already knew** — the documents we hold last changed **2026-06-22** (ashfield) and **2026-04-06** (marrickville), so the contradiction sits between two columns we already store and needs no new source. **HOW IT WAS FOUND, which is the uncomfortable part:** I attached marrickville's portal date this session, reported CURRENCY falling **460 → 403**, and only caught it while researching an unrelated question about which Inner West DCP applies. **The metric improved *because of* a wrong value.** A blank renders no claim; a stale "as at" renders a false currency assertion to a reader who cannot tell — and books as progress. **DQ-80 does not cover this**: that row checks the portal named the right *plan*, and here the identity was correct in both rows and the date was stale anyway. Clears by detaching the portal date and reading commencement from the plan's own version table — **never by re-fetching the portal, which is the stale source.** ✅ **RESOLVED 2 → 0 the same day by DETACHING both dates** — `portal_plan_name` / `portal_raw` / `portal_checked_at` kept, because "we looked and this is what the portal said" is true and is the evidence. Stays a standing guard: re-attaching a date older than our own copy turns it red. ⚠ **The detach exposed a SECOND understatement — currency was never 460.** Ashfield's pre-existing portal date had been masking **20** of its rows from the count since before this session. The honest figure is **480**, and the served-answer baseline was **RAISED** to record it rather than left at a number two false dates had bought. | ✅ Fixed 2026-08-15 — `dq_probe_live.py --id DQ-81` = **0** | P1 |
| DQ-80: **A GUARD, OPENING CLEAN AT 0 — written because nothing would have caught the failure it prevents.** On 2026-08-15 the only thing stopping a Planning-Portal commencement date being attached across a plan-identity mismatch was `pick_dcp_result()`'s token-subset rule — **a convention living inside the single script it governs**, which is precisely the shape `#957` fixed for the ratchet caps. Loosening it is a one-line edit, and **nothing downstream would have objected**: `check_served_answer_quality` counts whether a served row *has* a dated basis, not whether the date belongs to *our* plan. So attaching Bankstown DCP 2015's date to **Canterbury-Bankstown DCP 2023** would have made CURRENCY **fall**, and read as progress. ⚠ **A fabricated currency claim is strictly worse than the missing date it replaces.** This probe re-derives the subset test from what was actually **stored**, against the registry's **current** `dcp_name`, so it cannot be satisfied by editing the fetcher — and it fires on data drift with **no commit** (the Hornsby class: registry moves 2013 → 2024 while a date attached under the old identity keeps serving), which is why it must run nightly and not only in `gates`. **Falsifiability proven read-only, not asserted:** a hypothetical `Marrickville DCP 2027` returns **1**, moving both attached councils returns **2**, removing a council's registry returns **1**. That last case is why it `LEFT JOIN`s — the first draft inner-joined and **silently dropped** an attached date once a council's chapters went inactive, a fail-open reading CLEAN forever, which `/pre-impl` caught before it shipped rather than after. | ✅ Fixed 2026-08-15 — `dq_probe_live.py --id DQ-80` = **0** of 2 attached | P1 |
| DQ-79: **REOPENED 2026-09-01 — this row was declared FIXED while the check was RED, blocking every open PR's gate on a stale claim.** The 2026-08-15 fix (below, unchanged) was real and is still in the code: `head_request()` correctly reads the total from `Content-Range` when a server answers with a `bytes=0-0` range response. But `dq_probe_live.py --id DQ-79` is failing again TODAY, against a **different** row than the one that fix addressed — `dcp_chapter_registry` id 257, `ku_ring_gai` / `section-a-part-8-mixed-use`, `url_content_length = 1`, `check_failures = 0`, `url_last_checked` 2026-09-01 02:04 UTC. Re-ran `head_request()` against that exact URL live just now: **200, content_length 11,022,088, ETag present** — the document fetches fine right now. So today's 1-byte value was a **transient failure during the 78-hour self-hosted-runner outage** (all four runners were offline; see today's session), not a reversion of the 08-15 fix and not a new instance of the same bug class. **Not repaired here**: correcting the live row needs its own backup-scoped UPDATE per this project's DB-safety rules, not a hotfix bundled into a gate-unblocking PR. The row will very likely self-correct on the chapter monitor's next scheduled run now that runners are back online — if it does not, that is worth its own investigation. **What this correction actually does**: makes the ledger say what is TRUE right now (open, red, cause identified) instead of what was true three weeks ago for a different row, so `dq_check.py`'s ratchet stops reporting a false "declared fixed but check fails" mismatch. Original 08-15 finding, still accurate for the row it describes: I claimed the stored hash was "a hash of a failure", that Hornsby's document could no longer be fetched, and that DQ-70 therefore overstated by 32 — **all of that was retracted at the time**. Given Hornsby's current URL, fetching it and the stored one and comparing against the registry showed the document was fine (14,117,244 bytes) and the stored `content_hash 193ac6a4…` was a byte-exact match for the live file, ETag included — Hornsby's source genuinely had changed and DQ-70's 595 was correct. The real bug was one field: `head_request()` fell back to `GET Range: bytes=0-0` when a server answered HEAD with 405, then stored *that* response's `Content-Length` — 1, because one byte was requested — instead of the total in `Content-Range: bytes 0-0/14117244`. Fixed 2026-08-15 by reading the total, falling back to plain `Content-Length` otherwise. `url_content_length` never decided whether content changed — ETag and hash do — so the wrong value corrupted a recorded number, not a decision, and nothing failed downstream at the time. | 🔴 Reopened 2026-09-01 — `dq_probe_live.py --id DQ-79` = **1** (ku_ring_gai id 257, transient during the runner outage; live re-fetch confirms the document is fine). Closes on its own once the chapter monitor rechecks it, or via a dedicated, backed-up row correction if it does not. | P2 — recorded number, not a served decision; no live false claim while open |
| DQ-78: **111 served "provisions" are scrambled MAP LABELS and contain no control at all.** `Go wrie Street Uni B o D n St r r e ee a t R v o y i c n h f S e ord S tre t e` — street names lifted off a map **figure**, where labels at different angles interleaved into nonsense, then served to a planner as a development control. ⚠ **REMEDY CORRECTED 2026-08-15 — do NOT deactivate these rows.** My first reading said "there is nothing in the row to recover, exclude the figure pages". That is **wrong for much of the set**, found only by reading the rows nearest the **cut** rather than the obvious ones at ratio 0.9. The top of the distribution is pure scramble, but rows just inside the boundary carry **real controls with map text interleaved**: id 95870 (0.230) reads *"Objectives (a) Ensure that the safety and amenity of pedestrians and cyclists is not compromised by off-street parking access points"*; id 95375 (0.202) reads *"This locality is bounded by Ashmore Street to the north, Mitchell Road to the east"*; id 95887 (0.213) reads *"Building heights are to comply with 'Figure 6.1'"*. **Deactivating them would hide real controls — the liability direction.** The remedy is to strip figure text from the provision **at extraction**, keeping the prose; not to drop the row, and not to regex the text, because separating interleaved map labels from a control needs the source PDF's layout — the very information the extractor discarded. The metric stays as it is and stays red: it correctly finds affected rows, and what it *cannot* do is tell a pure-figure row from a mixed one, which is the whole remedy. Signature is the fraction of single-letter tokens (real prose sits near zero: only *a* and *I*). **Both thresholds were read off the distribution, not chosen**: ≥0.50 gives 34, ≥0.30 gives 83, ≥0.20 gives 128, ≥0.10 gives 663; the ≥100-token floor is what separates this from DQ-77, dropping the 31-token `s o o m m` rows that score 0.29 but are a unit defect. At the chosen cut **110 of 111 are one council's Section 2 precinct pages** — the shape of a single broken document, not a threshold artefact. Clears by excluding figure pages at extraction. | 🔴 Open — `dq_probe_live.py --id DQ-78` = 111 | P1 |
| DQ-77: **FIXED 581 → 0.** Served provisions split a unit across a space — `900 m m` for 900mm, `7 p m` for 7pm, `20 t h century`. The value is not wrong, but the text a planner quotes is not what the instrument says. ⚠ **Found because of the DQ-76 repair**: stripping the `$` from `$F o o d A c t 2003` removed the symptom DQ-76 could see and left the corruption invisible — **a repair blinding its own metric**, which is why it needs its own row rather than a quiet widening. Every signature sampled before inclusion (`900 m m of a side boundary`, `150 m m diameter sewer main`, `7 { : } 00 p m`); a space inside a unit is never correct here. ⚠ **Deliberately excludes the 4+-spaced-letters signature** — it conflates this with DQ-78's map scramble, and a metric mixing two remedies can be driven to zero by neither. Not repaired alongside DQ-76 because joining `900 m m` deletes a space between characters (safe) while joining `F o o d A c t` requires deciding where words begin (not safe) — that stays with DQ-78. ⚠ **The invariant here is stronger than DQ-76's**: this pass only ever deletes a space between two characters, so the ordered sequence of **non-whitespace characters must be identical** — nothing added, dropped or reordered. **0 skipped, 0 unchanged, 19,957 served rows before and after, DQ-76 held at 9.** The space before the unit is kept (`900 mm`, not `900mm`) because closing it is a typographic preference this pass has no business holding. **UPDATE 2026-09-10 — the metric was catching DQ-78's defect, and the narrowing is the finding.** The ratchet went red with DQ-77 declared *fixed* and the probe reading **1**. That row is not a recurrence: served row **id 122374** (`canterbury_bankstown/chapter-11-14-riverwood-estate`, a real height control — *"Building heights must not exceed the…"* — committed into the served set on 2026-09-09 by the review-queue clearance) is a **map-label interleave**, and the `[ap] m` signature matched a `2` / `a` / `m` sitting on **three consecutive lines**, a fragment of `…boundary` lifted off a map figure. `\s` spans newlines, so any one-character-per-line scramble region can manufacture a hit for a signature written for same-line prose. ⚠ **Measured before narrowing, not after** — loosening a live metric to go green is the failure this ledger exists to catch. Across the whole table including superseded pre-repair rows (the population the 2026-08-15 repair actually cleared) the old class matches **125** rows and space-or-tab matches **118**; all **7** dropped are visibly map scramble — six city_of_sydney Section 2 precinct pages plus 122374 — so **zero genuine unit splits are lost**. Probe and repair predicate narrowed together (enforced by `tests/test_repair_matches_probe.py`), which now also forces the failure both ways: 9 real signatures must still match, 4 scramble shapes must not. **Row 122374 is not repaired by this** — it is still a served provision carrying interleaved map text, and it belongs to DQ-78, where the remedy lives. | ✅ Fixed 2026-08-15 — `dq_probe_live.py --id DQ-77` = **0** (was 581); **re-verified 0 on 2026-09-10 after narrowing the signature to space-or-tab** | P2 |
| DQ-76: **ROLLED BACK 9 → 47 on 2026-08-16 — my repair damaged production and the rise is a correction, not a regression.** The first version unwrapped **every** TeX command generically. Right for a font macro; wrong for an operator — so it **deleted meaning from regulatory formulas**: `ratio $\div 2` → `ratio 2`; the setback formula `(building height− 4.5 m) \div 4 + 0.9 m` lost its division; `Y is A H \div 100` → `A H 100`; a contribution formula's `\frac { X × (100 RY − 3) } 3` lost its fraction; and `\phantom { - } 0.9 m` — where the dash is **invisible alignment** — became a literal `- 0.9 m`. **38 rows written, all 38 restored from backup**, guarded on the exact repaired value, 0 drifted. ⚠ **The invariant could not see it.** Every digit was unchanged; only the operators moved. I guarded the failure I had already imagined, and that is exactly as far as it reached. ⚠ **Found by the adversarial reviewer, not by me** — `scripts/cross_review.py` had *already* flagged `repair_tex_residue.py::correctness` on the original push, spelling out the `\frac{1}{2}` → `12` scenario, and I never read the output. The pipeline worked; the human step failed. **The fix is an inversion**: a command is skipped unless **known** presentation-only; anything else refuses the row and reports it for a human against the source. Re-run now reports **0 repairable, 38 refused** (`\cdot` 23, `\phantom` 3, `\div` 3, `\begin`/`\end` 2 each, `\dag` 2, `\ast` 2). | 🔴 Open — `dq_probe_live.py --id DQ-76` = **47** | P1 |
| DQ-75: **The zone-code lint is blind to the exact shape it was written to stop.** `check_line` flags a line carrying **two or more** distinct zone tokens. A hardcoded zone table is written **one key per line** (`'E1': [...]` newline `'R2': [...]`), so it is never flagged — and that is precisely the `ZONE_DEVELOPMENT_MAPPING` shape of **#928**, which served a hardcoded zone→permitted-use table from a live endpoint for **eleven months**, contradicting the LEP in **135 of 517** (council, zone, claim) triples across 26 councils, **8 against an explicit `prohibited` row**. ⚠ **Evidence, not theory:** `zone_code_baseline.json` tracked 99 files and listed `pages/api/development-types.ts` with 5 violations — but all 5 were unrelated `applicableZones` **arrays** further down the file; the actual mapping was absent, and the two other files holding a full `ZONE_DEVELOPMENT_TYPES` map **were not tracked at all**. **Not fixed here**: the obvious widening (any brace block with 2+ zone tokens) fires on switch statements, test fixtures and the DCP Part keys `PART_KEY_RE` already exists to excuse, and a noisy lint gets suppressed — worse than the gap. ⚠ **Fixing it will RAISE the baseline**, because the guard will find what was always there; that is the correct direction and must not be read as a regression. Opened 2026-08-15. | 🔴 Open — `python scripts/dq_probe_zone_lint_keyed_map.py` exits 1 | P2 |
| DQ-74: **10,103 of 19,957 served provisions record NOTHING about how their applicability was decided.** `v2_dev_type_source` is NULL on them, which is not the same as DQ-33's 1,278 `no_config` rows: those are rows the tagger looked at and could not resolve, these are rows it never looked at. **The two sets are DISJOINT — do not add them.** So a provision nobody ever tagged is indistinguishable from one deliberately left as ALL, and DQ-33's question cannot even be asked of it, because DQ-33's own WHERE clause requires the column to be populated. ⚠ **Third instance of the DQ-68/DQ-24 pattern** — a row scoped to the slice someone happened to measure, leaving the larger population in the same state with nothing watching it. Opened 2026-08-15 while wiring DQ-33's probe, by reading the column's full distribution instead of only the value being counted (NULL 10,103 · config_all 7,673 · no_config 1,278 · config_specific 903). **10,103 → 1,148 on 2026-08-16**; the remainder are rows whose recomputed tags did NOT match the stored ones, so the backfill refused rather than overwrite. ⚠ **READ FROM SOURCE 2026-08-17 - this is NOT a backlog awaiting per-council adjudication, and that framing is recorded here so it is not re-derived.** **1,035 of the 1,148 are STATEWIDE** instruments (Codes SEPP 395, Transport & Infrastructure 131, Housing 129, LEPs), not council DCPs; only **113** are council rows across 10 councils. The disagreement is mostly about **zones** (343 zones-only, 102 both, 703 dev-types-only). **The stored tag is usually right and the recompute usually wrong**: Housing SEPP s87 reaches land through an **OR** - limb (a) *"a residential flat building or shop top housing is permitted ... under Chapter 5, Chapter 6 or another environmental planning instrument"* OR limb (b) *"land in Zone E2 ... or Zone B3"* - and narrowing to E2/B3 would have **hidden the clause from everyone qualifying under (a)**. Only **13** of the 1,148 state a zone scope in their own words; of six read in full, exactly **one** is genuinely over-broad (*"This clause applies only to lots in Zone R5 that have an area of less than 4 000 m2"*, stored as every zone). **The refusal was correct behaviour.** Closing this means recording WHY a row is broad, not narrowing tags - narrowing on the recompute's say-so hides applicable clauses, the silent direction. | 🔴 Open — `dq_probe_live.py --id DQ-74` = 10,103 | P2 |
| DQ-73: **301 of the 365 dated setback controls fall on the 1st of a month — day precision claimed for a date we may only know to the month.** ⚠ **CANDIDATES, not confirmed defects**, framed like DQ-29: a real commencement *can* fall on the 1st, so 301 is an upper bound and NOT 301 things to change. The evidence is the **shape, not the count** — 82% of dated rows, clustered one single value per council: `canterbury_bankstown` 40 rows all on **2025-08-01**, `bayside` 32 all on **2026-04-01**, `hornsby` 30 all on **2025-06-01**. Chance does not do that; a month stored as a day does. **This is DQ-41's class in a different month** — DQ-41 removed the January instances and this asks whether the manufacturing simply moved. Found 2026-08-15 while proving DQ-41's zero was a real measurement rather than a query that could never match. **Adjudicate per council against the plan's own text; set NULL rather than guess** — 706 rows already have no date and that is the honest state. | 🔴 Open — `dq_probe_live.py --id DQ-73` = 301 | P2 |
| DQ-71: **Every provision waiting for approval was waiting on trust — 3,741 of 3,741 gradeable rows had never been checked against their source PDF — AND the check measuring that was itself unable to ever pass.** `fidelity_status` was not the check: 19,199 of 19,649 queue rows carried one, but it is a cheap inline heuristic (garbled glyphs, junk ref, emptied, oversize) that **never opens the document**. `fidelity_source_quote` is the real thing — the passage from the council's own PDF that grounds the row — and **12 rows in the table's entire history had one before this fix. 0.06%.** The backlog's cause was a COUPLING, not an absence: `dcp_fidelity_gate.gate_chapter` was gated on `AI_EXTRACTION`, a flag that **also swaps the whole deterministic extractor for an LLM**, so nobody was ever going to enable it in production just to get verification. Decoupled 2026-08-14 behind its own **opt-OUT** control `fidelity_gate_enabled()`; the three other `AI_EXTRACTION` sites are legitimate (it swaps the extractor, selects that path per council, and runs railguards meaningful only for LLM output) and remain. **THE CHECK ITSELF WAS ALSO WRONG, found 2026-09-05 while acting on this row**: `dq_probe_live.py`'s DQ-71 query tested `fidelity_source_quote IS NULL` as a proxy for "never graded" — but `dcp_fidelity_gate.ground_row` only writes a quote for a FLAGGED row whose quote-matcher clears a 40% word-overlap bar; a GROUNDED row (the majority outcome) has nothing to quote, by design, forever. **That query could never reach 0 no matter how completely the backlog was graded** — a structural instance of [[feedback-a-check-can-watch-the-field-the-fix-abandoned]]. Fixed to test `fidelity_status IS NULL` instead, which `gate_chapter` sets to `grounded` or `flagged` for every row it actually processes, so `NULL` genuinely means "never opened against source." **Backlog then cleared for real, same session**: backed up all 4,705 affected rows first (`data/db_rollback_backups/dcp_review_queue_fidelity_pre_dq71_backfill_2026-09-05.json`), ran `dcp_fidelity_gate.py` per council live across all 9 councils holding ungraded rows (marrickville, ashfield, woollahra, canterbury_bankstown, city_of_sydney, ku_ring_gai, blacktown, georges_river, hornsby) — 186 chapters, ~55 minutes, one interrupted mid-run by a foreground timeout and resumed cleanly (each chapter commits independently, so re-invoking just re-selects what's still ungraded). **Result: 4,742 rows graded, 3,975 grounded (84%), 767 flagged (16%) for human review**, each flagged row now carrying `fidelity_detail` and, where the quote-matcher found a match (377 of 767), a `fidelity_source_quote`. Flag rates varied widely by council — ashfield 6%, marrickville 13%, canterbury_bankstown 21%, city_of_sydney 22%, blacktown 17%, georges_river 14%, hornsby 15%, woollahra 23%, **ku_ring_gai 68%**, concentrated in 15 small site-specific precinct chapters (`section-b-part-14a`…`14o`) where several chapters graded 0% grounded — worth a follow-up look, but every one of those rows is now correctly flagged for a human instead of silently trusted. Cost was checked before switching anything on: one R2 download plus pdfplumber extraction per chapter via the **raw** page path, deliberately not the OCR-aware one, so it cannot inherit the unbounded Modal call. ⚠ A residual after the gate runs is a **FINDING** — the grader read the PDF and could not find the text — not a coverage gap. **This clears the already-queued backlog only** — the gate must run again as new chapters enter the queue (canterbury_bankstown's 391 gradeable rows here are only its 39 already-committed chapters' fresh queue activity, not its full pending set, precisely because the gate already ran on those as part of DQ-95's work). | ✅ Fixed 2026-09-05 — `dq_probe_live.py --id DQ-71` = **0** (corrected query; was structurally incapable of reaching 0 before the fix) | P1 — reviewers were approving unverified text into the served corpus; now every gradeable pending row carries a real source-checked verdict |
| DQ-70: **595 → 262, and the 333 that came off were never stale — they were never re-extracted either.** ⚠ **The re-export optimisation was defeating itself.** When a council recompresses a PDF, the monitor correctly detects the text is identical and skips re-extraction — then updates `content_hash` and **leaves `provisions_extracted_from_hash` behind**. That field has exactly **one writer** (the extractor), so the two diverge permanently, and *their divergence is what this row counts*. **Every re-export created a permanent false entry, clearable only by the full re-extraction the branch exists to avoid.** **Measured before acting** (`scripts/dq70_measure_text_delta.py`, comparing the extracted-from version against the held version in R2 using the existing text detector): **1 chapter re-export only** — ashfield heritage, 333 served, 25,959,773 bytes recompressed to 3,879,460 with **byte-identical** normalised text — **8 chapters real change** (262 served), **0 unknown**. Re-extracting Ashfield would have regenerated 333 provisions to fix nothing and fed 333 rows into a review queue already holding 8,693 and already known to be a bug report. **The remaining 262 are genuine** and still need re-extraction: city_of_sydney §3 (92), leichhardt part-e water (43), hornsby part3 (32), georges_river part-3 (26), ku_ring_gai ×4 (69). ⚠ **Not yet measured:** whether each real change touched the clauses those provisions came from — a chapter can change on one page and leave 90 provisions untouched, so **262 is an upper bound**. **CLOSED 2026-09-21 at 0.** The remaining chapters were re-read and committed: city_of_sydney section-3, blacktown part-c, ku_ring_gai ×2 and northern_beaches warringah-dcp-2011-full, the last of which also brought Part G10 (in force 15 Sep 2025) into the corpus and released that council's plan-in-force hold. 151 → 0 over 2026-09-20/21. | ✅ Fixed 2026-09-21 — `dq_probe_live.py --id DQ-70` = **0** | P1 |
| DQ-69: **FIXED — and this row's own headline sat stale for weeks after the fix landed, which is the DQ-79 pattern again: the check knew, the prose didn't.** Originally: the NSW legislation monitor hadn't run in 67 days and nothing raised an alarm, because `run_loop.sh`'s failure branch was `\|\| echo "will retry next cycle"` — a permanently broken monitor and a healthy one looked identical from outside. TWO independent causes found and fixed: (a) the Fly container died at import (`#504` added `refresh_runbook` to `legislation_monitor.py` without the matching `COPY`, confirmed live by `ModuleNotFoundError`); (b) even when it ran, `check_instrument` returned early whenever the source gave no version — the NORMAL case on the PCO path — so a run reporting "Checked: 26" wrote ZERO rows. **REVERIFIED LIVE 2026-09-01, from two independent sources, not just re-read:** `instrument_registry` shows `last_checked = 2026-08-27 22:36 UTC` on **25 of the 26** active instruments (the 26th, Wingecarribee, is the residual below — do not read "the monitor ran" as "every instrument was checked"), and the ops Telegram channel independently confirms weekly runs on 2026-08-14, 08-21 and 08-28, each "26 instruments checked via pco, no changes." The one open residual, exactly as `dq_checks.json`'s own note already predicted post-fix: **`wingecarribee_lep_2010` has no `pco_instrument_id` and has never been checked** — `dq_probe_live.py --id DQ-69` correctly reads this as count=1 and exits 1, which is the DOCUMENTED floor, not a live defect. **Separate finding, NOT this row — see DQ-88**: 7 instruments currently sit on `needs_review`, matching the 08-14 measurement's count but NOT confirmed to be the identical 7 — `updated_at` is bumped by every monitor run whether or not the flag changed, so it cannot distinguish "flagged three weeks ago" from "flagged this week", and that gap is recorded honestly in DQ-88 rather than asserted away. Either way it is a human-review backlog, not a monitor-liveness defect; conflating the two is exactly the kind of scope-widening this ledger's own rules warn against. | 🔴 Open — `dq_probe_live.py --id DQ-69` = **1** (was 26). Both liveness causes fixed; residual is Wingecarribee (no `pco_instrument_id`), reverified live 2026-09-01 against `instrument_registry` and the independent Telegram alert log — matches the documented floor, not drift. | P3 — one named, understood, non-blocking residual; the liveness gap that mattered is closed |
| DQ-60: **RULE SETTLED 2026-08-13 by the Regulation: the stored date is the FULL DCP's own commencement, never an amendment's.** **EP&A Regulation 2021** — *a development control plan comes into effect on the day on which the notice of the council's decision to approve the plan is published*. That is a stable fact identifying the instrument, the same way NSW Legislation separates an instrument's commencement from its *current version for [date] to date*. **Two rules had been applied to one column**: waverley held **2026-04-18**, which is **Amendment 6's** date, while liverpool held **2008-08-29**, the plan's own. **waverley CORRECTED to 2022-12-08** — its own page: *"The DCP 2022 was formally adopted on 6 December 2022 and was effective between 8 December 2022 to 18 August 2023."* liverpool 2008-08-29 was already right. ⚠ **The currently in-force TEXT is a different fact and is still unrecorded** — Waverley is on Amendment 6, Liverpool on Amendment 34+. That is the staleness question and it needs its own field, not this one. Do not conflate them again. | ✅ Rule settled and applied | P1 (was) |
| DQ-66: **Wingecarribee's 30 controls are cited to the BOWRAL TOWN PLAN but served SHIRE-WIDE.** ⚠ **CLAIM CORRECTED 2026-08-13 — this row previously said a Mittagong or Moss Vale property "is being given Bowral's setbacks", implying wrong numbers. It is not.** All three town plans were downloaded and hash-matched to `dcp_chapter_registry.content_hash`, and **Part C Sections 2–4 — which back all 32 stored controls — are NUMERICALLY IDENTICAL across them**: 100/40/16 numeric tokens per section, **zero** differences in all six pairwise comparisons. Text differs only in town names, figure captions and table numbering. **The defect is MIS-CITATION**: the reference names a plan that does not govern the property, and Bowral's `Table C2.2` is `Table C2.1` in Moss Vale, so it does not even resolve. The half said to have no data behind it does: the registry lists all three town plans, all `is_active`. ⚠ **Not the same as leichhardt's Balmain/Birchgrove or the_hills' Showground rows** — those are place-scoped too but SELF-DISCLOSING, each naming its locality in its own `condition`, which is what makes wingecarribee's silent. **Open decision on the remedy**: extracting the siblings would create ~60 rows duplicating proven-identical values; re-citing to the common Part C may be better. Probe measures the state, not the remedy. | ✅ Fixed 2026-09-15 — every served number cites all three town plans at their own clause and page (migrations 074/075, 28 sibling citations; `dq_probe_live.py --id DQ-66` = 0) | P2 |
| DQ-67: **The town-specific PRECINCT controls — MEASURED 2026-08-14, there is no project here.** Across all 21 precinct sections in the three town plans, **13 carry ZERO numeric controls** (character and design prose), and most of the rest repeat the same conservation block (20%, 2.5m, 1.5m, 90mm, 10m) **identically in all three towns** — so it is not a difference between them. The one genuinely numeric precinct is **Renwick** (Mittagong S18, 1,314 lines, 185 values), and even there the overlap with controls we serve is about **two**: max 2 storeys, max 7m wall height. **Renwick is its own suburb (2575)**, so address→suburb matching reaches it with no precinct geometry. Folded into the Wingecarribee suburb job — `memory/project-wingecarribee-suburb-scoping-planned-2026-08.md`. | ✅ Closed 2026-08-14 — folded into suburb scoping | P2 |
| DQ-68: **16% of every served provision carries no topic — the ledger was narrower than the defect.** **3,197 of 19,957** served provisions (`is_current AND v2_is_actionable`) have a NULL `v2_topic`, so they cannot be routed to the right section of a report or filtered by topic. Concentrated in **statewide instruments (2,530)** and the Inner West former councils (**marrickville 475**, **leichhardt 123**). ⚠ **DQ-24 is a strict subset of this** — it tracks the 523 from one SEPP, which was a defensible scope but left 2,674 rows in the same state with nothing watching them. Opened 2026-08-14 while auditing whether the measurements taken that day were sufficient; they were not. | 🔴 Open — `dq_probe_live.py --id DQ-69` = 3,197 | P2 |
| DQ-65: **How government handles this: TWO fields, never one — and it confirms DQ-60 + DQ-61 as the right pair.** NSW Legislation prints, for every consolidated instrument, its **commencement** AND a currency stamp — *"Current version for [date] to date (accessed [date])"* — plus point-in-time versions with a full history. DCPs are not on NSW Legislation, so councils do the equivalent with the **List of Amendments** table (last row = currency), often baked into the filename (`Wingecarribee DCP 2010 ... as amended 23 Sep 2015`). **Both matter legally because of savings provisions**: City of Parramatta states *"Any Development Application lodged before 18 September 2023 will be assessed in accordance with the relevant previous DCP"* — commencement decides WHICH plan governs an application, currency decides whether your copy of it is the current text. Neither substitutes for the other, which is why conflating them (DQ-60) produced a wrong date and why DQ-61 is a separate column rather than a refinement. | ✅ Model confirmed as standard practice | P3 |
| DQ-64: **canada_bay IDENTITY RESOLVED, one field short of a date.** Clause A1.1: *"This DCP may be referred to as the City of Canada Bay Development Control Plan. The DCP was adopted by Council and came into effect as specified in the List of Amendments."* No year in the name, so it is the consolidated plan whose **Amendment No. 0 was adopted 4 September 2007** — NOT the `Canada Bay DCP 2013` AustLII marks superseded, nor the portal's `Canada Bay DCP 2017`. **The three-plan ambiguity is closed.** ⚠ **Still not written**: 4 Sept 2007 is the ADOPTION date and DQ-60 defines this column as when the plan came into EFFECT. They differ here — Amendment 1 was adopted 5 Feb 2008 and took effect 7 Mar 2008, a month apart — so writing the adoption date would break the rule. **Needed: Amendment No. 0's 'in force' cell** from the List of Amendments table. Source document: `canadabay.t1cloud.com/T1Default/CiAnywhere/Web/CANADABAY/API/CMIS/PUB/content/?id=folder-7719475&streamId=streampdf-7719475` (403s to an automated fetcher; opens in a browser). One cell closes 32 claims. | ✅ Fixed 2026-08-13 — Amendment No. 0 effective **7 March 2008** | P2 |
| DQ-63: **camden 2019-09-16 and cumberland 2021-11-05 dated — 97 dateless claims -> 62.** Camden DCP 2019 adopted 13 Aug 2019, in force **16 September 2019** (`dcp.camden.nsw.gov.au/introduction/preliminary/what-date-did-the-dcp-commence/`). Cumberland DCP 2021 in force **5 November 2021** (council site). Both are PLAN commencements per DQ-60. ⚠ **cumberland is the proof that the council's own site beats the Planning Portal**: the portal still lists pre-merger Auburn and Holroyd plans for it (DQ-42). ⚠ **The search that found these was a PLAIN one** — `camden dcp commencement date`, no quotes, no operators. My earlier phrase-and-operator queries returned the DOCUMENTS and not the ANSWER, and cost several rounds. **Ask the plain question first.** **canada_bay HELD**: three candidate plans in play — a DCP 2013 marked SUPERSEDED, the portal's `Canada Bay DCP 2017`, and a DCP adopted 28 March 2023 — so which one our controls came from is unresolved, which is the DQ-60 identity test failing, not caution. | ✅ 2 councils dated; canada_bay + wingecarribee remain | P2 |
| DQ-62: **parramatta's stored commencement date is an AMENDMENT date and breaks the DQ-60 rule.** Audited all 12 rows carrying a `stated_date` on 2026-08-13. `parramatta 2024-09-18` has evidence reading *"parramatta-dcp-2023.pdf p3 LIST OF AMENDMENTS: latest Date in Force 18/09/2024 of 4 approved/in-force pairs"* — that is the most recent amendment to Parramatta DCP 2023, not the plan's commencement. Written by `scripts/extract_dcp_stated_dates.py`, which parses an amendment table when no commencement clause is present, so **the extractor itself can produce a rule-breaking date** and will do it again on the next council whose plan lacks the clause. Fix is two parts: correct parramatta to the DCP 2023 commencement, and make the extractor either skip amendment tables or record the value in a separate field. The other 10 rows pass — waverley flagged only because its evidence NARRATES the amendment while storing the plan date. | ✅ **Fixed 2026-08-13 — writer AND all four rows.** Writer: earliest wins, `None` when statements span 3+ years, amendment tables write `currency_*`. Rows: **strathfield 2006-05-03** (clause 1.2), **burwood 2013-03-01** (clause 1.4), **the_hills 2013-03-26** (Part A s8) — each old value traced to a consolidation stamp on the same document's cover. ⚠ **fairfield was a FALSE POSITIVE**: its 2024-08-22 was already right because our `...dcp-2013.pdf` IS the **DCP 2024** (clause 1.7); the stale field was `dcp_chapter_registry.dcp_name`, fixed on 3 rows. Probe = **0**. | P1 |
| DQ-61: **The in-force VERSION of each plan is unrecorded, so staleness is undetectable.** DQ-60 settles that the stored date is the plan's commencement. It says nothing about whether our extract reflects the current text. waverley's plan is on **Amendment 6** (effective 18 Apr 2026), but our served copy's own Amendment History lists only Amendment 0 (effect 8 Dec 2022) - corrected 2026-09-17; the earlier 'so we have it' was wrong; liverpool is on **Amendment 34** (Dec 2019) or later while one of our source PDFs is named `...linked-to-webpage-23-January-2017`, so our Liverpool controls may be **two amendments behind and nothing would show it**. Needs a second column — the amendment/version in force and when we last confirmed it — compared against the council's amendment log. | ✅ **FIXED 2026-09-17** — every served council now records which version of its plan we hold (`dq_probe_live.py --id DQ-61` = 0). Dates are the earliest the evidence proves the held version could have taken effect (own amendment table or stamp; a dated amendment the copy's wording shows it includes; or commencement where a copy is identical to the council's current file but no amendment names it, said in the label). nsw_statewide excluded, as in `check_dcp_as_at_coverage.py`. Backups `dcp_plan_as_at_pre_dq61_currency_2026-09-17_0920.csv`, `..._batch2_2026-09-17_1212.csv`. Waverley's copy being Amendment 0 is now an OC-17 plan-in-force problem | P1 |
| DQ-59g: **wingecarribee (30 claims) has NO single commencement date and should not be given one — it is the clearest instance of DQ-43.** The council maintains **17 separate DCPs by locality** (Bowral, Mittagong, Moss Vale, Berrima, Bundanoon, Robertson, the Northern Villages and more), each amended on its own schedule. The three we hold are `as amended 23 Sep 2015` (Bowral), `17 Jun 2015` (Mittagong) and `17 Jun 2015` (Moss Vale). Taking the OLDEST understates Bowral; taking the NEWEST overstates sixteen others — both are false claims and the second fails in the dangerous direction. **The fix is DQ-43: key the as-at to the PLAN, not the council.** The join already exists — controls carry `source_chapter_key` and `dcp_chapter_registry` holds a URL per chapter. Showing nothing council-wide is the correct behaviour until then, not a gap. ⚠ **Priority note: a consolidating draft DCP replacing all 17 is on public exhibition until 15 September 2026**, so per-locality dating has a four-week shelf life. Revisit after adoption. | ✅ Fixed 2026-08-13 — wingecarribee **16 June 2010**; keying stays DQ-43, citation stays DQ-66 | P3 |
| DQ-59f: **The evidence test is INSTRUMENT IDENTITY, not source honesty.** Nobody lies about commencement dates, and a council domain or the Planning Portal is authoritative. The failure mode is **misattribution — right domain, wrong instrument** — and it happened twice on 2026-08-13: canada_bay's own page states an **LEP gazettal date (19 July 2013)**, honest and wrong for a DCP; the **Planning Portal listed Auburn DCP 2014 / Holroyd DCP 2013 for cumberland**, councils abolished in 2016. So the question to ask of any date is not *is this source trustworthy* but *is this the plan we serve*. **liverpool 2008-08-29 WRITTEN** on that test — the source names *Liverpool DCP 2008* and we serve `liverpool-dcp-2008-part-1.pdf`/`part-2.pdf` from the same domain, so the instrument matches. **canada_bay HELD** — `fetch_dcp_as_at_dates.py` reported `IDENTITY MISMATCH: none of 1 portal plans match the served plan (Canada Bay DCP 2017…)`, so which plan our controls came from is genuinely unresolved for this council. That is a specific open question, not general caution. | ✅ Rule recorded; liverpool dated, canada_bay held | P2 |
| DQ-59e: **Two more commencement dates located by web search — NOT WRITTEN, because a search summary is not the same evidence class as the document's own clause.** **liverpool**: DCP 2008 adopted 28 July 2008, came into force **29 August 2008**. **canada_bay**: original adoption 4 September 2007; latest amendment adopted 17 June 2025, **effective 27 June 2025** — and we extracted canada_bay 12-22 May 2026, so our controls postdate it. ⚠ **Both come from a search engine's summary of the source, not from text read in the plan.** The four dates already stored (waverley, bayside, sutherland_shire, ryde) are verbatim quotes from the plan's own commencement clause, and mixing a paraphrase into that column would make the evidence field mean two different things. To confirm: open `liverpool-dcp-2008-part-1.pdf` at 'Adoption of Plan', and Canada Bay's 'List of Amendments' table — clause A1.1 states the plan 'came into effect as specified in the List of Amendments', so the table IS the source. Confirming both would take the count 122 -> 65. | ✅ Fixed 2026-08-13 — primary text read, coverage **0 dateless** | P2 |
| DQ-59d: **Where a commencement date exists, it is in the PLAN'S OWN TEXT — not the council's web page and not the Planning Portal.** Four of nine found this way 2026-08-13: **waverley 2026-04-18** (council page, Amendment 6) · **bayside 2023-04-10** (council page) · **sutherland_shire 2017-08-02** — DCP 2015 clause 1.3: *"approved by the Sydney South Planning Panel on 25 July 2017 and came into force on 2 August 2017"* · **ryde 2014-09-12** — *"adopted by Council on 28 May 2013 and came into effect on the 12 September 2014"*. ⚠ **Sutherland and Ryde publish NOTHING on their DCP web pages** — I checked both and reported no date; the clause is inside the plan document. So 'the council page has it' is wrong as a general rule: the commencement CLAUSE is what to search, and `scripts/extract_dcp_stated_dates.py` already parses exactly that pattern — it found 8 corpus-wide, and these 2 were missed only because those PDFs are not on disk. **Getting the remaining PDFs into `data/dcps` is the mechanical route, not more browsing.** ⚠ Also: canada_bay's page states an **LEP gazettal date (19 July 2013)** — a different instrument; using it for DCP controls would be wrong. wingecarribee has **17 separate DCPs** by locality with a consolidating draft on exhibition to 15 Sep 2026, which is why the portal returned 15 ambiguous plans — there is no single commencement date to find. | ✅ Fixed 2026-08-13 — coverage **0 dateless**, baseline empty | P2 |
| DQ-59c: **MEASURED 2026-08-13: the NSW Planning Portal yields a usable commencement date for ZERO of the 6 remaining councils.** Ran `scripts/fetch_dcp_as_at_dates.py` against each; it resolves a real propId for all six and verifies the plan identity before trusting anything. **cumberland — IDENTITY MISMATCH against 5 portal plans, every one PRE-MERGER**: `Auburn DCP 2014`, `Holroyd DCP 2013 - as amended 9 Aug 2017`, `Auburn DCP 2016`, `Auburn DCP 2010 - Amendment 6`. Cumberland was formed in 2016 from Auburn and Holroyd, so the portal is a decade stale, not lagging. **camden / liverpool / ryde — record found, NO dated phrase.** **sutherland_shire / wingecarribee — 22 and 15 plans match the served identity, ambiguous.** ⚠ This settles the question: the portal's in-force DCP LIST page does carry dated phrases (`Canada Bay DCP 2017 - as amended 19 Nov 2019`, `Ryde DCP 2014 - as amended 10 Aug 2016`) but they belong to plans that either do not match what we serve or predate what the council itself publishes — Waverley's own page states Amendment 6 in effect 18 April 2026 while the portal carries no date for it at all. **The portal is not a shortcut for these councils. The council's own page is, and it worked for the 2 read so far.** | ✅ Answered — portal route exhausted, measured not assumed | P3 |
| DQ-59b: **CANDIDATE commencement dates for 4 of the 7 remaining councils, from the NSW Planning Portal's in-force DCP list** (`planningportal.nsw.gov.au/DCP`, read in a browser 2026-08-13). **NOT written to the database — every one needs an identity check against the plan we actually serve first.** `Canada Bay DCP 2017 - as amended 19 Nov 2019` · `Ryde DCP 2014 - as amended 10 Aug 2016` · `Liverpool City Council DCP Amendment 34 Dec 2019` (month precision only) · `Wingecarribee DCP 2008 - Moss Vale Enterprise Corridor - as amended 14 Nov 2012`. ⚠ **Two are already known-bad**: `scripts/fetch_dcp_as_at_dates.py` reported `IDENTITY MISMATCH — none of 1 portal plans match the served plan` for canada_bay, and Wingecarribee's entry is a **precinct plan**, not the citywide DCP our controls come from. DQ-42 separately records that portal records are stale for 5+ served LGAs. Camden and Sutherland appear with no date at all. **The portal is authoritative for what it lists and still wrong for us where the plan identity differs — that is the whole reason the fetch script verifies the echo before trusting anything.** | ✅ Fixed 2026-08-13 — candidates adjudicated, coverage **0 dateless** | P2 |
| DQ-59: **Council commencement dates are published by only some councils, and the ones that publish them prove our extractions are current.** Read 5 of 9 council DCP pages in a browser 2026-08-13 (WebFetch is 403'd by Cloudflare on council domains; a real browser passes). **waverley**: "The DCP (Amendment 6) was formally adopted on 10 March 2026. The Amendment is in effect from 18 April 2026" — we extracted 10-23 May 2026, AFTER it, so our copy is the current amendment. **bayside**: adopted 22 March 2023, "will come into force on 10 April 2023" — extracted 10-22 May 2026, current. **sutherland_shire**: NO commencement date published for DCP 2015; its amendment log shows a change to vehicular access/traffic/parking in April 2026 (we extracted May, so captured) and a stormwater/flooding change in May 2026 (outside our control set). **ryde**: no commencement date published. **canada_bay**: page URL dead. ⚠ The real value is not the label — it is that an amendment log lets us CHECK whether an extraction is stale, which nothing currently does. | ✅ Fixed 2026-08-13 — every served council dated, coverage **0 dateless** | P2 |
| DQ-58: **3 of 9 `dcp_chapter_registry.council_page_url` values are dead** — canada_bay, camden and ryde all return 404 or a Page-Not-Found, measured 2026-08-13 in a real browser. Nobody finds out until a user clicks a citation link, and the registry is what the as-at 'observed current' basis is derived from, so a rotted URL can never be re-checked and that council can never earn a date. Found while reading council DCP pages for commencement dates. Ryde's 404 page names the correct path itself (`/Planning-and-Development/Planning-Controls/...` vs the stored `/development/planning-controls/...`), so this is URL drift, not removal. | 🔴 Open — measured, needs a probe that fetches every registry page URL and counts non-200s | P2 |
| DQ-85: **`lookup_lga` reads the `height` layer, which covers 75 councils. The `zone` layer in the SAME TABLE covers 128 — every NSW council.** So 53 councils are unresolvable for every satellite product that scopes by council, and **the boundaries were never missing** — the lookup reads the narrower of two layers sitting side by side. `services/lga_lookup.py::lookup_lga` queries `spatial_overlays WHERE layer_type='height'`; its own docstring has always said "covers 75 LGAs", while DQ-57's row and `ce-satellite-repair-PROMPT.md` both called it *statewide*. **80 of the 102** unresolved flood reports fall inside a zone polygon and would resolve today. Counted as **councils, not affected reports**: a report count reaches 0 when those rows age out of the 90-day cache while all 53 councils stay exactly as unresolvable — a check passing because its evidence expired (raised by cross-review of the first version). Deriving 128 from the zone layer means NSW's council count is measured here, never hardcoded. **This does NOT serve a false clear** — `flood_truth.py:1616` reports an absent study as unconsulted when the council is unknown. | 🔴 Open — measured 2026-08-24. `dq_probe_live.py --id DQ-85` = **53**. Remedy is a lookup change, not an ingestion; falls to 0 only when a council actually becomes resolvable. | P2 — blinds council scoping across every satellite product, not just flood |
| DQ-87: **The flood screen's recall is MEASURED but not ESTABLISHED, and there was no ledger row saying so — and the first measurement of it was itself wrong.** Status lived only in `ce-product-assurance-position-2026-08.md` as prose. Re-ran `scripts/run_flood_calibration_2022.py` on 2026-08-25: **recall 0.946 over 37 in-scope points (35 hits), cluster 95% CI 0.727-1.000 across 7 council clusters**, against a **0.90 mark committed before the first run**. The interval **straddles the mark**, so the verdict is *indistinguishable from it*. **The prompt's "~150 points would settle it" does not hold** — 150 DRAWS yield 37 scorable points, because EMSR567 mapped NSW and south-east Queensland and the script rightly refuses to score Brisbane as NSW recall. The binding constraint is **cluster diversity, not sample size**: 7 councils cannot produce a tight interval however many points come from them. **CORRECTION 2026-09-01:** this row originally recorded **0.919 (34 hits)** from the same script, same seed (20220228) — which contradicted this repo's own already-published "final" figure in `docs/qa/flood-calibration-2022-result.md` (0.946, PR #897), caught mechanically by `tests/test_flood_calibration_artifacts_agree.py` at push time. A third run reproduced 0.946, not 0.919. Cause, confirmed live in the rerun's own output, not merely suspected: the script makes per-point calls to `maps.six.nsw.gov.au` (DEM identify) and `www.bom.gov.au` (SOS2 / flood history) with 15-30s timeouts, and both hosts read-timed-out repeatedly mid-run — a timeout on a borderline point can flip its hit/miss between otherwise-identical runs. **This does not change the verdict**: `cluster_lo` is 0.727 in both the 0.919 and 0.946 results, still below 0.90 — DQ-87 stays open either way. What it changes is that the recall POINT ESTIMATE is not stable run-to-run and must be treated as provisional; the cluster interval, not the point estimate, is what governs, and that was already the probe's design. The probe pins the CONCLUSION (`cluster_lo >= pass_mark`), never the recall figure — a rerun that moves recall is a remeasurement, not a regression. **No specificity figure exists at all.** Run wrote nothing: `persist=False` (#1005) verified, flood rows 166 before and after. | 🔴 Open — measured 2026-08-25, corrected 2026-09-01. `dq_probe_flood_calibration.py` = exit 1 (0.727 < 0.90). Closes when flood events in MORE COUNCILS are added to the reference set. | P2 — a live product whose accuracy claim is unestablished; every surface must keep saying so |
| DQ-86: **81 servable cached flood reports predate the council lookup, at addresses it could have resolved.** Raised by cross-review of DQ-57's new probe, and correct: that probe's population is *`address_council` key **present** and null*, so a report written before #897 carries no key at all and is not counted. It is not DQ-85 either — these points sit **inside** the height layer, so the lookup would answer for every one of them if it were asked. Kept out of DQ-57 **deliberately**: DQ-57's remedy was "call the real lookup", that is done and verified, and reopening it for rows written before its own fix existed would make it unclosable a second time — the exact failure being repaired. Scoped to the 90-day cache window because that is the exposure; without the window it is 109, and the other 28 cannot be served. Same scoping, same reason, as DQ-50-window. | 🔴 Open — measured 2026-08-24. `dq_probe_live.py --id DQ-86` = **81** of 109. Falls to 0 as the cache window rolls or on regeneration. | P3 — under-reports (unconsulted, not clear); weaker than a regenerated report, never wrong |
| DQ-57: **The SES lookup returns no council name for 80% of flood reports, so the flood three-state fix's council scoping is close to inert.** Measured on all 151 stored flood rows: 30 (20%) fall inside a council study extent and always carry `ses_study_lga`; **109 (72%) were queried, fall outside every extent, and carry NO council name — 100% of them**; 12 (8%) were never queried. `ses_study_lga` is not "which council is this address in", it is "which study matched" — a different question, and it is null precisely when no study matched, which is exactly the case where an absent study would matter. So #892's scoping (report an absent study only when it belongs to this address's council) fires almost only when the study was already consulted. **The measurement inverts the assumption in #892's residual note:** this was written as a rare edge case and it is the common one. The right signal already exists — `services/lga_lookup.py::lookup_lga(lat, lng, conn)` resolves LGA from the `spatial_overlays` height layer by `ST_Contains`, and `flood_truth.py` already opens connections via `_get_conn()`. **CORRECTION 2026-08-24: that layer is NOT statewide.** It holds 75 distinct `lga_name` against NSW's 128 councils, so 53 councils cannot be resolved at all — `lga_lookup.py`'s own docstring has said "covers 75 LGAs" since it was written, and this row said otherwise. The residual is tracked as DQ-85. Flipping the default instead (treat unknown council as not-assessed) would mark ~80% of reports unassessed and destroy the signal, so the rate decides the policy: use the real lookup, do not pick a default. | ✅ **Fixed 2026-08-10 — PR #897**, confirmed by measurement 2026-08-24. `_query_address_council()` was added and wired into the flood query pool, and `flood_truth.py:1608` now reads `address_council` first, falling back to `ses_study_lga` only when it is absent. **The row nevertheless read Open for 14 days, because its CHECK MEASURED THE WRONG FIELD** — it counted `ses_study_lga` nulls, and that field is null BY DESIGN when no study matched, so the query could never reach 0 and this row could never close however well it was repaired. It also watched the exact field #897 deliberately stopped scoping on. Live 2026-08-24: **533 reports have run the lookup, 431 (81%) carry a council, 102 (19%) do not, and 0 of those 102 sit inside the height layer** — every one is DQ-85's coverage gap, not this defect. Forced red on the 109 pre-#897 reports that never ran the lookup and DO sit inside the layer. | P2 — correctness of a fix to a P1, not a live false claim |
| DQ-56: **233 tests may assert that an absence produces a NEGATIVE verdict rather than an unknown one — the class that hid the flood defect, and nobody had looked.** Distinct from DQ-53 (tests that CANNOT fail): these can fail and do run, they simply assert the wrong thing, so every gate was green while six of them guarded a false answer on the most consequential field in a property report — one named `test_epi_none_class_not_in_100yr`. Swept by `scripts/sweep_absence_negative_tests.py` (read-only, 200 Python + 81 TS/TSX test files): 55 tier-1 (served hazard verdict), 33 tier-2 (eligibility), 65 tier-3 (other served fields), 80 tier-4 (internal). **A candidate is not a defect** — `False` is right when a source was asked and said no, wrong only when it was never reached, and the two are indistinguishable from test text. Triage is cheap because good names announce themselves: `test_overlay_absent_is_false_only_when_layer_covered`, `test_heritage_lists_are_three_state` and `test_contaminated_failure_vs_genuinely_none_are_distinct` are all already correct, which is evidence #872/#873's typed-absence work landed. **The one confirmed live defect found: `frontend-nextjs/app/api/lot-search/route.ts:195-197` serves `heritage: r.heritage ?? false`, `flood_prone: … ?? false`, `bushfire_prone: … ?? false`** — a NULL overlay, meaning it was never resolved for that lot, is served as "not heritage, not flood prone, not bushfire prone" across three hazard flags at once. Pinned by `__tests__/api/lot-search.test.ts:297`, whose title states the defect as the intended behaviour: *"null heritage/flood/bushfire default to false in response"*. Consumed by `components/prospector/ProspectorClient.tsx` and `SummaryDashboard.tsx` — the Prospector surface, which memory records as shelved for lack of traffic, so the blast radius is small but the code is live. | 🟡 **CLOSED AS NOT WORTH CONTINUING — user ruling 2026-08-08.** One real defect in 233 candidates, on a feature with no traffic: this line of work stopped earning its keep. The lot-search defect is fixed separately. The remaining 232 are NOT adjudicated, the keyword tiering is NOT fixed, and neither should be reopened. Kept logged so the class is on the record and the sweep can be re-run if a served defect of this shape ever surfaces again — not as a backlog. | P2 — one confirmed live three-field defect on a low-traffic surface; the rest unadjudicated |
| DQ-55: **Three docs describe GitHub Actions workflows as current infrastructure; the workflows were deleted in #506 and only `gates.yml` and `main-red-alarm.yml` exist.** `docs/DCP_MONITORING.md:26-27` lists `.github/workflows/dcp-monitor.yml` and `dcp-extract.yml` in a table of live files ("GitHub Actions schedule + manual trigger"); `docs/DCP_UPDATE_GOVERNANCE.md:157` gives `dcp-extract.yml`, `dcp-commit.yml` and `dcp-watchdog.yml` a running cadence ("Daily 10:00 UTC"); `docs/QA-DATA-PROVENANCE.md:312` names `.github/workflows/satellite-freshness-monitor.yml` as the health-checks workflow. Anyone reading these believes scheduled extraction and a freshness monitor are running. Neither is. **`docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md:22` flagged the governance doc as stale in JUNE and it was still stale in August** — a doc that documents its own decay is not a fix. **Correction to PR #890, which said "seven workflows":** 13 distinct filenames are named across 27 citations, but 9 of them are in `docs/RAILWAY_MONITORS.md`, a deliberate "what happened to each workflow" migration table, and are correct by design. Only these three docs carry false CURRENT-state claims. The same filename in a migration table and in a live-infrastructure table means opposite things, and `scripts/doc_claims.py` cannot tell them apart — a reader can. | ✅ **FIXED 2026-08-12.** All three docs corrected against `docs/RAILWAY_MONITORS.md`: the DCP monitor and watchdog run as **Railway crons weekly**, and the satellite freshness monitor is **weekly, not daily**. The important correction is not the names — **DCP extraction is MANUAL and nothing schedules it.** The old auto-trigger was deleted in #506 and never replaced, so a detected change sets `needs_extraction=TRUE` and then waits for a human. The docs claimed a chain that has not run for months. Pinned by `dq_probe_stale_workflow_docs.py`. | P2 — false infrastructure claim, no served-output impact |
| DQ-54: **Any hook-called script that shells out to git can be silently answering about the WRONG repository.** Git exports `GIT_DIR` and `GIT_INDEX_FILE` to its hooks and they OVERRIDE `cwd`. Measured, not assumed: in a **worktree** — this project's standard workflow — all four hooks receive an absolute `GIT_DIR`, and `pre-commit`/`commit-msg`/`post-commit` also receive an absolute `GIT_INDEX_FILE`; in a plain clone `pre-push` receives neither. Demonstrated live: with `GIT_DIR` pointed elsewhere, `git log`, `git rev-parse --git-common-dir` and `git ls-files` run from this worktree all answered about the other repository, exit 0, no warning. **This already caused damage on 2026-08-07:** during a `pre-push` run, `tests/test_doc_claims.py`'s fixture `git commit` landed on the real worktree's branch and replaced its index (recovered by SHA, nothing lost). Exposed today: `scripts/cross_review.py` (2 calls, `cwd=_REPO_ROOT`), `scripts/validate_schema_contract.py:408` (`--git-common-dir` used to locate the `.env` that supplies `DATABASE_URL` — wrong repo means wrong credentials), and `scripts/qa_gate.py:1385` (`git log` for the commit-hash binding, while the SAME FILE scrubs correctly at :393). Already neutralised: `scripts/qa_gate.py:393-400`, `scripts/doc_claims.py` (`git_env()`), `tests/test_doc_claims.py`. Not exposed by design: `lint_bracket_access.py`, `lint_hardcoded_zone_codes.py`, `liability_language_check.py`, `pr_overlap_guard.py` — they pass no `cwd` and genuinely want the hook's repo. | ✅ **Fixed 2026-08-12 — PR #930.** The prescription said "one shared `git_env()` helper at **three** call sites"; an AST ratchet found **nine**. The four the hand-written list missed were `prove_qa_report_binding.py`, `prune_qa_reports.py`, `sol_common.py` and `sweep_absence_negative_tests.py`, then tightening the ratchet to require `git_env()` specifically surfaced `measure_flood_zone_unassessed.py` and `run_flood_calibration_2022.py`. Three of the nine locate the `.env` supplying `DATABASE_URL` or an API key; one DELETES files. Pinned by `tests/test_git_env_ratchet.py` — first run 4 failed / 242 passed against unpatched code, now 246/246 — and by `dq_check.py`, so this row cannot silently rot back. **A second incident occurred between logging and fixing:** #927's push failed because pytest inherited the hook's `GIT_DIR`. Prose did not prevent it; the ratchet does. | P2 — silent wrong answer in gates; two live incidents, no production impact |
| DQ-53b: **PR #883's fifth falsifiability case never held, and nothing noticed.** Re-running #883's proofs through the hardened `scripts/falsifiability.py`: the four RED cases reproduce EXACTLY as claimed (daylight saving ignored → 3 failed, the 183.0 constant restored → 42, suncalc lat/lng swapped → 81, a 0.6° bearing drift → 41), on current main and at #883's own tree, restored byte-identically. **Those four claims survive.** The fifth — a 0.15° drift asserted to be INSIDE the 0.50° pass mark and therefore still passing — goes RED, and goes red at commit `a7edd825` itself, so it never passed. `services/solar_position.py` and `tests/test_shadow_calibration.py` are byte-identical to #883, so this is not drift. Cause: the served bearing is `round(x, 1)`, so quantisation pushes a 0.13–0.15° planted drift past the mark; measured real headroom is 0.10° (0.10 passes, 0.13 and 0.15 fail). Measured worst deviations on the fixture grid: altitude 0.2057° at sep21_12pm/NSW envelope SW, bearing 0.3185° at Tweed Heads, raw azimuth 0.3463° at sep21_12pm/NSW envelope NE (this last figure is the 0.346° in plan §4h — correct). The case was in the throwaway script only, never in #883's QA report, so **no report claim is falsified** — but the script's own output would have read `*** FALSE ALARM ***` and no one recorded it. **PR #885 makes no plant-restore claim at all** — its falsifiability is the repair-verification structure (dry run, md5 guards, independent census, re-run selects zero), so it is unaffected. | 🟢 Verified 2026-08-08. Calibration verdict UNCHANGED — the pass marks were never in question and the numbers were re-derived live against pvlib. Only the tolerance-floor sanity case was mis-sized. | P3 — proof hygiene, no served-output impact |
| DQ-53: **Contract tests that compare two stored artefacts instead of comparing against a live call — a check that cannot fail in the way its own name claims.** `test_climate_hazard_contract_matches_service_to_dict_keys` was commented "locks ClimateHazardOutput to the exact keys HazardScore.to_dict emits", but compared the Pydantic contract to a **stored golden fixture**. When `to_dict` gained `confidence_reason` (output-grounding, 2026-08-03) the contract and the fixture were both missing it — wrong in the same direction — so the comparison stayed green for weeks while neither side matched the service. The module docstring asserted the same thing in prose: captured fixtures "cannot be self-confirming: if a service renames a key, re-capture + these tests diverge." True for a RENAMED key; false for an ADDED one. Same shape as DQ-30's "0% drift" verification, which compared code to itself. **Scope is UNMEASURED:** one instance is fixed, but nobody has counted how many other contract/golden tests across the suite assert artefact-against-artefact. | 🟠 Logged 2026-08-07 — one instance fixed (now references a live `to_dict()`; falsifiability proven by planting 4 mismatches — extra serialised key, re-serialised composite field, contract-only field, stale fixture — all red, all restored byte-identically) and the docstring corrected. **Suite-wide census NOT done.** Fix = enumerate every test asserting a contract against a fixture and re-anchor each on a live call wherever the service runs on the dev box. | P2 — serves no wrong data; it is a gate that silently does not gate |
| DQ-52: **The shadow landing page SOLD "Surface-change screening detail" as a paid-tier feature (`free: false, paid: true`) for a check that has never once returned a reading in 538 attempts.** `landing/data/shadow.ts:57`, beside a $29/$39 price. The detector is 0/538 across the whole stored corpus (231 insufficient-scenes, 10 timeouts, 5 errors, 292 legacy zeros) while all 538 reports rendered a confident negative about neighbouring land. **This is a category beyond DQ-47 (pvlib):** that was a false claim about METHOD with no price attached; this is a commercial representation about WHAT A BUYER RECEIVES, on the paywall comparison table — conduct in trade, not just an inaccurate methodology note. Four further surfaces advertised the same capability: the feature card (`shadow.ts:43-44`), the data-source chip (`:20`), the methodology prose (`:61`) and the public methodology page (`app/how-it-works/page.tsx:72`, "Spectral change detection to identify recent construction near the property"). | 🟢 Logged then removed 2026-08-07 (§4h removal, user ruling) — all five representations deleted; the check itself removed from every render surface; `services/sentinel2.py` deleted (zero remaining consumers). Logged BEFORE removal so the record shows it was found and why it mattered. | P1 — paid-feature misrepresentation |
| DQ-47: **pvlib named as our shadow method on the PDF, the marketing page, the seeded disclaimer and 381 audit-trail rows — while never imported anywhere in the repo.** `git grep -nE "^\s*(import\|from)\s+pvlib"` returns nothing on origin/main 0c41c09d; the only shadow library the code imports is pybdshadow (`shadow_model.py:92`), which derives sun position itself. The disclaimer additionally credited it as "NREL-backed, peer-reviewed". Related: the served `shadow_direction_deg` is a stored per-scenario constant, not a per-report calculation, and nothing said so. | ✅ Fixed 2026-08-06 (Lane 1 / D1) — PDF, marketing, audit-trail source string, docstrings and internal docs now describe pybdshadow only; `migrations/064` seeds `shadow-v2` and supersedes v1. `requirements.txt:197` still pins the unused package — flagged, not removed. | P1 (was) — false method claim on served output |
| DQ-48: **A named SAR flood threshold and endpoint sat in `flood_truth.py` with zero call sites**, reading as a shipped detector: `FLOOD_RATIO = 1.25`, `PC_CATALOG`, `S1_COLLECTION`. No pystac/planetary-computer import; the live path nulls every `sar_*` field and the manifest records `sentinel1_sar.queried: false`. | ✅ Fixed 2026-08-06 (Lane 1 / D2) — all three deleted; grep-confirmed zero references; no served output changes. `services/CLAUDE.md` flood section marked NOT BUILT. | P2 (was) — ambiguity about a capability we do not have |
| DQ-49: **Granny-flat reports served "you confirmed N structures — counts agree" and a "high" confidence for a count the user could not change.** `onCountChange` was passed to `ConfirmationPanel` and never invoked, so `confirmed_structure_count` could only echo the detector. Measured on production: 16 rows carry both counts, 13 "agree" — **0 of 16 carry human input**; both apparent disagreements are the frontend's `: 1` fallback when detection found nothing. 8 of 16 rows are "high" on that basis. Also: the 4-option per-structure answers never left the browser, `detect_id` was accepted and never stored, and the confirm write (`ON CONFLICT DO UPDATE`) deleted the detect row's `detected_structures` — 0 of 87 rows hold a structure and a judgement about it together. | ✅ Fixed 2026-08-06 (Lane 1, items 3+4) — structural provenance field `inputs.confirmed_count_source` (`secondary_detections_classified`/`machine_default`/`unrecorded`, absent ≠ human); `inputs.structure_types` persists per-structure answers bound to `detected_structures[].index`; `inputs.detect_id` stored; `detected_structures` carried through the confirm write; count control wired on both surfaces; "high" now requires `secondary_detections_classified`. 10 old-doctrine tests flipped with reasons. | P1 (was) — served claim of human validation that never occurred |
| DQ-51: **`confirmed_structure_count` drove the SEPP cl 53(1) multi-structure eligibility gate and was caller-supplied** — a request submitting a count lower than the detect run found slipped under the `>= 3` block. Pre-existing; nothing validated the count before. | ✅ Fixed 2026-08-06 (Lane 1, Sol round 11) — the detect row is now read on the SEPP-standards connection BEFORE the eligibility gate, and `_effective_structure_count` derives the gate's count from the detected structures less those answered part_of_main/rejected. The submitted figure is used only when there is nothing better, is kept beside it as `confirmed_structure_count_submitted`, and a divergence is served as a warning. An `existing_gf` answer also now outranks a contradicting `existing_secondary_dwelling=false`. | P2 (was) |
| DQ-50: **143 cached flood rows still carry "Microsoft Planetary Computer S1 RTC" in their stored `data_sources`** (131 inside the 90-day cache window, newest 2026-08-03), and the cache path serves `cached["data_sources"]` verbatim — so DQ-44's fix stops NEW rows naming the unqueried source but old rows keep serving it on a cache hit. Separately `_DATA_SOURCES_BASE` (`flood_truth.py:133`, used at `:1819`) still hardcodes that source as the empty-list fallback; 0 rows can currently reach it. | ✅ **FIXED 2026-08-12 — 143 → 0.** `array_remove` of the single false literal across 143 flood reports (121 of them inside the 90-day cache window). Backup: `property_reports_dq50_backup_20260812`. Repaired inside a transaction with checks BEFORE commit — the first attempt ROLLED BACK because a guard counted 22 source-less reports; they proved pre-existing `solar-yield` rows, **0 of them among the 143**, so the guard was re-scoped to 'no row I TOUCHED ends up empty' rather than loosened. Verified after commit by `dq_probe_live.py --id DQ-50` → 0, and the ratchet went RED on the stale 'open' status until this row was updated. ⚠ **Separate finding, NOT fixed:** those 22 `solar-yield` reports carry NO data sources at all. | P1 — live false source claim on cache-hit reports |
| DQ-44: **Flood served "Microsoft Planetary Computer S1 RTC" as a data source on EVERY report while no S1 query has ever run** (`sar_flood_detected` hard-nulled; batch is a Phase-3B stub) — a named source with no query behind it, on the flood report + PDF ("Most recent pass" implied an analysis). | ✅ Fixed 2026-08-03 — source appears only with a SAR result (`flood_truth._build_data_sources`); PDF SAR row says "Not analysed in this report"; manifest records `sentinel1_sar.queried: false`. Two old-doctrine tests flipped with reasons. | P1 (was) — false source claim on served output |
| DQ-45: **granny_flat lot clipping crashed on every surviving detection** — the filter-loop variable `bbox` shadowed the tile-bbox dict, so WGS84 conversion and `_pixel_area_to_m2` string-indexed a pixel LIST → TypeError → whole run collapsed to `detection_failed` whenever detection got that far. | ✅ Fixed 2026-08-03 — renamed to `bbox_px`; pinned by two loop-survival tests (test_execution_manifests.py). | P1 (was) — silent product-killing crash |
| DQ-46: **Terrain asserted "Geoscience Australia 5m DEM" even when the SIX Maps photogrammetry fallback served the raster** — the provider decision was only logged; the interpretation's `data_source` was a static claim. | ✅ Fixed 2026-08-03 — `fetch_dem_region_with_provider` returns the actual provider; `data_source` names it (or says "provider not recorded"); old pin flipped. | P2 (was) — misattributed source on served output |
| DQ-43: **`dcp_plan_as_at` is keyed by LGA, not plan identity** — an as-at date binds to the plan named in the section header, but a council serving current controls sourced from TWO plans (Waverley holds 4 `v2012-current` rows beside its 2022-plan rows) would date the older rows with the newer plan's date. Not live today: the only date-rendering LGAs were verified single-plan (ashfield portal; 8 stated LGAs), and Waverley renders no date. Durable fix needs the plan-identity model from the condition-structuring workstream — deriving identity from `dcp_version` labels is the banned parsing class. | 🟠 Logged 2026-08-03 (Sol finding, overridden with reason) — revisit when plan identity exists | P2 — latent, no live exposure |
| DQ-41: **528 of 893 `dcp_setback_controls.effective_date` values were `YYYY-01-01` manufactured from `dcp_version` labels** (migration 040's parser: `v2016-current` → 2016-01-01; `v2014-amended-feb-2026` → 2014-01-01, contradicting its own label). | ✅ Fixed 2026-08-03 — cohort NULLED (authorized): 528/528 via `scripts/repair_dq41_null_label_derived_dates.py`, backup `dcp_setback_controls_dq41_null_20260803`, verify 365 dates remain / 0 Jan-1. Nothing lost: `dcp_version` retained, `dcp_plan_as_at` is the precision-honest re-derivation home. The 365 surviving non-Jan-1 dates still carry no basis (separate question, unattributed, not served). | P2 (was) |
| DQ-42: **NSW Planning Portal `/dcp` records are stale for 5+ served LGAs** — lists pre-merger plans for Canterbury-Bankstown (Bankstown 2015 / Canterbury 2012), Cumberland (Auburn/Holroyd) and Georges River (Hurstville/Kogarah); Canada Bay shows DCP 2017 vs the council's 2020 plan; Hornsby shows DCP 2013 (amended 2019) vs the 2024 plan; all Inner West parcels map only to the Ashfield comprehensive plan. Permanent evidence that the portal-first authority hierarchy REQUIRES the served-plan identity cross-check in `scripts/fetch_dcp_as_at_dates.py` — a portal date must never attach across an identity mismatch. | 🟠 Logged 2026-08-03 — guarded in code (identity match + fail-closed), portal upstream not fixable by us | P2 — guarded, permanent constraint |
| DQ-40: **28 controls whose `control_type` contradicts their own quote — 26 SERVED.** A secondary-street setback (2–4m) served as the primary front setback (4.5–6m), across ≥10 councils. 24 of the 28 PASS the value checker: the number matches, the control is wrong. A class that check structurally cannot see. | 🟢 Fixed 2026-08-03 — 20 re-filed (migration 054), canada_bay 701 repaired 1.5→6.0, MISSING_PRIMARY set adjudicated against source (2 adds, 1 retire, 2 fail-closed flags); 3 rows remain open pending non-local sources / authorisation (see section below) | P1 (was) |
| DQ-39: **25 of 986 stored control values are not derivable from their own quoted `source_text`.** Four Waverley deep-soil rows store 10%/15% against a quote that says 50%; three Cumberland setbacks store 4.0/5.5/8.0 m against a quote whose only figure is "Minimum 6m"; two rows store a number while their own quote says "needs PDF verification". Now gated for all 1,069 rows. | ✅ Fixed 2026-09-14 — no SERVED number carries a derivability flag. The probe had counted 20 held-back rows (never shown) and 18 DQ-40 re-file notes; corrected to served rows and real flags = **0**. The 20 held-back rows remain candidates for a source check | P1 — the number IS the product |
| DQ-36: Provisions PDF hardcoded "Transport Oriented Development: ✗ Not applicable — property not within 400m of metro station"; the component receives NO TOD data, so the claim was unconditional. Four further SEPPs asserted "✗ Not applicable" for a proposal the report never sees. | ✅ Fixed 2026-08-01 | P1 — false statement of site fact |
| DQ-35: conveyancing_db.fetch_dcp_setbacks cited rows[0] from the UNFILTERED list, so clause_ref could name a control the function had just suppressed (needs_review) or excluded as belonging to a DIFFERENT zone | ✅ Fixed 2026-08-01 | P1 — citation is the product claim |
| DQ-34: ContextSection.tsx PDF "Housing SEPP 2021: ✓ Applies" line was a zone-only check, contradicting this same file's own determineDevelopmentPathway() on heritage land | ✅ Fixed 2026-08-01 | P1 — liability language on a definitive claim |
| DQ-33: document_id naming mismatch (verbose vs slug) caused silent ALL/ALL applicability fallthrough across Marrickville/Ashfield/Leichhardt — 9,854 served rows, re-tagged 2026-08-01, `no_config` 9,854 → 1,278. ⚠ **REOPENED 2026-08-17 AT ITS TRUE SIZE — 6,759, and NOT a regression.** The 1,278 floor was measured while **10,103 served rows carried no source at all**, so the `no_config` population was only partly visible and the floor was computed on a fraction of it. Recovering provenance labelled 19,558 already-tagged rows and found **5,481 more that were always ALL-by-fallthrough** — they read ALL/ALL before and read ALL/ALL now; the phase writes only the two source columns and never touches a tag, which `tests/test_applicability_provenance.py` enforces against the UPDATE itself. **The floor stays at 1,278 rather than being raised to today's number** — raising a floor to match a measurement is how a ratchet stops meaning anything. The row is simply open until it comes down. **CLOSED 2026-09-21 at a floor of 1,158, LOWERED from 1,278.** Leichhardt held nine ingested documents with no config entry — Part C Sections 3/4/5, Appendices B/D/E, the Tree Management Technical Manual, Amendments 1 and 7 — 871 served rows applying to every development type because nothing matched. Six of the nine matched no regex branch in the tagger at all, so no config could have reached them. Declaring their scope from their own provisions took council `no_config` 1,986 → 1,158. ⚠ **The floor was lowered, never raised** — the rule above is about raising, and leaving it at 1,278 would have let 120 rows of new breakage arrive while this still reported 0. ⚠ **1,158 rows remain wrong and the floor now hides them**: parramatta 341, canterbury_bankstown 216, marrickville 157, ashfield 118 and five smaller, each needing its unconfigured documents declared the same way. Lower the floor again each time one is done. | ✅ Fixed 2026-09-21 at floor 1,158 — `dq_probe_live.py --id DQ-33` = **0** | P1 — silent fallthrough class |
| DQ-32: Several correct control values share one `(lga, dev_type, control_type)` slot. **RULING 2026-08-13 (user): SHOW THEM ALL, each with its condition.** ⚠ **The 'engine picks one arbitrarily' framing was WRONG and cost re-derivation twice — check the SURFACE before planning any further work here.** Traced every served path: `fetch_dcp_setbacks` already returns every row; `/api/capacity/calculate` `setbacks` already attaches `condition`; `DcpStructuredControls.tsx` (the main UI) already renders a condition column. The real defects were narrower and are **FIXED 2026-08-13**: (1) `DcpSnapshotCard.tsx` declared no `condition` field so the API's value was dropped — four correct Sutherland parking rates rendered as four identical 'Car parking' rows holding 1 / 1.5 / 2 / 0.25 with nothing saying which applied; (2) its React key was `control_type-section_ref`, which those rows **share**, so React collapsed them and drew ONE; (3) `.slice(0, 6)` truncated silently; (4) the card asserted the numbers 'apply to any residential building on this block', false for a row gated on bedroom count; (5) `/api/capacity/calculate` `parking` and `landscaping` stripped `notes` while `setbacks` kept it. ⚠ **Those two capacity fields are consumed by NO UI** (`LepCapacityData` is rendered nowhere) — fixed for shape-consistency, not because a user sees them. **556 of 562 rows already carry their discriminator** (bedrooms 220 · visitor/resident 121 · lot size 108 · locality 95 · zone 56 · storeys 55); only **6** have none. Guarded by `__tests__/components/dcp-snapshot-card-conditions.test.tsx` — 4 of its 5 assertions fail against the old component. | ✅ **Fixed 2026-08-13 (present-all).** 6 rows with no condition at all remain — they need a source lookup, tracked separately. | P1 |
| DQ-32c: **6 served controls share a control slot with a different value while stating NO condition at all** (ids 10, 257, 259, 799, 2, 6 — ashfield, campbelltown x2, fairfield, marrickville x2). Under the present-all ruling several values for one slot is correct *provided each states its case*; these six state nothing, so no UI however correct can attribute them. Split from DQ-32 because the fix is different in kind: presentation was the fixable half and is done, these need a **source lookup per row**. Measured against **556 rows in the same groups that DO carry their condition** — this is 6 rows, not 562. | ✅ Fixed 2026-09-14 — ids 10, 257, 259, 799 given the case their own quoted sentence names ("houses", "each dwelling", "each multi dwelling housing unit", "per dwelling"); ids 2 and 6 had already left the served set. `dq_probe_live.py --id DQ-32c` = **0** | P2 |
| DQ-84: **A served control stores a number its own `source_text` attaches to a DIFFERENT subject.** The existing gate `validate_control_source_values.py` PASSES every one of these - it asks whether the digits are derivable from the quote, never what they are about. Found by hand, all filed as setbacks of the dwelling: a **driveway** setback (fairfield id=712, 0.5 m - **smaller than the 0.9 m real side setback in the same slot**, so following it under-sets-back the building), a duplex **minimum site frontage** (burwood id=704, 15 m, would sterilise the lot), a **facade-to-facade separation** (camden id=695, 12 m), **front fencing** (camden id=693) and a **bin hardstand** (camden id=696, 3 m). ⚠ **The first version of the rule was wrong and that is why it is positional**: "a foreign word appears near the number" flagged 8 rows of which the **4 SERVED ones were all correct** - marrickville reads *"must be 4 metres where there is no driveway"*, where the driveway is the CONDITION, not the subject. The rule now requires the foreign noun to **govern** the number with no conditional word between them, either direction, plus a whole-quote rule for the bin list whose giveaway words sit in sibling list items. Measured over 268 checkable rows: **5 of 6 known-bad recovered, 0 false positives, 0 of 4 known-good flagged.** NOT claimed: id=702 files a corner-lot side setback under `front_setback` - a front-vs-side confusion, a different class, and stretching the rule to reach it is how the noise returns. Guarded by `scripts/check_control_subject_mismatch.py` + `tests/test_control_subject_mismatch.py` (15 tests; the driveway sentences appear on BOTH sides, so a rule that cannot separate them fails). | ✅ **Fixed 2026-08-17 - 1 → 0 served.** `scripts/fixes/dq84_exclude_misfiled_controls.py`, backup `dcp_setback_controls_dq32c_backup_20260817`. id=696 excluded, so camden secondary-dwelling front setback is now ABSENT rather than a bin number - absent is the honest state. id=698 gained *"or the Prevailing Street Setback, whichever is the greater"*; serving the bare 4.5 m **understated** the requirement. Verified by reading the served state back, not by trusting rowcounts. `--all-rows` still shows 4, all already excluded. | P1 |
| DQ-32b: **76 served controls named a zone in their `condition` text while carrying a non-`zone_specific` `applicability`**, so the zone filter at `scripts/conveyancing_db.py:413` — gated on that field — never examined them. **Repaired 2026-08-12: 59 tagged `zone_specific`** (backup `dcp_setback_controls_dq32b_backup_20260812`). ⚠ **The other 17 must NOT be tagged, and finding that out was the whole job**: the filter is *skip-only*, so a wrong tag can only ever DELETE a correct control. 8 canada_bay rows read `within 800m station or 400m B3/B4` — **proximity to a zone, not membership in one**; 7 are clause/table references the regex mistook for zone codes (`(C1.1.9(e))`, `Table C2.2`, `(B3.8 s3.8.2 C1)`); 1 is a road classification (`major road frontage (C1)`); 1 carries an explicit fallback (`otherwise prevailing`) that tagging would drop outside R3; 1 uses the zone for a **sub-case only**, so the general 60% would be lost outside E4. They are excluded **by id**, not by loosening the regex, so a NEW untagged zone-naming row still fails the check. Verified against served output: Penrith `dwelling_house` landscaping went from 4 values in every zone to **R2→50% only, R4→35% only**. | ✅ **Fixed 2026-08-12 — 76 → 0.** | P1 |
| DQ-31: housing-sepp/eligibility over-eligibility — absent `isLMRArea` meant "yes"; the AI router additionally hardcoded `isLMRArea: true` and invented `zone`/`lotSize`/`lotWidth`. **Over-eligibility CLOSED 2026-08-01; full consolidation onto the Python service still open.** | 🟠 Wrong answer fixed, consolidation open | P1 |
| DQ-30: Applicability tagger — CODE fixed (PR1-4, this PR). **DATA NOT fixed: 286 rows still carry retired zone codes, 14 of them live+actionable in councils the retag covered.** The "0% drift" verification was invalid — it cannot fail. | ✅ **Data FIXED 2026-08-12 — 3 served rows → 0.** Lossless by construction: every one already carried the modern equivalent (E1/E2/MU1) beside the retired B-code, and nothing is zoned B1–B8 any more, so the removed entries could never match a current-zone lookup. Backup `regulatory_provisions_dq30_backup_20260812` (86 rows incl. superseded). **86 superseded rows still carry retired codes and were deliberately NOT touched — they are history, not served.** | P1 — validity, not traffic |
| DQ-29: Doubled-character OCR corruption in provision_text — 845 header lines stripped (backup saved); 22 scrambled-body rows remain for re-extraction | 🟡 Partially fixed 2026-07-15 | P1 |
| DQ-28: Ashfield chapter_e2_haberfield TOC — catch-all entry only, no section-level TOC extracted | ✅ Fixed 2026-03-30 | P2 (was) |
| DQ-24: **Transport & Infrastructure SEPP `v2_topic` retag — SCOPED 2026-08-14, it was never measured.** **523 of 1,076 SERVED provisions** from this SEPP carry no `v2_topic`, across its two document rows. Scoped to the served set on purpose: 1,248 more non-actionable rows are untagged but nobody sees them. ⚠ The document pattern needs BOTH words — `%Transport%` alone also matches `Penrith_DCP_2014__c10_transport_access_parking`. ⚠ **Not Transport-only**: the same query without the document filter returns **3,197**, a bigger row to open separately. | 🟠 Open — `dq_probe_live.py --id DQ-24` = 523 | P3 |
| DQ-25: **Transport & Infrastructure `sepp_structured_requirements` empty — STALE, it was not empty.** Joining `provision_id → regulatory_provisions.document_id` gives **110 rows** for this SEPP (69 + 41 across its two document rows), the largest holding after Exempt and Complying Development. **553 of the table's 560 rows carry a NULL `sepp_name`**, so a naive `GROUP BY sepp_name` shows nothing for Transport — which is what made this row look true. Nothing was built to close it; it had already stopped being true and no check existed to notice. | ✅ Closed 2026-08-14 on measurement | P2 |
| DQ-26: Marrickville truncated pdf_page_image_url stems | ✅ Fixed 2026-03-04 | P1 (was) |
| DQ-27: Marrickville LaTeX math artefacts in provision_text | ✅ Fixed 2026-03-04 | P1 (was) |
| DQ-1: Precinct CDC=0 | ✅ Not a bug | N/A |
| DQ-2: Topic misclassification | ✅ Fixed | P1 (was) |
| DQ-3: Headers in provisions | ✅ Fixed | P2 (was) |
| DQ-4: v2_marker NULL | ✅ Accepted | P3 |
| DQ-5: Generic layer 78% | ✅ Expected | P3 |
| DQ-6: Duplicates (2%) | ✅ Accepted | P3 |
| DQ-7: Dev-type coverage | ✅ Fixed | P0 (was) |
| DQ-8: DCP-ONLY scope | ✅ Documented | P1 |
| DQ-9: DCP filter bug (IWLEP) | ✅ FIXED | P1 |
| DQ-10: Council-specific UI/UX | ✅ DOCUMENTED | P1 |
| DQ-11: Heritage sub-categorization | ✅ COMPLETE | P2 (was) |
| DQ-13: Leichhardt uncategorized topics | ✅ FIXED | P1 (was) |
| DQ-14: Leichhardt PDF URL coverage | ✅ FIXED | P1 (was) |
| DQ-15: Topic case inconsistency | ✅ FIXED | P2 (was) |
| DQ-16: Heritage topic fragmentation | ✅ FIXED | P1 (was) |
| DQ-17: "Orphaned" non-heritage provisions | ✅ NOT ORPHANED | N/A |
| DQ-18: Marrickville pdf_page mismatch | ✅ FIXED | P1 (was) |
| DQ-19: Part 9 pattern collision | ✅ FIXED | P1 (was) |
| DQ-20: Part 5/6 vs Part 9 precedence | ✅ FIXED | P2 (was) |
| DQ-21: Double-underscore doc_id patterns | ✅ FIXED | P2 (was) |
| DQ-22: TOC provisions marked actionable | ✅ FIXED | P1 (was) |
| DQ-23: Duplicate provisions in TOC view | ✅ FIXED | P1 (was) |

---

## DQ-34: PDF "Housing SEPP 2021: ✓ Applies" line is an ungated definitive claim

**Status:** 🔍 Logged 2026-08-01, not sized — found via a Sol cross-review of the DQ-30 branch,
verified against the code, deliberately not fixed here (out of scope for a zone-taxonomy
consolidation PR).
**Found:** 2026-08-01

**Problem:** `frontend-nextjs/components/pdf/ContextSection.tsx` has two separate pieces of
Housing SEPP eligibility logic in the same file. `determineDevelopmentPathway()` (used for the
main pathway determination) correctly checks `heritage_status` first and returns a hedged reason
("CDC pathway available for eligible development"). But a second, separate JSX block rendering
the "Housing SEPP 2021" table row (around line 304) only checks `HOUSING_SEPP_ZONES.includes(zoneCode)`
and prints an unconditional "✓ Applies — `<zone>` zone eligible for complying development (CDC)
pathway" with no heritage, dev-type, or lot-size gating at all.

**Confirmed pre-existing:** verified via `git diff main` that this PR only swapped the inline
zone-code literal for the shared `HOUSING_SEPP_ZONES` constant at this exact line — the
surrounding "✓ Applies" conditional and copy are unchanged, pre-dating DQ-30. Not introduced or
worsened by the zone-taxonomy consolidation.

**Risk:** a heritage-listed or otherwise CDC-ineligible property zoned E1/MU1 would show
"✓ Applies" in the generated PDF, which reads as a definitive eligibility claim despite zone
membership alone not establishing CDC eligibility — the class of issue
`.claude/rules/pre-pr-review.md`'s liability-language check exists to catch.

**Fix:** not started, not sized. Needs deciding whether to gate this specific display block on
the same heritage check `determineDevelopmentPathway()` already does, or reuse
`determineDevelopmentPathway()`'s result directly instead of re-deriving eligibility inline a
second time in the same file.

---

## DQ-40: control_type contradicts its own quote (2026-08-03) — CLOSED with 3 open rows

**Status:** 🟢 Fixed 2026-08-03. Detector: `scripts/measure_control_type_mismatch.py`
(v2 — matches boundary wording, the v1 blind spot that hid canada_bay 701).

**What was done (all against source PDFs in `data/dcps/`, evidence STRONG):**
- **canada_bay 701** — served rear 1.5m was the second-storey SIDE setback (C6 table,
  400-char truncated quote); corrected to **6.0m per C9 printed p.E-15**, quote replaced
  in the same write (rule 2b). `scripts/repair_canada_bay_rear_setback.py`; backup
  `dcp_setback_controls_cb701_repair_20260803`.
- **20 rows re-filed** `front_setback` → `secondary_street_setback` (migration 054 +
  `scripts/refile_secondary_street_setbacks.py`, applied 2026-08-02; backup
  `dcp_setback_controls_refile_backup_20260803`). Vocabulary synced 2026-08-03 across
  `enforce_control_type_vocabulary.sql`, `enrichment/config/control_type_vocabulary.py`,
  the structured-controls TS maps and SEE CATEGORY_MAP (served rows previously rendered
  under "Other" with a raw slug).
- **MISSING_PRIMARY adjudication** (`scripts/repair_missing_primary_controls.py`; backup
  `dcp_setback_controls_missing_primary_20260803`): ryde front 6.0m ADDED (id 1175,
  s2.9.1(a) p.25 — was stored NOWHERE); ryde 680 re-filed front→rear (its quote is
  s2.9.3(a), 8m floor of a greater-of rule) and 681 conditioned as the s2.9.3(b)
  exception; burwood side 0.9–1.5m ADDED (id 1176, Ch4 s4.5 Table 3 p.221) and 707
  conditioned as the P10 garage-wall rule; camden 691 re-quoted to Table 4-2 side 0.9m;
  fairfield 715 re-quoted to 5B.2.3.1(a) and **714 RETIRED** (its 6m is a Chapter 5C
  narrow-lot garage setback; 5B prescribes NO numeric front setback for secondary
  dwellings — camden-692 model); fairfield 716 and ryde 682 flagged `needs_review`
  (fail closed) — see open items.
- **Truncation escape closed (Sol's case):** `evidence_is_truncated` no longer exempts a
  400-char quote ending in punctuation — a cut can land after punctuation, and at the
  extractor cap a complete quote is indistinguishable from a severed one. All 21
  at-limit rows ended mid-word, so no verdict changed; the hole is closed for the next
  extraction.
- Detector heuristics: NARROWING terms inherent to a control type no longer flag it
  (car_parking↔garage, secondary_street_setback↔corner); settled false positives are
  suppressed with per-row reasons (KNOWN_FALSE_POSITIVES).

**After state (2026-08-03):** category A = **3 open** (was 28/26 served), category B =
**0** (was 6), truncated = 19. Value checker green, baseline 41 → 38 (shrink-only).

**Open rows (A):**
- **884 city_of_sydney** — clause 4.1.2 contains no numbers; stored 0m encodes an
  observed pattern. Fix (NULL + qualitative) adjudicated but not authorised; also
  provisional against the Jan-2026 amendment.
- **570 georges_river** — front 5.5m garage/carport clause; source PDF not local,
  UNVERIFIABLE this pass.
- **895 marrickville** — side/rear one-clause shape, likely correct (577/109/105
  pattern) but source not read; open until it is.

**Held fail-closed — APPLIED 2026-08-03 (authorised):** both repairs executed via
`scripts/repair_authorized_held_rows.py` (backup
`dcp_setback_controls_authorized_repairs_20260803`, all-or-nothing, rule 2b):
- **fairfield 716** — rear 6.0m (Chapter 5C narrow-lot first-floor value) →
  **0.9m per 5B.2.3.1(a)**, quote replaced in the same write, needs_review cleared.
- **ryde 682** — side 4.0m (design-preference quote) → **0.9–1.5m per
  s2.9.2(a)/(b)** (900mm one storey / 1.5m two storey, range-row per burwood
  1080/1176), needs_review cleared. Baseline 38 → 37 (682 left TRUNCATED_EVIDENCE).

**Extraction gaps found while ruling (ADD candidates, STRONG sources local, NOT done —
new extraction was out of scope):** ryde side 0.9/1.5 (s2.9.2) + secondary street 2m
(s2.9.1(b)); camden secondary street 2m + front tiers 6.5m/10m (Table 4-2); fairfield
corner secondary street 1.5m (5B.2.3.1(c)); burwood two-storey front 9m (Table 3);
cumberland secondary-dwelling rear 0.9/3m and side 0.9/1.5m per the Table quoted by row
34 (row 35's 1.2m side carries a basement quote — suspect).

---

## DQ-39: 25 control values their own quote does not support (2026-08-02)

**Status:** MEASURED + GATED for all 1,069 rows. Data NOT fixed — each row needs a
ruling against the source PDF, which is extraction work.

**What changed the coverage.** DQ-38 established that only 42 controls can be
checked against the provisions corpus, because 14 of 30 councils have no provisions
ingested. But every row already carries `source_text` — the sentence its number was
taken from. Checking a number against **its own quote** needs no corpus, no PDF and
no ingestion, so it covers **all 1,069 instead of 42.** That is a 25× increase in
what is machine-checkable, achieved by changing the question rather than the data.

**The flag was not the answer.** `value_absent_from_source` flags rows whose digits
do not appear in their quote. Re-measured live: **137 on `value_min`, 11 on
`value_max`, 142 distinct rows** (the remembered "137 table-wide" was `value_min`
only). Reading a sample showed most were legitimate derivations — "900mm" stored as
0.9, "one space per 3 dwellings" stored as 0.333. **A list of flags where most
entries are fine is a list people stop reading**, and that is how a real mismatch
survives inside it.

So each derivation is now a NAMED rule that must produce the substring it matched.
Every row lands in exactly one state (`scripts/validate_control_source_values.py`):

| state | rows | |
|---|---|---|
| `exact_digit_match` | 839 | the number is literally in the quote |
| `ratio_or_rate` | 88 | "1 space per 4 dwellings" → 0.25 |
| `unit_conversion` | 19 | "900mm" → 0.9 m |
| `area_from_dimensions` | 5 | "3m x 3m" → 9 |
| `written_numeral` | 4 | "one car space" → 1 |
| `fraction_literal` | 2 | "min 1/3" → 0.333 |
| `implied_single_unit_rate` | 2 | "a space for every 4 dwellings" → 0.25 |
| `explicit_nil_requirement` | 1 | "no additional parking is required" → 0 |
| `built_to_boundary_zero` | 1 | "may be built to the rear boundary" → 0 |
| `percentage_phrasing` | 0 | reachable, but every real row hits the exact rule first |
| **`UNEXPLAINED`** | **25** | **the finding** |
| `no_value_stored` | 83 | a rule with no number — counted separately, NOT a pass |

**961 of the 986 rows carrying a number (97.5%) are derivable from their own quote.**

### The 25, grouped by what is actually wrong

> **ADJUDICATED 2026-08-03 against source PDFs — group A below was WRONG.**
> Full evidence: `docs/qa/controls-adjudication-2026-08.md`. Verdicts on all 25:
> **12 CORRECT, 8 EXTRACTION_ERROR, 3 NO_NUMERIC_CONTROL_IN_SOURCE, 2 UNVERIFIABLE.**
> Every one of the 11 rows whose source had to be fetched proved CORRECT.

**A. RETRACTED — the four Waverley rows are CORRECT.**
Waverley `deep_soil_min` 631/632 (10%) and 635/636 (15%) are right. The control is
a **two-clause derivation** and `source_text` stored only the second clause:
C1.9(c) *"minimum of **20%** of the total site area … as landscaped area"* ×
C1.9(d) *"minimum **50%** of the landscaped area must be deep soil"* = **10% of
site**; C2.9(b) **30%** × C2.9(c) **50%** = **15%**. Verified verbatim at pages 204
and 233 of WDCP 2022 (v1.1-2026-03-16). Calling these the most serious finding was
an assertion from a partial quote — the same error this workstream keeps repeating.

Of the Cumberland three, only two are errors, and **30 is CORRECT**: Table 1 p.B8
reads *"Rear Setback — Minimum 8m"*. It was flagged because all four Cumberland
rows share a `source_text` truncated at exactly **400 characters**, severing the
rear/corner/secondary rows of the table. **31** (4.0 m) is the *Secondary Frontage*
setback and **32** (5.5 m) is the *garage* setback, both stored as `front_setback`;
both are already `is_current=FALSE`.

**B. The quote is an admission that the value is unverified — 2 rows.**
- **1119** Cumberland POS stores 24 m² with `source_text` = *"...(needs PDF
  verification for numeric values)"*; **1120** Campbelltown POS stores 24 m² with
  *"(needs PDF verification — garbled extraction)"*. Note `fabricated_values`
  should catch this shape and does not: its marker pattern has "to be verified"
  but not "needs PDF verification".

**C. The quote is about a different control — 2 rows.**
- **693** Camden `front_setback` 2.0 m quoted from a clause about **front fence
  height** (1.2 m). This row also exposed the check's own worst false-pass: it
  was briefly "explained" by the `2` of a numbered list item, until numbered-list
  ordinals were excluded from quantity matching.
- **255** Campbelltown `car_parking` 2 spaces quoted from a clause about a
  **36 m² undercover parking area**.

**D. The quote is qualitative and the number is an assumption — 11 rows.**
690, 692 (Camden — "average setback of the 2 nearest dwelling houses"), 3
(Ku-ring-gai objectives text), 883, 884, 885 (City of Sydney — "consistent with the
Building setbacks map", heritage character), 606 (Sutherland — "determined by either
a specified minimum distance or the average"), 13 (Woollahra — envelope defined by a
Figure), 1, 2, 6 (Marrickville — garbled OCR objectives text with no numbers in it;
DQ-29 territory).

**E. A correct value whose derivation is deliberately not machine-named — 3 rows.**
- **229** Georges River: *"1 garage space and 1 driveway space per dwelling"* → 2.
  Plainly right, but a rule that summed arbitrary numbers from a quote could
  "explain" almost any value, so it stays a finding rather than getting a rule.
- **778** Ryde: *"Up to 2 spaces per dwelling house"* → max 2 is quoted, **min 1 is
  not**. **517** Marrickville stores 0 against *"1 per principal dwelling and
  secondary dwelling combined"* and belongs in group A on a re-read.

### How strong is an exact match, really?
**571 of the 839 exact matches (68.1%) sit in a quote that holds more than one
distinct quantity.** The stored value appears in its source — but so do others, so
the match is *consistent*, not *pinned*. Only 268 are uniquely attributable. That
split is now printed, because `exact_digit_match` otherwise reads as stronger
evidence than a number-matching check can give. Closing it properly means reading
clauses rather than matching numbers, which is a different tool.

Five further holes found in adversarial review and closed:
- a value stored with **no source_text at all** returned `no_value_stored` and
  passed as "nothing to check". It is now `MISSING_SOURCE_TEXT`, a failing state.
  0 rows are in it today — which is exactly why it needed one.
- the gate blocked on superseded rows. Only `is_current` rows can fail now (19 of
  the 25); the 6 superseded are reported, never silently dropped. The test is
  `is False`, not falsy, so a future nullable column fails closed.
- **the rounding tolerance was wrong in both directions.** A flat 0.005 let a
  stored 0.005 pass against a quoted "1 space per 1000 dwellings" (0.001) — five
  times too large. Tightening it to 0.0005 then rejected two honest rows, because
  the table stores 2/3 as **0.67** and 1/3 as both **0.33** and **0.333**. The
  tolerance now comes from the stored value's own precision (half its last decimal
  place) AND a 5% relative bound, so a whole number cannot absorb a large gap.
- `area_from_dimensions` ignored the unit, so "3m x 3m" could explain a 9 in a
  `spaces/dwelling` column. Now gated on an area unit.
- `written_numeral` matched "one" anywhere, so *"Objective one: provide a minimum
  6m front setback"* explained a stored 1 m setback. The numeral must now be
  counting something within two words.
- the rate rule offered **every** number before a "per" as a numerator, so
  *"Minimum setback 6m and provide 1 space per 4 dwellings"* could explain a
  stored 1.5 as 6/4 — a rate assembled from two unrelated clauses. Only the
  nearest number can be a numerator now.
- `percentage_phrasing` also accepted `pct * 100`, so a quoted 35% explained a
  stored 3500. Nobody stores a percentage that way; that direction existed only to
  manufacture matches, and is gone.
- **the baseline was never made to shrink.** A repaired row stayed accepted
  forever, so restoring its old value later would not have failed. A baseline
  entry that is now explained is a **failure** with the one command to fix it —
  and `--write-baseline` refuses to ADD ids without `--allow-growth`, so the
  remedy cannot double as the bypass.
- **the baseline was keyed on `id` alone**, so a baselined control could have its
  value swapped for a *different* unsupported number, or lose its quote entirely,
  and stay accepted. It now stores `id -> digest(value_min, value_max, unit,
  source_text)`, so any change to what the check reads makes the row new again.
- `unit_conversion` accepted both directions, so a quoted "0.9mm" explained a
  stored 900 m. One direction only now.
- a matched quantity whose text says it measures something else explained a value
  anyway — *"a minimum of 3 hours of sunlight"* explained a **3 metre** setback.
  A trailing unit in a different family (length / area / ratio / time / count /
  rate) now disqualifies the match, and only when BOTH sides are known, so an
  unlabelled number is never rejected on a guess.
- **the unit guard existed in one rule and its stored-unit map covered 6 strings.**
  `spaces/dwelling` and its eight siblings — **450+ rows, the largest unit group in
  the table** — fell outside it, so those rows were treated as "unknown unit" and
  the guard never fired for them. The map now resolves by prefix (`%…` → ratio,
  `spaces/…` → rate), and the guard is applied in `written_numeral` too, not only
  in exact matching. `percentage_phrasing` is gated on a ratio column (a quoted
  35% was explaining a 0.35 **metre** setback) and `unit_conversion` on a length
  column (it also accepted `m2` and unlabelled columns).
- the lead-in to a rate was cut on any `.`, **which split decimals**:
  *"0.5 spaces per 4 dwellings"* left `5 spaces` and produced 5/4, so a stored
  1.25 passed against a quote stating 0.125. The cut now ignores a full stop
  between two digits.

- a **whole-number** stored value got half-a-unit of slack, so *"24 spaces per 25
  dwellings"* (0.96) explained a stored **1**. Rounding a rate to a whole number is
  a judgement, not a derivation the text states; whole numbers must now match
  exactly. All five whole-number derived rows are exact products, so this cost
  nothing.
- the rate rules had **no column gate**, so *"1 visitor space per 4 dwellings"*
  could explain a stored 0.25 **metre** setback on a row whose `source_text` was
  attached to the wrong control. Refused on length, area and time columns.
- a **NaN** stored value read as explained. Postgres `numeric` accepts NaN and
  every comparison against it is False, so the exact rule's own "skip if not
  equal" test was False and the row fell through into a match. NaN and infinity
  are now findings.

- a clause label with a **space** was still a quantity: the number-token guard
  only caught a label glued on (`s4.3.6`), so *"Clause 4.3: minimum setback is
  6m"* explained a stored **4.3** — the citation vouching for the value it is
  supposed to be evidence against. Clause/Part/Table/Control/Figure/Objective and
  eleven more labels are now excluded.
- `written_numeral`'s unit guard read the position straight after the numeral, so
  *"three **full** hours"* put a word where the unit scan looked and the conflict
  went undetected. It now reads the noun the rule itself matched.
- `implied_single_unit_rate` invented its numerator: *"Visitor parking must be
  considered for every 4 dwellings"* became 1/4 although the quote states no
  quantity. The implied "one" must now be written as something ("**a** parking
  **space** for every 4 dwellings").
- `fraction_literal` had no column gate, so *"At least 1/3 of the landscaped
  area"* could explain a stored 0.333 **metre** setback. Same gate as the rates.
- a row whose value is **NULLed by a migration** moved into `no_value_stored` and
  passed as "nothing to check". The check cannot tell an intentional blank from a
  lost one, so the count is now ratcheted in the baseline (83) and a rise fails.

None of these eighteen changed the finding count — it stayed at 25 throughout —
which is the point: they closed paths by which a *future* wrong value would have
passed, not paths that were hiding current ones. Two were measured against live
data before being applied, to confirm they cost no legitimate row: whole-number
exactness affects 5 rows and all 5 are exact products, and the rate column gate
affects 0 of the 90 rate-explained rows.

**Where the hardening stopped, and why.** Seven rounds of adversarial review each
returned real findings, and the count of *data* findings did not move after the
first. That is the signal to stop: the remaining suggestions harden a check that
no longer changes its answer. One was declined outright — failing every exact
match that sits in a multi-quantity quote would put 571 of 839 rows in the finding
list, which is a re-statement of the method's ceiling rather than a defect list.
Closing that genuinely means reading clauses instead of matching numbers.

### Why this check can fail
Two ways: a NEW unexplained row fails against the baseline, and a value edited to
something its quote does not support becomes unexplained on the next run.
**Demonstrated firing** — three ids removed from the baseline produced
`NEW (not in the baseline): 3` and exit 1. The baseline is shrink-only.

Mutation-checked, because a rule that always explained would make this a check that
cannot fail: forcing the tolerance to always match, replacing exact matching with a
substring test, and letting the implied-rate rule ignore a written numerator were
all **killed by the tests**.

### What it does NOT prove
That the number is correct — only that it is consistent with the sentence stored
beside it. If the quote itself was mis-transcribed, both agree and this passes.
That failure mode belongs to the extraction gates.

### Named false-explanation traps the rules refuse
- a numbered-list ordinal explaining a value (this one was live: it hid Camden 693)
- a clause reference explaining a value (`s4.3.6` must not explain a stored 4.3)
- a bare number read as millimetres, or divided by 100 to reach a percentage
- `2 spaces per 5 dwellings` stored as 0.2 being "explained" as 1/5
- City of Sydney's *"where no front setback is shown on the map"* explaining a
  stored 0 — the map being silent is not a control of zero

Two of those were not hypothetical. Excluding clause references cost 5 rows their
explanation and excluding list ordinals cost 1 more — six rows that had been
reading as verified on the strength of a citation or a bullet number.

**Wired:** pre-push `[1f/5]` and CI (`gates.yml`, schema-contract job — the one with
live DB access). Exit 2 on no `DATABASE_URL` is a skip, never a pass.

---

## DQ-38: only 42 of 1,069 controls can be machine-checked against the corpus (2026-08-02)

**Status:** 42 links live. Ceiling reported, not chased. **Heading and cause corrected
2026-08-02** — the original title asserted a single cause ("the corpus lacks their
chapters") that is measurably false for most of the affected rows. See *Why the other
545 do not match* below.

**What it is.** DQ-37 left 535 controls in state `traceable` — a human can re-check
them against a clause reference. Linking each to `regulatory_provisions.provision_id`
would make that a machine's job. Measured across all 1,069 controls:

| outcome | rows |
|---|---|
| exactly one CURRENT provision contains the control's quote | **41** |
| multiple provisions match (ambiguous) | 2 |
| no provision contains the quote | 545 |
| **council has NO provisions in the corpus at all** | **450** |
| quote under 30 chars, not distinctive | 31 |

**Restricting candidates to current, actionable provisions IMPROVED the result.**
It removes superseded duplicates of the same clause, so ambiguity fell 23 -> 2 and
linkable rose 35 -> 41. Filtering for correctness made the numbers better, not
worse. It also caught a live defect: the first run had written **3 links to a
superseded Marrickville provision** (controls 1, 2, 6 -> provision 102098,
`is_current=False`). Those are now cleared to NULL — pointing a future automated
check at withdrawn text is worse than admitting there is no link.

**The finding is the ceiling, not the 41.** 14 of 30 control LGAs have zero
provisions ingested — Canterbury-Bankstown (68 controls), Canada Bay (40), Bayside
(38), Fairfield (33), Wingecarribee (32), Sutherland Shire (32), Randwick (28),
Liverpool (27), Burwood (27), Strathfield (25), The Hills (23), Ryde (23), Camden
(23), plus `nsw_statewide` (31). **That 450 figure was measured directly and stands.**

### Why the other 545 do not match — CORRECTED, and still partly unknown

The first version of this entry said those 545 "belong to councils that ARE in the
corpus but whose specific chapter was never ingested." **That is false for most of
them**, and it was asserted rather than measured. Marrickville has 8,413 provisions
loaded, Ashfield 7,429, Woollahra 6,546; the chapters are there and the quotes still
do not match. Measured 2026-08-02 by `scripts/measure_control_quote_gap.py`:

| test | result |
|---|---|
| a provision document exists for the control's own `source_chapter_key` | **339 / 545 (62.2%)** |
| no ingested document for that chapter — original explanation holds | 206 / 545 (37.8%) |
| quote IS in the corpus, but only on a provision excluded by `is_current`/`v2_is_actionable` | 15 |

Of those 545, **498 are `is_current` and 47 are superseded control versions.** The
population is deliberately unfiltered so it reconciles with the linker, which also
reads all 1,069 — but note the linker links superseded controls too, which is
harmless and worth knowing.

Independently, by longest contiguous shared word-run against the best provision in
that council (a set-overlap score was tried first and discarded — a long provision
contains all the words of a short quote by chance, so it proved nothing):

| how much of the quote appears verbatim | rows |
|---|---|
| ≥80% — the sentence IS there; substring match failed on punctuation/OCR alone | 57 (10.5%) |
| 40–80% — partly verbatim | 119 (21.8%) |
| 20–40% — fragmentary | 236 (43.3%) |
| <20% — not present in any recognisable form | 133 (24.4%) |

**The cause is mixed, and for the majority it is UNKNOWN.** What is established:
"chapter not ingested" is disproven for 62% of these rows, and the 57 verbatim rows
prove both the chapter and the sentence are present — those fail on normalisation,
not coverage. What is NOT established: the low-overlap bands are equally consistent
with "someone summarised the clause in their own words" and with "that sentence is
absent from the ingested text", and this measurement cannot tell them apart. One
weak supporting signal for the paraphrase hypothesis: **61 of 545 (11.2%) source_texts
OPEN with a document citation** ("Ashfield DCP 2016 A-Part8 Table 2: ..."), which is
editorial framing a sentence inside a PDF would not contain. That is 11%, not a
cause for the other 89%. **Do not write a cause into this entry without measuring it.**

Two named limits of the chapter test, so its 62.2% is not over-read: it compares
identifier token-sets (`chapter-f-dev-category` vs
`Inner_West_Ashfield_DCP_2016__chapter_f_dev_category`) after stripping council/year
noise, so a chapter whose key diverges by more than separators reads as "not ingested"
when it is present, and two chapters sharing a token-set could read as ingested when
the wrong one is. `section_ref` was tried as the test first and abandoned: **0 of 530**
control `section_ref` values exist as a `ref_number` in their council, because the two
columns use unrelated vocabularies ('chapter-f-dev-category/DS5.2' vs a clause number)
— that 0 measures the vocabulary gap, not the corpus.

Closing the 206-row coverage half is extraction work, out of scope per
`docs/EXTRACTION_WHY_IT_RECURS_AND_THE_DURABLE_FIX_2026-07.md`. The 57 verbatim rows
are a normalisation fix and are worth doing. The rest needs a cause before it needs a fix.

**Why only exact single matches were written.** A wrong link is worse than no link:
it would let a later check compare a number against someone else's clause and report
a confident false verdict. Matching is substring containment on normalised text — no
similarity score, so no threshold to tune wrong. The 2 ambiguous and 545 unmatched
stay NULL.

**Caught during the dry run:** the plan would have OVERWRITTEN the one pre-existing
human-made link (control 3 -> provision 98149; the matcher resolves it to 97850).
The same clause exists as more than one provision row, so "exactly one substring
match" can legitimately land on a different duplicate than a person chose. Neither
is provably right, so `PRESERVE_EXISTING_LINKS` keeps the human's link and the
disagreement is counted. The UPDATE also carries `AND provision_id IS NULL` so a
stale plan cannot clobber a link written since.

**Two safety defects found in my own script before the final write:**
1. Staleness was only handled inside the `linkable` branch, so a stale link on a row
   that no longer matched anything current was silently RETAINED. All 3 live rows
   were in exactly that state. Staleness is now tested before the outcome branch.
2. `CREATE TABLE IF NOT EXISTS` reused the previous run's backup table, and the
   `count >= plan` check passed spuriously (34 >= 13) while covering none of the rows
   about to change. The guard now asserts every planned id is present in the backup,
   and it was demonstrated firing: "10 planned rows missing", abort before any UPDATE.

**Falsifiable check:** `python scripts/link_controls_to_provisions.py` (dry-run
default). Predicted before the final write: 13 rows written (10 new + 3 cleared),
0 skipped, 42 linked after. All matched. Post-write verification, **re-run against the
live DB 2026-08-02**: 42 links, 0 dangling (FK), 0 pointing at a superseded or
non-actionable provision, controls 1/2/6 confirmed NULL, and **41 of 42 quotes verified
present inside the linked provision text** — the one exception being control 3, whose
link a different method made. Note an earlier verification query reported 14/35 because
it compared un-normalised SQL text; re-run with the matcher's own normalisation it
passes. The check was wrong, not the links.

**Rollback:** `dcp_setback_controls_provlink_backup_20260802b` (13 rows, holding the
pre-run provision_id and is_current for every changed row), SQL printed by the
script. The earlier `...20260802` table (34 rows) restores the pre-any-change state.

**Re-runnable by design.** As councils are ingested, re-running links more rows with
no code change. `scripts/validate_controls_provenance.py` now reports link coverage
so the number is visible over time.

**Advisory, not a gate:** requiring a link would fail on absent corpus rather than
on a defect, so link coverage never affects an exit code.

---

## DQ-37: `extraction_method` is not a provenance signal (measured 2026-08-02, no data change)

**Status:** MEASURED + GATED. No production write — the states are derived, not stored.

**What it is.** `dcp_setback_controls.extraction_method` was being read as if it
recorded how a row was produced. It does not. Measured against the repo:

| claimed method | a committed script regenerates it | it does not |
|---|---|---|
| `text_extraction` | 187 | **253** |
| `mistral_ocr` | 170 | **77** |
| `manual` | **145** | 205 |
| `manual_curation` | **32** | 0 |

So 330 rows labelled pipeline-extracted have no committed literal, and 177 rows
labelled hand-made are regenerable from a tracked script. The label and the
reality are close to uncorrelated.

**Why it drifted.** `scripts/insert_inner_west_landscaping.py` stamps
`extraction_method: "text_extraction"` onto hand-typed dict literals, and
`scripts/update_needs_review_controls.py:226` overwrites the column outright.
Neither is wrong locally; together they make the column a claim rather than a fact.

**Consequence for the retrospective.** `ce-reliability-retrospective-and-asset-inventory-2026-08.md`
§5.5 read "382 of 1,069 (36%) unreproducible" off this column. Measured against the
repo the split is **534 reproducible / 535 not** — half the table, not 36%. The
number was worse than reported, and it was worse because the measurement trusted a
self-reported field. Same shape as DQ-30's "0% drift": a check that compared code
to itself.

**What was NOT concluded.** Absence of a committed literal does not prove a row is
unreproducible — a genuine PDF-extraction pipeline holds no hardcoded text. Proving
those 330 would mean re-running extraction over council PDFs, which
`docs/EXTRACTION_WHY_IT_RECURS_AND_THE_DURABLE_FIX_2026-07.md` exists to stop. So
the mismatch is reported as advisory and never as a failure.

**The three states, all derived from existing columns:**
`reproducible` 534 (verbatim literal in a committed writer) / `traceable` 535
(`source_text` + `section_ref`, so re-checkable) / `unverifiable` **0**.

**Falsifiable check:** `python scripts/validate_controls_provenance.py`
— exit 1 if any row is `unverifiable`, exit 2 if it could not run (nothing verified
is not a pass). Wired into pre-push `[1e/5]` and the CI `schema-contract` job.
Predicted 534 / 535 / 0 before running; actual matched exactly. Demonstrated failing
on a synthetic row with no provenance, and on an empty writer tree.

**No migration.** A stored status column was considered and rejected: it goes stale
the moment a writer changes, whereas a derived one cannot. `needs_review` was also
considered and rejected — it is already consumed by four production routes
(`dcp/structured-controls`, `capacity/calculate`, `tod/parking-rates`,
`internal/setback-review`) and repurposing it would change served output.

**Open, not chased:** `provision_id` is populated on 1 row of 1,069 — table-wide
dead, so no manual row is missing it relative to any other row. Linking controls to
`regulatory_provisions.id` would make state (b) machine-checkable rather than
human-checkable, and is the natural next step before §5.6 grows the table.

---

## DQ-33: Case-sensitive document-naming mismatch causes silent ALL/ALL applicability fallthrough

**Status:** 🔍 Logged 2026-08-01, not sized — found while finishing DQ-30 PR3. Scope
deliberately not investigated further yet; this entry exists so it isn't lost, not as a
completed diagnosis.
**Found:** 2026-08-01

**Problem (as currently understood):** the DCP config lookups in
`enrichment/extractors/applicability_tagger.py` match `document_id` against config part
keys using plain case-sensitive substring checks (e.g. `_get_leichhardt_config()`:
`part_pattern in document_id or part_key in doc`, where `part_pattern`/`part_key` come from
`LEICHHARDT_CONFIG['parts']`'s Title-Case keys like `"Part A"`, `"Part C Section 1"`). Some
document IDs use an older, verbose naming convention (matching this casing) and others use a
newer slug-style convention (different case), so the same substring match silently succeeds
for one naming generation and silently fails for the other — a failed match falls through to
the unconditional `{'applicable_zones': ['ALL'], 'applicable_dev_types': ['ALL']}` default at
the end of the method, with no error or warning.

**Confirmed so far:** 18+ Leichhardt rows exhibit this ALL/ALL fallthrough due to the naming
mismatch. **Not yet checked:** whether the same old-verbose/new-slug split exists for the
other 6 configured councils (Ashfield, Marrickville, Waverley, Woollahra, City of Sydney,
Ku-ring-gai) — each has its own `_get_<council>_config()` method with its own matching logic,
so the exposure needs confirming per-council, not assumed from the Leichhardt case.

**Relationship to DQ-30:** a distinct defect class — DQ-30 is wrong/stale *zone-code values*
(legacy vs current NSW zone taxonomy); this is a *document-matching* failure that produces the
same symptom (ALL/ALL, ungated applicability) via a completely different mechanism (naming
convention drift, not zone taxonomy drift). Found as a side effect of DQ-30 PR3 verification,
deliberately not folded into that fix.

**Fix:** not started, not sized. Needs: (1) confirming the exact old-verbose vs new-slug
naming conventions in play and where each originates (extraction pipeline vs onboarding
script), (2) scoping how many rows/councils are affected before deciding whether to
case-normalize the match, fix the naming convention at the source, or both.

---

## DQ-32: Capacity engine picks setback/landscaping numbers without checking zone

**Status:** Tracked 2026-07-31, not started — found while checking DQ-30 didn't miss the real engine
**Found:** 2026-07-31

**Plain version:** `getSetbacks()` in `app/api/capacity/calculate/route.ts` is given the
property's zone but never uses it in the `dcp_setback_controls` query — it only filters by
council + dev type. When a council has different numbers for different zones (e.g. Penrith
`multi_dwelling_housing` landscaping: R1=40%, R3=40%, R4=35%), the query can hand back the
wrong one. Checked the DB: **168 council/dev-type groups, 560 rows, where this can give a
wrong number** — not a display bug, a wrong feasibility number shown to a real user.

**Fix:** not started. Needs the query to filter/select by zone against the `condition` text
column (free text like "zone R4 High Density Residential" — no clean zone column exists),
designed and tested carefully since it changes what the capacity engine returns.

**Also found (2026-07-31, not investigated further yet):** the scripts that WRITE
`dcp_setback_controls` in the first place (`scripts/insert_*_parking.py`,
`insert_*_landscaping.py`, `dcp_extract_changed.py`, `ai_extractor.py`,
`generate_conveyancing_report.py`, `conveyancing_db.py`, `dcp_preflight.py` — one per
council onboarding) also hardcode zone-code lists, some with the same retired B1/B2/B4
codes. Found via `python scripts/lint_hardcoded_zone_codes.py --all` (PR4). Means the
zone-code problem may go all the way back to how this table's data was written, not just
how it's queried. Needs its own look — not sized yet.

---

## DQ-33: document_id naming mismatch (fixed + re-tagged 2026-08-01)

**The defect.** The Marrickville / Ashfield / Leichhardt matchers in
`applicability_tagger.py` were written for a verbose document_id convention
("Chapter E1", "4.1", "_4_1_"). Every document_id in production uses a slug:
`Marrickville_DCP_2011__part4_s1_low_density`, `..._chapter_e1_heritage`,
`..._part_c_s2_urban_character`. `_detect_council()` still matched, so the row looked
handled — but the PART never resolved and it fell through to ALL/ALL. 9,854 served rows
across 107 document_ids; 85 of 100 sampled recorded `no_config`.

**Why this one needed a higher bar than the 241-row zone repair.** It NARROWS. Showing an
irrelevant control is noise; hiding a binding one is the liability, and hiding a rule that
applies is the original DQ-30 harm. So: a slug resolves ONLY to a key the council's config
already declares; nothing is invented; anything unrecognised stays ALL with source
`no_config`. `chapter_e2_haberfield` (118 rows) and `part2_s21` (131 rows) deliberately do
NOT resolve — the configs declare no such key, and resolving to the nearest neighbour would
be a guess. Under-matching is a missed improvement; over-matching is a hidden control.

**Blast radius, measured BEFORE the write** (22,007 rows in scope):
- 1,928 rows change values; 20,079 change provenance only
- 815 served rows narrow on zones, 882 on dev types
- highest risk — narrowed to a SINGLE zone: 2 documents / 369 rows
  (`part4_s1_low_density` → R2, `part6_industrial` → E4; both verified against
  `lep_zone_coverage` for Inner West)

**Prediction stated before running, and the actual after:** `config_all` 7,761 ·
`config_specific` 815 · `no_config` 1,278 — matched exactly. Zero rows narrowed while still
recording `no_config` (which would have meant a guess). Every written zone code exists in
Inner West's live land-use table.

**Consumer.** `ProvisionsByTocStructure` told Leichhardt users "all N provisions apply
regardless of dev type — your selection … does not remove any". Correcting the tagger gave
Leichhardt Part F (food premises) real dev types, making that sentence false. The copy is now
derived from the data (`anyDevTypeSpecific`) so it cannot drift again. No count display or
empty-state breaks on a shrunken list, and no row holds an empty zone array (checked, not
assumed — an empty array would match no zone at all).

**Rollback:** `regulatory_provisions_dq33_backup_20260801` (22,007 rows, all four columns).
Script: `scripts/retag_applicability_slug_docids.py` (dry-run default, backup-before-write,
null-safe per-row guard, printed rollback SQL).

**Still open, deliberately:** the ~20% of served provisions that are not controls at all
(historical narrative, TOC fragments, LaTeX garble). Real, separate, and narrowing
applicability does not touch it.

---

## DQ-31: housing-sepp/eligibility route never migrated to the Python service

**Status:** ⏳ Tracked 2026-07-31, not started — found as a side-effect of DQ-30 PR3, deliberately not folded into it
**Found:** 2026-07-31

**Problem:** `services/housing_sepp_eligibility.py`'s own docstring states it was written
specifically to *replace* `frontend-nextjs/app/api/housing-sepp/eligibility/route.ts`'s
logic — computing `inLMRArea` and TOD catchment **authoritatively** from live gate/polygon
data, because the frontend route "defaulted [inLMRArea] to true — a silent over-eligibility
bug" and "used a mock hardcoded station list + Haversine" instead of the real TOD catchment.
The docstring frames this as done ("the two surfaces can no longer disagree"), but the
migration never actually happened: the TS route still runs its own independent eligibility
logic and does not call the Python service. `app/api/upzoning/route.ts` proxies to
`/pipeline/upzoning` (which internally calls `housing_sepp_eligibility.evaluate_eligibility()`)
for a *different* frontend surface (the upzoning-check tool, input = bare address); there is
no equivalent live endpoint for `housing-sepp/eligibility`'s exact request shape
(`{address, zone, lotSize, developmentType, lga?, coordinates?}` — pre-resolved inputs).

**Why not a drop-in proxy fix:** `evaluate_eligibility()` only returns the eligibility gate
result (list of `FormEligibility`) — it does not replicate the numeric-standards DB fetch the
TS route also performs. Migrating this properly means either a new backend endpoint that
wraps both, or a more surgical partial fix — not a mechanical swap like `/api/upzoning` was.
Live-route regression risk: `components/compliance/HousingSEPPEligibilityCard.tsx` (rendered
on the assessment page) depends on the current response shape.

**Fixed 2026-08-01 — the wrong ANSWER, not the duplication.** Full consolidation onto
`services/housing_sepp_eligibility.py` remains open (it returns only the gate result, not the
numeric-standards fetch the TS route also performs, so it is not a drop-in). What was closed:

1. `const inLMRArea = isLMRArea !== false` → an ABSENT input meant "yes, in an LMR area", the
   single input the endpoint turns on, resolved in the claimant's favour. Now three-state:
   true / false / not-assessed, with not-assessed yielding "cannot confirm" rather than
   eligible — matching the Python service's fail-conservative contract.
2. **`lib/ai/router.ts` was worse than the route.** It hardcoded `isLMRArea: true` and
   substituted `zone || 'R2'`, `lotSize || 450`, `lotWidth || 12` — inventing four site
   measurements to force an answer for a property whose real values were unknown. Missing
   inputs now stop the check.
3. A SECOND fabrication in the same file: `handleDcpProvisionLookup` used `zone || 'R2'`, so
   an unknown zone returned **R2's DCP provisions** presented as this property's. The zone
   param is now omitted (it is optional on `for-property`, route.ts:297).

**Still open after this fix (raised by cross-review, verified, deliberately not fixed here):**
the endpoint treats a caller-supplied `isLMRArea: true` as authoritative, but the live page
derives it from `isLMRApplicable(zone, lga)` — a zone/LGA heuristic, NOT the parcel-level 776
exclusion layer that `services/housing_sepp_eligibility.py` uses. A parcel individually excluded
from the reform area can therefore still be reported eligible. Fixing it properly IS the
consolidation described above, not a patch: the alternative — refusing to trust any client
boolean — would make the Housing SEPP card read "Not Assessed" for every property until the
server-side derivation is wired, which is a product decision, not a code cleanup.

Same class as DQ-36: a verdict asserted from data nobody supplied. Guarded by
`frontend-nextjs/__tests__/api/housing-sepp-lmr-default.test.ts` (6 tests, mutation-verified).

---

## DQ-35 / DQ-34 / DQ-36: wrong content in an exported PDF (fixed 2026-08-01)

**DQ-35 — a citation to a control the report deliberately hid.**
`scripts/conveyancing_db.py::fetch_dcp_setbacks` builds the rendered control lists by
skipping rows two ways: `needs_review` (a control flagged after a DCP amendment, suppressed
on purpose) and a `zone_specific` control whose `condition` names zones excluding this
property. It then set `clause_ref = rows[0][7]` — the RAW query's first row. So the single
clause reference a conveyancer reads could point at a suppressed control, or at one that
applies to a different zone entirely. Fixed to take the first clause from the rows that
survived; empty when nothing survived, because an invented reference is worse than none.

**DQ-34 — one PDF, two contradictory answers.**
`ContextSection.tsx` decided "Housing SEPP 2021: ✓ Applies — zone eligible for complying
development (CDC) pathway" from the ZONE ALONE, while `determineDevelopmentPathway()` in the
same file correctly checks heritage first and returns "Development Application (DA) — CDC and
exempt development not permitted". On heritage-listed land the exported PDF printed both, in
the same table. Now gated identically, and a zone match is reported as the zone test passing
rather than as an eligibility verdict on a proposal the report has never seen.

**DQ-36 — a site fact asserted without ever checking it.** (found while fixing DQ-34)
The same table hardcoded `Transport Oriented Development: ✗ Not applicable — Property not
within 400m of metro station or 800m of strategic centre`. The component is passed no TOD or
LMR catchment data at all, so no code path could ever print anything else: for any property
inside a catchment the PDF stated a falsehood about that site. Now reports "Not assessed in
this report" and points at the Portal TOD maps. Four further SEPPs (Design Quality,
Affordable Rental Housing, Seniors/Disability, Build-to-Rent) asserted "✗ Not applicable"
about proposals the report never sees; they now state their scope instead, which is the part
that is actually known.

Guarded by `tests/test_conveyancing_clause_citation.py` (7) and
`frontend-nextjs/__tests__/components/pdf-context-claims.test.ts` (8). Both mutation-verified:
restoring the old code fails them.

---

## DQ-30: Applicability tagger (v2_applicable_zones / v2_applicable_dev_types) drift + config gaps

**Status:** 🟠 **CODE fixed, DATA still open, 2026-08-01.** An earlier revision of this entry
said "✅ Fixed" on the strength of a "0% drift" check. **That verification was invalid and the
status was wrong — corrected here.**

PR1 (shared zone taxonomy source), PR2 (DCP tagger config fixes), PR3 (frontend/Python
consolidation) and PR4 (CI guard) are complete on branch `fix/zone-taxonomy-consolidation`
(PR #853, not yet merged). pytest 3223 + jest 917 green.

**Why the verification was invalid.** "0% drift" re-runs the tagger and compares its output to
the stored DB value. That is a *self-consistency* check: if the code still emits a retired zone
code, drift is 0% and the data is still wrong. **A check that cannot fail when the bug is
present is not a verification.** This entry's own text warned about exactly this trap for
Ashfield/Leichhardt/Marrickville ("0% drift does NOT mean correct") and the metric was used
anyway.

**Actual DB state, queried against production 2026-08-01** — `regulatory_provisions` still holds
**286 rows with retired B/IN zone codes**:

| Scope | Rows | Note |
|---|---|---|
| ku_ring_gai + woollahra, `is_current` AND `v2_is_actionable` | **14** | **Served today, in councils PR5 covered.** 13 are Ku-ring-gai local-centre provisions tagged `B2`/`B4` (St Ives, Turramurra, Pymble, Gordon) — the original DQ-30 symptom, still live |
| woollahra, superseded | 71 | Not served, still wrong |
| NULL `source_council` | 142 | Never in retag scope — invisible to it |
| 7 no-config councils | 51 | Known out of scope |
| `dcp_all_provisions.applicable_zones` | 32 | Separate table, never examined |

**The correct check, replacing drift:** every stored zone code must exist in `lep_zone_coverage`
for that LGA where `is_complete = TRUE`. Exact set membership against ground truth — no regex, no
false positives, and it *can* fail when the bug is present. It would have caught all 286
instantly. Where coverage is incomplete it must report `unverifiable`, never `clean`. Spec:
`~/.claude/plans/ce-dcp-condition-structuring-2026-08.md` §2.5.

**Remaining work:** implement that check, then re-run the retag against it (not against drift),
including the NULL-council rows and `dcp_all_provisions`.
**Found:** 2026-07-31
**Priority:** P1 — driven by whether the data is **valid and legitimate**, not by whether
a given council is currently receiving traffic. Live/staged status is explicitly NOT
the triage signal for this issue (see `feedback-prioritize-validity-not-traffic.md`).
Do not close or deprioritize this on "council X isn't live yet" grounds.

**Problem (as originally understood):**
`enrichment/extractors/applicability_tagger.py` (`ApplicabilityTagger`) writes
`v2_applicable_zones` / `v2_applicable_dev_types`, consumed as a **hard filter** (not
just display) by `frontend-nextjs/app/api/provisions/for-property/route.ts` for
`layer='use_specific'` queries, plus relevance sorting for dev_types. Two distinct defect
classes found first:

1. **Stale pre-fix rows never retagged.** PR #341 (2026-05-22) added `_get_config_driven()`
   so councils with a structural config (Waverley, Woollahra, City of Sydney, Ku-ring-gai)
   stop guessing zones from free text — free-text regex was matching DCP chapter/topic
   labels as zone codes (e.g. Waverley Part B7 = "Transport" chapter, regex read "B7" as
   zone B7). `run_applicability_tagging()` only retags rows where `v2_applicable_zones IS
   NULL` (`enrichment/pipeline.py:671`), so rows tagged before #341 were never revisited.
   Re-running the (then-current) tagger against every already-tagged row and diffing against
   the stored value:

   | Council | Tagged rows | Disagree with current code | % |
   |---|---|---|---|
   | Waverley | 2,854 | 1,493 | 52.3% |
   | Ku-ring-gai | 2,524 | 1,011 | 40.1% |
   | City of Sydney | 742 | 269 | 36.3% |
   | Woollahra | 6,214 | 226 | 3.6% |
   | Ashfield / Leichhardt / Marrickville | 21,557 | 0 | 0% |

   Note: 0% drift does NOT mean correct — it means stored value == current code output,
   which is also wrong if current code itself has always been wrong (see below).

2. **Config-file / tagger-code drift (Marrickville) and undeclared intent (Waverley,
   Ku-ring-gai, City of Sydney).** `MARRICKVILLE_CONFIG['parts']` in
   `enrichment/config/marrickville_config.py` was not actually read by
   `ApplicabilityTagger._get_marrickville_config()` for zone/dev-type values — that method
   hardcoded its own separate copy inline, and the two had drifted (e.g. Part 4.3 Boarding
   Houses: config said zones restricted to residential+business, tagger said `ALL`). Waverley's
   own file header names C1/C2 and D1/D2 as distinct sub-parts with different zones, but
   `WAVERLEY_CONFIG['parts']` only had one "C" and one "D" key, so both collapsed to the same
   zone list. Ku-ring-gai's and City of Sydney's `chapter_topics` entries never set
   `applicable_zones`/`applicable_dev_types` at all (despite being labelled `use_specific`
   or `precinct`), so `_get_config_driven()` silently defaulted them to `ALL`/`ALL`.

**Verification pass (2026-07-31) found the issue was larger than the initial summary above:**

3. **ROOT CAUSE: the hardcoded zone constants themselves predate the NSW zone reform,
   and this project already had the fix (`lep_zone_coverage`) sitting unused.**
   `enrichment/config/{waverley,woollahra,ashfield,leichhardt,marrickville}_config.py` all
   hardcoded zone-code Python constants (`RESIDENTIAL_ZONES`, `BUSINESS_ZONES =
   ['B1','B2','B4']`, `INDUSTRIAL_ZONES = ['IN1','IN2']`, etc.) — exactly the
   pattern `.claude/rules/regulatory-data.md` prohibits ("NEVER hardcode NSW planning
   regulatory data... flag it and replace before shipping"). Cross-checked against
   `lep_zone_coverage` (live-scraped LEP land-use table, 26 LGAs, `is_complete=true`,
   scraped 2026-05-12, previously gate-verified per
   `memory/project-zone-permissibility-unblocked-2026-07.md`):

   | LGA (real, current) | Actual zones in `lep_zone_coverage` |
   |---|---|
   | Waverley | C2, E1, E2, MU1, R2, R3, R4, RE1, RE2, SP2 |
   | Woollahra | C1, C2, E1, MU1, R2, R3, RE1, RE2, SP2, SP3 |
   | Sydney (City of Sydney) | E1, E2, E3, E4, MU1, R1, R2, RE1, SP1, SP2, SP5 |
   | Inner West (Ashfield/Marrickville/Leichhardt's real current LGA) | E1, E2, E3, E4, MU1, R1, R2, R3, R4, RE1, RE2, SP1, SP2, W1, W2, W4 |
   | Ku-ring-gai | C1, C2, C3, C4, E1, E3, MU1, R1–R5, RE1, RE2, SP1, SP2, W1 |

   **None of these five LGAs has a single B-zone or IN-zone today.** Real April 2023 NSW
   Employment Zones Reform mapping, confirmed against DPE's own transition table:
   B1,B2→E1; B3,B8→E2; B5,B6,B7→E3; IN1,IN2→E4; IN3→E5; B4→MU1; IN4→W4. (An earlier
   attempt at this mapping in `frontend-nextjs/lib/zone-translation.ts` had B4 wrongly
   under E2, IN1/IN4 wrongly under E4, IN2 wrongly under E5 — corrected in PR1 below.)
   `MARRICKVILLE_CONFIG`/`ASHFIELD_CONFIG`/`LEICHHARDT_CONFIG` actively tagged every
   Commercial-part provision with `B1/B2/B4` and every Industrial-part provision with
   `IN1/IN2` — codes that do not exist in the real Inner West LEP. For Marrickville Part 5
   (Commercial) this was harmless in practice because `MU1` was unioned into the
   same list alongside the dead codes, so real MU1-zoned properties still matched. **For
   Marrickville Part 6, Ashfield Chapter F Part 7, and Leichhardt Part F (Industrial),
   the zone list was `['IN1','IN2']` with no current-code fallback at all** — meaning,
   under the hard-filter query in `for-property/route.ts:936-940`, these provisions could
   not match ANY real property, because no property is zoned IN1/IN2 anymore. This was the
   exact "hide a rule, nobody would find out" failure the original conversation opened with
   — not hypothetical, and not confined to the 4 councils with drift.

   This also means the "0% drift" reported for Ashfield/Leichhardt/Marrickville above
   was misleading on its own: 0% drift only means the code agreed with itself over
   time — it says nothing about whether the zone codes were ever right. They were not.

4. **Systematic (not manual) config-vs-tagger diff across all 7 config-driven councils**
   confirmed the 3 Marrickville divergences already listed (Part 4.3, Part 5 dev_types,
   Part 6 dev_types) and surfaced one new, previously-unknown, latent bug: Ashfield's
   `chapter_f_parts` lookup in `_get_ashfield_config()` iterated the dict in insertion
   order and did unanchored substring matching (`f'Part_{part_num}' in document_id`) —
   `"Part_1"` matched inside `"Part_10"`, so any Chapter F Part 10 document would have been
   silently mistagged as Part 1 (Dwelling Houses) instead of the correct
   ALL-zones/ALL-dev-types. Same bug class as the already-fixed DQ-19 (Part 9 pattern
   collision). **Current DB impact: zero** — no Ashfield document_id matching Part_1X
   exists yet (checked directly), so this was latent, not live. Confirmed no equivalent
   collision in Leichhardt/Woollahra/Waverley/CoS/Ku-ring-gai.

5. **The ~9 councils with no structural config at all (Parramatta, Hornsby, Penrith,
   Blacktown, Campbelltown, Northern Beaches, Georges River, Cumberland, Inner West-as-
   tagged) are not a staleness issue — they are a standing, since-day-one exposure to the
   exact blind-text-regex false-positive class PR #341 was written to fix for the other 4,
   because they were simply never given a config.** ~175 of ~1,124 tagged rows carry
   multi-zone "kitchen sink" tags (e.g. Northern Beaches: one provision tagged
   `[B1,B2,B5,B7,E3,IN1,IN2,R2,R3]` — 9 zones on one provision, the signature of text-regex
   picking up every zone mentioned anywhere in the passage, not genuine applicability).
   Out of scope for the current fix — needs new structural configs per council, a separate
   follow-up. Partial investigation for Northern Beaches (only Warringah is actually
   ingested — 49 rows, one document_id, `v2_dcp_part='unknown'` for every row, no per-part
   structure to key a config off yet; `docs/DCP_SCOPE_CONFIG_REFERENCE.md` has partial
   structural knowledge — Parts A-E universal, zone differentiation in Part F — but that's
   for a *different* config system, `lib/council-configs/{council}.json`'s DA-mode scope
   filtering, not `enrichment/config/*.py`'s applicability tagging).
   Cheap interim mitigation identified for these 9 (not yet built): intersect the blind
   regex's zone matches against `get_valid_zones_for_lga()` (PR1) before returning, killing
   the "kitchen sink" false-positive class without needing DCP structure knowledge.

6. **The B→E zone-code confusion is codebase-wide, not confined to the DCP tagger — and a
   correct fix for it already exists but was barely adopted.** Full-repo grep for hardcoded
   zone-code array literals (not just the applicability tagger) found the same defunct
   B1-B8/IN1-IN4 codes hardcoded independently in ~20+ locations: `frontend-nextjs/lib/
   regulatory-constants.ts` (NSW_STANDARD_ZONES, feeds LMR/apartment-eligibility checks
   across granny flat, CDC screener, exempt/complying, SEE builder), `services/
   housing_sepp_eligibility.py` (`RESIDENTIAL_ZONES` — confirmed correct on investigation,
   see PR3 below), and a `HOUSING_SEPP_ZONES = ['R1','R2','R3','R4','B1',
   'B2','B4']` literal copy-pasted verbatim across 4 separate files (`see-helpers.ts`,
   `seeBuilders.ts`, `section-aggregation.ts`, `ContextSection.tsx`), among
   others (`environmental-relevance-filter.ts` — confirmed dead code, `ADGSummaryCard.tsx`
   — a *separate* real bug found and fixed in PR3, see below, `ComplianceDashboard.tsx` and
   `pages/api/development-types.ts` — confirmed dead code). None of these imported a shared
   source or queried `lep_zone_coverage`.

   **This exact problem (B1/B2 vs E1 zone-code mismatch) had already happened once before,
   in a *different* table/pipeline**, per
   `.claude/docs/history/2026-01-implementation/ZONE_AND_DEVTYPE_TRANSLATION_CONTEXT.md`
   (Nov 2025): `dcp_general_requirements.applicable_zones` (the LLM-curated table behind
   the capacity/compliance API, separate from `regulatory_provisions.v2_applicable_zones`
   behind the provisions display) had the identical defect. The fix built then —
   `frontend-nextjs/lib/zone-translation.ts`, `ZONE_TRANSLATION_MAP` — modelled the right
   *concept* but, on verification, had its own mapping errors (see #3 above). It was also
   only ever wired into 2 routes (`/api/compliance/constraints`, `/api/compliance/
   dcp-complete`) — and a full reachability audit found **both of those routes are
   themselves dead code**, only reachable through the orphaned `ComplianceDashboard.tsx`
   which nothing in the live app renders. So `zone-translation.ts` had zero live consumers
   before this fix. The real live critical path for DCP provisions is
   `ProvisionsByTocStructure.tsx` → `app/assessment/page.tsx`, confirmed via reachability
   audit, which is what the applicability tagger (PR2) actually feeds.

**Fix — sequenced as PR1 through PR5 (see `~/.claude/plans/twinkly-bouncing-valiant.md` for
the full plan):**
- **PR1 (done):** `frontend-nextjs/shared/zone-taxonomy.json` — single corrected
  legacy↔current alias map, generated by `scripts/generate_zone_taxonomy.py` (CI drift-check
  via `--check`), consumed by both `frontend-nextjs/lib/zone-translation.ts` (TS) and the new
  `enrichment/config/zone_taxonomy.py` (Python) — no more independent copies. Added
  `getValidZonesForLga()` to both `frontend-nextjs/lib/db.ts` and `services/db_config.py`
  (live query against `lep_zone_coverage`, short in-process cache) for the separate question
  of "what zones currently exist in LGA X."
- **PR2 (done):** Marrickville tagger now reads `MARRICKVILLE_CONFIG['parts']` directly
  instead of a hardcoded shadow copy; Ashfield `Part_1`/`Part_10` collision fixed (word-
  boundary anchored); Waverley `WAVERLEY_CONFIG['parts']` split into C1/C2 (R2 vs R3,R4) and
  D1/D2 (E1,E2 vs MU1), matching the file's own documented distinction; Ku-ring-gai's 5
  residential parts whose name *is* the dev type now set `applicable_dev_types`; all 7
  configs' zone constants swapped to current-era codes; Woollahra's Part D/F3 direct B-zone
  literals fixed (not routed through a constant, hardcoded per-entry — same translation
  applied inline). City of Sydney's `section_4` and Ku-ring-gai's `part_8_mixed_use`/
  `part_9_non_residential` deliberately NOT filled in — would mean guessing at regulatory
  scope, not translating something already stated. Extended
  `tests/enrichment/test_applicability_tagger.py` with regression tests per bug (46 tests
  total, 13 new, all passing).
- **PR3 (done):** consolidated live frontend/Python zone hardcodes onto PR1's shared
  source — `regulatory-constants.ts`, `housing_sepp_eligibility.py`, the granny flat cluster
  (`app/api/satellite/granny-flat/route.ts`, `app/reports/granny-flat/page.tsx`,
  `app/api/canibuildit/check/route.ts`, `app/api/og/granny-flat/route.tsx`), and the
  SEE/CDC/pattern-book cluster (`lib/see/seeBuilders.ts`, `lib/see/section-aggregation.ts`,
  `lib/pdf/see-helpers.ts`, `components/pdf/ContextSection.tsx`,
  `components/compliance/ExemptComplyingProvisions.tsx`,
  `components/compliance/CDCScreener.tsx`, `components/compliance/ADGSummaryCard.tsx`,
  `app/api/sepp/exempt-complying/route.ts`, and
  `lib/pattern-book-eligibility/check-exclusions.ts`'s `isZoneEligible()`, whose own
  `['R1','R2','R3']` literal was the last remaining hardcode — now a new
  `PATTERN_BOOK_CDC.ELIGIBLE_ZONES` export in `regulatory-constants.ts`, deliberately not
  merged with `CDC_HOUSING_CODE_ZONES` since Pattern Book excludes R4/RU5). Also found and
  fixed a **separate real bug** while doing this: `components/compliance/ADGSummaryCard.tsx`'s
  `APARTMENT_RESTRICTED_ZONES` had current Employment zones E1-E4 mislabelled as "Environment
  zones," directly contradicting `NSW_STANDARD_ZONES.APARTMENT_PERMITTING` (E1/E2 correctly
  permit apartments/shop-top housing) — fixed. Also found `app/api/housing-sepp/eligibility/
  route.ts` has a deeper, separate issue than zone-code staleness (tracked as DQ-31 above, not
  folded into this fix). Verified clean via `python scripts/lint_hardcoded_zone_codes.py --all`
  (only pre-existing, out-of-scope hits remain: historical `scripts/fixes/DQ*.py` one-off
  scripts, the free-text `ZONE_PATTERNS`/`ZONE_CATEGORY_PATTERNS` regex fallback in
  `applicability_tagger.py` used for the ~9 no-config councils, and other pre-existing files
  untouched by PR1-3 — none are new hardcodes introduced by this work).
- **PR4 (done):** CI guard `scripts/lint_hardcoded_zone_codes.py` (following
  `scripts/lint_bracket_access.py`'s staged-diff pattern) wired into `.githooks/pre-commit`
  step 8 — fails a commit that introduces a new hardcoded zone-code array in a file that
  doesn't already import the shared taxonomy, with a `# noqa: zone-codes` escape hatch.
  Diff-scoped (only checks staged additions), so it does not fail-red on pre-existing
  hardcodes not yet fixed (the 9 no-config councils, City of Sydney's `section_4`, the
  historical `scripts/fixes/DQ*.py` scripts).
- **PR5 (done):** backup + guarded reset of `v2_applicable_zones`/`v2_applicable_dev_types`
  to NULL for the 7 configured councils' affected rows, re-ran `run_applicability_tagging()`
  with the fixed tagger. Verified: re-running the drift script (fixed tagger output vs stored
  DB value) shows **0% disagreement** across all 7 configured councils, confirming the retag
  matches current code by construction.

---

## DQ-29: Doubled-character OCR corruption in provision_text

**Status:** 🟡 Partially fixed 2026-07-15 — 845 header lines stripped in DB; 22 scrambled-body rows remain for re-extraction
**Found:** 2026-07-15 (surfaced by the latent-scope duplicate-audit lane)
**Priority:** P1 (>2% threshold breached for affected councils; City of Sydney ~97% of live actionable rules)

**Problem:** In affected provisions every character of the extracted text is
doubled, e.g. `SSPPEECCIIFFIICC SSIITTEESS`, `KKuu--rriinngg--ggaaii`,
`DDeevveellooppmmeenntt`. The `provision_text` is effectively unreadable — the
field customer-facing reports and the capacity/compliance engines read from.

**How it was found:** The cross-council duplicate audit
(`scripts/latent_scope_dup_audit.py`) returned false "contradiction" pairs
because TF-IDF was matching this garbled boilerplate rather than rule meaning.
Investigating the noise revealed the systematic corruption.

**Scope (live DB, full `regulatory_provisions`, 53,716 rows, 2026-07-15):**
854 corrupted rows total (1.6% overall), concentrated by council:

| Council | Corrupted | Live (`is_current`) |
|---|---|---|
| city_of_sydney | 684 | 644 |
| ku_ring_gai | 98 | 14 |
| campbelltown | 37 | 37 |
| ashfield | 27 | 0 (not served) |
| northern_beaches | 3 | 3 |
| (NULL council) | 5 | 5 |

**Detection query (read-only; regenerates the full ID list any time):**
```sql
SELECT id, source_council, is_current, v2_is_actionable
FROM regulatory_provisions
WHERE provision_text ~ '([A-Za-z])\1([A-Za-z])\2([A-Za-z])\3'
ORDER BY source_council NULLS LAST, id;
```
Snapshot of all 854 IDs + snippets: `data/latent_scope/ocr_corruption_worklist.csv` (git-ignored, local).

**Root cause (suspected):** the PDF→text extraction step for these documents
(City of Sydney DCP 2012 in particular) doubled every glyph — likely a specific
extractor/font path, not a content problem. Needs confirming against the source
extractor before re-running.

**Impact / urgency (traced 2026-07-15):**
- **SERVED customer-facing: YES, but confined to the DCP provisions display panel.**
  City of Sydney is configured and reachable (`frontend-nextjs/lib/council-config.ts:191`,
  no disable gate). `app/api/provisions/for-property/route.ts` selects `provision_text`,
  filters `is_current = TRUE` and `document_id ILIKE '%Sydney_DCP%'` (route.ts:548,846,873),
  and `components/compliance/PageGroupedProvisions.tsx` renders it raw. So a CoS address
  lookup shows the 644 live doubled-character rows in the provisions list.
- **Existing sanitisation does NOT help:** `stripOcrHeaderPrefix` (route.ts:125) is a
  Marrickville-only page-header regex — a no-op for CoS; it does not touch doubled chars.
- **NOT affected:** capacity/constraint engine (reads `dcp_setback_controls`, where CoS is
  clean — 0/27 corrupted source_text, 0 controls linked to a corrupted provision),
  intelligence brief, and conveyancing (none read `regulatory_provisions`).
- **Net severity:** a user-facing *display* defect in the provisions panel, NOT a
  wrong-number / liability defect. Computed numbers and verdicts for CoS remain correct.
  Business open question: actual CoS lookup traffic (config is live, but CoS is not a
  beachhead council).

**Fix applied 2026-07-15 (production read+transform+write):**
- Stripped the doubled-glyph header lines from `provision_text` for **845 rows** via a
  guarded transactional UPDATE — per-id, `WHERE id=%s AND provision_text=<backup value>`
  (optimistic-concurrency guard), never blanking a row, `statement_timeout=30s`.
- Verified: City of Sydney sample (id 95298) now renders clean; detection count dropped
  854 → 57 still matching the pattern, of which **35 are legitimate doubled-letter words**
  (e.g. the suburb "Woolloomooloo") — false positives, no action.
- **Backup / rollback source:** `data/latent_scope/ocr_fix_backup.json` (all 854 pre-fix rows,
  `{id, council, before}`). To roll back, UPDATE each id back to its `before` value.

**Remaining — 22 rows need SOURCE re-extraction (NOT strip-fixable):**
Their body text is doubled *and* scrambled (e.g. `PPrirmimaarryy` = "Primary"), which is not
losslessly reversible. Split: city_of_sydney 7, ku_ring_gai 10, campbelltown 4, (null) 1.
Worklist: `data/latent_scope/reextraction_worklist.csv`. Regenerate any time with the
detection query above (then exclude legitimate doubled-letter words).

**Root cause identified 2026-07-15 (investigated for re-extraction):** the source PDFs carry a
DUPLICATED text layer. pymupdf on the local Campbelltown Part 3 PDF returns each line twice
("Each dwelling shall have a minimum of / Each dwelling shall have a minimum of"); the original
extractor concatenated the overlapping copies, producing the char-interleaved scramble. A clean
re-extraction must therefore: (a) DEDUPLICATE the doubled text layer during extraction,
(b) re-chunk by clause, (c) re-map pages (DB `pdf_page` does not align with the PDF page index —
DB page 21 pointed at a different clause than the PDF's page 21). This is a pipeline job, not an
in-place fix: the char-interleaved DB text is not losslessly reversible, and blind page-dumping
would merge clauses (unsafe for legal text). City of Sydney section-6 source PDF is not local
(only sections 3-4 are present in `data/dcps/`) → must be re-downloaded first. Deferred to the
enrichment pipeline; scrambled bodies are already reduced (headers stripped in the 2026-07-15 pass).

**UI exposure + mitigation 2026-07-15:** Of the 22, only 7 were customer-visible (provisions panel
filters `is_current AND v2_is_actionable`); the other 15 sit in the DB unused. None have a
`pdf_page_image_url`, so there is no figure image to fall back on — only the OCR'd text. The 2
genuinely-unreadable ones (ids 95802, 95807 — City of Sydney section-6 figure/site-plan pages,
e.g. Cahill Expressway / Herald Square public-domain plans, which appear only for those specific
sites) were set `v2_is_actionable=false` to remove the text-soup from display (backup:
`data/latent_scope/actionable_flag_backup.json`; reversible). They are figure legends — the
enforceable setback controls live in separate text provisions / `dcp_setback_controls`, so nothing
enforceable was hidden. The remaining 5 shown rows (4 Campbelltown, 1 Ku-ring-gai) are
readable-but-untidy and left in place pending re-extraction.

---

## DQ-28: Ashfield chapter_e2_haberfield TOC — catch-all only

**Status:** ✅ Fixed 2026-03-30
**Found:** 2026-03-29
**Fixed:** 2026-03-30

**Problem:** The Haberfield neighbourhood chapter (121 provisions, all on pdf_page=2) had no extracted section-level TOC data. A depth=0 catch-all entry was inserted in migration 018 so the JOIN worked, but all 121 provisions grouped under a single bucket.

**Root cause:** `COUNCIL_CHAPTER_RANGES` for both `chapter_b_public_domain` and `chapter_e2_haberfield` had a single entry covering the whole chapter. The extractor sets `pdf_page = page_start` of the matching range, so all provisions got the same page.

**Fix (migration 024):**
- Expanded `COUNCIL_CHAPTER_RANGES` to per-section entries (7 for chapter_b, 17 for chapter_e2)
- Re-extracted both chapters: chapter_b 49→55 provisions across 7 pages; chapter_e2 121→134 across 17 pages
- Deleted old overlapping TOC entries; inserted 7 (chapter_b) + 17 (chapter_e2) non-overlapping TOC entries
- `KNOWN_GRANULARITY_EXEMPTIONS` emptied — both chapters now pass the granularity gate
- Ashfield grade: 93.7% → 100% TOC JOIN; Grade A confirmed

---

## DQ-22: TOC Provisions Marked as Actionable

**Status:** ✅ FIXED
**Found:** 2026-01-26
**Fixed:** 2026-01-26

**Problem:** 34 Table of Contents (TOC) provisions had `v2_is_actionable = true`, causing them to appear in the DCP tab UI. User reported Part D showing TOC as first provision for 185 Parramatta Road Annandale.

**Example:** ID 80116 (Leichhardt Part D Energy) contained:
```
SECTION 1 – ENERGY MANAGEMENT .
SECTION 2 – RESOURCE RECOVERY AND WASTE MANAGEMENT .......... .....6
```

**Root Cause:** v2 enrichment process didn't detect TOC patterns (dotted leaders like `........`). The `dcp-complete` route had TOC filters but `for-property` API relied solely on `v2_is_actionable`.

**Fix:** SQL update to set `v2_is_actionable = false` for provisions containing `........`:
```sql
UPDATE regulatory_provisions
SET v2_is_actionable = false
WHERE v2_is_actionable = true
AND provision_text LIKE '%........%'
-- Fixed 34 rows
```

**Affected Documents:** Leichhardt DCP (Parts C, D, G), Marrickville DCP (Parts 2, 4, 6, 7, 8, 9), LEP TOC pages

---

## DQ-23: Duplicate Provisions in TOC View

**Status:** ✅ FIXED
**Found:** 2026-01-26
**Fixed:** 2026-01-26

**Problem:** Provisions appearing multiple times in DCP tab TOC-structured view. User reported "C1.5 CORNER SITES" showing 18 provisions on page 17 (6 provisions × 3 duplicates) and 6 provisions on page 18 (3 provisions × 2 duplicates).

**Root Cause:** The `groupByTocStructure` function (frontend-nextjs/app/api/provisions/for-property/route.ts:685-691) flattened provisions from all 4 layers (generic, use_specific, condition, precinct) WITHOUT deduplication. When the same provision appeared in multiple layers due to the layer query logic, it was added to the TOC structure multiple times.

**Code Location:** `frontend-nextjs/app/api/provisions/for-property/route.ts:688-690`

**Fix:** Added Map-based deduplication by provision ID before grouping:
```typescript
// Before (buggy):
const allProvisions: any[] = [];
for (const layer of layers) {
  for (const provision of layer.provisions) {
    allProvisions.push({ ...provision, layer: layer.layer });
  }
}

// After (fixed):
const provisionMap = new Map<number, any>();
for (const layer of layers) {
  for (const provision of layer.provisions) {
    if (!provisionMap.has(provision.id)) {
      provisionMap.set(provision.id, { ...provision, layer: layer.layer });
    }
  }
}
const allProvisions = Array.from(provisionMap.values());
```

**Impact:** Prevents duplicate provision display in DCP tab. Keeps first occurrence (preserves layer priority order: generic → use_specific → condition → precinct).

**Test:** Reload 185 Parramatta Road Annandale assessment - C1.5 Corner Sites should now show 6 unique provisions on page 17, 3 unique provisions on page 18.

---

## DQ-19: Part 9 Pattern Collision with Section Numbers

**Status:** ✅ FIXED
**Found:** 2026-01-24 (via automated test suite)
**Fixed:** 2026-01-24

**Problem:** Layer tagger pattern `'9__' in doc` matched section numbers like `19__` or `29__`, causing Part 2 sections to be misclassified as Part 9 precincts.

**Example:** `Marrickville__DCP__2011__-__2__19__Trees` (Section 2.19 Trees) was classified as `precinct` instead of `generic`.

**Root Cause:** Pattern `'9__'` is a substring of `19__`, `29__`, etc.

**Fix:** Added leading delimiter requirement in `layer_topic_tagger.py:179`:
```python
# Before: if '9_' in doc or '9__' in doc or 'Precinct' in doc:
# After:
if '_9_' in doc or '_9__' in doc or '-9_' in doc or '-9__' in doc or 'Precinct' in doc:
```

**Validation:** Test `test_marrickville_part2_section_topics` now passes.

---

## DQ-20: Part 5/6 vs Part 9 Precedence Issue

**Status:** ✅ FIXED
**Found:** 2026-01-24 (via automated test suite)
**Fixed:** 2026-01-24

**Problem:** Part 5 check for `'Commercial' in doc` matched before Part 9 for precinct names containing "Commercial".

**Example:** `Marrickville__DCP__2011__-__9__40__Town__Centre__Commercial` was classified as `use_specific` (Part 5) instead of `precinct` (Part 9).

**Fix:** Reordered Part 9 check to run before Part 5/6 in `layer_topic_tagger.py:169-177`.

**Validation:** Test `test_part9_precinct` now passes.

---

## DQ-21: Double-Underscore Document_ID Patterns

**Status:** ✅ FIXED
**Found:** 2026-01-24 (via automated test suite)
**Fixed:** 2026-01-24

**Problem:** Part 4.1/4.2 detection only checked `'4_1'` and `'4.1'`, missing `'4__1'` patterns used in some document_ids.

**Fix:** Added `'4__1'` and `'4__2'` patterns to `layer_topic_tagger.py:159-166`.

**Validation:** Test `test_part4_1_use_specific` now passes.

---

## Two-Table Architecture: Raw vs LLM-Curated

**IMPORTANT: Do not assume low LLM coverage means incomplete extraction.**

There are TWO provision data sources:

1. **`regulatory_provisions`** (raw) - PDF paragraphs with regex-classified `v2_topic`
   - Complete coverage (all PDF content)
   - Lower quality (includes headers, intro text, cross-references)
   - 43 unique topics

2. **`dcp_general_requirements`** (LLM-curated) - Extracted actionable requirements with `category`
   - Intentionally selective (only actionable development controls)
   - Higher quality (distilled requirements)
   - 64 unique categories

**LLM Extraction is SELECTIVE by design:**
- The LLM is instructed to "Extract ALL actionable development controls"
- This EXCLUDES: headers, objectives, definitions, explanatory context, cross-references
- A 20-30% extraction rate is NORMAL - most DCP text is not actionable

**Coverage by council (as of 2025-12-01):**
- Ashfield: 791 LLM / 1,579 raw = 50%
- Marrickville: 1,338 LLM / 985 raw = 136% (expansion from multi-requirement paragraphs)
- Leichhardt: 834 LLM / 2,989 raw = 28%

**Leichhardt's 28% is NOT incomplete** - Part C Section 1 alone has 1,782 raw provisions but only 342 extracted requirements (19%). This is correct - most Part C content is objectives and context, not controls.

**Current API usage:**
- Heritage (condition layer): Uses LLM-curated `dcp_general_requirements`
- All other queries: Uses raw `regulatory_provisions` with `v2_topic`

---

## Context Files to Read First

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `.claude/prp/INDEX.md` | Architecture overview, implementation state |
| 2 | `PROVISION_BASED_ARCHITECTURE_STRATEGY.md` | Full 8-part strategy |
| 3 | `DEPLOYMENT.md` | How to sync local/Supabase |
| 4 | **THIS FILE** | Current quality issues and fix progress |
| 5 | `.claude/DQ11_HERITAGE_SUBCATEGORIZATION.md` | Heritage enrichment research & plan |

---

## Current Quality Issues (Priority Order)

### DQ-1: Precinct Filtering Returns 0 Provisions (CDC)
**Status:** ✅ RESOLVED - NOT A BUG
**Priority:** N/A - Expected behavior
**Evidence:** Full cascade with `precinct_id='12_'` + `assessment_type=CDC` returns Layer 4 = 0
**Root Cause:**
- Precinct 12_ (Marrickville Park and Morton Park) has 8 provisions for DA
- All 8 are character statements (qualitative, no numeric values)
- CDC filter requires `v2_has_numeric_value = true`
- Therefore CDC correctly returns 0 for this precinct

**NOT A BUG:** Other precincts (G7=6, Part 1=6, 25_=4, 10_=4) have CDC-compatible provisions with numeric values.

**Verification:**
```sql
-- DA returns 8 for precinct 12_
SELECT COUNT(*) FROM regulatory_provisions
WHERE v2_is_actionable = true AND v2_dcp_layer = 'precinct' AND v2_precinct_id = '12_';
-- Result: 8

-- CDC returns 0 (expected - no numeric values in this precinct)
SELECT COUNT(*) FROM regulatory_provisions
WHERE v2_is_actionable = true AND v2_dcp_layer = 'precinct'
AND v2_precinct_id = '12_' AND v2_provision_type = 'control' AND v2_has_numeric_value = true;
-- Result: 0
```

### DQ-2: Topic Misclassification
**Status:** ✅ RESOLVED
**Priority:** P1 - HIGH (was)
**Evidence:** "Car parking design controls" (ID 78329) was tagged as HEIGHT topic
**Root Cause:** Two issues in `layer_topic_tagger.py`:
1. **Dictionary iteration order**: `TOPIC_KEYWORDS` checked `height` before `parking`
2. **Unused section mapping**: `MARRICKVILLE_PART2_TOPICS` was never used

**Fix Applied (2025-11-24):**
1. Added `_extract_marrickville_part2_topic_from_docid()` method to use document_id section number
2. Changed `_extract_topic_from_text()` to return earliest match by position

**Results:**
- 14,501 provisions had topics updated
- ID 78329 now correctly tagged as `parking`
- "parking" provisions: 347 → 722 (+375)
- "parking" provisions wrongly tagged as height: 124 → 64 (-60)

**Fix Script:** `scripts/fixes/DQ2_fix_topic_classification.py`

### DQ-3: Provision Text Contains Headers Not Controls
**Status:** RESOLVED
**Priority:** P2 - MEDIUM (was)
**Evidence:** "Part 1 Preliminary..." TOC entries marked as actionable
**Root Cause:** LEP table of contents extracted as provisions
**Fix Applied (2025-11-24):** Marked 9 TOC entries as `v2_is_actionable = false`
**Result:** 11,835 -> 11,826 actionable provisions
**Fix Script:** `scripts/fixes/DQ3_fix_toc_entries.py`

### DQ-4: v2_marker Mostly NULL
**Status:** ACCEPTED - Design Limitation
**Priority:** P3 - LOW
**Evidence:** 8.5% have markers (1,008/11,826)
**Root Cause:** Extractor handles C markers only, not O (Objectives). 248 missing are all "O1" boilerplate objectives.
**Decision:** Accept as-is. C markers (topic mapping) work. O markers are qualitative, not needed for CDC.
**Impact:** None - fitness test passed without full marker coverage.

### DQ-5: Generic Layer Dominates (78%)
**Status:** ACCEPTED - Expected
**Priority:** P3 - LOW
**Evidence:** generic=78%, condition=10%, precinct=10%, use_specific=1%
**Assessment:** This is normal for DCP structure. Dev_type filter reduces 354→34 (90%). Working as intended.

### DQ-6: Duplicate Provisions
**Status:** ACCEPTED - Minor
**Priority:** P3 - LOW
**Evidence:** 246 duplicates in 10 groups (2% of total)
**Assessment:** Mostly SEPP boilerplate text repeated across contexts. Minor impact, not blocking.

### DQ-7: Dev-Type Coverage
**Status:** ✅ RESOLVED
**Priority:** P0 - CRITICAL (was)
**Evidence:** All 13 dev_types now have adequate CDC provision coverage.

| Dev Type | Before | After | Status |
|----------|--------|-------|--------|
| dwelling_house | 34 | 307 | OK |
| secondary_dwelling | 8 | 281 | OK |
| dual_occupancy | 10 | 283 | OK |
| multi_dwelling_housing | 10 | 282 | OK |
| residential_flat_building | 10 | 280 | OK |
| retail_premises | 11 | 109 | OK |
| commercial_premises | 0 | 99 | OK |
| office_premises | 0 | 122 | OK |
| industrial_development | 6 | 117 | OK |
| warehouse | 4 | 109 | OK |
| boarding_house | 9 | 277 | OK |
| child_care_centre | 1 | 40 | OK |
| shop_top_housing | 10 | 53 | OK |

**Root Cause:** 286 provisions tagged `['ALL']` instead of specific dev_types.

**Fix Applied (2025-11-24):**
1. `DQ7_devtype_enrichment.py` - Section-based + keyword mapping for residential
2. `DQ7_commercial_industrial_enrichment.py` - Zone-based enrichment for B/IN zones
3. `DQ7_remaining_devtypes.py` - Text matching + parking provisions for all types

**Fix Scripts:** `scripts/fixes/DQ7_*.py`

---

## Fix Workflow

### Per-Issue Process
```
1. Read this file to understand issue
2. Investigate root cause with diagnostic queries
3. Create fix script in scripts/fixes/DQ-{N}_fix_{description}.py
4. Run fix on LOCAL first
5. Verify with test_workflow_quality.py
6. Sync to Supabase: python scripts/sync_v2_to_supabase.py
7. Update status in this file
8. Commit with message: "fix(data): DQ-{N} {description}"
```

### Session Start Checklist
```
[ ] Read .claude/prp/INDEX.md
[ ] Read this file (DATA_QUALITY_TRACKER.md)
[ ] Check which DQ-N is next to fix
[ ] Run test_workflow_quality.py to see current state
[ ] Pick ONE issue to fix this session
```

---

## Test Commands

```bash
# Run quality assessment
python test_workflow_quality.py

# Check sync status
python scripts/compare_local_supabase.py

# Check specific issue
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL') or 'dbname=nsw_planning')
cur = conn.cursor()
# Add diagnostic query here
"
```

---

## Session Log

### 2024-11-24: Initial Assessment
- Completed 4-layer API implementation
- Ran workflow quality tests
- Identified 6 data quality issues
- Created this tracking file

### 2025-11-24: DQ-1 and DQ-2 Resolution + Fitness Assessment
- **DQ-1 RESOLVED**: Not a bug - expected behavior
  - Precinct 12_ has 8 DA provisions but 0 CDC provisions (no numeric values)
  - Other precincts (G7, Part 1, 25_) have CDC-compatible provisions
- **DQ-2 RESOLVED**: Topic misclassification fixed
  - Root cause: Dictionary iteration order + unused section mapping
  - Fix: Added section-based topic extraction + earliest-match algorithm
  - Result: 14,501 provisions updated, ID 78329 now correctly tagged

**FITNESS FOR PURPOSE ASSESSMENT:**
```
Scenario: R2 Zone, Dwelling House, CDC Assessment
  Layer 1 (Generic + dev_type): 34
  Layer 2 (Zone R2):            3
  Layer 3 (Condition):          0 (non-heritage)
  Layer 4 (Precinct 12_):       0 (qualitative only)
  TOTAL:                        37 provisions

VERDICT: PASS - Within target range (30-100)
```

Key findings:
- Full cascade with dev_type filter reduces 354 -> 34 (90% reduction)
- v2_applicable_dev_types is 100% populated for generic layer
- Topic classification working for Marrickville Part 2.10 (all 38 = parking)
- System is FIT FOR PURPOSE for CDC certifier workflow

### 2025-11-24: DQ-7 Dev-Type Enrichment Complete
- **DQ-7 RESOLVED**: All 13 dev_types now have adequate CDC provision coverage
  - Before: Only dwelling_house (34) worked, others had 0-11
  - After: All types have 40-307 provisions
- **Fix approach**:
  1. `DQ7_devtype_enrichment.py` - Section/keyword mapping for residential (8,103 updated)
  2. `DQ7_commercial_industrial_enrichment.py` - Zone-based enrichment for B/IN zones
  3. `DQ7_remaining_devtypes.py` - Text matching + parking provisions for remaining types

**ALL DATA QUALITY ISSUES NOW RESOLVED**

### DQ-8: DCP-ONLY Scope Clarification (2025-11-24)
**Finding**: Previous DQ-7 enrichment incorrectly included SEPP/LEP provisions.
**Scope**: This pipeline is DCP-ONLY. SEPP/LEP values come from Planning Portal API.

**Actual DCP CDC Data:**
| Council | Total DCP | CDC-eligible |
|---------|-----------|--------------|
| Marrickville | 1,051 | 79 (8%) |
| Leichhardt | 2,989 | 43 (1%) |
| Ashfield | 1,526 | 10 (1%) |
| **TOTAL** | **5,566** | **132 (2%)** |

**Reality**: Only 2% of DCP provisions are CDC-eligible (have numeric values).
This is DATA REALITY - DCPs are mostly qualitative (objectives, character statements).
The 132 DCP CDC provisions ARE correctly dev_type tagged.

### Professional Scenario Testing (2025-11-24)
- **CDC scenarios**: All pass (272-274 provisions for residential, 86-88 for commercial/industrial)
- **DA scenarios**: Return more results (7000+) - expected, DA includes objectives not just controls
- **Zone handling**: 'ALL' correctly treated as wildcard (matches any zone)
  - Marrickville uses specific zones (R2, R3/R4 for Part 4)
  - Leichhardt/Ashfield use 'ALL' (zone not a determinant for those DCPs)

### DQ-9: DCP Filter Bug - IWLEP Reference (2025-11-24)
**Status:** ✅ FIXED
**Priority:** P1 - HIGH (was)
**Finding**: Wrong DCP filter was excluding valid DCP provisions.

**Root Cause:**
- WRONG filter: `NOT ILIKE '%LEP%'` - excluded DCP files with "IWLEP" in name
- CORRECT filter: `NOT ILIKE '%Local_Environmental_Plan%'` - only excludes actual LEP docs

**Impact:**
- 2,330 Leichhardt DCP provisions were incorrectly filtered out
- Leichhardt appeared to have "659" provisions but actually has **2,989**

**Corrected Data:**
| Council | generic | precinct | condition | use_specific | TOTAL |
|---------|---------|----------|-----------|--------------|-------|
| Marrickville | 230 (22%) | 359 (34%) | 315 (30%) | 147 (14%) | 1,051 |
| **Leichhardt** | **2,309 (77%)** | 659 (22%) | 0 | 21 (1%) | **2,989** |
| Ashfield | 422 (28%) | 197 (13%) | 907 (59%) | 0 | 1,526 |

**Fix:** Updated filter in INDEX.md and test files to use correct pattern

### DQ-10: Council-Specific UI/UX Strategy (2025-11-24)
**Status:** ✅ DOCUMENTED
**Priority:** P1 - HIGH

**Finding**: Each council's DCP has a DIFFERENT compliance philosophy that UI should reflect.

**Council DCP Structures:**
| Council | Primary Layer | Filter Strategy |
|---------|---------------|-----------------|
| Marrickville | Balanced (precinct 34%, condition 30%, generic 22%) | Zone + Precinct + Topic |
| Leichhardt | **Generic-heavy (77%)** | Topic is PRIMARY filter (reduces 2,211 → 30-85) |
| Ashfield | Condition-heavy (59%) | Site conditions + Topic |

**Test Results (dwelling_house filter with correct DCP filter):**
| Council | dwelling_house count | Layer distribution |
|---------|---------------------|-------------------|
| Marrickville | 228 | generic 53%, use_specific 21%, precinct 15%, condition 11% |
| **Leichhardt** | **2,211** | generic 98%, precinct 2% |
| Ashfield | 394 | generic 99%, condition 1% |

**UI/UX Implications:**
1. **Leichhardt**: Has 2,211 dwelling_house provisions - MUST use topic filter to narrow
   - Topic options: parking (85), building_form (81), landscaping (34), heritage (30)
2. **Marrickville**: Zone filter effective, also use topic
3. **Ashfield**: Site condition (heritage) is key filter, also use topic

**For certifier workflow:**
- Leichhardt CDC: 21 provisions (workable)
- Marrickville CDC: 17 provisions (workable)
- Topic filtering reduces DA queries by 80-95%

### Comprehensive Professional Testing (2025-11-24)
**Test Suite:** `test_comprehensive_professional.py`, `test_tailored_filters.py`
**Results:** 9/13 scenarios PASS

**Scenario Results:**
| Scenario | Count | Expected | Status |
|----------|-------|----------|--------|
| Marrickville R2 Dwelling DA | 193 | 50+ | PASS |
| Marrickville R2 Dwelling CDC | 17 | 5+ | PASS |
| Marrickville R3 Multi-Dwelling DA | 109 | 30+ | PASS |
| Marrickville B2 Retail CDC | 25 | 3+ | PASS |
| Leichhardt R2 Dwelling DA | 39 | 100+ | FAIL (data gap) |
| Leichhardt R2 Dwelling CDC | 2 | 5+ | FAIL (data gap) |
| Ashfield R2 Dwelling DA | 390 | 50+ | PASS |
| Ashfield Dual Occ DA | 397 | 30+ | PASS |
| ALL COUNCILS R2 Dwelling DA | 649 | 200+ | PASS |

**Key Insights:**
1. **Marrickville**: Full 4-layer support, zone filtering effective (34% zone-specific)
2. **Leichhardt**: Generic-heavy (77% generic, 2,989 total) - topic filter CRITICAL
3. **Ashfield**: Condition-heavy (59% condition layer), low CDC is data reality

**Filter Effectiveness by Type:**
- **Dev_type**: Effective for ALL councils (reduces to 2-30% of total)
- **Topic**: Very effective (2-8% per topic, 80-95% reduction)
- **Zone**: Only for Marrickville (34% zone-specific)

### Session Log: Council-Specific UI Implementation (2025-11-24)

**Completed:**
1. ✅ Fixed DCP filter bug (`NOT ILIKE '%LEP%'` was wrong - excluded IWLEP-referenced files)
2. ✅ Correct filter: `NOT ILIKE '%Local_Environmental_Plan%'`
3. ✅ Discovered Leichhardt has 2,989 provisions (not 659) - was filter bug, not data gap
4. ✅ Implemented council-specific UI in `ProvisionsByTopic.tsx`:
   - Topic filter buttons with council-specific suggested topics
   - Warning for Leichhardt when no topic selected
   - Professional priority ordering of topics
5. ✅ Created `frontend-nextjs/lib/council-config.ts`
6. ✅ Created `PROFESSIONAL_USER_GUIDE.md` for trial users
7. ✅ Created git tag `v1.0-pre-council-ux` on main before merge
8. ✅ Pushed tag to remote

### Next Steps:
1. ✅ ~~Fix DQ-9~~ (was filter bug, not data gap - FIXED)
2. ✅ ~~Implement council-aware filtering~~ (DONE)
3. Merge to main and deploy to Vercel
4. Test production with professional users

### DQ-11: Heritage Sub-Categorization (2025-11-25)
**Status:** ✅ COMPLETE
**Priority:** P2 (was)
**Scope:** Ashfield Chapter E1 heritage provisions (907 total)

**Problem:** 907 heritage provisions shown as undifferentiated list. No way to find relevant controls.

**Solution Applied:** LLM categorization using OpenAI gpt-4o-mini

**Final Results (verified in database):**
| Type | Count | Description |
|------|-------|-------------|
| control | 163 | Actionable requirements with C markers or imperative verbs |
| character | 422 | HCA-specific descriptions and significance statements |
| descriptive | 322 | Historical narratives, style definitions, background |

**Element Tagging (controls):**
- fence: 39, materials: 37, roof: 29, verandah: 21, scale: 16
- car_parking: 15, window: 14, facade: 14, demolition: 13, chimney: 12

**HCA Tagging:**
- ashfield_heights: 142, summer_hill: 49, queen_street: 17, victoria_square: 16
- murrell: 11, farleigh: 7, tintern: 6, moonagee: 6, holwood: 6

**Schema columns added:**
- `v2_heritage_type` (TEXT)
- `v2_heritage_element` (TEXT[])
- `v2_heritage_hca` (TEXT)

**Fix Script:** `scripts/fixes/DQ11_heritage_categorization.py`

### DQ-13: Leichhardt Uncategorized Topics (2025-11-29)
**Status:** ✅ FIXED
**Priority:** P1 (was)
**Problem:** 42% of Leichhardt provisions (1,242/2,962) had NULL v2_topic

**Root Cause:** Bug in `enrichment/extractors/layer_topic_tagger.py`
- Section 1 handler only used C marker extraction
- Many provisions lack C markers but have keyword matches
- Missing fallback: `or self._extract_topic_from_text(provision_text)`

**Fixes Applied:**
1. Fixed `layer_topic_tagger.py` - added keyword fallback for Section 1
2. Marked 124 Part A (Introduction) provisions as non-actionable
3. Re-classified 1,164 Part C Section 1 provisions

**Results:**
- Uncategorized: 42% → 10.1% (reduced by 32 percentage points)
- 878 provisions now have topics assigned
- Part A correctly marked non-actionable (procedural, not requirements)

**Fix Script:** `scripts/fixes/DQ13_leichhardt_fixes.py`

### DQ-14: Leichhardt PDF URL Coverage (2025-11-29)
**Status:** ✅ FIXED
**Priority:** P1 (was)
**Problem:** Only 26% of Leichhardt provisions had PDF page image URLs (vs 100% for Marrickville/Ashfield)

**Root Cause:** Multiple issues
1. `pdf_page_image_url` column was NULL, needed population from `pdf_page`
2. Folder mapping regex: "Section 1" matched before "Part G"
3. Part G offset: `pdf_page` has +100 offset, should use `page_number` column
4. Missing PNG files: pages 10, 21, 23, 24, 25, 35 not extracted

**Fixes Applied:**
1. `DQ14_leichhardt_pdf_urls.py` - Initial URL population (2,097 provisions)
2. `extract_missing_pdf_pages.py` - Extracted 115 missing pages using PyMuPDF
3. `DQ14b_fix_part_g_urls.py` - Fixed Part G using `page_number` (487 provisions)
4. `extract_missing_part_g.py` - Extracted 6 additional Part G pages
5. Uploaded all new PNG files to Cloudflare R2

**Results:**
| Metric | Before | After |
|--------|--------|-------|
| PDF URL coverage | 26% (773/2,962) | **100%** (2,838/2,838) |
| Part G coverage | 0% | 100% |
| Missing PNG files | 160 | 0 |

**Key Insight:** Part G has inconsistent offset pattern (pdf_page ≠ page_number).
Always use `page_number` column for Part G PDF URLs.

**Fix Scripts:** `scripts/fixes/DQ14_leichhardt_pdf_urls.py`, `scripts/fixes/DQ14b_fix_part_g_urls.py`

### DQ-15: Topic Case Inconsistency (2025-11-29)
**Status:** ✅ FIXED
**Priority:** P2 (was)
**Problem:** Leichhardt had duplicate topics differing only by case (e.g., `parking` vs `Parking`)

**Root Cause:** Inconsistent capitalization during topic extraction
- 17 topics affected: heritage, height, setbacks, parking, access, landscaping, trees, signage, waste, privacy, stormwater, fencing, flooding, contamination, safety, roofing, solar

**Fix Applied:**
1. Normalized all topics to Title Case
2. Fixed `building_form` → `Building Form`

**Results:**
- 845 provisions updated (725 case normalization + 120 building_form)
- All topics now use consistent Title Case
- Leichhardt topic distribution now accurate

**Fix Script:** `scripts/fixes/DQ15_normalize_topic_case.py`

### 50-Address Comprehensive Test (2025-11-29)
**Status:** ✅ ALL PASS
**Scope:** 50 representative addresses across all Inner West councils

**Test Results:**
| Council | Tests | Pass | Warn | Fail | Avg Provisions | Topic | PDF |
|---------|-------|------|------|------|----------------|-------|-----|
| Marrickville | 17 | 17 | 0 | 0 | 623 | 95% | 100% |
| Leichhardt | 17 | 17 | 0 | 0 | 2,790 | 90% | 100% |
| Ashfield | 16 | 16 | 0 | 0 | 1,502 | 93% | 100% |
| **TOTAL** | **50** | **50** | **0** | **0** | - | - | - |

**Zones Tested:**
- R2, R3 (residential)
- B1, B2, B4 (business)
- IN1, IN2 (industrial)

**Conclusion:** All 50 addresses return complete, accurate provision data with 100% PDF coverage.

### Two-Table Architecture Clarification (2025-12-01)
**Status:** DOCUMENTED

**Issue:** Previous sessions incorrectly assumed Leichhardt's 28% LLM coverage meant incomplete extraction.

**Reality:**
- LLM extraction is INTENTIONALLY SELECTIVE - only extracts actionable development controls
- 20-30% extraction rate is NORMAL - most DCP text is objectives, definitions, context
- Leichhardt Part C Section 1: 1,782 raw → 342 LLM (19%) is CORRECT
- Marrickville >100% is also correct - one paragraph can yield multiple requirements

**Coverage (verified 2025-12-01):**
- Ashfield: 791 LLM / 1,579 raw = 50%
- Marrickville: 1,338 LLM / 985 raw = 136%
- Leichhardt: 834 LLM / 2,989 raw = 28%

**DO NOT** assume low percentage means extraction needs to be re-run.

### DQ-16: Heritage Topic Fragmentation (2025-12-07)
**Status:** ✅ FIXED
**Priority:** P1 - HIGH (was)
**Problem:** Ashfield Heritage chapter provisions split across multiple topics in UI

**Evidence:**
- User sees: Heritage (187), Character (80), Fencing (22), Streetscape (22), etc.
- Reality: ALL 364 provisions are from Heritage chapter (part_name='Heritage')
- The `category` field (subject matter) is being used as `v2_topic` in API response

**Root Cause:**
In `queryHeritageFromDcpGeneralRequirements()` (for-property/route.ts:363):
```sql
INITCAP(REPLACE(category, '_', ' ')) as v2_topic
```
This maps `category` (e.g., 'character', 'fencing') to `v2_topic` instead of using 'Heritage'.

**Fix Applied (2025-12-07):**

1. **API change** (`for-property/route.ts`):
   - Changed: `CASE WHEN part_name = 'Heritage' THEN 'Heritage' ELSE ... END as v2_topic`
   - Added: `INITCAP(REPLACE(category, '_', ' ')) as v2_heritage_subcategory`
   - Fixed: Changed `part_name ILIKE '%Heritage%'` to exact match `part_name = 'Heritage'`
     (Excludes Leichhardt "Connections (Heritage and Transport)" which is NOT heritage)

2. **TypeScript types** (`ProvisionsByTopic.tsx`):
   - Added `v2_heritage_subcategory?: string` to Provision interface

3. **UI enhancement** (`ProvisionsByTopic.tsx`):
   - Added subcategory grouping within Heritage topic
   - Shows collapsible sections: Character (80), Fencing (22), Heritage (187), etc.

**Result:**
- Before: Heritage: 187, Character: 80, Fencing: 22 (separate topics)
- After: Heritage: 364 (consolidated with subcategory grouping)

**Also Fixed:**
- Leichhardt "Connections (Heritage and Transport)" no longer incorrectly included as heritage
- 78 provisions correctly excluded (they're about events/safety, not heritage)

### DQ-17: "Orphaned" Non-Heritage Provisions (2025-12-07)
**Status:** ✅ RESOLVED - NOT ORPHANED
**Priority:** N/A - Working as intended
**Initial Concern:** 1,072 provisions in `dcp_general_requirements` not returned by provisions UI

**Investigation (2025-12-07):**

Provisions by council not shown in main provisions UI:
- Leichhardt: 695 (83% of their 834 LLM provisions)
- Ashfield: 212 (27% of their 791)
- Marrickville: 69 (5% of their 1,338)

**Key Discovery: These ARE Used by Capacity API**

Tested `/api/capacity/calculate` in production - it queries `dcp_general_requirements` for:
- **Parking**: Returns clean data like "One car parking space is required per dwelling"
- **Setbacks**: Returns 8 structured setback values
- **Landscaping**: Queries this table (currently returns empty for Ashfield)

**Why Two Tables Exist (Intentional Architecture):**

| Table | Used By | Data Quality | Purpose |
|-------|---------|--------------|---------|
| `regulatory_provisions` | Provisions UI | Raw PDF text, OCR artifacts, verbose | Show full DCP context |
| `dcp_general_requirements` | Capacity API, Heritage UI | LLM-cleaned, distilled | Power calculations |

**Raw vs LLM Quality Comparison:**

LLM (capacity API):
> "One car parking space is required per dwelling"

Raw (provisions UI):
> "Parking requirement for restaurant $2 0 0 { \mathrm { m } } 2 - 1$ space per $4 0 \mathrm { m } 2$..."

The raw data has LaTeX artifacts and OCR noise. LLM extraction cleaned this into usable requirements.

**Conclusion:**
The "orphaned" provisions are NOT orphaned - they power the capacity calculator with clean data.
The two-table architecture is intentional separation of concerns:
- Raw table → provisions display (full context)
- LLM table → calculations (clean values)

**No action required.** Architecture is correct.

### DQ-18: Marrickville pdf_page Field (2026-01-12)
**Status:** ✅ FIXED
**Priority:** P1 (was)

**Understanding:**
- Marrickville DCP was split into 19+ separate PDF files by section
- Each section PDF starts at page 1 (relative numbering)
- `pdf_page` stores the relative page within each section (CORRECT)
- `pdf_page_image_url` contains absolute page numbers across combined document
- Images load correctly from URL; labels show relative page within section

**Incorrect "Fix" Applied & Reverted (2026-01-12):**
1. `DQ18_fix_marrickville_page_numbers.py` incorrectly changed pdf_page to absolute numbers
2. This broke the UI labels (e.g., "Page 5" instead of "Page 1" for first page of Landscaping section)
3. `DQ18_revert_marrickville_pages.py` restored correct relative page numbers
4. Formula: `relative_page = url_page - section_min_page + 1`
5. 1,671 provisions corrected back to relative numbering

**Part 4.1 Specific Issue (2026-01-12):**
- Part 4.1 Zone-Specific provisions showed wrong page numbers (e.g., "Page 5" when PDF footer showed "Page 1")
- Root cause: URL filename truncation created two groups (`_4.1_Low_Density_Res` vs `_4.1_Low_Density_Resid`)
- Each group calculated separate min_url, giving wrong offsets for the truncated variant
- Additional issue: TOC pages (url pages 3-6) were included in min calculation, but actual content starts at page 7

**Fix Applied:**
1. `DQ18_fix_by_section_number.py` - Groups by section number (e.g., "4_1") instead of URL filename
2. `DQ18_fix_exclude_toc.py` - Excludes TOC pages (containing "........") from min calculation
3. `DQ18_fix_part41_direct.py` - Direct fix using confirmed data: page_7.png = PDF page 1
   - MIN_CONTENT_URL = 7 (user confirmed from PDF footer inspection)
   - TOC pages (url 3-6) set to pdf_page = 1
   - Content pages: `pdf_page = url_page - 7 + 1`

**Verification:**
- url_page=7 → pdf_page=1 ✓
- UI now shows correct page numbers matching PDF footers

**Fix Scripts:** `scripts/fixes/DQ18_*.py`

**Current State:**
- `pdf_page` = relative page within each section PDF (correct for display)
- Images load from URL with absolute pages (correct rendering)
- UI shows "View Part 2 Page 1" for first page of each section (correct)

### DQ-25: Transport & Infrastructure sepp_structured_requirements Empty (2026-02-14)
**Status:** ⏳ BACKLOG
**Priority:** P2 — blocks classified road noise feature for certifiers

**Problem:** `sepp_structured_requirements` table has zero rows for `sepp_id = 'transport_infrastructure_2021'`. The UI transport section (`StateLevelControls.tsx` lines 658-672) is fully wired but never renders because the underlying data was never populated.

**What's blocking the feature:**
- `sepp-router.ts` adds `SEPP_TRANSPORT_INFRASTRUCTURE_2021` to every property unconditionally (line 126-128)
- `StateLevelControls` fetches `/api/sepp/structured-requirements` with `seppId = 'transport_infrastructure_2021'`
- API queries `sepp_structured_requirements WHERE sepp_id = 'transport_infrastructure_2021'` → empty → nothing renders

**What needs to go in this table:**
Three provision categories relevant to residential certifiers:
1. **Classified road corridor** — noise attenuation requirements for dwellings within X metres of classified roads (State Roads, RMS/TfNSW). Affects large % of inner-Sydney properties (Parramatta Rd, King St etc.). Most important for CDC certifiers.
2. **Rail corridor** — noise/vibration requirements near railway lines
3. **Airport obstacle limitation surfaces** — height controls near Sydney/Bankstown airports

**Source document:** `State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation` (2,733 provisions) — but v2_topic tagging is wrong (see DQ-24). Will need either:
- Manual curation of the specific classified road/rail/airport clauses into `sepp_structured_requirements`, OR
- Fix DQ-24 first (retag document), then build query-based lookup

**Triggering condition:** Should only show when Planning Portal API detects classified road corridor or rail corridor proximity — not for every property. Currently added unconditionally in sepp-router.ts (should be conditional).

**Do not fix until:** Classified road/rail corridor detection from Planning Portal is confirmed working for a test address on a classified road.

---

### DQ-24: Transport & Infrastructure SEPP v2_topic Retag (2026-02-14)
**Status:** ⏳ BACKLOG
**Priority:** P3 — No current production impact
**Document:** `State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation` (2,733 provisions)

**Problem:** Entire document tagged with DCP-style topic taxonomy (heritage, building_form, height, landscaping, waste, signage etc.) which is wrong for a state infrastructure instrument. Solar/wind turbine provisions (the main use case) are tagged `waste` instead of `solar`.

**Distribution of wrong tags:**
- (null): 1,724 (63%)
- heritage: 116, building_form: 110, height: 106, landscaping: 95, safety: 94, access: 87, waste: 83, signage: 59, stormwater: 47, trees: 41, fencing: 40, flooding: 38, parking: 33
- solar: 20 (only correct ones)

**Root cause:** DCP topic taxonomy applied to a SEPP document during an earlier tagging pass. DCP labels (setbacks, heritage, signage etc.) are meaningless for infrastructure development types.

**Current production impact:** ZERO — live app uses `sepp_structured_requirements` table for the transport section, not `regulatory_provisions`. Broken tags are never queried by the UI.

**Future impact:** Blocks solar provision browser — certifier filtering by Solar would see 0 actionable provisions.

**Fix required:**
1. Clear all v2_topic values for this document
2. Re-run classification with infrastructure-appropriate taxonomy: roads, rail, electricity/solar, water/stormwater, parking, community_infrastructure, general
3. Note: the 168-provision duplicate (`State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021___NSW_Legislation` with parentheses) also exists — may need cleanup

**Do not fix until:** Solar provision browser is being built.

---

### DQ-26: Marrickville Truncated pdf_page_image_url Stems (2026-03-04)
**Status:** ✅ FIXED
**Priority:** P1 (was)

**Problem:** Old Marrickville provisions (double-underscore document_id format from first extraction pass) had `pdf_page_image_url` pointing to truncated R2 image filenames (e.g., `Signs_and_Adv_page_5.png` instead of `Signs_and_Advertising_page_5.png`). New re-extraction provisions used full names matching actual R2 filenames. When old images were absent from R2, PDF link buttons showed broken images.

**Scope:** 57 chapters, 391 provisions. Heritage chapter (`8.0_Heritage`) correctly excluded — it has 244 new provisions confirming it's a valid complete chapter name, not a truncation.

**Root Cause:** First extraction pass used truncated PDF filenames (likely Windows path-length limit). Image files were uploaded to R2 with truncated names. Re-extraction used full filenames. Some old images were deleted/overwritten; others remain. For Landscaping chapter (first reported), old images were absent from R2.

**Fix Applied:**
```sql
-- Pattern: replace truncated stem with full stem, keep _page_N.png suffix
-- Example: Landscaping_an_page_N -> Landscaping_and_Open_Spaces_page_N
-- 57 UPDATE statements run in a single transaction, 391 total rows changed
```
Full-name images confirmed to exist in R2 (verified by working new provisions). Page numbers preserved exactly.

**Also fixed separately (2026-03-04):** The Landscaping chapter (14 provisions, first user-reported broken link) was fixed in the same session before this batch fix.

---

### DQ-27: Marrickville LaTeX Math Artefacts in provision_text (2026-03-04)
**Status:** ✅ FIXED
**Priority:** P1 (was)

**Problem:** 36 Marrickville provisions contained raw LaTeX math mode tokens from pdfplumber extraction. Example: "Contour lines and levels for sites in excess of 6 0 0 { \mathsf { m } } ^ { 2 }$" instead of "600m²".

**Patterns cleaned:**
- `\mathsf`, `\mathfrak`, `\mathtt` math font commands
- `{ \mathsf { m } } ^ { 2 }$` → `m²` (two variants: with and without outer `{ }`)
- `\mathsf { m m }` → `mm`, `\mathsf { p m }` → `pm`
- `\mathtt { x 0.6 }` → `x 0.6` (strip wrapper, keep content)
- `\star _ { \mathsf { N B } }` → `` (NB note markers)
- `{ , }` → `,` (LaTeX thousands separator)
- Trailing `$` delimiters
- Spaced digits: `6 0 0` → `600` (via lookbehind/lookahead patterns)

**Fix applied:** Python script + companion `preProcessReplacements` added to Marrickville config in `frontend-nextjs/lib/dcp-format-configs.ts` (safety net for future re-extractions).

**Script:** `scripts/fix_marrickville_latex.py` (gitignored, not committed to repo)

---

### Provision Text Formatting Enhancement (2026-01-12)
**Status:** ✅ IMPLEMENTED
**File:** `frontend-nextjs/lib/provision-text-formatter.ts`

**Issue:** Numbered lists (1. text 2. text 3. text) not being rendered as list items in provision display

**Fix Applied:**
Added numbered list detection to `splitInlineList()` function:
```typescript
// Pattern for numbered lists: "1. text 2. text 3. text"
const numberPattern = /(?:^|\s)(\d+)\.\s+/g;
const numberMatches = text.match(numberPattern);

if (numberMatches && numberMatches.length >= 2) {
  const parts = text.split(/(?=(?:^|\s)\d+\.\s+)/);
  const cleanParts = parts.map(p => p.trim()).filter(p => p.length > 0 && /^\d+\./.test(p));
  if (cleanParts.length >= 2) {
    return cleanParts;
  }
}
```

**Result:** Numbered lists now render as proper list items alongside roman numerals (i., ii.) and letters (a., b.)
