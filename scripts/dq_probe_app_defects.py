#!/usr/bin/env python3
"""Checks for five defects found by using the live app on 2026-10-04 (DQ-122..DQ-126).

prior-art-checked: none of these had a check. dq_probe_live.py holds count-only SQL probes and cannot
call an HTTP endpoint or read a source file, which DQ-122 and DQ-123/124 need; the two SQL ones live
here too so the five rows logged together are checked together.

Each was found on verify.plotdetect.com.au while checking Woollahra and Waverley by real address, and
logged as backlog under the freeze rule. A check exists so the row can go green only when the defect
is really gone -- and red again if it comes back.

Usage:  python scripts/dq_probe_app_defects.py --id DQ-122
Exit:   0 clean, 1 defect present, 2 could not look (no network, no database)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

APP = "https://verify.plotdetect.com.au"

#: (address the page sends, house number and suburb the answer must carry). The first two FAILED on
#: 2026-10-04 (893 and 582 came back); the rest resolved correctly and stay as controls, so a fix that
#: breaks ordinary lookups also goes red.
ADDRESSES = [
    ("700 New South Head Rd, Rose Bay NSW 2029", "700", "ROSE BAY"),
    ("235 New South Head Rd, Point Piper NSW 2027", "235", "POINT PIPER"),
    ("680 New South Head Rd, Rose Bay NSW 2029", "680", "ROSE BAY"),
    ("60 Hall St, Bondi Beach NSW 2026", "60", "BONDI BEACH"),
    ("180 Ocean St, Edgecliff NSW 2027", "180", "EDGECLIFF"),
]


def _number_matches(asked: str, returned: str) -> bool:
    """'680' matches '674-680 ...'; '20' does NOT match '120 ...' or '893 ...'."""
    head = returned.split(" ")
    for tok in head[:3]:
        for part in re.split(r"[-/]", tok):
            if part == asked:
                return True
        m = re.match(r"^(\d+)-(\d+)$", tok)
        if m and int(m.group(1)) <= int(asked) <= int(m.group(2)):
            return True
    return False


def dq122() -> tuple[int, str]:
    wrong, errors = [], []
    for addr, number, suburb in ADDRESSES:
        url = f"{APP}/api/property?address={urllib.parse.quote(addr)}"
        try:
            # The site's edge refuses Python's default User-Agent (403); a browser one gets the page's own answer.
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (dq_probe_app_defects)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                got = (json.load(r).get("data") or {}).get("address") or ""
        except Exception as exc:  # noqa: BLE001 - unreachable is "could not look", not clean
            errors.append(f"{addr}: {exc}")
            continue
        if not (_number_matches(number, got.upper()) and suburb in got.upper()):
            wrong.append(f"'{addr}' -> '{got}'")
    if errors and not wrong:
        return 2, f"could not reach {APP}: {errors[0]}"
    return (1 if wrong else 0), (f"{len(wrong)} of {len(ADDRESSES)} addresses returned another property: "
                                 + "; ".join(wrong) if wrong else "every address returned itself")


def _db():
    import dq_db
    return dq_db.connect()


def dq123() -> tuple[int, str]:
    """The DCP name the page prints must be the plan the council's served material comes from."""
    src = (ROOT / "frontend-nextjs/components/compliance/ProvisionsByTocStructure.tsx").read_text(encoding="utf-8")
    start = src.find("const councilDcpNames")
    if start < 0:
        return 0, "councilDcpNames is gone from ProvisionsByTocStructure.tsx -- the hardcoded table no longer exists"
    labels = dict(re.findall(r"(\w+): '([^']+)'", src[start:src.index("};", start)]))
    try:
        conn = _db()
    except Exception as exc:  # noqa: BLE001
        return 2, f"database unreachable ({exc})"
    try:
        with conn.cursor() as cur:
            # The plan behind the most served material, rule text and numbers together.
            cur.execute("""
                WITH served AS (
                    SELECT source_council AS council, source_chapter_key AS ck FROM regulatory_provisions
                     WHERE is_current AND v2_is_actionable AND source_council IS NOT NULL
                    UNION ALL
                    SELECT lga, source_chapter_key FROM dcp_setback_controls
                     WHERE is_current AND (needs_review IS NULL OR needs_review = FALSE)
                )
                SELECT r.council, r.dcp_name, count(*) FROM served s
                  JOIN dcp_chapter_registry r ON r.council = s.council AND r.chapter_key = s.ck AND r.is_active
                 WHERE r.dcp_name IS NOT NULL GROUP BY 1, 2""")
            rows = cur.fetchall()
    finally:
        conn.close()
    top: dict[str, tuple[str, int]] = {}
    for council, name, n in rows:
        key = council.replace("-", "_")
        if n > top.get(key, ("", -1))[1]:
            top[key] = (name, n)
    year = lambda s: set(re.findall(r"(?:19|20)\d\d", s))  # noqa: E731
    wrong = []
    for council, label in sorted(labels.items()):
        if council not in top:
            continue
        served = top[council][0]
        # A label with no year is incomplete, not wrong; one whose year differs names another plan.
        if (year(label) and year(label) != year(served)) or ("warringah" in served.lower()) != ("warringah" in label.lower()):
            wrong.append(f"{council}: page '{label}', served '{served}'")
    return (1 if wrong else 0), (f"{len(wrong)} council DCP names on the page are not the plan served: "
                                 + "; ".join(wrong) if wrong else "every printed DCP name is the plan served")


def dq124() -> tuple[int, str]:
    """The 'full chapter text ... not loaded yet' note must not render when chapter text IS loaded.
    DcpStructuredControls is rendered twice by ProvisionsByTocStructure: once as the no-text fallback,
    once beneath loaded text. The note may only appear in the first, so it must be conditional."""
    src = (ROOT / "frontend-nextjs/components/compliance/DcpStructuredControls.tsx").read_text(encoding="utf-8")
    if "not loaded yet" not in src:
        return 0, "the note no longer exists"
    unconditional = re.search(r"^\s*\{textNotLoadedNote\}\s*$", src, re.M)
    return ((1, "textNotLoadedNote renders unconditionally, so it is printed beneath loaded chapter text")
            if unconditional else (0, "the note is conditional"))


def _sql_count(sql: str, what: str) -> tuple[int, str]:
    try:
        conn = _db()
    except Exception as exc:  # noqa: BLE001
        return 2, f"database unreachable ({exc})"
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            n = cur.fetchone()[0]
    finally:
        conn.close()
    return (1 if n else 0), f"{n} {what}"


def dq125() -> tuple[int, str]:
    return _sql_count("SELECT count(*) FROM regulatory_provisions WHERE is_current AND v2_is_actionable "
                      "AND provision_text LIKE '%<table%'",
                      "served rules carry raw '<table' markup in their text")


def dq126() -> tuple[int, str]:
    """Woollahra served rows on no_config whose OWN document names a chapter the config has an entry for:
    the document says which Part, the tagger read a different code out of the heading and gave up."""
    from enrichment.config import COUNCIL_CONFIGS
    parts = sorted(k for k in COUNCIL_CONFIGS["woollahra"]["parts"] if re.match(r"^[A-Z]\d+$", k))
    codes = ",".join(f"'{p.lower()}'" for p in parts)
    return _sql_count(
        "SELECT count(*) FROM regulatory_provisions WHERE is_current AND v2_is_actionable "
        "AND source_council = 'woollahra' "
        "AND (v2_dev_type_source = 'no_config' OR v2_zone_source = 'no_config') "
        f"AND substring(lower(document_id) from 'chapter_([a-z][0-9]+)') IN ({codes})",
        "woollahra served rows fell to no_config although their document names a configured Part")


CHECKS = {"DQ-122": dq122, "DQ-123": dq123, "DQ-124": dq124, "DQ-125": dq125, "DQ-126": dq126}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, choices=sorted(CHECKS))
    args = ap.parse_args()
    rc, msg = CHECKS[args.id]()
    print(f"{args.id}: {msg}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
