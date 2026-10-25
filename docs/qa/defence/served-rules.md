<!-- prior-art-checked: docs/qa/defence did not exist; this sheet links the area's diagram, baseline and verdicts. -->
# Served rules — defence sheet (frozen `a6d2e378`, 2026-10-25)

**What it does.** Address in → only that property's rules out, in the council's words with document and page.
Next.js reads Postgres directly; Python fills the tables offline. Diagram: `../diagrams/served-rules.md`.

**Strengths (with evidence)**
- Failed checks are tracked as "not checked" across most of the path (`lib/hazard-unchecked.ts`,
  `lib/conditions-not-checked.ts`, `notChecked(...)` in `app/api/property/route.ts:222`); the PDF honours it.
- Typed planning numbers are under a ledger enforced in CI (`.claude/regulatory_figure_ledger.json`, 223 entries).
- Every claim in this review is reproducible: frozen sha, pinned tools, machine live-file list, pre-registered
  rules and answer keys committed before results (`../review-protocol.md`).

**How the review was run.** Tools baseline (`../quality-baseline-2026-10-25/`), then Codex with the 8 house rules
as checks, every finding opened by Opus, the one rejection sent back to Codex.
Codex alone on 5 past fixes found 1 (`../codex-bench/RESULTS.md`); with house rules, 8 of 8 findings here were real.

**Found (all on the frozen commit; check today's main before fixing)** — `../codex-briefs/served-rules-verdicts.md`
- Wrong-answer risk (P1): flood "No" when the map query failed (screen only); SEPP "no requirements" when the
  request failed; overlays tested at the address point, not the lot; typed zone lists and a typed 450 m² deciding
  what is shown.
- Labelling (P2): granny-flat PDF figures marked "cited" though paraphrased; typed lot sizes in Pattern Book text.
- Gate gap (P1 for the gate): the typed-figure scanner misses "min", bare numbers, old zone lists and
  "paraphrased" cites, so its "83 open" undercounts.

**Known trade-offs.** `../known-tradeoffs.md` (10 items + clause-count gap G1/G1a).

**Fixed so far.** None yet — fixes go in separate PRs, each with a test that fails before and passes after.

**Not measured.** Slow DB queries (needs read-only production access).
