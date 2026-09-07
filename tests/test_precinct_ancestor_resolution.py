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


def test_the_nearest_ancestor_wins_over_a_further_one(conn):
    """`ORDER BY length(a.k) DESC` — pinned, not assumed.

    This was recorded as untestable, on the grounds that every inheriting
    POLYGON has exactly one provisioned ancestor. That was true and irrelevant:
    the resolution takes the requested id as a parameter, so the test can ask
    about any id it likes, and only needs two real KEYS in an ancestor chain.

    City of Sydney has fifteen such pairs. '2.13.11' and '2.13' are both live
    keys, so asking about a child of 2.13.11 separates the two rules: nearest
    gives 2.13.11, furthest gives 2.13. The id itself need not exist — nothing
    is written, and no polygon is invented.
    """
    out = resolve(conn, ["2.13.11.99"], "city_of_sydney")
    assert out == {"2.13.11"}, (
        "the NEAREST provisioned ancestor must win. Resolving to 2.13 would "
        "serve a whole village centre's controls to one sub-precinct."
    )


def test_a_non_actionable_key_is_never_inherited(conn):
    """The v2_is_actionable half of the availability filter, on real data.

    Parramatta's '8.4.1' — Special Character Areas, Sylvia Gardens — is a real
    polygon in dcp_precinct_boundaries whose only provision row is
    is_current=TRUE but v2_is_actionable=FALSE. So it is excluded by the
    ACTIONABLE half specifically, and this test is named for that: an earlier
    version called it "superseded", which was simply wrong about which filter
    it was exercising.

    Drop v2_is_actionable from the lookup and 8.4.1 becomes available, so a
    property in Sylvia Gardens is served a non-actionable row that reads exactly
    like a control.
    """
    out = resolve(conn, ["8.4.1"], "parramatta")
    assert "8.4.1" not in out, (
        "8.4.1 has no actionable provisions — resolving to it means the "
        "availability lookup has lost its v2_is_actionable filter"
    )


def test_a_superseded_key_is_never_inherited(conn):
    """The is_current half, which needed a different case entirely.

    Ashfield's 'Ashfield East' is actionable but NOT current — superseded text
    that still parses as a control. Asking about a child of it separates the two
    behaviours: with the currency filter the key is unavailable and nothing is
    inherited; without it, superseded controls are served and look current.

    The child id is synthetic. It does not need to exist — the resolution takes
    the requested id as a parameter, which is the same reframing that made the
    nearest-ancestor ordering testable after it had been written off.
    """
    out = resolve(conn, ["Ashfield East.99"], "ashfield")
    assert "Ashfield East" not in out, (
        "'Ashfield East' is not current — resolving to it means the "
        "availability lookup has lost its is_current filter and superseded "
        "text is being served as live"
    )
