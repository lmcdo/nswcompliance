#!/usr/bin/env python3
# prior-art-checked: PLAN docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md §5.3 Tier 1 (golden-PDF
# regression corpus, never built: tests/ held 0 council PDFs on 2026-11-04). Reuses the
# hand-made answer key of 2026-10-14 (~/.claude/plans/ce-council-words-probes/answer_key/,
# 100 pages, 977 labelled rules) and the extractor's own page reader (dx._extract_page_text +
# _clean_page_text) -- no new labelling of those pages, no new PDF reader. Pattern follows capture_brief_golden_fixtures.py.
"""Build tests/fixtures/rule_answer_set.json -- real council text with a known answer.

Two parts, both read-only against the database and R2:

  key    Every rule in the 2026-10-14 answer key, its full text cut from the LIVE R2 PDF
         between the key's first_words and last_words. A rule whose words are no longer on
         that page (the council replaced the PDF) is left out and counted, never guessed.
  queue  Waiting review rows in the exact shape the pipeline gives the sorting step
         ("# heading" then "cell | value"), labelled by reading them in the main session on
         2026-11-04 (labels in QUEUE_LABELS below). Their text is fetched by id.

Usage:
    python scripts/build_rule_answer_set.py --key-dir ~/.claude/plans/ce-council-words-probes/answer_key
"""

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pdfplumber
import psycopg2

import dcp_extract_changed as dx

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "rule_answer_set.json"

# Labelled 2026-11-04 from the rows' own text (setbacks, parking and bicycle rates, shade
# cover, overhang widths, flood-level controls). Left out as unsure: 406514-406521 (City of
# Sydney month/time table, purpose not stated in the row), 419380 (Hornsby guidance
# "should be guided by"), 423952 (garbled diagram text).
QUEUE_RULE_IDS = [
    423106, 423107, 423109, 423438, 423441, 423477, 423478, 423479, 423480, 423481, 423482,
    423483, 423484, 423485, 423509, 423510, 423556, 423557, 423558, 423559,
    427228, 427229, 427230, 427231, 427234, 427235, 427236, 427237, 427240, 427242, 427243,
    427244, 427248, 427249, 427250, 427251, 427254, 427257, 427258, 427259, 427261, 427267,
    427271, 427272, 427277, 427278, 427280, 427281, 427282, 427283, 427285, 427286, 427287,
    428468, 428469, 428470, 428471, 428589, 428669, 428670, 428671, 428672, 428722, 428723,
    428724, 428725, 428726, 428727, 428728, 428771, 428772, 428773, 428774, 428775, 428776,
    428777, 428927, 428928, 428929, 428930, 429048, 429104, 429105, 429106, 429107, 429171,
    429172, 429174, 429175, 429176, 429177, 429178,
]
# The answer key's labels: a control or an objective is a rule a user is shown; a note or a
# definition is not.
IS_RULE = {"control": True, "objective": True, "note": False, "definition": False}


def _span(page_text: str, first: str, last: str) -> str | None:
    """The page text from first_words to last_words, matched ignoring spacing and case."""
    def pat(words: str) -> str:
        return r"\s*".join(re.escape(ch) for ch in re.sub(r"\s+", "", words))
    if not first or not last:
        return None
    m1 = re.search(pat(first), page_text, re.I)
    if not m1:
        return None
    m2 = re.search(pat(last), page_text[m1.start():], re.I)
    if not m2:
        return None
    return re.sub(r"\s+", " ", page_text[m1.start():m1.start() + m2.end()]).strip()


def _raw_pages(s3, r2_path: str, council: str, wanted: set[int]) -> dict[int, str]:
    """{page -> text} for the wanted pages only, as the pipeline reads them, NOT normalised:
    the sorting step sees case. Reading only the keyed pages keeps a 360 MB corpus quick."""
    pages: dict[int, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "chapter.pdf"
        s3.download_file(dx.R2_BUCKET_NAME, r2_path, str(local))
        with pdfplumber.open(str(local)) as pdf:
            for i in sorted(wanted):
                if 1 <= i <= len(pdf.pages):
                    pages[i] = dx._clean_page_text(dx._extract_page_text(pdf.pages[i - 1], council), council)
    return pages


def key_part(key_dir: Path, s3, cur) -> tuple[list[dict], Counter]:
    manifest = json.loads((key_dir / "manifest.json").read_text(encoding="utf-8"))
    key = json.loads((key_dir / "key.json").read_text(encoding="utf-8"))
    out, missed, pages_cache = [], Counter(), {}
    wanted: dict[str, set[int]] = {}
    for item in manifest:
        wanted.setdefault(item["r2"], set()).add(item["pdf_page"])
    for i, item in enumerate(manifest, 1):
        if item["r2"] not in pages_cache:
            pages_cache[item["r2"]] = _raw_pages(s3, item["r2"], item["council"], wanted[item["r2"]])
        page = pages_cache[item["r2"]].get(item["pdf_page"], "")
        # The document id the pipeline passes for this chapter's rules (most common one).
        cur.execute("SELECT document_id FROM regulatory_provisions WHERE source_council = %s "
                    "AND source_chapter_key = %s AND document_id IS NOT NULL "
                    "GROUP BY 1 ORDER BY count(*) DESC LIMIT 1", (item["council"], item["chapter"]))
        hit = cur.fetchone()
        if hit is None:
            missed["no_document_id"] += len(key[f"{item['n']:03d}"]["rules"])
            continue
        for rule in key[f"{item['n']:03d}"]["rules"]:
            if rule["label"] not in IS_RULE:
                missed["unknown_label"] += 1
                continue
            text = _span(page, rule["first_words"], rule["last_words"])
            if text is None:
                missed["words_not_on_live_page"] += 1
                continue
            out.append({"source": "key", "council": item["council"], "r2": item["r2"],
                        "document_id": hit[0],
                        "page": item["pdf_page"], "label": rule["label"], "where": rule["where"],
                        "is_rule": IS_RULE[rule["label"]], "text": text})
        print(f"DONE key page {i}/{len(manifest)}", flush=True)
    return out, missed


def queue_part(cur) -> list[dict]:
    cur.execute("SELECT id, council, chapter_key, document_id, new_text FROM dcp_review_queue "
                "WHERE id = ANY(%s)",
                (QUEUE_RULE_IDS,))
    rows = cur.fetchall()
    if len(rows) != len(QUEUE_RULE_IDS):
        sys.exit(f"queue part: {len(rows)} of {len(QUEUE_RULE_IDS)} labelled rows found -- refusing "
                 f"a partial fixture.")
    return [{"source": "queue", "id": rid, "council": co, "chapter": ck, "document_id": doc,
             "where": "table", "label": "control", "is_rule": True, "text": tx}
            for rid, co, ck, doc, tx in rows]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--key-dir", required=True, type=Path)
    args = ap.parse_args()
    s3 = dx.boto3.client("s3", endpoint_url=dx.R2_ENDPOINT, aws_access_key_id=dx.R2_ACCESS_KEY_ID,
                         aws_secret_access_key=dx.R2_SECRET_ACCESS_KEY, region_name="auto")
    conn = psycopg2.connect(dx.DATABASE_URL)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30s'")
    rows, missed = key_part(args.key_dir.expanduser(), s3, cur)
    rows += queue_part(cur)
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    c = Counter((r["source"], r["is_rule"]) for r in rows)
    print(f"wrote {len(rows)} rows to {OUT}: {dict(c)}; left out: {dict(missed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
