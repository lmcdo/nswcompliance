#!/usr/bin/env python3
"""Fleet measure: which council chapter PDFs print glyphs twice over themselves (the Campbelltown Part 3 defect). READ-ONLY.

prior-art-checked: scripts/visible_text_repair.white_report measures ONE PDF through PyMuPDF span colour; the extractor
reads with pdfplumber, where both copies are black fills (only the stroke colour differs), so this counts what the
extractor fix itself removes: characters dropped by pdfplumber's page.dedupe_chars(tolerance=1)
(scripts/dcp_extract_changed._drop_doubled_chars). Counts characters only; no text is extracted or written.

    python scripts/measure_doubled_chars.py --out data/doubled_chars_fleet_<date>.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def doubled_counts(pdf) -> dict:
    """{'chars': n, 'doubled': n removed by dedupe_chars, 'pages_with_doubled': n} over a pdfplumber PDF."""
    chars = doubled = pages = 0
    for page in pdf.pages:
        n = len(page.chars)
        d = n - len(page.dedupe_chars(tolerance=1).chars)
        chars += n
        doubled += d
        pages += d > 0
        page.flush_cache()
    return {"chars": chars, "doubled": doubled, "pages_with_doubled": pages}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "page_evidence_cache"))
    a = ap.parse_args()
    import pdfplumber
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import page_proof_council as ppc
    from state_law_proof import connect
    cur = connect().cursor()
    cur.execute("SELECT DISTINCT reg.council, reg.r2_current_path FROM dcp_chapter_registry reg WHERE reg.is_active "
                "AND reg.r2_current_path IS NOT NULL AND EXISTS (SELECT 1 FROM regulatory_provisions rp WHERE rp.is_current "
                "AND rp.v2_is_actionable AND rp.source_council = reg.council AND rp.source_chapter_key = reg.chapter_key) "
                "ORDER BY 1, 2")
    todo = cur.fetchall()
    tot = defaultdict(int)
    with open(a.out, "w", encoding="utf-8") as fh:
        for council, path in todo:
            rec = {"council": council, "path": path}
            try:
                with pdfplumber.open(str(ppc.local_pdf(path, Path(a.cache_dir) / "pdf"))) as pdf:
                    rec.update(doubled_counts(pdf), pages=len(pdf.pages))
            except Exception as e:  # noqa: BLE001 -- an unreadable PDF is reported, not fatal
                rec["error"] = f"{type(e).__name__}: {str(e)[:120]}"
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            tot["pdfs"] += 1
            tot["with_doubled"] += (rec.get("doubled") or 0) > 0
            tot["with_doubled_over_1pct"] += (rec.get("doubled") or 0) > 0.01 * max(rec.get("chars") or 0, 1)
            tot["errors"] += "error" in rec
            print(f"{tot['pdfs']}/{len(todo)} {council} {path.rsplit('/', 1)[-1]} "
                  f"chars={rec.get('chars')} doubled={rec.get('doubled')}", flush=True)
    print("TOTAL", dict(tot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
