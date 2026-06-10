# Worked Example — Ku-ring-gai DCP Change Detection (June 2026)

**Purpose:** This document walks through a real change detection event to demonstrate the system's end-to-end operation: detection, extraction, comparison, decision, and resolution.

---

## Background

Ku-ring-gai Council publishes its Development Control Plan as individual chapter PDFs on its website. The system monitors 16 active chapters covering residential development, parking, signage, trees, heritage, and more.

The system tracks 53 structured control values for Ku-ring-gai, including setbacks, height limits, floor area ratios, and parking rates, extracted from these chapter PDFs.

---

## Timeline of events

### 1. Change detected — 8 June 2026, 04:55 UTC

The scheduled monitor checked all 16 Ku-ring-gai chapter URLs. Every chapter returned a different SHA-256 hash from the stored value.

```
Chapter: section-a-part-4-rfb-mixed-use
  Old hash: a3f7c2e1...
  New hash: 8b4d91f0...
  → needs_extraction = TRUE
```

This repeated for all 16 chapters. The system flagged all 16 for re-extraction.

**What this tells us:** Ku-ring-gai republished their entire DCP. This is common when councils consolidate amendments — the content may or may not have changed, but the PDF files are regenerated.

### 2. Extraction — 8 June 2026, 08:47–08:55 UTC

The extraction pipeline processed all 16 chapters:

- Downloaded each PDF from Cloudflare R2 (where the monitor had already uploaded the new versions)
- Extracted provisions using pdfplumber with Ku-ring-gai's two-column layout configuration (Objectives | Controls format)
- Total: 291 provisions extracted across 16 chapters
- Extraction grade: A (88.4% — clean extraction, minimal artifacts)

### 3. Comparison — per-chapter diff results

For each chapter, the system compared the newly extracted provisions against the existing database provisions.

**Representative results:**

| Chapter | Unchanged | Changed | Added | Removed | Numeric changes |
|---------|-----------|---------|-------|---------|-----------------|
| Part 4 — Residential flat buildings | 24 | 2 | 0 | 0 | 0 |
| Part 4.1 — Secondary dwellings | 11 | 0 | 0 | 0 | 0 |
| Part 5 — Dual occupancy | 18 | 1 | 0 | 0 | 0 |
| Part 6 — Dwelling houses | 15 | 0 | 0 | 0 | 0 |
| Part 7 — Residential flat buildings | 22 | 3 | 0 | 0 | 0 |
| Part 8 — Mixed use | 19 | 1 | 0 | 0 | 0 |
| Part 22 — Parking | 31 | 2 | 0 | 0 | 0 |

**Key finding: zero numeric changes across all 16 chapters.**

The "changed" provisions had text differences only — minor rewording, punctuation changes, or pagination shifts. No setback values, height limits, floor areas, or parking rates changed.

### 4. Decision — smart flagging

Because no provisions had numeric changes (`has_numeric_change = False` for all changed provisions), the system applied the **auto-verify** path:

```
[CONTROLS] Auto-verified 53 rows (text_only_change)
```

All 53 structured control values for Ku-ring-gai were confirmed as still accurate. Their `last_verified_at` timestamps were updated to the current date. No alert was sent.

### 5. What would have happened without smart flagging

Before this improvement, the system applied blanket flagging — every chapter change triggered `needs_review = TRUE` on all linked control rows, regardless of whether values actually changed.

| Metric | Old behaviour | New behaviour |
|--------|--------------|---------------|
| Rows flagged for review | 53 | 0 |
| Alert sent | Yes — "53 control rows need review" | No — auto-verified |
| Manual work required | Open each chapter PDF, compare every control value | None |
| Time to resolve | ~2 hours manual verification | 0 (automatic) |
| Risk of alert fatigue | High — repeated false alarms erode trust | Low — alerts only fire on genuine value changes |

### 6. What would happen if values HAD changed

If Part 5 (Dual occupancy) had contained a genuine numeric change — say, the rear setback changed from 6m to 4.5m — the system would have:

1. Detected `has_numeric_change = True` on that provision
2. Flagged all linked control rows with `review_reason = 'numeric_value_changed'`
3. Sent a **CRITICAL** alert: "N control rows have NUMERIC VALUE CHANGES: ku_ring_gai: N rows (section-a-part-5-dual-occupancy)"
4. Required human verification before clearing the flag

The auto-verify path only activates when zero numeric changes are detected. Any single numeric change triggers the full review workflow.

---

## Evidence chain for this event

An auditor can independently verify every step:

| Step | Evidence | Location |
|------|----------|----------|
| PDF changed | `dcp_chapter_registry.content_hash` vs `provisions_extracted_from_hash` | Database query |
| Old PDF preserved | `source-pdfs/dcps/ku_ring_gai/v1.1-baseline/` | Cloudflare R2 bucket |
| New PDF preserved | `source-pdfs/dcps/ku_ring_gai/v1.2-2026-06-08/` | Cloudflare R2 bucket |
| Extraction output | `reviews/ku_ring_gai_20260608_1842.txt` (3,910 lines) | Repository `/reviews/` directory |
| Provision-level diff | `provision_changes` table, filtered by `council = 'ku_ring_gai'` | Database query |
| Control verification | `dcp_setback_controls.last_verified_at` = 2026-06-08 | Database query |
| No numeric changes | `provision_changes.has_numeric_change = FALSE` for all rows | Database query |

### Sample verification query

```sql
-- Show all Ku-ring-gai provision changes with numeric change flag
SELECT chapter_key, change_type, has_numeric_change,
       left(old_text, 80) as old_excerpt,
       left(new_text, 80) as new_excerpt
FROM provision_changes
WHERE council = 'ku_ring_gai'
ORDER BY changed_at DESC;
```

---

## What this demonstrates

1. **Completeness** — the system detected changes across all 16 chapters within hours of publication
2. **Accuracy** — the extraction pipeline correctly identified which provisions changed and which did not
3. **Precision** — numeric change detection distinguished formatting changes from value changes, eliminating 53 false alarm rows
4. **Traceability** — every step is recorded with timestamps, hashes, and full text, enabling independent verification
5. **Proportionality** — the system responds to the nature of the change, not just the fact of change. Cosmetic republishes are verified automatically; genuine value changes require human review
