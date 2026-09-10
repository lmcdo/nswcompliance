#!/usr/bin/env python3
# prior-art-checked: no existing per-council field-count comparison. Neighbours
# opened, not guessed from their names: validate_dcp_health.py is per-council and
# post-commit but every check is an ABSOLUTE invariant (gap=0, duplicates=0), so
# none can see a field that legitimately sits at 36% and falls to 6%;
# dcp_quality_report.py has no persistence to compare against;
# test_dcp_pipeline_completeness.py asserts STAGES exist, not data.
# audit_precinct_keying_coverage.py and validate_zone_code_validity.py detect
# their own single case and are CALLED below rather than copied. DB sweep: no
# snapshot-shaped table (only lep_zone_coverage / spatial_overlays_coverage,
# unrelated). Frontend sweep (app/**, components/, hooks/): display surfaces only.
"""Did this council's provisions lose a field since last time?

WHY THIS EXISTS
---------------
Full history in migrations/068_council_field_snapshot.sql. In short: #1079, #1080
and #1081 were one defect in three fields -- a council update silently dropping
what it carried -- and the two that were caught were the only two with a check
watching them.

So this does not ask "is this field correct"; other scripts do that, for fields
somebody already thought of. It asks "does this council still carry what it
carried last time", which is answerable for a field nobody has thought of yet.

WHAT IT COMPARES
----------------
Per council, over the SERVED set (is_current AND v2_is_actionable): the row count,
and how many of those rows populate each watched field. Both are written to
dcp_council_field_snapshot, and each recording is compared against that council's
previous one.

THREE STATES, NEVER TWO
-----------------------
Every (council, field) is OK (measured both times, no material fall), DROP (the
finding), or NO_BASELINE (not measured before -- first run, new council, newly
watched field). NO_BASELINE is never folded into OK: a check that reports "fine"
when it has nothing to compare against is how DQ-30 stayed marked Fixed on the
strength of a self-comparison that could not fail.

WHAT IT DOES NOT MEASURE, AND WHY
---------------------------------
Zone codes are NOT watched as a fill count. Measured 2026-09-11:
v2_applicable_zones is populated on 100.0% of served rows for all 18 councils --
the #1081 write guard falls back to ['ALL'] rather than leaving it empty -- so a
fill count there cannot move, and would be a check that cannot fail. Zone health
comes from calling scripts/validate_zone_code_validity.py, which can.

Exit codes (matching r2_monitor / dcp_watchdog / dcp_extract_changed, which
run_monitors.py already treats this way):
    0 = nothing went backwards
    2 = findings -- the run itself succeeded; CRITICAL/STANDARD also alert
    1 = the check itself broke (unhandled exception, no DB)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

from dotenv import load_dotenv  # noqa: E402


def _load_env() -> None:
    """Find .env, including from inside a git worktree, which has none of its own.

    Resolved inline rather than by importing scripts/dq_db.main_checkout(): dq_db
    is NOT copied into Dockerfile.monitors, so importing it would trade a local
    inconvenience for a production ImportError. On Railway the env vars are
    already set, so this whole function returns early.
    """
    load_dotenv(ROOT / ".env")
    if os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"):
        return
    try:
        # Imported HERE, not at module scope, for the same reason dq_db is not
        # imported at all: qa_report_path is a development helper and is not
        # COPYed into Dockerfile.monitors. This branch is unreachable in the
        # container -- DATABASE_URL is set there, so the function has already
        # returned -- so a local-only import cannot become a production
        # ImportError. It is wrapped regardless.
        sys.path.insert(0, str(HERE))
        from qa_report_path import git_env

        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=10,
            # cwd alone does NOT scope git: a hook exports GIT_DIR/GIT_INDEX_FILE
            # and those override it, so this would confidently answer about the
            # hook's repository instead. git_env() strips them.
            env=git_env(),
        ).stdout.strip()
        if common:
            load_dotenv(Path(common).parent / ".env")
    except (OSError, ImportError, subprocess.SubprocessError):
        pass


_load_env()

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

#: source_council is NULL for statewide instruments (7,268 served rows, 2026-09-11);
#: one losing its citations is the same defect, so NULL is recorded under this
#: sentinel. Verified the same day: ZERO served rows carry an empty-string
#: source_council, so it cannot collide with a real slug.
STATEWIDE = "(statewide)"

#: field name -> the SQL predicate meaning "this row populates the field". These
#: are OUR OWN identifiers, interpolated into the SELECT because a column name
#: cannot be a bind parameter; --council, the one value from outside, is bound.
#: Adding a field here costs nothing because `counts` is JSONB, and that
#: cheapness is the point -- a field expensive to start watching does not get
#: watched. v2_applicable_dev_types is here because DQ-30 was a tagger defect.
WATCHED_FIELDS: dict[str, str] = {
    "v2_precinct_id": "v2_precinct_id IS NOT NULL",
    "ref_number": "ref_number IS NOT NULL AND ref_number <> ''",
    "pdf_page": "pdf_page IS NOT NULL",
    "v2_topic": "v2_topic IS NOT NULL AND v2_topic <> ''",
    "v2_provision_type": "v2_provision_type IS NOT NULL AND v2_provision_type <> ''",
    "v2_applicable_dev_types": (
        "v2_applicable_dev_types IS NOT NULL "
        "AND array_length(v2_applicable_dev_types, 1) > 0"
    ),
}

#: A fill ratio falling by this many percentage points is a finding. Calibrated
#: against the defect this exists to catch, not picked round: Ashfield's precinct
#: fill went 35.9% -> 5.8% (30.1pp) and Marrickville's 32.7% -> 1.5% (31.2pp).
#: 5pp is far enough below both to catch a partial version of the same failure,
#: and far enough above the movement a normal re-extraction produces.
MATERIAL_DROP_PP = 5.0
#: A fall this large is not a regression, it is a field being emptied.
CRITICAL_DROP_PP = 25.0
#: Served rows legitimately move on re-extraction (a chapter re-extracted to 739
#: live rows from 680 is normal). A tenth of a council disappearing is not.
SERVED_DROP_PCT = 10.0
#: Below this many served rows a single row is worth several percentage points,
#: so ratios are noise. Small councils are compared on absolute counts instead.
#: inner_west serves 11 rows; one row there is 9.1pp.
MIN_SERVED_FOR_RATIO = 20

CRITICAL, STANDARD, INFO = "CRITICAL", "STANDARD", "INFO"


def send_telegram(msg: str) -> None:
    """Best-effort alert.

    Deliberately a local copy rather than an import from dcp_watchdog: that module
    opens a psycopg2 connection at MODULE level, so importing it to borrow fifteen
    lines would connect to the database as a side effect of an import.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] skipped -- no token or chat_id")
        return
    try:
        import requests

        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg[:4000]},
            timeout=10,
        )
        print(f"[telegram] {'sent OK' if resp.ok else f'HTTP {resp.status_code}'}")
    except Exception as exc:  # noqa: BLE001 -- an alert failure must not fail the check
        print(f"[telegram] send failed: {exc}")


def measure(cur, councils: list[str] | None = None) -> dict[str, dict]:
    """Current served-row and per-field fill counts, keyed by council."""
    selects = ", ".join(
        f"COUNT(*) FILTER (WHERE {pred}) AS {name}" for name, pred in WATCHED_FIELDS.items()
    )
    sql = f"""
        SELECT COALESCE(source_council, %s) AS council, COUNT(*) AS served, {selects}
        FROM regulatory_provisions
        WHERE is_current AND v2_is_actionable
        GROUP BY 1
    """
    params: list = [STATEWIDE]
    if councils:
        # Bind parameter, not interpolation: --council is the one value here that
        # comes from outside. STATEWIDE is matched on the COALESCE output, so
        # asking for the statewide set by name works like any other council.
        sql += " HAVING COALESCE(source_council, %s) = ANY(%s)"
        params += [STATEWIDE, list(councils)]
    cur.execute(sql, params)
    names = list(WATCHED_FIELDS)
    out: dict[str, dict] = {}
    for row in cur.fetchall():
        council, served = row[0], row[1]
        out[council] = {
            "served": served,
            "counts": {names[i]: row[2 + i] for i in range(len(names))},
        }
    return out


def load_previous(cur, council: str) -> dict | None:
    """This council's most recent recording, or None if it has never been recorded."""
    cur.execute(
        """SELECT served, counts, taken_at FROM dcp_council_field_snapshot
           WHERE council = %s ORDER BY taken_at DESC, id DESC LIMIT 1""",
        (council,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    served, counts, taken_at = row
    # psycopg2 decodes jsonb to dict, but a hand-written row could hold anything.
    # A malformed baseline must read as "no baseline", never as zeros.
    if not isinstance(counts, dict):
        return None
    return {"served": served, "counts": counts, "taken_at": taken_at}


def compare(council: str, prev: dict | None, now: dict) -> list[dict]:
    """Findings for one council. Empty list means nothing went backwards."""
    findings: list[dict] = []
    served_now = now["served"]

    if prev is None:
        findings.append({
            "severity": INFO, "council": council, "field": "-", "state": "NO_BASELINE",
            "message": f"first recording ({served_now} served rows) -- nothing to compare yet",
        })
        return findings

    served_before = prev["served"]

    # A council that served rows and now serves none is the largest possible drop,
    # and it is reported before any per-field comparison: every ratio below would
    # be 0/0, which must not read as "no change".
    if served_before > 0 and served_now == 0:
        findings.append({
            "severity": CRITICAL, "council": council, "field": "served", "state": "DROP",
            "message": f"served {served_before} -> 0 -- this council serves nothing",
        })
        return findings

    if served_before > 0:
        pct = 100.0 * (served_before - served_now) / served_before
        if pct > SERVED_DROP_PCT:
            findings.append({
                "severity": CRITICAL if pct >= 50 else STANDARD,
                "council": council, "field": "served", "state": "DROP",
                "message": f"served {served_before} -> {served_now} ({pct:.1f}% fewer)",
            })

    for field in WATCHED_FIELDS:
        before = prev["counts"].get(field)
        after = now["counts"].get(field)
        # Absent from the older snapshot means it was not measured then. It does
        # NOT mean zero, and treating it as zero would manufacture a 100% "gain"
        # now and a false drop the moment the field is removed from the watch list.
        if before is None or after is None:
            findings.append({
                "severity": INFO, "council": council, "field": field, "state": "NO_BASELINE",
                "message": f"not measured in the previous snapshot (now {after})",
            })
            continue

        # Small councils: a single row is worth several points, so ratios are
        # noise. Compare absolute counts, and only when the denominator did not
        # itself shrink -- otherwise a legitimate smaller re-extraction reads as
        # a field loss.
        if served_before < MIN_SERVED_FOR_RATIO or served_now < MIN_SERVED_FOR_RATIO:
            if after < before and served_now >= served_before:
                findings.append({
                    "severity": STANDARD, "council": council, "field": field, "state": "DROP",
                    "message": (f"{before} -> {after} rows carry it, while served held at "
                                f"{served_now} (small council -- absolute comparison)"),
                })
            continue

        ratio_before = 100.0 * before / served_before
        ratio_after = 100.0 * after / served_now
        fall = ratio_before - ratio_after
        if fall >= MATERIAL_DROP_PP:
            findings.append({
                "severity": CRITICAL if fall >= CRITICAL_DROP_PP else STANDARD,
                "council": council, "field": field, "state": "DROP",
                "message": (f"{ratio_before:.1f}% -> {ratio_after:.1f}% of served rows "
                            f"({before}/{served_before} -> {after}/{served_now}, -{fall:.1f}pp)"),
            })
    return findings


def _run_sibling(script: str, args: list[str] | None = None) -> tuple[int, str]:
    """Run another checker and return (exit code, stdout+stderr).

    Subprocess rather than import, for one reason each: audit_precinct_keying_coverage
    does its work in main() with no return value to borrow, and both open their own
    connections. Their exit codes and output are the interface.
    """
    path = HERE / script
    if not path.exists():
        # A missing sibling is reported, never silently skipped. Dockerfile.monitors
        # has twice shipped without a script something imported (#1080, #1081).
        return 127, f"{script} not found at {path} -- is it COPYed into the image?"
    try:
        proc = subprocess.run(
            [sys.executable, str(path), *(args or [])],
            capture_output=True, text=True, timeout=600, cwd=str(ROOT),
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:  # noqa: BLE001 -- a sibling crash is a finding, not our crash
        return 1, f"{script} could not be run: {exc}"


def zone_validity_finding() -> dict | None:
    """Zone codes are checked by validity, not by fill count. See the module docstring."""
    rc, out = _run_sibling("validate_zone_code_validity.py", ["--quiet"])
    if rc == 0:
        return None
    tail = "\n".join(out.strip().splitlines()[-6:])
    return {
        "severity": CRITICAL if rc == 1 else STANDARD,
        "council": "(all)", "field": "v2_applicable_zones", "state": "DROP",
        "message": f"validate_zone_code_validity.py exited {rc}:\n{tail}",
    }


def parse_exposed(out: str) -> set[str]:
    """LGA names from audit_precinct_keying_coverage.py's summary line.

    From the SUMMARY line, not the per-LGA table. The table left-justifies the
    name into a fixed-width column, so taking the first token off a table row
    turns "City of Parramatta" into "City" -- a name that matches nothing, and
    which would then look like a NEW exposure on the very next run and a
    disappearance on the one after. The summary line lists full names,
    comma-separated, after a colon:

        >>> 1 LGA(s) EXPOSED (keyed, no reproducible rule): Woollahra

    No summary line means nothing is exposed, which is a legitimate empty set --
    the caller reports growth, never absence.
    """
    exposed: set[str] = set()
    for line in out.splitlines():
        if not (line.startswith(">>>") and "EXPOSED" in line and ":" in line):
            continue
        for name in line.split(":", 1)[1].split(","):
            if name.strip():
                exposed.add(name.strip())
    return exposed


def precinct_exposure() -> tuple[set[str], str]:
    """Exposed LGAs, as a set to compare against the previous run.

    Not asserted empty: Woollahra is exposed today and has been for months, and
    making that a hard failure would produce an alarm nobody can satisfy --
    precisely how the daily SUSPECT alert taught an operator to stop reading the
    channel (migrations/066). Growth of this set is the signal.
    """
    rc, out = _run_sibling("audit_precinct_keying_coverage.py")
    return parse_exposed(out), out if rc not in (0,) else ""


def run(trigger_source: str = "manual", councils: list[str] | None = None,
        record: bool = True, alert: bool = True, as_json: bool = False) -> int:
    """Measure, compare, record, report. Returns the process exit code.

    Callable directly so scripts/dcp_commit_approved.py can invoke it in-process
    the way it already invokes derive_precinct_keys, rather than shelling out to
    a second Python and a second connection.
    """
    councils = list(councils) if councils else None

    if not DATABASE_URL:
        print("ERROR: DATABASE_URL is not set -- cannot check anything. This is a "
              "failure, not a pass.", file=sys.stderr)
        return 1

    conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '60s'")
        now = measure(cur, councils)

        findings: list[dict] = []
        # A council that was recorded before and is absent from this measurement
        # entirely is invisible to the loop below, which iterates what EXISTS. It
        # is the same defect as served -> 0 and must be found the same way.
        cur.execute("SELECT DISTINCT council FROM dcp_council_field_snapshot")
        known = {r[0] for r in cur.fetchall()}
        scope = set(councils) if councils else known
        for gone in sorted(scope & known - set(now)):
            prev = load_previous(cur, gone)
            if prev and prev["served"] > 0:
                findings.append({
                    "severity": CRITICAL, "council": gone, "field": "served", "state": "DROP",
                    "message": (f"served {prev['served']} rows at the last recording and now "
                                f"has no served rows at all"),
                })

        for council in sorted(now):
            findings += compare(council, load_previous(cur, council), now[council])

        zf = zone_validity_finding()
        if zf:
            findings.append(zf)

        exposed, exposure_err = precinct_exposure()
        if exposure_err:
            findings.append({
                "severity": STANDARD, "council": "(all)", "field": "v2_precinct_id",
                "state": "DROP", "message": f"precinct-rule audit did not run cleanly:\n{exposure_err[-400:]}",
            })
        cur.execute("""SELECT counts -> 'exposed_lgas' FROM dcp_council_field_snapshot
                       WHERE council = %s ORDER BY taken_at DESC, id DESC LIMIT 1""",
                    (STATEWIDE,))
        row = cur.fetchone()
        prev_exposed = set(row[0]) if row and isinstance(row[0], list) else None
        if prev_exposed is not None and exposed - prev_exposed:
            findings.append({
                "severity": CRITICAL, "council": "(all)", "field": "v2_precinct_id",
                "state": "DROP",
                "message": (f"newly exposed to precinct un-keying on re-extraction: "
                            f"{sorted(exposed - prev_exposed)} -- add a rule to "
                            f"scripts/derive_precinct_keys.py before re-extracting them"),
            })

        if record:
            for council, m in sorted(now.items()):
                counts = dict(m["counts"])
                if council == STATEWIDE:
                    # Piggy-backed on the statewide row because it is corpus-wide,
                    # not per-council, and a second table for one list would be a
                    # parallel surface with its own drift.
                    counts["exposed_lgas"] = sorted(exposed)
                cur.execute(
                    """INSERT INTO dcp_council_field_snapshot
                           (trigger_source, council, served, counts)
                       VALUES (%s, %s, %s, %s)""",
                    (trigger_source, council, m["served"], Json(counts)),
                )
            conn.commit()
    finally:
        conn.close()

    if as_json:
        print(json.dumps(findings, indent=2, default=str))
    else:
        print("=" * 64)
        print(f"COUNCIL COMPLETENESS ({trigger_source})")
        print("=" * 64)
        for council in sorted(now):
            m = now[council]
            bits = " ".join(
                f"{f.replace('v2_', '')}={m['counts'][f]}" for f in WATCHED_FIELDS
            )
            print(f"  {council:<24} served={m['served']:<6} {bits}")
        print("-" * 64)
        for sev in (CRITICAL, STANDARD, INFO):
            for f in [x for x in findings if x["severity"] == sev]:
                print(f"  [{sev}] {f['council']}/{f['field']}: {f['message']}")
        if not findings:
            print("  nothing went backwards.")

    actionable = [f for f in findings if f["severity"] in (CRITICAL, STANDARD)]
    if actionable and alert:
        lines = [f"{f['severity']} {f['council']}/{f['field']}: {f['message']}"
                 for f in actionable]
        send_telegram("Council completeness -- a field went backwards\n\n" + "\n\n".join(lines))

    # INFO alone is exit 0: a first recording is not a finding, and a run that
    # exits non-zero on its own first execution trains everyone to ignore it.
    return 2 if actionable else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trigger-source", default="manual",
                    choices=["commit", "monitor", "manual"],
                    help="What caused this recording (stored on the snapshot row).")
    ap.add_argument("--council", action="append",
                    help="Limit to this council (repeatable). Default: every council.")
    ap.add_argument("--no-record", action="store_true",
                    help="Compare only; do not write a snapshot row.")
    ap.add_argument("--no-alert", action="store_true", help="Never send Telegram.")
    ap.add_argument("--json", action="store_true", help="Emit findings as JSON.")
    a = ap.parse_args()
    return run(trigger_source=a.trigger_source, councils=a.council,
               record=not a.no_record, alert=not a.no_alert, as_json=a.json)


if __name__ == "__main__":
    sys.exit(main())
