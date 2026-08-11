# DCP extraction remediation — 3 causes, not 170 problems (2026-07-29)

The semantic sweep's 170 raw confirmed findings collapse to **3 systematic causes**.
Fix these and the long tail (mostly repetitions + figure-numeric limitation + over-claims)
mostly evaporates. Ordered by dependency — #1 must land before #2 is safe.

## Cause 1 — Two-column / table layout defeats reading order  (KEYSTONE)
**Symptom:** on two-column pages the extractor reads across both columns, interleaving
sentences; on table-heavy pages it drops sections (ref sequences skip, e.g. CoS 5_2_3→5_2_5).
Biggest bucket of sweep findings (dropped sections + garbled controls). Blocks re-extraction
of Ashfield ch.D, Marrickville (whole DCP), CoS Section 5.
**Fix:** column-aware page text — detect the two bands from word x-geometry (the preflight
already computes this), read left column fully then right column, then run the normal
splitter. Table cells extracted structurally, not flattened into prose.
**Status:** BUILDING NOW (preflight worktree). Review-gated; no auto-commit.

## Cause 2 — Registry never re-extracts amendments (silent staleness)
**Symptom:** source amendment detected (`url_last_changed` updates) but `needs_extraction`
stays False and `last_extracted_version` never advances. Ashfield chapter-e1-heritage:
v1.2-2026-06-22 amendment never extracted; also chapter-g-definitions, preliminary.
The change-detector clears its own alarm without acting.
**Fix:** (a) data — set `needs_extraction=True` where `url_last_changed > last_extracted date`;
(b) code — the monitor must not clear the flag until an extraction actually commits that
version. **DEPENDS ON #1**: queueing re-extraction of two-column chapters before #1 exists
just produces interleave (gates would block the commit, but it's wasted + noisy). Do after #1.

## Cause 3 — Supersede-without-replacement drops content silently
**Symptom:** a re-extraction deactivates the old rows and produces fewer/none, leaving content
`is_current=false` with no current replacement (the Ashfield 49-HCA drop; CoS Danks St).
**Fix:** the `count_drop` gate already exists and now blocks these at review (proven on
Marrickville). Harden: on any net content drop, KEEP the superseded rows current until the
new extraction is human-approved — never auto-deactivate on a drop. Largely covered by the
gate + preflight; verify no path bypasses it.

## Not a cause worth "fixing": figure/diagram numerics
44 sweep findings are numbers printed inside figures/diagrams — not extractable text in ANY
pipeline. Mitigation = OCR fallback (already live) + honest labelling; not a code bug.

## Sequence
1. Build + test column-aware extraction (#1) — review-gated. ← IN PROGRESS
2. Re-extract the known-bad chapters (Ashfield ch.D + e1-heritage, Marrickville, CoS S5) through it; human-review; commit.
3. Fix registry staleness flag + monitor clear-logic (#2).
4. Harden supersede gate (#3); confirm no bypass.
5. Re-run the semantic sweep on the re-extracted chapters to confirm the causes closed.
