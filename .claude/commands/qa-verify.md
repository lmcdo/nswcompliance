---
description: "Phase 3/3: Validate that tests actually catch bugs, not just exercise code. Run AFTER /qa-break."
---

# QA Phase 3 — VERIFY

You are now in **verification mode**. You are auditing the tests you just wrote to determine which ones actually protect against regressions and which ones are theatre.

## Step 1: Mutation analysis (manual)

For each test, mentally apply these mutations to the code under test and check whether the test would still pass:

| Mutation | Example | If test still passes... |
|----------|---------|------------------------|
| Return constant | `return []` / `return None` / `return True` | Test doesn't check logic |
| Flip comparison | `<` to `<=`, `>` to `>=`, `==` to `!=` | Test doesn't hit boundary |
| Remove guard | Delete the `if x is None` check | Test doesn't send None |
| Swap branches | Switch if/else bodies | Test only checks one path |
| Drop a field | Remove one field from the response model | Test doesn't check completeness |
| Change default | Swap `False` to `True`, `[]` to `None` | Test doesn't verify defaults |

**Report the results.** For each test, state:
- STRONG — fails on 3+ mutations
- ADEQUATE — fails on 1-2 mutations
- WEAK — passes on all or most mutations → rewrite or delete

Target: 0 WEAK tests. If any remain, rewrite them now.

## Step 2: Coverage gap analysis

Read the code under test one more time. List:
1. **Functions with no tests** — are they trivial (pure delegation) or do they contain logic?
2. **Branches with no tests** — especially else/except/default branches
3. **Combinations not tested** — if A can be None and B can be None, did you test both-None?

For each gap: decide if it matters. Not all gaps need tests. But **document the decision.** "No test for X because Y" is fine. Silent gaps are not.

## Step 3: Fixture realism check

For each test fixture / test data:
1. Does it match the shape of real API responses? (Check against spike-results.json or actual API docs)
2. Does it include the quirks? (HTML in strings, inconsistent casing, trailing whitespace, null vs missing key)
3. Would a real response ever have a shape your fixture doesn't cover?

If you're testing with cleaner data than production serves, your tests are lying.

## Step 4: Cross-function integration check

Tests so far are unit tests — one function at a time. But bugs live at boundaries. Check:
1. **Does the output of function A, when fed to function B, actually work?** Not in theory — trace the actual types and values.
2. **If function A fails gracefully (returns error wrapper), does function B handle that error wrapper?** Or does it treat the error wrapper as valid data?
3. **Are there any functions that assume their caller has already validated something?** That assumption is a bug waiting to happen.

Write integration-style tests for any gaps found.

## Step 5: Generate QA report

Now fill out `.qa_report.json` using the template at `scripts/qa_report_template.json`.

Requirements:
- `commit_hash`: run `git rev-parse --short HEAD`
- `functions`: every function you wrote/modified, with **actual AST line numbers** (verify by reading the file, don't estimate)
- `break_it`: the scenarios from Phase 2, updated based on Phase 3 findings
- Every `input`/`output`/`if_none` description must be >=8 words for Critical tier
- Every `break_it.scenario` and `what_happens` must be >=10 words for Critical tier

Run:
```bash
python scripts/qa_gate.py .qa_report.json --diff-files <changed-files>
```

If it fails, fix the report (not the gate). Show the passing output in the conversation.

## Done

State findings:
- How many tests were STRONG / ADEQUATE / WEAK
- What gaps were found and addressed
- What mutations would have escaped

Then proceed to commit with the QA tier line in the message.
