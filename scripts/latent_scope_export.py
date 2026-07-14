#!/usr/bin/env python3
"""Read-only export of regulatory provisions for latent-scope analysis.

prior-art-checked: reuse not viable — the existing provisions surfaces
(frontend-nextjs/app/api/provisions/* routes, ProvisionsByTocStructure.tsx,
sepp_full_text_extraction/02_parse_markdown_to_json.py) are per-property /
per-change serving APIs and an extraction-time markdown parser. None does a
read-only bulk export of the live table to a flat file for offline embedding.
This is a new analysis-lane capability, not a serving path.

This is an *analysis-lane* utility. It never writes to the database and never
sends provision text off-box: it runs a single ``SELECT`` against
``regulatory_provisions`` inside a ``READ ONLY`` transaction and writes a local
flat file (parquet or CSV) that latent-scope's ``ls-ingest`` can consume.

Provision text is public NSW regulatory data, but per the project rules the
export stays on disk — nothing here calls an external API. Downstream embedding
is done separately (see ``docs/latent_scope_runbook.md``); prefer the local
sentence-transformers embedder to keep the whole pipeline egress-free.

Usage examples
--------------
    # Every actionable provision for one council -> parquet
    python scripts/latent_scope_export.py --council Marrickville --actionable-only

    # Whole table (all 46k rows) -> csv, capped for a quick smoke test
    python scripts/latent_scope_export.py --format csv --limit 2000

Environment: reuses the project DB connection (``DB_HOST`` / ``DB_NAME`` /
``DB_USER`` / ``DB_PASSWORD`` / ``DB_PORT`` via ``services/db_config.py``).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

# Make the project's DB helper importable regardless of CWD.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "services"))

# Columns exported. `provision_text` is the embeddable text; the rest are
# metadata used for latent-scope's colour-by (topic/council/precinct) and for
# the duplicate-audit worklist. Keep this list in sync with the runbook.
EXPORT_COLUMNS: Tuple[str, ...] = (
    "id",
    "provision_text",
    "v2_topic",
    "v2_marker",
    "v2_is_actionable",
    "is_current",  # currency flag — exported so staleness is visible, not hidden
    "v2_applicable_dev_types",
    "former_council",
    "v2_precinct_id",
    "v2_dcp_part",
    "source_ref",
    "pdf_page_image_url",
)

DEFAULT_OUT = _REPO_ROOT / "data" / "latent_scope" / "provisions.parquet"


def _build_query(
    councils: Optional[Sequence[str]],
    actionable_only: bool,
    current_only: bool,
    min_chars: int,
    limit: Optional[int],
) -> Tuple[str, List[object]]:
    """Build a parameterised read-only SELECT and its params.

    Currency note: ``regulatory_provisions.is_current`` is *exported as a column*
    (see ``EXPORT_COLUMNS``) rather than force-filtered, so a QA pass can see and
    colour-by stale rows instead of them being silently dropped — surfacing
    superseded provisions is a goal of this tool, not a bug. Pass
    ``current_only=True`` to restrict to live rows (``is_current = TRUE``).

    Args:
        councils: If given, restrict to these ``former_council`` values.
        actionable_only: If True, only ``v2_is_actionable = TRUE`` rows.
        current_only: If True, only ``is_current = TRUE`` (live) rows.
        min_chars: Drop provisions whose trimmed text is shorter than this.
        limit: Optional row cap (applied after ordering by id).

    Returns:
        A ``(sql, params)`` tuple ready for ``cursor.execute``.
    """
    cols = ", ".join(EXPORT_COLUMNS)
    where = [
        "provision_text IS NOT NULL",
        "length(btrim(provision_text)) >= %s",
    ]
    params: List[object] = [max(min_chars, 1)]

    if current_only:
        where.append("is_current = TRUE")

    if actionable_only:
        where.append("v2_is_actionable = TRUE")

    if councils:
        where.append("former_council = ANY(%s)")
        params.append(list(councils))

    sql = f"SELECT {cols} FROM regulatory_provisions WHERE " + " AND ".join(where)
    # Currency: is_current is SELECTed (see EXPORT_COLUMNS) so staleness stays
    # visible to the QA pass; --current-only adds `is_current = TRUE` above when
    # only live rows are wanted. Stale provisions are surfaced, never hidden.
    sql += " ORDER BY id"
    if limit is not None:
        sql += " LIMIT %s"
        params.append(limit)
    return sql, params


def fetch_provisions(
    councils: Optional[Sequence[str]],
    actionable_only: bool,
    current_only: bool,
    min_chars: int,
    limit: Optional[int],
) -> Tuple[List[str], List[tuple]]:
    """Run the read-only export query and return ``(columns, rows)``.

    The connection is pinned to ``READ ONLY`` before any statement runs, so a
    stray non-SELECT would raise rather than mutate the database.

    prior-art-checked: extends this module's own exporter (justification in the
    module docstring); adds a currency filter, no new capability.
    """
    from db_config import get_connection  # imported lazily so --help needs no DB

    sql, params = _build_query(
        councils, actionable_only, current_only, min_chars, limit
    )
    conn = get_connection()
    try:
        # Hard guard: no write can succeed on this session.
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        return columns, rows
    finally:
        conn.close()


def write_output(
    columns: Sequence[str],
    rows: Sequence[tuple],
    out_path: Path,
    fmt: str,
) -> Path:
    """Write rows to parquet or CSV, creating the parent directory.

    Falls back to CSV if parquet is requested but pyarrow is unavailable, so the
    export never hard-fails on a missing optional dependency.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "parquet":
        try:
            import pandas as pd

            df = pd.DataFrame.from_records(list(rows), columns=list(columns))
            df.to_parquet(out_path, index=False)
            return out_path
        except (ImportError, ValueError) as exc:
            csv_path = out_path.with_suffix(".csv")
            print(
                f"[warn] parquet unavailable ({exc}); writing CSV -> {csv_path}",
                file=sys.stderr,
            )
            out_path = csv_path

    # CSV path (default fallback and explicit --format csv).
    import csv

    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        writer.writerows(rows)
    return out_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only export of regulatory_provisions for latent-scope.",
    )
    parser.add_argument(
        "--council",
        action="append",
        default=None,
        metavar="NAME",
        help="Restrict to a former_council (repeatable, e.g. --council Marrickville).",
    )
    parser.add_argument(
        "--actionable-only",
        action="store_true",
        help="Only rows with v2_is_actionable = TRUE.",
    )
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="Only live rows (is_current = TRUE). Off by default so a QA pass "
        "can see superseded provisions; is_current is exported either way.",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=1,
        help="Drop provisions shorter than N characters (default: 1).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of rows exported (default: no cap).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output path (default: {DEFAULT_OUT}).",
    )
    parser.add_argument(
        "--format",
        choices=("parquet", "csv"),
        default="parquet",
        help="Output format (default: parquet).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    out_path = args.out
    if args.format == "csv" and out_path.suffix != ".csv":
        out_path = out_path.with_suffix(".csv")

    columns, rows = fetch_provisions(
        councils=args.council,
        actionable_only=args.actionable_only,
        current_only=args.current_only,
        min_chars=args.min_chars,
        limit=args.limit,
    )

    if not rows:
        print(
            "[warn] query returned 0 rows — check --council spelling / filters.",
            file=sys.stderr,
        )
        return 1

    written = write_output(columns, rows, out_path, args.format)
    scope = ", ".join(args.council) if args.council else "all councils"
    print(f"Exported {len(rows):,} provisions ({scope}) -> {written}")
    print("Local analysis artifact only — do not commit; not for DB writeback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
