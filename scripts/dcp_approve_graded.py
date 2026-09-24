#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no approve script exists. Approval
# runs through the UI one row at a time (app/api/dcp-review/[id]) or one chapter
# at a time (app/api/dcp-review/chapter), and neither can express "approve the
# rows a named verdict class covers". scripts/dcp_commit_approved.py is the next
# stage, not this one: it moves already-approved rows into regulatory_provisions
# and never sets a verdict. The safety shape here -- dry run by default, backup
# CSV first, explicit id lists, printed rollback -- is copied deliberately from
# scripts/retag_applicability_slug_docids.py rather than reinvented.
"""Approve the review-queue rows the repaired fidelity gate has cleared.

WHY THIS EXISTS, AND WHY IT IS NOT "BULK APPROVE"
-------------------------------------------------
On 2026-09-09, 8,875 queued rows were approved in one night and 578 bad rows
went live. That is the accident this file has to not be. Two things make it
different, and both are structural rather than intentions:

  * Every row here carries a verdict from the fidelity gate as REPAIRED on
    2026-09-22. The grader that produced the 2026-09-09 verdicts scored words as
    an unordered bag, ignored short tokens and matched numbers by substring, so
    scrambled text, reversed word order and split numbers all read `grounded`.
    Re-running the fixed grader over the same backlog moved 2,105 "waiting on a
    human" to 106 genuinely flagged.
  * Approval is by NAMED CLASS, and the class is written into `review_reason` on
    every row. "Bulk approved" is not a reason anybody can audit later; "the
    unmatched numbers are page and document references, not controls" is.

WHAT IT REFUSES
---------------
Anything outside the four classes below stays pending. In particular a row with
reversed text (DQ-104) or with an unmatched number that looks like a control on
a page the gate could not even locate is never touched here -- those are the
rows a person is for.

It writes ONLY to dcp_review_queue. Nothing here can reach regulatory_provisions;
`dcp_commit_approved.py` does that, separately, and is itself a dry run by
default.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

#: Unmatched numbers the gate reports, pulled back out of its own detail string.
_MISSING = re.compile(r"numbers not in source: ([^;]+)")

#: A number shaped like a planning CONTROL, kept deliberately narrow so the
#: classes below stay honest:
#:
#:   3.5, 7.8, 0.5   a DECIMAL between 0.5 and 100 -- what a setback, a height
#:                   or a floor space ratio looks like. Held for a person.
#:   11, 94, 2660    a bare integer. Page number, figure number, clause number,
#:                   document reference. Approved.
#:   01, 04          a leading zero is the objective LABEL bug (the page says
#:                   "O1", the reader emitted "01"), not a measurement at all.
#:
#: An earlier version called anything one-to-three digits control-shaped and
#: then only held it when the gate had failed to locate a page, which let `3.5`
#: and `7.8` through as "reference numbers" on a verified page. A one-decimal
#: number in planning range is the single most likely thing to BE a control, so
#: it is held whether or not the page resolved.
def _is_control_shaped(tok) -> bool:
    # Non-str first. `re.fullmatch(pattern, None)` raises TypeError, not
    # ValueError, so the `except ValueError` below would NOT have caught it --
    # a None token would have killed the whole approve run partway through,
    # after some rows had already been updated. No live path produces one today
    # (`missing` is built by `.strip()`ing regex groups, which always yields
    # str), but the crash would be silent about which rows had landed.
    #
    # It answers False rather than True because the question this function asks
    # is literally "is this token a decimal in planning range" — a None is not,
    # and claiming otherwise would hold rows for a person under a reason that
    # names a number that does not exist. The row is still protected by the
    # other rules in `_classify`: reversed text, and >6 unmatched numbers on a
    # page the gate could not locate.
    if not isinstance(tok, str):
        return False
    if not re.fullmatch(r"\d{1,3}\.\d{1,2}", tok):
        return False
    try:
        return 0.5 <= float(tok) <= 100.0
    except ValueError:
        return False


def _classify(fidelity, detail, page_verified, text):
    """Which named class this row falls in, or None to leave it pending."""
    from scripts.dcp_extract_changed import reversed_text_tokens

    detail = detail or ""
    if len({t.lower() for t in reversed_text_tokens(text)}) >= 2:
        return None, "reversed text -- DQ-104, nothing for a person to decide either"

    if fidelity == "grounded":
        return ("grounded",
                "fidelity gate (repaired 2026-09-22): every number and key word "
                "found on this row's own source page")

    if fidelity in (None, "ok"):
        return ("non_actionable",
                "no content to ground -- heading, contents line or objective "
                "text carrying no cited number; the gate skips these rather "
                "than grading them")

    if fidelity in ("flagged", "failed"):
        # DQ-111. Before this line, a citation-only flag has no unmatched number
        # and would fall through to "flagged_other" and be APPROVED. A clause
        # number the council never printed is re-read, never approved by class.
        from scripts.citation_proof import CITATION_FINDING
        if CITATION_FINDING in detail:
            return None, ("clause number not proven on its source page -- re-read, "
                          "not approvable by class: %s" % detail[:120])
        m = _MISSING.search(detail)
        missing = [x.strip() for x in m.group(1).split(",")] if m else []
        control_shaped = [x for x in missing if _is_control_shaped(x)]
        if control_shaped:
            return None, ("unmatched number %s is shaped like a control "
                          "(a decimal in planning range)" % control_shaped[:3])
        if page_verified is None and len(missing) > 6:
            return None, ("%d unmatched numbers and the gate could not locate "
                          "this row's page" % len(missing))
        if missing:
            return ("reference_numbers",
                    "unmatched numbers are page references, figure numbers or "
                    "document reference codes, not controls: %s"
                    % ", ".join(missing[:6]))
        if "number split by the reader" in detail:
            return ("objective_label",
                    "the reader read the letter O as a zero in objective labels "
                    "(page says 'O1', row says '01'); the control text itself "
                    "matched its source page")
        return ("flagged_other",
                "flagged with no unmatched number and no split number: %s"
                % detail[:120])
    return None, "unrecognised fidelity status %r" % fidelity


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Execute. Without this nothing is written.")
    ap.add_argument("--council", help="Limit to one council.")
    ap.add_argument("--reviewer", default="fidelity-gate-2026-09-22",
                    help="Recorded in reviewed_by, so the basis is auditable.")
    ap.add_argument("--classes", nargs="+",
                    default=["grounded", "non_actionable", "reference_numbers",
                             "objective_label", "flagged_other"],
                    help="Which named classes to approve.")
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set -- nothing was checked, which is not "
              "a pass.", file=sys.stderr)
        return 2
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")

    try:
        sql = ("SELECT id, council, chapter_key, fidelity_status, fidelity_detail, "
               "source_page_verified, new_text FROM dcp_review_queue "
               "WHERE status = 'pending'")
        params = ()
        if args.council:
            sql += " AND council = %s"
            params = (args.council,)
        cur.execute(sql, params)
        rows = cur.fetchall()

        plan, held = {}, Counter()
        backup = []
        for pid, council, chapter, fidelity, detail, page, text in rows:
            cls, reason = _classify(fidelity, detail, page, text)
            if cls is None or cls not in args.classes:
                # The held-reason heading, trimmed at the first " --" so the
                # printed tally groups by CAUSE rather than by the specific
                # numbers each row names. `_classify` always returns a reason,
                # and `"".split(x)` yields `['']` rather than `[]`, so neither
                # an empty string nor a missing separator can raise -- but the
                # fallback is explicit rather than resting on that.
                head = (reason or "unclassified").split(" --")
                label = (head[0] if head else "") or "unclassified"
                held[label[:70] if cls is None else cls] += 1
                continue
            plan.setdefault((cls, reason), []).append(pid)
            backup.append((pid, council, chapter, "pending", fidelity, detail))

        print("\n=== approve-graded plan ===")
        print("  pending rows in scope : %s" % format(len(rows), ","))
        print("  to approve            : %s"
              % format(sum(len(v) for v in plan.values()), ","))
        by_class = {}
        for (cls, reason), ids in plan.items():
            n, sample = by_class.get(cls, (0, reason))
            by_class[cls] = (n + len(ids), sample)
        for cls, (n, sample) in sorted(by_class.items(), key=lambda kv: -kv[1][0]):
            print("    %6s  %s" % (format(n, ","), cls))
            print("            e.g. %s" % sample[:130])
        print("  LEFT PENDING for a person : %s"
              % format(sum(held.values()), ","))
        for why, n in held.most_common():
            print("    %6s  %s" % (format(n, ","), why))

        if not args.apply:
            print("\nDRY RUN -- nothing written. Re-run with --apply to execute.")
            return 0

        stamp = datetime.now(timezone.utc)
        out = ROOT / "data" / "db_rollback_backups" / (
            "dcp_review_queue_pre_approve_%s.csv" % stamp.strftime("%Y-%m-%d_%H%M"))
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "council", "chapter_key", "status",
                        "fidelity_status", "fidelity_detail"])
            w.writerows(backup)
        print("\n  backed up %s rows -> %s" % (format(len(backup), ","), out))
        if len(backup) != sum(len(v) for v in plan.values()):
            print("ERROR: backup smaller than plan -- aborting before any UPDATE.",
                  file=sys.stderr)
            return 2

        written = 0
        for (cls, reason), ids in plan.items():
            # Guarded on status: a row a human ruled on while this was running is
            # never overwritten.
            cur.execute(
                "UPDATE dcp_review_queue SET status = 'approved', reviewed_by = %s, "
                "reviewed_at = %s, review_reason = %s "
                "WHERE id = ANY(%s) AND status = 'pending'",
                (args.reviewer, stamp, "%s: %s" % (cls, reason), ids),
            )
            written += cur.rowcount
        conn.commit()
        print("  approved %s rows (%s skipped by the status guard)"
              % (format(written, ","),
                 format(sum(len(v) for v in plan.values()) - written, ",")))
        print("\nROLLBACK: restore status='pending' for the ids in %s" % out.name)
        return 0
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print("ERROR (rolled back): %s" % exc, file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
