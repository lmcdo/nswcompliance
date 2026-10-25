# Step 2 result — Codex recall on 5 real past fixes (2026-10-25)

**Recall = 1 / 5.** Indication only: 5 cases cannot pin a rate (1/5 is consistent with roughly 1%–72%).
Scored blind by Sonnet against the pre-registered keys (`../review-protocol.md`); Opus re-read #1492 and #1490
NOT FOUND verdicts against `out-*.json` and agrees.

| PR | Verdict | Codex's closest finding |
|---|---|---|
| #1492 monitor | NOT FOUND | right file, other problems (hub-scrape exceptions, HEAD 403/transport counted as failures) |
| #1491 monitor | **FOUND** (finding 0) | "diff_urls silently retains the last discovered URL for a duplicated chapter_key … can repoint … to the wrong PDF" |
| #1490 served | NOT FOUND | zone filter on structured controls, ST_Contains on a point, corner-only controls, rate limit |
| #1489 served | NOT FOUND | address matching, search filters, rate limit; nothing on typed rule numbers |
| #1481 served | NOT FOUND | heritage query, Part 6 Lot/DP, ST_Contains; nothing on battle-axe constants |

Other findings: 28 (unjudged). Severity: 18 of 29 marked P1 — likely over-rated.

## What this means (plain)
- Codex found the one bug that is a single local logic slip (last link wins). It missed the ones that need project
  knowledge: which values must come from the DB, and that "failed" must never read as "none apply".
- A clean Codex report is **not** evidence of no bugs. Use it as extra eyes, never as the gate.
- The served-area brief is broad; Codex spent its findings elsewhere. Several of those look real on a first read
  (e.g. flood facts tested on the address point, not the lot), but none is verified yet. Precision is measured in Step 4.
- Before Step 4: give each area brief the house rules that matter (no typed figures; failed = "not checked") as
  explicit check items. Recorded as a protocol change made AFTER this result, so Step 4 is not compared to this score.
