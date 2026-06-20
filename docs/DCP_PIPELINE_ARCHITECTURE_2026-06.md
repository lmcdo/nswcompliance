# DCP Monitoring & Updating — Optimal Architecture (2026-06-20)

**Question:** Make DCP monitoring + updating as automated, efficient, and effective as safely possible.
**Method:** 3-agent investigation — git-history archaeology + current-state audit + external best-practice research.
**Status:** Recommendation, not yet implemented. The `dcp_watchdog` exit-code fix (1→2, stops double-alerting) ships in this same branch.

---

## 1. The diagnosis (three independent investigations, one conclusion)

The pipeline was designed roughly right. The problem is **half of it was deleted, and the recurring failure modes were never structurally solved.**

**Intended (4 stages):** detect change → auto extract-to-review → human approves → commit to prod. Plus a watchdog alarm.

**Actual today (post-migration #506, 2026-06-18):**
- ✅ Detect (`r2_monitor.py`) and Watchdog (`dcp_watchdog.py`) run on Railway cron.
- ❌ Auto **extract-to-review** (`dcp-extract.yml`) — DELETED, no replacement. Nothing auto-runs the extractor.
- ❌ **Commit** workflow (`dcp-commit.yml`) — DELETED. Commit is now "a human types a local script."
- ❌ Per-council **rate-limit isolation** (parallel jobs / different IPs) — DELETED. Railway runs all councils sequentially from one IP, re-exposing the single worst failure mode in the project's history.
- ⚠️ Governance doc (`DCP_UPDATE_GOVERNANCE.md`) is now **stale** — still documents the deleted workflows.

**Why the migration happened:** cost. "GitHub Actions budget exhausted ($38.59/mo, 91% from this repo)" (`5a9a5313` #369, `e2216165` #506). Any fix must stay ~$0 incremental.

**Asset already half-built:** `run_monitors.py` already has `ping_healthcheck()` and references `HC_PING_URL` — the healthchecks.io dead-man's-switch that external research independently names as THE fix for silent-stage failures. It's just **unset** (the "Env missing: ['HC_PING_URL']" alert). The right thing was started; it isn't wired.

**Unused precise staleness signal already in the schema:** migration 036 added `provisions_extracted_from_hash`. The exact "what's stale" query is `content_hash != provisions_extracted_from_hash` — more precise than the time-based `needs_extraction` flag.

---

## 2. Top recurring pain points (from git history, ranked frequency × severity)

1. **CDN rate-limiting / WAF on bulk PDF fetch** — caused 93–98/104 chapter failures historically. The matrix-isolation fix that solved it was **deleted by #506**. *Just regressed; highest severity.*
2. **Change-detection false positives / alert noise** — most-fixed class (one bug fired **233 Telegram messages** in a run). Erodes trust in the alert channel.
3. **ETag/Content-Length logic** — broken from day one (stored NULL ETags every run; CL mismatch permanent). Both false-misses and false-positives.
4. **Per-council PDF extraction quality** — every new council needs hand-tuned page ranges / two-column configs. Doesn't generalize (`DCP_EXTRACTION_KNOWN_PATTERNS.md` §1–§8).
5. **Over-aggressive gates / soft-delete scoping** — once **wiped 1,592 real Leichhardt provisions**; also false-aborted good extractions.
6. **Migration debt** — dropped auto-extract, matrix isolation, artifact review; stale docs.
7. **Railway observability** — hidden stderr, hidden cron crashes, swallowed Telegram errors.
8. **Manual reconciliation / review bottleneck** — orphan re-keying + non-negotiable human gate; *more* manual post-#506.

---

## 3. External best-practice convergence (CourtListener/RECAP, Open States, UK Planning Data, Ascent RegTech)

Everyone serving legally-cited data uses the **same shape** — which this project has half-built:

1. **Brittle source-adapter isolated from a stable core** — per-council parsers fail LOUD on unexpected input (Open States "intentionally fragile"); core stays stable.
2. **Content-hash-gated reprocessing + deterministic identity keys** — key provisions by `(council, chapter, clause)`, never by page/bbox (RECAP).
3. **Diff old-vs-new + classify the change, weighting numeric deltas highest** — a setback/height/FSR/parking change is the high-risk event (Ascent's highlighted new/changed/deleted diff).
4. **Schema-as-contract, validated BEFORE touching the live DB** (Open States JSON schemas; Soda/Pandera/Great Expectations).
5. **Explicit human gate before "trusted/current"** — and *low-confidence escalates to a human, never silently drops* (a silent drop keeps the stale value live — a high-liability trap).
6. **Structured source beats PDF where available** — but NSW councils publish DCPs only as PDFs, so PDF extraction is unavoidable here (see §6).

**Governing principle for cited data:** the expensive error is the *silent* one. Bias every choice toward making failure loud, even at the cost of extra alarms.

---

## 4. Recommended path (phased; minimal-change first)

### Phase 0 — Stop the bleeding (hours, ~$0). Restore what #506 deleted, governance-compliant.
- **Add a `dcp-extract` Railway monitor** running `dcp_extract_changed.py --review` on a schedule shortly after the detector. Writes the review file + sends Telegram "review ready." **No DB writes** — keeps the human commit gate intact.
- **Re-add rate-limit protection** for the single-IP Railway run: confirm `adaptive_delay()` is active in the sequential path, and stagger/throttle councils (or split into a few cron offsets). Un-regresses pain point #1.
- **Wire `HC_PING_URL`** (healthchecks.io, free) on every monitor service. This alone would have caught the silent-stage failure.
- **Update the governance doc** to match reality (Railway, not GitHub Actions).
- **Decide the stuck chapters** the governed way: run `--review`, inspect (some under-extract to ~2 sections — likely missing page-range config for `section-a-part-6-multi-dwelling` & `section-c-part-23-building-design`, plus the `inner_west`↔`ashfield` council-key mismatch on `chapter-a-miscellaneous`). Fix config, then commit only the good ones.

### Phase 1 — Kill the highest-liability failure modes (days, ~$0). The "minimal change" bundle.
- **Per-provision normalized-text hash + numeric-token diff** — replace byte-hash / ETag-as-truth. Normalize away metadata/whitespace/headers; **never** normalize away digits/units/cell boundaries. Kills false-positive noise (#2/#3) and surfaces risky numeric changes.
- **Postgres review-queue table** — `stage` enum, atomic per-item commit, claim with `SELECT … FOR UPDATE SKIP LOCKED`, retry/backoff, **dead-letter → human** (never silent drop). Replaces "run a script" with durable, inspectable state. Guards #5/#8.
- **Dead-man's-switch v2** — beyond `HC_PING_URL`, add a "queue not stalled" check (alert if any row stuck `in_progress` > 1h). Catches a wedged stage even if cron keeps ticking.
- **Schema-validate every provision before commit** (Pandera/JSON-schema: clause format, units present, numeric ranges e.g. setback < ~30m). Blocks silent under-extraction / drift corruption before the live DB.
- **Diff-based review UI** — small Next.js page against the queue: old-vs-new + PDF page crop + the numeric diff. Goal: approve in ~30s from the diff alone.

### Phase 2 — Reduce per-council toil + concentrate human time (moderate).
- Route **scanned / borderless-table councils** to a **structure-aware extractor** — Azure Document Intelligence Layout ($10/1k pages, tables included; pay-per-use only for hard councils), self-hosted **Docling** (free, ~97.9% complex-table accuracy), or a **vision LLM (e.g. Gemini)** as a *proposing* extractor (see §6 — never system-of-record). Structure-aware extraction is **drift-tolerant** — it won't silently shift columns on re-layout the way x-coordinate page-range configs do. Structural cure for pain point #4.
- **Synthesized confidence score** (no model needed for deterministic extract): structural stability + numeric-delta magnitude + double-extraction agreement (table-mode vs text-mode). Auto-approve only cosmetic/low-risk; concentrate humans on real changes. Still hard-gate every cited numeric change.
- **Anomaly gates** (Great Expectations/Pandera): per-doc row-count bounds, moving-stddev volume anomaly; a **low-confidence volume spike = template-drift alarm**.

### Phase 3 — Ideal end-state (only when hand-rolled bookkeeping becomes the bottleneck).
- **Self-hosted Prefect** (single Postgres) for durable orchestration: native Late/Crashed/Failed automations, per-task retry/timeout, a human-approval *suspend* step. Keep healthchecks.io as the independent external watchdog. (Temporal/Airflow are over-scoped solo.)
- **Dual-extractor reconciliation** — deterministic extractor = system-of-record; an ML/LLM second opinion only *flags discrepancies* to human review, never commits.
- **Schema-as-contract with full provenance** (`effective_date`, `source_version`, source hash, extraction strategy, confidence) + per-council freshness SLAs with alerting. Modeled on UK Planning Data + Open States.

---

## 5. LLM (e.g. Gemini) — where it helps defensibly, and where it must not

An LLM can help **a lot**, but only in roles that never make it the authoritative source of a cited number. The liability rule is not "no AI" — it is "a human approves before live, and the cited value traces to source."

**Defensible, high-value roles:**
- **Vision extractor for the hard councils** (scanned PDFs, borderless/two-column tables) where pdfplumber needs hand-tuned page ranges. Gemini's native PDF/vision + long context handles these well — output is a *proposal* fed through schema validation + numeric-range checks + the human gate. Directly attacks pain point #4.
- **Second-opinion / discrepancy flagger** — extract independently, compare to the deterministic extractor, route disagreements to human review. Raises recall of errors without being authoritative (Phase 3 dual-extractor).
- **Reviewer accelerator** — generate a plain-English "what changed" summary for the review UI ("front setback 6 m → 7 m in clause 4.2"), with the PDF crop shown so the human verifies against source.
- **Triage/classification** — "is this a scanned/garbage PDF?", "did a numeric control change?" — assistive, human decides.

**Must NOT do (liability + determinism):**
- Be the **system-of-record** for a cited value with no deterministic cross-check and no human review.
- Drive **change-detection / the diff**. LLMs are non-deterministic — the same PDF yields slightly different output, manufacturing phantom "changes." Keep the change signal deterministic (normalized-hash); use the LLM for extraction *assist* and review *acceleration*.
- Auto-commit anything. The human gate stays (conflicts with "deterministic processing only" if trusted blindly).

**Cost note:** Gemini Flash-class models are cheap enough to be cost-competitive with Azure DocIntel for the few hard councils, and the "propose → validate → human-approve" wrapper is what makes it defensible.

---

## 6. Premise checks (challenge before building)

- **Should DCP be PDF-extracted at all?** Yes, unavoidably. SEPP/LEP permissibility is queried live from the Planning Portal API; **DCP has no live API** — councils publish only PDFs. Stored extraction is the only path. (Prefer structured data if a council ever publishes it.)
- **Is the maintenance worth it?** The DCP extracted corpus is a high-maintenance "volatile skin." That's a *product* call, not an architecture one. This plan minimizes the maintenance cost; it doesn't decide whether DCP-depth is worth carrying.
- **How often must it run?** DCP amendments are quarterly–annual per council. The need is **reliability** (never miss one, never serve stale), not frequency. Over-frequent runs were the cost driver — keep cadence modest, make reliability loud.
- **Don't weaken the human gate.** "Named human approves before live" stays. Phase 1 makes that gate *faster and auditable*, not optional. Auto-commit of safe text-only changes is a possible future policy change — separate decision, with its own liability analysis.

---

## 7. Sources & cost/effort

| Phase | New infra cost | Effort | Removes |
|---|---|---|---|
| 0 | ~$0 (healthchecks free) | Hours | Orphaned-pipeline + rate-limit regressions from #506 |
| 1 | ~$0 (Supabase + existing frontend) | Days | Highest-liability silent failures (#2,#3,#5,#8) |
| 2 | ~$10/1k pp (or Gemini Flash), hard councils only | ~1 week | Per-council extraction toil (#4) |
| 3 | ~$0 self-host Prefect | Ongoing | Hand-rolled orchestration fragility |

**Do Phase 0 + 1 regardless** — pure regression-repair + cheapest removal of the worst liability modes.

Strongest external precedents: CourtListener/RECAP (content-hash + deterministic identity + idempotent retry), Open States (fail-loud + schema validation), UK Planning Data (standardize-and-validate, domain sibling), Ascent RegTech (highlighted old-vs-new diff + expert gate). Neutral extraction benchmark: arXiv 2410.09871 (DocLayNet).
