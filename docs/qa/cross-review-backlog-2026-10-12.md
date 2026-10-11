# Cross-review backlog, 2026-10-12

The GPT-5.6 Sol cross-review failed with "no credits remaining" from 2026-10-11 14:12. A failed call
only blocks a push that touches served output, so #1264 (final push), #1265, #1267, #1268, #1269 and
#1270 merged unreviewed. Credits were restored on 2026-10-12 and each PR was reviewed on its own
(`python scripts/cross_review.py --pr N`), plus branch feat/hazard-gates. 21 findings; every one has a
verdict below. Live impact was measured before deciding.

| Finding | Verdict | Live impact measured | Action |
|---|---|---|---|
| 1269-1 neighbour check not re-run after a map check widens the parcels | real | 14M: not re-checkable today (NSW address register returning 400); live 45 Warrane Rd shows 0 site rules | re-run neighbours after widening; any neighbour inside holds the site |
| 1269-2 raster outline may be a legend swatch | real | none observed (all passing maps checked by eye) | MIN_PAGE_SHARE applied to raster outlines |
| 1269-3 fallback count ignores is_active | wrong | dcp_precinct_boundaries has no is_active column; the live lookup has no such filter | none |
| 1268-1 `--only` loads passing sites when a requested one fails | real | none (every requested site passed) | refuse unless every requested site passes |
| 1268-2 copy check equates "Lot 1-2" and "Lot 12" | real | all 14 recorded texts re-verified against their pages with the stricter check | keep hyphens, commas, "&" |
| 1268-4 backup lacks geometry and LGA scope | real | none lost: every loaded outline was a new row | full rollback row scoped by (precinct_id, lga) |
| 1265-2 B2.n sub-section refs would fall to the all-eleven rule | real | 0 such rows exist | match the whole sub-section tree |
| 1270-2 heritage-area holes dropped | real | 0 holes in the 7 C-B outlines | holes kept |
| 1265-1, 1268-3, 1270-4, branch-3 `\|\| true` hides a failed post-write check | real, low | every run's output was read by hand | fixed in the unrun apply_site_condition_gates.sh; earlier one-off scripts left |
| 1267-1 OC-21 claims more than DQ-146 checks | real | exactly the flood gap found 2026-10-11 (page sent no flags) | claim narrowed to the checked invariant |
| 1265-3 Wollongong E11 omits "vicinity" land | real, limit | no layer records adjacency | recorded on DQ-143 |
| 1270-1 C-B 4.4 "vicinity" shown council-wide | real, limit | 3 rules | recorded on DQ-143 (counted unconfirmed under DQ-144) |
| 1270-3 C-B 4.2 heritage-item rules reach heritage-area lots | real, limit | 26 rules | recorded on DQ-143; needs an item-vs-area signal on the page |
| 1264-1 DQ-143 accepts any tag without comparing to the chapter's | real, limit | count is a floor | recorded on DQ-143 |
| 1264-2 DQ-144 skips zone/heritage-tagged rows | real, limit | count is an upper bound only for untagged rows | recorded |
| 1264-3 C-B 4.2 counted as ungated | already fixed | #1270 heritage_general kind | none |
| branch-1 Ku-ring-gai 16 omits the evacuation map | real, accepted | user decision 2026-10-11 option (a) | recorded |
| branch-2 unknown site facts treated as false | real | same as the known /api/property lookup-failure fault | tracked as that fault |
