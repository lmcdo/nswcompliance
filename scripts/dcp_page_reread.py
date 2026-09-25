"""Re-read only the pages of a chapter that need it, one page per model call.

WHY THIS EXISTS
---------------
Reading 12 pages per call got rule numbers wrong and skipped pages (DQ-111,
DQ-112). A 5-page trial on 2026-09-25 read ONE page per call with the same
instructions: 45 of 48 citations proved on the council's page (94%), including
Marrickville 3.3 O13 that the 12-page read had filed as "3.2 C14". Re-reading
whole chapters to fix a few pages also cost $37 in a week; this reads only the
pages that need it (~1,745 across the corpus).

WHICH PAGES
-----------
* pages holding a live rule whose citation is not proven (citation_proof), and
* pages left out of the chapter that hold rule words (page_coverage).
A live rule's page is where its WORDS are found, not its stored page_range: the
AI reader stored the first page of its 12-page batch, so page_range is often wrong.

TWO TRAPS, HANDLED
------------------
* Publishing replaces rules by ref_number. A page whose rule shares its number with
  a rule on another page pulls that page in too, so a replacement can never wipe a
  rule that was not re-read.
* A rule running across a page break is cut in two by page-at-a-time reading. When
  page N+1 opens with the same code page N closed on, the two parts are joined.

WHAT IT WRITES
--------------
Nothing by default. With --apply it queues a TARGETED change set (removed rules
from the re-read pages, their replacements added) via the existing
enqueue_review_changes, then grades it with the existing fidelity gate. A chapter
that already has pending rows is skipped: enqueue would clear them.

    python scripts/dcp_page_reread.py --council marrickville --chapter part3-subdivision [--max-pages 20] [--apply]

prior-art-checked: reuse not viable because dcp_extract_changed reads whole
chapters (its --chapter path has no page selection) and dcp_queue_reread only
flags chapters for that whole-chapter read. This reuses their parts: the model
call, prompt, section builder, ref builder, enqueue and fidelity gate.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import citation_proof as cp  # noqa: E402
import page_coverage as pc  # noqa: E402

#: A run of consecutive pages that must be read together (a shared rule number)
#: longer than this is not attempted: it is reported instead.
MAX_CLOSURE_PAGES = 8


def located_pages(ch, text: str) -> set[int]:
    """Pages a rule's words sit on, from the first place they are found. Pure."""
    anchors = cp._anchors(ch, text or "", None)
    if not anchors:
        return set()
    end, start = anchors[0]
    return set(range(ch.lines[start].page, ch.lines[end].page + 1))


def section_in_force(ch, page: int) -> str | None:
    """The last numbered heading printed before `page`, as the section a rule at
    the top of `page` belongs to. Pure. None when no numbered heading precedes it."""
    code = None
    for ln in ch.lines:
        if ln.page >= page:
            break
        if ln.page in ch.toc_pages or not cp._heading_like(ln, ch.page_width):
            continue
        m = cp.CODE_AT_START.match(ln.text)
        if m and "." in m.group(1):
            code = m.group(1)
    return code


def close_over_refs(targets: set[int], rows: list[tuple[str, set[int]]]) -> tuple[set[int], list[str]]:
    """Add every page holding a rule that shares a ref with a rule on a target page.

    `rows` is (ref_number, pages) for each live rule. Returns (pages, refs too spread
    out to close over -- the caller must not touch them). Pure."""
    by_ref: dict[str, set[int]] = defaultdict(set)
    for ref, pages in rows:
        by_ref[ref] |= pages
    pages = set(targets)
    changed = True
    while changed:
        changed = False
        for ref, ps in by_ref.items():
            if ps & pages and not ps <= pages:
                pages |= ps
                changed = True
    spread = [r for r, ps in by_ref.items() if ps & pages and len(ps) > MAX_CLOSURE_PAGES]
    return pages, spread


def join_page_breaks(pages: list[tuple[int, list[dict]]]) -> list[dict]:
    """Join a rule cut by a page break: page N+1's first provision carries the same
    code as page N's last. Each provision keeps the page it started on. Pure."""
    out: list[dict] = []
    prev_page = None
    for page, provs in pages:
        for i, p in enumerate(provs):
            p = {**p, "page": page}
            if (i == 0 and out and prev_page == page - 1
                    and str(out[-1].get("code", "")).strip() == str(p.get("code", "")).strip()):
                out[-1] = {**out[-1], "text": f"{out[-1].get('text', '')} {p.get('text', '')}".strip()}
                continue
            out.append(p)
        prev_page = page
    return out


def unique_codes(provs: list[dict], taken: set[str]) -> list[dict]:
    """A repeated code with different text gets _2, _3 from numbers nobody holds,
    the same rule dcp_extract_changed applies; an exact repeat is dropped. Pure."""
    seen: dict[str, list[str]] = {}
    taken = set(taken)
    out = []
    for p in provs:
        code, text = str(p.get("code", "")).strip(), str(p.get("text", "")).strip()
        if not code or not text:
            continue
        texts = seen.setdefault(code, [])
        if text in texts:
            continue
        texts.append(text)
        if len(texts) > 1 or code in taken:
            n = max(2, len(texts))
            while f"{code}_{n}" in taken:
                n += 1
            code = f"{code}_{n}"
        taken.add(code)
        out.append({**p, "code": code})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--council", required=True)
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--max-pages", type=int, default=20, help="Refuse to read more pages than this.")
    ap.add_argument("--apply", action="store_true", help="Queue the change set. Without it nothing is written.")
    ap.add_argument("--out", help="Write the proposed change set here as JSON.")
    args = ap.parse_args()

    import boto3
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import ai_extractor as ai
    s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    cur.execute("SELECT r2_current_path, content_hash FROM dcp_chapter_registry WHERE council=%s "
                "AND chapter_key=%s AND is_active", (args.council, args.chapter))
    row = cur.fetchone()
    if not row or not row[0] or not row[1]:
        # The commit only takes rows whose hash matches the registry's: a row queued
        # without it could never be committed.
        print("ERROR: no active registry PDF (or no content hash) for this chapter")
        return 2
    r2, content_hash = row
    cur.execute("SELECT count(*) FROM dcp_review_queue WHERE council=%s AND chapter_key=%s AND status='pending'",
                (args.council, args.chapter))
    if cur.fetchone()[0]:
        print("SKIP: this chapter already has pending review rows; queueing would clear them.")
        return 2
    cur.execute("SELECT ref_number, provision_text, document_id FROM regulatory_provisions "
                "WHERE is_current AND source_council=%s AND source_chapter_key=%s",
                (args.council, args.chapter))
    live = cur.fetchall()
    if not live:
        print("ERROR: no live rules for this chapter")
        return 2
    document_id = Counter(d for _r, _t, d in live).most_common(1)[0][0]

    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "src.pdf")
        s3.download_file(os.environ["R2_BUCKET_NAME"], r2, pdf)
        readings = cp.load_readings(pdf)
        ch = readings[1]
        page_lines = pc.pdf_page_lines(pdf)

        # 1. which pages
        placed = [(ref, text, located_pages(ch, text)) for ref, text, _d in live]
        bad = {p for ref, text, ps in placed if ps
               and cp.prove_citation_any(ref, text, readings, None)["status"] == "not_proven"
               for p in ps}
        gaps = {p for p in pc.skipped_pages(page_lines, [t for _r, t, _d in live])
                if pc.holds_rules(page_lines[p])}
        pages, spread = close_over_refs(bad | gaps, [(r, ps) for r, _t, ps in placed if ps])
        print(f"pages: {len(bad)} with unproven citations, {len(gaps)} left out -> "
              f"{len(pages)} after closing over shared numbers")
        if spread:
            print(f"REFUSED: {len(spread)} rule number(s) span more than {MAX_CLOSURE_PAGES} pages: {spread[:5]}")
            return 2
        if len(pages) > args.max_pages:
            print(f"REFUSED: {len(pages)} pages exceeds --max-pages {args.max_pages}")
            return 2
        if not pages:
            print("nothing to re-read")
            return 0

        # 2. read each page alone, with the section in force given by code
        from pypdf import PdfReader
        reader = PdfReader(pdf)
        model = (os.getenv("AI_MODEL") or ai.configured_model() or "").strip().lower()
        print(f"  model: {model}")
        got = []
        for p in sorted(pages):
            prompt = ai._build_prompt(section_in_force(ch, p))
            got.append((p, ai._call_and_parse_with_empty_retry(model, ai._subset_bytes(reader, p - 1, p), prompt)))
            print(f"  read page {p}: {len(got[-1][1])} provisions")

    # 3. the change set
    replaced = [(ref, text) for ref, text, ps in placed if ps and ps <= pages]
    kept_codes = {ref.split("__", 2)[-1] for ref, _t, ps in placed if not (ps and ps <= pages)}
    new = unique_codes(join_page_breaks(got), taken={c for c in kept_codes})
    import dcp_extract_changed as dx
    added, changed, removed = [], [], []
    old_by_ref = dict(replaced)
    for sec in ai.provisions_to_sections(new):
        ref = dx.build_ref_number(document_id, sec["section_number"])
        text = dx.build_provision_text(sec)
        if ref in old_by_ref:
            changed.append({"ref_number": ref, "old_text": old_by_ref.pop(ref), "new_text": text,
                            "new_page": sec["page_start"], "has_numeric_change": True})
        else:
            added.append({"ref_number": ref, "new_text": text, "new_page": sec["page_start"]})
    removed = [{"ref_number": r, "old_text": t} for r, t in old_by_ref.items()]
    proven = Counter(cp.prove_citation_any(x["ref_number"], x["new_text"], readings, x.get("new_page"))["status"]
                     for x in added + changed)
    print(f"change set: {len(removed)} removed, {len(changed)} changed, {len(added)} added; "
          f"new citations {dict(proven)}")
    # No page may end up missing rules that it was not missing before: an old row
    # can carry text from a page that was not re-read (Marrickville part 3 C17 held
    # a Building Code note from another page), and removing it would drop that text.
    gone = {x["ref_number"] for x in removed} | {x["ref_number"] for x in changed}
    after = [t for r, t, _d in live if r not in gone] + [x["new_text"] for x in added + changed]
    newly = sorted({p for p in pc.skipped_pages(page_lines, after) if pc.holds_rules(page_lines[p])}
                   - gaps)
    if newly:
        print(f"REFUSED: the change would leave page(s) {newly} missing rules they hold now.")
        return 2
    if args.out:
        Path(args.out).write_text(json.dumps({"removed": removed, "changed": changed, "added": added},
                                             indent=1, ensure_ascii=False), encoding="utf-8")
    if not args.apply:
        print("DRY RUN -- nothing queued. Re-run with --apply.")
        return 0

    diff = {"status": "amendment", "total_old": len(live), "changed": changed,
            "added": added, "removed": removed}
    n = dx.enqueue_review_changes(conn, [{"council": args.council, "chapter_key": args.chapter,
                                          "document_id": document_id, "diff": diff,
                                          "content_hash": content_hash}])
    conn.commit()
    import dcp_fidelity_gate as gate
    g, f, s = gate.gate_chapter(cur, s3, args.council, args.chapter, r2)
    conn.commit()
    print(f"QUEUED {n} rows (targeted); fidelity gate: {g} grounded, {f} flagged, {s} not actionable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
