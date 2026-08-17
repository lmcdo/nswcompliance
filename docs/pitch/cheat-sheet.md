# Cheat-sheet — the seven checks, one line each

For glancing at during a call. Every row is a check that catches one class of lie. Every one has a PR you can point to on GitHub.

| \# | Check | Class of lie it catches | PR |
|----|----|----|----|
| 1 | `scripts/falsifiability.py` | A test suite that stays green when the code it tests is silently wrong — proven by planting the bug and watching the check go red. | [\#890](https://github.com/lmcdo/nswcompliance/pull/890) |
| 2 | `scripts/doc_claims.py` | A document that says the code does something the code does not do — file paths that don't resolve, version numbers that don't match, dependencies no installer ever reads. **Runs on every push and in CI — in observation mode, so it reports and never blocks.** | [\#890](https://github.com/lmcdo/nswcompliance/pull/890) |
| 3 | `scripts/lint_fabricated_verdicts.py` | A conclusion in the UI ("Not applicable", "Does not apply") that was never actually computed — the component had no input that could ever have changed it. | [\#859](https://github.com/lmcdo/nswcompliance/pull/859) |
| 4 | `scripts/liability_language_check.py` | User-facing prose using words that create legal exposure — "safe", "compliant", "verified", "guaranteed" — when the system is not entitled to make those claims. **Scoped to changed lines, not the whole surface.** | [\#363](https://github.com/lmcdo/nswcompliance/pull/363) |
| 5 | `scripts/validate_schema_contract.py` | SQL in the code that references a table or column the database no longer has — the class of bug the type checker cannot see and the tests miss without a live database. | [\#856](https://github.com/lmcdo/nswcompliance/pull/856) |
| 6 | `scripts/qa_gate.py` (+ template) | A QA report that is well-written but ungrounded — the `file:line` references have to resolve to real functions via AST, not just look plausible. | [\#347](https://github.com/lmcdo/nswcompliance/pull/347) |
| 7 | `scripts/lint_hardcoded_confidence.py` | A confidence grade ("high", "medium") that is a hardcoded string rather than a computed value — a badge asserting rigour that no computation backs. | [\#872](https://github.com/lmcdo/nswcompliance/pull/872) |

## Two things to say if asked

**"Did you write these yourself?"** Claude wrote most of the code. I designed what each check must catch, decided how it fails (closed, never open), and proved every one by planting the bug it exists to catch. The commit messages name the class of lie; the PRs show the review.

**"Why seven, not one?"** Because they catch different classes of lie, and no single tool catches them all. A liability-language scan won't notice a fabricated verdict. A schema-contract check won't notice a stale document. The point of the census — day one of any engagement — is to find out which classes of lie a codebase is exposed to. Not every product needs all seven.

## What is not on this list, on purpose

- **Type checking, unit tests, linters, code coverage.** Every codebase has these; they are the floor, not the ceiling. My finding, from the fortnight of 29 PRs (#835–#906), is that at the time 3,207 Python tests + ~900 frontend tests + type checking + a bracket linter + a liability-language scanner all stayed green through a route that had been broken since a table rename. Volume does not protect. (The figures above are the state on the day that defect was found, not today's. **Do not quote a current test count from this document — ask the repository: `python -m pytest --collect-only -q | tail -1`.** It read 5,460 collected on 2026-08-17, against the 4,024 this sentence used to assert, and it will be wrong again by the time you read it.)
- **AI-assisted "code review" tools.** They flag opinions about style. The checks above flag statements of fact that turn out to be false. Different axis.

------------------------------------------------------------------------

*Every PR number, script path and figure above re-verified against `origin/main` on 2026-08-10. Two PR attributions were wrong in the 2026-08-09 edition (rows 4 and 6 both cited #835, which contains neither script) and are corrected here.*
