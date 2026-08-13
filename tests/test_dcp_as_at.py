"""Campaign item 3 — per-source "as at" dates on served DCP claims.

What must hold:
  - wording is basis-appropriate and language-ladder compliant (stated /
    observed; never "verified"),
  - precision honesty: a month-precision date must never render a day,
  - authority order portal > stated > observed, three states (date / checked-
    none / lookup-failed) — and a failed as-at lookup must not take the
    controls down with it,
  - no date is ever parsed from a bare year label (the retired-parser class).

Mutation notes: swapping the authority order fails test_portal_beats_stated;
ignoring precision fails test_month_precision_never_renders_a_day; parsing
labels fails test_bare_year_is_never_a_date; letting the as-at query raise
through fails test_as_at_failure_does_not_kill_controls.
"""
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from conveyancing_db import (  # noqa: E402
    _plan_as_at,
    fetch_dcp_setbacks,
    format_as_at_line,
)
from extract_dcp_stated_dates import _STATEMENTS  # noqa: E402
from fetch_dcp_as_at_dates import (  # noqa: E402
    parse_dated_phrase,
    pick_dcp_result,
    resolve_portal_dates,
)


# ---------------------------------------------------------------------------
# format_as_at_line — the single wording source
# ---------------------------------------------------------------------------

class TestAsAtWording:
    def test_portal_amended_day(self):
        line = format_as_at_line({"date": "2022-09-09", "precision": "day",
                                  "kind": "amended", "basis": "portal_plan_record"})
        assert line == ("As amended 9 September 2022 "
                        "(date stated in the NSW Planning Portal plan record)")

    def test_stated_effective_day(self):
        line = format_as_at_line({"date": "2020-09-08", "precision": "day",
                                  "kind": "effective", "basis": "stated_in_document"})
        assert line == "In force from 8 September 2020 (date stated in the plan document)"

    def test_stated_adopted(self):
        line = format_as_at_line({"date": "2013-05-28", "precision": "day",
                                  "kind": "adopted", "basis": "stated_in_document"})
        assert line == "Adopted 28 May 2013 (date stated in the plan document)"

    def test_observed_wording_claims_only_the_stored_fact(self):
        """A URL check cannot establish that the plan is the CURRENT
        published version (a superseding amendment can live at another URL) —
        the wording claims only the check itself."""
        line = format_as_at_line({"date": "2026-08-01", "precision": "day",
                                  "kind": None, "basis": "observed_current"})
        assert line == ("All registered source documents for this plan were "
                        "last checked on or after 1 August 2026; an in-force "
                        "date is not available")
        assert "current" not in line.lower()

    def test_month_precision_never_renders_a_day(self):
        """A month-precision date stored as the 1st must not gain a day."""
        line = format_as_at_line({"date": "2026-03-01", "precision": "month",
                                  "kind": "amended", "basis": "stated_in_document"})
        assert "March 2026" in line
        assert "1 March" not in line

    def test_year_precision_renders_year_only(self):
        line = format_as_at_line({"date": "2015-01-01", "precision": "year",
                                  "kind": "effective", "basis": "stated_in_document"})
        assert "2015" in line
        assert "January" not in line

    def test_language_ladder_no_banned_words(self):
        for payload in (
            {"date": "2022-09-09", "precision": "day", "kind": "amended",
             "basis": "portal_plan_record"},
            {"date": "2026-08-01", "precision": "day", "kind": None,
             "basis": "observed_current"},
        ):
            line = format_as_at_line(payload).lower()
            for banned in ("verified", "confirmed", "guaranteed", "certified"):
                assert banned not in line

    @pytest.mark.parametrize("payload", [
        None,
        {},
        {"date": None, "precision": "day", "basis": "stated_in_document"},
        {"date": "2022-09-09", "precision": "day", "kind": "amended", "basis": "invented_basis"},
        {"date": "not-a-date", "precision": "day", "kind": "amended", "basis": "stated_in_document"},
    ])
    def test_no_line_without_a_defensible_payload(self, payload):
        assert format_as_at_line(payload) is None


# ---------------------------------------------------------------------------
# _plan_as_at — authority order and failure states
# ---------------------------------------------------------------------------

def _cur(row):
    cur = MagicMock()
    cur.fetchone.return_value = row
    return cur


FULL = ("2022-09-09", "day", "amended",     # portal
        "2020-09-08", "day", "effective",   # stated (conflicts with portal)
        "2026-08-01")                        # observed
PORTAL_ONLY = ("2022-09-09", "day", "amended",
               None, None, None, "2026-08-01")


class TestPlanAsAtAuthorityOrder:
    def test_portal_wins_when_stated_absent(self):
        got = _plan_as_at(_cur(PORTAL_ONLY), "x")
        assert got["basis"] == "portal_plan_record"
        assert got["date"] == "2022-09-09"

    def test_conflicting_portal_and_stated_render_nothing(self):
        """A portal date contradicting the document's own statement is a
        conflict to adjudicate, never a pick-one — no date renders (the
        check script surfaces the disagreement)."""
        assert _plan_as_at(_cur(FULL), "x") is None

    def test_matching_portal_and_stated_serve_portal_basis(self):
        row = ("2022-09-09", "day", "amended",
               "2022-09-09", "day", "effective", "2026-08-01")
        got = _plan_as_at(_cur(row), "x")
        assert got["basis"] == "portal_plan_record"

    def test_stated_beats_observed(self):
        row = (None, None, None) + FULL[3:]
        got = _plan_as_at(_cur(row), "x")
        assert got["basis"] == "stated_in_document"
        assert got["date"] == "2020-09-08"

    def test_observed_is_the_last_resort(self):
        row = (None,) * 6 + ("2026-08-01",)
        got = _plan_as_at(_cur(row), "x")
        assert got == {"date": "2026-08-01", "precision": "day", "kind": None,
                       "basis": "observed_current"}

    def test_nothing_defensible_is_none_not_a_guess(self):
        assert _plan_as_at(_cur((None,) * 7), "x") is None

    def test_wrong_arity_row_is_none(self):
        """The conveyancing test harness returns 1-tuples for every fetchone;
        a malformed row must degrade to no-date, never raise or misread."""
        assert _plan_as_at(_cur(("https://example.gov.au",)), "x") is None

    def test_no_row_is_none(self):
        assert _plan_as_at(_cur(None), "x") is None


# ---------------------------------------------------------------------------
# fetch_dcp_setbacks integration — the as-at must not endanger the controls
# ---------------------------------------------------------------------------

def _control_row(section_ref="A-1.1"):
    return ("dwelling_house", "front_setback", 4.5, None, "m", "",
            "Provide a front setback.", section_ref, "general", False,
            "part_3", 12, "v2022-current")


class TestFetchDcpSetbacksAsAt:
    def test_as_at_line_present_when_lookup_resolves(self):
        cur = MagicMock()
        cur.fetchall.return_value = [_control_row()]
        cur.fetchone.side_effect = [("https://example.gov.au/dcp",), PORTAL_ONLY]
        conn = MagicMock()
        conn.cursor.return_value = cur
        result = fetch_dcp_setbacks(conn, "waverley", "R2 Low Density")
        assert result["as_at"]["basis"] == "portal_plan_record"
        assert result["as_at_status"] == "resolved"
        assert result["as_at_line"].startswith("As amended 9 September 2022")

    def test_as_at_failure_does_not_kill_controls_and_is_disclosed(self):
        """The as-at is provenance FOR the controls; its query failing must
        degrade to a VISIBLE could-not-be-retrieved disclosure — typed as
        'unavailable', never mistakable for 'checked, none exists' — while
        the controls still serve. And the failure must roll back only to the
        probe's savepoint, never the caller's transaction."""
        executed = []

        def flaky_execute(sql, *a, **k):
            executed.append(sql)
            if "dcp_plan_as_at" in sql:
                raise RuntimeError("as-at lookup down")

        cur = MagicMock()
        cur.execute.side_effect = flaky_execute
        cur.fetchall.return_value = [_control_row()]
        cur.fetchone.return_value = ("https://example.gov.au/dcp",)
        conn = MagicMock()
        conn.cursor.return_value = cur
        result = fetch_dcp_setbacks(conn, "waverley", "R2 Low Density")
        assert result is not None
        assert result["setbacks"]
        assert result["as_at"] is None
        assert result["as_at_status"] == "unavailable"
        assert "could not be retrieved" in result["as_at_line"]
        assert any("ROLLBACK TO SAVEPOINT" in s for s in executed)
        conn.rollback.assert_not_called()

    def test_checked_absence_renders_no_line_and_is_typed_absent(self):
        cur = MagicMock()
        cur.fetchall.return_value = [_control_row()]
        cur.fetchone.side_effect = [("https://example.gov.au/dcp",),
                                    (None,) * 7,
                                    # Fourth basis added 2026-08-13: the
                                    # earliest capture date for this council's
                                    # served controls. None here means even
                                    # that found nothing, which must still type
                                    # as "checked, absent" and NOT slide into
                                    # "source unavailable" — the DQ-36 class.
                                    (None,)]
        conn = MagicMock()
        conn.cursor.return_value = cur
        result = fetch_dcp_setbacks(conn, "waverley", "R2 Low Density")
        assert result["as_at"] is None
        assert result["as_at_status"] == "absent"
        assert result["as_at_line"] is None

    def test_extraction_date_is_used_when_no_plan_date_exists(self):
        """The fourth basis: no commencement date, but we know which published
        version we read and when. That answers a different question — how stale
        our copy might be — and it must never be worded as "in force since"."""
        cur = MagicMock()
        cur.fetchall.return_value = [_control_row()]
        cur.fetchone.side_effect = [("https://example.gov.au/dcp",),
                                    (None,) * 7,
                                    ("2026-05-10",)]
        conn = MagicMock()
        conn.cursor.return_value = cur
        result = fetch_dcp_setbacks(conn, "waverley", "R2 Low Density")
        assert result["as_at"] is not None, "an extraction date was available"
        assert result["as_at"]["basis"] == "extracted_from_published"
        assert result["as_at"]["date"] == "2026-05-10"
        assert result["as_at_status"] != "absent"
        # `or ""` here would let the test pass with NO line rendered at all -
        # it would check only that wrong wording is absent, not that anything is
        # present. Sol's cross-review caught exactly that. Assert presence FIRST.
        line = result.get("as_at_line")
        assert line, "no as_at line rendered at all - the basis is not reaching the output"
        # The date is rendered human-readable, not ISO, so compare against the
        # same formatter the code uses rather than hardcoding a format that a
        # later change would silently break.
        from conveyancing_db import _format_as_at_date
        shown = _format_as_at_date("2026-05-10", "day")
        assert shown and shown in line, f"the date itself must appear: {line!r}"
        assert "in force" not in line.lower(), (
            "the extraction date must not be rendered as a commencement claim"
        )


# ---------------------------------------------------------------------------
# Portal date parsing — explicit phrases only, never labels
# ---------------------------------------------------------------------------

class TestPortalDateParsing:
    def test_amended_day_phrase(self):
        got = parse_dated_phrase("Ashfield DCP 2016 - as amended 9 September 2022_S-5507.pdf")
        assert got[0:3] == ("2022-09-09", "day", "amended")

    def test_amended_month_phrase_is_month_precision(self):
        got = parse_dated_phrase("Sydney DCP 2012 (amended March 2026)")
        assert got[0:3] == ("2026-03-01", "month", "amended")

    def test_bare_year_is_never_a_date(self):
        """'Goulburn Mulwaree DCP 2009' is a label, not a date — the retired
        version-parser class. Parsing it would manufacture 2009-01-01."""
        assert parse_dated_phrase("Goulburn Mulwaree DCP 2009") is None

    def test_impossible_date_is_rejected(self):
        assert parse_dated_phrase("as amended 31 February 2022") is None

    def test_empty_and_none_are_none(self):
        assert parse_dated_phrase("") is None

    def test_name_url_date_conflict_refuses(self):
        """A planName date disagreeing with the planURL's date is recorded,
        never attached — the URL can carry the newer amendment."""
        hit, source, conflict = resolve_portal_dates(
            "Example DCP 2020 (amended March 2024)",
            "https://x/Example+DCP+as+amended+5+June+2025.pdf")
        assert hit is None
        assert conflict is not None and "conflicts" in conflict

    def test_name_url_agreement_attaches(self):
        hit, source, conflict = resolve_portal_dates(
            "Example DCP (as amended 9 September 2022)",
            "https://x/Example+DCP+as+amended+9+September+2022.pdf")
        assert conflict is None
        assert hit[0] == "2022-09-09"
        assert source == "planName"

    def test_url_only_date_attaches_from_url(self):
        hit, source, conflict = resolve_portal_dates(
            "Example DCP 2016",
            "https://x/Example+DCP+as+amended+9+September+2022.pdf")
        assert conflict is None
        assert hit[0] == "2022-09-09"
        assert source == "planURL"


# ---------------------------------------------------------------------------
# Portal plan selection — anchored to the served identity
# ---------------------------------------------------------------------------

class TestPickDcpResult:
    SYD = [{"planName": "Sydney Development Control Plan 2012"},
           {"planName": "Sydney Development Control Plan 2012 - Green Square"},
           {"planName": "City of Sydney Late Night Trading DCP"}]

    def test_exact_identity_beats_site_specific_supersets(self):
        chosen, err = pick_dcp_result(["Sydney DCP 2012"], self.SYD)
        assert err is None
        assert chosen["planName"] == "Sydney Development Control Plan 2012"

    def test_identity_mismatch_is_a_finding_not_a_pick(self):
        """Hornsby class: we serve the 2024 plan; the portal lists only the
        2013 one. No date may attach across that mismatch."""
        chosen, err = pick_dcp_result(
            ["Hornsby DCP 2024"],
            [{"planName": "Hornsby Development Control Plan 2013"}])
        assert chosen is None
        assert "IDENTITY MISMATCH" in err

    def test_latest_registry_year_wins(self):
        chosen, err = pick_dcp_result(
            ["Waverley DCP 2012", "Waverley DCP 2022"],
            [{"planName": "Waverley Development Control Plan 2012"},
             {"planName": "Waverley Development Control Plan 2022"}])
        assert err is None
        assert chosen["planName"].endswith("2022")

    def test_empty_results_fail(self):
        chosen, err = pick_dcp_result(["X DCP 2020"], [])
        assert chosen is None


# ---------------------------------------------------------------------------
# Stated-statement patterns (extractor)
# ---------------------------------------------------------------------------

class TestStatedPatterns:
    @pytest.mark.parametrize("line,expected", [
        ("In Force 6 May 2022", date(2022, 5, 6)),
        ("In force: 8 September 2020", date(2020, 9, 8)),
        ("Effective: 5 March 2026", date(2026, 3, 5)),
        ("...Development Control Plan 2015 Effective:11/03/16", date(2016, 3, 11)),
        ("This Development Control Plan came into effect on 22 August 2024.", date(2024, 8, 22)),
    ])
    def test_survey_statements_parse(self, line, expected):
        for pat, _kind in _STATEMENTS:
            m = pat.search(line)
            if m:
                g = m.groups()
                if g[1].lower() in {"january", "february", "march", "april",
                                    "may", "june", "july", "august",
                                    "september", "october", "november",
                                    "december"}:
                    months = ["january", "february", "march", "april", "may",
                              "june", "july", "august", "september",
                              "october", "november", "december"]
                    got = date(int(g[2]), months.index(g[1].lower()) + 1, int(g[0]))
                else:
                    y = int(g[2])
                    got = date(y if y >= 100 else 2000 + y, int(g[1]), int(g[0]))
                assert got == expected
                return
        pytest.fail(f"no statement pattern matched: {line!r}")

    def test_prose_about_effectiveness_does_not_match(self):
        """'regulate effective and orderly development' must never parse."""
        line = "Development Control Plan 2023 combine to regulate effective and orderly development,"
        assert not any(p.search(line) for p, _ in _STATEMENTS)


# ---------------------------------------------------------------------------
# Extractor selection rules — real (generated) PDFs
# ---------------------------------------------------------------------------

def _make_pdf(path, pages):
    import fitz

    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


class TestExtractorSelectionRules:
    def test_latest_effective_statement_wins(self, tmp_path):
        """A document stating its original commencement AND a later
        amendment's effective date must serve the later one."""
        from extract_dcp_stated_dates import scan_statement

        pdf = tmp_path / "burwood-dcp.pdf"
        _make_pdf(pdf, ["In Force 6 May 2022", "Effective: 5 March 2026"])
        got = scan_statement(str(pdf), "burwood-dcp.pdf")
        assert got.date_iso == "2026-03-05"

    def test_amendment_table_ignores_approved_only_dates(self, tmp_path):
        """An amendment approved but not yet in force (odd date count) breaks
        the pairing assumption — skip, never take the page-wide maximum."""
        from extract_dcp_stated_dates import scan_amendment_table

        pdf = tmp_path / "parramatta-dcp-2023.pdf"
        _make_pdf(pdf, ["LIST OF AMENDMENTS\nDate Approved\nDate in Force\n"
                        "22/07/2024\n18/09/2024\n30/06/2026"])
        assert scan_amendment_table(str(pdf), "parramatta-dcp-2023.pdf",
                                    "parramatta") is None

    def test_amendment_table_takes_latest_in_force_of_pairs(self, tmp_path):
        from extract_dcp_stated_dates import scan_amendment_table

        pdf = tmp_path / "parramatta-dcp-2023.pdf"
        _make_pdf(pdf, ["LIST OF AMENDMENTS\nDate Approved\nDate in Force\n"
                        "26/10/2021\n01/12/2023\n22/07/2024\n18/09/2024"])
        got = scan_amendment_table(str(pdf), "parramatta-dcp-2023.pdf",
                                   "parramatta")
        assert got.date_iso == "2024-09-18"
        assert got.kind == "amended"

    def test_amendment_table_without_both_headers_is_skipped(self, tmp_path):
        from extract_dcp_stated_dates import scan_amendment_table

        pdf = tmp_path / "parramatta-dcp-2023.pdf"
        _make_pdf(pdf, ["LIST OF AMENDMENTS\n26/10/2021\n01/12/2023"])
        assert scan_amendment_table(str(pdf), "parramatta-dcp-2023.pdf",
                                    "parramatta") is None


# ---------------------------------------------------------------------------
# Brief: query date must never masquerade as data currency
# ---------------------------------------------------------------------------

class TestBriefDcpAsAt:
    def _dcp_data(self, as_at):
        return {"setbacks": [], "sd_setbacks": [], "dcp_name": "X DCP 2020",
                "dcp_url": None, "section": "S", "clause_ref": "", "as_at": as_at}

    def test_brief_dcp_fields_carry_plan_date_not_today(self):
        from services.intelligence_brief import _build_dcp_controls

        got = _build_dcp_controls(
            self._dcp_data({"date": "2022-09-09", "precision": "day",
                            "kind": "amended", "basis": "portal_plan_record"}),
            "waverley")
        assert got.dcp_name.as_at == "2022-09-09"
        assert got.controls.as_at == "2022-09-09"

    def test_brief_dcp_fields_carry_no_date_when_none_defensible(self):
        """as_at=date.today() here was the freshness-misrepresentation class:
        the query date presented as data currency. No date beats a false one."""
        from datetime import date as _date

        from services.intelligence_brief import _build_dcp_controls

        got = _build_dcp_controls(self._dcp_data(None), "waverley")
        assert got.dcp_name.as_at is None
        assert got.dcp_name.as_at != _date.today().isoformat()
