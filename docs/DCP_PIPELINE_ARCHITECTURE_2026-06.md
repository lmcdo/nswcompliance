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
- **[TEST] Pipeline-completeness gate (the #506-catcher).** A pytest test asserting every stage in a committed `dcp_pipeline_manifest` has a matching scheduled job (parse `run_monitors.MONITORS` + the baked Railway cron config). **Enforced by the existing pre-push `pytest tests/` gate** — drop a stage and the push blocks. Offline, fast, deterministic. This is the single check that would have caught #506; build it first. (See §5.3.)
- **[TEST] Real-endpoint smoke canary.** Extend the watchdog's ePlanning layer-health pattern to HEAD each council PDF source + R2 + verify ArcGIS layer IDs/schema, pinging healthchecks.io on success. **Enforced by the dead-man's-switch**, not pre-push (must not hit live gov servers on every push). Catches ETag/header drift, URL rot, layer-ID shift, WAF blocks. (See §5.3.)

### Phase 1 — Kill the highest-liability failure modes (days, ~$0). The "minimal change" bundle.
- **Per-provision normalized-text hash + numeric-token diff** — replace byte-hash / ETag-as-truth. Normalize away metadata/whitespace/headers; **never** normalize away digits/units/cell boundaries. Kills false-positive noise (#2/#3) and surfaces risky numeric changes.
- **Postgres review-queue table** — `stage` enum, atomic per-item commit, claim with `SELECT … FOR UPDATE SKIP LOCKED`, retry/backoff, **dead-letter → human** (never silent drop). Replaces "run a script" with durable, inspectable state. Guards #5/#8.
- **Dead-man's-switch v2** — beyond `HC_PING_URL`, add a "queue not stalled" check (alert if any row stuck `in_progress` > 1h). Catches a wedged stage even if cron keeps ticking.
- **Schema-validate every provision before commit** (Pandera/JSON-schema: clause format, units present, numeric ranges e.g. setback < ~30m). Blocks silent under-extraction / drift corruption before the live DB.
- **Diff-based review UI** — small Next.js page against the queue: old-vs-new + PDF page crop + the numeric diff. Goal: approve in ~30s from the diff alone.
- **[TEST] Golden-PDF regression corpus.** Commit a handful of real council PDF fixtures + their expected provision output; a pytest test extracts offline and asserts the result. **Enforced by the existing pre-push `pytest tests/` gate** — a pdfplumber bump or page-range edit that changes output blocks the push. Implements the domain framework's Golden tests at the *extraction* level. (See §5.3.)
- **[TEST] Silent-drop / Three-State adversity suite.** pytest tests for the documented failure modes: scanned/short PDF → abort; provision-count drop → escalate; source URL 404/redirect → escalate-not-skip; two-extractor disagreement → human; soft-delete scoped to the chapter (the 1,592-wipe guard); **auto-reject queues a human, never keeps stale (State-3 ≠ State-2)**. Pure-logic, **enforced by pre-push pytest**. One enforcement test per §5.2 invariant. (See §5.3.)

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

## 5.1 Review acceleration + the automation boundary (the correction)

**Confidence signals ≠ defensibility signals.** An earlier framing leaned on a blend of four confidence signals (structural stability, numeric-delta plausibility, double-extraction agreement, schema pass) as if they were the legal safeguard. They are not. They decide *where to point the human*; they do not constitute the legal defence. The two layers are distinct and both required.

### The boundary is two-dimensional (field-class first, confidence second)
A single confidence threshold is the wrong primary gate for cited legal data. The defensible boundary keys on **what kind of field changed**:

1. **Field-class gate (PRIMARY).** Any change to a **cited numeric value or clause identifier** (setback, height, FSR, parking rate, or the clause number it sits under) is **always human-required, regardless of confidence.** No score auto-commits this class. Cautionary precedent: Michigan's MiDAS auto-decided a high-liability class without human oversight → **93% error rate, ~20,000 people falsely accused.** Cited provisions are the MiDAS-risk class here.
2. **Confidence band (SECONDARY, only within the cosmetic/text-only class).** Auto-approve a change *only* if every numeric value and clause id is byte-identical to the prior version AND it passes schema validation AND double-extraction agreement AND structural-stability — i.e. genuinely cosmetic (whitespace, re-flow, punctuation). Everything else → human queue, sorted worst-first.
3. **Audit sample.** Even auto-approved cosmetic changes are logged and a ~5% random sample is re-checked (Pulse pattern), so the "safe" lane can't drift wrong unnoticed.

### The confidence signals, corrected
Keep the four — but as a *routing/ordering* aid, not a gate, with two fixes:
- **Double-extraction agreement is the strongest; build it first.** Run two extractors (e.g. pdfplumber table-parse vs text/regex). **Disagreement forces a human even if each path is internally "sure"** (ensemble disagreement drops real confidence 10–20%).
- **Schema-validation failure is a hard human-trigger, not a soft score.** Out-of-range value/unit → straight to human.
- Structural stability and numeric-delta plausibility remain useful triage inputs (an implausible delta like `6m → 600m` is more likely an extraction bug than a real amendment).

### What actually makes it legally defensible (the spine — aligns to the existing four-layer defence)
The defence is NOT a confidence score. It is, in order:
1. **Provenance / traceability** — store page + bounding-box + a **verbatim source crop** with every value ("clause 4.2 as it appears in the gazetted PDF, p.14"). This is Layer 1+2 of the four-layer defence and the thing Tepko/Butcher actually protect.
2. **Verbatim-not-interpreted** — the stored value is a literal transcription of source text (the "never interpret regulations" rule), deterministically checkable.
3. **Currency proof** — value extracted from the *current* document version (`content_hash == provisions_extracted_from_hash`) + `effective_date`. Serving a superseded provision as current is the Shaddock risk.
4. **Named-human-approval audit trail** — who approved, when, against which crop. In a dispute this *is* the defence.
5. **Confidence labelling + product framing** — amber "extracted — verify against source" badges, "screening only", "engage a planner" (four-layer defence Layers 2–3). Already decided in `ce-intelligence-brief-legal-reference.md`.

### Silent-drop prohibition (a defensibility requirement, not just hygiene)
**Auto-reject must escalate to a human — never silently keep the old value.** If re-extraction can't find a clause it previously had, two passes disagree, a delta is implausible, schema fails, *or a council's provision count drops sharply between runs*, that raises an alert and queues a human. A silent keep-stale is indistinguishable from MiDAS-style silent wrong-data and is the direct Shaddock exposure. Add a per-council record-count guard (sharp drop = halt + escalate, never auto-apply). The govtech analog (Open States) automates *detection + queueing* aggressively but **gates the commit** of the high-liability record.

### The "30-second review" UX + build recommendation
- One screen, reviewer never opens the full PDF: **old vs new** with word/number diff highlighted, a **pre-rendered PDF crop** of the source region beside the value, and a one-line plain-language summary ("front setback 6m → 7m, clause 4.2") generated *from the fields already computed* (old/new/clause — nothing for an LLM to hallucinate), shown above the crop the human verifies against.
- **Keyboard-first:** approve / reject / needs-info + next/prev + bulk-approve-cosmetic-batch. No mouse.
- **Build it in-app, not on an annotation tool.** Label Studio / Argilla / Prodigy are shaped for *creating annotations* and each forces a second service + two-way sync. Roll your own: a Supabase `pending_changes` table → a protected Next.js route → `react-diff-viewer-continued` for the value diff → a crop PNG (rendered by pdfplumber/pdf.js **at extraction time**, stored in Supabase Storage). The hard part (source-snippet beside value) none of the generic tools do for you anyway.

---

## 5.2 Operating model — least manual work, reliably, with integrity

Design target: the **only** recurring human task is approving/rejecting *flagged numeric-or-clause changes* from a pre-sorted queue — realistically minutes per month, since DCP amendments are quarterly–annual per council. Everything else runs unattended, and every unattended path is built to **fail loud**, never to fail silent.

### The one human touchpoint
- Open the review queue → for each flagged item, glance old-vs-new + crop + summary → `A`/`R`/`N`. Done.
- Nothing else requires you on the happy path. Cosmetic churn auto-clears; the queue only ever contains real, risky changes.

### Everything automated (unattended)
| Stage | Runs | Output |
|---|---|---|
| Detect | Railway cron, modest cadence | sets `needs_extraction` / writes `content_hash` |
| Extract-to-review | auto after detect (the step #506 deleted — restore it) | provisions extracted **in memory**, no live writes |
| Crop render + diff + summary | inside extract | `pending_changes` rows with crop PNG + numeric diff + plain summary |
| Cosmetic auto-approve + 5% sample | inside commit path | byte-identical-number changes committed; sample logged |
| Alerts | healthchecks + queue monitor | "review ready", "stage silent", "queue stalled", "count dropped" |

### Hard requirements (non-negotiable invariants — the integrity contract)
1. **Atomic per-item commit** — each provision set commits-or-not in one DB transaction; never half a chapter.
2. **Idempotency** — key items by `(council, chapter, content_hash, clause_id)`; claim queue rows with `SELECT … FOR UPDATE SKIP LOCKED`; re-runs are safe.
3. **Provenance stored on every value** — page + bbox + verbatim crop + source hash + extraction strategy + confidence. No value without its lineage.
4. **Schema-validate before commit** — type/unit/range per control; failure = hard human route, never a live write.
5. **Currency check** — only the current `content_hash` is treated as live; `effective_date` recorded.
6. **No silent drop** — auto-reject / "could not extract" / "row count dropped" all escalate + alert.
7. **Human gate on cited numbers** — field-class gate above; deterministic extractor is the system-of-record; LLM is presentation-only.
8. **Fail loud** — external dead-man's-switch (healthchecks.io, the unset `HC_PING_URL`) per stage + a "queue not stalled >1h" check. Silence trips an alarm.

### Constraints (the reality this must fit)
- **Cost ~$0 incremental.** Cost ($38.59/mo GitHub Actions) drove the migration that broke this. Build on what's paid for: Supabase, Railway cron, the existing Next.js app. Paid extraction (Azure/Gemini) only for the few hard councils, pay-per-use.
- **Solo operator.** No second system to babysit — the review surface lives *in* the existing app over Supabase, not a separate annotation service.
- **Railway single-IP.** Re-add per-council throttling/backoff (deleted by #506) so council CDNs don't WAF-block; stagger councils across cron offsets.
- **Determinism.** Deterministic processing is the system-of-record (project rule). LLM only writes human-facing summaries from already-computed fields and proposes extractions for hard councils — always validated + human-gated.

### Reliability mechanisms (what keeps it running without you watching)
- **Dead-man's-switch** per stage (alert on *absence* of a success ping) + **queue-not-stalled** monitor.
- **Retry/backoff with dead-letter → human** — transient failures retry; poison items escalate, never silently drop.
- **Record-count + freshness anomaly guards** per council — the "wrote zero rows, still green" class.
- **Quarantined per-council adapters** — a council's format break fails loud and in isolation (Open States "intentionally fragile"), without taking down the core.

### Failure-mode → guard (so "as intended" is enforced, not hoped)
| If this happens | Guard | Result |
|---|---|---|
| A stage silently stops | dead-man's-switch on success ping | alert within minutes |
| Re-extract loses a clause | count-drop guard + no-silent-drop | halt + human, stale value flagged |
| Scanned/garbage PDF | min-sections + 0-provision gate | escalate, never commit empty |
| Numeric mis-read | double-extraction disagreement → human | wrong number never auto-commits |
| Council CDN blocks | per-council throttle/backoff + WAF detect | ret/queue, alert on repeated failure |
| Cosmetic lane drifts wrong | 5% audit sample | caught on sample |

**Net:** maximal automation of detection, extraction-to-review, crop/diff/summary, cosmetic auto-clear, and alerting; minimal, pre-sorted human approval confined to the genuinely risky changes; integrity enforced by hard invariants and loud failure rather than vigilance.

---

## 5.3 Testing & verification requirements — enforced, not documented

**The rule:** a requirement written only in a doc is ignorable; the only requirement that holds is one a *gate blocks on*. So every item below names the gate that enforces it. (This is the project's own stated lesson — "enforce rules via hooks, not documentation" — applied here.)

**Why the current gates miss everything that matters here:** today's pre-push runs mocked-unit pytest (`conftest_mocks` stubs `requests`/`psycopg2`/`pyproj`), jest, a *self-authored* QA-report form-check, and a liability-language diff scan. All static or mocked. The pipeline's real failure surface — live HTTP, real PDFs, real DB writes, multi-stage orchestration, runtime alerting — is untouched. Not one recurring DCP bug in the history would have been caught. Closing that needs two enforcement tiers.

### Tier 1 — blocks at `git push` (no new hook machinery needed)
Anything deterministic + offline is a pytest test, and **the existing pre-push `pytest tests/` gate already runs and blocks on it.** The gap is that the tests don't exist — *writing them IS enforcing them.* Required tests:
- **Pipeline-completeness assertion** (Phase 0) — stages-manifest ↔ scheduled-jobs. The #506-catcher.
- **Golden-PDF regression corpus** (Phase 1) — real PDF fixtures → expected output; locks extraction against silent drift.
- **Silent-drop / Three-State / Safe-Default suite** (Phase 1) — every documented failure mode escalates, never serves stale-as-current; one test per §5.2 invariant.
- **Schema-contract tests** — every committed provision matches type/unit/range; a violation fails the build.

### Tier 2 — can't block at push, enforced by scheduled canary + dead-man's-switch
These need live network or a real DB, so they must NOT run on every push (slow, flaky, would hammer gov servers). The **dead-man's-switch IS the hook-equivalent for runtime**: the canary runs on Railway cron, pings healthchecks.io on success; failure *or silence* alerts loudly.
- **Real-endpoint smoke** — council PDFs + R2 + ArcGIS schema (extend the watchdog canary).
- **Real-DB integration** — soft-delete scope, atomic per-chapter commit, `SKIP LOCKED` claim, count-gate — run against a **scratch/staging DB on a schedule**, never prod, never mocked.
- **Alert-delivery canary** — prove Telegram + healthchecks actually fire and deliver (history: silently swallowed alerts).

### Meta-enforcement — ensuring the tests get *written*, not just *run*
"Make it un-ignorable" needs a gate on test *presence*, not just test *execution*:
- **Coverage-manifest ratchet** (mirrors the existing TSC-baseline + mutmut ratchet): a pre-push check that the required artifacts exist and are non-empty — a new pipeline stage with no completeness entry, no golden fixture, and no adversity test **fails the push**. This is how "you ignore everything not hook-enforced" gets structurally closed.
- **Mutation ratchet on the new suite** — a test that passes proves nothing if `return []` also passes it; the existing `MUTMUT=1` path should cover the new pipeline tests so weak tests are caught.

**Honest limit:** hooks can enforce *presence + pass + mutation-resistance*. They cannot enforce *judgment* (is the golden fixture representative? is the adversity case the right one?). That residual is the one thing left to process — `/code-review ultra` on liability changes (Gap A) — and should be the *only* thing relying on discipline. Everything else above is a gate.

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
