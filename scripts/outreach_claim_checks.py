#!/usr/bin/env python3
"""Checks for the outreach claims that no single existing command answers.

prior-art-checked: composes existing checks rather than re-implementing them. Each sub-check calls a
probe that already backs a DQ row (scripts/dq_probe_live.py --id ...), an existing test file, or the
served read itself (scripts/conveyancing_db.fetch_dcp_setbacks), so a claim passes only on the same
evidence the DQ ledger already trusts. No existing script maps a public claim to that evidence:
scripts/verify_coverage_stats.py covers the published counts (claims 1-7 use it directly) and
scripts/check_served_answer_quality.py scores served answers against a baseline, not a claim.

Spec: ~/.claude/plans/ce-outreach-readiness-benchmark-SPEC-2026-09-11.md, claim set decided by the user
on 2026-09-14 (rows OC-1..OC-17 in .claude/dq_checks.json, run by `python scripts/dq_check.py --outreach`).

Usage:  python scripts/outreach_claim_checks.py OC-8
Exit:   0 every sub-check passed
        1 at least one sub-check failed
        2 none failed, but at least one could not run here (no database, no node_modules)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

_reconfigure = getattr(sys.stdout, "reconfigure", None)
if callable(_reconfigure):
    _reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import outreach_flood_depth_probe as flood_probe  # noqa: E402  (path set above)

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
Result = tuple[str, str]

#: The served guard, as scripts/conveyancing_db.fetch_dcp_setbacks applies it, minus the statewide and
#: umbrella slugs the published counts exclude.
SERVED = ("is_current AND (needs_review IS NULL OR needs_review = FALSE) "
          "AND lga <> 'nsw_statewide' AND lga <> 'inner_west'")


# ── building blocks ────────────────────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path = ROOT, timeout: int = 600) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return -1, str(exc)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _last(text: str) -> str:
    lines = [l for l in text.splitlines() if l.strip()]
    return lines[-1][:240] if lines else ""


def probe(dq_id: str) -> Result:
    """Run the check the DQ ledger itself records for this defect (.claude/dq_checks.json), so a claim
    and its defect row can never test different things. Exit 0 clean, 1 found, 2 could not look.

    Not a hard-coded dq_probe_live.py call: DQ-99's check is its own script, and calling the wrong one
    made the first full run report DQ-99 as "could not look" instead of running it (2026-09-14)."""
    try:
        spec = json.loads((ROOT / ".claude" / "dq_checks.json").read_text(encoding="utf-8"))["checks"][dq_id]
    except (OSError, ValueError, KeyError) as exc:
        return FAIL, f"{dq_id}: no ledger row to run ({exc})"
    cmd = list(spec.get("check") or [])
    if not cmd:
        return FAIL, f"{dq_id}: the ledger row has no check ({spec.get('why_no_check') or 'no reason'})"
    if cmd[0] in ("python", "python3"):
        cmd[0] = sys.executable
    cwd = ROOT / spec["cwd"] if spec.get("cwd") else ROOT
    rc, out = _run(cmd, cwd=cwd)
    return {0: PASS, 1: FAIL}.get(rc, UNKNOWN), f"{dq_id}: {_last(out)}"


def pytest_files(*paths: str, k: str | None = None) -> Result:
    cmd = [sys.executable, "-m", "pytest", "-q", "-o", "addopts=", *paths] + (["-k", k] if k else [])
    rc, out = _run(cmd)
    # Any non-zero pytest exit is a FAIL: 1 tests failed, 2 a collection error, 4 a usage error, 5 nothing
    # collected. Each is a check that did not pass, and a broken check must be visible, never "unknown".
    # Only -1 (the interpreter or pytest could not be started at all) is UNKNOWN.
    verdict = PASS if rc == 0 else UNKNOWN if rc == -1 else FAIL
    return verdict, f"pytest {' '.join(paths)}{' -k ' + k if k else ''}: {_last(out)}"


def _borrowable_node_modules():
    """The main checkout's node_modules, when this one has none.

    Used only to TELL THE OPERATOR how to make the check runnable. Borrowing
    the runner itself does not work and was tried: JavaScript module resolution
    walks directories, so pointing a borrowed jest at this checkout with
    --rootDir makes it fail in jest.setup.js on the first import, and widening
    --moduleDirectories makes it swallow the file argument and run all 104
    suites. The tree genuinely needs its own node_modules, or a junction to one.
    """
    # env=git_env() is NOT optional here, and DQ-54's ratchet caught it missing.
    # This runs inside git hooks, which export GIT_DIR. With it set, `git
    # rev-parse --git-common-dir` answers for the hook's repository rather than
    # this one -- so the function would confidently return some other
    # checkout's node_modules and the message would send an operator to link
    # the wrong dependencies.
    try:
        from qa_report_path import git_env

        done = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=str(ROOT), env=git_env(), capture_output=True, text=True,
            timeout=30)
    except (OSError, subprocess.SubprocessError, ImportError):
        return None
    if done.returncode != 0 or not done.stdout.strip():
        return None
    main_root = Path(done.stdout.strip())
    if main_root.name == ".git":
        main_root = main_root.parent
    if main_root.resolve() == ROOT.resolve():
        return None
    candidate = main_root / "frontend-nextjs" / "node_modules"
    return candidate if candidate.is_dir() else None


def _lockfiles_agree(main_modules) -> bool:
    """Do this checkout and the one we would borrow from pin the same packages?

    RAISED BY THE PRE-PUSH REVIEW, and it is right: if this worktree changes
    package-lock.json and the main checkout has not, borrowing its node_modules
    runs the test against the OLD dependencies. It would pass, and a clean
    `npm ci` here might not. That is the same shape as everything else this
    file is about -- a check that answers a question adjacent to the one asked.

    So the junction is only offered when the two lockfiles match, and when they
    do not the operator is told to install rather than borrow.
    """
    here = ROOT / "frontend-nextjs" / "package-lock.json"
    there = main_modules.parent / "package-lock.json"
    try:
        if not (here.is_file() and there.is_file()):
            return False
        return here.read_bytes() == there.read_bytes()
    except OSError:
        return False


def jest_file(test_path: str) -> Result:
    """Run a frontend test, or say EXACTLY how to make it runnable.

    WHY THE MESSAGE MATTERS. "could not run here" is not a failure, which makes
    it easy to accept and move past. It was: OC-9 sat NOT VERIFIED while three
    of its four sub-checks passed and the fourth was one command away from
    running. The same blind spot cost five Vercel deployments the same day,
    where "Type check skipped: node_modules absent" read as a pass for two
    days. An unrunnable check has to hand back the fix, not just the excuse.
    """
    name = "jest.cmd" if sys.platform == "win32" else "jest"
    jest = ROOT / "frontend-nextjs" / "node_modules" / ".bin" / name
    if not jest.exists():
        borrow = _borrowable_node_modules()
        if borrow and _lockfiles_agree(borrow):
            how = (f"link the main checkout's: cd frontend-nextjs && "
                   f'cmd //c mklink //J node_modules "{borrow}"')
        elif borrow:
            how = ("install them: cd frontend-nextjs && npm ci  "
                   "(NOT the main checkout's — this worktree's package-lock.json "
                   "differs from it, so borrowing would test the wrong packages)")
        else:
            how = "install them: cd frontend-nextjs && npm ci"
        return UNKNOWN, (f"jest {test_path}: frontend-nextjs/node_modules is absent, "
                         f"so it could not run here. This is NOT a pass -- {how}")
    rc, out = _run([str(jest), test_path], cwd=ROOT / "frontend-nextjs")
    return (PASS if rc == 0 else FAIL), f"jest {test_path}: {_last(out)}"


def _connect():
    try:
        from dq_db import connect
        return connect()
    except Exception:  # noqa: BLE001 - unreachable is UNKNOWN, reported by the caller
        return None


def sql_count(label: str, sql: str, expect: int = 0) -> Result:
    conn = _connect()
    if conn is None:
        return UNKNOWN, f"{label}: database unreachable"
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            n = cur.fetchone()[0]
    except Exception as exc:  # noqa: BLE001 - a query that no longer runs is a broken check: FAIL
        return FAIL, f"{label}: query failed ({exc})"
    finally:
        conn.close()
    return (PASS if n == expect else FAIL), f"{label}: {n} (must be {expect})"


def served_entries() -> tuple[list[tuple[str, dict, dict]] | None, str]:
    """Every served control, read through the serve path itself: (lga, entry, registry_pdf_urls)."""
    conn = _connect()
    if conn is None:
        return None, "database unreachable"
    try:
        import conveyancing_db as cdb
        with conn.cursor() as cur:
            cur.execute(f"SELECT DISTINCT lga FROM dcp_setback_controls WHERE {SERVED} ORDER BY lga")
            lgas = [r[0] for r in cur.fetchall()]
        out: list[tuple[str, dict, dict]] = []
        for lga in lgas:
            res = cdb.fetch_dcp_setbacks(conn, lga)
            if not res:
                continue
            urls = res.get("registry_pdf_urls") or {}
            for entry in (res.get("setbacks") or []) + (res.get("sd_setbacks") or []):
                out.append((lga, entry, urls))
        return out, ""
    except Exception as exc:  # noqa: BLE001
        return None, f"serve path failed ({exc})"
    finally:
        conn.close()


def no_rendered_phrase(label: str, pattern: str) -> Result:
    """No non-comment line under the frontend's app/, components/ or lib/ matches the pattern."""
    rx = re.compile(pattern, re.I)
    hits: list[str] = []
    for sub in ("app", "components", "lib"):
        for f in sorted((ROOT / "frontend-nextjs" / sub).rglob("*.ts*")):
            if "node_modules" in f.parts:
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if line.strip().startswith(("//", "*", "/*", "{/*")):
                    continue
                if rx.search(line):
                    hits.append(f"{f.relative_to(ROOT).as_posix()}:{n}")
    return (PASS if not hits else FAIL), f"{label}: {len(hits)} rendered occurrence(s) {hits[:3]}"


# ── sub-checks specific to one claim ───────────────────────────────────────────────────────────────

def every_served_number_is_cited() -> Result:
    """Claim 8 is about NUMBERS, so only entries carrying a value are counted. A served "no set number" note
    (e.g. "No maximum site coverage specified in the DCP") has no number to cite; whether council material
    traces to a published document is claim 12's check."""
    import conveyancing_db as cdb
    entries, why = served_entries()
    if entries is None:
        return UNKNOWN, f"served citations: {why}"
    instruments = registered_instruments()
    if instruments is None:
        return UNKNOWN, "served citations: instrument_registry could not be read, so a legislation link cannot be judged"
    statewide = instruments.get(None, frozenset())
    missing = []
    numbers = 0
    for lga, e, urls in entries:
        if e.get("value_min") is None and e.get("value_max") is None:
            continue
        numbers += 1
        url = urls.get(e.get("source_chapter_key") or "") or ""
        allowed = instruments.get(lga, frozenset()) | statewide
        # A clause withheld because its page does not prove it is cited by that page (migration 077);
        # withheld with no page is no citation at all (a blank citation is not evidence).
        cited = bool((e.get("clause") or "").strip()) or (
            e.get("clause_shown") is False and bool(cdb.clause_or_page("", e.get("pdf_page"))))
        if (not cited or not (e.get("source_text") or "").strip()
                or not is_source_link(url, allowed)):
            missing.append(f"{lga}/{e.get('semantic_type')}")
    return ((PASS if not missing else FAIL),
            f"served numbers missing where they are printed (proven clause or page), the council's sentence or a link to its source document: "
            f"{len(missing)} of {numbers} {missing[:4]}")


#: A page on the official NSW legislation site is the source document for an LEP or SEPP clause, which is published
#: there rather than as a council PDF (user decision 2026-09-15). It counts only when it is a view of ONE instrument
#: and that instrument is registered for the council (or statewide): the site's home page, a search page or another
#: council's LEP would otherwise pass while opening nothing the number came from (cross-review, same day).
#: prior-art-checked: extends claim 8's own link test in place; the files the guard named render legislation text or
#: monitor versions, none decides whether a served number's link opens its source document.
_LEGISLATION_DOC = re.compile(r"^https://legislation\.nsw\.gov\.au/view/(?:whole/)?(?:html|pdf)/(?:inforce|asmade)/"
                              r"(?:current|\d{4}-\d{2}-\d{2})/((?:epi|act|sl)-\d{4}-\d{3,4})(?:[/#?]|$)")
# Bounded on both sides: a longer id such as epi-2024-12345 must register nothing, never its prefix epi-2024-1234
# (cross-review MEDIUM, 2026-09-15). An unregistered id fails its link visibly instead of passing a different law.
_INSTRUMENT_ID = re.compile(r"(?<![A-Za-z0-9])((?:epi|act|sl)-\d{4}-\d{3,4})(?!\d)")


def registered_instruments() -> dict | None:
    """{council, or None for a statewide instrument: frozenset of legislation ids} from the active
    instrument_registry rows. None when the registry cannot be read, which the caller reports as UNKNOWN."""
    conn = _connect()
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT council, pco_instrument_id, legislation_url FROM instrument_registry WHERE is_active")
            rows = cur.fetchall()
    except Exception:  # noqa: BLE001 - unreadable registry: UNKNOWN, never a pass
        return None
    finally:
        conn.close()
    found: dict = {}
    for council, pco_id, url in rows:
        m = _INSTRUMENT_ID.search(f"{pco_id or ''} {url or ''}")
        if m:
            found.setdefault(council, set()).add(m.group(1))
    return {k: frozenset(v) for k, v in found.items()}


def is_source_link(url: str, legislation_ids: frozenset = frozenset()) -> bool:
    """True for a link that opens the document a number was read from: a PDF (the council's own copy or our R2
    mirror of it), or a legislation.nsw.gov.au view of an instrument in ``legislation_ids``."""
    u = (url or "").strip()
    if ".pdf" in u.lower() or "r2.dev" in u.lower():
        return True
    m = _LEGISLATION_DOC.match(u)
    return bool(m) and m.group(1) in legislation_ids


#: The council's own sentence states a maximum. Read here, independently of how the serve path words it.
_SOURCE_STATES_MAXIMUM = re.compile(r"\bmax(?:imum)?\b", re.I)
_SOURCE_DENIES_BEFORE = re.compile(r"\b(?:no|not|without|non)\b(?:\s+[A-Za-z]+){0,2}\s*$", re.I)
_SOURCE_DENIES_AFTER = re.compile(r"^\s*(?:[A-Za-z]+\s+)?(?:(?:is|are)\s+)?(?:not|n/a|none)\b", re.I)


def _source_states_maximum(text: str) -> bool:
    """"no maximum applies" and "maximum not specified" name the word while denying it."""
    return any(not (_SOURCE_DENIES_BEFORE.search(text[max(0, m.start() - 40):m.start()])
                    or _SOURCE_DENIES_AFTER.search(text[m.end():m.end() + 40]))
               for m in _SOURCE_STATES_MAXIMUM.finditer(text))


def no_range_printed_as_a_maximum() -> Result:
    """A between-rule (e.g. a rear setback of 3-6 m by lot width) must not read as a maximum the plan does not
    set, and a number must print in its own unit.

    A range may still read "minimum ... maximum" when the council's sentence states a maximum, as canada_bay's
    "Minimum 1, maximum 2 car parking spaces" does. Measured 2026-09-14 before the wording fix: 33 served ranges,
    and every number printed in metres, so 18 parking rates read "1 m minimum; 2 m maximum"."""
    entries, why = served_entries()
    if entries is None:
        return UNKNOWN, f"range wording: {why}"
    bad, wrong_unit = [], []
    for lga, e, _ in entries:
        vmin, vmax, sem = e.get("value_min"), e.get("value_max"), (e.get("semantic_type") or "")
        requirement = e.get("requirement") or ""
        is_ceiling = sem.startswith("max_") or sem.endswith("_max")
        if (vmin is not None and vmax is not None and float(vmin) < float(vmax) and not is_ceiling
                and "maximum" in requirement.lower()
                and not _source_states_maximum(e.get("source_text") or "")):
            bad.append(f"{lga}/{sem}")
        unit = (e.get("unit") or "").strip()
        if (vmin is not None or vmax is not None) and unit and unit not in requirement:
            wrong_unit.append(f"{lga}/{sem}")
    return ((PASS if not bad and not wrong_unit else FAIL),
            f"served ranges printed with a 'maximum' the plan does not set: {len(bad)} {bad[:4]}; "
            f"numbers printed in a unit other than their own: {len(wrong_unit)} {wrong_unit[:4]}")


def dcp_plans_are_dated() -> Result:
    rc, out = _run([sys.executable, "scripts/check_dcp_as_at_coverage.py"])
    if rc == 2 or rc == -1:
        return UNKNOWN, f"plan dates: could not measure ({_last(out)})"
    start, end = out.find("{"), out.rfind("}")
    try:
        report = json.loads(out[start:end + 1])
    except ValueError:
        return FAIL, "plan dates: check_dcp_as_at_coverage.py output was not the JSON report"
    dateless = report.get("dateless_lgas") or []
    return (PASS if not dateless else FAIL), f"served councils with no plan date: {len(dateless)} {dateless[:5]}"


# prior-art-checked: reuse not viable as-is -- these sub-checks CALL the existing serve filter
# (conveyancing_db.zone_row_applies) and the existing translation table (shared/zone-taxonomy.json) and read
# the existing registry and dcp_plan_as_at tables. dq_probe_live.py's DQ-61 asks only whether a version date
# is recorded, not which plan is served or confirmed, so it cannot answer the cross-review finding; the
# flagged frontend files display provisions and are not checks.

#: One row per served council that fails, with the first reason that applies. SERVED carries is_current
#: and needs_review. Numbers keyed _external_* come from state instruments (the LEP, the Apartment Design
#: Guide), not a council plan; their currency is DQ-88, which OC-17 also runs. A NULL chapter key is not
#: external: it cannot be traced, so it fails. A registered chapter with no plan name counts as a plan of
#: its own, so it can never merge silently into a named one.
_PLAN_IN_FORCE_SQL = f"""
WITH served AS (
    SELECT lga, source_chapter_key FROM dcp_setback_controls
     WHERE {SERVED} AND COALESCE(source_chapter_key, '') NOT LIKE '\\_external\\_%'
), traced AS (
    SELECT s.lga, r.id AS registry_id, COALESCE(r.dcp_name, '(no plan name)') AS plan
      FROM served s
      LEFT JOIN dcp_chapter_registry r
        ON r.council = s.lga AND r.chapter_key = s.source_chapter_key AND r.is_active
), per_council AS (
    SELECT lga,
           count(*) FILTER (WHERE registry_id IS NULL) AS untraced,
           count(DISTINCT plan) FILTER (WHERE registry_id IS NOT NULL) AS plans,
           min(plan) FILTER (WHERE registry_id IS NOT NULL) AS plan
      FROM traced GROUP BY lga
)
SELECT p.lga,
       CASE WHEN p.untraced > 0 THEN p.untraced || ' number(s) trace to no active chapter'
            WHEN p.plans <> 1 THEN p.plans || ' plan names served'
            WHEN a.currency_confirmed_at IS NULL THEN 'no confirmation'
            WHEN a.currency_confirmed_at < NOW() - INTERVAL '90 days' THEN 'confirmation older than 90 days'
            ELSE 'confirmation names ' || COALESCE(a.currency_confirmed_plan, 'no plan') END AS reason
  FROM per_council p
  LEFT JOIN dcp_plan_as_at a ON a.lga = p.lga
 WHERE p.untraced > 0 OR p.plans <> 1
    OR a.currency_confirmed_at IS NULL OR a.currency_confirmed_at < NOW() - INTERVAL '90 days'
    OR a.currency_confirmed_plan IS DISTINCT FROM p.plan
 ORDER BY p.lga"""


def every_served_council_has_a_current_plan_check() -> Result:
    """Every council's served DCP numbers come from ONE registered plan, and a person confirmed within 90
    days that THAT plan is the one in force.

    Added 2026-09-14 after measuring councils whose plan changed while an older version was served
    (Northern Beaches, Canada Bay, Randwick, Burwood, The Hills; Strathfield before them). A repeal is not
    visible in a URL, so the repealed-source query alone cannot catch it; a dated confirmation can.

    The first version joined dcp_plan_as_at by council only, so a recent confirmation of one plan passed a
    council still serving numbers from another (cross-review of #1115). Measured the same day: waverley
    serves 7 numbers from Waverley DCP 2012 beside 42 from Waverley DCP 2022. The confirmation now has to
    name the plan (dcp_plan_as_at.currency_confirmed_plan, migration 073), and a council whose numbers
    cannot all be traced to one registered plan fails before any confirmation is looked at."""
    conn = _connect()
    if conn is None:
        return UNKNOWN, "plan in force: database unreachable"
    try:
        with conn.cursor() as cur:
            cur.execute(_PLAN_IN_FORCE_SQL)
            failing = cur.fetchall()
    except Exception as exc:  # noqa: BLE001 - a query that no longer runs is a broken check: FAIL
        return FAIL, f"plan in force: query failed ({exc})"
    finally:
        conn.close()
    return ((PASS if not failing else FAIL),
            f"served councils without one confirmed plan in force behind every number: {len(failing)} "
            f"{[f'{lga} ({reason})' for lga, reason in failing[:4]]}")


def no_site_loses_a_rule_to_a_retired_zone_code() -> Result:
    """No served row applies to a pre-2023 zone code but not to the code that replaced it.

    The serve filter reads zone codes as written and does not alias legacy codes (zone_row_applies), so a
    row scoped to "B1, B2, B4 zones" with no stored scope hid itself from every E1 and MU1 site. Three such
    rows were given a stored scope on 2026-09-14 (ashfield 504, sutherland 242 and 243); this keeps it at 0.
    It asks the serve filter itself, using the repo's translation table, rather than matching text: a rule
    for every zone that mentions "within 400m B3/B4" (canada_bay 816 and 824) is correctly not counted."""
    try:
        taxonomy = json.loads((ROOT / "frontend-nextjs" / "shared" / "zone-taxonomy.json")
                              .read_text(encoding="utf-8"))
        aliases = taxonomy["legacyToCurrentAliases"]
    except (OSError, ValueError, KeyError) as exc:
        return FAIL, f"retired zone codes: translation table unreadable ({exc})"
    successors: dict[str, list[str]] = {}
    for current, members in aliases.items():
        for member in members:
            if member != current:
                successors.setdefault(member, []).append(current)
    if not successors:
        return FAIL, "retired zone codes: the translation table maps no retired code, so nothing was checked"
    conn = _connect()
    if conn is None:
        return UNKNOWN, "retired zone codes: database unreachable"
    try:
        import conveyancing_db as cdb
        with conn.cursor() as cur:
            # SERVED carries is_current and needs_review.
            cur.execute("SELECT id, lga, applicability, condition, zones_include, zones_exclude "
                        f"FROM dcp_setback_controls WHERE {SERVED}")
            rows = cur.fetchall()
    except Exception as exc:  # noqa: BLE001 - a check that cannot read the rows is broken: FAIL
        return FAIL, f"retired zone codes: could not read the served rows ({exc})"
    finally:
        conn.close()
    lost: list[str] = []
    for row_id, lga, applicability, condition, include, exclude in rows:
        for legacy, currents in successors.items():
            if (cdb.zone_row_applies(applicability, condition, legacy, include, exclude)
                    and not all(cdb.zone_row_applies(applicability, condition, code, include, exclude)
                                for code in currents)):
                lost.append(f"{lga}/{row_id} {legacy}")
                break
    return ((PASS if not lost else FAIL),
            f"served rows that apply to a retired zone code but not to its successor: {len(lost)} {lost[:4]}")


#: Claim 12: every served council number and rule comes from an active registered chapter that records
#: where the council publishes it. SERVED carries is_current and needs_review; provisions are the served
#: set (is_current AND v2_is_actionable). _external_* numbers come from state instruments, not a council
#: document, and are left to the claims about those instruments.
_UNTRACED_COUNCIL_MATERIAL_SQL = f"""
SELECT (SELECT count(*) FROM dcp_setback_controls s
          LEFT JOIN dcp_chapter_registry r
            ON r.council = s.lga AND r.chapter_key = s.source_chapter_key AND r.is_active
         WHERE s.id IN (SELECT id FROM dcp_setback_controls WHERE {SERVED})
           AND COALESCE(s.source_chapter_key, '') NOT LIKE '\\_external\\_%'
           AND (r.id IS NULL OR (r.council_url IS NULL AND r.council_page_url IS NULL)))
     + (SELECT count(*) FROM regulatory_provisions p
          LEFT JOIN dcp_chapter_registry r
            ON r.council = p.source_council AND r.chapter_key = p.source_chapter_key AND r.is_active
         WHERE p.is_current AND p.v2_is_actionable
           AND p.source_council IS NOT NULL AND p.source_council <> 'state'
           AND (r.id IS NULL OR (r.council_url IS NULL AND r.council_page_url IS NULL)))"""


# ── the claims ─────────────────────────────────────────────────────────────────────────────────────

CLAIMS: dict[str, list[Callable[[], Result]]] = {
    # Disposition 2026-09-14: garbled text served as rules makes "N provisions" count things that are not
    # the council's words, so the text-damage probes block this claim alongside its counts.
    "OC-4": [
        lambda: _coverage_fields("provisionsTotal", "dcpActionableProvisions"),
        lambda: probe("DQ-76"),
        lambda: probe("DQ-78"),
        lambda: probe("DQ-97"),
        lambda: probe("DQ-29"),
    ],
    # Disposition 2026-09-14: Housing SEPP standards that a known amendment should have staled (DQ-96)
    # make "45 SEPP standards" a count of rules not all in force.
    "OC-6": [
        lambda: _coverage_fields("heritageAreas", "regulatoryDefinitions", "seppStandards", "adgCriteria"),
        lambda: probe("DQ-96"),
    ],
    "OC-7": [
        lambda: _coverage_fields("floodStudies", "floodDepthStudies"),
        lambda: flood_probe.flood_depth_delivered_in_production(),
    ],
    # Added 2026-09-14: 15 active chapters' public links named an older copy than the one their rules were read
    # from, so Waverley DCP 2022's link opened a 490-page PDF while its rules cite the 448-page one. Compared
    # exactly, not with LIKE: an underscore in a path is a LIKE wildcard.
    "OC-8": [
        every_served_number_is_cited,
        lambda: probe("DQ-39"),
        lambda: sql_count("active chapters whose public PDF link is not their current copy",
                          "SELECT count(*) FROM dcp_chapter_registry WHERE is_active "
                          "AND r2_current_path IS NOT NULL AND r2_public_pdf_url IS NOT NULL "
                          "AND right(r2_public_pdf_url, length(r2_current_path) + 1) <> ('/' || r2_current_path)"),
    ],
    "OC-9": [
        lambda: pytest_files("tests/test_conveyancing_da_threestate.py", "tests/test_typed_absence_fixes.py",
                             "tests/test_fabricated_verdicts.py"),
        lambda: probe("DQ-50"),
        lambda: jest_file("__tests__/api/canibuildit/lead-verdict-integrity.test.ts"),
    ],
    "OC-10": [
        dcp_plans_are_dated,
        lambda: probe("DQ-61"),
        lambda: probe("DQ-70"),
    ],
    "OC-11": [
        lambda: sql_count("councils whose LEP zones are all complete",
                          "SELECT count(*) FROM (SELECT lga FROM lep_zone_coverage GROUP BY lga "
                          "HAVING bool_and(COALESCE(is_complete, FALSE))) t", expect=28),
    ],  # 26 -> 28 on 2026-09-24 (user decision): the repaired zone scraper added
        # Wollongong and Newcastle. Exact on purpose, so the claim moves with the data.
    # Reworded 2026-09-14: "No council data is stored" was contradicted by the council PDFs kept so each rule
    # can link to its page. The claim is now what is true, and the retired wording must stay gone.
    "OC-12": [
        lambda: no_rendered_phrase("retired 'No council data is stored'", r"No council data is stored|Privacy safe"),
        lambda: sql_count("served council numbers and rules not traced to a published council document",
                          _UNTRACED_COUNCIL_MATERIAL_SQL),
    ],
    # "8 risk layers" was retired 2026-09-14: nothing in the repo produced an 8, so it could not be grounded.
    # The two counts left are checked against their sources; the retired figure must stay off every page.
    "OC-13": [
        lambda: pytest_files("tests/test_coverage_source_derived_stats.py",
                             k="gov_data_sources or secondary_dwelling or risk_layers"),
        lambda: no_rendered_phrase("retired '8 risk layers'", r"riskLayers|Risk layers|\b8 risk layers\b"),
    ],
    "OC-14": [
        lambda: no_rendered_phrase("retired '7 councils with full structured provisions'",
                                   r"dcpFullCouncils|full structured (provisions|DCP|build)"),
    ],
    "OC-15": [
        lambda: no_rendered_phrase("retired planner time savings",
                                   r"TIME_SAVINGS|10 minutes, not 2 hours|2 hours to 10 minutes|"
                                   r"\b(5|10|15|20|30)–(10|15|20|30|60) min\b|time saved|hours back|"
                                   r"minutes saved|hours saved|billable assessments"),
    ],
    # Run through this script, not a bare "python -m pytest" row: sys.executable is the interpreter that
    # launched the gate. A bare "python" resolves through PATH, and on this machine that is a different
    # venv whose missing packages made the calibration test error on collection (2026-09-14).
    "OC-16": [
        lambda: pytest_files("tests/test_shadow_calibration.py"),
    ],
    "OC-17": [
        lambda: probe("DQ-99"),
        lambda: probe("DQ-66"),
        lambda: probe("DQ-32c"),
        lambda: probe("DQ-61"),
        lambda: probe("DQ-70"),
        lambda: sql_count("active chapters sourced from a repealed plan",
                          "SELECT count(*) FROM dcp_chapter_registry WHERE is_active AND ("
                          "council_url ILIKE '%repealed%' OR r2_current_path ILIKE '%repealed%' "
                          "OR r2_public_pdf_url ILIKE '%repealed%')"),
        no_range_printed_as_a_maximum,
        every_served_council_has_a_current_plan_check,
        no_site_loses_a_rule_to_a_retired_zone_code,
        lambda: probe("DQ-88"),
        lambda: probe("DQ-33"),
    ],
}


def _coverage_fields(*keys: str) -> Result:
    rc, out = _run([sys.executable, "scripts/verify_coverage_stats.py", "--field", *keys])
    return {0: PASS, 1: FAIL}.get(rc, UNKNOWN), f"published {', '.join(keys)}: {_last(out)}"


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in CLAIMS:
        print(f"usage: outreach_claim_checks.py {{{','.join(CLAIMS)}}}", file=sys.stderr)
        return 1
    results = [check() for check in CLAIMS[argv[0]]]
    for verdict, detail in results:
        print(f"  {verdict:<8} {detail}")
    verdicts = {v for v, _ in results}
    if FAIL in verdicts:
        print(f"{argv[0]}: FAILS")
        return 1
    if UNKNOWN in verdicts:
        print(f"{argv[0]}: NOT VERIFIED HERE")
        return 2
    print(f"{argv[0]}: HOLDS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
