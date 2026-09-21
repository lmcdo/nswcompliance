"""A bare % inside parameterised psycopg2 SQL is read as a placeholder.

conveyancing_db.fetch_dcp_setbacks carried the SQL comment "-- ... discarded 60% of
them." in its registry link-map query from 2026-08-26 (#1012). psycopg2 formats the
whole string, comments included, so every call raised IndexError("tuple index out of
range"); the surrounding except logged it and returned an empty map, and every numeric
control was served with no PDF link. Nothing failed visibly.

This scans every ``<cursor>.execute(<string literal>, <params>)`` in the served and
script code and fails on a % that is not a ``%s`` / ``%(name)s`` placeholder or a
``%%`` escape. Calls without params are skipped (psycopg2 does not format them), as
are sqlite ``?`` queries. f-string SQL is not a literal and is not scanned.

prior-art-checked: no test in tests/ inspects SQL literals for placeholder hazards
(grep for "execute" together with "%%" or "placeholder" found none).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

REPO = Path(__file__).resolve().parents[1]
ROOTS = ("scripts", "services", "src", "enrichment")
# After removing %% escapes, every remaining % must open a complete psycopg2
# placeholder: %s or %(name)s. %(name), %()s and %(name)d all raise at execute().
BARE_PERCENT = re.compile(r"%(?!s|\(\w+\)s)")

sys.path.insert(0, str(REPO / "scripts"))
from conveyancing_db import fetch_dcp_setbacks  # noqa: E402


def stray_percents(source: str) -> list[tuple[int, str]]:
    """Return (line, excerpt) for each bare % in a parameterised execute() literal."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("execute", "executemany") and len(node.args) >= 2):
            continue
        sql_node, params = node.args[0], node.args[1]
        if not (isinstance(sql_node, ast.Constant) and isinstance(sql_node.value, str)):
            continue
        if isinstance(params, ast.Constant) and params.value is None:
            continue
        sql = sql_node.value
        if "?" in sql and "%s" not in sql and "%(" not in sql:
            continue  # sqlite paramstyle: % is literal there
        unescaped = sql.replace("%%", "")
        for m in BARE_PERCENT.finditer(unescaped):
            found.append((node.lineno, unescaped[max(0, m.start() - 40): m.start() + 10].strip()))
    return found


def test_no_stray_percent_in_parameterised_sql() -> None:
    hits = []
    for root in ROOTS:
        for path in sorted((REPO / root).rglob("*.py")):
            if "archive" in path.parts:
                continue
            for line, excerpt in stray_percents(path.read_text(encoding="utf-8", errors="replace")):
                hits.append(f"{path.relative_to(REPO)}:{line}: {excerpt!r}")
    assert hits == [], "bare % in parameterised SQL (use %% or move the comment out):\n" + "\n".join(hits)


def test_detector_flags_the_original_defect() -> None:
    src = ('cur.execute("""\n'
           '    -- r2_public_pdf_url IS NOT NULL discarded 60% of them.\n'
           '    SELECT chapter_key FROM dcp_chapter_registry WHERE council = %s\n'
           '""", (lga_slug,))\n')
    assert len(stray_percents(src)) == 1


def test_detector_flags_like_wildcard_with_params() -> None:
    src = "cur.execute(\"SELECT id FROM t WHERE name LIKE '%Road%' AND lga = %s\", (lga,))"
    assert len(stray_percents(src)) == 2


def test_detector_flags_malformed_named_placeholders() -> None:
    src = ("cur.execute(\"SELECT 1 FROM t WHERE a = %(name)\", params)\n"
           "cur.execute(\"SELECT 1 FROM t WHERE a = %()s\", params)\n"
           "cur.execute(\"SELECT 1 FROM t WHERE a = %(name)d\", params)\n")
    assert len(stray_percents(src)) == 3


def test_detector_allows_escapes_and_placeholders() -> None:
    src = ("cur.execute(\"SELECT 1 FROM t WHERE a ILIKE 'Item%%' AND b = %s AND c = %(c)s\", params)\n"
           "cur.executemany(\"INSERT INTO t VALUES (%s, %s)\", rows)\n")
    assert stray_percents(src) == []


def test_fetch_dcp_setbacks_link_map_survives_real_parameter_formatting() -> None:
    """The served function, run through a cursor that formats SQL the way psycopg2 does.

    The existing fetch_dcp_setbacks tests use a MagicMock cursor whose execute() ignores
    the SQL, which is why a query that could never run passed them for 18 days. Here any
    parameterised statement is %-formatted first, so a stray % raises exactly as it did
    in production and the link map comes back empty.
    """
    def psycopg2_like_execute(sql, params=None):
        if params is not None:
            sql % tuple("'x'" for _ in params)  # raises on a bare % anywhere in the string

    cur = MagicMock()
    cur.execute.side_effect = psycopg2_like_execute
    cur.fetchall.side_effect = [
        [("dwelling_house", "front_setback", 4.5, None, "m", "", "Provide a front setback.",
          "A-1.1", "general", False, "part-3-residential", 12, "v2022-current", None, None, None)],
        [("part-3-residential", "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/x.pdf")],
    ]
    cur.fetchone.return_value = ("https://example.gov.au/dcp",)
    conn = MagicMock()
    conn.cursor.return_value = cur

    result = fetch_dcp_setbacks(conn, "penrith", "R2 Low Density")

    assert result is not None and result["setbacks"]
    # "_external_lep" is the council's registered LEP landing page, added 2026-09-21.
    # A control sourced from a state instrument has no dcp_chapter_registry row on
    # purpose -- an LEP is not one of the council's DCP chapters -- so without this it
    # resolved to no source link at all and OC-8 went CONTRADICTED the moment a
    # NUMBERED one existed. The fetchone above stands in for instrument_registry.
    assert result["registry_pdf_urls"] == {
        "part-3-residential": "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/x.pdf",
        "_external_lep": "https://example.gov.au/dcp",
    }


def test_no_registered_instrument_means_no_invented_lep_link() -> None:
    """The confusable negative. A council with no instrument_registry row must get NO
    _external_lep key, not a guessed one: a fabricated legislation link is worse than
    an absent one, because it looks like a citation and opens the wrong law."""
    def psycopg2_like_execute(sql, params=None):
        if params is not None:
            sql % tuple("'x'" for _ in params)

    cur = MagicMock()
    cur.execute.side_effect = psycopg2_like_execute
    cur.fetchall.side_effect = [
        [("dwelling_house", "front_setback", 4.5, None, "m", "", "Provide a front setback.",
          "A-1.1", "general", False, "part-3-residential", 12, "v2022-current", None, None, None)],
        [("part-3-residential", "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/x.pdf")],
    ]
    cur.fetchone.return_value = None          # nothing registered for this council
    conn = MagicMock()
    conn.cursor.return_value = cur

    result = fetch_dcp_setbacks(conn, "penrith", "R2 Low Density")

    assert result is not None
    assert "_external_lep" not in result["registry_pdf_urls"]


def test_detector_skips_calls_psycopg2_does_not_format() -> None:
    src = ("cur.execute(\"SELECT '50%' AS share\")\n"
           "cur.execute(\"SELECT '50%' AS share\", None)\n"
           "cur.execute(\"SELECT id FROM t WHERE a LIKE '%x%' LIMIT ?\", (5,))\n")
    assert stray_percents(src) == []
