"""A precinct mapped finer than its text is keyed must still serve its controls.

ORIGIN, 2026-08-20. #990 imported City of Parramatta's 76 council-supplied Part
8 polygons; #992 wired the resolved precinct through to the page. Measured live
against production afterwards:

    precinct_id=8.2.6    -> layer_4_precinct = 50   correct
    precinct_id=8.1.1.1  -> layer_4_precinct =  0   WRONG
    no precinct at all   -> layer_4_precinct =  0

Epping Central returned precisely what a property outside any precinct returns.
The council maps Epping as fifteen polygons (8.1.1.1 … 8.1.1.5.1) and writes
every one of their controls once, against 8.1.1, so exact matching never meets.
22 of 89 City of Parramatta polygons are in that state. #992 could not have
caught it — it measured with 8.2.6, an exact match.

The fix resolves the key inside the provisions query. This file pins the two
directions that matter against the REAL database, because the rule is SQL and a
mock asserting the SQL's text would only confirm the text.

    PYTEST_REAL_DB=1 pytest tests/test_precinct_ancestor_resolution.py -m database

In CI it runs in the schema-contract job, which already holds DATABASE_URL.

Skipped by default: conftest_mocks stubs psycopg2, so without the opt-in this
would interrogate a MagicMock and pass on nonsense.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

import pytest

REPO = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.database

# The resolution is EXTRACTED FROM THE SERVED SOURCE, never copied here.
#
# The first version of this file pasted the SQL in. That is the same
# self-referential trap that let a mutation through earlier in this work: a test
# holding its own copy passes whatever the source does, so breaking the served
# query would leave it green. Reading the source binds the two — and if the
# query is renamed or restructured, extraction fails loudly rather than the test
# quietly validating a string nothing uses.
SERVICE_TS = REPO / "frontend-nextjs" / "lib" / "precinct-service.ts"


def _extract_resolution_sql() -> str:
    """Pull the WITH ... precinct_keys CTE chain out of precinct-service.ts."""
    src = SERVICE_TS.read_text(encoding="utf-8")
    start = src.find("WITH requested AS (")
    if start == -1:
        raise AssertionError(
            f"no 'WITH requested AS (' in {SERVICE_TS.name} — the ancestor-key "
            "resolution has been removed or renamed. If that was deliberate, "
            "this file must be rewritten, not deleted."
        )
    end = src.find("SELECT" + chr(10) + "        rp.id", start)
    if end == -1:
        raise AssertionError(
            "found the CTE chain but not the provisions SELECT that follows it; "
            "the query has been restructured and this extraction needs updating."
        )
    cte = src[start:end].rstrip()
    if "precinct_keys" not in cte or "COALESCE" not in cte:
        raise AssertionError("extracted CTE looks wrong: " + cte[:400])
    # psycopg2 takes %s where node-postgres takes $n. $1 is the requested ids,
    # $2 the council slug, and they appear in that order.
    cte = cte.replace("$1", "%s").replace("$2", "%s")
    # Read precinct_keys straight out. An earlier version re-derived the
    # mapping here with its own ORDER BY length DESC, which re-imposed
    # nearest-first and MASKED a mutation that made the CTE pick the furthest
    # ancestor — the test passed against broken source. A harness that repairs
    # the thing it is measuring is worse than no harness.
    return cte + """
SELECT k FROM precinct_keys
"""


RESOLVE_SQL = _extract_resolution_sql()


@pytest.fixture(scope="module")
def conn():
    """A read-only connection, from DATABASE_URL in CI or .env locally."""
    if os.environ.get("PYTEST_REAL_DB") != "1":
        pytest.skip("needs PYTEST_REAL_DB=1 — conftest_mocks stubs psycopg2 otherwise")

    import psycopg2

    url = os.environ.get("DATABASE_URL")
    if not url:
        from dotenv import load_dotenv

        # .env is gitignored, so it exists ONLY in the main working tree. Run
        # from a worktree it is absent, and the failure surfaces as "server does
        # not support SSL" — which reads as TLS and is really missing
        # credentials. Same trap caught the Parramatta import script.
        env = REPO / ".env"
        if not env.exists():
            env = next(
                (c / ".env" for c in REPO.parents
                 if (c / ".env").exists() and (c / "services" / "db_config.py").exists()),
                env,
            )
        load_dotenv(env)
        if not os.getenv("PGHOST"):
            pytest.skip(f"no DATABASE_URL and no .env with credentials from {REPO}")
        url = (
            f"postgresql://{quote(os.environ['PGUSER'], safe='')}:"
            f"{quote(os.environ['PGPASSWORD'], safe='')}@{os.environ['PGHOST']}:"
            f"{os.environ.get('PGPORT', '5432')}/{os.environ['PGDATABASE']}?sslmode=require"
        )

    c = psycopg2.connect(url)
    c.set_session(readonly=True, autocommit=True)
    yield c
    c.close()


def resolve(conn, ids: list[str], council: str) -> set[str | None]:
    """The set of keys the CTE resolved these ids onto — its own answer, unedited."""
    cur = conn.cursor()
    cur.execute("SET statement_timeout='30s'")
    cur.execute(RESOLVE_SQL, (ids, council))
    return {row[0] for row in cur.fetchall()}


def test_finer_polygon_inherits_the_key_its_controls_are_written_against(conn):
    """The defect: Epping Central served nothing."""
    out = resolve(conn, ["8.1.1.1", "8.1.1.2", "8.1.1.3.1"], "parramatta")
    # All three collapse onto the one key their controls are written against.
    assert out == {"8.1.1"}, (
        "Epping polygons must inherit 8.1.1 — without this a property in Epping "
        "Central is served no precinct controls at all"
    )


def test_a_precinct_with_its_own_controls_does_not_also_take_its_parents(conn):
    """The dangerous direction, and the one that looks like success.

    Serving a property controls it is not subject to is worse than serving none.
    """
    out = resolve(conn, ["8.2.6", "8.2.2"], "parramatta")
    assert out == {"8.2.6", "8.2.2"}, (
        "each keeps its own key; neither 8.2 nor 8 may appear"
    )


def test_no_provisions_at_any_level_resolves_to_nothing(conn):
    """20 of the 89 polygons are specific sites whose text is not extracted.

    "No controls" is the honest answer; inventing a parent would not be.
    """
    out = resolve(conn, ["8.5.13.9", "8.3.10"], "parramatta")
    assert out == {None}, "neither has text at any level, so nothing is served"


@pytest.mark.parametrize(
    "precinct_id,council",
    [
        ("Part 1", "ashfield"),       # 165 provisions, no dots
        ("47_", "marrickville"),      # underscore: a LIKE wildcard if LIKE were used
        ("G6", "leichhardt"),         # 187 provisions
        ("2.5.8", "city_of_sydney"),  # dotted, but exact
    ],
)
def test_other_councils_resolve_to_themselves_unchanged(conn, precinct_id, council):
    """Containment. Sydney, Inner West, Ku-ring-gai, Waverley and Woollahra all
    match exactly today — 259 polygons — so this change must be invisible to
    them. If one of these starts inheriting, the fix has stopped being contained.
    """
    out = resolve(conn, [precinct_id], council)
    assert out == {precinct_id}


def test_underscore_ids_are_not_treated_as_wildcards(conn):
    """`left(id, length(k)+1) = k || '.'` rather than `LIKE k || '.%'`.

    Marrickville ids such as '47_' contain an underscore, which LIKE reads as
    "any single character" — '47_.%' would match '470.1', '471.1' and so on.
    Nothing like that exists today, which is exactly why it would go unnoticed.
    """
    out = resolve(conn, ["47_.1"], "marrickville")
    assert out <= {None, "47_"}, (
        "a synthetic child of 47_ must resolve to 47_ or to nothing — never to "
        "another precinct reached through a wildcard match"
    )


def test_nearest_ancestor_ordering_is_still_unobservable(conn):
    """A canary, not a check — and it is here because the check is impossible.

    `ORDER BY length(a.k) DESC` in the resolution picks the NEAREST provisioned
    ancestor. Mutating it to ASC changes nothing today: measured 2026-08-23,
    every inheriting polygon in every council has exactly ONE provisioned
    ancestor, so both orderings select the same key. The mutation survives, and
    saying "covered" would be a lie.

    So this asserts the PRECONDITION instead. The day a polygon gains a second
    provisioned ancestor, the ordering starts deciding real output and this
    fails — telling whoever is here that it has become testable and must be
    pinned properly, rather than leaving a silent gap that nobody revisits.
    """
    cur = conn.cursor()
    cur.execute("SET statement_timeout='30s'")
    cur.execute("""
        WITH poly AS (
          SELECT b.precinct_id,
                 lower(coalesce(b.former_council, replace(b.lga, '-', '_'))) AS council
          FROM dcp_precinct_boundaries b
        ),
        keys AS (
          SELECT DISTINCT lower(source_council) AS council, v2_precinct_id AS k
          FROM regulatory_provisions
          WHERE is_current AND v2_is_actionable AND v2_precinct_id IS NOT NULL
        )
        SELECT p.precinct_id, string_agg(k.k, ', ' ORDER BY length(k.k) DESC)
        FROM poly p
        JOIN keys k ON k.council = p.council
                   AND left(p.precinct_id, length(k.k) + 1) = k.k || '.'
        GROUP BY p.precinct_id
        HAVING count(*) > 1
    """)
    multi = cur.fetchall()
    assert multi == [], (
        "A polygon now has more than one provisioned ancestor, so nearest-vs-"
        "furthest decides which controls are served and is no longer untestable:\n  "
        + "\n  ".join(f"{pid} -> {anc}" for pid, anc in multi)
        + "\nAdd a case pinning that the NEAREST is chosen, then delete this canary."
    )
