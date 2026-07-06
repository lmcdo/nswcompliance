# DCP Extraction — Architecture Overview (2026-07-01)

A plain-language + technical record of how NSW council DCP (Development Control Plan)
provisions are extracted and kept current. Written so it can be described later to a
teammate, investor, or in product docs. Companion decision record with the full
evidence: `~/.claude/plans/ce-ai-extraction-decision-2026-07.md`.

---

## The problem
Councils publish their DCPs as **PDFs**, and every council formats them differently —
watermarks, two-column layouts, image-heavy heritage chapters, inconsistent numbering.
The old approach hand-wrote **per-council parsing rules** (pdfplumber + regex). It does
not scale: a full session of tuning fixed 5 chapters across 2 councils and still
couldn't cleanly read the hardest one (a watermarked Woollahra chapter that came out as
**1 rule instead of 50**). With 128 NSW councils × dozens of chapters each, this is a
treadmill.

## The pivot
Stop hand-writing rules per council. Use **AI to read any layout**, keep a deterministic
signal for **detecting change**, and keep a **human** in the loop. Split the work by the
tool that's actually good at it:

```
  A council changes a PDF
        │
        ▼
  ① WATCHER  — is the change real? (deterministic)
        │        hashes the PDF's extracted TEXT; a re-save with identical wording
        │        is ignored, only a genuine text change passes
        ▼
  ② READER   — AI reads the changed PDF (Mistral)
        │        extracts clean provisions from any layout, no per-council config
        ▼
  ③ GUARDS   — did the AI drop sections or truncate a rule? → flag, don't use
        │
        ▼
  ④ HUMAN    — approves real changes in /internal/dcp-review before anything goes live
        │
        ▼
  regulatory_provisions (live)
```

The AI's job is **reading**. The watcher's job is **detecting change**. The human's job
is **approving**. Nothing re-reads unchanged documents; nothing publishes itself.

## Why each piece is what it is (the evidence)
- **Reader = Mistral** (`mistral-small-latest`, `temperature=0`). Read the watermarked
  Woollahra chapter cleanly for **~$0.04** (vs $0.63 on Claude Haiku, ~15× more).
  Haiku stays available via one env var (`AI_MODEL=haiku`).
- **DeepSeek rejected** — its API is **text-only** (tested: `400 unknown variant
  image_url`), so it can't read a PDF at all. Cheaper-but-can't-do-the-job.
- **Guards** — the live head-to-head showed *both* models err at the provision level
  (dropped whole sections; truncated a rule). Two AI-specific guards flag those:
  **coverage** (did it miss sections listed in the table of contents?) and **truncation**
  (is a rule cut off / suspiciously short?). Advisory only — they surface a chapter for
  human review, never block or auto-commit.
- **Watcher = text hash, NOT AI diff.** Measured 2026-07-01: asking the AI to re-read the
  *same* document twice produced **~89% different text** — so you cannot detect real
  changes by re-reading with AI and comparing. Instead the watcher hashes the PDF's
  **extracted text** (pdfplumber is deterministic — same file, same text), and compares a
  changed PDF against the previous version. This kills the re-export false alarm (a
  re-saved PDF has different bytes but identical text) while catching genuine edits.
- **Human approval** is required regardless — you are publishing planning rules; a machine
  read cannot go live unreviewed. This is standard practice in regulated document
  pipelines (banks, compliance firms): machine reads, human approves.

## What's built (this is live in code)
| PR | Piece |
|----|-------|
| #618–#620 | change-detection cadence + alerting contract + config-as-code crons |
| #621, #622 | false-negative guards (count-drop, schema) + SUSPECT Telegram |
| #623–#625 | scope + module-shipping fixes + TOC-driven extraction (interim) |
| **#626** | **AI extraction engine** — `scripts/ai_extractor.py`, drop-in behind `AI_EXTRACTION` |
| **#627** | **Mistral default + coverage/truncation guards** |
| **#628** | **deterministic content-change gate** — `scripts/pdf_text_hash.py` + r2_monitor |
| #632, #634 | section-code correctness (coverage guard + chunk-boundary code loss) |
| #635, #636, #639 | review UI: per-chapter bulk approve · source-PDF view · group-by-section + ⚠ flags |
| **#637** | **commit the *reviewed* text, not a re-read** (`dcp_commit_approved`) |
| **#641** | **amendment-safe commit** — `is_full_replace`; targeted amendments update only changed refs, never wipe unchanged rules |
| #643 | **AI was silently bypassed for page-range-configured councils** (ashfield/waverley ran regex) — now every council uses the AI |
| #644 | AI timeout resilience on large PDFs (300s + retry) + `--chapter` single-chapter retry |
| #645, #646 | review UI: true total / auto-load next 500 (no false "empty") · already-resolved isn't an error |

Key files: `scripts/ai_extractor.py` (reader), `scripts/pdf_text_hash.py` (watcher),
`scripts/dcp_extract_changed.py` (pipeline + guards + review-queue enqueue),
`scripts/dcp_commit_approved.py` (commit-on-approve), `frontend-nextjs/app/internal/dcp-review/` (human UI).

## How to turn it on (operational)
1. On the `dcp-extract-all` Railway service, set **`MISTRAL_API_KEY`** (value is currently
   only in the repo-root `.env`) and **`AI_EXTRACTION=1`**. Mistral is the default model,
   so `AI_MODEL` is optional.
2. Wait for the monitor image to rebuild (Railway auto-deploys on merge).
3. Run extraction on-demand for a council; output lands in `dcp_review_queue`; approve in
   `/internal/dcp-review`; approved becomes the new baseline.

**Do NOT** wire a blind recurring "re-extract everything and diff" loop — the AI's text
is non-deterministic, so that produces fake changes. Re-extract a chapter only when the
**watcher** says its text actually changed.

## Baseline vs amendment — the ongoing process (READ THIS)
The heavy work is a **one-time baseline per council**, not the steady state:

- **Baseline (once per council):** the *whole* DCP is read fresh → thousands of changes →
  a large human review. This is `is_full_replace=TRUE` (a full re-extraction). It's what
  the review sessions on leichhardt/ashfield are.
- **Amendment (ongoing, a few times a year):** a council edits its PDF → only the *changed*
  rules surface. `is_full_replace=FALSE`, so the commit **updates only the changed refs and
  leaves every unchanged rule live** (#641). A 3-rule amendment = 3 review items, not 2,300.

The ongoing loop, all built:
```
1. WATCHER  — hashes each council PDF's text on a schedule; a real edit flags the chapter   [#628]
2. READER   — AI re-reads only the flagged chapter
3. DIFF     — enqueues only the changed rules (is_full_replace=FALSE)                        [#641]
4. REVIEW   — a handful of items, ⚠-flagged if the guards fire; human approves
5. PUBLISH  — dcp_commit_approved --commit; reversible (old rows kept is_current=FALSE)
```

### Turning on hands-off monitoring (the last flip — NOT yet on)
The pieces exist but the schedules are off; today extraction is triggered manually. To make
it autonomous: (1) schedule the byte/text-hash monitor (`r2_monitor` / `pdf_text_hash`) so
it flags changed chapters; (2) run the reactive AI extraction on `needs_extraction=TRUE`
chapters (the no-`--all` path) on a cadence; (3) the flagged diffs land in `/internal/dcp-review`
as usual. **Do this only after baselining the councils you care about**, so the monitor only
ever sees small amendments (never a first full re-read via the wobbly AI-vs-AI diff).

## Status (2026-07-03)
- **Leichhardt: 18/18 sections live** on clean AI-reviewed rules (first full baseline).
- **Ashfield: 6/7 live**; `chapter-e1-heritage` held by one rejected row (see governance note).
- Extraction is **manual/on-demand** per council; the autonomous monitor is not yet switched on.

### Governance note — a rejected row holds the chapter
`dcp_commit_approved` will not commit a chapter that has ANY `rejected` row — a rejection
means "investigate the source" before any of it goes live. The review UI only lists
`pending` rows, so a rejected one currently can't be un-rejected from the screen (a known
gap); flip it back in the DB (status='approved' or 'pending') to release the chapter.

## What's left (optional)
- **Switch on the autonomous monitor** (the three steps above) — when you're ready.
- **Un-reject in the UI** — let a reviewer see/reverse a rejected row without a DB edit.
- **Tidy odd codes** — some appendices/manuals label rules oddly (`S1`, `1 O1`, `Control C2`);
  content is correct, labels are cosmetic. A prompt/normalisation pass would clean them.
- **Numeric layer link** — extract the structured setback numbers *from* the clean AI text
  (the two layers are still separate pipelines; see the coverage doc).

## One-line summary
From hand-written PDF rules that never scaled → a cheap, self-running system that reads
any council's PDFs with AI, detects real changes deterministically, checks its own work,
and always asks a human before anything counts.
