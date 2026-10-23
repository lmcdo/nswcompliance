"""Daily council-list check, daily cadence, run results and the one alarm (VerifyOps v6 steps 3+4).

Spec: ~/.claude/plans/ce-verifyops-v5-SPEC-2026-10-22.md, v6 resolutions 4-7, 9, 10, 12, 13.
Real lists: tests/fixtures/verifyops/*_list_2026-10-22.json are the live scraper output for
bayside, canada_bay and canterbury_bankstown on 2026-10-22 (read-only fetch, unedited).
"""
from __future__ import annotations

import copy
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verifyops_coverage as cov  # noqa: E402
from verifyops_links import (  # noqa: E402
    alert_lines, diff_lists, fingerprint, held_match, is_draft, likely_replaces, link_entries,
    normalise_href,
)
from verifyops_record import (  # noqa: E402
    FULL_DOWNLOAD_EVERY, OUTCOMES, Recorder, decide_fetch, in_shadow, is_spot_check,
)

FIX = ROOT / "tests" / "fixtures" / "verifyops"
NOW = datetime(2026, 10, 22, 2, 0, tzinfo=timezone.utc)


def real(council: str) -> dict:
    return json.loads((FIX / f"{council}_list_2026-10-22.json").read_text(encoding="utf-8"))


# ── link normalising (resolution 12) ────────────────────────────────────────────────────────

def test_a_query_that_names_the_document_is_kept():
    # canada_bay and liverpool name the document in the query; dropping it would merge them all.
    a, _ = normalise_href("https://canadabay.t1cloud.com/x/content/?id=folder-7719479&streamId=streampdf-7719479")
    b, _ = normalise_href("https://canadabay.t1cloud.com/x/content/?id=folder-7719480&streamId=streampdf-7719480")
    assert a != b


def test_a_version_in_the_query_is_a_different_document():
    a, _ = normalise_href("https://x.gov.au/dcp.pdf?version=1")
    b, _ = normalise_href("https://x.gov.au/dcp.pdf?version=2")
    assert a != b


def test_a_one_council_run_is_recorded_as_partial_even_with_force():
    src = (ROOT / "scripts" / "r2_monitor.py").read_text(encoding="utf-8")
    line = src[src.index("    mode = ("):src.index("recorder = Recorder(conn")]
    assert line.index('f"council:{args.council}"') < line.index('"force"')


def test_cache_busters_case_and_fragment_do_not_make_a_new_link():
    a, _ = normalise_href("https://WWW.Council.nsw.gov.au/files/dcp.pdf?itok=abc&t=3#page=2")
    b, _ = normalise_href("https://www.council.nsw.gov.au/files/dcp.pdf")
    assert a == b


def test_a_drupal_reupload_is_one_document_and_a_chapter_number_is_not_a_reupload():
    a, base_a = normalise_href("https://x.gov.au/sites/default/files/2024-06/dcp_part_3_0.pdf")
    assert base_a.endswith("/dcp_part_3.pdf") and a.endswith("/dcp_part_3_0.pdf")
    prev = link_entries([{"url": "https://x.gov.au/files/dcp_part_3.pdf", "label": "Part 3"}])
    cur = link_entries([{"url": "https://x.gov.au/files/dcp_part_3_0.pdf", "label": "Part 3"}])
    d = diff_lists(prev, cur)
    assert not d.new and not d.gone and len(d.reuploads) == 1
    assert alert_lines("x", d, {}) == ["[x] possible re-upload: part 3 https://x.gov.au/files/dcp_part_3_0.pdf"]
    # part_2 replaced by part_3 is a real change, not a re-upload
    d2 = diff_lists(link_entries([{"url": "https://x.gov.au/files/dcp_part_2.pdf", "label": "Part 2"}]),
                    link_entries([{"url": "https://x.gov.au/files/dcp_part_3.pdf", "label": "Part 3"}]))
    assert len(d2.new) == 1 and len(d2.gone) == 1 and not d2.reuploads


# ── the list diff on real pages ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("council", ["bayside", "canada_bay", "canterbury_bankstown"])
def test_the_same_real_list_twice_raises_nothing(council):
    # Resolution 10 + shadow-week pass mark: an unchanged page gives 0 alerts.
    entries = link_entries(real(council)["discovered"])
    d = diff_lists(entries, copy.deepcopy(entries))
    assert not d.new and not d.gone and not d.redesigned
    assert alert_lines(council, d, real(council)["held"]) == []
    assert fingerprint(entries) == fingerprint(copy.deepcopy(entries))


def test_first_scan_saves_and_never_alerts():
    d = diff_lists(None, link_entries(real("bayside")["discovered"]))
    assert d.first_scan and alert_lines("bayside", d, {}) == []


def test_bayside_new_edition_is_named_against_the_whole_plan():
    # Real: Bayside lists "Bayside Development Control Plan 2022 - Amendment 2" with no part number.
    fx = real("bayside")
    cur = link_entries(fx["discovered"])
    prev = [e for e in cur if "amendment 2" not in e["norm"].lower()]
    assert len(prev) == len(cur) - 1
    lines = alert_lines("bayside", diff_lists(prev, cur), fx["held"], plans=["Bayside DCP 2022"])
    assert len(lines) == 1 and "may replace the whole plan (Bayside DCP 2022)" in lines[0]


def test_a_redesign_is_one_line_but_a_held_chapter_match_still_shows():
    # Resolution 6, on the real CB list: half the links replaced, one matching a held chapter number.
    fx = real("canterbury_bankstown")
    prev = link_entries(fx["discovered"])
    cur = prev[: len(prev) // 2] + [
        {"href": f"https://cb.example/new-{i}.pdf", "norm": f"https://cb.example/new-{i}.pdf",
         "text": f"guide {i}", "chapter_key": None} for i in range(30)
    ] + [{"href": "https://cb.example/c73.pdf", "norm": "https://cb.example/c73.pdf",
          "text": "chapter 7.3 city west (2026)", "chapter_key": None}]
    held = {"chapter-7-3": "Chapter 7.3 City West", "chapter-7-2": "Chapter 7.2 City East"}
    d = diff_lists(prev, cur)
    assert d.redesigned
    lines = alert_lines("canterbury_bankstown", d, held)
    assert lines[0].startswith("[canterbury_bankstown] page redesigned")
    assert len(lines) == 2 and "may replace chapter-7-3" in lines[1]


def test_one_new_edition_on_a_small_real_page_is_not_a_redesign():
    # bayside lists 7 links; 1 new is 1/7 changed, canada_bay 3 new of 8 would be > 1/3 but < 5 links
    cur = link_entries(real("canada_bay")["discovered"])
    d = diff_lists(cur[3:], cur)
    assert len(d.new) == 3 and not d.redesigned and len(alert_lines("canada_bay", d, {})) == 3


def test_six_new_links_on_the_real_70_link_cb_page_are_not_a_redesign():
    prev = link_entries(real("canterbury_bankstown")["discovered"])
    extra = [{"href": f"https://cb.example/{i}.pdf", "norm": f"https://cb.example/{i}.pdf",
              "text": f"guide {i}", "chapter_key": None} for i in range(6)]
    d = diff_lists(prev, prev + extra)
    assert not d.redesigned and len(alert_lines("cb", d, {})) == 6


def test_a_plan_name_without_a_year_never_matches():
    # Real dcp_name on the registry: 'Ku-ring-gai DCP' (no year) would match every Ku-ring-gai link.
    assert likely_replaces("ku-ring-gai dcp 2024 part 5", {}, ["Ku-ring-gai DCP"]) is None
    assert likely_replaces("ku-ring-gai dcp 2024 part 5", {}, ["Ku-ring-gai DCP 2024"]) is not None


def test_below_the_redesign_share_each_new_link_is_its_own_line():
    prev = link_entries(real("canterbury_bankstown")["discovered"])
    cur = prev + [{"href": "https://cb.example/a.pdf", "norm": "https://cb.example/a.pdf",
                   "text": "a", "chapter_key": None}]
    d = diff_lists(prev, cur)
    assert not d.redesigned and len(alert_lines("cb", d, {})) == 1


def test_delisted_is_not_gone():
    # #1188 / resolution 7: dead file = removed; live file = possibly repealed; unknown = said so.
    prev = link_entries([{"url": f"https://x.gov.au/{n}.pdf", "label": n} for n in "abcdefghij"])
    cur = [e for e in prev if not e["norm"].endswith(("/a.pdf", "/b.pdf", "/c.pdf"))]
    d = diff_lists(prev, cur)
    assert not d.redesigned
    alive = {d.gone[0]["norm"]: False, d.gone[1]["norm"]: True}
    lines = alert_lines("x", d, {}, alive)
    assert "no longer opens" in lines[0]
    assert "possibly repealed or replaced" in lines[1]
    assert "file not checked" in lines[2]


def test_draft_words_are_labelled():
    assert is_draft("Draft DCP 2026 on public exhibition")
    # the folder name is not evidence: canada_bay serves an operative guide from an "exhibitions" path
    assert not is_draft("Homebush Transport Oriented Development Precinct Design Guide",
                        "https://x.amazonaws.com/NSW%2BPlanning%2BPortal%2Bexhibitions%2B/Homebush/x.pdf")
    assert not is_draft("Part 4 Residential")
    prev = link_entries([{"url": "https://x.gov.au/a.pdf", "label": "a"}] * 1)
    cur = prev + link_entries([{"url": "https://x.gov.au/d.pdf", "label": "Draft Part 4 Residential"}])
    line = alert_lines("x", diff_lists(prev, cur), {})[0]
    assert "title says draft or exhibition - check whether it is in force" in line
    assert "not in force)" not in line


def test_held_match_is_exact_number_and_unique():
    held = {"c72": "Chapter 7.2 City East", "c73": "Chapter 7.3 City West", "p4a": "Part 4 Dwellings",
            "p4b": "Part 4 Dual occupancy"}
    assert held_match("Chapter 7.3 - amended 2026", held) == "c73"
    assert held_match("Chapter 7.4", held) is None
    assert held_match("City West", held) is None          # no fuzzy label match (#1430)
    assert held_match("Part 4", held) is None             # two held Part 4s: ambiguous, not a guess
    assert likely_replaces("appendices", held, ["Bayside DCP 2022"]) is None


# ── daily cadence (resolutions 4 and 9) ─────────────────────────────────────────────────────

def _fetch(**kw):
    base = dict(force=False, stored_hash="h", stored_etag=None, head_etag=None, stored_len=100_000,
                head_len=100_000, last_downloaded=NOW - timedelta(days=1), now=NOW, spot=False)
    base.update(kw)
    return decide_fetch(**base)


def test_untagged_six_days_is_head_only_seven_days_downloads():
    assert _fetch(last_downloaded=NOW - timedelta(days=6)) == (False, "untagged_recent")
    assert _fetch(last_downloaded=NOW - FULL_DOWNLOAD_EVERY) == (True, "untagged_weekly")
    assert _fetch(last_downloaded=None) == (True, "untagged_weekly")


def test_tagged_downloads_only_on_a_tag_change_or_spot_check():
    assert _fetch(stored_etag="a", head_etag="a") == (False, "etag_match")
    assert _fetch(stored_etag="a", head_etag="b") == (True, "etag_changed")
    assert _fetch(stored_etag="a", head_etag="a", spot=True) == (True, "spot_check")


def test_a_size_change_behind_an_unchanged_tag_downloads():
    # Cross-review 2026-10-22: the tag alone was trusted, so a changed file with a reused tag
    # stayed served as current until a spot check happened to pick it.
    assert _fetch(stored_etag="a", head_etag="a", stored_len=100_000, head_len=200_000) == (True, "size_changed")
    assert _fetch(stored_etag="a", head_etag="a", stored_len=100_000, head_len=None) == (False, "etag_match")


def test_size_change_force_and_no_baseline_always_download():
    assert _fetch(head_len=100_001) == (True, "size_changed")
    assert _fetch(force=True, stored_etag="a", head_etag="a") == (True, "force")
    assert _fetch(stored_hash=None, stored_etag="a", head_etag="a") == (True, "no_baseline")
    # a stored tag the server stopped sending falls to the untagged rule, not to a free pass
    assert _fetch(stored_etag="a", head_etag=None, last_downloaded=NOW - timedelta(days=8))[0]


def test_spot_check_is_about_five_percent_once_a_week():
    monday = datetime(2026, 10, 19, 2, 0, tzinfo=timezone.utc)
    week = [monday + timedelta(days=i) for i in range(7)]
    picks = {cid: [d for d in week if is_spot_check(cid, d)] for cid in range(1, 4001)}
    picked = [cid for cid, days in picks.items() if days]
    assert all(len(picks[cid]) == 1 for cid in picked)          # never twice in a week
    assert 0.035 < len(picked) / 4000 < 0.065                    # ~1 in 20


def test_shadow_week():
    assert in_shadow(None, NOW)
    assert in_shadow(NOW - timedelta(days=6), NOW)
    assert not in_shadow(NOW - timedelta(days=7), NOW)


# ── run results ─────────────────────────────────────────────────────────────────────────────

class FakeCursor:
    def __init__(self, log):
        self.log, self._one = log, None

    def execute(self, sql, params=None):
        self.log.append((" ".join(sql.split()), params))
        self._one = (None,) if "min(started_at)" in sql else (7,)

    def executemany(self, sql, rows):
        self.log.append((" ".join(sql.split()), list(rows)))

    def fetchone(self):
        return self._one

    def close(self):
        pass


class FakeConn:
    def __init__(self):
        self.log: list = []
        self.commits = 0

    def cursor(self):
        return FakeCursor(self.log)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


def test_a_dry_run_writes_nothing():
    conn = FakeConn()
    rec = Recorder(conn, dry_run=True, mode="daily")
    rec.start()
    rec.chapter(1, "x", "k", "rate_limited")
    rec.flush()
    rec.finish({})
    assert conn.log == [] and conn.commits == 0


def test_every_outcome_is_written_with_its_run():
    conn = FakeConn()
    rec = Recorder(conn, dry_run=False, mode="daily")
    rec.start()
    rec.chapter(1, "x", "k", "rate_limited", detail="HEAD 429 twice")
    rec.council_list("x", "https://x", "blocked", detail="403")
    rec.flush()
    chapter_rows = next(p for s, p in conn.log if s.startswith("INSERT INTO dcp_monitor_chapter_results"))
    council_rows = next(p for s, p in conn.log if s.startswith("INSERT INTO dcp_monitor_council_results"))
    assert chapter_rows == [(7, 1, "x", "k", "rate_limited", None, "HEAD 429 twice")]
    assert council_rows[0][:4] == (7, "x", "https://x", "blocked")


def test_an_unknown_outcome_is_refused():
    rec = Recorder(FakeConn(), dry_run=True, mode="daily")
    with pytest.raises(ValueError):
        rec.chapter(1, "x", "k", "skipped")
    with pytest.raises(ValueError):
        rec.council_list("x", None, "fine")


def test_outcomes_match_the_migration_check_constraint():
    sql = (ROOT / "migrations" / "116_dcp_monitor_results.sql").read_text(encoding="utf-8")
    for outcome in OUTCOMES:
        assert f"'{outcome}'" in sql, outcome
    assert sql.count("CHECK (outcome IN") == 2


def test_the_rate_limited_skip_is_recorded_in_r2_monitor():
    # Finding 13: the 429-twice branch used to `continue` with no trace.
    src = (ROOT / "scripts" / "r2_monitor.py").read_text(encoding="utf-8")
    branch = src[src.index("still rate-limited after host pauses"):][:600]
    assert '"rate_limited"' in branch and 'results["rate_limited"].append' in branch


# ── the alarm (metric C, resolution 5) ──────────────────────────────────────────────────────

def test_a_new_red_is_red_even_when_an_old_one_cleared():
    new, cleared = cov.compare(["a|1|no_url", "b|2|no_url"], ["a|1|no_url", "c|3|not_checked_8d"])
    assert new == ["c|3|not_checked_8d"] and cleared == ["b|2|no_url"]


TODAY = date(2026, 10, 23)


class AlarmConn:
    """Answers each alarm query with a fixed set of rows."""

    def __init__(self, reds: dict[str, list[tuple]], served: int = 10, missing: bool = False,
                 run_rows: list[tuple] | None = None, active: list[tuple] | None = None):
        self.reds, self.served, self.missing = reds, served, missing
        self.active = [("x", f"k{i}") for i in range(served)] if active is None else active
        # Default: the latest full run content-checked every active chapter.
        self.run_rows = ([(c, k, "unchanged_hash") for c, k in self.active]
                         if run_rows is None else run_rows)

    def cursor(self):
        outer = self

        class C:
            rows: list = []

            def execute(self, sql, params=None):
                if outer.missing and "dcp_monitor_" in sql:
                    raise RuntimeError('relation "dcp_monitor_runs" does not exist')
                if sql.strip().startswith("SELECT r.council, r.chapter_key FROM dcp_chapter_registry r WHERE r.is_active"):
                    self.rows = list(outer.active)
                    return
                if sql == cov._LAST_RUN_ROWS:
                    self.rows = outer.run_rows
                    return
                if sql.startswith("SELECT git_sha FROM dcp_monitor_runs"):
                    self.rows = []  # no run: deployed_not_main has its own tests
                    return
                reason = next(r for r, q in cov.QUERIES.items() if q == sql)
                self.rows = outer.reds.get(reason, [])

            def fetchall(self):
                return self.rows

            def fetchone(self):
                return self.rows[0] if self.rows else None

            def close(self):
                pass

        return C()


def test_alarm_passes_on_baseline_and_fails_on_a_new_key(tmp_path, monkeypatch):
    base = tmp_path / "b.json"
    base.write_text(json.dumps({"keys": ["inner_west|*|unwatched"],
                                "since": {"inner_west|*|unwatched": "2026-10-20"}}), encoding="utf-8")
    monkeypatch.setattr(cov, "BASELINE", base)
    assert cov.main([], conn=AlarmConn({"unwatched": [("inner_west", "*")]}), today=TODAY) == 0
    assert cov.main([], conn=AlarmConn({"unwatched": [("inner_west", "*")],
                                         "last_run_unchecked": [("x", "k")]}), today=TODAY) == 1


def test_alarm_cannot_look_is_never_a_pass(monkeypatch):
    assert cov.main([], conn=AlarmConn({}, missing=True)) == 2
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert cov.main([]) == 2


def test_update_is_shrink_only(tmp_path, monkeypatch):
    base = tmp_path / "b.json"
    base.write_text(json.dumps({"keys": ["a|1|no_url", "b|2|no_url"],
                                "since": {"a|1|no_url": "2026-10-20", "b|2|no_url": "2026-10-20"},
                                "why": {"a|1|no_url": "first run", "b|2|no_url": "first run"}}), encoding="utf-8")
    monkeypatch.setattr(cov, "BASELINE", base)
    conn = AlarmConn({"no_url": [("a", "1")], "not_checked_8d": [("c", "3")]})
    assert cov.main(["--update"], conn=conn, today=TODAY) == 1          # refused: new key
    assert json.loads(base.read_text())["keys"] == ["a|1|no_url", "b|2|no_url"]
    assert cov.main(["--update"], conn=AlarmConn({"no_url": [("a", "1")]}), today=TODAY) == 0
    doc = json.loads(base.read_text())
    assert doc["keys"] == ["a|1|no_url"]                                # cleared key dropped
    assert doc["since"] == {"a|1|no_url": "2026-10-20"} and doc["why"] == {"a|1|no_url": "first run"}


def test_every_reason_has_a_query_and_the_windows_match_the_spec():
    q = cov.QUERIES
    assert "INTERVAL '2 days'" in q["list_not_read_2d"] and "INTERVAL '8 days'" in q["not_checked_8d"]
    assert "INTERVAL '3 days'" in q["new_doc_undecided_3d"]
    assert "INTERVAL '33 days'" in q["update_unpublished_33d"]
    assert "dcp_setback_controls" in q["unwatched"] and "regulatory_provisions" in q["unwatched"]


def test_cross_review_fixes_stay_in_the_queries():
    # An inert-only council is unwatched; a missing change date is old, not never.
    q = cov.QUERIES
    assert "NOT COALESCE(r.is_inert, FALSE)" in q["unwatched"]
    assert "COALESCE(r.url_last_changed, '-infinity'::timestamptz)" in q["update_unpublished_33d"]
    assert "mode IN ('daily', 'force')" in q["no_run_2d"]


def test_the_download_date_is_saved_only_with_a_good_outcome():
    # Cross-review 2026-10-22: saving it straight after the download meant a later error still
    # committed it, and an untagged changed file was then skipped for up to 7 days.
    src = (ROOT / "scripts" / "r2_monitor.py").read_text(encoding="utf-8")
    between = src[src.index("content, resp_headers = download_pdf(url)"):src.index("if new_hash == stored_hash:")]
    assert "url_last_downloaded" not in between
    assert src.count("url_last_downloaded=%s") == 3            # unchanged-hash, re-export, changed
    tail = src[src.index("except WAFBlockError as exc:"):src.index("adaptive_delay(url)  # per-domain")]
    assert "url_last_downloaded" not in tail


def test_coverage_counts_only_active_chapters_and_council_and_fleet_keys():
    active = [("a", "1"), ("a", "2"), ("b", "1"), ("c", "1")]
    # a new-document key for a row that is not an active chapter never lowers C (it read -24/547)
    assert cov.coverage(["d|new-doc|new_doc_undecided_3d"], active) == "C = 4/4 active chapters with no red key"
    assert cov.coverage(["a|1|no_url"], active) == "C = 3/4 active chapters with no red key"
    assert cov.coverage(["a|*|list_not_read_2d"], active) == "C = 2/4 active chapters with no red key"
    assert cov.coverage(["*|*|no_run_2d"], active) == "C = 0/4 active chapters with no red key"


def test_a_link_with_no_address_is_not_a_document():
    assert link_entries([{"url": None, "label": "DCP"}, {"url": "  ", "label": "x"}]) == []
    conn = FakeConn()
    rec = Recorder(conn, dry_run=True, mode="daily")
    rec.council_list_checked("x", "https://x", [{"url": None, "label": "DCP"}], {}, probe=lambda u: None,
                             send=lambda t: None, now=NOW)
    assert rec._councils[0][2] == "empty"


# ── step 5: the baseline guard (v7) ────────────────────────────────────────────────────────────

RUN2 = json.loads((ROOT / "tests" / "fixtures" / "verifyops" / "run2_results_2026-10-23.json")
                  .read_text(encoding="utf-8"))
RUN2_ACTIVE = [tuple(r) for r in RUN2["active"]]
RUN2_ROWS = [tuple(r) for r in RUN2["rows"]]


def test_run2_real_share_is_81_of_547():
    # Real data: force run 2. 8 active chapters have no row at all; they count as unchecked.
    assert cov.unchecked_share(RUN2_ACTIVE, RUN2_ROWS) == (81, 547)


def test_inactive_rows_do_not_count_toward_checked():
    rows = [("a", "1", "unchanged_hash"), ("zz", "old", "unchanged_hash")]
    assert cov.unchecked_share([("a", "1"), ("a", "2")], rows) == (1, 2)


@pytest.mark.parametrize("outcome", ["rate_limited", "waf_blocked", "no_url", "failed", "transient"])
def test_not_checked_outcomes_count_as_unchecked(outcome):
    assert cov.unchecked_share([("a", "1")], [("a", "1", outcome)]) == (1, 1)


@pytest.mark.parametrize("outcome", sorted(cov.CHECKED))
def test_checked_outcomes_count_as_checked(outcome):
    assert cov.unchecked_share([("a", "1")], [("a", "1", outcome)]) == (0, 1)


def test_update_refused_on_run2(tmp_path, monkeypatch):
    # Known-wrong case: freezing run 2 (14.8% unchecked) as the baseline.
    base = tmp_path / "b.json"
    monkeypatch.setattr(cov, "BASELINE", base)
    conn = AlarmConn({}, active=RUN2_ACTIVE, run_rows=RUN2_ROWS)
    assert cov.main(["--update", "--allow-raise", "run 2"], conn=conn, today=TODAY) == 1
    assert not base.exists()


def test_update_refused_with_no_finished_run(tmp_path, monkeypatch):
    monkeypatch.setattr(cov, "BASELINE", tmp_path / "b.json")
    conn = AlarmConn({}, active=[("a", "1")], run_rows=[])
    assert cov.main(["--update", "--allow-raise", "x"], conn=conn, today=TODAY) == 1


def test_update_allowed_at_exactly_10_percent_refused_above(tmp_path, monkeypatch):
    base = tmp_path / "b.json"
    monkeypatch.setattr(cov, "BASELINE", base)
    active = [("a", str(i)) for i in range(10)]
    rows = [("a", str(i), "unchanged_hash") for i in range(9)] + [("a", "9", "rate_limited")]
    conn = AlarmConn({}, active=active, run_rows=rows)
    assert cov.main(["--update", "--allow-raise", "first daily run"], conn=conn, today=TODAY) == 0
    base.unlink()
    rows[8] = ("a", "8", "rate_limited")  # 2/10 = 20%
    conn = AlarmConn({}, active=active, run_rows=rows)
    assert cov.main(["--update", "--allow-raise", "x"], conn=conn, today=TODAY) == 1
    assert not base.exists()


def test_raise_records_reason_and_date_for_every_key_and_keeps_first_date(tmp_path, monkeypatch):
    base = tmp_path / "b.json"
    base.write_text(json.dumps({"keys": ["a|1|no_url"], "since": {"a|1|no_url": "2026-10-01"},
                                "why": {"a|1|no_url": "old"}}), encoding="utf-8")
    monkeypatch.setattr(cov, "BASELINE", base)
    conn = AlarmConn({"no_url": [("a", "1"), ("b", "2")]})
    assert cov.main(["--update", "--allow-raise", "first daily run 2026-10-24"], conn=conn, today=TODAY) == 0
    doc = json.loads(base.read_text())
    assert doc["since"] == {"a|1|no_url": "2026-10-01", "b|2|no_url": "2026-10-23"}
    assert doc["why"] == {"a|1|no_url": "old", "b|2|no_url": "first daily run 2026-10-24"}
    assert set(doc["keys"]) == set(doc["since"]) == set(doc["why"])


def test_baselined_over_30_days_alarms_again_and_re_raise_does_not_reset_it(tmp_path, monkeypatch, capsys):
    base = tmp_path / "b.json"
    base.write_text(json.dumps({"keys": ["a|1|no_url"], "since": {"a|1|no_url": "2026-09-22"},
                                "why": {"a|1|no_url": "x"}}), encoding="utf-8")
    monkeypatch.setattr(cov, "BASELINE", base)
    conn = AlarmConn({"no_url": [("a", "1")]})
    assert cov.main([], conn=conn, today=date(2026, 10, 22)) == 0   # 30 days: still quiet
    assert "still red for 30 days" in capsys.readouterr().out
    assert cov.main([], conn=conn, today=TODAY) == 1                # 31 days: alarms
    assert "EXPIRED  a|1|no_url" in capsys.readouterr().out
    assert cov.main(["--update", "--allow-raise", "again"], conn=conn, today=TODAY) == 1
    assert cov.main([], conn=conn, today=TODAY) == 1


def test_baselined_key_with_no_date_counts_as_expired():
    assert cov.baselined_ages({"a|1|no_url": ""}, ["a|1|no_url"], TODAY) == [("a|1|no_url", 31)]


def test_ages_are_oldest_first_and_skip_keys_not_red_today():
    since = {"a|1|no_url": "2026-10-20", "b|2|no_url": "2026-10-01", "c|3|no_url": "2026-10-01"}
    assert cov.baselined_ages(since, ["a|1|no_url", "b|2|no_url"], TODAY) == [
        ("b|2|no_url", 22), ("a|1|no_url", 3)]


def test_old_style_baseline_with_no_dates_alarms(tmp_path, monkeypatch):
    # A key baselined before dates were recorded cannot prove it is recent: it alarms.
    base = tmp_path / "b.json"
    base.write_text(json.dumps({"keys": ["a|1|no_url"]}), encoding="utf-8")
    monkeypatch.setattr(cov, "BASELINE", base)
    assert cov.main([], conn=AlarmConn({"no_url": [("a", "1")]}), today=TODAY) == 1


def test_a_future_date_counts_as_expired():
    assert cov.baselined_ages({"a|1|no_url": "2027-10-01"}, ["a|1|no_url"], TODAY) == [("a|1|no_url", 31)]


def test_impossible_stored_size_downloads_once_dq79():
    # Row 766 (ku_ring_gai, 2026-10-23): stored 1 byte behind a matching ETag -> never re-measured.
    assert _fetch(stored_etag="a", head_etag="a", stored_len=1, head_len=None) == (True, "size_impossible")
    assert _fetch(stored_len=999, head_len=None) == (True, "size_impossible")
    assert _fetch(stored_etag="a", head_etag="a", stored_len=1000, head_len=None) == (False, "etag_match")
    # Unknown (never recorded) is not impossible: 31 active rows hold NULL and must not download daily.
    assert _fetch(stored_etag="a", head_etag="a", stored_len=None, head_len=None) == (False, "etag_match")
