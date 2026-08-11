# Waverley DCP 2022 — full-corpus fidelity sweep (current rows vs source pages)

**Run:** 2026-07-28. 28 Sonnet verifier agents over all 33 parts (498 currently-served rows, 470 source pages). Method: adversarial compare, per the /how-it-works methodology section. Calibration basis: on Part B9, Sonnet found a strict superset of Opus's findings at ~1/5 cost.

## Headline result

**Zero missing provisions and zero wrong regulatory values in served text.** Every objective/control on the source pages is present in the served rows, and no numeric control value (setback, height, rate, hour) was found altered. Findings are extraction *noise* and *addressing* defects, itemised below. Several agents verified page-by-page that trailing spans are annexures (wind tunnel study, CMP, colour tables, definitions) correctly not extracted as provisions.

## Findings by class (most severe first)

### 1. Ref collisions — HIGH (addressability, not content)
Distinct provisions share one `ref_number`, breaking citation deep-links/dedup keyed on ref:
- **B7**: `B7_7_2_objectives` reused by 5 different objective sets (ids 100919/100921/100923/100926/100928 = 7.2, 7.2.1, 7.2.2, 7.2.5, 7.2.6); `B7_7_2_controls` reused by 6 (100920/100922/100924/100925/100927/100929).
- **C2**: `C2_2_3_objectives` shared by 101081 (2.3.1 street setbacks) + 101083 (2.3.2 side/rear); `C2_2_3_controls` by 101082 + 101084.
- **E5**: `E5_5_4_objectives` shared by 4 rows (101269/101271/101273/101275 = 5.4.1–5.4.4); `E5_5_4_controls` by 4 (101270/101272/101274/101276).
- **E2**: `E2_2_1_objectives` shared by 7 rows (2.1.1–2.1.7), `E2_2_1_controls` by 7, `E2_2_2_controls` by 3.
- **B5**: rows 100895–100901 (5.2.1–5.2.7) share section label + ref suffix `_B5_5_2_performance_criteria` — 7 subsections metadata-indistinguishable.
Fix: extend ref generation to one more nesting level where sub-subsections exist.

### 2. Phantom "banner tables" — systematic parser artifact (LOW-MED each, many rows)
The blue section-heading banner is mis-parsed as a 1-cell empty table appended to part-intro rows. Confirmed in: B1 (100840), B2 (100849), B8 (100943), B9 (100985), B10 (100988), B11 (100991), B12 (100996), B13 (100999), B17 (101029), C2 (101075), D1 (101134), D2 (101143), E2 (101219), E5 (101261, also page-mislabelled), E6 (101277, page-mislabelled). Fix: deterministic strip of empty single-cell tables whose header equals the part title.

### 3. Part-intro rows carrying misattached duplicate table blocks (MED)
Part-intro rows aggregate "Table N (Page X)" blocks that belong to (and are already correctly present in) later rows, sometimes with wrong page labels:
- B1 100840 (waste clause dup of 100848); B2 100849 (4 page-ranges dup of 100860/100863/100869); B3 100870 (Tables 2–15 dup of 100871/100872/100881); B8 100943 (Aboriginal-heritage prose + Table 8 dup of 100949/100951, page tags off by 1); B5 100889 (flood matrix dup of 100894); C2 101075 (empty/garbled dups of 101079/101084 tables); E7 101289 (species table dup of 101302). Fix: same strip pass — drop intro-row table bundles whose content exists verbatim in a dedicated row.

### 4. Footer/boilerplate bleed (LOW, systematic)
'W AVERLEY DEVELOPMENT CONTROL PLAN 2022' (split W) or footer+page-number embedded mid-text in most rows spanning page breaks (B2, B8 ~11 rows, B9–B13 ~6 rows, B17 101031, B5 section labels polluted). Fix: deterministic regex strip (candidate for the existing garble-strip gate).

### 5. Genuine content nits (isolated)
- **D1 101134 (MED)**: structured hours-of-operation table omits 4 centre rows (Rose Bay North, Charing Cross, Curlewis Street, Rose Bay South) present in source; full text lives in 101139, so corpus-complete but the structured copy under-reports.
- **B5 flood matrix (LOW)**: Fencing row cells truncated to '1,' (trailing digit lost) in both copies.
- **B2 100861 (MED)**: 'PM10/PM2.5' subscripts detached → bullet reads 'PM and PM'.
- Superscript loss m²→m2 (B3 100871, E5/E6 101283) — values correct.
- E1 wind-criteria table: one spurious header-fragment table (101144); real data intact.

### 6. Source-asset defect (MED)
`DCPpdfimages` files -178/-179 are byte-duplicates of -176/-177 (AS2700 colour table twice); true printed pages shift by 2 in the 178–185 window. Affects any file-number==page assumption in that range only (annexure territory, no provisions).

### 7. Late-arriving findings (E1 first third, B14–B16)
- **E1 101169 (LOW but visible)**: row 'E1_1_9_controls' has EMPTY body text — vestigial placeholder (real content lives in sibling 101170 'general_controls'); would render as a blank card. Likely overlaps the 36 NULL-topic header-row set.
- **E1 101144**: banner pseudo-tables (pages 262/263) + setback tables duplicated under wrong page label (284 vs true 279; correct copy in 101174).
- **B16**: the full Inter-War Conservation Principles table is served TWICE (structured in 101026, inline text in 101028).

## Clean parts
C1 (both halves, 44 rows), C2 second half, E3 (both halves), F1–F5, pp412–459 annexure spans — no findings at all.

## Fixes APPLIED 2026-07-28 (second pass)
- Text strips on 61 current rows (backup `data/db_rollback_backups/waverley_text_strip_before_2026-07-28.csv`): phantom banner-tables removed, 'W AVERLEY'→'WAVERLEY' (0 remaining), PM10/PM2.5 subscripts rejoined (100861).
- E5 ref collisions FIXED (8 rows → E5_5_4_1..4_objectives/controls; backup `e5_ref_fix_before_2026-07-28.csv`). Mapping verified against source p379-380 with per-row content assertions.
- REMAINING ref clusters (B7 7.2.x, C2 2.3.x, E2 2.1.x, B5 5.2.x): subsection numbers are NOT in the stored rows (extractor flattened sub-headings) — agent-proposed mappings below must be source-verified before applying, OR regenerate refs in the extraction pipeline where headings are available. Do NOT stamp unverified.

## Recommended fixes (all deterministic, no LLM)
1. Ref regeneration for the collision sets (B7 7.2.x, C2 2.3.x, E5 5.4.x, E2 2.1.x/2.2.x, B5 5.2.x) — one more nesting level.
2. Garble-strip pass: empty banner-tables, intro-row duplicate table bundles, 'W AVERLEY' footer bleed, subscript rejoin (PM10/PM2.5).
3. Patch D1 101134 structured table (4 missing centre rows) + B5 fencing cells from source.
4. Re-split or annotate the duplicated page-image files (-178/-179).
