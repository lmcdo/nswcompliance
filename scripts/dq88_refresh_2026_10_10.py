#!/usr/bin/env python3
"""DQ-88 2026-10-10: bring stored SEPP text in line with the law in force (two instruments).

prior-art-checked: reuse not viable because the 2026-09-15 refresh (same method, memory
reference-law-text-refresh-method-2026-09) lived in a scratchpad; this records the edits.

Found by scripts/law_change_diff.py (point-in-time comparison on legislation.nsw.gov.au, run
from the Fly monitor's IP) between the version our text was taken from and today's:
  * Primary Production SEPP (epi-2021-0729), 4 Apr 2025 -> current: s 2.27 repealed
    (2026 (286), Sch 1.9). Rows holding only s 2.27 are retired (is_current FALSE, never
    deleted); the served chunk 22361 that contains it gets the passage replaced by
    "2.27 (Repealed)", as the instrument now reads.
  * Sustainable Buildings SEPP (epi-2022-0521), 5 Apr 2024 -> current: s 2.1(2A) inserted and
    s 4.2(2) repealed with its Note (2025 (599), Sch 1). Inserted / replaced in place.
Every edit checks that the old passage occurs exactly once in the row before it changes it, and
writes provision_versions (v1 = stored text, v2 = new text or the retired text) +
provision_change_log, current_version_id, version_count, text_hash_current (sha256), and
text_hash (md5) only where it was already set.

    python scripts/dq88_refresh_2026_10_10.py            # dry run: rolled back
    python scripts/dq88_refresh_2026_10_10.py --apply
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
load_dotenv()

PP = "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0729"
SB = "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2022-0521"
PP_REF = ("Changed between the version in force on 4 Apr 2025 and the version in force on "
          "10 Oct 2026: s 2.27 Rep 2026 (286), Sch 1.9.")
SB_REF = ("Changed between the version in force on 5 Apr 2024 and the version in force on "
          "10 Oct 2026: 2025 (599), Sch 1.")
DETECTED = "point-in-time comparison of in-force text on legislation.nsw.gov.au (scripts/law_change_diff.py)"

RETIRE = [(13406, PP, PP_REF, "s 2.27 repealed."), (42785, PP, PP_REF, "s 2.27(1) repealed."),
          (42786, PP, PP_REF, "s 2.27(2) repealed."), (42787, PP, PP_REF, "s 2.27(2)(a)-(b) repealed."),
          (42783, PP, PP_REF, "s 2.27 heading, repealed."), (13534, PP, PP_REF, "summary of repealed s 2.27."),
          (13535, PP, PP_REF, "summary of repealed s 2.27.")]

S227 = re.compile(r"2\.27\s+Consultation with Secretary of Department of Industry.*?(?=2\.28\s)", re.S)
NEW_2A = ("(2A) The standards that apply to BASIX development the subject of an amended BASIX certificate are— "
          "(a) if the BASIX development is the subject of a development application or application for a complying "
          "development certificate that has been lodged—the standards that applied to the development when the "
          "original BASIX certificate was issued, or (b) otherwise—the standards specified in subsections (1) or (2). ")
def flex(phrase: str) -> str:
    """A literal phrase as a regex where any run of spaces matches any whitespace (stored text
    carries non-breaking spaces after clause numbers and PDF line breaks)."""
    return r"\s+".join(re.escape(w) for w in phrase.split())


OLD_42 = re.compile(flex("(2) Section 2.1(1) does not, until the end of 30 September 2024,") + r".*?"
                    + flex("30 September 2023.") + r"(?:\s*" + flex(
                        "Note— See also the Environmental Planning and Assessment (Development Certification and Fire "
                        "Safety) Regulation 2021 for savings and transitional provisions relating to BASIX certificates "
                        "for relevant BASIX development.") + r")?", re.S)
_2A_ANCHOR = re.compile(flex("accompanied by a BASIX certificate.") + r"\s+(?:" + flex(
    "State Environmental Planning Policy (Sustainable Buildings) 2022 - NSW Legislation") + r"\s+)?(?="
    + flex("(3) The standard specified in Schedule 2") + ")")


def insert_2a(t: str) -> tuple[str, int]:
    return _2A_ANCHOR.subn(lambda m: m.group(0) + NEW_2A, t)


EDITS = [(22361, PP, PP_REF, "s 2.27 repealed; passage replaced by '2.27 (Repealed)'.",
          lambda t: S227.subn("2.27 (Repealed)\n", t)),
         (6079, SB, SB_REF, "s 2.1(2A) inserted.", insert_2a),
         (43153, SB, SB_REF, "s 2.1(2A) inserted.", insert_2a),
         (6097, SB, SB_REF, "s 4.2(2) and its Note repealed.", lambda t: OLD_42.subn("(2) (Repealed)", t)),
         (43182, SB, SB_REF, "s 4.2(2) repealed.", lambda t: OLD_42.subn("(2) (Repealed)", t))]


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def version(cur, pid: int, text_after: str | None, src: str, ref: str, why: str, now: datetime) -> None:
    """Record v1 (as stored) and v2 (after), the change log row, and update the provision."""
    cur.execute("SELECT provision_text, created_at, text_hash FROM regulatory_provisions "
                "WHERE id = %s FOR UPDATE", (pid,))
    row = cur.fetchone()
    if row is None:
        sys.exit(f"{pid}: row vanished -- refusing")
    old, created, md5_set = row
    # created_at is TEXT and NULL on some rows; effective_from is NOT NULL.
    cur.execute("INSERT INTO provision_versions (provision_id, version_number, provision_text, effective_from, "
                "effective_to, change_type, change_summary, text_hash, extraction_date) "
                "VALUES (%s, 1, %s, COALESCE(%s::timestamptz, %s), %s, 'created', "
                "'Text as stored before the 2026-10-10 refresh from the law in force.', %s, "
                "COALESCE(%s::timestamptz, %s)) RETURNING id",
                (pid, old, created, now, now, sha(old), created, now))
    v1 = cur.fetchone()[0]
    kind = "deleted" if text_after is None else "modified"
    body = old if text_after is None else text_after
    cur.execute("INSERT INTO provision_versions (provision_id, version_number, provision_text, effective_from, "
                "change_type, change_summary, text_hash, extracted_from_document, extraction_date, extraction_method) "
                "VALUES (%s, 2, %s, %s, %s, %s, %s, %s, %s, 'legislation.nsw.gov.au in-force HTML, verbatim') "
                "RETURNING id", (pid, body, now, kind, why, sha(body), src, now))
    v2 = cur.fetchone()[0]
    cur.execute("INSERT INTO provision_change_log (provision_id, version_from, version_to, change_type, fields_changed, "
                "changed_at, triggered_by_document, amendment_reference, change_reason, detected_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (pid, v1, v2, kind, ["is_current"] if text_after is None else ["provision_text"], now, src, ref, why,
                 DETECTED))
    if text_after is None:
        cur.execute("UPDATE regulatory_provisions SET is_current = FALSE, current_version_id = %s, version_count = 2 "
                    "WHERE id = %s", (v2, pid))
    else:
        cur.execute("UPDATE regulatory_provisions SET provision_text = %s, current_version_id = %s, version_count = 2, "
                    "text_hash_current = %s, text_hash = %s WHERE id = %s",
                    (text_after, v2, sha(text_after),
                     hashlib.md5(text_after.encode("utf-8")).hexdigest() if md5_set else None, pid))


def main() -> int:
    apply = "--apply" in sys.argv
    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=60000")
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    for pid, src, ref, why in RETIRE:
        cur.execute("SELECT is_current, provision_text FROM regulatory_provisions WHERE id = %s", (pid,))
        row = cur.fetchone()
        if row is None or not row[0] or not any(k in row[1] for k in ("2.27", "oyster", "Department of Industry")):
            sys.exit(f"{pid}: not a current s 2.27 row -- refusing")
        version(cur, pid, None, src, ref, why, now)
    for pid, src, ref, why, fn in EDITS:
        cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = %s AND is_current", (pid,))
        row = cur.fetchone()
        if row is None:
            sys.exit(f"{pid}: not current -- refusing")
        new, n = fn(row[0])
        if n != 1:
            sys.exit(f"{pid}: expected the old passage exactly once, found {n} -- refusing")
        version(cur, pid, new, src, ref, why, now)
    cur.execute("SELECT count(*) FROM regulatory_provisions WHERE is_current AND provision_text ~ "
                "'Consultation with Secretary of Department of Industry|until the end of 30 September 2024'")
    left = cur.fetchone()[0]
    print(f"retired {len(RETIRE)}, edited {len(EDITS)}; current rows still holding repealed text: {left}")
    if left:
        conn.rollback()
        sys.exit("repealed text still held somewhere -- rolled back")
    (conn.commit if apply else conn.rollback)()
    print("COMMITTED" if apply else "ROLLED BACK (dry run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
