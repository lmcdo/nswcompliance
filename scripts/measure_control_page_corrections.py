#!/usr/bin/env python3
# prior-art-checked: reuse not viable as a new capability -- the comparison core is IMPORTED
# from scripts/validate_controls_against_source_pdf.py rather than reimplemented, and the R2
# path is that module's, itself reused from numeric_control_review.py. Nothing else proposes
# a pdf_page correction: numeric_control_review.py diffs VALUES for a human to read and never
# touches pdf_page; validate_control_source_values.py (#868) and validate_controls_provenance.py
# (#866) never open a document; repair_camden_front_setbacks.py and repair_canada_bay_rear_setback.py
# are single-row value repairs. Four sweeps run 2026-08-09 against origin/main f5acb080.
"""Where does each control's number ACTUALLY appear, and is that one place unambiguous?

MEASURE HALF. Writes nothing to the database. Produces a proposal file that a separate,
guarded write step consumes.

WHY THIS IS NOT JUST "USE found_on_page"
----------------------------------------
The checker reports the FIRST page carrying the value with enough matching words. On a
1,563-page document that first hit can be a coincidence, and the observed offsets include
+194, -103 and -127 -- distances that are far more likely to be an unrelated page using the
same number than a genuine pagination error. Writing those into production would replace a
wrong page reference with a differently wrong one, which is worse: it looks repaired.

So a correction is proposed ONLY when the whole document contains EXACTLY ONE page carrying
the control's value with high term coverage. One candidate is evidence. Two or more is a
coincidence risk, and zero means the number is not in this document at all. Both of those
are reported and neither is ever proposed.

STATES, kept distinct rather than collapsed
-------------------------------------------
    already_correct        cited page (+/-1) carries it; nothing to do
    single_candidate       exactly one page in the document carries it -> PROPOSED
    ambiguous              several pages carry it -> reported, NOT proposed
    not_in_document        no page carries it -> reported, NOT proposed (see the 12)
    not_testable           no number to look for, or no text layer, or no document

Read-only. Prints no secret values.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import fitz  # module scope: absent library must be RED, never a quiet skip

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from validate_controls_against_source_pdf import (  # noqa: E402
    PAGE_TOLERANCE,
    ROWS_SQL,
    TERM_COVERAGE_MIN,
    connect,
    distinctive_terms,
    download_from_r2,
    normalise,
    numeric_tokens,
    page_supports,
    read_pages,
    required_values,
)

# Served controls that carry a number but NO page at all (2026-09-26: 18 council rows). With
# its clause withheld as unproven, such a number would be cited by nothing but a link.
MISSING_PAGE_SQL = """
    SELECT c.id, c.lga, c.control_type, c.source_text, c.pdf_page, g.r2_current_path,
           c.value_min, c.value_max, c.unit
    FROM dcp_setback_controls c
    JOIN dcp_chapter_registry g
      ON g.council = c.lga AND g.chapter_key = c.source_chapter_key AND g.is_active
    WHERE c.pdf_page IS NULL
      AND c.is_current = TRUE
      AND (c.needs_review IS NULL OR c.needs_review = FALSE)
      AND (c.value_min IS NOT NULL OR c.value_max IS NOT NULL)
      AND g.r2_current_path IS NOT NULL AND g.r2_current_path <> ''
    ORDER BY c.lga, g.r2_current_path, c.id
"""

# A correction must clear a higher bar than a report: the same value+terms test, but the
# only page in the document that passes it.
STRONG_COVERAGE = 0.80


def main() -> int:
    ap = argparse.ArgumentParser(description="Propose pdf_page corrections (no writes)")
    ap.add_argument("--cache", default=None)
    ap.add_argument("--out", default="data/control_page_corrections_proposal.json")
    ap.add_argument("--missing-page-only", action="store_true",
                    help="only served numbers with NO page: search the whole document for it")
    args = ap.parse_args()

    import tempfile
    cache = Path(args.cache) if args.cache else Path(tempfile.gettempdir()) / "dcp_pdf_cache"
    cache.mkdir(parents=True, exist_ok=True)

    conn = connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '60s'")
    cur.execute(MISSING_PAGE_SQL if args.missing_page_only else ROWS_SQL)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    by_doc: dict[str, list] = {}
    for r in rows:
        by_doc.setdefault(r[5], []).append(r)

    print(f"{len(rows)} controls across {len(by_doc)} documents")
    print(f"a correction is proposed only where EXACTLY ONE page carries the value "
          f"with >={STRONG_COVERAGE:.0%} term coverage\n")

    states: Counter[str] = Counter()
    proposals: list[dict] = []
    reported: list[dict] = []

    for n, (r2_path, doc_rows) in enumerate(sorted(by_doc.items()), 1):
        pdf = download_from_r2(r2_path, cache)
        if pdf is None:
            states["not_testable"] += len(doc_rows)
            continue
        pages, count = read_pages(pdf)
        basename = (r2_path or "").rstrip("/").rsplit("/", 1)[-1] or "(unnamed document)"
        print(f"[{n}/{len(by_doc)}] {basename} ({count}pp, {len(doc_rows)} controls)")

        # ROWS_SQL gained `unit` after this was written; *_ keeps the unpack from breaking.
        for cid, lga, ct, quote, cited, _p, vmin, vmax, *_ in doc_rows:
            if not quote or (cited is None and not args.missing_page_only):
                states["not_testable"] += 1
                continue
            if not required_values(vmin, vmax) and not numeric_tokens(quote):
                states["not_testable"] += 1
                continue

            window = [] if cited is None else [
                p for p in range(cited - PAGE_TOLERANCE, cited + PAGE_TOLERANCE + 1) if p >= 1]
            if window and any(page_supports(quote, pages.get(p, ""), vmin, vmax)[0] for p in window):
                states["already_correct"] += 1
                continue

            hits = []
            for p, text in pages.items():
                ok, cov, _ = page_supports(quote, text, vmin, vmax)
                if ok and cov >= STRONG_COVERAGE:
                    hits.append((p, cov))

            base = {"id": cid, "lga": lga, "control_type": ct, "cited_page": cited,
                    "document": r2_path, "document_pages": count,
                    "quote": (quote or "")[:160]}
            if len(hits) == 1:
                p, cov = hits[0]
                states["single_candidate"] += 1
                proposals.append({**base, "proposed_page": p,
                                  "offset": None if cited is None else p - cited,
                                  "term_coverage": round(cov, 3)})
            elif len(hits) > 1:
                states["ambiguous"] += 1
                reported.append({**base, "state": "ambiguous",
                                 "candidate_pages": [p for p, _ in hits][:12]})
            else:
                states["not_in_document"] += 1
                reported.append({**base, "state": "not_in_document"})

    print(f"\n{'=' * 78}\nSTATES\n{'=' * 78}")
    for k, v in states.most_common():
        print(f"  {k:<22} {v:>4}")

    print(f"\n{'=' * 78}\nPROPOSED CORRECTIONS ({len(proposals)}) — one candidate page each\n{'=' * 78}")
    for p in sorted(proposals, key=lambda x: (x["lga"], x["id"])):
        print(f"  id={p['id']:<6} {p['lga']:<16} {p['control_type']:<24} "
              f"page {p['cited_page']} -> {p['proposed_page']}  "
              f"({'new' if p['offset'] is None else format(p['offset'], '+d')}, "
              f"cov {p['term_coverage']:.0%})")

    amb = [r for r in reported if r["state"] == "ambiguous"]
    if amb:
        print(f"\n--- NOT proposed, several pages carry it ({len(amb)}) ---")
        for r in amb:
            print(f"  id={r['id']:<6} {r['lga']:<16} cites {r['cited_page']}, "
                  f"candidates {r['candidate_pages']}")

    out = REPO_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"generated_against": "origin/main f5acb080",
         "rule": f"proposed only where exactly one page carries the value with "
                 f">={STRONG_COVERAGE} term coverage; ambiguous and absent are never proposed",
         "states": dict(states), "proposals": proposals, "reported": reported},
        indent=2), encoding="utf-8")
    print(f"\nproposal written: {out.relative_to(REPO_ROOT)}")
    print("NOTHING WAS WRITTEN TO THE DATABASE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
