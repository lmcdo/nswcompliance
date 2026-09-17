# Why DCP extraction keeps recurring — and the durable fix (2026-07-29, extended 2026-08-01)

Written after a full-day session that re-fixed CoS / Ashfield / Leichhardt / Marrickville /
Ku-ring-gai *again*. The point of this doc is to end the loop, not add to it.

## The uncomfortable finding: this is an IMPLEMENTATION problem, not a knowledge problem

Every failure hit this session is **already diagnosed** in
`docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md` (June 2026). That doc's own words:
*"You already designed roughly the right pipeline. The problem is half of it was deleted
and the recurring failure modes were never structurally solved."*

Proof — this session's pain mapped to that doc's already-listed recurring modes:

| This session (2026-07-29) | Already documented as | 
|---|---|
| Ashfield 49 HCAs silently `is_current=false`, served nothing for months | "silent drop keeps the stale value live — high-liability trap" (§3.5) |
| My `LIKE '%…%'` wrongly deactivated 1,125 rows (reverted) | "over-aggressive gates once wiped 1,592 Leichhardt provisions" (pain #5) |
| Whole session = hand re-keying orphans, part by part | "manual reconciliation / review bottleneck" (pain #8) |
| Page-based re-key only reproduced 615/1020 rows | "key by (council, chapter, clause), NEVER by page/bbox" (§3.2) — we key by page, so re-extraction can't reproduce it |
| Two-column interleave dropped whole sections | "every council needs hand-tuned two-column configs; doesn't generalize" (pain #4) |
| v1.2 amendment never re-extracted, `needs_extraction` wrongly False | "ETag/hash logic broken; `content_hash != provisions_extracted_from_hash` is the precise unused signal" (§1) |
| Word-coverage said 98% while clauses were missing | "schema-validate every provision before commit… blocks silent under-extraction" (§4 Phase 1) — never built |

**Nothing here is new. The diagnosis has been stable for a year. What's missing is that the
fixes are applied to the DATA (patch the rows) instead of the SYSTEM (codify a reproducible
build), so the next re-extraction wipes the patch and the same hand-work recurs.**

## The single root cause of the churn

The corpus is treated as a **destination** (rows you hand-edit) instead of a **reproducible
build from source** (rows a versioned recipe regenerates). Concretely, three couplings make
every re-extraction destructive, which is why we avoid re-extracting, which is why bad text
lingers, which is why we hand-patch:

1. **Keying is manual, not derived.** `v2_precinct_id` was set by one-off analysis (text
   location + per-part duplication), so it lives only in the rows — a re-extraction nulls it.
   Fix: keying is a **deterministic pipeline pass** (derive Part/precinct from a committed rule:
   page-range, footer key, document id, or HCA name) that re-runs automatically after extraction.
2. **Layers are entangled.** raw-text / enrichment (topic·layer·dev-type) / keying are one
   write; re-doing one nukes the others. Fix: **three decoupled idempotent passes** keyed off a
   stable clause identity, each re-derivable.
3. **Identity is positional.** Keyed by page/bbox, so any re-layout breaks the match. Fix:
   **clause identity = (council, chapter, clause-ref)** — the RECAP/Open States standard.

Fix those three and re-extraction becomes SAFE and IDEMPOTENT: change the source, re-run the
recipe, keying+enrichment re-derive, verification gates it. The hand-work disappears.

## The durable fix (already planned as Phase 0+1 — "do regardless")

Not new work to design — work to *execute*, from the June plan:
- **Schema-validate before commit** (clause format, units present, numeric ranges, per-doc
  row-count bounds). Blocks silent under-extraction — would have stopped the 49-HCA drop.
- **Deterministic clause-identity keys** + **keying as a re-runnable derivation pass** (not
  manual). Makes re-extraction non-destructive — removes the reason we avoid it.
- **Fail-closed staleness:** `content_hash != provisions_extracted_from_hash` marks a chapter
  NOT-current until a *verified* build clears it; the flag can't self-clear (the exact
  Ashfield-heritage bug).
- **Never silent-drop:** a net content drop KEEPS the old rows current until a human approves
  the replacement (already half-enforced by the `count_drop` gate; make it universal).
- **Verification at the altitude of the promise, as a standing gate:** the clause+number
  semantic sweep (built this session, wf_cf93d319-54f) becomes per-chapter CI, not a one-off.
  Word-coverage is a proxy that hides exactly the errors that matter — retire it as an
  acceptance metric.
- **Layout preflight before parse** (built this session, PR #844) + **geometric columnar
  reader** (PR #844) — the structural cure for pain #4; extends to Phase-2 structure-aware
  extraction (Docling/Azure Layout) for the hard councils.

## Portable playbook — for ANY PDF-extraction job (the 12-month lesson, domain-agnostic)

1. **Treat the corpus as a reproducible build, never a hand-edited destination.** Every
   document has a committed, idempotent recipe (source URL+hash, layout mode, split config,
   derivation rules). Re-running reproduces the rows exactly. If a fix can't be expressed as a
   recipe change, it will be lost on the next run — don't apply it to the rows.
2. **Stable identity keys, never positional.** Key records by their semantic identity
   (clause/section/id), never by page/bbox/row-order. Positional keys break on every re-layout.
3. **Separate raw-extract / enrich / key into decoupled idempotent passes.** Re-running one
   must not destroy the others.
4. **Preflight the layout before you parse.** Detect two-column / rotated / scanned / empty
   layers up front and route (columnar read / OCR / structure-aware) — never blind-parse.
5. **Verify at the altitude of the deliverable, and make it a gate.** If the promise is "the
   exact number," verify the number against source — not a proxy like word-coverage. A chapter
   is not "done" until it passes; the gate blocks the commit.
6. **Fail loud, fail closed, never silent-drop.** The expensive error is the silent one. A
   detected change or a content drop must KEEP the last-good state live and escalate to a human
   — never quietly supersede with something worse.
7. **Provenance on every value.** Source page + hash + extraction strategy + effective date, so
   any served value is traceable and any staleness is computable.

## Decision this doc forces

**Stop re-planning and stop hand-re-extracting.** Today's manual re-key of chapter-D would have
been the anti-pattern (page-based re-key reproduces only 60%). The next unit of work should be
the smallest structural piece that ends the churn: **the config-driven keying-derivation pass +
schema-gate**, so re-extraction stops being destructive. Then the deferred re-extractions
(CoS S5, Marrickville, Ashfield) run through it safely, keying re-derives, the semantic gate
verifies — once — and stays enforced.

Related: `docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md` (the standing plan — execute Phase 0+1),
`data/cos_precincts/EXTRACTION_REMEDIATION_PLAN_2026-07-29.md` (the 3-cause list),
memory `project-ashfield-heritage-hca-drop-2026-07`.

---

# PART 2 — the numeric-controls layer (added 2026-08-01)

Part 1 above concerns the **corpus** — the 55,696 rule-text chunks. This part concerns the
**numeric controls** — the 1,069 extracted numbers. They failed differently and the lessons do
not overlap, so they are kept separate. (Table names are given in the rules below where they
matter.)

**Why this part exists:** every one of those 1,069 numbers was, for the first time, checked
against the sentence it was extracted from. ~93% held up. The failures that didn't are all
instances of one thing, and it's a different thing to Part 1's churn problem.

## The one pattern behind every controls failure

Evidence, all verified against source PDFs on 2026-08-01:

| What was stored | What the source actually said |
|---|---|
| Camden 692 — front setback 4.0 m | a **driveway crossover width** (p.P4-20) |
| Cumberland 31/32 — front setback 4.0 / 5.5 m | **secondary frontage** and **garage** setbacks (Table 1, p.B8) |
| Camden 690 — front setback 3.5 m | the **exception** ("fronting open space"), not the 4.5/6.5/10 m rule |
| Cumberland 1119 — POS 24 m² | **50 m² for lots >451 m², 30 m² for ≤450 m²** — a tiered control |
| Waverley 631/632 — landscaping 10% | correct, but a **two-clause derivation** (20% site × 50% deep soil); only clause 2 was stored |
| City of Sydney 883/884/885 — setbacks 0 / 0–0.9 / 3–8 m | clause 4.1.2 contains **no numbers at all** |
| Camden — front setback | **no row exists** for the actual control |

**The number survived. The context that makes the number mean something did not.**

A planning control is not a number. It is a bundle — *value + which control + when it applies +
under what condition + where it came from*. The pipeline preserved the value and degraded
everything else into free text or lost it outright.

## Six rules for extracting numeric controls

1. **Extract the tuple, never the number.** The control-type label must come from the *same
   structural position* as the value — same table cell, same row. When label and value are
   inferred by separate steps they drift apart: that is the 26 live rows serving a
   secondary-street setback as the primary front setback across 10+ councils. This is an argument
   for **table-aware** extraction specifically, not merely better text OCR.

2. **Provenance must be sufficient to RE-VERIFY, not just to cite.** `source_text` was specified
   in migration 031 as a "≤250 char snippet … for citation" and is now load-bearing evidence.
   ~27 rows are truncated at a hard 400-char limit mid-word, which both flagged a correct row
   (Cumberland 30, rear 8 m) and let a row pass on luck (Cumberland 28 — "6m" happened to survive
   the cut). Store the full clause, or a precise retrievable pointer (document + page + offsets).
   *Sharpens Part 1 playbook item 7.*

   **2b. A CORRECTION must update the evidence, not just the value.** Demonstrated the same day:
   Camden 690 was corrected from 3.5 m (the "fronting open space" exception) to 4.5 m (the actual
   Table 4-2 rule), and the standing gate immediately failed it — because `source_text` still held
   the quote supporting 3.5. The row now had the right number and the wrong evidence, which is a
   *different* defect to the one just fixed and arguably a worse one: it looks verified.
   Any write that changes a value must carry the quote that supports the new value, in the same
   transaction. The gate catching this within minutes is the argument for having it.

3. **NULL is a legitimate value. A guess is not.** Three separate failure modes — the invented
   Sydney setbacks, 28 self-declared "Assumed standard NSW POS min" placeholders, and zones
   filtered to `ALL` — all come from a system that cannot say "I don't know."
   `services/extracted_data_integrity.py::assert_clean_row` already encodes the doctrine
   ("store NULL — rule exists, value unknown — rather than a guess"). The extractor must too.

4. **One control can hold many values, and the schema must record WHY.** Tiered by lot size,
   varied by zone, different above ground floor. Flattening to a single value destroys
   information that cannot be recovered from the row. Structured discriminator columns — never
   prose in a `condition` field. (The read-side consequence is documented separately in
   `~/.claude/plans/ce-dcp-condition-structuring-2026-08.md`.)

5. **Completeness is a SEPARATE check from correctness.** Camden's missing front setback passed
   every correctness check ever run, because the row does not exist. Correctness checks can only
   examine rows that are present. Add per-`(council, control_type)` coverage assertions: *if we
   captured exceptions, where is the rule?*

6. **Derive keys, never pattern-match prose.** Zone codes are lexically identical to chapter
   numbers (`B3` the zone vs `Part B3` the chapter). Three separate regexes were fooled during
   this work, and the DQ-33 matcher missed 9,854 rows keying off `4.1` while document ids used
   `part4_s1_low_density`. Where a structural identity exists, use it.

## The structural fix for imports — the biggest single item

**Controls were extracted from the PDFs independently of the corpus.** Same source documents, two
separate passes, no shared identity. Consequences, all measured:

- Only **42 of 1,069** controls can ever be linked to a provision — a ceiling, not a matching
  problem.
- **14 of 30** control-bearing councils have **zero** provisions ingested. Six of the nine
  councils holding truncated rows are among them, so the severed text exists nowhere in the
  database and can only be recovered from the PDF.

**One ingestion pass should emit both** — text chunks and extracted numbers, linked at creation.
Then every control carries a `provision_id` for free, the full clause is always retrievable, and
truncation stops mattering because the snippet becomes a pointer rather than the evidence itself.

That single change dissolves the truncation problem, the link ceiling, and most of the
re-verification cost simultaneously.

## Onboarding sequence for a new council

Waiting until the checks existed was the right call. Per council, from now:

1. **Ingest text and extract numbers in one linked pass** (above).
2. **Run the gates immediately** — zone validity (`scripts/validate_zone_code_validity.py`),
   source-value check, control-type consistency, coverage.
3. **Human-adjudicate the flagged rows before the council goes live** — that is what
   `/internal/setback-review` exists for.
4. **Record the flag rate.** It is the extraction-quality score, per council and per engine.

Step 4 is the quiet win: it converts "is this OCR engine better?" from a judgement into a
measurement. Run one chapter through each, count the flags.

## What NOT to conclude from this

- **Truncation is not an OCR artefact.** It is a fixed-width slice in the write path. Better OCR
  will not touch it. Better *table* extraction plausibly would reduce rule 1's class, because
  label-to-number binding is what is being lost — and that is now testable.
- **Do not widen `source_text` as a patch.** It is a citation field by design. Changing its
  purpose is a schema decision, not a fix.
- **A flagged row is not a defect.** Of 25 flagged, 12 were CORRECT — including four Waverley
  rows initially reported as the most serious finding, then retracted once the source was read.
  Evidence before verdict; partial quotes are common enough that asserting a defect from one is
  how this workstream repeatedly went wrong.

---

# PART 3 — When it happens again: symptoms, causes, what to run (added 2026-09-17)

Written after a session that hit six extraction problems in one day, each of which looked new and
none of which was. Find the symptom, confirm the cause with the check, then act. Every check here
is read-only unless it says otherwise.

## Symptom → cause → check

**1. Review rows contain doubled letters: "ttoo bbee aa ooff", "KKuu-- --", "ssttoorreeyy".**
The PDF draws some text twice (captions, running headers, and sometimes the rule itself), so the
text layer holds every glyph twice. `strip_garbled_header_lines` in `scripts/dcp_extract_changed.py`
handles it. **Rule: restore doubled text, never delete it, unless the line is a running header.**
Campbelltown's live rules include "rroooomm,, bbuutt oonnllyy iiff::" (room, but only if:) and
"33..55 mmeettrreess;;" (3.5 metres;), and on a fresh read of ku_ring_gai Part 8 the old cleaner
deleted a whole guidance paragraph ("Building facades are to be articulated into a series of
vertically proportioned bays...") and left "ttoo bbee aa ooff" in its place. A restored line is
dropped only when the whole line was doubled and it repeats in the same text or names the plan
("Ku-ring-gai Development Control Plan"). Numbers are un-doubled only next to a doubled word:
"1100 3300mm" and "AABB1122" are real. Before changing this code, run the old and new function over
every served provision and queued row and list the words each output loses — every lost word must
be a doubled fragment — and run both over a fresh extraction of a chapter with doubled text.
Tests: `tests/test_dcp_extraction_fidelity.py::TestDoubledTextIsRestoredNotDeleted`.
Not the cause: `pdfplumber`'s `dedupe_chars()` does not remove these (measured on the real pages).

**2. A re-read lost a large part of a section.** Woollahra B3 (2026-09-15): B3.5 went from 6,285
words to 2,780 and B3.8 from 9,860 to 4,595, with `fidelity_status = 'ok'` on every row. The number
check cannot see missing prose. Compare old and new word counts row by row before approving; a
row that halves is a failed reading, not an amendment. Do not approve — one rejected row holds the
whole chapter back until it is re-read.

**3. A council's PDF changed but its rules were never re-read.** Blacktown Part C: the February
2026 file was in R2 for months, `needs_extraction` was FALSE, nothing re-read it and nothing
alarmed. Check: `python scripts/dq_probe_live.py --id DQ-70`, then
`SELECT council, chapter_key FROM dcp_chapter_registry WHERE is_active AND content_hash <>
provisions_extracted_from_hash AND NOT needs_extraction` — every row there is stuck. Setting the
flag is a production write; take a backup first.

**4. A chapter will not go live although every good row is approved.**
`dcp_commit_approved.py` commits a chapter only when EVERY row for its current PDF is approved; one
rejected row blocks it, including rows the pipeline rejected by itself. Check:
`SELECT id, ref_number, review_reason FROM dcp_review_queue q JOIN dcp_chapter_registry r
ON r.council=q.council AND r.chapter_key=q.chapter_key AND r.is_active WHERE q.status='rejected'
AND q.source_content_hash = r.content_hash AND q.council = '<council>'`.
**Do not make those rejections non-blocking.** The `junk_ref` ones (keys ending `__2012`, `__R1`,
`__R2`) were real rules filed under a false heading: a table row or zone list starting "R1 General
Residential..." or a figure label "2012 Western Distributor" matched the section-heading pattern.
Committing past them would leave the live rule on old text while the chapter reads as current.
Fixed where it starts (2026-09-17): headings whose code is a bare year or `R` plus one digit are
skipped (`is_junk_heading_code`). A fresh `--review` re-read supersedes the old rejections, so re-read
the chapter after the fix is deployed. Other rejection types (for example a human's source-verification
rejection) must be resolved by a person.

**5. The file we hold is not the plan in force.** Waverley's copy is Amendment 0 (2022) while the
registry label said Amendment 5 and the council is on Amendment 6 (2026). Read the copy's own
amendment table, not the label. `dcp_plan_as_at.currency_date` records the EARLIEST date the
evidence proves the held version could have taken effect, never later (a later date can hide
staleness). Byte-compare our R2 copy with the file the council's plan page links today.

**6. The monitor watches a web address the council no longer links.** Penrith moved D2 and C10 to
new URLs; the old ones still serve the old files, so the monitor sees no change and would miss the
next amendment. Ku-ring-gai links `/v/5/` while the registry holds `/v/4/` (identical bytes today).
Check the council's plan page links against `dcp_chapter_registry.council_url`.

## Re-reading and committing, safely

- Re-read one chapter into the review queue (nothing goes live):
  `python scripts/dcp_extract_changed.py --review --council <c> --chapter <key>`.
  **Without `--review` it writes straight to the live rules.** The scheduled job uses `--review`.
- Commit approved chapters: `python scripts/dcp_commit_approved.py` (dry run lists what would go
  live), then `--commit`. Exit code 2 means "committed something", not failure.
- Two-column pages: `COUNCIL_COLUMN_CONFIGS` (councils with an Objectives|Controls header pair),
  `GEOMETRIC_COLUMN_COUNCILS` (gutter detection: ashfield, marrickville, city_of_sydney, hornsby),
  or `AI_EXTRACTION=1` with Sonnet (used for marrickville and woollahra, 2026-09). The geometric
  reader was tested on canterbury_bankstown and does not transfer. The `preflight_two_column`
  flag on a row is a pre-read page heuristic, not evidence the row is wrong.

## Gaps still open (2026-09-17), in the order that prevents most harm

1. **Nothing checks the words, only the numbers.** A gate that every word of a new reading is on
   its cited page would have caught problems 1 and 2 before review. The one-off version exists
   (the "text on page" classes in the 2026-09-16 review packet); it is not in the pipeline.
2. **Stuck chapters raise no alarm** (problem 3). A daily check should alert when a chapter's PDF
   changed and it has not been re-read within a few days.
3. ~~The pipeline's own junk-ref rejections block good chapters~~ — fixed at the heading stage 2026-09-17 (problem 4); re-read the affected chapters.
4. **The monitor does not follow the council's page** (problem 6).
