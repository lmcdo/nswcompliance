# DCP chapter measurement and the page-map gate

Phase A + C0 of `~/.claude/plans/ce-dcp-data-repair-PLAN-2026-09-12.md`.
Built 2026-09-12. Read this before changing any of the four signals, the parser,
or either baseline file.

---

## The defect this exists to stop

`ai_extractor.coverage_gap()` has been the completeness check since 2026-07-01
(#627). It has never been able to fire:

- its regex required dot leaders or double spacing before a trailing page number,
  and matched **0 of 10** real Waverley contents lines
- with fewer than `COVERAGE_MIN_TOC = 8` parsed codes it returned `(0.0, [])` —
  read by every caller as "judged, nothing missing"
- it only ran under `AI_EXTRACTION=1`, so pdfplumber chapters were never checked
- its verdict was never stored anywhere durable

So for two and a half months a completeness check reported "all present" every
time it failed to read the document, while Waverley was missing 11 parts and
carrying 54 mislabelled rows.

**Fail-closed is the whole point.** Every check here returns UNKNOWN rather than
PASS when it cannot run, and UNKNOWN is never folded into PASS.

---

## What runs

| | script | needs | blocks? |
|---|---|---|---|
| Measurement | `scripts/dcp_chapter_measure.py` | DB + R2 | no — measures and reports |
| Page-map gate | `scripts/dcp_page_map_gate.py` | DB + R2 | **yes**, check 1 only |
| Contents parser | `scripts/dcp_toc_parse.py` | nothing | pure |

```bash
python scripts/dcp_chapter_measure.py --sweep           # the 10 audited councils
python scripts/dcp_chapter_measure.py --sweep --councils all
python scripts/dcp_chapter_measure.py --rescore raw.json  # re-verdict, no download
python scripts/dcp_page_map_gate.py --check
python scripts/dcp_toc_parse.py                          # parser self-test
```

Exit codes match `r2_monitor` / `dcp_watchdog` / `check_council_completeness`:
`0` nothing worse than baseline, `2` findings, `1` the check itself broke.

---

## The four signals, and why four

Each is blind to what the others see.

| | signal | needs a PDF? | catches |
|---|---|---|---|
| 1 | contents list vs served codes | yes | whole sections **absent** |
| 2 | gaps in our own numbering | **no** | holes, e.g. starts at 4.1.12 |
| 3 | page header vs stored part | yes | **mislabelled** content |
| 4 | text capture ratio | yes | hollow chapters |

**Signal 3 is the only one that catches Waverley's defect.** A code-presence check
calls part B15 "present" while its rows hold B17's text — the sub-section numbers
are read from the page and only the part label comes from the broken map.

**Signal 2 is the only one with 100% coverage**, because it reads our own data.
It is what makes "every chapter has a measured state" reachable at all.

### `measured` is not `clean`

`measured` is true when at least one signal **that could have failed** actually
ran. A chapter where every signal abstains is UNMEASURED, and UNMEASURED is never
folded into OK. This is a column in the ledger, not a convention, because the
entire reason this phase exists is that 42% of the corpus was reported fine while
unread.

---

## The contents parser

Widened from three formats to six, against text sampled from the chapters that
could not be read. Two shapes were **73 of the 113** unreadable chapters:

| council | shape | why the old parser failed |
|---|---|---|
| ku_ring_gai (34) | `14A.1 St Ives Local Centre Context` | code carries a **trailing letter** — the old regex read `14`, demanded a space, found `A` |
| canterbury_bankstown (39) | `Section 1 - Introduction ......` | a **prefix word**, an en dash, and leaders running off the line with **no page number** |
| leichhardt | `G13.1 ...` and `4.1. Desired ...` | a trailing dot on the code |
| waverley | `B16 Inter-War Buildings 143` | (already worked) |

The residue is **reason-coded**, not lumped into one unknown:

- `UNREADABLE` — a contents page announced itself and we still could not read it.
  **The only status that is a defect in the parser**, and the only one that should
  shrink as it improves.
- `TITLES_ONLY` — a real contents page listing titles and page numbers and no
  codes at all (ashfield chapter-b). A code-vs-code comparison cannot run.
- `NO_CONTENTS` — the document has none. For a cover, a map or a two-page chapter
  that is correct, not a fault.

### The confusable negatives are the load-bearing half

Every loosening raises the chance body prose parses as a contents page, and **a
fabricated contents list produces a fabricated "sections missing" finding** —
worse than the fail-open check it replaces, because it looks like evidence.

`2.1 Development must maintain significant views to the place of heritage.` has
the same shape as a contents entry. Three defences, all in
`tests/test_dcp_toc_parse.py`:

1. a contents title is a **noun phrase**; a control is a **sentence**. Sentences
   end in terminal punctuation and run long — both rejected. The test applies to
   the raw line as well as the captured title, so the guard does not depend on
   where the regex happens to put a trailing full stop.
2. entries carrying dot leaders or a page number skip test 1 — those markers
   appear on contents pages and nowhere else.
3. a two-tier page density gate: a page with a `CONTENTS` heading passes on fewer
   entries; a page without one must show more.

---

## The page-map gate (C0)

### There are 32 hardcoded page maps, not one

The plan records `COUNCIL_PAGE_RANGES['waverley']` as "the only such map in the
codebase". Measured 2026-09-12, there are **32**: `COUNCIL_CHAPTER_RANGES` holds
31 more (ashfield 7, ku_ring_gai 24). All three checks run over all 32.

### Check 1 blocks. Checks 2 and 3 do not.

**Check 1 — no range may point past the end of the PDF.** Arithmetic, so it
cannot be wrong, and `assert_map_usable()` raises `PageMapUnusable` in
`dcp_extract_changed` *before* extraction. Across all 32 maps, exactly **two**
fire:

| map | violation |
|---|---|
| `waverley` | F1–F5 map to 460–473 of a **448**-page PDF |
| `ku_ring_gai/section-a-part-9-non-residential` | `9c_16` maps to 34–35 of a **34**-page PDF |

The ku_ring_gai one is a **new finding** from this sweep, recorded nowhere before.

Two chapters, both genuinely broken, is what makes a hard block affordable — the
alternative the plan warns against is switching a fail-closed check on against 95
known-bad chapters and taking the corpus dark.

The check is placed **before** `extract_pdf_isolated`, not after it, even though
the page count is free afterwards: under `AI_EXTRACTION` the extraction it would
validate has already been paid for in API credit by then.

**Checks 2 and 3** need the running header a page carries, and most councils do
not carry one — they return `NO_HEADER_TRUTH`, which is not a pass. Where headers
exist they are ratcheted against `.claude/dcp_page_map_baseline.json`.

Check 2 reports **two** measures, because they disagree and conflating them is
how the plan came to record "22 of 33":

| measure | waverley | gated? |
|---|---|---|
| majority code on the range's pages is another part | **14 of 33** | yes |
| the range's first page is not where that part begins | **30 of 33** | reported only |

Neither the narrow `^[A-F]\d{1,2}$` regex the original probe used nor the wider
one in the gate reproduces 22 — both give 14 and 30. The finding is unchanged and
arguably worse; only the figure differs. Check 3's **54 of 263** reproduces
exactly.

The start-shift measure is not gated because a one-page shift is a real but minor
defect, and gating on it would make the ratchet fire constantly on documents that
are merely imperfectly mapped rather than broken.

Check 3 also carries a vocabulary guard: at or above 90% disagreement the two
sides are not the same kind of code. Without it, `C5` in `E2.2.4 C5 Control 5`
reads as part C5 and Woollahra looks 95% broken. It is not.

---

## The two baselines, and why they are not one

| file | gates | compared against |
|---|---|---|
| `.claude/dcp_page_map_baseline.json` | **yes** | this code against itself |
| `.claude/dcp_measurement_baseline.json` | reports only, for now | this code against itself |

**The frozen 2026-09-12 numbers are provenance and are never gated on.** They came
from one signal and a narrower parser. Gating the new numbers against them would
be wrong in both directions:

- widening the parser moves chapters out of "contents unreadable" into a real
  verdict, some of which are INCOMPLETE — that count rises because the
  *measurement* improved, not because the data got worse
- adding signals 2–4 means a chapter signal 1 called OK can now be found to have
  numbering holes or mislabelled rows — OK legitimately falls

A ratchet against those numbers would fail on exactly the work it exists to
protect, and the pressure would be to weaken the parser to keep the count down.

So `ratchet.per_council` starts **empty**. Every key reports `NO_BASELINE` — which
is not a pass, and says so — until a first four-signal run has been read and
recorded with `--record-baseline`. Three states, never two.

Ratchet keys are `NOT_OK` and `UNMEASURED`, not `INCOMPLETE`:

- `NOT_OK` — a chapter stopped being known-good. May not rise.
- `UNMEASURED` — a chapter stopped being measurable at all. May not rise.

`INCOMPLETE`, `GAPS`, `MISLABELLED`, `HOLLOW` and `listed_not_served` are reported
and **not** gated, because each moves when measurement improves.

---

## What the first run measured (2026-09-12, the 10 audited councils)

270 chapters. Compare the "unknown" row against the frozen baseline's 113: **that
is what Phase A was for.**

| | frozen (1 signal) | now (4 signals) |
|---|---|---|
| chapters | 270 | 270 |
| **could not be measured at all** | **113 (42%)** | **9 (3.3%)** |
| contents page unreadable | 113 | 13 |
| known-good (OK) | 9 | 8 |
| INCOMPLETE | 95 | 121 |
| listed sections not served | 984 | 1,023 |
| chapters with mislabelled rows | not measurable | 1 (54 rows) |
| hollow chapters | not measurable | 1 |
| **stores MORE text than its own PDF** | not measurable | **39** |

`INCOMPLETE` rose from 95 to 121 and `listed sections not served` from 984 to
1,023 **because the parser can now read 100 more chapters**, not because anything
got worse. This is exactly why the ratchet is on `NOT_OK`, not on `INCOMPLETE`.

### Two findings that need their own follow-up

**39 chapters store more text than their source PDF contains.** woollahra alone
is 18 of them (chapter-e1-parking-access is 3.3×, and 26 of its 27 chapters serve
rows whose `section_header` carries no parseable code at all). That combination —
text that is not in the registry PDF, and codes that do not match it — is
consistent with the rows having been extracted from a *different document* than
the one the registry now points at. woollahra is already under an open finding for
being sourced from repealed documents (`ce-HANDOFF-woollahra-repealed-2026-09-10`).
**That is a correlation, not a proven cause.** It is recorded, not acted on.

**9 chapters remain unmeasured** — marrickville 5, leichhardt 3, ku_ring_gai 1.
These are the residue: no contents page, too few codes to judge numbering, no
page-header truth, and too little text to judge capture. They are reason-coded in
the ledger rather than counted as clean.

---

## What is deliberately NOT done here

- **`parse_toc_entries` / `_TOC_LINE_RE` is untouched.** It is not only a
  diagnostic: for `TOC_DRIVEN_COUNCILS` (woollahra, leichhardt) it drives
  extraction via `build_toc_ranges` → `extract_by_page_ranges`. Widening it
  changes what those councils extract, and the standing rule is *nothing gets
  re-extracted until its chapter has a measured state*. A parser that both
  measures and changes what it measures cannot establish a baseline. Repointing
  extraction at `dcp_toc_parse` is Phase C, per council, after measurement.
  Only `ai_extractor.toc_codes_from_pdf` was repointed — it feeds a guard and
  never extraction.
- ~~No CI job.~~ **Both are wired (2026-09-12).** The earlier note here said CI
  had no R2 credentials. That was wrong: all four `R2_*` secrets exist in the
  repository; no *workflow* referenced them.
- **Nothing is re-extracted.** Waverley's map is still wrong; deleting it and
  deriving parts from the running header is C1, and the re-extraction needs API
  credit the account does not currently have.
- **Scope is the 10 audited councils by default.** The registry holds 525 active
  chapters across 19 councils, but 241 are city_of_sydney of which only **7**
  serve any rows. Folding 234 never-extracted chapters in would swamp the ratchet
  with a different problem. `--councils all` reports the wider picture.

---

## How this runs in CI

Two jobs, because one check cannot be both fast and authoritative.

| | where | how | runtime |
|---|---|---|---|
| every PR + push | `gates.yml` → schema-contract | `--check --from-ledger` | **2s** |
| nightly 20:00 UTC | `data-watch.yml` | `--check` (reads R2) | ~10 min |

**The PR job** reads `pdf_pages` from `dcp_chapter_measurement` — no downloads,
`DATABASE_URL` only. It exits 2 if a map has no ledger row at all: an unmeasured
map is not a passing map.

**Its limitation, stated plainly:** the page count is only as fresh as the last
measurement sweep. If a council republishes a shorter PDF and no sweep has run,
the PR job compares against the old count and misses it. That is the waverley
failure mode itself, which is why it is not left to this job alone.

**The nightly job** opens the real PDFs in R2 and is the authoritative check. It
lives in `data-watch` because this is the one check here that can drift *with no
commit* — a council amends a document and nothing in the repo changes. It is
wired into that workflow's alarm aggregation (step id `page_maps`, index 10 of
10); an unwired check that fails silently is this repo's recorded failure class.

The full check takes ~10 minutes because it downloads and opens 32 PDFs. That is
affordable nightly and not affordable on a pull request — the whole reason for
the split.

### A fail-open the CI work exposed

Adding `--from-ledger` surfaced a real defect in the ratchet. In ledger mode only
check 1 runs, so checks 2 and 3 produce no count. `summarise()` emitted **0** for
them, and the ratchet duly reported waverley going `22 → 0` and `54 → 0` as
**RATCHET DOWN (good)**. A check that could not run was scoring as a fix.

Fixed: a check whose status is UNKNOWN now contributes **no count at all**, and
`ratchet()` returns a fourth state — `not_measured` — which prints the baseline it
could not verify as `UNVERIFIED`. `--record-baseline` also merges rather than
overwrites, so a run that could not measure something cannot erase its floor.

---

## Corrections to the plan, found while building

1. **There are 32 hardcoded page maps, not 1.** `COUNCIL_CHAPTER_RANGES` holds 31
   more. Same defect class throughout.
2. **A second map already points past its PDF:**
   `ku_ring_gai/section-a-part-9-non-residential`, `9c_16` → 34–35 of 34 pages.
3. **The real contents formats are six, not three.** Two of the new ones
   (ku_ring_gai trailing-letter codes, canterbury_bankstown prefix words) are 73
   of the 113 unreadable chapters between them.
4. **"UNREADABLE" was doing two jobs.** A 1-page cover and a 92-page chapter whose
   contents page we failed to parse are both unknown, but only one is a parser
   defect. Now reason-coded.
5. **`parse_toc_entries` drives extraction**, so the measurement parser had to be
   a separate module — the plan implied one parser could serve both.
6. **`coverage_gap`'s verdict was not quite "never stored"** — it reaches
   `dcp_review_queue.suspect_reason` on pending rows. But those rows are deleted
   and refreshed on every extraction, and a chapter that extracts nothing leaves
   no row at all, so there is no durable per-chapter answer. The ledger is.
