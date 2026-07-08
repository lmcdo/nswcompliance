"""Regression: the conveyancing Nearby-DA lookup must NOT filter by council name.

The DB (development_applications) stores a different council-name vocabulary than
the LEP-derived name the pipeline produces — e.g. "The Council of the Shire of
Hornsby" vs "Hornsby Shire Council". Filtering fetch_nearby_das by the derived
name silently matched zero rows and printed a false "No development applications
within 200m" for ~6 councils (Hornsby, Ryde, Hunters Hill, Kiama, Broken Hill,
Glen Innes — 1,668 real DAs hidden). The 200m Haversine radius filter already
scopes the search, so the council filter is redundant; passing council_name=None
(as services/intelligence_brief.py already does) removes the bug class.
"""

import os
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

_CONVEYANCING_SRC = (_ROOT / "services" / "conveyancing.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Source guard — always runs (no DB). Mutation: re-adding the council filter
# to either fetch_nearby_das call reintroduces the false-negative and fails.
# ---------------------------------------------------------------------------

class TestNoCouncilFilterOnNearbyDA:
    def test_no_conveyancing_call_filters_nearby_das_by_council(self):
        # every fetch_nearby_das call in the conveyancing service must pass
        # council_name=None (never council_name=council_name).
        calls = re.findall(r"fetch_nearby_das\([^)]*\)", _CONVEYANCING_SRC, re.DOTALL)
        assert calls, "expected fetch_nearby_das call sites in conveyancing.py"
        for call in calls:
            assert "council_name=council_name" not in call, (
                f"fetch_nearby_das is filtering by the LEP-derived council name "
                f"again — this silently returns zero for councils whose DB name "
                f"differs. Pass council_name=None. Offending call: {call!r}"
            )
            assert "council_name=None" in call, (
                f"fetch_nearby_das call must explicitly pass council_name=None: {call!r}"
            )


# ---------------------------------------------------------------------------
# Behavioural proof — needs the real DB (runs under `pytest -m database`).
# ---------------------------------------------------------------------------

@pytest.mark.database
class TestNearbyDaVocabularyMismatchRecovered:
    def _conn(self):
        url = os.getenv("DATABASE_URL")
        if not url:
            pytest.skip("DATABASE_URL not set")
        import psycopg2
        from unittest.mock import MagicMock
        # tests/conftest_mocks.py stubs psycopg2 for pure-logic runs — skip the
        # behavioural proof cleanly there (it runs under `pytest -m database`
        # with real deps + DATABASE_URL).
        if isinstance(psycopg2, MagicMock) or isinstance(getattr(psycopg2, "connect", None), MagicMock):
            pytest.skip("psycopg2 is mocked (pure-logic run) — needs real DB")
        c = psycopg2.connect(url)
        c.autocommit = True
        if isinstance(c, MagicMock):
            pytest.skip("psycopg2 is mocked (pure-logic run) — needs real DB")
        return c

    def test_hidden_das_recovered_for_vocab_mismatch_council(self):
        """For a real Hornsby DA point, the LEP-derived council filter returns
        zero (the bug) while council_name=None returns the real DAs (the fix)."""
        from conveyancing_db import fetch_nearby_das
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT latitude, longitude FROM development_applications "
                "WHERE council_name = 'The Council of the Shire of Hornsby' "
                "AND latitude IS NOT NULL LIMIT 1"
            )
            row = cur.fetchone()
            if not row:
                pytest.skip("no Hornsby DA with coordinates in this DB")
            lat, lng = row
            # the buggy filter (LEP-derived ePlanning name) → zero
            filtered = fetch_nearby_das(conn, lat, lng, council_name="Hornsby Shire Council", radius_m=200)
            # the fix (spatial-only) → the real nearby DAs
            unfiltered = fetch_nearby_das(conn, lat, lng, council_name=None, radius_m=200)
            assert len(filtered) == 0, "expected the vocab-mismatched filter to hide DAs"
            assert len(unfiltered) >= 1, "council_name=None must surface the real nearby DAs"
        finally:
            conn.close()
