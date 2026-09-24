#!/usr/bin/env python3
"""DQ-111: a served provision's clause number is not proven where the council printed it.

prior-art-checked: the proof itself is `scripts/citation_proof.py`, shared with
the fidelity gate so the ledger and the gate cannot disagree about what a
proven citation is. This file only runs it over what is SERVED and counts.

HISTORY OF THE BAR
------------------
The first version (9a913992) asked whether a cited code appeared ANYWHERE in
its source PDF and read 1,302 of 14,083 (9.25%). That bar was too low: a code
printed elsewhere in the document passed, so Leichhardt rows citing G10.5.2
under a printed G6.12 were counted as fine, and City of Sydney's page number
"6.2-20" served as a clause. It also produced false positives -- Warringah's
"G6.8 R3" is Part G6 > "8. Traffic generation" > R3, all printed.

The bar now is the gate's: printed at the start of a line, the nearest heading
of its family above the rule, parents printed, item label printed between.

Rows whose ref carries no discriminating code, and rows whose wording cannot
be found in their own source, are counted under their own names -- never
dropped, never folded into the headline.

Contract as `dq_probe_live.py`: exit 0 when nothing is unproven, 1 when
something is, 2 when a source cannot be reached. Read-only.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import citation_proof as cp  # noqa: E402

SERVED_SQL = """
SELECT rp.id, rp.source_council, rp.source_chapter_key, rp.ref_number,
       reg.r2_current_path, rp.provision_text, rp.page_range
FROM regulatory_provisions rp
JOIN dcp_chapter_registry reg
  ON reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key
 AND reg.is_active
WHERE rp.is_current AND rp.v2_is_actionable AND rp.source_council IS NOT NULL
"""
SERVED_COUNT_SQL = ("SELECT count(*) FROM regulatory_provisions WHERE is_current "
                    "AND v2_is_actionable AND source_council IS NOT NULL")


def _cache_file(cache_dir: Path, r2_path: str) -> Path:
    return cache_dir / f"{hashlib.sha1(r2_path.encode()).hexdigest()[:16]}.lines.json"


def chapter_lines(s3, bucket, r2_path: str, cache_dir: Path):
    """The PDF's lines, cached per R2 path. A new version is a new path, so the
    cache cannot go stale; a cold run downloads everything."""
    cf = _cache_file(cache_dir, r2_path)
    if not cf.exists():
        import fitz
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "src.pdf"
            s3.download_file(bucket, r2_path, str(local))
            raw, width = [], None
            with fitz.open(str(local)) as doc:
                for pno, page in enumerate(doc, 1):
                    width = width or page.rect.width
                    for block in page.get_text("dict")["blocks"]:
                        for ln in block.get("lines", []):
                            t = " ".join(s["text"] for s in ln["spans"]).strip().lower()
                            if t:
                                raw.append([pno, ln["bbox"][1], ln["bbox"][0], t])
        cf.write_text(json.dumps({"width": width, "lines": raw}), encoding="utf-8")
    data = json.loads(cf.read_text(encoding="utf-8"))
    return cp.both_orders([cp.Line(*x) for x in data["lines"]], data["width"])


def kind_of(verdict: dict) -> str:
    """The first failing reason, without its evidence: not_nearest, item_format..."""
    if verdict["status"] != "not_proven":
        return verdict["status"]
    return (verdict["detail"] or "").split(": ", 1)[-1].split(":")[0].split(";")[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "dq111_lines"))
    ap.add_argument("--council", help="Limit to one council.")
    ap.add_argument("--csv", help="Write every row that is not proven here.")
    ap.add_argument("--examples", type=int, default=3)
    args = ap.parse_args()

    try:
        import boto3
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
        s3 = boto3.client(
            "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
        bucket = os.environ["R2_BUCKET_NAME"]
    except Exception as exc:  # noqa: BLE001
        print(f"UNREACHABLE: {exc}")
        return 2
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cur = conn.cursor()
    cur.execute(SERVED_COUNT_SQL)
    served_total = cur.fetchone()[0]
    sql, params = SERVED_SQL, []
    if args.council:
        sql += " AND rp.source_council = %s"
        params.append(args.council)
    cur.execute(sql, params)
    rows = cur.fetchall()
    print(f"served council rows: {served_total}  ({SERVED_COUNT_SQL})")
    print(f"rows joined to an active registry PDF: {len(rows)}")

    by_pdf = collections.defaultdict(list)
    for r in rows:
        by_pdf[r[4]].append(r)

    # Downloads are the cost (the 139 MB PDF takes ~40s); warm 8 at a time.
    def _warm(path):
        try:
            _cache_file(cache_dir, path).exists() or chapter_lines(s3, bucket, path, cache_dir)
        except Exception:  # noqa: BLE001 -- reported by the main loop
            pass

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_warm, by_pdf))

    status = collections.Counter()
    kinds = collections.Counter()
    coarse = collections.Counter()
    unjudged = collections.Counter()
    per_council = collections.defaultdict(collections.Counter)
    per_chapter = collections.Counter()
    examples = collections.defaultdict(list)
    failing, unreadable = [], []
    for n, (r2_path, prow) in enumerate(sorted(by_pdf.items(), key=lambda kv: len(kv[1])), 1):
        try:
            ch = chapter_lines(s3, bucket, r2_path, cache_dir)
        except Exception as exc:  # noqa: BLE001
            unreadable.append((r2_path, str(exc)[:120]))
            continue
        for rid, council, chapter, ref, _, text, pages in prow:
            v = cp.prove_citation_any(ref, text, ch, (pages or [None])[0])
            status[v["status"]] += 1
            per_council[council][v["status"]] += 1
            if v["status"] == "unjudged":
                unjudged[v["detail"]] += 1
            elif v["status"] == "imprecise":
                coarse["names only the chapter" if "names only the chapter" in (v["detail"] or "")
                       else "a finer heading is printed above the rule"] += 1
            elif v["status"] != "proven":
                k = kind_of(v)
                kinds[k] += 1
                per_chapter[f"{council}/{chapter}"] += 1
                failing.append((rid, council, chapter, ref, v["status"], k, v["detail"]))
                if len(examples[council]) < args.examples:
                    examples[council].append(f"{chapter}: {ref.split('__')[-1]!r} -> {v['detail']}")
        print(f"  [{n}/{len(by_pdf)}] {len(prow):5} rows  {r2_path}", file=sys.stderr)

    judged = status["proven"] + status["imprecise"] + status["not_proven"] + status["text_not_found"]
    bad = status["not_proven"] + status["text_not_found"]
    print()
    print(f"CITATION NOT PROVEN ON ITS SOURCE PAGE: {bad} of {judged} judged rows "
          f"({100 * bad / judged if judged else 0:.2f}%)")
    print(f"    {status['not_proven']:6}  printed wrongly or not at all (by first reason below)")
    for k, c in kinds.most_common():
        if k != "text_not_found":
            print(f"             {c:6}  {k}")
    print(f"    {status['text_not_found']:6}  the rule's wording is not in its own source "
          f"(a text defect; the citation cannot be proven without it)")
    print(f"proven: {status['proven']}")
    print(f"imprecise (true, but a more specific printed heading exists -- the collapsed-parent "
          f"class, counted apart): {status['imprecise']}")
    for k, c in coarse.most_common():
        print(f"    {c:6}  {k}")
    print(f"not judged: {status['unjudged']}")
    for reason, c in unjudged.most_common():
        print(f"    {c:6}  {reason}")
    if unreadable:
        print(f"UNREADABLE PDFs: {len(unreadable)}")
        for p, e in unreadable:
            print(f"    {p}: {e}")
    print("\nper council: judged / not proven / %")
    for council, c in sorted(per_council.items(),
                             key=lambda kv: -(kv[1]["not_proven"] + kv[1]["text_not_found"])):
        j = c["proven"] + c["imprecise"] + c["not_proven"] + c["text_not_found"]
        b = c["not_proven"] + c["text_not_found"]
        print(f"  {council:22} {j:6} {b:6} ({100 * b / j if j else 0:5.1f}%)")
    print("\nchapters with unproven citations:")
    for chp, c in per_chapter.most_common(40):
        print(f"  {c:5}  {chp}")
    print("\nexamples:")
    for council, ex in examples.items():
        for e in ex:
            print(f"  {council}: {e}")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "council", "chapter", "ref_number", "status", "kind", "detail"])
            w.writerows(failing)
    if unreadable:
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
