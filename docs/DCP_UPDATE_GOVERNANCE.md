# DCP Update Governance — Policy & Workflow

*Status: Active policy. Do not auto-commit provisions without following this process.*

---

## The Core Rule

**Automated detection and extraction to review. Human-gated commit to production.**

No provision goes live without a named human reviewing the extraction output and explicitly approving it. This is non-negotiable given the professional stakes.

---

## Why This Exists

Verify serves town planners, architects, and building certifiers preparing DA submissions. They cite provisions by page number in legal documents lodged with council. A wrong provision — stale, mis-extracted, or missed — causes:

- DA lodged against incorrect controls → council rejection → redesign + delay ($5k–$50k+)
- Design signed off against wrong setback → construction non-compliance → stop-work order
- Superseded provision cited professionally → professional liability claim

The product's precision is its value proposition. That makes data accuracy a liability exposure, not just a quality concern. Disclaimers do not cover a tool that actively presents source citations and positions as "design compliant from the start."

---

## The Approved Workflow

```
Monday 02:00 UTC
  └─ Railway cron `monitor-dcp`   (was a GitHub Actions workflow; deleted #506)
       └─ r2_monitor.py
            ├─ HEAD request + SHA-256 hash check per chapter
            ├─ Content-Length + ETag must BOTH match to skip download
            └─ On change: upload new PDF to R2, set needs_extraction=TRUE

  ⚠ NOT AUTOMATIC. The auto-trigger was deleted in #506 and nothing replaced
     it; a detected change waits for someone to run this by hand:
  └─ dcp_extract_changed.py --review   (manual, local)
            ├─ Extraction runs IN MEMORY — no DB writes
            ├─ Provision count gate: aborts if new count < 75% of previous
            ├─ Minimum sections gate: aborts if < 5 sections extracted
            ├─ Writes human-readable review file to reviews/
            └─ Review file uploaded as GitHub Actions artifact (14 day retention)

  └─ Telegram: "DCP Review ready — [council] [chapter] — download artifact"

  └─ YOU: Download artifact → inspect review file (5–15 min per chapter)
       Check:
         ✓ Section count reasonable vs previous extraction?
         ✓ Section titles recognisable (not garbled text)?
         ✓ Sample provisions read like real DCP text?
         ✓ No [ABORT] or [WARN] lines?

  └─ If satisfied: Actions → "DCP Commit Reviewed Provisions"
       → council = [council name]
       → confirmed = CONFIRM   ← must type this explicitly
       → Commits provisions to production DB
       → Soft-deletes old provisions (incl. legacy NULL-keyed)
       → Runs enrichment pipeline (actionability, layer, applicability)
       → Telegram: "DCP Committed to production — approved by [you]"
```

---

## What Happens If You Don't Review

- A council re-publishes a chapter as a scanned PDF → pdfplumber extracts garbage → garbage provisions served as current
- A council restructures a chapter → section count drops 60% → missing provisions served silently as complete
- A council URL changes → old provisions stay live indefinitely, presented as current

All three happened to other property compliance tools. None are hypothetical.

---

## Escalation: When NOT to Commit

Do not commit (investigate manually first) if any of the following appear in the review file:

| Signal | Meaning |
|---|---|
| Section count < 75% of previous | Scanned PDF, format change, or extraction failure |
| Section count < 5 | Almost certainly empty or image-only PDF |
| Provision text contains repeated garbage characters | OCR/encoding issue |
| Sanity gate fired (>40% chapters changed) | Council website restructure or false CDN positive |
| [ABORT] lines in extraction output | Quality gate caught something — read why |
| Chapter titles don't match DCP structure | Wrong PDF, section detection failure |

In these cases: leave `needs_extraction=TRUE`, investigate the PDF manually, contact council if needed, and re-extract once the source is confirmed good.

---

## Monitoring Alerts You Will Receive

| Alert | Meaning | Action |
|---|---|---|
| "DCP Monitor: N chapters changed" | PDF hash change detected | Wait for review artifact |
| "DCP Review ready" | Review file generated | Download and inspect |
| "DCP Committed to production" | Provisions live | No action needed |
| "DCP Monitor ERROR: N chapters failed" | Download failures | Check council URLs |
| "DCP Watchdog alert — stuck chapters" | needs_extraction=TRUE >25h | Manual investigation |
| "DCP Monitor: no changes (N chapters)" | Weekly clean run | No action needed |

The weekly "no changes" message is intentional — it confirms the pipeline ran, not just silence.

---

## Manual Operations Reference

### Force re-check all chapters (bypass Content-Length/ETag skip)
```
Actions → DCP Chapter Monitor → Run workflow → force=true
```

### Check specific council only
```
Actions → DCP Chapter Monitor → Run workflow → council=inner_west
```

### Dry-run extraction (no R2 uploads, no DB writes)
```
Actions → DCP Chapter Extraction → Run workflow → dry_run=true
```

### Commit after review
```
Actions → DCP Commit Reviewed Provisions → Run workflow
  council = [council name]
  confirmed = CONFIRM
```

### Check for stuck chapters manually
```
Actions → DCP Watchdog → Run workflow
```

---

## Effort Reality Check

At current scale (3 councils, ~113 chapters), DCP amendments are infrequent — typically quarterly or annually per council. Realistic review workload:

- Minor amendment (1–3 chapters changed): 15–20 minutes total
- Major review (5–10 chapters): 45–60 minutes total
- Comprehensive DCP overhaul: 2–3 hours (rare, every few years)

This is the correct tradeoff for a tool that professionals use for DA submissions.

---

## How this actually runs now

⚠ **The GitHub Actions workflows named here were DELETED in #506.** Only
`gates` and `main-red-alarm` exist. This table described them as live
infrastructure for months; corrected 2026-08-12 (DQ-55).

| Step | Where it runs now | Cadence |
|---|---|---|
| Detect PDF changes, upload to R2 | Railway cron `monitor-dcp` | Weekly Mon 02:00 UTC |
| Alert on stuck/failing chapters | Railway cron `monitor-watchdog` | Weekly Wed 10:00 UTC |
| Extract to review | `scripts/dcp_extract_changed.py` | **Manual, local — nothing schedules it** |
| Commit reviewed provisions | `scripts/dcp_commit_approved.py` | **Manual, local** |

See `docs/RAILWAY_MONITORS.md` for the full migration record.

---

*Policy established: 2026-03-18*
*Applies to: all councils in dcp_chapter_registry*
