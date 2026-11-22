#!/usr/bin/env python3
# prior-art-checked: scripts/link_controls_to_provisions.py links a control to a provision ONLY when the control's stored quote is already a
# substring of exactly one provision, so a control whose stored text is a PARAPHRASE can never link (Waverley: 58 of 59 controls were typed
# summaries in May 2026). scripts/dcp_quote_status.py proves a stored quote against the PDF but never edits it. Nothing replaced a
# paraphrase with the council's own words. The earlier one-off batches (data/db_rollback_backups batch1..5_requote) are not in scripts/.
# docs: ~/.claude/plans/ce-dcp-controls-verify-and-link-PLAN-2026-10-07.md (step 2: the number must be inside the linked provision's text).
"""Replace a control's paraphrased quote with the council's own words, taken from the council's CURRENT live rules, and link it.

WHY. After a council's plan is republished, its numeric controls (dcp_setback_controls) do not follow: they are a separate table, often typed or
AI-written summaries, and fail the word-for-word check against the new file. Waverley, 2026-11-23: 59 controls, 0 served.

THE RULE (the same whoever proposes the quote, a program or a reader):
  PROVEN  the quote is an exact substring (whitespace aside) of the text of a CURRENT rule of THIS council, AND it contains every number of
          the control as a whole token, AND it is not shared with another control of a different value (a table cell that cannot say
          which row it answers is not a quote for any of them).
  Anything else is left alone and reported. The program never guesses: a proposal that fails the rule is dropped, not repaired.

PROPOSERS. (1) propose(): a deterministic pass over the council's rules, one unit (line or sentence) at a time; it accepts a unit only when it
holds all the control's numbers and clearly beats the next unit. (2) --answers FILE: a JSON list [{control_id, provision_id, quote}] from a
reader (for example a Sonnet pass over the candidates written by --candidates). Both go through the same rule.

WHAT IT WRITES (--apply only; dry run is the default): source_text := the council's words, pdf_page := the rule's page, provision_id := the rule,
on the proven rows only, after a CSV backup, each guarded on the values read at planning time (any change since aborts the whole write).
It does NOT prove and does NOT release. Migration 120 wipes quote_status on this edit, so run next:
    python scripts/dcp_quote_status.py --council <lga> --apply      # proves against the PDF
    python scripts/requote_controls_from_provisions.py --council <lga> --release   # dry run; --apply to release rows proven verbatim
--release only frees rows held for a quote reason (never a person's written hold) and only when quote_status = 'verbatim' and a provision is linked.

usage:  python scripts/requote_controls_from_provisions.py --council waverley [--answers FILE] [--candidates OUT] [--apply]
        python scripts/requote_controls_from_provisions.py --council waverley --release [--apply]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
MARGIN = 1.5            # noqa: regulatory-number -- engineering margin: best unit must beat the runner-up by this factor, not a planning figure
MIN_QUOTE = 8           # noqa: regulatory-number -- shortest quote worth storing, in characters
MAX_QUOTE = 400         # noqa: regulatory-number -- longest quote, in characters (one sentence or one table row)
HOLD_REASON = re.compile(r"(quote not word-for-word in source PDF \(whole-PDF check [0-9-]+\)"
                         r"|quote not proven word for word on the cited PDF page \((unchecked|wrong_page|not_found|no_source)\)"
                         r"|chapter_pdf_changed)")   # the complete reasons the quote check writes; HOLD_REASON.fullmatch, never a prefix, so a person's note is never released
_NUM = re.compile(r"\d+(?:\.\d+)?")
_STOP = set("the a an of to and or for in on is are be must not shall with by at as that this from all any".split())


def ws(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def numbers_of(ctl: dict) -> set[str]:
    return {("%g" % float(v)) for v in (ctl.get("value_min"), ctl.get("value_max")) if v is not None}


def units(text: str) -> list[str]:
    """The pieces a quote may be taken from: each line, and each sentence inside a long line. Whitespace-normalised, empties dropped."""
    out: list[str] = []
    for line in (text or "").split("\n"):
        line = ws(line)
        if not line:
            continue
        out.append(line)
        if len(line) > MAX_QUOTE:
            out.extend(ws(p) for p in re.split(r"(?<=[.;:])\s+", line) if ws(p))
    return [u for u in out if MIN_QUOTE <= len(u) <= MAX_QUOTE]


LABEL = re.compile(r"^(?:[A-Za-z]{0,3}[0-9]+(?:[.][0-9]+)*[.)]?|[(][a-z0-9]+[)]|[-*>#]+)" + chr(92) + "s*")   # O1, 3.2.1, (a), a bullet or a heading mark
OBJECTIVE = re.compile(r"^(to|the objectives? (of|are|is))" + chr(92) + "b", re.I)   # an objective states an aim ("To support ... target"), not a control a lot must meet


def prove(quote: Optional[str], provision_text: Optional[str], ctl: dict) -> tuple[bool, str]:
    """(ok, reason). The rule in the module docstring, minus the cross-control ambiguity test (see ambiguous())."""
    q = ws(quote)
    if not q or not MIN_QUOTE <= len(q) <= MAX_QUOTE:
        return False, "no quote or wrong length"
    if q not in ws(provision_text):
        return False, "not an exact substring of the rule"
    bare = q
    for _ in range(6):          # a label may be stacked: "# O1 (a) To support ..."
        bare = LABEL.sub("", bare, count=1).strip()
    if OBJECTIVE.match(q) or OBJECTIVE.match(bare):
        return False, "an objective, not a control"
    want = numbers_of(ctl)
    if want and not want <= set(_NUM.findall(q)):
        return False, "the quote does not hold the control's number"
    return True, "proven"


def ambiguous(planned: dict[int, dict]) -> set[int]:
    """Control ids whose quote is also planned for a control of a DIFFERENT value: a table cell block cannot say which row it answers."""
    by_q: dict[str, list[int]] = collections.defaultdict(list)
    for cid, p in planned.items():
        by_q[p["quote"]].append(cid)
    out: set[int] = set()
    for q, ids in by_q.items():
        vals = {(planned[i]["ctl"].get("value_min"), planned[i]["ctl"].get("value_max")) for i in ids}
        if len(vals) > 1:
            out.update(ids)
    return out


def _tok(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+|\d+(?:\.\d+)?", (s or "").lower()) if w not in _STOP]


class Index:
    """IDF-weighted word overlap over a council's current rules (units, not whole rules)."""

    def __init__(self, provs: list[dict]):
        self.rows: list[tuple[int, Any, str, set[str]]] = []
        df: collections.Counter = collections.Counter()
        for p in provs:
            for u in units(p["text"]):
                s = set(_tok(u))
                self.rows.append((p["id"], p.get("page"), u, s))
                df.update(s)
        self.n = max(1, len(self.rows))
        self.df = df

    def score(self, q: set[str], s: set[str]) -> float:
        return sum(math.log(self.n / (1 + self.df[w])) for w in q & s)

    def best(self, ctl: dict, k: int = 6) -> list[tuple[float, int, Any, str]]:
        q = set(_tok((ctl.get("source_text") or "") + " " + (ctl.get("condition") or "") + " " + str(ctl.get("control_type") or "").replace("_", " ")))
        q |= numbers_of(ctl)
        want = numbers_of(ctl)
        scored = [(self.score(q, s), pid, page, u) for pid, page, u, s in self.rows if want <= set(_NUM.findall(u))]
        scored.sort(key=lambda x: -x[0])
        return scored[:k]


def propose(ctl: dict, idx: Index) -> Optional[tuple[int, Any, str]]:
    """The deterministic proposer: the unit that holds all the control's numbers and clearly beats the next one, else None (needs a reader)."""
    if not numbers_of(ctl):
        return None
    top = idx.best(ctl, 2)
    if not top or top[0][0] <= 0:
        return None
    if len(top) > 1 and top[1][0] > 0 and top[0][0] < MARGIN * top[1][0]:
        return None
    return top[0][1], top[0][2], top[0][3]


def plan(ctls: list[dict], provs: list[dict], answers: dict[int, dict], others: Optional[list[dict]] = None) -> tuple[dict[int, dict], dict[int, str]]:
    """(planned, rejected). planned[cid] = {provision_id, page, quote, ctl, by}; rejected[cid] = why it was left alone."""
    by_id = {p["id"]: p for p in provs}
    idx = Index(provs)
    planned: dict[int, dict] = {}
    rejected: dict[int, str] = {}
    for ctl in ctls:
        cid = ctl["id"]
        a = answers.get(cid)
        if a is not None and not (a.get("quote") and a.get("provision_id") in by_id):
            rejected[cid] = "reader gave none"      # a reader's explicit none stands; the program does not overrule it
            continue
        if a:
            pid, quote, by = a["provision_id"], ws(a["quote"]), "reader"
        else:
            got = propose(ctl, idx)
            if not got:
                rejected[cid] = "no proposal"
                continue
            pid, _page, quote = got
            by = "program"
        if not ctl.get("source_chapter_key") or by_id[pid].get("chapter") != ctl.get("source_chapter_key"):
            rejected[cid] = f"{by}: the rule is not in the control's own chapter"
            continue
        ok, why = prove(quote, by_id[pid]["text"], ctl)
        if not ok:
            rejected[cid] = f"{by}: {why}"
            continue
        planned[cid] = {"provision_id": pid, "page": by_id[pid].get("page"), "quote": quote, "ctl": ctl, "by": by}
    for cid in ambiguous(planned):
        rejected[cid] = "ambiguous: the same quote is planned for a control of a different value"
        planned.pop(cid)
    # ... and against EVERY other current control of the council, including ones already proven: a table-cell quote already verbatim for
    # value 0 must not be written onto the control for 0.4.
    held = {ws(o.get("source_text")): [] for o in (others or [])}
    for o in others or []:
        held[ws(o.get("source_text"))].append(o)
    for cid in list(planned):
        q = planned[cid]["quote"]
        mine = (planned[cid]["ctl"].get("value_min"), planned[cid]["ctl"].get("value_max"))
        if any(o["id"] != cid and (o.get("value_min"), o.get("value_max")) != mine for o in held.get(q, [])):
            rejected[cid] = "ambiguous: another current control with a different value already holds this quote"
            planned.pop(cid)
    return planned, rejected


CTL_SQL = """SELECT id, control_type, dev_type, value_min, value_max, unit, condition, source_text, pdf_page, provision_id, source_chapter_key
             FROM dcp_setback_controls WHERE lga = %s AND is_current AND (needs_review IS TRUE OR provision_id IS NULL OR quote_status IS DISTINCT FROM 'verbatim')
             ORDER BY id"""
OTHERS_SQL = """SELECT id, value_min, value_max, source_text FROM dcp_setback_controls WHERE lga = %s AND is_current"""
PROV_SQL = """SELECT id, provision_text, pdf_page, source_chapter_key FROM regulatory_provisions
              WHERE source_council = %s AND is_current AND source_chapter_key = ANY(%s)"""


def _connect(readonly: bool):
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    opts = "-c statement_timeout=60000" + (" -c default_transaction_read_only=on" if readonly else "")
    return psycopg2.connect(os.environ["DATABASE_URL"], options=opts)


def _load(cur, council: str):
    cur.execute(CTL_SQL, (council,))
    cols = [d[0] for d in cur.description]
    ctls = [dict(zip(cols, r)) for r in cur.fetchall()]
    chapters = sorted({r for r in _chapters(cur, council)})
    cur.execute(PROV_SQL, (council, chapters))
    provs = [{"id": i, "text": t, "page": p, "chapter": ch} for i, t, p, ch in cur.fetchall()]
    cur.execute(OTHERS_SQL, (council,))
    others = [dict(zip(("id", "value_min", "value_max", "source_text"), r)) for r in cur.fetchall()]
    return ctls, provs, others


def _chapters(cur, council: str) -> list[str]:
    cur.execute("SELECT DISTINCT source_chapter_key FROM dcp_setback_controls WHERE lga = %s AND is_current AND source_chapter_key IS NOT NULL "
                "AND NOT source_chapter_key LIKE '\\_external%%'", (council,))
    return [r[0] for r in cur.fetchall()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--council", required=True)
    ap.add_argument("--answers", help="JSON list of {control_id, provision_id, quote} from a reader")
    ap.add_argument("--candidates", help="write the top candidate rules per unresolved control to this JSON file for a reader")
    ap.add_argument("--release", action="store_true", help="free rows proven verbatim (dry run unless --apply)")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = _connect(readonly=not a.apply)
    try:
        return _release(conn, a) if a.release else _requote(conn, a)
    finally:
        conn.close()


def _requote(conn, a) -> int:
    cur = conn.cursor()
    ctls, provs, others = _load(cur, a.council)
    answers = {x["control_id"]: x for x in json.loads(Path(a.answers).read_text(encoding="utf-8"))} if a.answers else {}
    planned, rejected = plan(ctls, provs, answers, others)
    print(f"{a.council}: {len(ctls)} controls not yet proven; {len(provs)} current rules; proven proposals {len(planned)} "
          f"({sum(1 for p in planned.values() if p['by'] == 'program')} by program, {sum(1 for p in planned.values() if p['by'] == 'reader')} by reader); left alone {len(rejected)}")
    for why, n in collections.Counter(rejected.values()).most_common():
        print(f"  left alone: {n} x {why}")
    if a.candidates:
        idx = Index(provs)
        out = [{"control_id": c["id"], "control_type": c["control_type"], "dev_type": c["dev_type"], "value_min": float(c["value_min"]) if c["value_min"] is not None else None,
                "value_max": float(c["value_max"]) if c["value_max"] is not None else None, "stored_text": c["source_text"],
                "candidates": [{"provision_id": pid, "page": pg, "text": u} for _s, pid, pg, u in idx.best(c, 6)]} for c in ctls if c["id"] in rejected]
        Path(a.candidates).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"candidates for {len(out)} controls -> {a.candidates}")
    if not a.apply:
        print("dry run: nothing written")
        return 0
    if not planned:
        print("nothing to write")
        return 0
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    back = ROOT / "data" / "db_rollback_backups" / f"requote_controls_{a.council}_pre_{stamp}.csv"
    back.parent.mkdir(parents=True, exist_ok=True)
    by_id = {c["id"]: c for c in ctls}
    with back.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "source_text", "pdf_page", "provision_id"])
        for cid in planned:
            c = by_id[cid]
            w.writerow([cid, c["source_text"], c["pdf_page"], c["provision_id"]])
    print("backup:", back)
    n = 0
    for cid, p in planned.items():
        c = by_id[cid]
        cur.execute("UPDATE dcp_setback_controls SET source_text = %s, pdf_page = %s, provision_id = %s WHERE id = %s AND is_current "
                    "AND source_text IS NOT DISTINCT FROM %s AND pdf_page IS NOT DISTINCT FROM %s AND provision_id IS NOT DISTINCT FROM %s",
                    (p["quote"], p["page"], p["provision_id"], cid, c["source_text"], c["pdf_page"], c["provision_id"]))
        n += cur.rowcount
    if n != len(planned):
        conn.rollback()
        print(f"ABORTED: {len(planned) - n} row(s) changed while planning; nothing written. Re-run.")
        return 1
    conn.commit()
    print(f"WROTE {n} controls. Next: python scripts/dcp_quote_status.py --council {a.council} --apply")
    return 0


def _release(conn, a) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id, review_reason FROM dcp_setback_controls WHERE lga = %s AND is_current AND needs_review IS TRUE "
                "AND quote_status = 'verbatim' AND provision_id IS NOT NULL ORDER BY id", (a.council,))
    rows = cur.fetchall()
    free = [i for i, why in rows if HOLD_REASON.fullmatch(why or "")]
    print(f"{a.council}: {len(rows)} held rows are proven verbatim and linked; {len(free)} are held only for a quote reason (releasable); "
          f"{len(rows) - len(free)} carry a person's note and are left held")
    if not a.apply or not free:
        print("dry run: nothing written" if not a.apply else "nothing to release")
        return 0
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    back = ROOT / "data" / "db_rollback_backups" / f"requote_controls_release_{a.council}_pre_{stamp}.csv"
    with back.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "review_reason"])
        for i, why in rows:
            if i in free:
                w.writerow([i, why])
    print("backup:", back)
    why_by_id = dict(rows)
    n = 0
    for i in free:       # per row, guarded on exactly what was read: a hold a person wrote since is never released
        cur.execute("UPDATE dcp_setback_controls SET needs_review = FALSE, review_reason = NULL, reviewed_at = now() WHERE id = %s AND lga = %s AND is_current "
                    "AND needs_review IS TRUE AND quote_status = 'verbatim' AND provision_id IS NOT NULL AND review_reason IS NOT DISTINCT FROM %s",
                    (i, a.council, why_by_id[i]))
        n += cur.rowcount
    if n != len(free):
        conn.rollback()
        print(f"ABORTED: {len(free) - n} row(s) changed while planning; nothing written.")
        return 1
    conn.commit()
    print(f"RELEASED {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
