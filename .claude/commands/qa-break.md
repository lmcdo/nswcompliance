---
description: "Phase 2/3: Adversarially break the code you just wrote. Run AFTER /qa-write, BEFORE committing."
---

# QA Phase 2 — BREAK

You are now in **adversarial mode**. Your goal has changed: you are trying to find inputs that produce **wrong results without raising errors**. Crashes are easy. Silent corruption is the real risk.

## Step 1: Re-read the code with fresh eyes

Read every file you changed in Phase 1. Do NOT rely on your memory of writing it. Actually read it again. You are looking for what you missed, not confirming what you remember.

## Step 2: For each function, answer these questions

For every function you wrote or modified, answer in a scratchpad (not tests yet):

1. **What input produces a result that LOOKS correct but IS wrong?**
   Not None, not an exception — a plausible-looking wrong answer. Example: empty list that looks like "no results" but actually means "query failed."

2. **What happens if I call this function with the output of a failed upstream function?**
   Trace the actual failure propagation. If function A fails and returns a default, does function B handle that default correctly or does it silently produce garbage?

3. **What's the widest type this function actually accepts vs what it claims?**
   If the type hint says `str` but it'll actually receive `Optional[str]` from a dict.get() — that's a bug. If it says `list[DA]` but an empty list means something different than a populated list — that's a semantic gap.

4. **Would a hardcoded return value pass my planned test?**
   If `return True` or `return []` would pass, the test is worthless. The test must fail if the logic is wrong, not just if the function is missing.

## Step 3: Write break-it scenarios

Write 5+ scenarios (more for Critical tier) using this format. Each must be a **silent wrong result**, not a crash:

```
SCENARIO: [one line — what the real-world situation is]
INPUT: [the actual data values]
EXPECTED: [what the user should see]
ACTUAL: [what the user would see with the bug]
WHY SILENT: [why no error is raised]
TEST: [the test that catches it]
```

Prioritise:
- False negatives over false positives (telling user "no flood risk" when data was unavailable is worse than showing an error)
- Boundary values at exact thresholds (off-by-one in comparisons: `<` vs `<=`)
- Empty vs None vs missing key (three different things, often conflated)
- Upstream failure propagation (what does this function do when its input is the error-state output of another function?)
- Type coercion traps (`float("nan")`, `int("")`, `bool([])`, `"" == False`)

Do NOT write scenarios for:
- Input validation (that's the gate's job, tested in Phase 1 patterns)
- Things Pydantic already validates (extra fields, wrong types)
- Network timeouts or connection failures (infrastructure, not logic)

## Step 4: Write the tests

Now write tests. Each test must:
- **Test your code's logic, not the framework's.** If removing your function body and returning a constant would still pass, delete the test.
- **Assert on the specific wrong value, not just "not None".** `assert result.confidence == ConfidenceLevel.not_available` not `assert result is not None`.
- **Use realistic data from the spike/fixtures, not synthetic minimums.** Real API responses have quirks that synthetic data doesn't.
- **Name the failure mode in the test name.** `test_flood_overlay_query_failure_looks_like_no_constraints` not `test_flood_overlay_error`.

After writing tests, run them. Then say: **"Ready for Phase 3 — run /qa-verify to validate these tests."**
