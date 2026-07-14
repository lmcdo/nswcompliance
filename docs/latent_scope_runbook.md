# latent-scope Analysis Lane — Runbook

A local, offline instrument for **inspecting and QA-ing `regulatory_provisions`**
as a whole. It is not a production dependency and writes nothing back to the
database. Use it to answer questions the row-by-row pipeline can't show you:

- **Classifier QA** — which provisions are mislabelled (`v2_topic` /
  `v2_is_actionable`) relative to their semantic neighbours?
- **Duplication / contradiction** — which controls are copied across
  councils/precincts, and where does near-identical wording carry *different*
  numeric standards (a 3 m vs 4.5 m setback)?
- **Coverage** — which topics exist for one council but are absent for another?

It wraps [`enjalot/latent-scope`](https://github.com/enjalot/latent-scope):
`ingest → embed → umap → cluster → label → scope → serve`, an interactive 2D map
at `localhost:5001`.

---

## Guardrails (read before running)

1. **Read-only DB.** `latent_scope_export.py` pins the connection to
   `READ ONLY`. It only ever runs a `SELECT`. Never add a writeback path here —
   corrections go back through the normal enrichment pipeline with human review.
2. **No egress by default.** Provision text is public regulatory data, but keep
   it on-box: use the local embedder. `--embedder tfidf` needs no network at
   all; the default sentence-transformers embedder downloads a model **once**
   from Hugging Face, then runs locally. Do **not** point `ls-embed` at OpenAI /
   Cohere unless you have a specific reason.
3. **Outputs are disposable.** Everything lands under `data/latent_scope/` and
   `latent-scope-data/`, both git-ignored. Nothing here is a source of truth;
   the audit CSV is a *review worklist*.
4. **IP hygiene.** If you screenshot or share a map, don't leak internal
   pipeline/algorithm names into anything public (see
   `.claude/rules/blog-content.md`).

---

## One-time setup

latent-scope pulls `torch` + `umap-learn` + `hdbscan` (multi-GB). Install it in
a **separate venv** so it never touches `venv_linux` / the API environment.

```bash
python -m venv .venv-latentscope
# Windows:
.venv-latentscope/Scripts/activate
# macOS/Linux:
source .venv-latentscope/bin/activate

pip install -r requirements-latentscope.txt
```

The DB export step (`latent_scope_export.py`) only needs `psycopg2` +
`pandas`/`pyarrow`, which the main backend env already has — you can run the
export from `venv_linux` and the rest from `.venv-latentscope`.

---

## Step 1 — Export provisions (read-only)

Run where the DB env vars are set (`DB_HOST` / `DB_NAME` / `DB_USER` /
`DB_PASSWORD` / `DB_PORT`).

```bash
# One council, actionable provisions only (good first slice):
python scripts/latent_scope_export.py --council Marrickville --actionable-only

# The whole table (46k rows) as parquet:
python scripts/latent_scope_export.py

# CSV, capped for a quick smoke test:
python scripts/latent_scope_export.py --format csv --limit 2000
```

Output → `data/latent_scope/provisions.parquet` (git-ignored). Columns:
`id, provision_text, v2_topic, v2_marker, v2_is_actionable, is_current,
v2_applicable_dev_types, former_council, v2_precinct_id, v2_dcp_part,
source_ref, pdf_page_image_url`.

`is_current` is exported (not force-filtered) so a QA pass can **see** stale /
superseded provisions — colour-by `is_current` on the map to spot them. Pass
`--current-only` if you want live rows only.

---

## Step 2 — Duplicate / contradiction audit (no web UI needed)

This is the highest-signal, fully-scriptable use. It reads the export and emits
a ranked worklist without you having to open the map.

```bash
# Offline (no network) — good default for copied boilerplate:
python scripts/latent_scope_dup_audit.py --embedder tfidf --min-cosine 0.90

# Semantic embedder (downloads bge-small once, then local):
python scripts/latent_scope_dup_audit.py --embedder sentence-transformers
```

Output → `data/latent_scope/dup_worklist.csv`, sorted with
**`numeric_mismatch` pairs first** (near-identical text, different numbers =
candidate contradiction), then by descending cosine similarity. Columns include
both provision ids, councils, precincts, topics, the extracted numeric tokens,
and truncated text for each side.

Cross-council/cross-precinct pairs are reported by default (the interesting
ones). Add `--include-same-scope` to also see duplicates within a single
council+precinct.

**What to do with it:** exact-match cross-precinct pairs are canonicalisation
candidates; `numeric_mismatch=True` rows are the ones to eyeball for genuine
contradictions. Apply any fixes through the normal enrichment pipeline — this
tool never edits the data.

---

## Step 3 — Interactive map (classifier-QA)

For the visual mislabel hunt, run the full latent-scope pipeline and open the
map. Set the data directory once:

```bash
export LATENT_SCOPE_DATA=./latent-scope-data   # Windows: set LATENT_SCOPE_DATA=...

ls-ingest provisions data/latent_scope/provisions.parquet --text_column provision_text

# Local embedder (no per-row egress). See `ls-list-models` for options.
ls-embed provisions provisions BAAI/bge-small-en-v1.5

ls-umap    provisions provisions 25 0.1
ls-cluster provisions provisions-umap-001 --method hdbscan
ls-label   provisions provisions-cluster-001 --model <local-or-skip>
ls-scope   provisions provisions-embedding-001 provisions-umap-001 provisions-cluster-001
ls-serve
```

Open `http://localhost:5001`, load the `provisions` dataset, then:

- **Color by `v2_topic`.** A point coloured "parking" sitting deep inside a
  tight "heritage" cluster is a visually obvious mislabel.
- **Color by `v2_is_actionable`.** Actionable=false points buried in an
  otherwise-actionable cluster are re-tagging candidates.
- **Lasso** the misfits → export their `id`s → feed back as a re-tagging
  worklist through the enrichment pipeline.

> If Hugging Face egress is blocked in your environment, the POC that seeded
> this tooling used a local TF-IDF+SVD embedder instead — `ls-embed` supports
> OpenAI-compatible endpoints, or use `scripts/latent_scope_dup_audit.py
> --embedder tfidf` for the offline audit path.

---

## Notes on scale

- The dup audit uses a k-nearest-neighbour search (not a full N×N matrix), so it
  scales to the full 46k rows. Tune breadth with `--top-k` and strictness with
  `--min-cosine`.
- `ls-umap` / `ls-cluster` on 46k rows are fine on CPU; set
  `LATENT_SCOPE_DEVICE` for cuML GPU acceleration if available.
- The `numeric_mismatch` flag is a heuristic (regex over number+unit tokens). It
  surfaces *candidates* for review — it does not assert a contradiction.
