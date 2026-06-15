---
globs:
  - "**/*.py"
  - "**/*.ts"
  - "**/*.tsx"
---

# Pre-PR Code Review

Before creating any PR, apply these 5 checks to every changed file:

1. **DB query filters** — every `SELECT` must have correct `WHERE` clauses: `is_active = TRUE`, council/instrument scope, no missing filters
2. **Unguarded nulls** — DB rows, API responses, optional fields must be null-checked: `.rows[0]?.field ?? null`, optional chaining, loading states
3. **Type assumptions** — types match at every boundary: DB→API (date parsing), API→component (ISO string vs Date), component state (undefined vs null vs false)
4. **Silent failure modes** — if this fails, does it fail visibly (error/banner) or silently (wrong data served)? Silent = always worse.
5. **Liability language** — grep changed user-facing text for: `safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|approved|guaranteed|certified|confirmed|verified|ensure|assure|accurate|definitive|comprehensive|reliable`. Each match: (a) regulatory quotation, (b) internal variable, or (c) replace with factual language. See `docs/qa/language-audit-2026-05-18.md`.
