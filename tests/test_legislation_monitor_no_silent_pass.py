"""No silent pass, no fallback (2026-10-08 PCO format change).

The monitor's whole point is: a data-source failure is a NAMED error, nothing
is ever stamped "checked" on a miss, and "no changes" is reported on exactly
one path — everything else checked out. This file pins that contract against
regression, specifically the failure mode that shipped undetected for four
months: PCO's export format changed, every instrument_id came back blank,
`pco_listed_keys` read every instrument as "not listed", and the monitor kept
reporting "all current" while at least 7 instruments had actually changed.

Reuses the patterns in tests/test_sepp_auto_stale.py and
tests/test_legislation_monitor_stale_backfill.py: sys.path -> scripts/, a
recording FakeCursor/FakeConn, psycopg2/requests stubbed globally by
tests/conftest_mocks.py. Unlike those files this one imports the modules
directly (as tests/test_legislation_monitor_version_date.py does) rather than
exec-slicing source, because main() end-to-end needs every module-level name
(psycopg2, send_telegram, time.sleep, pco_listed_keys, ...) patchable via
monkeypatch.setattr on the live module object.

No network, no real database: every data-fetch function and psycopg2.connect
itself are monkeypatched; the drift-guard test only compares file bytes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import legislation_monitor as lm  # noqa: E402
import pco_client  # noqa: E402
from pco_client import PCOError, _parse_changes  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fakes for the main() end-to-end tests
# ---------------------------------------------------------------------------

FAKE_COLUMNS = [
    "instrument_key", "instrument_label", "instrument_type",
    "legislation_url", "current_version", "pco_instrument_id", "austlii_url",
]


def _row(key, version="1 May 2026", pco_id=None):
    """A row matching main()'s instrument_registry SELECT column order."""
    return (
        key, f"Label for {key}", "SEPP",
        f"https://legislation.nsw.gov.au/{key}", version, pco_id, None,
    )


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = [(c,) for c in FAKE_COLUMNS]
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.conn.executed.append((sql, params))

    def fetchall(self):
        return self.conn.rows

    def fetchone(self):
        # Only the stale-backfill SELECT calls fetchone(); None means "this
        # instrument was never flagged", making that sweep a no-op here.
        return None

    def close(self):
        pass


class FakeConn:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self.autocommit = None

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def _update_sqls(conn):
    return [(s, p) for s, p in conn.executed if s.lstrip().startswith("UPDATE instrument_registry")]


def _wire_db(monkeypatch, conn):
    """psycopg2.connect returns `conn`; any OTHER connect attempt is a bug."""
    monkeypatch.setattr(lm.psycopg2, "connect", lambda *a, **kw: conn)


def _refuse_db(monkeypatch):
    """psycopg2.connect must never be reached (e.g. argparse should fail first)."""
    def _boom(*a, **kw):
        raise AssertionError("real/mock DB connect attempted — should have exited first")
    monkeypatch.setattr(lm.psycopg2, "connect", _boom)


def _wire_telegram(monkeypatch):
    log: list[str] = []
    monkeypatch.setattr(lm, "send_telegram", lambda msg: log.append(msg))
    return log


def _wire_no_sleep(monkeypatch):
    monkeypatch.setattr(lm.time, "sleep", lambda s: None)


def _wire_fetch(monkeypatch, url_to_result: dict):
    """legislation_monitor._fetch_nsw_legislation_version_http -> table lookup.
    A value that is an Exception instance is raised instead of returned."""
    def _fake(url):
        result = url_to_result[url]
        if isinstance(result, BaseException):
            raise result
        return result
    monkeypatch.setattr(lm, "_fetch_nsw_legislation_version_http", _fake)


# ---------------------------------------------------------------------------
# 1-4: PCO parser (pco_client._parse_changes, pco_listed_keys)
# ---------------------------------------------------------------------------

class TestPcoParser:
    def test_new_format_record_yields_instrument_id(self):
        data = [{
            "title": "X",
            "view": "/view/html/inforce/current/epi-2008-0572",
            "xml": "/export/xml/current/epi-2008-0572",
            "images": [],
        }]
        changes = _parse_changes(data)
        assert len(changes) == 1
        assert changes[0].instrument_id == "epi-2008-0572"

    def test_old_format_record_yields_instrument_id(self):
        data = [{
            "Title": "X",
            "URL": "https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714",
        }]
        changes = _parse_changes(data)
        assert len(changes) == 1
        assert changes[0].instrument_id == "epi-2021-0714"

    def test_unrecognised_records_raise_pco_error(self):
        data = [{"title": "A", "foo": "bar"}]
        with pytest.raises(PCOError, match="not recognised"):
            _parse_changes(data)

    def test_empty_list_parses_to_empty_list(self):
        assert _parse_changes([]) == []

    def test_pco_listed_keys_raises_on_empty_weekly_export(self, monkeypatch):
        """An empty export is a broken feed, never 'nothing changed' (NSW
        amends legislation every week)."""
        monkeypatch.setattr(pco_client, "get_weekly_changes", lambda: [])
        with pytest.raises(RuntimeError, match="no records"):
            lm.pco_listed_keys([{"instrument_key": "k", "pco_instrument_id": "epi-1"}])


# ---------------------------------------------------------------------------
# 5-6: pco_cross_check
# ---------------------------------------------------------------------------

class TestPcoCrossCheck:
    def test_listed_and_unchanged_page_is_an_error_naming_the_key(self):
        instruments = [{"instrument_key": "k", "current_version": "1 May 2026"}]
        errors = lm.pco_cross_check({"k"}, {"k": "1 May 2026"}, instruments)
        assert len(errors) == 1
        assert "k" in errors[0]

    def test_listed_but_page_shows_a_newer_date_is_not_an_error(self):
        instruments = [{"instrument_key": "k", "current_version": "1 May 2026"}]
        errors = lm.pco_cross_check({"k"}, {"k": "2 May 2026"}, instruments)
        assert errors == []

    def test_listed_but_page_is_none_is_not_an_error_here(self):
        """The fetch miss is reported elsewhere (source_fetch_errors); the
        cross-check must not ALSO manufacture an error from a None page."""
        instruments = [{"instrument_key": "k", "current_version": "1 May 2026"}]
        errors = lm.pco_cross_check({"k"}, {"k": None}, instruments)
        assert errors == []


# ---------------------------------------------------------------------------
# 7-9: check_via_nsw_legislation
# ---------------------------------------------------------------------------

class TestCheckViaNswLegislation:
    def test_missing_legislation_url_is_a_named_error_not_a_fetch_attempt(self, monkeypatch):
        _wire_no_sleep(monkeypatch)
        telegram = _wire_telegram(monkeypatch)
        instruments = [{"instrument_key": "sepp_x", "legislation_url": None}]
        results, errors = lm.check_via_nsw_legislation(instruments)
        assert results["sepp_x"] is None
        assert len(errors) == 1
        assert "sepp_x" in errors[0] and "no legislation_url" in errors[0]
        assert telegram == []  # no download-triggered alert expected here

    def test_http_error_from_fetch_is_a_named_error(self, monkeypatch):
        _wire_no_sleep(monkeypatch)
        _wire_telegram(monkeypatch)
        url = "https://legislation.nsw.gov.au/sepp_y"
        _wire_fetch(monkeypatch, {url: RuntimeError("HTTP 403")})
        instruments = [{"instrument_key": "sepp_y", "legislation_url": url}]
        results, errors = lm.check_via_nsw_legislation(instruments)
        assert results["sepp_y"] is None
        assert len(errors) == 1
        assert "sepp_y" in errors[0] and "HTTP 403" in errors[0]

    def test_download_triggered_is_a_named_error(self, monkeypatch):
        _wire_no_sleep(monkeypatch)
        telegram = _wire_telegram(monkeypatch)
        url = "https://legislation.nsw.gov.au/sepp_z"
        _wire_fetch(monkeypatch, {url: lm.DownloadTriggeredError("serves a download")})
        instruments = [{"instrument_key": "sepp_z", "legislation_url": url}]
        results, errors = lm.check_via_nsw_legislation(instruments)
        assert results["sepp_z"] is None
        assert len(errors) == 1
        assert "sepp_z" in errors[0]
        assert any("sepp_z" in msg for msg in telegram)


# ---------------------------------------------------------------------------
# 10: check_instrument on a miss writes nothing, for every source
# ---------------------------------------------------------------------------

class TestCheckInstrumentOnAMiss:
    @pytest.mark.parametrize("source", ["nsw_legislation", "austlii", "pco"])
    def test_no_reading_executes_no_sql_and_commits_nothing(self, source):
        conn = FakeConn(rows=[])
        instrument = {
            "instrument_key": "sepp_q", "instrument_label": "SEPP Q",
            "current_version": "1 May 2026",
            "legislation_url": "https://legislation.nsw.gov.au/q",
        }
        result = lm.check_instrument(instrument, None, source, False, conn)
        assert conn.executed == [], f"{source}: a miss must execute no SQL"
        assert conn.commits == 0
        assert result.new_version is None and result.changed is False


# ---------------------------------------------------------------------------
# 11-15: main() end-to-end
# ---------------------------------------------------------------------------

class TestMainEndToEnd:
    def test_every_page_failing_is_fatal_with_no_false_success(self, monkeypatch):
        """11: all fetches fail -> exit 1, an ERROR telegram, never 'no changes'."""
        rows = [_row("sepp_a"), _row("sepp_b")]
        conn = FakeConn(rows)
        _wire_db(monkeypatch, conn)
        telegram = _wire_telegram(monkeypatch)
        _wire_no_sleep(monkeypatch)
        _wire_fetch(monkeypatch, {
            "https://legislation.nsw.gov.au/sepp_a": RuntimeError("timeout"),
            "https://legislation.nsw.gov.au/sepp_b": RuntimeError("timeout"),
        })
        monkeypatch.setattr(sys, "argv", ["legislation_monitor.py"])

        with pytest.raises(SystemExit) as exc:
            lm.main()
        assert exc.value.code == 1
        assert any("ERROR" in msg for msg in telegram)
        assert not any("no changes" in msg for msg in telegram)

    def test_one_fetch_failure_is_reported_and_never_stamped_checked(self, monkeypatch):
        """12: one instrument's page fails, the other is unchanged, PCO quiet
        -> exit 1, error names the failed key, no 'no changes', and the failed
        key never reaches an UPDATE ... last_checked statement."""
        rows = [_row("sepp_fail", version="1 May 2026"), _row("sepp_ok", version="1 May 2026")]
        conn = FakeConn(rows)
        _wire_db(monkeypatch, conn)
        telegram = _wire_telegram(monkeypatch)
        _wire_no_sleep(monkeypatch)
        _wire_fetch(monkeypatch, {
            "https://legislation.nsw.gov.au/sepp_fail": RuntimeError("connection reset"),
            "https://legislation.nsw.gov.au/sepp_ok": "1 May 2026",  # unchanged
        })
        monkeypatch.setattr(lm, "pco_listed_keys", lambda instruments: set())  # PCO quiet
        monkeypatch.setattr(sys, "argv", ["legislation_monitor.py"])

        with pytest.raises(SystemExit) as exc:
            lm.main()
        assert exc.value.code == 1
        assert any("sepp_fail" in msg for msg in telegram)
        assert not any("no changes" in msg for msg in telegram)

        update_sqls = _update_sqls(conn)
        assert not any("sepp_fail" in (params or ()) for _, params in update_sqls), \
            "a failed fetch must never be stamped as checked"
        assert any("sepp_ok" in (params or ()) for _, params in update_sqls), \
            "sanity: the instrument that DID resolve should still be stamped"

    def test_pco_export_failure_is_a_named_cross_check_error(self, monkeypatch):
        """13: pages fine and unchanged, but the PCO export itself is broken
        -> exit 1, error telegram names the cross-check failure."""
        rows = [_row("sepp_a", version="1 May 2026"), _row("sepp_b", version="1 May 2026")]
        conn = FakeConn(rows)
        _wire_db(monkeypatch, conn)
        telegram = _wire_telegram(monkeypatch)
        _wire_no_sleep(monkeypatch)
        _wire_fetch(monkeypatch, {
            "https://legislation.nsw.gov.au/sepp_a": "1 May 2026",
            "https://legislation.nsw.gov.au/sepp_b": "1 May 2026",
        })
        monkeypatch.setattr(
            lm, "pco_listed_keys",
            lambda instruments: (_ for _ in ()).throw(
                RuntimeError("PCO weekly export returned no records")),
        )
        monkeypatch.setattr(sys, "argv", ["legislation_monitor.py"])

        with pytest.raises(SystemExit) as exc:
            lm.main()
        assert exc.value.code == 1
        assert any("PCO export cross-check failed" in msg for msg in telegram)
        assert not any("no changes" in msg for msg in telegram)

    def test_pco_lists_an_unchanged_page_is_a_named_error(self, monkeypatch):
        """14: PCO lists an instrument whose own page shows no movement ->
        exit 1, error names that key."""
        rows = [_row("sepp_a", version="1 May 2026"), _row("sepp_b", version="1 May 2026")]
        conn = FakeConn(rows)
        _wire_db(monkeypatch, conn)
        telegram = _wire_telegram(monkeypatch)
        _wire_no_sleep(monkeypatch)
        _wire_fetch(monkeypatch, {
            "https://legislation.nsw.gov.au/sepp_a": "1 May 2026",
            "https://legislation.nsw.gov.au/sepp_b": "1 May 2026",
        })
        monkeypatch.setattr(lm, "pco_listed_keys", lambda instruments: {"sepp_a"})
        monkeypatch.setattr(sys, "argv", ["legislation_monitor.py"])

        with pytest.raises(SystemExit) as exc:
            lm.main()
        assert exc.value.code == 1
        assert any("sepp_a" in msg for msg in telegram)
        assert not any("no changes" in msg for msg in telegram)

    def test_all_current_and_pco_quiet_is_the_only_success_path(self, monkeypatch):
        """15: everything checks out -> exit 0 and the 'no changes' telegram,
        and ONLY this scenario produces it."""
        rows = [_row("sepp_a", version="1 May 2026"), _row("sepp_b", version="1 May 2026")]
        conn = FakeConn(rows)
        _wire_db(monkeypatch, conn)
        telegram = _wire_telegram(monkeypatch)
        _wire_no_sleep(monkeypatch)
        _wire_fetch(monkeypatch, {
            "https://legislation.nsw.gov.au/sepp_a": "1 May 2026",
            "https://legislation.nsw.gov.au/sepp_b": "1 May 2026",
        })
        monkeypatch.setattr(lm, "pco_listed_keys", lambda instruments: set())
        monkeypatch.setattr(sys, "argv", ["legislation_monitor.py"])

        with pytest.raises(SystemExit) as exc:
            lm.main()
        assert exc.value.code == 0
        assert any("no changes" in msg for msg in telegram)


# ---------------------------------------------------------------------------
# 16: PCO is a cross-check only, never a --source choice
# ---------------------------------------------------------------------------

class TestArgparsePcoNotASource:
    def test_source_pco_is_rejected_by_argparse(self, monkeypatch):
        _refuse_db(monkeypatch)
        monkeypatch.setattr(sys, "argv", ["legislation_monitor.py", "--source", "pco"])
        with pytest.raises(SystemExit) as exc:
            lm.main()
        assert exc.value.code == 2


# ---------------------------------------------------------------------------
# 17: drift guard — the deployed copy must never diverge from scripts/
# ---------------------------------------------------------------------------

class TestDeployedCopyMatchesSource:
    @pytest.mark.parametrize("filename", [
        "legislation_monitor.py", "pco_client.py", "refresh_runbook.py",
    ])
    def test_deploy_copy_is_byte_identical(self, filename):
        src = (ROOT / "scripts" / filename).read_bytes()
        deployed = (ROOT / "deploy" / "flyio-legislation-monitor" / filename).read_bytes()
        assert src == deployed, (
            f"deploy/flyio-legislation-monitor/{filename} has drifted from "
            f"scripts/{filename} — redeploy or resync before shipping."
        )
