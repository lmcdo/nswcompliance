#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no existing surface repairs
# provision_text. The neighbours each do something else: repair_shadow_reports
# .py regenerates satellite report ROWS through the pipeline; cleanup_bad_
# setbacks.py and delete_bad_leichhardt_rows.py DELETE rows from other tables;
# fix_topics_step1_garbage_cleanup.py rewrites v2_topic, not the text.
# dq_probe_live.py MEASURES this exact set and is the source of the predicate
# below, but is read-only by design and must stay so -- a check that can write
# is not a check.
"""DQ-76: strip PDF-extraction residue from served provision text.

WHAT THIS IS FOR
----------------
99 served provisions carry TeX math-mode residue emitted by pdfplumber instead
of the rendered glyph. They are not cosmetic. Among them:

    "at least 12 00 { m } 2 of the 60 00 m 2 set aside for employment"
    "4 {} 000 m 2 { - } 15 m"
    "must not be higher than 3.6 { m } above ground level"
    "Omit 666 m { - } 18 m 3 from clause 3C.28(4)"

A reader is shown markup where a regulated value belongs.

THE ONE RULE THIS OBEYS
-----------------------
**No digit may change.** The repair strips TeX WRAPPERS and keeps their
contents; it never joins split digits, never inserts a separator, never
"corrects" a number. So ``12 00 { m } 2`` becomes ``12 00 m 2`` -- markup gone,
spacing untouched -- and NOT ``1,200 m2``, however obvious that reading looks.

Turning ``12 00`` into ``1200`` is a judgement about what the source PDF says.
It may well be right, and it is still a different job needing the source
document, not a regex. Doing it here would be inventing a regulated number,
which is the defect this row exists to remove.

The invariant is machine-checked per row: the ordered sequence of digits in the
repaired text must be IDENTICAL to the original. Any row that fails is skipped
and reported, never written.

SAFETY
------
- Dry run by default; ``--apply`` required to write.
- Full JSON backup of every affected row BEFORE any write, and it refuses to
  write if the backup cannot be saved.
- Per-row UPDATE guarded on the text read during planning, so a concurrent
  write is never clobbered.
- One transaction, rolled back if the affected row count disagrees.
- 30s statement timeout.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

REPO = Path(__file__).resolve().parents[1]
BACKUP_DIR = REPO / ".claude" / "backups"

#: Must stay identical to PROBES['DQ-76'] in dq_probe_live.py. If these drift,
#: the repair stops covering what the metric counts and the row can never close
#: -- the first pass did exactly that: a brace class of [-A-Za-z0-9] left 103
#: rows carrying '{}', '{ : }' and '{ t h }' behind while the metric read 0.
PREDICATE = (
    r"provision_text ~ '\\[A-Za-z]{2,}' "
    r"OR (provision_text LIKE '%%$%%' AND provision_text !~ '\$[0-9]') "
    r"OR provision_text LIKE '%%{%%' OR provision_text LIKE '%%}%%'"
)

# Order matters: unwrap inner groups before removing the commands that wrap
# them, or the contents are lost with the wrapper.
_RULES: list[tuple[re.Pattern, str]] = [
    # \( ... \) and \[ ... \] math delimiters -> keep the contents
    (re.compile(r"\\[\(\[]\s*|\s*\\[\)\]]"), " "),
    # ^{2} / _{A10} superscripts and subscripts -> keep the contents
    (re.compile(r"[\^_]\s*\{\s*([^{}]*?)\s*\}"), r"\1"),
    # \command { contents } -> contents   (repeat for nesting)
    (re.compile(r"\\[A-Za-z]+\s*\{\s*([^{}]*?)\s*\}"), r"\1"),
    # bare \command with no braces -> drop it
    (re.compile(r"\\[A-Za-z]+"), " "),
    # { x } / { - } / {} leftover brace groups -> contents
    (re.compile(r"\{\s*([^{}]*?)\s*\}"), r"\1"),
    # a lone backslash left behind
    (re.compile(r"(?<![A-Za-z])\\(?![A-Za-z])"), " "),
    # math-delimiter $ that is not money
    (re.compile(r"\$(?![0-9])"), " "),
    # TeX tilde spacing
    (re.compile(r"(?<=[0-9A-Za-z])\s*~\s*(?=[0-9A-Za-z])"), " "),
    # tidy the whitespace the above leaves, without touching newlines
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r"[ \t]+([,.;:)])"), r"\1"),
]


def repair(text: str) -> str:
    out = text
    for _ in range(4):                    # nested groups need a few passes
        before = out
        for pat, sub in _RULES:
            out = pat.sub(sub, out)
        if out == before:
            break
    return "\n".join(line.rstrip() for line in out.split("\n")).strip()


def digits(text: str) -> str:
    """The ordered digit sequence -- the thing that must never change."""
    return "".join(ch for ch in text if ch.isdigit())


# --------------------------------------------------------------------------
# pass 2: DQ-77 -- a unit split across a space
# --------------------------------------------------------------------------
#
# '900 m m' is 900mm, '7 p m' is 7pm, '20 t h' is 20th. The VALUE is not wrong;
# the text a planner quotes is not what the instrument says.
#
# This pass is safer than the TeX one and its invariant says so: it only ever
# deletes a space between two characters, so the ordered sequence of
# NON-WHITESPACE characters must come out identical. Nothing added, dropped or
# reordered. A row failing that check is skipped, not written.
#
# The space BEFORE the unit is KEPT -- '900 mm', not '900mm'. Closing that gap
# is a typographic preference and this pass has no business holding one; the
# minimal transform is also what makes the invariant provable.
_UNIT_RULES: list[tuple[re.Pattern, str]] = [
    # 900 m m -> 900 mm
    (re.compile(r"(?<=[0-9])(\s+)m\s+m\b"), r"\1mm"),
    # 900 m 2 -> 900 m2   (metres split from a squared/cubed exponent)
    (re.compile(r"(?<=[0-9])(\s+)m\s+([23])\b"), r"\1m\2"),
    # 7 p m -> 7 pm, 8 a m -> 8 am
    (re.compile(r"(?<=[0-9])(\s+)([ap])\s+m\b"), r"\1\2m"),
    # 20 t h -> 20th. The one place a space next to a digit is removed, because
    # "th" is an ordinal suffix rather than a unit.
    (re.compile(r"(?<=[0-9])\s+t\s+h\b"), "th"),
]


def repair_units(text: str) -> str:
    out = text
    for _ in range(3):
        before = out
        for pat, sub in _UNIT_RULES:
            out = pat.sub(sub, out)
        if out == before:
            break
    return out


def nonspace(text: str) -> str:
    """Every non-whitespace character, in order -- the unit pass's invariant.

    Stronger than the digit check: it proves no character was added, dropped or
    reordered, only spaces removed.
    """
    return "".join(ch for ch in text if not ch.isspace())


def _connect():
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO / ".env")
    except ImportError:
        pass
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        raise SystemExit(2)
    conn = psycopg2.connect(url)
    conn.cursor().execute("SET statement_timeout = '30000'")
    return conn


#: Must stay identical to PROBES['DQ-77'] in dq_probe_live.py.
UNIT_PREDICATE = (
    r"provision_text ~ '[0-9]\s+m\s+m\M' "
    r"OR provision_text ~ '[0-9]\s+m\s+[23]\M' "
    r"OR provision_text ~ '[0-9]\s+[ap]\s+m\M' "
    r"OR provision_text ~ '[0-9]\s+t\s+h\M'"
)

#: name -> (row id, predicate, transform, invariant, what the invariant means)
PASSES = {
    "tex": ("DQ-76", PREDICATE, repair, digits,
            "the ordered digit sequence"),
    "units": ("DQ-77", UNIT_PREDICATE, repair_units, nonspace,
              "every non-whitespace character, in order"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="which", choices=sorted(PASSES),
                    default="tex",
                    help="tex = DQ-76 markup residue; units = DQ-77 split units")
    ap.add_argument("--apply", action="store_true",
                    help="write the repairs; without it this is a dry run")
    ap.add_argument("--show", type=int, default=12,
                    help="how many before/after pairs to print")
    args = ap.parse_args()

    dq_id, predicate, transform, invariant, invariant_name = PASSES[args.which]

    conn = _connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        f"""SELECT id, ref_number, source_council, provision_text
              FROM regulatory_provisions
             WHERE is_current AND v2_is_actionable AND ({predicate})
             ORDER BY id"""
    )
    rows = cur.fetchall()
    print(f"pass '{args.which}' ({dq_id}) - matching served rows: {len(rows)}")
    print(f"invariant: {invariant_name} must be identical before and after\n")

    planned, skipped, unchanged = [], [], []
    for r in rows:
        original = r["provision_text"]
        fixed = transform(original)
        if fixed == original:
            unchanged.append(r)
            continue
        if invariant(fixed) != invariant(original):
            skipped.append((r, fixed))
            continue
        planned.append((r, fixed))

    print(f"  repairable (invariant holds)          : {len(planned)}")
    print(f"  SKIPPED (invariant would break)       : {len(skipped)}")
    print(f"  matched but no change produced        : {len(unchanged)}")

    for r, fixed in skipped:
        print(f"\n  SKIPPED id={r['id']} - {invariant_name} differs, not written")
        print(f"    before: {invariant(r['provision_text'])[:60]}")
        print(f"    after : {invariant(fixed)[:60]}")

    if unchanged:
        print("\n  rows the predicate matches but the repair leaves alone "
              "(the predicate may be broader than the repair):")
        for r in unchanged[:5]:
            flat = re.sub(r"\s+", " ", r["provision_text"])[:110]
            print(f"    id={r['id']}: {flat}")

    print(f"\n--- before/after, first {args.show} ---")
    for r, fixed in planned[:args.show]:
        b = re.sub(r"\s+", " ", r["provision_text"])[:150]
        a = re.sub(r"\s+", " ", fixed)[:150]
        print(f"\n  id={r['id']} ({r['source_council'] or 'statewide'})")
        print(f"    before: {b}")
        print(f"    after : {a}")

    if not args.apply:
        print(f"\nDRY RUN - nothing written. {len(planned)} rows would change.")
        return 0

    if not planned:
        print("\nNothing to write.")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    backup = BACKUP_DIR / f"tex_residue_repair_{stamp}.json"
    try:
        backup.write_text(json.dumps(
            {"captured_at": stamp,
             "predicate": PREDICATE,
             "rows": [{"id": r["id"], "ref_number": r["ref_number"],
                       "before": r["provision_text"], "after": f}
                      for r, f in planned]},
            indent=1, default=str), encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: backup could not be written ({exc}); refusing to write.",
              file=sys.stderr)
        return 2
    print(f"\nbackup: {backup} ({backup.stat().st_size / 1000:.0f} KB)")

    write = conn.cursor()
    try:
        n = 0
        for r, fixed in planned:
            # Guarded on the text read during planning: if another writer has
            # touched the row since, this updates nothing rather than clobber.
            write.execute(
                "UPDATE regulatory_provisions SET provision_text = %s "
                "WHERE id = %s AND provision_text = %s",
                (fixed, r["id"], r["provision_text"]),
            )
            n += write.rowcount
        if n != len(planned):
            conn.rollback()
            print(f"ERROR: updated {n} of {len(planned)} - a row changed under "
                  f"us. Rolled back, nothing written.", file=sys.stderr)
            return 2
        conn.commit()
        print(f"repaired {n} rows")
    except Exception as exc:                                    # noqa: BLE001
        conn.rollback()
        print(f"ERROR: rolled back: {exc}", file=sys.stderr)
        return 2

    # Re-measure from the database rather than reporting arithmetic, so the
    # number quoted afterwards is the one the probe will report.
    cur.execute(
        f"""SELECT count(*) AS n FROM regulatory_provisions
             WHERE is_current AND v2_is_actionable AND ({predicate})"""
    )
    print(f"{dq_id} after repair: {cur.fetchone()['n']}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
