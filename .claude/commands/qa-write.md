---
description: "Phase 1/3: Write code with defensive patterns baked in. Run BEFORE writing implementation code."
---

# QA Phase 1 — WRITE

You are in **build mode**. Write the implementation code now, but with these structural constraints enforced during writing — not bolted on after.

## Defensive patterns to apply AS YOU WRITE (not after)

### 1. Null/None at every boundary
Every value that crosses a boundary (API response, DB row, dict lookup, function parameter) must have an explicit None path **in the same function that first touches it**. Not "we'll handle it upstream." Here. Now.

Ask for each value: "What does the user see if this is None?" If the answer is "I don't know" — stop and figure it out before writing the next line.

### 2. Three-state semantics
Never conflate "we checked and the answer is empty" with "we failed to check." If a function can fail:
- Success with data = the value
- Success with no data = explicit empty (None, [], {}) with a confidence/source marker
- Failure = error wrapper with reason string

If you return the same type for cases 2 and 3, you have a silent failure bug. Fix it in the type, not in a comment.

### 3. Error isolation
Any function that calls an external service, parses untrusted input, or does type conversion:
- Must not raise to its caller (wrap in try/except or equivalent)
- Must return a typed error value, not a bare None
- Must log/record what failed and why

One function crashing must never take down an unrelated section of the response.

### 4. Input validation at the gate
Validate at the outermost boundary only. Use Pydantic models, regex patterns, range checks. Reject bad input with a specific error message, not a generic 500.

After the gate: trust the types. Don't re-validate inside helper functions.

### 5. No silent defaults
If a function has a fallback/default value, it must be **obviously correct, not just non-crashing**. `zone_prefix = ""` is fine (downstream handles empty). `is_flood_risk = False` as a default is dangerous (false negative). Ask: "Is the default the safe answer or just the convenient one?"

### 6. Constants extraction
Magic numbers, threshold values, timeout durations, regex patterns — extract to a config object or module-level constants. Name them to explain the "why" not the "what." `STRATA_APARTMENT_MAX_LOT_M2 = 400` not `THRESHOLD = 400`.

## When you're done writing

State what you built, then say: **"Ready for Phase 2 — run /qa-break to adversarially test this code."**

Do NOT write tests in this phase. Do not even think about tests. You are building, not validating.
