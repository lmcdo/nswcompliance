#!/usr/bin/env python3
# prior-art-checked: neighbours opened, not guessed from their names.
#   derive_precinct_keys.py    backfills a different key (v2_precinct_id) from
#                              different source text. Same CLASS of job and the
#                              model for this script's dry-run + backup shape.
#   dcp_commit_approved.py     the WRITER for newly reviewed provisions. It has no
#                              path to repair rows already committed, and it is
#                              patched in the same change so it stops re-creating
#                              this defect (see WHY A BACKFILL ALONE IS NOT ENOUGH).
#   enrichment/pipeline.py     fills v2_* fields; never touches section_header.
# DB sweep: no column already holds a per-row section code. v2_dcp_part is
# 'unknown' for all of leichhardt and marrickville, prose in ashfield and slugs in
# ku-ring-gai, so it is not a usable key. Frontend sweep (app/**, app/internal,
# components/, hooks/): section_header is the field provisions are grouped and
# displayed by, which is why it is the field repaired.
"""Put the section code back on rows that lost it, from ref_number. No model calls.

WHAT THIS FIXES, AND WHAT IT DOES NOT
-------------------------------------
Measured 2026-09-12 over 12,124 live DCP rows: 59% sit under too few section
labels to be addressable. That is TWO defects, and only one of them is repairable
from stored data:

  NO LABEL (3,501 rows)    section_header carries no code -- "Residential parking
                           generation rates" -- while ref_number holds E1_4_2.
                           The code was never lost, only never copied across.
                           **THIS SCRIPT FIXES THESE.** 2,330 rows across 10
                           councils, restoring 2,260 addressable sections:
                           city_of_sydney 666, parramatta 634, woollahra 530,
                           ku_ring_gai 210, penrith 78, blacktown 68,
                           campbelltown 47, northern_beaches 45,
                           georges_river 26, cumberland 24.

  COLLAPSED (4,445 rows)   the extractor stamped a whole chapter with one parent
                           code. ref_number carries the SAME collapsed code
                           (2_25_C11 on a row belonging to 2.25.3.4), so there is
                           nothing to recover. **Not fixable here** -- only a
                           re-extraction, which costs API credit. marrickville is
                           1,181 of these and recovers ZERO rows from this script.

WHY A BACKFILL ALONE IS NOT ENOUGH
----------------------------------
dcp_commit_approved recomputes section_header on EVERY commit, from the first
line of the reviewed provision text. So repairing these rows and stopping there
would see the repair wiped the next time each chapter is committed -- precisely
the failure recorded in project-precinct-keys-nulled-on-every-commit-2026-09,
where a derived field was silently reset by the very pipeline that should have
preserved it.

So the same change gives `_section_header_from_text` a ref_number fallback. This
script repairs the past; that fallback stops the defect being re-created. Running
this without that patch buys a repair with a known expiry date.

SAFETY
------
* Dry run by default. --apply is required to write.
* section_header is part of uq_provisions_current_identity (document_id,
  ref_number, section_header, md5(provision_text)) WHERE is_current, so a change
  alters row identity. Every planned write is checked for a collision against
  that key BEFORE anything is written, and a colliding row is skipped and
  reported rather than allowed to abort the batch.
* --apply takes a complete backup of every affected row into its own timestamped
  table first, verifies the row count matches, and refuses to write otherwise.
* Single production database. Changes are immediately live.

    python scripts/dcp_restore_section_codes.py                 # dry run, all
    python scripts/dcp_restore_section_codes.py --council woollahra
    python scripts/dcp_restore_section_codes.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from scripts.dcp_section_code import repaired_header
except ImportError:
    from dcp_section_code import repaired_header


def _connect():
    try:
        from scripts.check_council_completeness import _load_env as shared
    except ImportError:
        from check_council_completeness import _load_env as shared
    shared()
    import psycopg2
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise SystemExit(
            "FATAL: no DATABASE_URL / SUPABASE_DB_URL. This script repairs live "
            "provisions; without a database there is nothing to repair.")
    conn = psycopg2.connect(url, connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SET statement_timeout='120s'")
    return conn, cur


def identity(document_id, ref_number, section_header, provision_text) -> tuple:
    """The uq_provisions_current_identity key, as Postgres computes it."""
    return (document_id or "", ref_number or "", section_header or "",
            hashlib.md5((provision_text or "").encode("utf-8")).hexdigest())


def _say(text: str) -> None:
    """print(), but never die on a console that cannot encode the corpus.

    DCP text carries box-drawing and private-use glyphs from the source PDFs
    (U+25A0, U+F07D). On a cp1252 terminal a bare print() raises
    UnicodeEncodeError mid-report -- which killed a dry run after it had already
    done the work. A diagnostic that crashes while describing a defect is its own
    defect.
    """
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(enc, "replace").decode(enc, "replace"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--apply", action="store_true",
                    help="write. Without this the script is a dry run.")
    ap.add_argument("--council", help="restrict to one council")
    ap.add_argument("--show", type=int, default=4, help="sample rows per council")
    args = ap.parse_args(argv)

    conn, cur = _connect()
    where = ["is_current", "source_council IS NOT NULL"]
    params: list = []
    if args.council:
        where.append("source_council = %s")
        params.append(args.council)
    cur.execute(
        "SELECT id, source_council, section_header, ref_number, document_id, "
        "       provision_text "
        "FROM regulatory_provisions WHERE " + " AND ".join(where), params)
    rows = cur.fetchall()

    # Every current identity, so a planned change that would collide is caught
    # before the write rather than as a failed transaction.
    cur.execute(
        "SELECT document_id, ref_number, section_header, provision_text "
        "FROM regulatory_provisions WHERE is_current")
    taken = {identity(*r) for r in cur.fetchall()}

    updates, collisions = [], []
    tally = defaultdict(lambda: defaultdict(int))
    samples = defaultdict(list)
    for rid, council, head, ref, doc, text in rows:
        new_head = repaired_header(head, ref, doc)
        if new_head is None:
            tally[council]["unchanged"] += 1
            continue
        new_id = identity(doc, ref, new_head, text)
        if new_id in taken:
            tally[council]["collision"] += 1
            collisions.append((council, rid, str(head)[:40], new_head[:40]))
            continue
        taken.add(new_id)
        updates.append((rid, new_head))
        tally[council]["repair"] += 1
        if len(samples[council]) < args.show:
            samples[council].append((str(head or "(blank)")[:44], new_head[:50]))

    print("  council".ljust(24) + "REPAIR".rjust(8) + "unchanged".rjust(12) +
          "collision".rjust(11))
    tot = defaultdict(int)
    for council in sorted(tally, key=lambda c: -tally[c]["repair"]):
        t = tally[council]
        for k, v in t.items():
            tot[k] += v
        if not t["repair"]:
            continue
        print("  " + str(council).ljust(22) + str(t["repair"]).rjust(8) +
              str(t["unchanged"]).rjust(12) + str(t["collision"]).rjust(11))
    print("  " + "-" * 55)
    print("  " + "TOTAL".ljust(22) + str(tot["repair"]).rjust(8) +
          str(tot["unchanged"]).rjust(12) + str(tot["collision"]).rjust(11))

    print()
    print("  what changes:")
    for council in sorted(samples):
        print("   " + council)
        for old, new in samples[council]:
            _say("      " + old.ljust(46) + " ->  " + new)
    if collisions:
        print()
        print("  SKIPPED -- would collide with an existing row identity:")
        for council, rid, old, new in collisions[:8]:
            _say("   " + council.ljust(20) + "id=" + str(rid).ljust(9) +
                 old + "  ->  " + new)

    if not args.apply:
        print()
        print("DRY RUN -- nothing written. " + str(len(updates)) +
              " rows would change. Re-run with --apply to write.")
        print("NOTE: without the _section_header_from_text fallback in "
              "dcp_commit_approved, this repair is undone at the next commit "
              "of each chapter.")
        conn.close()
        return 0

    if not updates:
        print("nothing to do")
        conn.close()
        return 0

    backup = ("regulatory_provisions_section_code_backup_" +
              datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    ids = [r[0] for r in updates]
    cur.execute(
        "CREATE TABLE " + backup + " AS SELECT id, section_header, ref_number, "
        "document_id, source_council, source_chapter_key "
        "FROM regulatory_provisions WHERE id = ANY(%s)", (ids,))
    cur.execute("SELECT count(*) FROM " + backup)
    n_backed = cur.fetchone()[0]
    if n_backed != len(ids):
        conn.rollback()
        conn.close()
        raise SystemExit(
            "FATAL: backup holds " + str(n_backed) + " of " + str(len(ids)) +
            " rows. Nothing was written.")
    cur.executemany(
        "UPDATE regulatory_provisions SET section_header = %s "
        "WHERE id = %s AND is_current",
        [(new, rid) for rid, new in updates])
    conn.commit()
    print()
    print("WROTE " + str(len(updates)) + " rows.  backup: " + backup)
    # The UNDO carries the same currency filter as the UPDATE it reverses.
    # Without it a later run of this hint could rewrite a row that stopped
    # being current after the change it is meant to undo.
    print("UNDO:  UPDATE regulatory_provisions p SET section_header = b.section_header")
    print("       FROM " + backup + " b WHERE p.id = b.id AND p.is_current;")
    conn.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print("FATAL: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
