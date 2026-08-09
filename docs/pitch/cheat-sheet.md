# Cheat-sheet — the seven checks, one line each

For glancing at during a call. Every row is a check that catches one class of
lie. Every one has a PR you can point to on GitHub.

| # | Check | Class of lie it catches | PR |
|---|---|---|---|
| 1 | `scripts/falsifiability.py` | A test suite that stays green when the code it tests is silently wrong — proven by planting the bug and watching the check go red. | [#890](https://github.com/lmcdo/nswcompliance/pull/890) |
| 2 | `scripts/doc_claims.py` | A document that says the code does something the code does not do — file paths that don't resolve, version numbers that don't match, dependencies no installer ever reads. | [#890](https://github.com/lmcdo/nswcompliance/pull/890) |
| 3 | `scripts/lint_fabricated_verdicts.py` | A conclusion in the UI ("Not applicable", "Does not apply") that was never actually computed — the component had no input that could ever have changed it. | [#859](https://github.com/lmcdo/nswcompliance/pull/859) |
| 4 | `scripts/liability_language_check.py` | User-facing prose using words that create legal exposure — "safe", "compliant", "verified", "guaranteed" — when the system is not entitled to make those claims. | [#835](https://github.com/lmcdo/nswcompliance/pull/835) |
| 5 | `scripts/validate_schema_contract.py` | SQL in the code that references a table or column the database no longer has — the class of bug the type checker cannot see and the tests miss without a live database. | [#856](https://github.com/lmcdo/nswcompliance/pull/856) |
| 6 | `scripts/qa_gate.py` (+ template) | A QA report that is well-written but ungrounded — the `file:line` references have to resolve to real functions via AST, not just look plausible. | [#835](https://github.com/lmcdo/nswcompliance/pull/835) |
| 7 | `scripts/lint_hardcoded_confidence.py` | A confidence grade ("high", "medium") that is a hardcoded string rather than a computed value — a badge asserting rigour that no computation backs. | [#872](https://github.com/lmcdo/nswcompliance/pull/872) |

## Two things to say if asked

**"Did you write these yourself?"** Claude wrote most of the code. I designed
what each check must catch, decided how it fails (closed, never open), and
proved every one by planting the bug it exists to catch. The commit messages
name the class of lie; the PRs show the review.

**"Why seven, not one?"** Because they catch different classes of lie, and no
single tool catches them all. A liability-language scan won't notice a
fabricated verdict. A schema-contract check won't notice a stale document.
The point of the census — day one of any engagement — is to find out which
classes of lie a codebase is exposed to. Not every product needs all seven.

## What is not on this list, on purpose

- **Type checking, unit tests, linters, code coverage.** Every codebase has
  these; they are the floor, not the ceiling. My finding from six weeks of
  work is that 3,207 Python tests + ~900 frontend tests + type checking + a
  bracket linter + a liability-language scanner all stayed green through a
  route that had been broken since a table rename. Volume does not protect.
- **AI-assisted "code review" tools.** They flag opinions about style. The
  checks above flag statements of fact that turn out to be false. Different
  axis.
