#!/usr/bin/env python3
"""Near-duplicate & contradiction audit over exported provisions.

prior-art-checked: reuse not viable — flagged matches are token coincidences.
NumericChecker.tsx / numericCompliance.ts check one property's value against a
control; design-tokens.ts is CSS; worksScope.ts is SEE scope; app/embed is an
iframe layout. None does corpus-wide semantic near-duplicate detection across
provisions. This is a new offline analysis capability.

Reads the flat file produced by ``latent_scope_export.py`` and emits a ranked
canonicalisation worklist: pairs of provisions whose text is near-identical in
embedding space. Two things fall out of that:

  * duplicated boilerplate copied across councils/precincts (merge candidates);
  * *contradictions* — near-identical wording carrying different numeric
    standards (e.g. a 3 m vs 4.5 m setback). These are flagged, never resolved:
    the output is a human review worklist, not a source of truth.

The embedder is pluggable so the whole pipeline can stay egress-free:

  * ``sentence-transformers`` (default, ``BAAI/bge-small-en-v1.5``) — a real
    semantic embedder; downloads the model once from Hugging Face, then local.
  * ``tfidf`` — TF-IDF + truncated SVD, fully local/offline. Use this when HF
    egress is blocked; regulatory text reuses exact phrasing, so lexical
    similarity already surfaces most copied boilerplate.

This is analysis only: it reads a local file and writes a local CSV. It touches
neither the database nor any external service (beyond the one-time model
download when ``--embedder sentence-transformers`` is chosen).

Usage
-----
    python scripts/latent_scope_dup_audit.py \
        --input data/latent_scope/provisions.parquet \
        --min-cosine 0.90 --embedder tfidf
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import FrozenSet, List, Optional, Sequence, Tuple

import numpy as np

# --- Numeric-standard extraction (for the contradiction flag) ---------------
# Capture a number immediately followed by a planning unit. Unit synonyms are
# normalised so "metres"/"m"/"meters" collapse to one token.
_NUM_UNIT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*"
    r"(m²|m2|sqm|mm|km|m|metres|meters|metre|meter|%|percent|"
    r"storeys|storey|degrees|degree|°)",
    re.IGNORECASE,
)
_UNIT_CANON = {
    "metres": "m", "meters": "m", "metre": "m", "meter": "m", "m": "m",
    "m²": "m2", "m2": "m2", "sqm": "m2",
    "percent": "%", "%": "%",
    "storey": "storeys", "storeys": "storeys",
    "degree": "deg", "degrees": "deg", "°": "deg",
    "mm": "mm", "km": "km",
}


def numeric_tokens(text: str) -> FrozenSet[str]:
    """Return the set of ``value+unit`` tokens in a provision (e.g. ``4.5m``)."""
    out = set()
    for value, unit in _NUM_UNIT_RE.findall(text or ""):
        canon = _UNIT_CANON.get(unit.lower(), unit.lower())
        # Normalise trailing-zero noise: 4.50 -> 4.5, 3.0 -> 3.
        num = value.rstrip("0").rstrip(".") if "." in value else value
        out.add(f"{num}{canon}")
    return frozenset(out)


# --- Embedders --------------------------------------------------------------
def embed_sentence_transformers(texts: Sequence[str], model_name: str) -> np.ndarray:
    """Embed with a sentence-transformers model (downloaded once, then local)."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - environment guard
        raise SystemExit(
            "sentence-transformers not installed. Install the analysis deps "
            "(pip install -r requirements-latentscope.txt) or use --embedder tfidf."
        ) from exc
    model = SentenceTransformer(model_name)
    vecs = model.encode(
        list(texts),
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    return np.asarray(vecs, dtype=np.float32)


def embed_tfidf(texts: Sequence[str], dims: int = 256) -> np.ndarray:
    """Embed fully offline with TF-IDF + truncated SVD, L2-normalised."""
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    tfidf = TfidfVectorizer(
        lowercase=True, stop_words="english", ngram_range=(1, 2), min_df=2
    )
    matrix = tfidf.fit_transform(texts)
    n_components = min(dims, matrix.shape[1] - 1, max(matrix.shape[0] - 1, 1))
    if n_components < 2:
        # Degenerate corpus (tiny sample): fall back to the raw tfidf rows.
        return normalize(matrix).toarray().astype(np.float32)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    reduced = svd.fit_transform(matrix)
    return normalize(reduced).astype(np.float32)


def embed(texts: Sequence[str], embedder: str, model_name: str) -> np.ndarray:
    if embedder == "sentence-transformers":
        return embed_sentence_transformers(texts, model_name)
    if embedder == "tfidf":
        return embed_tfidf(texts)
    raise ValueError(f"unknown embedder: {embedder}")


# --- Pairing ----------------------------------------------------------------
def find_pairs(
    vecs: np.ndarray,
    min_cosine: float,
    top_k: int,
) -> List[Tuple[int, int, float]]:
    """Return ``(i, j, cosine)`` pairs with cosine >= threshold, i < j.

    Uses a k-nearest-neighbour search (cosine) rather than a full N×N matrix so
    it scales to the whole 46k-row table.
    """
    from sklearn.neighbors import NearestNeighbors

    n = vecs.shape[0]
    k = min(top_k + 1, n)  # +1 because the nearest neighbour is the point itself
    nn = NearestNeighbors(n_neighbors=k, metric="cosine")
    nn.fit(vecs)
    distances, indices = nn.kneighbors(vecs)

    seen = set()
    pairs: List[Tuple[int, int, float]] = []
    for i in range(n):
        for dist, j in zip(distances[i], indices[i]):
            if i == j:
                continue
            cosine = 1.0 - float(dist)
            if cosine < min_cosine:
                continue
            key = (i, j) if i < j else (j, i)
            if key in seen:
                continue
            seen.add(key)
            pairs.append((key[0], key[1], cosine))
    pairs.sort(key=lambda p: p[2], reverse=True)
    return pairs


# --- IO ---------------------------------------------------------------------
def load_frame(input_path: Path):
    import pandas as pd

    if input_path.suffix == ".parquet":
        return pd.read_parquet(input_path)
    return pd.read_csv(input_path)


def build_worklist(df, pairs: Sequence[Tuple[int, int, float]], cross_scope_only: bool):
    """Assemble the ranked worklist rows from candidate pairs."""
    import pandas as pd

    text_col = "provision_text"
    council_col = "source_council"
    precinct_col = "v2_precinct_id"
    topic_col = "v2_topic"

    numbers = [numeric_tokens(t) for t in df[text_col].tolist()]
    records = []
    for i, j, cosine in pairs:
        row_i, row_j = df.iloc[i], df.iloc[j]
        council_a, council_b = row_i.get(council_col), row_j.get(council_col)
        precinct_a, precinct_b = row_i.get(precinct_col), row_j.get(precinct_col)

        cross_council = council_a != council_b
        cross_precinct = precinct_a != precinct_b
        if cross_scope_only and not (cross_council or cross_precinct):
            continue

        nums_a, nums_b = numbers[i], numbers[j]
        numeric_mismatch = bool(nums_a ^ nums_b) and bool(nums_a) and bool(nums_b)

        records.append(
            {
                "cosine": round(cosine, 4),
                "numeric_mismatch": numeric_mismatch,
                "cross_council": cross_council,
                "cross_precinct": cross_precinct,
                "id_a": row_i.get("id"),
                "id_b": row_j.get("id"),
                "council_a": council_a,
                "council_b": council_b,
                "precinct_a": precinct_a,
                "precinct_b": precinct_b,
                "topic_a": row_i.get(topic_col),
                "topic_b": row_j.get(topic_col),
                "numbers_a": " ".join(sorted(nums_a)),
                "numbers_b": " ".join(sorted(nums_b)),
                "text_a": _truncate(row_i.get(text_col)),
                "text_b": _truncate(row_j.get(text_col)),
            }
        )
    # Contradictions first (numeric_mismatch), then by descending similarity.
    worklist = pd.DataFrame.from_records(records)
    if not worklist.empty:
        worklist = worklist.sort_values(
            ["numeric_mismatch", "cosine"], ascending=[False, False]
        ).reset_index(drop=True)
    return worklist


def _truncate(text: Optional[str], limit: int = 240) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Near-duplicate / contradiction audit over exported provisions.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/latent_scope/provisions.parquet"),
        help="Export file from latent_scope_export.py (parquet or csv).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/latent_scope/dup_worklist.csv"),
        help="Output worklist CSV.",
    )
    parser.add_argument(
        "--embedder",
        choices=("sentence-transformers", "tfidf"),
        default="sentence-transformers",
        help="Embedding backend (default: sentence-transformers; tfidf = offline).",
    )
    parser.add_argument(
        "--model",
        default="BAAI/bge-small-en-v1.5",
        help="Model for --embedder sentence-transformers.",
    )
    parser.add_argument(
        "--min-cosine",
        type=float,
        default=0.90,
        help="Minimum cosine similarity to report a pair (default: 0.90).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Neighbours considered per provision (default: 10).",
    )
    parser.add_argument(
        "--include-same-scope",
        action="store_true",
        help="Also report pairs within the same council AND precinct.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if not args.input.exists():
        print(f"[error] input not found: {args.input}", file=sys.stderr)
        print("Run latent_scope_export.py first.", file=sys.stderr)
        return 2

    df = load_frame(args.input)
    df = df[df["provision_text"].notna()].reset_index(drop=True)
    n = len(df)
    if n < 2:
        print(f"[error] need >=2 provisions, got {n}.", file=sys.stderr)
        return 2

    print(f"Embedding {n:,} provisions via {args.embedder} …", file=sys.stderr)
    vecs = embed(df["provision_text"].tolist(), args.embedder, args.model)

    pairs = find_pairs(vecs, args.min_cosine, args.top_k)
    worklist = build_worklist(df, pairs, cross_scope_only=not args.include_same_scope)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    worklist.to_csv(args.out, index=False)

    n_pairs = len(worklist)
    n_contra = int(worklist["numeric_mismatch"].sum()) if n_pairs else 0
    print(
        f"Wrote {n_pairs:,} candidate pairs "
        f"({n_contra:,} with differing numeric standards) -> {args.out}"
    )
    print("Review worklist — merge/canonicalise via the normal pipeline; no auto-writeback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
