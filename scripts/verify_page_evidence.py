#!/usr/bin/env python3
# prior-art-checked: no existing verifier of page evidence; counterpart of page_proof_council.py.
"""Re-derive every page proof in a data/page_evidence_<date>.jsonl from the PDF alone.

For each line: (1) the PDF is the pinned one -- its sha256 equals the recorded one; (2) the
evidence's own location (page, order or table + cells, char offsets) holds EXACTLY the recorded
span; (3) the span's sha256 matches; (4) the span is on no other page of the PDF (unless
--no-unique); (5) the plan's page is the evidence's page and its verdict follows from the old
page. With --db the row's provision_text must still hash to the recorded md5 and its words
must equal the span. Exit 1 on any mismatch, 2 when nothing could be verified.

  python scripts/verify_page_evidence.py data/page_evidence_2026-10-17.jsonl [--pdf-dir DIR] [--db]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import page_evidence as pe  # noqa: E402


def _boundary(hay: str, s: int, e: int) -> bool:
    return (s == 0 or hay[s - 1] == " ") and (e == len(hay) or hay[e] == " ")


def check_evidence(ev: dict, page, words_sha: str | None = None) -> list:
    """Problems re-deriving ONE proof on a fitz page ([] = holds). Pure over the page."""
    bad = []
    span = ev.get("span")
    if not span:
        return ["evidence has no span"]
    if hashlib.sha256(span.encode()).hexdigest() != ev.get("span_sha256"):
        bad.append("span_sha256 does not match span")
    if len(span.split()) < pe.MIN_WORDS:
        bad.append("span shorter than MIN_WORDS")
    s, e = ev.get("start"), ev.get("end")
    if not isinstance(s, int) or not isinstance(e, int) or e - s != len(span):
        return bad + ["start/end do not frame the span"]
    if ev.get("matcher") == "text-run":
        if ev.get("order") not in pe.ORDERS:
            return bad + ["unknown reading order"]
        hay = pe.page_texts(page)[ev["order"]]
    elif ev.get("matcher") == "table-cells":
        grids = pe.page_tables(page)
        t = ev.get("table")
        if not isinstance(t, int) or not 0 <= t < len(grids):
            return bad + ["table index not on the page"]
        grid, cells = grids[t], ev.get("cells") or []
        parts = []
        for rc in cells:
            if (len(rc) != 2 or not all(isinstance(x, int) and x >= 0 for x in rc)):
                return bad + [f"cell coordinate {rc} is not a non-negative [row, col]"]
        for r, c in cells:
            if r >= len(grid) or c >= len(grid[r]) or grid[r][c] is None:
                return bad + [f"cell {r},{c} missing or merged (None)"]
            w = pe.normalise(grid[r][c])
            if not w:
                return bad + [f"cell {r},{c} is empty"]
            parts.append(w)
        hay = " ".join(parts)
        rows, cols = {r for r, _ in cells}, {c for _, c in cells}
        kind = ev.get("reading")
        ok = {"row": len(rows) == 1,
              "col": len(cols) == 1,
              "header+row": rows <= {0, max(rows)} and len(rows - {0}) <= 1}.get(kind, False)
        if not ok:
            bad.append(f"cells do not form a '{kind}' reading")
        if cells != sorted(cells, key=lambda x: (x[0], x[1])):
            bad.append("cells not in reading order")
        if len({tuple(c) for c in cells}) != len(cells):
            bad.append("a cell is listed twice")
    else:
        return bad + ["unknown matcher"]
    if hay[s:e] != span:
        bad.append("page text at the recorded offsets is not the span")
    elif not _boundary(hay, s, e):
        bad.append("span does not start/end on a word boundary")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("jsonl")
    ap.add_argument("--pdf-dir", help="Directory of PDFs named <sha256>.pdf; else fetched from R2.")
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "page_evidence_cache"))
    ap.add_argument("--no-unique", action="store_true", help="Skip the exactly-one-page re-check.")
    ap.add_argument("--db", action="store_true", help="Also check provision_text md5/words (read-only).")
    args = ap.parse_args()

    import fitz
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parents[2] / ".env")
    import dcp_page_repair as dpr
    import page_proof_council as ppc
    import rule_page_locator as rpl

    recs = [json.loads(x) for x in Path(args.jsonl).read_text(encoding="utf-8").splitlines() if x.strip()]
    texts = {}
    if args.db:
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
        conn.set_session(readonly=True)
        cur = conn.cursor()
        cur.execute("SELECT id, md5(provision_text), provision_text FROM regulatory_provisions "
                    "WHERE is_current AND id = ANY(%s)", ([r["id"] for r in recs],))
        texts = {i: (m, t) for i, m, t in cur.fetchall()}
        conn.close()
    pdfs, pages_cache, labels_cache, failures = {}, {}, {}, []

    def pdf_for(rec):
        sha = rec["pdf_sha256"]
        if sha not in pdfs:
            if args.pdf_dir and (Path(args.pdf_dir) / f"{sha}.pdf").exists():
                p = Path(args.pdf_dir) / f"{sha}.pdf"
            else:
                p = ppc.local_pdf(rec["pdf_path"], Path(args.cache_dir) / "pdf")
            pdfs[sha] = (p, pe.sha256_file(p))
        return pdfs[sha]

    for rec in recs:
        bad = []
        ev = rec["evidence"]
        try:
            path, got = pdf_for(rec)
            if got != rec["pdf_sha256"]:
                bad.append(f"pdf sha256 {got[:12]} != recorded {rec['pdf_sha256'][:12]}")
            else:
                with fitz.open(str(path)) as doc:
                    pno = ev["page"]
                    if not 1 <= pno <= len(doc):
                        bad.append("page not in pdf")
                    else:
                        bad += check_evidence(ev, doc[pno - 1])
                if not bad and not args.no_unique:
                    if got not in pages_cache:
                        pages_cache[got] = ppc.read_pages(path, got, Path(args.cache_dir))
                    v, ev2, info = pe.prove(ev["span"], pages_cache[got])
                    if v != "proven" or ev2["page"] != ev["page"]:
                        bad.append(f"span now {v} on pages {info.get('pages')}")
            plan, old = rec["plan"], rec["old"]
            if plan["pdf_page"] != ev["page"] or plan["page_check"] != rec["verdict"]:
                bad.append("plan page/verdict disagree with the evidence")
            held = set(old.get("page_range") or []) | {old.get("pdf_page")}
            if (rec["verdict"] == "on_page") != (ev["page"] in held):
                bad.append("verdict does not follow from the old page")
            if plan.get("id") != rec["id"]:
                bad.append("plan id differs from the record id")
            exp_range = (dpr.shift_range(old.get("page_range"), old.get("pdf_page"), ev["page"])
                         if rec["verdict"] == "moved" else old.get("page_range"))
            if list(plan.get("page_range") or []) != list(exp_range or []):
                bad.append("plan page_range is not the old range shifted by the page move")
            if got not in labels_cache:
                labels_cache[got] = rpl.printed_labels(dpr._margins(str(path)))
            if plan.get("printed_page_label") != labels_cache[got].get(ev["page"]):
                bad.append("plan printed_page_label is not the label printed on that page")
            if plan["page_source_path"] != rec["pdf_path"]:
                bad.append("plan page_source_path is not the pinned pdf")
            if args.db:
                m, t = texts.get(rec["id"], (None, None))
                if m != rec["provision_text_md5"]:
                    bad.append("provision_text changed since the proof (md5)")
                elif pe.rule_words(t) != ev["span"]:
                    bad.append("rule words differ from the evidence span")
        except Exception as e:  # noqa: BLE001 -- an unreadable proof is a failed proof
            bad.append(f"error: {type(e).__name__}: {str(e)[:100]}")
        if bad:
            failures.append((rec["id"], bad))
            print(f"FAIL id={rec['id']}: {'; '.join(bad)}")
    n = len(recs)
    print(f"verified {n - len(failures)}/{n} proofs ({len(pdfs)} pinned PDFs)")
    if not n:
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
