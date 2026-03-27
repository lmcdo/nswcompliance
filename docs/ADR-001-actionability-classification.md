# ADR-001: Actionability Classification — Three-Stage Conservative Hybrid

**Status:** Accepted
**Date:** 2026-03-27
**Author:** Lawrence McDonald

---

## Context

The compliance engine must classify every extracted planning provision as either
**actionable** (a real development control the SEE must address) or **boilerplate**
(TOC entries, legislative headers, figure captions, page numbers).

This gate — stored as `v2_is_actionable` on `regulatory_provisions` — is the first
filter in the enrichment pipeline and the primary filter in all frontend provision
queries. A false negative (binding control marked non-actionable) silently removes
that control from the DCP browser, the SEE document, and the PDF export. The
certifier never sees it.

Under EP&A Act s4.15 a consent authority must consider "the provisions of any
development control plan." A SEE that omits relevant DCP provisions because they
were incorrectly filtered at this stage is legally incomplete. The acceptable number
of silently dropped binding controls is zero.

**Problem with the original regex-only approach:**

- The pipeline only processed `v2_is_actionable IS NULL` rows. Previously-classified
  `false` rows were never re-evaluated when classifier rules improved.
- 277 DCP provisions containing "must" and 89 containing "shall" were confirmed
  non-actionable in the DB despite the classifier's definitive-control rule
  (`must`/`shall` = always actionable). These were classified under an older version
  of the code.
- Performance-based DCPs (Ashfield Purpose/Performance Criteria/Design Solutions
  format) produce structural ambiguity that regex cannot resolve — heritage narrative
  text incidentally contains "must" in colloquial senses the classifier cannot
  distinguish from regulatory language.

**Why not Gemini for all provisions?**

~90% of the classification task is unambiguous boilerplate (page numbers, TOC
entries, figure captions). Regex handles these with 100% accuracy, runs offline,
produces a fully auditable decision trail, and completes a full re-run in seconds.
Running Gemini on clear cases adds API dependency, rate-limit fragility, and
non-reproducible audit trails for zero quality gain. All-Gemini is architecturally
valid but operationally fragile for pipeline re-runs on new LGAs.

---

## Decision

Actionability classification uses a **three-stage conservative hybrid**:

### Stage 1 — Regex: deterministic boilerplate exclusion (permanent)

`enrichment/extractors/actionable_classifier.py` handles legislative headers,
TOC entries, figure/map captions, and page numbers. These patterns are
unambiguous and regex is the correct tool.

**Conservative default:** Any DCP provision that does not match a clear boilerplate
pattern is marked `true`. False positives (noisy provisions shown to the user) are
tolerable. False negatives (binding controls hidden) are a professional liability.

**Stale-data fix:** The pipeline's `run_actionability_classification()` gains a
`force_reprocess` flag that re-evaluates `v2_is_actionable = false` rows against
the current classifier, not only `NULL` rows. This is the mechanism for applying
classifier improvements retroactively.

### Stage 2 — Default-to-actionable (immediate)

When Stage 1 produces no confident boilerplate match on a DCP provision, the
result is `true`. This is already the classifier's intent; this ADR makes it
explicit policy. The implementation is confirmed in
`actionable_classifier.py:229-237` (`dcp_substantial_text` branch).

### Stage 3 — Gemini Flash with substring verification (future, interface locked now)

For performance-based DCPs (Ashfield and future LGAs using Purpose/Performance
Criteria/Design Solutions structure), a Gemini Flash classifier is used. Its
output is accepted **only if** the identified text is a verbatim substring of the
source provision (`source[char_start:char_end] == identified_text`). Output that
fails verification is rejected and the provision defaults to actionable (Stage 2
conservative default). This eliminates hallucination risk and produces a
machine-verifiable audit trail.

Interface defined in `enrichment/extractors/gemini_actionability_classifier.py`.
Triggered by document format detection, not by LGA name, so it scales to any
future performance-based council.

---

## Consequences

**Positive:**
- False negatives from stale classification are eliminated by `force_reprocess`
- Conservative default means classifier improvements can only increase coverage,
  never silently drop provisions
- Gemini path scales to 100+ LGAs without per-LGA regex maintenance
- Substring verification makes the Gemini path as auditable as the regex path
- SEE documents generated after migration are defensible under EP&A Act s4.15

**Negative / accepted trade-offs:**
- `force_reprocess` will flip some Ashfield E1 Heritage narrative provisions to
  actionable (they contain regulatory "must" and the classifier correctly cannot
  distinguish this from narrative "must" at regex level). These provisions are a
  pre-existing upstream extraction quality issue; they appear as noise in the
  Ashfield DCP browser. Fixing the extraction root cause is out of scope here.
- Gemini path introduces API dependency for performance-based DCP pipeline runs.
  Clear boilerplate remains regex-only and offline-capable.
- Provisions newly flipped to actionable will initially lack enrichment metadata
  (type, applicability, extracted rules). They will appear in the browser but
  without full tagging until the subsequent pipeline stages are re-run.

---

## Alternatives Rejected

**All-regex (status quo):** Cannot handle performance-based DCP formats at scale.
Known false negatives confirmed in production data. Rejected.

**All-Gemini:** Architecturally valid. Cost (~$2/full run) is not the objection.
Rate limits make full pipeline re-runs on new LGAs operationally slow. Non-deterministic
output complicates compliance audit trails. Rejected in favour of hybrid; may be
revisited if regex maintenance burden grows beyond threshold.

**LLM for actionability only, regex retired:** Premature. Regex handles 90% of
cases with 100% accuracy and zero API dependency. The 10% that benefit from LLM
context are handled by Stage 3. Rejected.

---

## Related

- `enrichment/extractors/actionable_classifier.py` — Stage 1 implementation
- `enrichment/extractors/gemini_actionability_classifier.py` — Stage 3 interface
- `enrichment/pipeline.py` — `run_actionability_classification(force_reprocess=)`
- `docs/DCP_EXTRACTION_KNOWN_PATTERNS.md` — known artifact classes per LGA
- `memory/structural-exclusion-architecture.md` — why `v2_topic` is not used for
  hard filtering (same principle applies here)
- EP&A Act s4.15 — legislative basis for zero-false-negative requirement
