"""Every reader of housing_sepp_standards must handle the path-specific rules.

Migrations 083/084 add rows tagged with an approval_pathway (cdc/da). Some carry
wording and no number; band rules only make sense with their lot-area limits. A
reader that selects every row would crash on float(None) or show bare thresholds
on a public page. Found the hard way on PR #1239: three such readers (the
/planning-standards page, the housing-sepp/eligibility route and the coverage
count) were missed by a manual search and only caught by a production check.

So the inventory is a test. Every query on the table, in any language, must
either
  - filter `approval_pathway` (IS NULL to skip them, or read them on purpose), or
  - select fixed standard types (`standard_type =` / `standard_type IN`) that no
    path rule uses, or
  - be one of the named path-aware readers below, each with its reason.
A new reader that does none of these fails here before it can reach production.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN = ["services", "scripts", "deploy", "frontend-nextjs/app", "frontend-nextjs/lib", "src", "enrichment"]
SKIP_PARTS = {"node_modules", ".next", "archive", "__pycache__", "tests", "__tests__"}
QUERY_RE = re.compile(r"(?:FROM|JOIN)\s+housing_sepp_standards\b", re.IGNORECASE)
SAFE_RE = re.compile(r"approval_pathway|standard_type\s*(?:=|IN\b)", re.IGNORECASE)
WINDOW = 700  # characters of code either side of FROM/JOIN: the query and its filter
IS_QUERY_RE = re.compile(r"\bSELECT\b", re.IGNORECASE)  # prose that names the table is not a query

# Readers that handle path rules by design, each with the reason.
PATH_AWARE = {
    "services/secondary_dwelling_paths.py": "the engine for path rules; validates every one",
    "deploy/flyio-legislation-monitor/secondary_dwelling_paths.py": "byte-identical deployed copy of the above",
    "scripts/provenance_check.py": "traces every quoted rule, path rules included, to its clause",
    "deploy/flyio-legislation-monitor/provenance_check.py": "byte-identical deployed copy of the above",
    "scripts/dq_probe_live.py": "DQ-96 counts rows predating an amendment; new path rows are created after it",
}


def _readers():
    for top in SCAN:
        base = ROOT / top
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if f.suffix not in (".py", ".ts", ".tsx", ".js") or SKIP_PARTS & set(f.parts):
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for m in QUERY_RE.finditer(text):
                before = text[max(0, m.start() - WINDOW):m.start()]
                if not IS_QUERY_RE.search(before):
                    continue  # a comment or docstring naming the table, not a SELECT
                rel = f.relative_to(ROOT).as_posix()
                yield rel, text[:m.start()].count("\n") + 1, before + text[m.start():m.start() + WINDOW]


def test_the_scan_finds_the_known_readers():
    # Guard the guard: if the scan stopped finding readers, every test below would pass on nothing.
    found = {rel for rel, _, _ in _readers()}
    for known in ("services/granny_flat.py", "scripts/conveyancing_db.py",
                  "frontend-nextjs/app/planning-standards/page.tsx"):
        assert known in found, f"scan no longer finds {known}"


def test_every_reader_handles_path_specific_rules():
    unsafe = [f"{rel}:{line}" for rel, line, sql in _readers()
              if rel not in PATH_AWARE and not SAFE_RE.search(sql)]
    assert not unsafe, (
        "These queries read housing_sepp_standards without filtering approval_pathway or fixing "
        "standard_type, so they would serve path-specific rules (wording rows, band thresholds) "
        "as if they were flat standards:\n  " + "\n  ".join(unsafe)
    )


def test_path_aware_list_has_no_stale_entries():
    found = {rel for rel, _, _ in _readers()}
    stale = sorted(set(PATH_AWARE) - found)
    assert not stale, f"PATH_AWARE names files that no longer read the table: {stale}"
