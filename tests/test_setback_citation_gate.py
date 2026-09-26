"""A report prints a DCP clause label only when the council's page proves EVERY piece of it.

Migration 077. Pins, each against the code that serves it:
  * citation_proof.unjudged_pieces / prove_label -- a label with a piece the check never
    reads ("Table 1", "Control 4", "(a)") is 'partial', never 'proven';
  * conveyancing_db.fetch_dcp_setbacks -- the one read behind the conveyancing PDF, the Brief,
    the controls card and the parking API -- withholds an unproven clause and its siblings;
  * served_source_ref never borrows ANOTHER row's clause for a row whose own was withheld;
  * granny_flat._fetch_sd_setbacks applies the same gate;
  * scripts/dcp_setback_citation_status.py judges external rows and unreadable PDFs.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import citation_proof as cp  # noqa: E402
import conveyancing_db as cdb  # noqa: E402
import dcp_setback_citation_status as S  # noqa: E402


# -- the rule ------------------------------------------------------------------

@pytest.mark.parametrize("label, left", [
    ("5.2.1 Setbacks C5", []),                 # section + item: both judged
    ("Doc__chap__C4_9", []),
    ("DS5.2", []),
    ("SECTION 3 C12", []),                     # bare section judged against "Section 3"
    ("16 16_1", []),                           # "16" only names the parent of 16.1
    ("B7 5. Table 1", ["5", "1"]),             # split_ref judges B7 only
    ("6.1.2.3 Control 4", ["4"]),
    ("3.7.1 C12 Table 7", ["7"]),
    ("4.1.2(1)", ["1"]),
    ("Doc__chap__C4_9(a)", ["a"]),
    ("3_5_3_2 f)", ["f"]),
])
def test_unjudged_pieces(label, left):
    assert cp.unjudged_pieces(label) == left


def test_a_proven_label_with_an_unchecked_piece_is_partial(monkeypatch):
    monkeypatch.setattr(cp, "prove_citation_any", lambda *a, **k: {"status": "proven", "detail": None})
    assert cp.prove_label("B7 5. Table 1", "x", [])["status"] == "partial"
    assert cp.prove_label("5.2.1 Setbacks C5", "x", [])["status"] == "proven"


def test_a_failed_label_keeps_its_own_reason(monkeypatch):
    monkeypatch.setattr(cp, "prove_citation_any", lambda *a, **k: {"status": "not_proven", "detail": "d"})
    assert cp.prove_label("B7 5. Table 1", "x", [])["status"] == "not_proven"


# -- the served read -------------------------------------------------------------

def _row(section_ref, status, pdf_page=12, dev_type="dwelling_house"):
    # Column order of the SELECT in fetch_dcp_setbacks.
    return (dev_type, "front_setback", 6.0, None, "m", None, "Provide a front setback.",
            section_ref, "universal_residential", False, "part-3", pdf_page, "DCP 2015",
            None, None, None, status)


def _fetch(rows):
    cur = MagicMock()
    cur.fetchall.side_effect = [rows] + [[]] * 5
    cur.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cur
    return cdb.fetch_dcp_setbacks(conn, "woollahra")


@pytest.mark.parametrize("status, shown", [
    ("proven", True), ("imprecise", True), ("external", True),
    ("partial", False), ("not_proven", False), ("text_not_found", False),
    ("unjudged", False), ("no_source", False),
    (None, False),                              # not checked, or 077 not applied: fails closed
])
def test_fetch_dcp_setbacks_shows_a_clause_only_when_proven(status, shown):
    e = _fetch([_row("C2.1", status)])["setbacks"][0]
    assert e["clause_shown"] is shown
    assert (e["clause"] == "C2.1") is shown
    assert e["pdf_page"] == 12                  # the page is always served


def test_select_reads_the_verdict_without_requiring_the_column():
    cur = MagicMock()
    cur.fetchall.side_effect = [[]] + [[]] * 5
    conn = MagicMock()
    conn.cursor.return_value = cur
    cdb.fetch_dcp_setbacks(conn, "woollahra")
    sql = cur.execute.call_args_list[0][0][0]
    assert "to_jsonb(dcp_setback_controls) ->> 'citation_status'" in sql


def test_clause_ref_never_names_a_withheld_clause():
    got = _fetch([_row("C9.9", "not_proven"), _row("C2.1", "proven")])
    assert got["clause_ref"] == "C2.1"
    assert all(e["clause"] != "C9.9" for e in got["setbacks"])


# -- consumers --------------------------------------------------------------------

def test_served_source_ref_gives_the_page_not_another_rows_clause():
    hidden = {"clause": "", "clause_shown": False, "pdf_page": 7}
    assert cdb.served_source_ref(hidden, "C2.1") == "p. 7"
    assert cdb.served_source_ref({**hidden, "pdf_page": None}, "C2.1") is None
    assert cdb.served_source_ref({"clause": "C3", "clause_shown": True, "pdf_page": 7}, "C2.1") == "C3, p. 7"  # noqa: zone-codes (DCP clause labels, not zones)
    # An entry from before 077 (no clause_shown key) keeps the old fallback.
    assert cdb.served_source_ref({"clause": ""}, "C2.1") == "C2.1"


def test_pdf_cell_prints_the_page_when_the_clause_is_withheld():
    assert cdb.clause_or_page("", 30) == "p. 30"
    assert cdb.clause_or_page("C2.1", 30) == "C2.1, p. 30"          # page always, clause when shown
    assert cdb.clause_or_page("C2.1", None) == "C2.1"
    assert cdb.clause_or_page("", None) == ""
    # A sibling-plan citation already names its own page: not added twice.
    assert cdb.clause_or_page("C2.1 — Bowral, p.12. The same clause is in: X", 12).count("p.") == 1


def test_granny_flat_applies_the_same_gate():
    from services.granny_flat import _fetch_sd_setbacks
    row = ("secondary_dwelling", "front_setback", 6.0, None, "m", None, None, "4.2.1",
           "secondary_dwelling_specific", 12)
    for status, want in (("proven", "4.2.1, p. 12"), ("not_proven", "p. 12"), (None, "p. 12")):
        cur = MagicMock()
        cur.fetchall.return_value = [row + (status,)]
        cur.fetchone.return_value = None
        conn = MagicMock()
        conn.cursor.return_value = cur
        assert _fetch_sd_setbacks(conn, "inner_west")["sd_setbacks"][0]["clause"] == want


# -- the writer ------------------------------------------------------------------

def test_writer_judges_external_and_unreadable_rows_without_the_page_check(monkeypatch):
    monkeypatch.setattr(cp, "prove_label", lambda ref, *a, **k: {"status": "proven" if ref == "C2.1" else "not_proven"})

    def readings_for(path):
        if path == "gone.pdf":
            raise FileNotFoundError(path)
        return []

    rows = [
        (1, "nsw_statewide", "adg_part3_visual_privacy", "ADG-3F-1", None, "t", None),
        (2, "hornsby", "_external_lep", "LEP", None, "t", None),
        (3, "woollahra", "part-3", "plan.pdf#C2.1", "ok.pdf", "t", 4),   # label after '#'
        (4, "woollahra", "part-3", "C9.9", "ok.pdf", "t", 4),
        (5, "woollahra", "part-4", "C2.1", "gone.pdf", "t", 4),
        (6, "woollahra", "part-5", "C2.1", None, "t", 4),
    ]
    assert S.judge_rows(rows, readings_for) == {
        1: "external", 2: "external", 3: "proven", 4: "not_proven", 5: "no_source", 6: "no_source"}


def test_writer_refuses_an_unknown_verdict():
    with pytest.raises(ValueError):
        S.plan_updates({1: "maybe"}, {})
    assert S.plan_updates({1: "proven", 2: "partial"}, {1: "proven"}) == [(2, "partial")]


def test_the_shown_set_is_the_same_in_the_writer_and_the_reader():
    assert cdb.CLAUSE_SHOWN_STATUSES <= set(S.STATUSES)
    assert "partial" in S.STATUSES


def test_a_verdict_is_written_only_onto_the_row_it_was_judged_on():
    """A row edited while the writer ran must not receive the old row's verdict (cross-review)."""
    cur = MagicMock()
    cur.rowcount = 1
    conn = MagicMock()
    conn.cursor.return_value = cur
    rows = [(7, "woollahra", "part-3", "C2.1", "ok.pdf", "the words", 12)]
    assert S.write_verdicts(conn, [(7, "proven")], rows) == 1
    sql, params = cur.execute.call_args[0]
    for col in ("lga", "source_chapter_key", "section_ref", "source_text", "pdf_page"):
        assert f"s.{col} IS NOT DISTINCT FROM" in sql
    assert params == ([7], ["proven"], ["woollahra"], ["part-3"], ["C2.1"], ["the words"], [12])


def test_the_outreach_check_does_not_count_see_the_plan_as_a_citation(monkeypatch):
    import outreach_claim_checks as O
    url = "https://example.org/x.pdf"
    base = {"value_min": 6.0, "source_text": "t", "source_chapter_key": "k", "semantic_type": "front_setback"}
    monkeypatch.setattr(O, "registered_instruments", lambda: {None: frozenset()})
    monkeypatch.setattr(O, "is_source_link", lambda u, allowed: True)
    for entry, ok in (({**base, "clause": "C2.1", "clause_shown": True}, True),
                      ({**base, "clause": "", "clause_shown": False, "pdf_page": 12}, True),
                      ({**base, "clause": "", "clause_shown": False, "pdf_page": None}, False)):
        monkeypatch.setattr(O, "served_entries", lambda e=entry: ([("woollahra", e, {"k": url})], ""))
        assert (O.every_served_number_is_cited()[0] == O.PASS) is ok, entry
