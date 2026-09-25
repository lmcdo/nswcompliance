"""Page re-reads through OpenAI's Batch API: the same work as dcp_page_reread at half price.

WHY THIS EXISTS
---------------
A page read cost about 3 cents with the strong model (2026-09-25: $8.53 for 296 reads).
Two things cut that: a cheap model first with the strong one only where the checks fail
(dcp_page_reread), and the Batch API, which charges half for answers returned within
24 hours. This file runs the SAME planning, checks and queueing as dcp_page_reread --
it imports them -- in stages that survive waiting:

    prepare  plan every chapter; write round-1 requests (cheap model)
    submit   upload the pending requests as one batch
    collect  download finished answers; judge every page; pages whose answer failed
             (rules left out, or numbers that do not prove) become round-2 requests
             for the strong model; a chapter whose pages are all settled is queued
             (with --apply) as a targeted change, guarded exactly as the sync tool

    python scripts/dcp_page_batch.py prepare --dir D --chapters-file F [--max-pages 150]
    python scripts/dcp_page_batch.py submit  --dir D
    python scripts/dcp_page_batch.py collect --dir D [--apply]

Nothing is queued without --apply; nothing is ever committed here.

prior-art-checked: reuse, not a new capability -- planning, reading prompts, the
page/label checks, change building, guards and queueing are dcp_page_reread's own
functions; this adds only the batch transport and the saved state between stages.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import dcp_page_reread as R  # noqa: E402

CHEAP, STRONG = "gpt-5.4-mini", "gpt-5.6-sol"


def live_signature(live) -> str:
    """Fingerprint of a chapter's live rules, so answers are never applied to rules
    that changed while the batch was out. Pure."""
    h = hashlib.sha1()
    for ref, text, _d in sorted(live):
        h.update(ref.encode() + b"\0" + (text or "").encode() + b"\0")
    return h.hexdigest()


def request(custom_id: str, model_id: str, pdf_bytes: bytes, prompt: str) -> dict:
    """One Batch API line: the same call ai_extractor._call_sol makes. Pure."""
    data = base64.standard_b64encode(pdf_bytes).decode()
    return {"custom_id": custom_id, "method": "POST", "url": "/v1/chat/completions",
            "body": {"model": model_id, "response_format": {"type": "json_object"},
                     "messages": [{"role": "user", "content": [
                         {"type": "file", "file": {"filename": "page.pdf",
                                                   "file_data": f"data:application/pdf;base64,{data}"}},
                         {"type": "text", "text": prompt}]}]}}


def cid(key: str, page: int, kind: str, rnd: int) -> str:
    return f"{key}|{page}|{kind}|{rnd}"


def chapter_of(custom_id: str) -> str:
    return custom_id.rsplit("|", 3)[0]


def _load_state(d: Path) -> dict:
    f = d / "state.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {
        "chapters": {}, "pending": {}, "answers": {}, "batches": []}


def _save_state(d: Path, st: dict) -> None:
    (d / "state.json").write_text(json.dumps(st, indent=1), encoding="utf-8")


def _connect():
    import boto3
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    return conn, s3


def _page_requests(ctx, read_pages, label_rows, key, rnd, model_id, only=None) -> list[dict]:
    """Request lines for the given read pages and label pages (only those in `only`)."""
    import ai_extractor as ai
    from pypdf import PdfReader
    reader = PdfReader(ctx["pdf"])
    rd = ctx["readings"]
    out = []
    for p in sorted(read_pages):
        if only is None or (p, "read") in only:
            out.append(request(cid(key, p, "read", rnd), model_id, ai._subset_bytes(reader, p - 1, p),
                               ai._build_prompt(R.section_in_force(rd[1], p))))
    for p, rows in sorted(label_rows.items()):
        if only is None or (p, "label") in only:
            out.append(request(cid(key, p, "label", rnd), model_id, ai._subset_bytes(reader, p - 1, p),
                               R.label_prompt(R.section_in_force(rd[1], p), [R.body_of(t) for _r, t in rows])))
    return out


def prepare(d: Path, chapters: list[str], max_pages: int) -> None:
    st = _load_state(d)
    conn, s3 = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        for key in chapters:
            if key in st["chapters"]:
                continue
            council, chapter = key.split("/", 1)
            with tempfile.TemporaryDirectory() as tmp:
                ctx = R.load_chapter(cur, s3, council, chapter, tmp)
                if isinstance(ctx, str):
                    st["chapters"][key] = {"status": "skipped", "why": ctx}
                else:
                    plan = R.plan_pages(ctx, max_pages)
                    if isinstance(plan, str) or not plan["pages"]:
                        st["chapters"][key] = {"status": "skipped",
                                               "why": plan if isinstance(plan, str) else "nothing to re-read"}
                    else:
                        for line in _page_requests(ctx, plan["read"], plan["label"], key, 1, CHEAP):
                            st["pending"][line["custom_id"]] = line
                        st["chapters"][key] = {
                            "status": "planned", "sig": live_signature(ctx["live"]),
                            "read": sorted(plan["read"]),
                            "label": {str(p): [r for r, _t in rows] for p, rows in plan["label"].items()}}
            print(f"{key}: {st['chapters'][key]['status']} {st['chapters'][key].get('why', '')[:100]}")
            _save_state(d, st)
    finally:
        conn.close()
    print(f"pending requests: {len(st['pending'])}")


def submit(d: Path) -> None:
    import openai
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    st = _load_state(d)
    if not st["pending"]:
        print("nothing pending")
        return
    f = d / f"requests_{len(st['batches']) + 1}.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in st["pending"].values()), encoding="utf-8")
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    with f.open("rb") as fh:
        up = client.files.create(file=fh, purpose="batch")
    b = client.batches.create(input_file_id=up.id, endpoint="/v1/chat/completions",
                              completion_window="24h")
    st["batches"].append({"id": b.id, "ids": list(st["pending"]), "collected": False})
    st["pending"] = {}
    _save_state(d, st)
    print(f"submitted batch {b.id} with {len(st['batches'][-1]['ids'])} requests")


def judge(ctx, key: str, entry: dict, answers: dict):
    """Settle a chapter's pages from its answers: (got, labels, retry), where retry is
    {(page, kind)} for the strong model. A round-2 answer is final either way."""
    import ai_extractor as ai
    got, labels, retry = [], {}, set()
    rd, lines = ctx["readings"], ctx["page_lines"]
    for p in entry["read"]:
        a2, a1 = answers.get(cid(key, p, "read", 2)), answers.get(cid(key, p, "read", 1))
        provs = ai.parse_provisions(a2 if a2 is not None else (a1 or ""))
        if a2 is None and (R.page_missing(lines.get(p, []), provs) or R.proven_share(
                provs, rd, ctx["document_id"], p) < R.MIN_PROVEN_SHARE):
            retry.add((p, "read"))
        got.append((p, provs))
    for ps, refs in entry["label"].items():
        p = int(ps)
        a2, a1 = answers.get(cid(key, p, "label", 2)), answers.get(cid(key, p, "label", 1))
        labs = R.parse_labels(a2 if a2 is not None else (a1 or ""))
        mine = {r: labs[i + 1] for i, r in enumerate(refs) if i + 1 in labs}
        labels.update(mine)
        if a2 is None:
            trial = R.build_change(ctx, {"read": set(), "gaps": set(), "label": {}}, [], mine)
            fixed = {x["ref_number"] for x in trial["removed"]} if isinstance(trial, dict) else set()
            if any(r not in fixed for r in refs):
                retry.add((p, "label"))
    return got, labels, retry


def collect(d: Path, apply: bool) -> None:
    import openai
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    st = _load_state(d)
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    for b in st["batches"]:
        if b["collected"]:
            continue
        info = client.batches.retrieve(b["id"])
        print(f"batch {b['id']}: {info.status} {info.request_counts}")
        if info.status not in ("completed", "expired", "cancelled", "failed"):
            continue
        for fid in (info.output_file_id, info.error_file_id):
            if not fid:
                continue
            for line in client.files.content(fid).text.splitlines():
                if line.strip():
                    x = json.loads(line)
                    body = (x.get("response") or {}).get("body") or {}
                    choice = (body.get("choices") or [{}])[0]
                    st["answers"][x["custom_id"]] = (choice.get("message") or {}).get("content") or ""
        b["collected"] = True
    _save_state(d, st)
    waiting = {chapter_of(c) for b in st["batches"] if not b["collected"] for c in b["ids"]}
    waiting |= {chapter_of(c) for c in st["pending"]}
    conn, s3 = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        for key, entry in st["chapters"].items():
            if entry["status"] != "planned" or key in waiting:
                continue
            council, chapter = key.split("/", 1)
            with tempfile.TemporaryDirectory() as tmp:
                ctx = R.load_chapter(cur, s3, council, chapter, tmp)
                if isinstance(ctx, str) or live_signature(ctx["live"]) != entry["sig"]:
                    entry.update(status="stale", why=ctx if isinstance(ctx, str) else "live rules changed")
                else:
                    got, labels, retry = judge(ctx, key, entry, st["answers"])
                    if retry:
                        text_of = {r: t for r, t, _d in ctx["live"]}
                        label_rows = {int(p): [(r, text_of[r]) for r in refs if r in text_of]
                                      for p, refs in entry["label"].items()}
                        for line in _page_requests(ctx, set(entry["read"]), label_rows, key, 2, STRONG,
                                                   only=retry):
                            st["pending"][line["custom_id"]] = line
                        print(f"{key}: {len(retry)} page(s) go to the strong model")
                        _save_state(d, st)
                        continue
                    plan = {"read": set(entry["read"]), "gaps": R.plan_pages(ctx, 10 ** 6)["gaps"],
                            "label": {}}
                    change = R.build_change(ctx, plan, got, labels)
                    if isinstance(change, str):
                        entry.update(status="refused", why=change)
                    elif apply:
                        entry.update(status="queued", why=R.queue_change(conn, s3, ctx, change))
                    else:
                        entry.update(status="ready", why=f"{len(change['removed'])} removed, "
                                     f"{len(change['changed'])} changed, {len(change['added'])} added")
            print(f"{key}: {entry['status']} {entry.get('why', '')[:120]}")
            _save_state(d, st)
    finally:
        conn.close()
    print(f"pending requests for the next submit: {len(st['pending'])}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("stage", choices=["prepare", "submit", "collect"])
    ap.add_argument("--dir", required=True)
    ap.add_argument("--chapters-file")
    ap.add_argument("--max-pages", type=int, default=150)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    d = Path(a.dir)
    d.mkdir(parents=True, exist_ok=True)
    if a.stage == "prepare":
        chapters = [x.strip() for x in Path(a.chapters_file).read_text().splitlines() if x.strip()]
        prepare(d, chapters, a.max_pages)
    elif a.stage == "submit":
        submit(d)
    else:
        collect(d, a.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
