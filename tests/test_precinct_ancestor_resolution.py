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

Skipped by default: conftest_mocks stubs psycopg2, so without the opt-in this
would interrogate a MagicMock and pass on nonsense.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.database

# The resolution exactly as frontend-nextjs/lib/precinct-service.ts issues it.
# Kept verbatim rather than paraphrased: a paraphrase would pass while the
# served query was broken, which is the failure this file exists to prevent.
RESOLVE_SQL = """
WITH requested AS (SELECT unnest(%s::text[]) AS id),
avail AS (
  SELECT DISTINCT v2_precinct_id AS k
  FROM regulatory_provisions
  WHERE source_council = %s AND is_current AND v2_is_actionable
    AND v2_precinct_id IS NOT NULL
),
precinct_keys AS (
  SELECT DISTINCT COALESCE(
    (SELECT a.k FROM avail a WHERE a.k = r.id),
    (SELECT a.k FROM avail a
      WHERE left(r.id, length(a.k) + 1) = a.k || '.'
      ORDER BY length(a.k) DESC LIMIT 1)
  ) AS k
  FROM requested r
)
SELECT r.id,
       (SELECT k FROM precinct_keys pk
         WHERE pk.k IS NOT NULL
           AND (pk.k = r.id OR left(r.id, length(pk.k) + 1) = pk.k || '.')
         ORDER BY length(pk.k) DESC LIMIT 1) AS resolved_key
FROM requested r
"""


@pytest.fixture(scope="module")
def conn():
    if os.environ.get("PYTEST_REAL_DB") != "1":
        pytest.skip("needs PYTEST_REAL_DB=1 — conftest_mocks stubs psycopg2 otherwise")
    from dotenv import load_dotenv

    # .env is gitignored, so it exists ONLY in the main working tree. Run from a
    # worktree it is absent, db_config falls through to its localhost defaults,
    # and the failure surfaces as "server does not support SSL" — which reads as
    # a TLS problem and is really a missing-credentials one. Same trap caught
    # scripts/import_parramatta_part8_boundaries.py.
    env = REPO / ".env"
    if not env.exists():
        env = next(
            (c / ".env" for c in REPO.parents
             if (c / ".env").exists() and (c / "services" / "db_config.py").exists()),
            env,
        )
    load_dotenv(env)
    if not os.getenv("PGHOST") and not os.getenv("DB_HOST"):
        pytest.skip(f"no .env with credentials found from {REPO}")
    for pg, db in (("PGHOST", "DB_HOST"), ("PGUSER", "DB_USER"),
                   ("PGPASSWORD", "DB_PASSWORD"), ("PGDATABASE", "DB_NAME"),
                   ("PGPORT", "DB_PORT")):
        if os.getenv(pg):
            os.environ[db] = os.environ[pg]
    os.environ.setdefault("PGSSLMODE", "require")
    sys.path.insert(0, str(REPO / "services"))
    from db_config import get_connection

    c = get_connection()
    c.set_session(readonly=True, autocommit=True)
    yield c
    c.close()


def resolve(conn, ids: list[str], council: str) -> dict[str, str | None]:
    cur = conn.cursor()
    cur.execute("SET statement_timeout='30s'")
    cur.execute(RESOLVE_SQL, (ids, council))
    return {row[0]: row[1] for row in cur.fetchall()}


def test_finer_polygon_inherits_the_key_its_controls_are_written_against(conn):
    """The defect: Epping Central served nothing."""
    out = resolve(conn, ["8.1.1.1", "8.1.1.2", "8.1.1.3.1"], "parramatta")
    assert out == {"8.1.1.1": "8.1.1", "8.1.1.2": "8.1.1", "8.1.1.3.1": "8.1.1"}, (
        "Epping polygons must inherit 8.1.1 — without this a property in Epping "
        "Central is served no precinct controls at all"
    )


def test_a_precinct_with_its_own_controls_does_not_also_take_its_parents(conn):
    """The dangerous direction, and the one that looks like success.

    Serving a property controls it is not subject to is worse than serving none.
    """
    out = resolve(conn, ["8.2.6", "8.2.2"], "parramatta")
    assert out == {"8.2.6": "8.2.6", "8.2.2": "8.2.2"}


def test_no_provisions_at_any_level_resolves_to_nothing(conn):
    """20 of the 89 polygons are specific sites whose text is not extracted.

    "No controls" is the honest answer; inventing a parent would not be.
    """
    out = resolve(conn, ["8.5.13.9", "8.3.10"], "parramatta")
    assert out == {"8.5.13.9": None, "8.3.10": None}


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
    assert out == {precinct_id: precinct_id}


def test_underscore_ids_are_not_treated_as_wildcards(conn):
    """`left(id, length(k)+1) = k || '.'` rather than `LIKE k || '.%'`.

    Marrickville ids such as '47_' contain an underscore, which LIKE reads as
    "any single character" — '47_.%' would match '470.1', '471.1' and so on.
    Nothing like that exists today, which is exactly why it would go unnoticed.
    """
    out = resolve(conn, ["47_.1"], "marrickville")
    assert out["47_.1"] in (None, "47_"), (
        "a synthetic child of 47_ must resolve to 47_ or to nothing — never to "
        "another precinct reached through a wildcard match"
    )
