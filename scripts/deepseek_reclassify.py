"""Batch dev-type re-classification suggestions via DeepSeek — REVIEW-ONLY.

prior-art-checked: services/conveyancing.py is the conveyancing report
orchestrator (PDF generation + data fetchers); it contains no LLM
classification, no DeepSeek/OpenAI-compatible client, and no suggestion-CSV
workflow — token overlap (call/vocabulary) is coincidental. No existing module
provides budget-LLM batch classification with a DB-derived label vocabulary.

Reads provisions for one council, asks DeepSeek V3 (OpenAI-compatible API) to
suggest `v2_applicable_dev_types` labels, and writes a CSV of suggestions for
human review. This script NEVER writes to the database — applying accepted
suggestions is a separate, deliberate step (see tag-provisions skill).

Why DeepSeek: text-only classification gated by human review is the one slot
where a budget model is defensible (~$0.28/M in, $0.42/M out ≈ $5-6 per LGA vs
~$48 with the previous Gemini anchor). Do NOT use budget models for the
fidelity/verify pass — that stays on a frontier model.

Setup:
  1. Add DEEPSEEK_API_KEY to root .env (https://platform.deepseek.com)
  2. DATABASE_URL must be set (root .env)

Usage:
  python scripts/deepseek_reclassify.py --council waverley --limit 50   # trial
  python scripts/deepseek_reclassify.py --council waverley              # full
Output: data/reclassify_review/<council>_devtype_suggestions_<date>.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import psycopg2

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
BATCH_SIZE = 20          # provisions per API call
MAX_RETRIES = 3
OUT_DIR = Path("data/reclassify_review")


def get_vocabulary(cur) -> list[str]:
    """Allowed labels = what the corpus already uses. Never invent labels."""
    cur.execute(
        """SELECT DISTINCT unnest(v2_applicable_dev_types) AS label
           FROM regulatory_provisions
           WHERE v2_applicable_dev_types IS NOT NULL
           ORDER BY 1"""
    )
    vocab = [r[0] for r in cur.fetchall()]
    if not vocab:
        sys.exit("No existing v2_applicable_dev_types vocabulary found — aborting.")
    return vocab


def fetch_batch(cur, council: str, after_id: int, limit: int) -> list[dict]:
    cur.execute(
        """SELECT id, ref_number, section_header, provision_text, v2_applicable_dev_types
           FROM regulatory_provisions
           WHERE source_council = %s AND id > %s
           ORDER BY id
           LIMIT %s""",
        (council, after_id, limit),
    )
    return [
        {"id": r[0], "ref": r[1], "section": r[2],
         "text": (r[3] or "")[:2000], "current": r[4]}
        for r in cur.fetchall()
    ]


def call_deepseek(api_key: str, vocab: list[str], batch: list[dict]):
    """Returns ({provision_id: {labels, rationale}}, usage)."""
    items = [
        {"id": p["id"], "section": p["section"], "text": p["text"]} for p in batch
    ]
    prompt = (
        "You classify NSW council DCP provisions by which development types they apply to.\n"
        f"Allowed labels (use ONLY these, choose all that apply): {json.dumps(vocab)}\n"
        "A provision that applies regardless of development type gets every label it "
        "genuinely governs; do not over-tag boilerplate. Return STRICT JSON:\n"
        '{"results": [{"id": <id>, "labels": ["..."], "rationale": "<one short sentence>"}]}\n\n'
        f"Provisions:\n{json.dumps(items, ensure_ascii=False)}"
    )
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read())
            content = json.loads(payload["choices"][0]["message"]["content"])
            usage = payload.get("usage", {})
            out = {}
            for r in content.get("results", []):
                labels = [l for l in r.get("labels", []) if l in vocab]  # hard vocab gate
                out[r["id"]] = {"labels": labels, "rationale": r.get("rationale", "")}
            return out, usage
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as e:
            if attempt == MAX_RETRIES:
                raise
            wait = 5 * attempt
            print(f"  API error ({e}); retry {attempt}/{MAX_RETRIES} in {wait}s")
            time.sleep(wait)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--council", required=True, help="source_council value, e.g. waverley")
    ap.add_argument("--limit", type=int, default=None, help="max provisions (trial runs)")
    args = ap.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        sys.exit("DEEPSEEK_API_KEY not set — add it to root .env first.")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30s'")

    vocab = get_vocabulary(cur)
    print(f"vocabulary: {len(vocab)} labels")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{args.council}_devtype_suggestions_{date.today().isoformat()}.csv"
    total = changed = 0
    in_tok = out_tok = 0
    after_id = 0

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "ref_number", "current_labels", "suggested_labels",
                    "differs", "rationale"])
        while True:
            room = BATCH_SIZE if args.limit is None else min(BATCH_SIZE, args.limit - total)
            if room <= 0:
                break
            batch = fetch_batch(cur, args.council, after_id, room)
            if not batch:
                break
            after_id = batch[-1]["id"]
            suggestions, usage = call_deepseek(api_key, vocab, batch)
            in_tok += usage.get("prompt_tokens", 0)
            out_tok += usage.get("completion_tokens", 0)
            for p in batch:
                s = suggestions.get(p["id"])
                if s is None:
                    w.writerow([p["id"], p["ref"], p["current"], "", "NO_RESPONSE", ""])
                    continue
                current = sorted(p["current"] or [])
                suggested = sorted(s["labels"])
                differs = current != suggested
                changed += differs
                w.writerow([p["id"], p["ref"], json.dumps(current),
                            json.dumps(suggested), differs, s["rationale"]])
            total += len(batch)
            print(f"  {total} done ({changed} differ) — tokens in/out: {in_tok}/{out_tok}")

    cost = in_tok / 1e6 * 0.28 + out_tok / 1e6 * 0.42
    print(f"\nWrote {out_path}")
    print(f"{total} provisions, {changed} suggested changes, est. cost ${cost:.2f}")
    print("Review the CSV, then apply accepted rows via the tag-provisions workflow. "
          "This script made no database changes.")
    conn.close()


if __name__ == "__main__":
    main()
