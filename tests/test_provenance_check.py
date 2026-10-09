"""scripts/provenance_check.py: a rule traces only when its quote sits in its own clause.

Pure tests over a small synthetic law page and an injected fetch, so every
failure mode is forced, not hoped for. The live run is
tests/test_secondary_dwelling_provenance_live.py and the weekly Fly job.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import provenance_check as pc  # noqa: E402

BASE = "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714"
PAGE = (
    '<div id="sec.53" class="frag-clause"> 53 Standards <div id="sec.53-ssec.2"> (2) The following apply— '
    '<div id="sec.53-ssec.2-para1.a"> (a) for a detached secondary dwelling—a minimum site area of 450m 2 , </div>'
    '<div id="sec.53-ssec.2-para1.b"> (b) the number of parking spaces is the same. </div></div></div>'
    '<div id="sec.54" class="frag-clause"> 54 Other clause (1) something else entirely. </div>'
)


def _row(**kw):
    row = {"id": 1, "development_type": "dual_occupancy", "standard_type": "site_area",
           "legislation_url": BASE + "#sec.53-ssec.2-para1.a",
           "source_quote": "(2) The following apply— ... (a) for a detached secondary dwelling—a minimum site area of 450m2,"}
    row.update(kw)
    return row


def _trace(rows, fetch=None):
    """(traced, tracing problems): these tests check clause tracing only, so the
    always-on granny-flat rule validation (tested separately) is set aside."""
    traced, problems = pc.run(rows, fetch=fetch or _fetch_ok, pause_s=0)
    return traced, [p for p in problems if not p.startswith("validation:")]


def _fetch_ok(url):
    assert url == BASE
    return PAGE


def test_a_rule_in_its_own_clause_traces():
    assert _trace([_row()]) == (1, [])


def test_quote_in_the_law_but_linked_to_the_wrong_clause_is_broken():
    traced, problems = _trace([_row(legislation_url=BASE + "#sec.53-ssec.2-para1.b")])
    assert traced == 0 and "quote not inside clause #sec.53-ssec.2-para1.b" in problems[0]


def test_changed_number_is_broken():
    q = _row()["source_quote"].replace("450m2", "500m2")
    traced, problems = _trace([_row(source_quote=q)])
    assert traced == 0 and "quote not inside clause" in problems[0]


def test_lead_in_not_in_the_law_is_broken():
    q = "(2) Words the law never said— ... (a) for a detached secondary dwelling—a minimum site area of 450m2,"
    traced, problems = _trace([_row(source_quote=q)])
    assert traced == 0 and "quote part not in the law in force" in problems[0]


def test_anchor_missing_from_current_page_is_broken():
    traced, problems = _trace([_row(legislation_url=BASE + "#sec.99")])
    assert traced == 0 and "anchor #sec.99 not found" in problems[0]


def test_link_without_anchor_or_off_site_or_with_whitespace_is_broken():
    for url in (BASE, "https://example.com/x#sec.53", BASE[:30] + "\r\n  " + BASE[30:] + "#sec.53"):
        traced, problems = pc.run([_row(legislation_url=url)], fetch=_fetch_ok, pause_s=0)
        assert traced == 0 and problems, url


def test_failed_fetch_is_named_and_every_rule_on_that_page_is_broken():
    def fetch_403(url):
        raise RuntimeError("HTTP 403")
    traced, problems = pc.run([_row(), _row(id=2, standard_type="other")], fetch=fetch_403, pause_s=0)
    assert traced == 0 and any("fetch failed" in p and "HTTP 403" in p for p in problems)


def test_failed_fetch_counts_every_row_even_when_rows_share_a_standard_type():
    # 2026-10-09: Cloudflare 403'd the one page all 53 rules link to, and the
    # check printed "25/53 traced" -- broken was keyed by standard_type, so 53
    # rows over 28 distinct types read as 25 traced when none had been checked.
    def fetch_403(url):
        raise RuntimeError("HTTP 403")
    rows = [_row(id=1, development_type="dual_occupancy", standard_type="max_height"),
            _row(id=2, development_type="terraces", standard_type="max_height")]
    traced, _ = pc.run(rows, fetch=fetch_403, pause_s=0)
    assert traced == 0


def test_one_broken_row_does_not_break_its_same_type_sibling():
    q = _row()["source_quote"].replace("450m2", "500m2")
    rows = [_row(id=1, standard_type="site_area"),
            _row(id=2, development_type="terraces", standard_type="site_area", source_quote=q)]
    traced, problems = _trace(rows)
    assert traced == 1 and len(problems) == 1


def test_no_rules_is_a_failure_not_a_pass():
    assert pc.run([], fetch=_fetch_ok, pause_s=0) == (0, ["no rules with a quote were found to check"])


def test_empty_quote_is_broken():
    traced, problems = _trace([_row(source_quote="   ")])
    assert traced == 0 and "no quote" in problems[0]


def test_each_page_is_fetched_once():
    calls = []

    def counting(url):
        calls.append(url)
        return PAGE
    pc.run([_row(), _row(id=2, standard_type="b", legislation_url=BASE + "#sec.53-ssec.2-para1.b",
                         source_quote="(b) the number of parking spaces is the same.")],
           fetch=counting, pause_s=0)
    assert calls == [BASE]


def test_missing_granny_flat_path_rules_fail_even_when_other_rules_trace():
    # Round-3 cross-review: with every path rule deleted, a remaining generic
    # quoted rule must not let the weekly check pass.
    traced, problems = pc.run([_row()], fetch=_fetch_ok, pause_s=0)
    assert traced == 1  # the generic row itself traces...
    assert any(p.startswith("validation:") and "rule missing" in p for p in problems)  # ...but the run fails


def test_alert_not_delivered_exits_2(monkeypatch, capsys):
    import types
    fake_lm = types.SimpleNamespace(send_telegram=lambda msg: False)
    monkeypatch.setitem(sys.modules, "legislation_monitor", fake_lm)
    monkeypatch.setattr(pc, "run", lambda rows, **k: (0, ["x: broken"]))
    monkeypatch.setattr(pc, "served_rows", lambda conn: [])

    class FakeConn:
        def close(self):
            pass
    import psycopg2
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: FakeConn(), raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setattr(sys, "argv", ["provenance_check.py"])
    assert pc.main() == 2
    assert "ALERT NOT DELIVERED" in capsys.readouterr().out


def test_alert_delivered_exits_1(monkeypatch):
    import types
    monkeypatch.setitem(sys.modules, "legislation_monitor", types.SimpleNamespace(send_telegram=lambda msg: True))
    monkeypatch.setattr(pc, "run", lambda rows, **k: (0, ["x: broken"]))
    monkeypatch.setattr(pc, "served_rows", lambda conn: [])

    class FakeConn:
        def close(self):
            pass
    import psycopg2
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: FakeConn(), raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setattr(sys, "argv", ["provenance_check.py"])
    assert pc.main() == 1
