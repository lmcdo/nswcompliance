#!/usr/bin/env python3
# prior-art-checked: four sweeps 2026-11-07 on feat/lmr-clean-law (origin/main eaa9964d). (1) DB content:
# no law_facts table (to_regclass is NULL on the live database); instrument_registry holds one row per
# instrument (key sepp_housing_2021, version 9 October 2026, last checked 2026-10-15), not per figure;
# housing_sepp_standards (67 rows) is hand-typed SQL with no version stamp or text hash. (2) Frontend:
# nothing reads law figures from a table with clause+page+quote. (3) Python: apply_state_law_proof.py and
# import_cb_centre_boundaries.py give the dry-run/--apply/backup pattern copied here; none loads law facts.
# (4) Plans: ce-lmr-tod-clean-state-law-PLAN-2026-11-07.md sections 2c, 2h; owner said yes 2026-11-07.
"""Load the low-and-mid-rise / TOD law facts into `law_facts`, and check the database against the JSON.

The JSON (`data/law/housing_sepp_lmr_facts.json`) is built from the saved law text and proven against it
by `scripts/extract_lmr_law_facts.py --check`. This script puts the same facts in the database, one row
per fact with clause, PDF page, the sentence, the law version date and the text hash, so the page reads
rows that can be defended and the ledger can prove the database still equals the file.

Modes:
  (default, dry run)  read-only. Prints the database name, the rows already there and what would change.
  --apply             writes. Refuses unless the JSON still matches the saved law text and the table exists
                      (migration 123). Backs up the existing rows first. One transaction; commits only if the
                      database then equals the JSON, otherwise rolls back.
  --check             read-only. Exit 0 = database equals JSON; 1 = differs or not loaded; 2 = unknown
                      (no database reachable). UNKNOWN is never reported as clean.

A newer law version is a NEW set of rows: the old rows stay (is_current = false) as history.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_lmr_law_facts as law  # noqa: E402

REPO_ROOT = law.REPO_ROOT
BACKUP_DIR = REPO_ROOT / "data" / "db_rollback_backups"
INSTRUMENT_KEY = "sepp_housing_2021"  # the key instrument_registry already uses for this instrument

COLUMNS = (
    "instrument_key", "fact_key", "law_version_date", "clause", "pdf_page", "pdf_page_to",
    "value", "value_number", "unit", "measured", "quote", "extra", "text_file", "text_sha256",
)
_KNOWN = {"value", "clause", "page", "pages_to", "quote", "unit", "measured"}


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def build_rows(doc: dict) -> list[dict]:
    """One row per fact, in the order the JSON lists them."""
    rows = []
    for key, fact in doc["facts"].items():
        if key == "s164":
            value = {"paragraphs": fact["paragraphs"], "live_count": fact["live_count"]}
            quote = f"{fact['live_count']} live paragraphs of s164(1); the words of each are in value"
            extra = {}
        else:
            value, quote = fact["value"], fact["quote"]
            extra = {k: v for k, v in fact.items() if k not in _KNOWN}
        rows.append(
            {
                "instrument_key": INSTRUMENT_KEY,
                "fact_key": key,
                "law_version_date": doc["law_version_date"],
                "clause": fact["clause"],
                "pdf_page": fact["page"],
                "pdf_page_to": fact.get("pages_to"),
                "value": value,
                "value_number": _number(value),
                "unit": fact.get("unit"),
                "measured": fact.get("measured"),
                "quote": quote,
                "extra": extra,
                "text_file": doc["text_file"],
                "text_sha256": doc["text_sha256"],
            }
        )
    return rows


def _canon(row: dict) -> tuple:
    """Comparable form: JSON canonical text for structures, float for numbers, date as ISO text."""
    out = []
    for c in COLUMNS:
        v = row.get(c)
        if c == "law_version_date" and v is not None:
            v = str(v)
        elif c == "value_number" and v is not None:
            v = float(v)
        elif c in ("value", "extra"):
            v = json.dumps(v, sort_keys=True, ensure_ascii=False)
        out.append(v)
    return tuple(out)


def diff_rows(json_rows: list[dict], db_rows: list[dict]) -> list[str]:
    """Names of facts that differ between the JSON and the database's CURRENT rows. Empty = identical."""
    want = {r["fact_key"]: r for r in json_rows}
    have = {r["fact_key"]: r for r in db_rows}
    problems = [f"missing in database: {k}" for k in want if k not in have]
    problems += [f"not in the JSON: {k}" for k in have if k not in want]
    for k in want.keys() & have.keys():
        if _canon(want[k]) != _canon(have[k]):
            cols = [c for c, a, b in zip(COLUMNS, _canon(want[k]), _canon(have[k])) if a != b]
            problems.append(f"differs: {k} ({', '.join(cols)})")
    return sorted(problems)


def plan_changes(json_rows: list[dict], db_all: list[dict], correct: frozenset = frozenset()) -> dict:
    """What --apply would do. `db_all` = every row in law_facts (current and history), with is_current.

    `correct` names facts whose wording was wrong under the SAME law version (a bug in the extractor, not a new law). The table allows
    one row per fact per law version, so a correction updates that row in place; the old row is saved to the backup file first.
    Without the name, the same-version difference stays a CONFLICT.
    """
    insert, supersede, unchanged, conflicts, update = [], [], 0, [], []
    current = {r["fact_key"]: r for r in db_all if r.get("is_current")}
    for row in json_rows:
        cur = current.get(row["fact_key"])
        if cur is None:
            insert.append(row)
        elif str(cur["law_version_date"]) == str(row["law_version_date"]):
            if _canon(cur) == _canon(row):
                unchanged += 1
            elif row["fact_key"] in correct:
                update.append(row)
            else:
                conflicts.append(f"{row['fact_key']}: same law version {row['law_version_date']} but different content "
                                 f"(a wording fix under the same version needs --correct {row['fact_key']})")
        elif str(cur["law_version_date"]) < str(row["law_version_date"]):
            supersede.append(row["fact_key"])
            insert.append(row)
        else:
            conflicts.append(f"{row['fact_key']}: database holds a NEWER law version {cur['law_version_date']}")
    unknown = sorted(set(correct) - {r["fact_key"] for r in update})
    for k in unknown:   # naming a fact that is not a same-version difference must never silently do nothing
        conflicts.append(f"--correct {k}: that fact is not a same-version difference (nothing to correct)")
    return {"insert": insert, "supersede": supersede, "unchanged": unchanged, "conflicts": conflicts, "update": update}


# ---- database side (kept thin; the logic above is what the tests pin) ------------------------------


def _fetch(cur, where: str = "") -> list[dict]:
    cur.execute(f"SELECT {', '.join(COLUMNS)}, is_current FROM law_facts {where} ORDER BY fact_key, law_version_date")
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def _table_exists(cur) -> bool:
    cur.execute("SELECT to_regclass('public.law_facts') IS NOT NULL")
    return bool(cur.fetchone()[0])


def _doc() -> dict:
    stored = json.loads(law.FACTS_PATH.read_text(encoding="utf-8"))
    problems = law.differences(stored, law.build(law.DEFAULT_TEXT))
    if problems:
        raise SystemExit(f"REFUSED: the JSON no longer matches the saved law text ({', '.join(problems[:5])}). "
                         "Run scripts/extract_lmr_law_facts.py --check first.")
    return stored


def check() -> int:
    import dq_db

    try:
        rows = build_rows(_doc())
        with dq_db.session() as conn:
            cur = conn.cursor()
            if not _table_exists(cur):
                print("NOT LOADED: table law_facts does not exist (migration 123 not applied)")
                return 1
            problems = diff_rows(rows, _fetch(cur, "WHERE is_current"))
    except RuntimeError as exc:
        print(f"UNKNOWN: {exc}  UNKNOWN is not CLEAN.")
        return 2
    except Exception as exc:  # an unreachable database must never read as clean
        print(f"UNKNOWN: {type(exc).__name__}: {str(exc)[:160]}  UNKNOWN is not CLEAN.")
        return 2
    for p in problems:
        print(" ", p)
    print(f"law_facts vs JSON: {len(problems)} difference(s) across {len(rows)} fact(s)")
    return 1 if problems else 0


def run(apply: bool, correct: frozenset = frozenset()) -> int:
    import dq_db

    rows = build_rows(_doc())
    conn = dq_db.connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT current_database()")
        print("database:", cur.fetchone()[0])
        if not _table_exists(cur):
            print("law_facts does not exist: apply migration 123 first (nothing to load into).")
            return 1
        existing = _fetch(cur)
        plan = plan_changes(rows, existing, correct)
        print(f"existing rows: {len(existing)} | to insert: {len(plan['insert'])} | to supersede: "
              f"{len(plan['supersede'])} | to correct in place: {len(plan['update'])} | unchanged: {plan['unchanged']} | JSON facts: {len(rows)}")
        for row in plan["update"]:
            old = next(r for r in existing if r["fact_key"] == row["fact_key"] and r.get("is_current"))
            print(f"  will correct {row['fact_key']}: stored value {len(json.dumps(old['value']))} chars -> {len(json.dumps(row['value']))} chars")
        for c in plan["conflicts"]:
            print("CONFLICT:", c)
        if plan["conflicts"]:
            return 1
        if not apply:
            print("dry run: nothing written. Re-run with --apply to write.")
            return 0
        if not plan["insert"] and not plan["update"]:
            print("nothing to do.")
            return 0

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
        backup = BACKUP_DIR / f"law_facts_pre_{stamp}.json"
        backup.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")
        print(f"backup: {backup.relative_to(REPO_ROOT)} ({len(existing)} rows)")

        from psycopg2.extras import Json

        conn.rollback()
        conn.set_session(readonly=False)
        cur = conn.cursor()
        cur.execute("SET LOCAL statement_timeout = 30000")
        for key in plan["supersede"]:
            cur.execute("UPDATE law_facts SET is_current = false WHERE instrument_key = %s AND fact_key = %s AND is_current",
                        (INSTRUMENT_KEY, key))
        placeholders = ", ".join(["%s"] * len(COLUMNS))
        for row in plan["update"]:   # same law version, corrected wording: the old row is in the backup file above
            sets = ", ".join(f"{c} = %s" for c in COLUMNS if c not in ("instrument_key", "fact_key", "law_version_date"))
            vals = [Json(row[c]) if c in ("value", "extra") else row[c] for c in COLUMNS if c not in ("instrument_key", "fact_key", "law_version_date")]
            cur.execute(f"UPDATE law_facts SET {sets}, loaded_at = now() WHERE instrument_key = %s AND fact_key = %s AND is_current",
                        vals + [INSTRUMENT_KEY, row["fact_key"]])
            if cur.rowcount != 1:
                conn.rollback()
                print(f"ROLLED BACK: expected to correct 1 row for {row['fact_key']}, matched {cur.rowcount}")
                return 1
        for row in plan["insert"]:
            vals = [Json(row[c]) if c in ("value", "extra") else row[c] for c in COLUMNS]
            cur.execute(f"INSERT INTO law_facts ({', '.join(COLUMNS)}) VALUES ({placeholders})", vals)
        after = diff_rows(rows, _fetch(cur, "WHERE is_current"))
        if after:
            conn.rollback()
            print("ROLLED BACK: the database would not equal the JSON:", after[:5])
            return 1
        conn.commit()
        print(f"committed: {len(plan['insert'])} inserted, {len(plan['update'])} corrected in place. law_facts now equals the JSON.")
        return 0
    finally:
        conn.close()


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the rows (default is a dry run)")
    ap.add_argument("--check", action="store_true", help="read-only: does the database equal the JSON? exit 0/1/2")
    ap.add_argument("--correct", action="append", default=[], metavar="FACT_KEY",
                    help="a fact whose wording was wrong under the SAME law version: update that row in place (old row saved to the backup)")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    return run(args.apply, frozenset(args.correct))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
