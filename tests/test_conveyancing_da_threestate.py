"""Three-state nearby-DA count: a check that could not run must be None, not a false 0.

Regression for CONVEYANCING_QA_ADVERSARIAL.md S1 / R6. The conveyancing report
initialised da_count=0 and left it 0 whenever the nearby-DA lookup could not run
(council unresolved, DATABASE_URL absent, or the query raised), so a conveyancer
saw "0 DAs within 200 m" — an authoritative "none nearby" — when the truth was
"not assessed". conveyancing._nearby_da_count now returns (None, True) for every
not-completed case and (count, False) only when the query actually ran, so a
genuine 0 stays distinguishable from a failure.

The success/exception paths patch psycopg2.connect with a fake connection so the
tests are self-contained: they never touch a real DB and don't depend on whether
psycopg2 is the conftest stub or the real driver (which would fail to connect to
the placeholder URL and mask the behaviour under test).
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import psycopg2  # noqa: E402  (may be the conftest stub; we patch connect explicitly)

import conveyancing  # noqa: E402

_LAT, _LNG = -33.8, 151.2
_COUNCIL = "Hornsby Shire Council"


class _FakeConn:
    """Minimal stand-in for a psycopg2 connection: only autocommit + close used."""

    def __init__(self):
        self.autocommit = False

    def close(self):
        pass


def _patch_connect(monkeypatch):
    """Make psycopg2.connect return a fake connection (no real DB, any URL)."""
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: _FakeConn())


class TestNearbyDaCountThreeState:
    def test_no_council_returns_none_not_zero(self, monkeypatch):
        # An unresolved council means "not assessed" even with a DB configured.
        monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
        count, failed = conveyancing._nearby_da_count(None, _LAT, _LNG)
        assert count is None
        assert failed is True

    def test_no_database_url_returns_none_not_zero(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        count, failed = conveyancing._nearby_da_count(_COUNCIL, _LAT, _LNG)
        assert count is None
        assert failed is True

    def test_query_exception_returns_none_not_zero(self, monkeypatch):
        # Connection succeeds; the FETCH raises — proves the fetch-exception path,
        # not an accidental connect failure.
        monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
        _patch_connect(monkeypatch)

        def _boom(*a, **k):
            raise RuntimeError("DB exploded")

        monkeypatch.setattr(conveyancing, "fetch_nearby_das", _boom)
        count, failed = conveyancing._nearby_da_count(_COUNCIL, _LAT, _LNG)
        assert count is None
        assert failed is True

    def test_genuine_zero_is_zero_not_failed(self, monkeypatch):
        # The crux: a real "0 within 200 m" must be (0, False), NOT (None, True) —
        # over-correcting to None would hide genuine clean results.
        monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
        _patch_connect(monkeypatch)
        monkeypatch.setattr(conveyancing, "fetch_nearby_das", lambda *a, **k: [])
        count, failed = conveyancing._nearby_da_count(_COUNCIL, _LAT, _LNG)
        assert count == 0
        assert failed is False

    def test_real_count_passthrough(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
        _patch_connect(monkeypatch)
        monkeypatch.setattr(conveyancing, "fetch_nearby_das", lambda *a, **k: [1, 2, 3])
        count, failed = conveyancing._nearby_da_count(_COUNCIL, _LAT, _LNG)
        assert count == 3
        assert failed is False

    def test_query_passes_council_name_none(self, monkeypatch):
        # Must not re-introduce the vocab-mismatch council filter (see
        # test_conveyancing_nearby_da_council): the query passes council_name=None.
        monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
        _patch_connect(monkeypatch)
        seen = {}

        def _capture(conn, lat, lng, council_name="SENTINEL"):
            seen["council_name"] = council_name
            return []

        monkeypatch.setattr(conveyancing, "fetch_nearby_das", _capture)
        conveyancing._nearby_da_count(_COUNCIL, _LAT, _LNG)
        assert seen["council_name"] is None
