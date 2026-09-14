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


def jest_file(test_path: str) -> Result:
    name = "jest.cmd" if sys.platform == "win32" else "jest"
    jest = ROOT / "frontend-nextjs" / "node_modules" / ".bin" / name
    if not jest.exists():
        return UNKNOWN, f"jest {test_path}: frontend-nextjs/node_modules is absent, so it could not run here"
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
    entries, why = served_entries()
    if entries is None:
        return UNKNOWN, f"served citations: {why}"
    missing = []
    for lga, e, urls in entries:
        url = urls.get(e.get("source_chapter_key") or "") or ""
        has_pdf = ".pdf" in url.lower() or "r2.dev" in url.lower()
        if not (e.get("clause") or "").strip() or not (e.get("source_text") or "").strip() or not has_pdf:
            missing.append(f"{lga}/{e.get('semantic_type')}")
    return ((PASS if not missing else FAIL),
            f"served numbers missing a clause, the council's sentence or a PDF link: "
            f"{len(missing)} of {len(entries)} {missing[:4]}")


def no_range_printed_as_a_maximum() -> Result:
    """A between-rule (e.g. R2 rear setback 6-10 m) must not read as '10 m maximum' in the report."""
    entries, why = served_entries()
    if entries is None:
        return UNKNOWN, f"range wording: {why}"
    bad = []
    for lga, e, _ in entries:
        vmin, vmax, sem = e.get("value_min"), e.get("value_max"), (e.get("semantic_type") or "")
        is_ceiling = sem.startswith("max_") or sem.endswith("_max")
        if (vmin is not None and vmax is not None and float(vmin) < float(vmax) and not is_ceiling
                and "maximum" in (e.get("requirement") or "").lower()):
            bad.append(f"{lga}/{sem}")
    return ((PASS if not bad else FAIL),
            f"served ranges printed with a 'maximum' the plan does not set: {len(bad)} {bad[:4]}")


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


def not_yet_grounded(label: str, reason: str) -> Result:
    """A part of a kept claim that nothing can verify yet. It fails until someone replaces this
    sub-check with a real one; it never passes by itself."""
    return FAIL, f"{label}: {reason}"


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
        lambda: not_yet_grounded(
            "flood depth delivered in production",
            "the R2 raster download for the depth studies has never been observed succeeding on the "
            "production host (claim inventory §5.1). Replace this with a probe of the production flood "
            "answer for a Tweed, Wollongong or Redbank address."),
    ],
    "OC-8": [
        every_served_number_is_cited,
        lambda: probe("DQ-39"),
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
                          "HAVING bool_and(is_complete)) t", expect=26),
    ],
    "OC-13": [
        lambda: pytest_files("tests/test_coverage_source_derived_stats.py",
                             k="gov_data_sources or secondary_dwelling"),
        lambda: not_yet_grounded(
            "8 risk layers", "coverage.ts marks riskLayers UNVERIFIED with no source list. Ground it against a "
            "real list and replace this sub-check with that check."),
    ],
    "OC-14": [
        lambda: no_rendered_phrase("retired '7 councils with full structured provisions'",
                                   r"dcpFullCouncils|full structured (provisions|DCP|build)"),
    ],
    "OC-15": [
        lambda: no_rendered_phrase("retired planner time savings",
                                   r"TIME_SAVINGS|10 minutes, not 2 hours|2 hours to 10 minutes|"
                                   r"\b(5|10|15|20|30)–(10|15|20|30|60) min\b"),
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
