#!/usr/bin/env python3
# prior-art-checked: row set = dq_probe_live DQ-145 (council part); write shape and columns =
# dcp_page_repair.plan_row / write (migration 079). No evidence column exists on
# regulatory_provisions, so evidence goes to a committed data/page_evidence_<date>.jsonl.
"""Plan page proofs for served council DCP rows DQ-145 still counts. READ-ONLY, no model calls.

For each unproven served council row (page_check not on_page/moved, citation not proven):
re-read its chapter PDF (the registry's r2_current_path, sha256 pinned) and try
scripts/page_evidence.py. A row is `proven` only when its whole normalised text is one
contiguous span on exactly one page; otherwise it stays unresolved / not_found / too_short.

  python scripts/page_proof_council.py [--council ashfield] [--out data/page_evidence_DATE.jsonl]

Writes the JSONL (one line per PROVEN row: id, provision_text md5, pdf path + sha256, verdict
on_page|moved, old/new page, plan columns, evidence) and prints counts + 5 examples each.
Applying it is scripts/apply_page_evidence.py (never run from here).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import page_evidence as pe  # noqa: E402

ROWS_SQL = """
SELECT rp.id, rp.source_council, rp.source_chapter_key, rp.pdf_page, rp.page_range, rp.provision_text,
       md5(rp.provision_text) AS md5, reg.r2_current_path, reg.r2_public_pdf_url,
       rp.printed_page_label, rp.page_check, rp.page_source_path
FROM regulatory_provisions rp
JOIN dcp_chapter_registry reg
  ON reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key AND reg.is_active
WHERE rp.is_current AND rp.v2_is_actionable AND (rp.v2_provision_type IS NULL OR rp.v2_provision_type <> 'TOC')
  AND rp.source_council IS NOT NULL AND rp.source_council <> 'inner_west_lep'
  AND NOT (COALESCE(rp.citation_status, '') IN ('proven', 'imprecise')
           OR COALESCE(rp.page_check, '') IN ('on_page', 'moved'))
"""


def local_pdf(r2_path: str, cache: Path) -> Path:
    """The chapter PDF from R2, cached by path (a new version is a new path)."""
    dest = cache / (hashlib.sha1(r2_path.encode()).hexdigest()[:16] + ".pdf")
    if not dest.exists():
        import boto3
        s3 = boto3.client(
            "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
        dest.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(os.environ["R2_BUCKET_NAME"], r2_path, str(dest))
    return dest


def read_pages(pdf: Path, sha: str, cache: Path) -> dict:
    """page -> (texts, grids), cached on the PDF's sha256 + the extractor version."""
    import fitz
    pk = cache / f"{sha[:24]}.pages-v2.pkl"
    if pk.exists():
        return pickle.loads(pk.read_bytes())
    out = {}
    with fitz.open(str(pdf)) as doc:
        for pno, page in enumerate(doc, 1):
            out[pno] = (pe.page_texts(page), pe.prepare(pe.page_tables(page)))
    pk.write_bytes(pickle.dumps(out))
    return out


def judge_pdf(args):
    r2_path, rows, cache_dir = args
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parents[2] / ".env")           # the main checkout's, from a worktree
    import dcp_page_repair as dpr
    import rule_page_locator as rpl
    cache = Path(cache_dir)
    try:
        pdf = local_pdf(r2_path, cache / "pdf")
    except Exception as e:  # noqa: BLE001
        return [{"id": r["id"], "verdict": "no_source", "why": str(e)[:100]} for r in rows], None
    sha = pe.sha256_file(pdf)
    pages = read_pages(pdf, sha, cache)
    labels = rpl.printed_labels(dpr._margins(str(pdf)))
    out = []
    for r in rows:
        words = pe.rule_words(r["provision_text"])
        v, ev, info = pe.prove(words, pages)
        res = {"id": r["id"], "words": len(words.split()), "pages": info.get("pages")}
        if v != "proven":
            res["verdict"] = v
            out.append(res)
            continue
        page = ev["page"]
        held = set(r["page_range"] or []) | {r["pdf_page"]}
        verdict = "on_page" if page in held else "moved"
        plan = dpr.plan_row(r, page, verdict, labels)
        res.update(verdict=verdict, plan=plan, evidence=ev)
        out.append(res)
    return out, {"path": r2_path, "sha256": sha, "bytes": pdf.stat().st_size, "pages": len(pages)}


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("--council")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "page_evidence_cache"))
    ap.add_argument("--out", default=str(ROOT / "data" / f"page_evidence_{date.today():%Y-%m-%d}.jsonl"))
    ap.add_argument("--unresolved-out", default=str(Path(tempfile.gettempdir()) / "page_proof_unresolved.json"))
    args = ap.parse_args()

    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parents[2] / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    conn.set_session(readonly=True)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        sql, params = ROWS_SQL, []
        if args.council:
            sql += " AND rp.source_council = %s"
            params.append(args.council)
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()
    by_id = {r["id"]: r for r in rows}
    by_pdf = defaultdict(list)
    for r in rows:
        by_pdf[r["r2_current_path"]].append(r)
    jobs = [(p, rs, args.cache_dir) for p, rs in by_pdf.items() if p]
    Path(args.cache_dir).mkdir(parents=True, exist_ok=True)
    results, pdfs = [], {}
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as ex:
        for (path, _rs, _c), (got, info) in zip(jobs, ex.map(judge_pdf, jobs)):
            results += got
            if info:
                pdfs[path] = info
    proven = [x for x in results if x["verdict"] in ("on_page", "moved")]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for x in sorted(proven, key=lambda x: x["id"]):
            r = by_id[x["id"]]
            f.write(json.dumps({
                "id": x["id"], "council": r["source_council"], "chapter": r["source_chapter_key"],
                "provision_text_md5": r["md5"], "pdf_path": r["r2_current_path"],
                "pdf_sha256": pdfs[r["r2_current_path"]]["sha256"],
                "old": {"pdf_page": r["pdf_page"], "page_range": r["page_range"],
                        "page_check": r["page_check"], "printed_page_label": r["printed_page_label"],
                        "page_source_path": r["page_source_path"]},
                "verdict": x["verdict"], "plan": x["plan"], "evidence": x["evidence"]},
                ensure_ascii=False, sort_keys=True) + "\n")
    json.dump([{"id": x["id"], "council": by_id[x["id"]]["source_council"],
                "verdict": x["verdict"], "pages": x.get("pages"), "words": x.get("words"),
                "text": by_id[x["id"]]["provision_text"][:200]}
               for x in results if x["verdict"] not in ("on_page", "moved")],
              open(args.unresolved_out, "w", encoding="utf-8"), indent=1)

    print(f"rows {len(rows)}  PDFs {len(pdfs)}  proven {len(proven)}  -> {args.out}")
    per = defaultdict(Counter)
    for x in results:
        r = by_id[x["id"]]
        key = x["verdict"] if x["verdict"] not in ("on_page", "moved") else (
            f"{x['verdict']}/{x['evidence']['matcher']}")
        per[r["source_council"]][key] += 1
    keys = sorted({k for c in per.values() for k in c})
    print("per council:", keys)
    for co, c in sorted(per.items()):
        print(f"  {co:22} " + "  ".join(f"{k}={c[k]}" for k in keys if c[k]))
    tot = Counter(k for c in per.values() for k in c.elements())
    print("TOTAL", dict(tot))
    shown = Counter()
    for x in proven:
        m = x["evidence"]["matcher"]
        if shown[m] < 5:
            shown[m] += 1
            r = by_id[x["id"]]
            print(f"\nEXAMPLE {m} id={x['id']} {r['source_council']} {x['verdict']} "
                  f"stored p{r['pdf_page']} -> p{x['plan']['pdf_page']}")
            print("  ", repr(pe.rule_words(r['provision_text'])[:140]))
            ev = x["evidence"]
            print("  ", {k: v for k, v in ev.items() if k not in ("span",)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
