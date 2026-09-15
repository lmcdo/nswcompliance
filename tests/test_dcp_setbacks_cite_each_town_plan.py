"""A served Wingecarribee number cites every town plan that publishes its clause, from the database.

prior-art-checked: tests/test_cite_clause.py covers the wording of cite_clause; tests/test_conveyancing_dcp_needs_review.py
fakes fetch_dcp_setbacks with one canned result for every query, which cannot tell the sibling-citation read apart.
This fake answers each query by the table it names, so it can hand fetch_dcp_setbacks the sibling rows, or fail that
one read, and check what the served entry says.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from conveyancing_db import fetch_dcp_setbacks  # noqa: E402

BOWRAL = "wingecarribee-bowral-town-plan"
REF = "part-c-s2/C2.13.2(a)-Table-C2.2"
SIBLINGS = [
    (BOWRAL, REF, "Bowral Town Plan (as amended 23 Sep 2015)", "Mittagong Town Plan (as amended 17 Jun 2015)",
     "part-c-s2/C2.13.2(a)-Table-C2.1", 195, "https://r2/mittagong.pdf"),
    (BOWRAL, REF, "Bowral Town Plan (as amended 23 Sep 2015)", "Moss Vale Town Plan (as amended 17 Jun 2015)",
     "part-c-s2/C2.13.2(a)-Table-C2.1", 200, "https://r2/moss-vale.pdf"),
]


def _row(section_ref=REF, chapter=BOWRAL):
    # Column order of the SELECT in fetch_dcp_setbacks.
    return ("dwelling_house", "landscaping_min", 35, None, "%", None,
            "Table C2.2: Lot size less than 2,000m2 — minimum Private Landscaped Open Space 35% of the site area",
            section_ref, "development_specific", False, chapter, 200, "v1.0", None, None, None)


class _Cursor:
    def __init__(self, rows, siblings, sibling_read_fails=False):
        self.rows, self.siblings, self.fails = rows, siblings, sibling_read_fails
        self.sql = ""

    def execute(self, sql, params=None):
        self.sql = sql
        if "dcp_clause_sibling_citations" in sql and self.fails:
            raise RuntimeError('relation "dcp_clause_sibling_citations" does not exist')

    def fetchall(self):
        if "dcp_setback_controls" in self.sql:
            return list(self.rows)
        if "dcp_clause_sibling_citations" in self.sql:
            return list(self.siblings)
        if "dcp_chapter_registry" in self.sql:
            return [(BOWRAL, "https://r2/bowral.pdf")]
        return []

    def fetchone(self):
        return None

    def close(self):
        pass


class _Conn:
    def __init__(self, cur):
        self.cur = cur

    def cursor(self):
        return self.cur

    def rollback(self):
        pass


def _entry(cur, lga="wingecarribee"):
    result = fetch_dcp_setbacks(_Conn(cur), lga, "R2")
    assert result is not None and result["setbacks"], "the control was not served"
    return result["setbacks"][0]


def test_a_number_cites_all_three_town_plans_each_at_its_own_page():
    entry = _entry(_Cursor([_row()], SIBLINGS))
    for plan in ("Bowral Town Plan", "Mittagong Town Plan", "Moss Vale Town Plan"):
        assert plan in entry["clause"], f"{plan} missing from the served citation"
    assert "Table-C2.1, p.195" in entry["clause"] and "p.200" in entry["clause"]
    assert [(a["plan"][:9], a["pdf_page"], a["url"]) for a in entry["also_cited"]] == [
        ("Mittagong", 195, "https://r2/mittagong.pdf"), ("Moss Vale", 200, "https://r2/moss-vale.pdf")]


def test_an_unreadable_sibling_table_still_says_the_plan_covers_one_town():
    """A failed read must not silently leave the number citing Bowral alone, and must not stop it being served."""
    entry = _entry(_Cursor([_row()], SIBLINGS, sibling_read_fails=True))
    assert "table numbers differ" in entry["clause"]
    assert entry["also_cited"] == []


def test_a_sibling_citation_for_another_clause_is_not_borrowed():
    """Confusable negative: citations are matched on the row's own clause, not on the plan alone."""
    entry = _entry(_Cursor([_row(section_ref="part-c-s2/C2.6.2(e)")], SIBLINGS))
    assert entry["also_cited"] == []
    assert "Mittagong Town Plan (as amended" not in entry["clause"]


def test_a_council_with_one_plan_is_unchanged():
    entry = _entry(_Cursor([_row(section_ref="C3.2", chapter="part-c")], []), lga="ashfield")
    assert entry["clause"] == "C3.2" and entry["also_cited"] == []
