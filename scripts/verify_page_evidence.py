#!/usr/bin/env python3
# prior-art-checked: no existing verifier of page evidence; counterpart of page_proof_council.py.
"""Re-derive every page proof in a data/page_evidence_<date>.jsonl from the PDF alone.

For each line: (1) the PDF is the pinned one -- its sha256 equals the recorded one; (2) the
evidence's own location (page, order or table + cells, char offsets) holds EXACTLY the recorded
span; (3) the span's sha256 matches; (4) the span is on no other page of the PDF (unless
--no-unique) -- or, when evidence.all_pages is present, all_pages is re-derived from the PDF and
must be identical and the row's stored page must be one of them; (5) the plan's page is the evidence's page and its verdict follows from the old
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
    combo = {None: ("text-run", "table-cells"), "full_text": ("text-run", "table-cells"),
             "all_words_label": ("all-words+label",)}
    if ev.get("fallback") not in combo or ev.get("matcher") not in combo[ev.get("fallback")]             or (ev.get("matcher") == "all-words+label" and ev.get("fallback") != "all_words_label"):
        return bad + [f"matcher {ev.get('matcher')!r} does not go with fallback {ev.get('fallback')!r}"]
    if ev.get("matcher") == "all-words+label":   # fallback (user 2026-10-18): every word + the rule's own label
        texts = pe.page_texts(page)
        if len(span.split()) < pe.MIN_WORDS_BAG:
            bad.append("span shorter than MIN_WORDS_BAG")
        if not pe.bag_ok(span, texts, pe.prepare(pe.page_tables(page)), ev.get("row_labels") or ()):
            bad.append("a word or whole number of the span is not printed on the page")
        if not ev.get("labels") or not all(pe.has_label(lb, texts) for lb in ev["labels"])                 or not set(ev["labels"]) <= set(ev.get("row_labels") or ()):
            bad.append("the rule's own label is not printed on the page")
        if not pe.table_or_figure(span, ev.get("row_labels") or [], pe.prepare(pe.page_tables(page))):
            bad.append("every-word proof used for prose: only tables and figures may use it")
        return bad
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


def check_uniqueness(ev: dict, old: dict, verdict: str, pages: dict) -> list:
    """Problems with the 'where else is the span printed' half of a proof. Pure over `pages`
    (page -> (texts, prepared tables)). Evidence with all_pages: the list must be re-derived
    exactly from the PDF and the row's stored page must be one of them. Older evidence (no
    all_pages): the span must be on exactly the one recorded page."""
    if "all_pages" not in ev:
        v, ev2, info = pe.prove(ev["span"], pages)
        if v != "proven" or ev2["page"] != ev["page"]:
            return [f"span now {v} on pages {info.get('pages')}"]
        return []
    held = set(old.get("page_range") or []) | {old.get("pdf_page")}
    if ev.get("matcher") == "all-words+label":   # re-derive the candidate pages from the PDF with the row's labels
        hits = pe.bag_pages(ev["span"], ev.get("row_labels") or [], pages)
        if hits != ev["all_pages"]:
            return [f"every-word+label pages now {hits}, recorded {ev['all_pages']}"]
        pick = pe.pick_page(hits, held, old.get("pdf_page"))   # the planner's own choice, re-made (cross-review)
        if pick != ev["page"]:
            return [f"every-word+label picks page {pick}, recorded {ev['page']}"]
        return []
    v, ev2, info = pe.prove(ev["span"], pages, held, old.get("pdf_page"), ev.get("by_heading"))
    if v != "proven" or ev2["page"] != ev["page"] or info["pages"] != ev["all_pages"]             or ev2.get("by_heading") != ev.get("by_heading"):
        return [f"span now {v} on pages {info.get('pages')}, recorded all_pages {ev['all_pages']}"]
    # prove() only picks a page of an ambiguous span from `held`, and the page it picked must be
    # the evidence's, so a pass above already means the stored page is among all_pages; a
    # single-page span may legitimately be 'moved'.
    if len(ev["all_pages"]) > 1 and verdict != "on_page" and not ev.get("by_heading"):
        return ["span on several pages but verdict is not on_page"]
    return []


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
        # prior-art-checked: widens this file's own existing read-only SELECT by two columns; no new source
        cur.execute("SELECT id, md5(provision_text), provision_text, pdf_page, page_range "
                    "FROM regulatory_provisions WHERE is_current AND id = ANY(%s)",
                    ([r["id"] for r in recs],))
        rows_db = cur.fetchall()
        texts = {i: (m, t) for i, m, t, _p, _r in rows_db}
        pages_db = {i: (p, list(r or [])) for i, _m, _t, p, r in rows_db}
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
                    bad += check_uniqueness(ev, rec["old"], rec["verdict"], pages_cache[got])
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
                elif ev.get("fallback") == "full_text":
                    full, body = pe.full_text_words(t).split(), pe.rule_words(t).split()
                    k = ev.get("dropped_head_words")
                    if (not isinstance(k, int) or k < 0 or k > len(full) - len(body)
                            or " ".join(full[k:]) != ev["span"] or pe.OPERATIVE_WORDS & set(full[:k])):
                        bad.append("full-text span is not the row's text minus leading heading words")
                elif pe.rule_words(t) != ev["span"]:
                    bad.append("rule words differ from the evidence span")
                if ev.get("matcher") == "all-words+label" and pe.row_labels(t) != ev.get("row_labels"):
                    bad.append("row_labels are not the row's own labels")
                elif ev.get("by_heading") and pe.row_heading(t) != ev["by_heading"]:
                    bad.append("by_heading is not the row's own section number")
                if len(ev.get("all_pages") or ()) > 1:
                    # an ambiguous span is anchored ONLY by the row's own stored page, so the
                    # file's claim of what that page is must equal the live row (on_page leaves it)
                    live = pages_db.get(rec["id"])
                    if live != (rec["old"].get("pdf_page"), list(rec["old"].get("page_range") or [])):
                        bad.append("stored pdf_page/page_range in the file differ from the live row")
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
