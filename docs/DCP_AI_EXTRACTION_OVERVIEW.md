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

## What's left (optional, scoped)
- **Review-UI upgrades** (scoped in the decision doc, not built): show the source PDF page
  next to each change (reuse `PdfImageModal`, populate `dcp_review_queue.crop_url`); let a
  reviewer edit a provision's text; capture correction notes. Makes approving faster and
  more defensible; not required to run.

## One-line summary
From hand-written PDF rules that never scaled → a cheap, self-running system that reads
any council's PDFs with AI, detects real changes deterministically, checks its own work,
and always asks a human before anything counts.
