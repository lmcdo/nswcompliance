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
import re
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
    """Every page a rule's words run over, from the first place they are found. Pure.

    The whole span, not the page of its first words: an old rule can be a block
    running across many pages (Campbelltown part 4, pages 12-26), and placing it
    on its first page let a one-page re-read replace -- and so drop -- the whole
    block. The chapter guard caught all 36 such cases on 2026-09-25."""
    anchors = cp._anchors(ch, text or "", None)
    if not anchors:
        return set()
    start = anchors[0][1]
    end = max(e for e, s in anchors if s == start)
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
                    and str(out[-1].get("code") or "").strip() == str(p.get("code") or "").strip()):
                out[-1] = {**out[-1], "text": f"{out[-1].get('text', '')} {p.get('text', '')}".strip()}
                continue
            out.append(p)
        prev_page = page
    return out


def _norm(code: str) -> str:
    """A code as it appears in a stored ref: dots become underscores."""
    return code.replace(".", "_")


def unique_codes(provs: list[dict], taken: set[str]) -> list[dict]:
    """A repeated code with different text gets _2, _3 from numbers nobody holds,
    the same rule dcp_extract_changed applies; an exact repeat is dropped. Pure.

    `taken` holds the ref tails of rules NOT being re-read, in stored form
    ("4_1 C2"). New codes come from the model with dots ("4.1 C2"), so both are
    compared normalised -- compared raw, a clash was never seen, two rules got one
    ref, and the targeted publish would have wiped the one that was not re-read."""
    seen: dict[str, list[str]] = {}
    taken = {_norm(t) for t in taken}
    out = []
    for p in provs:
        code, text = str(p.get("code") or "").strip(), str(p.get("text") or "").strip()
        if not code or not text:
            continue
        texts = seen.setdefault(code, [])
        if text in texts:
            continue
        texts.append(text)
        if len(texts) > 1 or _norm(code) in taken:
            n = max(2, len(texts))
            while _norm(f"{code}_{n}") in taken:
                n += 1
            code = f"{code}_{n}"
        taken.add(_norm(code))
        out.append({**p, "code": code})
    return out


#: A page whose citations prove below this share is read again with the fallback
#: model. gpt-5.4-mini proved 131 of 298 on Ashfield F where gpt-5.6-sol had
#: proved 442 of 495 (2026-09-25): cheap is only good enough where it proves.
MIN_PROVEN_SHARE = 0.8


def proven_share(provs: list[dict], readings, document_id: str, page: int) -> float:
    """Share of a page's returned citations proven on the council's page. 1.0 when
    nothing was judged (nothing to hold against the read)."""
    judged = proven = 0
    for p in provs:
        code = str(p.get("code") or "").strip()
        if not code:
            continue
        ref = f"{document_id}__{_norm(code)}"
        st = cp.prove_citation_any(ref, f"# {code} {p.get('title', '')}" + chr(10) * 2 + str(p.get('text', '')),
                                   readings, page)["status"]
        if st in ("proven", "not_proven", "imprecise"):
            judged += 1
            proven += st == "proven"
    return proven / judged if judged else 1.0


def page_missing(lines: list[str], provs: list[dict]) -> bool:
    """Does what the model returned leave out this page's rules? Pure."""
    texts = [f"{p.get('code', '')} {p.get('title', '')} {p.get('text', '')}" for p in provs]
    return bool(pc.skipped_pages({1: lines}, texts)) and pc.holds_rules(lines)


def _read(ai, model: str, model_id: str | None, pdf_bytes: bytes, prompt: str) -> list[dict]:
    """One page through the extractor's own call, with the model id chosen per call."""
    old = os.environ.get("AI_MODEL_ID")
    try:
        if model_id:
            os.environ["AI_MODEL_ID"] = model_id
        return ai._call_and_parse_with_empty_retry(model, pdf_bytes, prompt)
    finally:
        if old is None:
            os.environ.pop("AI_MODEL_ID", None)
        else:
            os.environ["AI_MODEL_ID"] = old


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--council", required=True)
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--max-pages", type=int, default=20, help="Refuse to read more pages than this.")
    ap.add_argument("--apply", action="store_true", help="Queue the change set. Without it nothing is written.")
    ap.add_argument("--out", help="Write the proposed change set here as JSON.")
    ap.add_argument("--model-id", help="Model id for the first read (e.g. a cheaper one).")
    ap.add_argument("--fallback-model-id", default="gpt-5.6-sol",
                    help="Model id for a page whose rules the first read left out.")
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
    try:
        return _run(args, conn, s3, ai)
    finally:
        conn.close()


LABEL_PROMPT = (
    "This is one page of a NSW council Development Control Plan, and a numbered list of "
    "provisions whose words are printed on it. For each, give its citation as the page prints "
    "it: the section number printed in the nearest numbered heading above it, a space, then "
    "the provision's own label exactly as printed beside it. Copy every character -- never add "
    "a letter or number the page does not show, never renumber, never convert a label into a "
    "different style. If the page prints no label for it, give the section number alone. Also "
    "give the words of that heading. Return ONLY a JSON object "
    '{"labels": [{"i", "code", "title"}]} with one entry per numbered provision.')

NL = chr(10)


def label_prompt(section: str | None, texts: list[str]) -> str:
    """The small question: which printed number labels each of these wordings. Pure."""
    head = (f" These pages may continue section {section} from earlier pages." if section else "")
    items = NL.join(f"{i + 1}. {t[:300]}" for i, t in enumerate(texts))
    return LABEL_PROMPT + head + NL + NL + "Provisions:" + NL + items


def parse_labels(raw: str) -> dict[int, dict]:
    """{item number: {"code", "title"}} from the model's JSON; bad input gives {}. Pure."""
    try:
        d = json.loads(re.sub(r"^```(json)?|```$", "", (raw or "").strip(), flags=re.M).strip())
    except ValueError:
        return {}
    out = {}
    for e in (d.get("labels") if isinstance(d, dict) else None) or []:
        try:
            out[int(e.get("i"))] = {"code": str(e.get("code") or "").strip(),
                                    "title": str(e.get("title") or "").strip()}
        except (TypeError, ValueError, AttributeError):
            continue
    return out


def body_of(text: str) -> str:
    """A stored provision's words without its '# code title' first line. Pure."""
    first, _, rest = (text or "").partition(NL)
    return rest.lstrip(NL) if first.startswith("#") and rest.strip() else (text or "")


def load_chapter(cur, s3, council: str, chapter: str, tmp: str):
    """Everything a re-read needs about one chapter, or an error string."""
    cur.execute("SELECT r2_current_path, content_hash FROM dcp_chapter_registry WHERE council=%s "
                "AND chapter_key=%s AND is_active", (council, chapter))
    row = cur.fetchone()
    if not row or not row[0] or not row[1]:
        # The commit only takes rows whose hash matches the registry's.
        return "ERROR: no active registry PDF (or no content hash) for this chapter"
    cur.execute("SELECT count(*) FROM dcp_review_queue WHERE council=%s AND chapter_key=%s "
                "AND status='pending'", (council, chapter))
    if cur.fetchone()[0]:
        return "SKIP: this chapter already has pending review rows; queueing would clear them."
    cur.execute("SELECT ref_number, provision_text, document_id FROM regulatory_provisions "
                "WHERE is_current AND source_council=%s AND source_chapter_key=%s", (council, chapter))
    live = cur.fetchall()
    if not live:
        return "ERROR: no live rules for this chapter"
    pdf = os.path.join(tmp, "src.pdf")
    s3.download_file(os.environ["R2_BUCKET_NAME"], row[0], pdf)
    readings = cp.load_readings(pdf)
    return {"council": council, "chapter": chapter, "r2": row[0], "content_hash": row[1],
            "live": live, "document_id": Counter(d for _r, _t, d in live).most_common(1)[0][0],
            "pdf": pdf, "readings": readings, "page_lines": pc.pdf_page_lines(pdf),
            "placed": [(r, t, located_pages(readings[1], t)) for r, t, _d in live]}


def plan_pages(ctx: dict, max_pages: int):
    """Which pages need a full read and which only the small label question, or an
    error string. A page gets the label question only when every rule on it sits on
    that page alone, its words are found, and the page is not missing rules."""
    rd, placed = ctx["readings"], ctx["placed"]
    unproven = {r for r, t, ps in placed if ps
                and cp.prove_citation_any(r, t, rd, None)["status"] == "not_proven"}
    bad = {p for r, _t, ps in placed if r in unproven for p in ps}
    gaps = {p for p in pc.skipped_pages(ctx["page_lines"], [t for _r, t, _d in ctx["live"]])
            if pc.holds_rules(ctx["page_lines"][p])}
    pages, spread = close_over_refs(bad | gaps, [(r, ps) for r, _t, ps in placed if ps])
    if spread:
        return f"REFUSED: {len(spread)} rule number(s) span more than {MAX_CLOSURE_PAGES} pages: {spread[:5]}"
    if len(pages) > max_pages:
        return f"REFUSED: {len(pages)} pages exceeds --max-pages {max_pages}"
    on = defaultdict(list)
    for r, t, ps in placed:
        for p in ps:
            on[p].append((r, t, ps))
    label, read = {}, set()
    for p in sorted(pages):
        if p not in gaps and on[p] and all(ps == {p} for _r, _t, ps in on[p]):
            rows = [(r, t) for r, t, _ps in on[p] if r in unproven]
            if rows:
                label[p] = rows
        else:
            read.add(p)
    return {"pages": pages, "gaps": gaps, "read": read, "label": label}


def build_change(ctx: dict, plan: dict, got: list, labels: dict):
    """The targeted change set, or an error string. `got` is [(page, provisions)] for
    fully read pages; `labels` is {ref: {"code","title"}} for label-question rows."""
    import ai_extractor as ai
    import dcp_extract_changed as dx
    read = plan["read"]
    placed, live, doc = ctx["placed"], ctx["live"], ctx["document_id"]
    replaced = [(r, t) for r, t, ps in placed if ps and ps <= read]
    kept = {r.rpartition("__")[2] for r, _t, ps in placed if not (ps and ps <= read)}
    new = unique_codes(join_page_breaks(got), taken=kept)
    added, changed = [], []
    old_by_ref = dict(replaced)
    for sec in ai.provisions_to_sections(new):
        ref = dx.build_ref_number(doc, sec["section_number"])
        text = dx.build_provision_text(sec)
        if ref in old_by_ref:
            changed.append({"ref_number": ref, "old_text": old_by_ref.pop(ref), "new_text": text,
                            "new_page": sec["page_start"], "has_numeric_change": True})
        else:
            added.append({"ref_number": ref, "new_text": text, "new_page": sec["page_start"]})
    removed = [{"ref_number": r, "old_text": t} for r, t in old_by_ref.items()]
    # The small question: same words, corrected number -- used only when the new
    # number proves on the page and clashes with no other rule.
    taken = ({_norm(r.rpartition("__")[2]) for r, _t, _p in placed}
             | {_norm(x["ref_number"].rpartition("__")[2]) for x in added})
    text_of = {r: t for r, t, _d in live}
    page_of = {r: min(ps) for r, _t, ps in placed if ps}
    for ref, lab in labels.items():
        code = lab.get("code", "")
        if not code or ref not in text_of:
            continue
        new_ref = dx.build_ref_number(doc, code)
        if new_ref == ref or _norm(code) in taken:
            continue
        new_text = f"# {code} {lab.get('title', '')}".rstrip() + NL + NL + body_of(text_of[ref])
        if cp.prove_citation_any(new_ref, new_text, ctx["readings"], page_of.get(ref))["status"] != "proven":
            continue
        taken.add(_norm(code))
        removed.append({"ref_number": ref, "old_text": text_of[ref]})
        added.append({"ref_number": new_ref, "new_text": new_text, "new_page": page_of.get(ref)})
    gone = {x["ref_number"] for x in removed} | {x["ref_number"] for x in changed}
    after = [t for r, t, _d in live if r not in gone] + [x["new_text"] for x in added + changed]
    newly = sorted({p for p in pc.skipped_pages(ctx["page_lines"], after)
                    if pc.holds_rules(ctx["page_lines"][p])} - plan["gaps"])
    if newly:
        return f"REFUSED: the change would leave page(s) {newly} missing rules they hold now."
    return {"removed": removed, "changed": changed, "added": added}


def queue_change(conn, s3, ctx: dict, change: dict) -> str:
    """Queue a targeted change set and grade it with the fidelity gate."""
    import dcp_extract_changed as dx
    import dcp_fidelity_gate as gate
    diff = {"status": "amendment", "total_old": len(ctx["live"]), **change}
    n = dx.enqueue_review_changes(conn, [{"council": ctx["council"], "chapter_key": ctx["chapter"],
                                          "document_id": ctx["document_id"], "diff": diff,
                                          "content_hash": ctx["content_hash"]}])
    conn.commit()
    cur = conn.cursor()
    g, f, s = gate.gate_chapter(cur, s3, ctx["council"], ctx["chapter"], ctx["r2"])
    conn.commit()
    return f"QUEUED {n} rows (targeted); fidelity gate: {g} grounded, {f} flagged, {s} not actionable"


def _ask(model: str, model_id: str | None, pdf_bytes: bytes, prompt: str) -> str:
    """One raw model call through the extractor's provider, model id chosen per call."""
    import ai_extractor as ai
    old = os.environ.get("AI_MODEL_ID")
    try:
        if model_id:
            os.environ["AI_MODEL_ID"] = model_id
        return ai._call_with_retry(model, pdf_bytes, prompt)
    finally:
        if old is None:
            os.environ.pop("AI_MODEL_ID", None)
        else:
            os.environ["AI_MODEL_ID"] = old


def _run(args, conn, s3, ai) -> int:
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = load_chapter(cur, s3, args.council, args.chapter, tmp)
        if isinstance(ctx, str):
            print(ctx)
            return 2
        plan = plan_pages(ctx, args.max_pages)
        if isinstance(plan, str):
            print(plan)
            return 2
        print(f"pages: {len(plan['pages'])} ({len(plan['read'])} full read, {len(plan['label'])} label "
              f"question), {len(plan['gaps'])} left out")
        if not plan["pages"]:
            print("nothing to re-read")
            return 0
        from pypdf import PdfReader
        reader = PdfReader(ctx["pdf"])
        rd, lines = ctx["readings"], ctx["page_lines"]
        model = (os.getenv("AI_MODEL") or ai.configured_model() or "").strip().lower()
        got, labels, fell_back = [], {}, 0
        for p in sorted(plan["read"]):
            prompt = ai._build_prompt(section_in_force(rd[1], p))
            pdf_bytes = ai._subset_bytes(reader, p - 1, p)
            provs = _read(ai, model, args.model_id, pdf_bytes, prompt)
            # The cheap reader can leave a page's rules out or mis-number them; such a
            # page is read again with the stronger model (Ashfield F p46, 2026-09-25).
            if args.fallback_model_id and (page_missing(lines.get(p, []), provs) or proven_share(
                    provs, rd, ctx["document_id"], p) < MIN_PROVEN_SHARE):
                provs = _read(ai, model, args.fallback_model_id, pdf_bytes, prompt)
                fell_back += 1
            got.append((p, provs))
        for p, rows in sorted(plan["label"].items()):
            prompt = label_prompt(section_in_force(rd[1], p), [body_of(t) for _r, t in rows])
            labs = parse_labels(_ask(model, args.model_id, ai._subset_bytes(reader, p - 1, p), prompt))
            labels.update({r: labs[i + 1] for i, (r, _t) in enumerate(rows) if i + 1 in labs})
        print(f"  pages read again with the fallback model: {fell_back} of {len(plan['read'])}")
        change = build_change(ctx, plan, got, labels)
        if isinstance(change, str):
            print(change)
            return 2
        proven = Counter(cp.prove_citation_any(x["ref_number"], x["new_text"], rd, x.get("new_page"))["status"]
                         for x in change["added"] + change["changed"])
        print(f"change set: {len(change['removed'])} removed, {len(change['changed'])} changed, "
              f"{len(change['added'])} added; new citations {dict(proven)}")
        if args.out:
            Path(args.out).write_text(json.dumps(change, indent=1, ensure_ascii=False), encoding="utf-8")
        if not args.apply:
            print("DRY RUN -- nothing queued. Re-run with --apply.")
            return 0
        print(queue_change(conn, s3, ctx, change))
    return 0


if __name__ == "__main__":
    sys.exit(main())
