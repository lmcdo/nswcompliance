"""The "not heritage" filter must keep rules that have no topic.

Found 2026-09-13: app/api/provisions/for-property/route.ts compared
`LOWER(v2_topic) != 'heritage'`. When v2_topic is NULL that expression is NULL,
not true, so Postgres drops the row -- every untagged rule vanished for every
non-heritage property. Marrickville low-density housing served 186 of its 211
current rules, and one of the missing ones was "4.1.6.3 C13 Maximum site
coverage controls".

The predicate now lives once, in frontend-nextjs/lib/provision-sql-filters.ts.
The database tests below run THAT string, read out of the file, against real
Postgres, so they cannot pass on a lookalike. They need no table data: the rows
are a VALUES list, because what is under test is Postgres's own NULL semantics.

The cross-reviewer's objection is pinned as cases, not argued in prose: an untagged
row from a heritage chapter must stay hidden, and a mixed-case heritage marker must
not slip through. A TAGGED row in a heritage chapter keeps its old behaviour.

Run the database half:
    PYTEST_REAL_DB=1 pytest -m database tests/test_provision_sql_filters.py -o addopts=
"""
import os
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "frontend-nextjs" / "lib" / "provision-sql-filters.ts"
ROUTE = REPO / "frontend-nextjs" / "app" / "api" / "provisions" / "for-property" / "route.ts"

# The predicate as it stood on main before the fix. Kept so the database test can
# show the check discriminates: the old string must fail where the new one passes.
OLD_PREDICATE = (
    "(LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))"
)

# (label, v2_topic, v2_marker, source_chapter_key, should_be_kept)
CASES = [
    ("no topic, no marker", None, None, "part4-s1-low-density", True),
    ("no topic, statewide, no chapter", None, None, None, True),
    ("ordinary topic", "Parking", None, "part2-s10-parking", True),
    ("tagged topic inside a heritage chapter", "Parking", None, "part8-heritage", True),
    ("heritage topic, mixed case", "Heritage", None, "part4-s1-low-density", False),
    ("no topic, heritage marker", None, "heritage", None, False),
    ("no topic, mixed-case heritage marker", None, "Heritage", None, False),
    ("no topic, inside a heritage chapter", None, None, "part8-heritage", False),
]


def shared_predicate() -> str:
    m = re.search(r"export const NOT_HERITAGE_SQL\s*=\s*`([^`]+)`",
                  LIB.read_text(encoding="utf-8"))
    assert m, "NOT_HERITAGE_SQL is no longer a single template literal -- update this reader"
    return m.group(1)


def test_the_route_uses_the_shared_predicate_and_no_bare_copy_remains():
    """Drift guard only. The semantics are proven by the database tests below."""
    src = ROUTE.read_text(encoding="utf-8")
    assert "@/lib/provision-sql-filters" in src and "${NOT_HERITAGE_SQL}" in src
    assert "LOWER(v2_topic) != 'heritage'" not in src, (
        "a hand-copied heritage predicate is back in the route; it drops every rule "
        "with no topic -- use NOT_HERITAGE_SQL"
    )


def test_the_predicate_carries_no_percent_sign():
    """psycopg2 reads '%' as a placeholder. The route uses $n placeholders and would not
    care, but the database test runs this string through psycopg2 -- a '%' would make
    that test error for the wrong reason rather than check anything."""
    assert "%" not in shared_predicate()


def _real_conn():
    if os.environ.get("PYTEST_REAL_DB") != "1":
        pytest.skip("Real-DB test. Run with PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_provision_sql_filters.py -o addopts=")
    from dotenv import load_dotenv
    sys.path.insert(0, str(REPO / "scripts"))
    from dq_db import main_checkout  # a worktree has no .env of its own
    load_dotenv(main_checkout() / ".env")
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        # FAIL, not skip: the run asked for the database explicitly, and a skip exits 0,
        # which reads as the check having passed. (Cross-review finding on this PR.)
        pytest.fail("PYTEST_REAL_DB=1 was set but no DATABASE_URL/SUPABASE_DB_URL is "
                    "available -- an explicitly requested database test must not pass by skipping.")
    import psycopg2
    conn = psycopg2.connect(url, connect_timeout=20)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def _kept_labels(predicate: str) -> set[str]:
    conn = _real_conn()
    try:
        cur = conn.cursor()
        rows = ", ".join(["(%s, %s::text, %s::text, %s::text)"] * len(CASES))
        params = [v for label, topic, marker, chapter, _ in CASES
                  for v in (label, topic, marker, chapter)]
        cur.execute(
            f"SELECT label FROM (VALUES {rows}) "
            f"AS r(label, v2_topic, v2_marker, source_chapter_key) WHERE {predicate}",
            params,
        )
        return {r[0] for r in cur.fetchall()}
    finally:
        conn.close()


@pytest.mark.database
def test_the_shared_predicate_keeps_untagged_rules_and_still_drops_heritage():
    kept = _kept_labels(shared_predicate())
    assert kept == {label for label, _, _, _, keep in CASES if keep}


@pytest.mark.database
def test_the_old_predicate_really_dropped_untagged_rules():
    """The check above can fail: the pre-fix string, run the same way, loses the
    untagged row. It must still keep the ordinary row -- otherwise an empty result
    from a broken query would satisfy the first assertion vacuously."""
    kept = _kept_labels(OLD_PREDICATE)
    assert "no topic, no marker" not in kept
    assert "ordinary topic" in kept
