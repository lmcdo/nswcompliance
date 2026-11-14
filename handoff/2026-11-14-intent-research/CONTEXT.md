# Handoff: opportunity-finding research (cloud session, 13–14 Nov 2026)

Pull this into a local Claude Code session with: "Read handoff/2026-11-14-intent-research/CONTEXT.md and continue."

## What was discussed, in order
1. **Dev tools review.** EGM (Google Elephant-Goldfish), Serena, Spec Kit, Superpowers, Repomix were
   weighed against this repo's incident history. Verdict: try EGM's `egm-review` (run locally,
   on new-surface designs), trial Serena; skip `egm-bootstrap` repo-wide (would write ~430 AI READMEs:
   441 code dirs vs 14 READMEs), skip Spec Kit and Repomix. Biggest real fix for the CI incidents
   (#902/#907): GitHub branch protection (needs a paid plan).
2. **NVIDIA Auto Ontology.** Relational-only semantic layer for agent text-to-SQL. Possible internal use
   as certified definitions over Supabase (read-only role); not for customer-facing answers.
   Side finding: `services/autoschema_kg_query.py` reads CSVs not in the repo and returns empty
   silently; `services/clause_citation_inline.py` has a hardcoded `fake_to_real_mapping` (violates
   the no-hardcoded-regulatory-data rule). Not fixed, no DQ entry created.
3. **Business direction.** Desk research keeps "finding no opportunity" because it can only see
   visible competition, not demand. Recommended: sell the build skill as fixed-price services first;
   use existing NSW planning assets (cdc_screen, conveyancing, granny_flat) as per-job deliverables.
4. **Outreach engine.** User's position: the key is intelligent *finding* and *fielding* of
   opportunities, not keyword alerts. Starter tool built (`lead_finder/`), then judged too
   keyword-bound; deep research commissioned.

## Deliverables in this folder
- `AI buyer intent discovery 2026.md`: final research report (about 4,000 words). Read this first.
- `research_notes/`: four underlying notes (tools, techniques, data access, market/build), with sources.
- `lead_finder/` (sent as files in the chat, not committed; it is not part of this product): v0 pipeline (HN + Reddit → keyword prefilter → Claude scoring → daily digest).
  12 tests pass (`python -m pytest -q tests`). Never run on live data: the cloud proxy blocked
  hn.algolia.com and www.reddit.com. Reddit fetcher is non-commercial-use only under Reddit's terms.

File index (lead_finder):
- `lead_finder/config.py`: pain phrases, HN queries, subreddit targets
- `lead_finder/sources.py`: HN Algolia + Reddit fetchers
- `lead_finder/scoring.py`: prefilter + Claude structured scoring
- `lead_finder/run.py`: daily run, digest, leads.csv
- `lead_finder/tests/test_pipeline.py`: offline tests

## Research conclusions (see report for evidence levels)
- No tool has demonstrated latent-need detection; commercial "AI intent" = LLM scoring of stated needs.
- Approach that fits the evidence: infer pain from observable business situations (hiring admin/data
  entry, DA lodgement streams, regulatory change) rather than complaint words.
- Data: Reddit gated + litigious; LinkedIn off-limits; Facebook Groups no API; X cheap and legitimate.
- NSW limits: Privacy Act, statutory privacy tort (from 10 Jun 2025), Spam Act consent.
- Market: horizontal SaaS crowded/thin; gap = AU vertical lead feed from public records. Use internally
  first.

## Agreed next step (not started)
GOAL: a property/development lead finder over the NSW planning data, cascade-scored (Haiku triage →
escalate on disagreement → human gate), with outcome tracking against a holdout.
DONE WHEN: hand-label 200–300 items as a gold set; measure precision@20 against a bar set in advance.
BUDGET: one weekend build; no research agents until precision is measured.

## To verify before relying on
Reddit official API terms, OAIC guidance on scraping and the small-business exemption, SEEK terms.
Many figures in the notes are search-snippet or vendor-sourced (marked in the report).
