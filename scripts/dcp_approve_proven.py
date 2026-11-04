#!/usr/bin/env python3
# prior-art-checked: PLAN ce-council-words-PLAN-2026-10-12.md lines 301-307 (approve step approved 2026-10-12); ported verbatim from the probes folder, never in git.
"""PRODUCTION WRITE (user yes 2026-10-12: "commit"): approve the review-queue rows the checker proves.

For each named chapter, every pending added/changed row is judged AGAIN against the chapter's CURRENT
PDF (scripts/council_quote.judge, code = ref_number) at write time, and approved only when
  exact  AND  >= MIN_CHARS alnum  AND  not starting lowercase (mid-sentence)  AND  not an orphan lead-in
(known-wrong probe 2026-10-12: 0/520 mutations pass; 273/360 known-right pass). Removed rows are approved
only for chapters named in --removals (R2 coverage showed no rule line lost). Everything else stays pending
for a person. Rows read from a PDF other than the active one are never touched.

Backup of every touched row first (status before). Rollback: set status back to 'pending' and clear
reviewed_by/at/reason for reviewed_by = 'auto:council_quote' rows in the backup.

usage: python scripts/dcp_approve_proven.py --chapters c/k,c/k [--removals c/k,...] [--apply]   (dry run unless --apply)
"""
from __future__ import annotations

import argparse
import atexit
import csv
import collections
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
import council_quote as cq
import rule_page_locator as rpl

REVIEWER = "auto:council_quote"
REASON = "printed word for word in the current PDF (council_quote exact, >=25 chars, sentence start)"
REASON_RM = "removal: R2 PDF-line coverage after commit lost no rule line (2026-10-12)"

NL = chr(10)
GAP = 8      # letters/digits allowed between joined parts: a list label ("a", "iv", "12")
ROW_DY = 12  # points: a table cell and its row's name are printed within this height of each other


def table_row(heading, value, page, lines):
    """A short table cell ("1 space per 45sq.m GFA") counts only when the PDF prints it on the same row as the
    use its heading names ("5.3.7 Bulky goods premises"): a line holding the value and, within ROW_DY points on
    that page, a line holding the first 12 letters of the name. Otherwise a rate could be paired with the wrong
    use (plan R4)."""
    name = cq.norm(heading.split(" ", 1)[1] if " " in heading else "")[:12]
    val = cq.norm(value)
    if len(name) < 6 or not val:
        return False
    on_page = [ln for ln in lines if ln.page == page]
    ys = [ln.y for ln in on_page if val in cq.norm(ln.text)]
    return any(abs(ln.y - y) <= ROW_DY and name in cq.norm(ln.text) for y in ys for ln in on_page)
#: a list label at the end of a queue ref: "..._5_2_3 (a)", "... b)", "... (ii)", "... 3."
REF_ITEM = re.compile(r"\s+\(?(?:[a-z]|[ivx]{1,4}|\d{1,2})[).]$")
_WORDS = re.compile(r"[a-z0-9]+")
REASON_HEAD = "heading, not a rule: printed, 6 words or fewer, no number, no rule wording"
REASON_JOIN = "list rejoined with its lead-in; the joined text is printed word for word in the current PDF"
#: a heading with a list-item label after its code: "B1.2.2 a) Streetscape ..." -> lead-in "B1.2.2 Streetscape ..."
ITEM = re.compile(r"^(\S+)\s+\(?(?:[a-z]|[ivx]{1,4}|\d{1,2})[).]\s+(.*)$")


def head(text):
    """The row's '# code title' heading line, without the '#'. '' when there is none."""
    t = (text or "").lstrip()
    return t.partition("\n")[0][1:].strip() if t.startswith("#") else ""


def removal_decision(change_type: str, in_removals: bool) -> str | None:
    """'approve_removal' | 'left_removed' for a removed row; None when the row is not a removal."""
    if change_type != "removed":
        return None
    return "approve_removal" if in_removals else "left_removed"


def plain_approvable(status: str, body: str) -> bool:
    """The core approval test, unchanged: exact AND >= MIN_CHARS alnum AND not starting lowercase AND
    not an orphan lead-in (ends ':' and shorter than 300)."""
    return (status == "exact" and len(cq.norm(body)) >= cq.MIN_CHARS and not re.match(r"[a-z]", body)
            and not (body.endswith(":") and len(body) < 300))


#: pending rows are read only from the chapter's ACTIVE PDF: active registry entry + matching content hash
CHAPTER_ROWS_SQL = """SELECT q.id, q.change_type, q.ref_number, q.new_text, q.new_page, reg.r2_current_path,
                          q.created_at, q.source_content_hash, q.document_id, q.is_full_replace
                     FROM dcp_review_queue q JOIN dcp_chapter_registry reg
                       ON reg.council = q.council AND reg.chapter_key = q.chapter_key AND reg.is_active
                    WHERE q.status = 'pending' AND q.council = %s AND q.chapter_key = %s
                      AND q.source_content_hash = reg.content_hash ORDER BY q.id"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", required=True)
    ap.add_argument("--removals", default="")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    WT = Path(__file__).resolve().parents[1]
    chapters = [tuple(x.split("/")) for x in a.chapters.split(",") if x]
    removals = {tuple(x.split("/")) for x in a.removals.split(",") if x}

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    # main() leaves through sys.exit on several paths; close the connection on every one.
    # prior-art-checked: PLAN ce-council-words-PLAN-2026-10-12.md lines 301-307 -- closes the
    # script's existing connection (push gate: connection leak); no new data source.
    atexit.register(conn.close)
    cur = conn.cursor()
    cur.execute("SET lock_timeout = '5s'")
    cur.execute("SET statement_timeout = '30s'")
    approve, approve_rm, report = [], [], []
    headings, joins = [], []
    tabled = [0]
    leadins = [0]
    listed = [0]
    for council, key in chapters:
        cur.execute(CHAPTER_ROWS_SQL, (council, key))
        meta = cur.fetchall()
        rows = [r[:6] for r in meta]
        if not rows:
            report.append((council, key, 0, 0, 0, 0))
            continue
        readings, cased = cq.load_chapter(rows[0][5])
        streams = [cq.Stream(ch, cased) for ch in readings]
        # LIST ITEMS (added after the Woollahra B1 dry run): "B1.2.2 a)" + "the rich mixture of ...;" starts lowercase
        # because its label sits in the code. It is a whole rule when its lead-in -- the row coded "B1.2.2" whose text
        # ends ':' -- is in the same batch (pending or approved). Then both the items and the lead-in are approvable.
        cur.execute("""SELECT q.ref_number, q.new_text FROM dcp_review_queue q JOIN dcp_chapter_registry reg
                         ON reg.council = q.council AND reg.chapter_key = q.chapter_key AND reg.is_active
                      WHERE q.council = %s AND q.chapter_key = %s AND q.status IN ('pending', 'approved')
                        AND q.change_type <> 'removed' AND q.source_content_hash = reg.content_hash""", (council, key))
        batch_rows = cur.fetchall()
        lead_ins = {head(t) for _ref, t in batch_rows if rpl.rule_body(t or "").strip().endswith(":")}
        item_parents = {m.group(1) + " " + m.group(2) for _ref, t in batch_rows if (m := ITEM.match(head(t)))}
        ok, rm, left = [], [], collections.Counter()
        # SPLIT LISTS (Blacktown pilot 2026-10-13): the reader returned a list's lead-in as the row coded "5_2_3" and its
        # items as rows coded "5_2_3 (a)", "(b)", ... each starting lowercase. Rejoined by code (items in queue order);
        # the joined text is approved only when the checker finds it printed word for word, and the parts are then
        # superseded by it. A group none of whose items starts lowercase is left as it is.
        live_rows = [r for r in meta if r[1] != "removed"]
        by_ref = {str(r[2] or "").strip(): r for r in live_rows}
        groups = collections.defaultdict(list)
        for r in live_rows:
            parent = REF_ITEM.sub("", str(r[2] or "").strip())
            if parent != str(r[2] or "").strip() and parent in by_ref:
                groups[parent].append(r)
        taken = set()
        for parent, items in groups.items():
            lead = by_ref[parent]
            lb = rpl.rule_body(lead[3] or "").strip()
            if not any(re.match(r"[a-z]", rpl.rule_body(r[3] or "").strip()) for r in items):
                continue
            items.sort(key=lambda r: r[0])
            # the item's label sits in its code, not its text; the PDF prints it ("(a) ...") unless it prints bullets
            labelled = lb + NL + NL.join(REF_ITEM.search(str(r[2])).group(0).strip() + " "
                                         + rpl.rule_body(r[3] or "").strip() for r in items)
            bare = lb + NL + NL.join(rpl.rule_body(r[3] or "").strip() for r in items)
            for body_j in (labelled, bare):
                jj = cq.judge({"id": lead[0], "source_council": council, "pdf_page": lead[4], "page_check": None,
                               "provision_text": body_j, "code": lead[2]}, streams)
                if jj["status"] == "exact" and len(body_j) <= cq.OVERSIZED:
                    text_j = ("# " + head(lead[3]) + NL + NL if head(lead[3]) else "") + body_j
                    joins.append({"parts": [lead[0]] + [r[0] for r in items], "ref": lead[2], "text": text_j,
                                  "page": jj.get("quote_page") or lead[4], "meta": lead[6:10], "council": council,
                                  "key": key})
                    taken.update([lead[0]] + [r[0] for r in items])
                    break
        # BY POSITION (Blacktown pilot, second pass): the reader also coded items under the NEIGHBOURING section, so
        # their codes do not lead to their lead-in. Each remaining row is found in the PDF's reading order; a lead-in
        # ending ':' joins the rows printed straight after it that start lowercase, with a bullet, or carry a list label,
        # when nothing but a label (<= GAP letters) lies between them. The joined text is COPIED from the PDF over that
        # span (so the council's own labels are kept) and judged again before it counts.
        st = streams[-1]
        placed = []
        for r in live_rows:
            if r[0] in taken:
                continue
            q = cq.norm(rpl.rule_body(r[3] or ""))
            if len(q) < 8:
                continue
            hits = st.find_all(q, cap=10)
            if not hits:
                continue
            k = next((h for h in hits if st.page(h) == r[4]), hits[0])
            placed.append((k, k + len(q) - 1, r))
        placed.sort(key=lambda x: x[0])
        i = 0
        while i < len(placed):
            k0, end, lead = placed[i]
            lb = rpl.rule_body(lead[3] or "").strip()
            j = i + 1
            group = []
            while lb.endswith(":") and j < len(placed):
                ks, ke, r = placed[j]
                b = rpl.rule_body(r[3] or "").strip()
                is_item = bool(re.match(r"[a-z]", b)) or b[:1] in "•-–·▪" or bool(REF_ITEM.search(str(r[2] or "")))
                if not is_item or not (0 <= ks - end - 1 <= GAP):
                    break
                group.append(r)
                end = ke
                j += 1
            if group:
                span = st.copy(k0, end)
                jj = cq.judge({"id": lead[0], "source_council": council, "pdf_page": lead[4], "page_check": None,
                               "provision_text": span, "code": lead[2]}, streams)
                if jj["status"] == "exact" and len(span) <= cq.OVERSIZED:
                    text_j = ("# " + head(lead[3]) + NL + NL if head(lead[3]) else "") + span
                    joins.append({"parts": [lead[0]] + [r[0] for r in group], "ref": lead[2], "text": text_j,
                                  "page": jj.get("quote_page") or lead[4], "meta": lead[6:10], "council": council,
                                  "key": key})
                    taken.update([lead[0]] + [r[0] for r in group])
                    i = j
                    continue
            i += 1
        # MISSING LEAD-IN (Blacktown pilot, third pass): the reader kept a list's items but dropped the sentence that
        # introduces them ("The objectives of this Part of the DCP are to:"). For a run of item rows with no lead row
        # before it, the lead-in is taken from the PDF: the lines just before the first item, back to the end of the
        # previous sentence, when the last of them ends ':' and no row already holds it. Copied over the span and
        # judged again, like every join.
        first_char = {}
        for idx, (li, _p) in enumerate(st.at):
            first_char.setdefault(li, idx)
        all_norm = [cq.norm(rpl.rule_body(t or "")) for _r, t in batch_rows]
        rest = [x for x in placed if x[2][0] not in taken]
        i = 0
        while i < len(rest):
            ks, ke, r = rest[i]
            b = rpl.rule_body(r[3] or "").strip()
            if not re.match(r"[a-z]", b):
                i += 1
                continue
            li = st.at[ks][0]
            j = li - 1
            while j >= 0 and not cq.norm(st.text[j]):
                j -= 1
            if j < 0 or not st.text[j].rstrip().endswith(":") or st.lines[j].page != st.lines[li].page:
                i += 1
                continue
            start = j
            while (start - 1 >= 0 and j - start < 4 and st.lines[start - 1].page == st.lines[j].page
                   and not st.text[start - 1].rstrip().endswith((".", ":", ";")) and cq.norm(st.text[start - 1])):
                start -= 1
            lead_norm = cq.norm(" ".join(st.text[start:j + 1]))
            if not lead_norm or any(lead_norm in x for x in all_norm):
                i += 1
                continue
            group, end, k = [r], ke, i + 1
            while k < len(rest):
                ks2, ke2, r2 = rest[k]
                b2 = rpl.rule_body(r2[3] or "").strip()
                if not (re.match(r"[a-z]", b2) or b2[:1] in "•-–·▪" or REF_ITEM.search(str(r2[2] or ""))) \
                        or not (0 <= ks2 - end - 1 <= GAP):
                    break
                group.append(r2)
                end = ke2
                k += 1
            span = st.copy(first_char.get(start, ks), end)
            jj = cq.judge({"id": r[0], "source_council": council, "pdf_page": r[4], "page_check": None,
                           "provision_text": span, "code": r[2]}, streams)
            if jj["status"] == "exact" and len(span) <= cq.OVERSIZED:
                parent = REF_ITEM.sub("", str(r[2] or "").strip())
                hd = head(r[3])
                hd = REF_ITEM.sub("", hd.split(" ", 1)[0]) + (" " + hd.split(" ", 1)[1] if " " in hd else "") if hd else ""
                joins.append({"parts": [x[0] for x in group], "ref": parent, "text": ("# " + hd + NL + NL if hd else "") + span,
                              "page": jj.get("quote_page") or r[4], "meta": r[6:10], "council": council, "key": key})
                taken.update(x[0] for x in group)
                leadins[0] += 1
                i = k
                continue
            i += 1
        for qid, ctype, ref, new, page, _p in rows:
            if qid in taken:
                continue
            rd = removal_decision(ctype, (council, key) in removals)
            if rd is not None:
                if rd == "approve_removal":
                    rm.append(qid)
                else:
                    left["removed"] += 1
                continue
            body = rpl.rule_body(new or "").strip()
            j = cq.judge({"id": qid, "source_council": council, "pdf_page": page, "page_check": None,
                          "provision_text": new or "", "code": ref}, streams)
            m = ITEM.match(head(new))
            is_item = bool(m) and (m.group(1) + " " + m.group(2)) in lead_ins   # an item whose lead-in is present
            is_lead = body.endswith(":") and head(new) in item_parents          # a lead-in whose items are present
            words = _WORDS.findall(body.lower())
            if (j["status"] == "exact" and 0 < len(words) <= 6 and not re.search(r"\d", body)
                    and not cq._RULE_WORDS.search(body.lower()) and not body.endswith(":")):
                headings.append(qid)          # a bare heading ("Cool roofs"): printed, not a rule
                continue
            if j["status"] == "exact" and re.search(r"\d", body) and len(cq.norm(body)) < cq.MIN_CHARS \
                    and table_row(head(new), body, page, readings[-1].lines):
                ok.append(qid)                 # a table cell proven on the same printed row as its use
                tabled[0] += 1
                continue
            if j["status"] == "exact" and (is_item or is_lead):
                ok.append(qid)
                listed[0] += 1
            elif plain_approvable(j["status"], body):
                ok.append(qid)
            else:
                left[j["status"]] += 1
        approve += ok
        approve_rm += rm
        report.append((council, key, len(rows), len(ok), len(rm), sum(left.values())))
        print(f"{council}/{key}: pending {len(rows)} -> approve {len(ok)} proven (list items + lead-ins {listed[0]}) "
              f"+ {len(rm)} removals; headings {sum(1 for h in headings)} (running total); "
              f"lists rejoined {sum(1 for x in joins if x['key'] == key)} from {len(taken)} rows; table cells {tabled[0]}; lead-ins copied from the PDF {leadins[0]}; "
              f"left for a person {sum(left.values())} {dict(left)}", flush=True)

    print(f"TOTAL approve {len(approve)} proven + {len(approve_rm)} removals; headings superseded {len(headings)}; "
          f"lists rejoined {len(joins)} (replacing {sum(len(x['parts']) for x in joins)} rows)")
    if not a.apply:
        print("dry run: nothing written")
        sys.exit(0)
    ids = approve + approve_rm + headings + [p for x in joins for p in x["parts"]]
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup = WT / "data" / "db_rollback_backups" / f"dcp_review_queue_pre_auto_approve_{stamp}.csv"
    backup.parent.mkdir(parents=True, exist_ok=True)
    cur.execute("SELECT id, council, chapter_key, status, reviewed_by, reviewed_at, review_reason "
                "FROM dcp_review_queue WHERE id = ANY(%s)", (ids,))
    with backup.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([d[0] for d in cur.description])
        w.writerows(cur.fetchall())
    print(f"backup: {backup}")
    cur.execute("""UPDATE dcp_review_queue SET status = 'approved', reviewed_by = %s, reviewed_at = now(),
                   review_reason = %s WHERE id = ANY(%s) AND status = 'pending'""", (REVIEWER, REASON, approve))
    n1 = cur.rowcount
    cur.execute("""UPDATE dcp_review_queue SET status = 'approved', reviewed_by = %s, reviewed_at = now(),
                   review_reason = %s WHERE id = ANY(%s) AND status = 'pending' AND change_type = 'removed'""",
                (REVIEWER, REASON_RM, approve_rm))
    n2 = cur.rowcount
    cur.execute("""UPDATE dcp_review_queue SET status = 'superseded', reviewed_by = %s, reviewed_at = now(),
                   review_reason = %s WHERE id = ANY(%s) AND status = 'pending'""", (REVIEWER, REASON_HEAD, headings))
    n3 = cur.rowcount
    parts = [p for x in joins for p in x["parts"]]
    cur.execute("""UPDATE dcp_review_queue SET status = 'superseded', reviewed_by = %s, reviewed_at = now(),
                   review_reason = %s WHERE id = ANY(%s) AND status = 'pending'""", (REVIEWER, REASON_JOIN, parts))
    n4 = cur.rowcount
    for x in joins:
        created, chash, doc_id, full = x["meta"]
        cur.execute("""INSERT INTO dcp_review_queue (council, chapter_key, document_id, ref_number, change_type, new_text,
                         new_page, source_content_hash, is_full_replace, created_at, status, reviewed_by, reviewed_at,
                         review_reason)
                       VALUES (%s, %s, %s, %s, 'added', %s, %s, %s, %s, %s, 'approved', %s, now(), %s)""",
                    (x["council"], x["key"], doc_id, x["ref"], x["text"], x["page"], chash, full, created,
                     REVIEWER, REASON_JOIN))
    if n1 != len(approve) or n2 != len(approve_rm) or n3 != len(headings) or n4 != len(parts):
        conn.rollback()
        print(f"ROLLED BACK: updated {n1}/{len(approve)} and {n2}/{len(approve_rm)} (rows changed meanwhile)")
        sys.exit(1)
    conn.commit()
    print(f"WRITTEN: approved {n1} proven + {n2} removals; {n3} headings superseded; {len(joins)} lists rejoined "
          f"({n4} parts superseded)")



if __name__ == "__main__":
    main()
