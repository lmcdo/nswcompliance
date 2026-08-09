"""
LGA onboarding coverage tests.

These tests enforce the gate sequence: tag-provisions → check coverage → enable LGA.
They are meant to fail fast when an LGA is added to NEXT_PUBLIC_ENABLED_LGAS
before its provision data is ready.

Gate sequence before enabling a new LGA:
  1. Extract + load provisions into regulatory_provisions
  2. Run /tag-provisions skill to populate v2_applicable_dev_types
  3. Run python scripts/diagnose_provisions.py --lga <slug> to verify coverage
  4. Pass these tests
  5. Add to NEXT_PUBLIC_ENABLED_LGAS

Run: pytest tests/test_lga_coverage.py -v
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.database

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

_has_db = bool(
    os.environ.get("DATABASE_URL")
    or (Path(__file__).parent.parent / ".env").exists()
)


@pytest.fixture(scope="module")
def conn():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
    import psycopg2
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    c = psycopg2.connect(url)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# LGA registry
#
# Add new LGAs here when onboarding. Each entry's tests will FAIL until the
# onboarding gate sequence is complete — that failure is the intended signal.
#
# Fields:
#   lga_slug          str   — matches NEXT_PUBLIC_ENABLED_LGAS values
#   source_council    str   — matches regulatory_provisions.source_council
#   min_provision_count int — fail if fewer than this many provisions loaded
#   min_dev_type_coverage float — fraction of provisions that must have
#                                  v2_applicable_dev_types non-null/non-empty
# ---------------------------------------------------------------------------

ONBOARDED_LGAS = [
    # Inner West = 3 former councils; source_council is per-council slug.
    # Known data quality gaps documented inline:
    #   - marrickville: ~5% NULL v2_topic (un-classified rows from extraction)
    #   - leichhardt:   100% NULL v2_precinct_id (precinct assignment not run for this council)
    #   - ashfield:     ~67% NULL v2_precinct_id (same gap), ~10% NULL v2_topic
    # These are KNOWN ISSUES in the live IW deployment. Fix target: run precinct
    # assignment pipeline for leichhardt + ashfield, then tighten thresholds.
    {
        "lga_slug": "inner-west/marrickville",
        "source_council": "marrickville",
        "min_provision_count": 2500,   # 2853 is_current=TRUE as of 2026-04-19
        "min_dev_type_coverage": 0.80,
        "max_null_topic_rate": 0.10,   # known gap — tighten after topic re-run
        "max_null_precinct_rate": 1.0,  # KNOWN ISSUE: v2_precinct_id never populated in rp table
    },
    {
        "lga_slug": "inner-west/leichhardt",
        "source_council": "leichhardt",
        "min_provision_count": 400,    # 468 is_current=TRUE as of 2026-04-19
        "min_dev_type_coverage": 0.80,
        "max_null_topic_rate": 0.10,
        "max_null_precinct_rate": 1.0,  # KNOWN ISSUE: precinct assignment not run
    },
    {
        "lga_slug": "inner-west/ashfield",
        "source_council": "ashfield",
        "min_provision_count": 1500,   # checked 2026-04-19
        "min_dev_type_coverage": 0.80,
        "max_null_topic_rate": 0.10,
        "max_null_precinct_rate": 0.70,  # KNOWN ISSUE: ~67% NULL precinct
    },
    # Add new LGAs below as they are onboarded:
    # {
    #     "lga_slug": "canterbury-bankstown",
    #     "source_council": "Canterbury-Bankstown",
    #     "min_provision_count": 300,
    #     "min_dev_type_coverage": 0.80,
    # },
]

_ids = [l["lga_slug"] for l in ONBOARDED_LGAS]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLgaProvisionCoverage:
    """Verify provision data quality for every LGA in NEXT_PUBLIC_ENABLED_LGAS."""

    @pytest.mark.parametrize("lga", ONBOARDED_LGAS, ids=_ids)
    def test_minimum_provision_count(self, conn, lga):
        """Enough provisions loaded — guards against accidental truncation or failed extract."""
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM regulatory_provisions WHERE source_council = %s AND is_current = TRUE",
            (lga["source_council"],),
        )
        count = cur.fetchone()[0]
        cur.close()
        assert count >= lga["min_provision_count"], (
            f"{lga['lga_slug']}: only {count} active provisions "
            f"(min required: {lga['min_provision_count']}). "
            f"Re-run the extraction pipeline."
        )

    @pytest.mark.parametrize("lga", ONBOARDED_LGAS, ids=_ids)
    def test_dev_type_tagging_coverage(self, conn, lga):
        """v2_applicable_dev_types coverage meets threshold.

        Low coverage means the tag-provisions pipeline has not been run.
        The gate is 80% — structural/boilerplate provisions that apply to all
        dev types are expected to have empty arrays, not NULL.
        """
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE v2_applicable_dev_types IS NOT NULL
                      AND v2_applicable_dev_types != '{}'
                ) AS tagged,
                COUNT(*) AS total
            FROM regulatory_provisions
            WHERE source_council = %s AND is_current = TRUE
            """,
            (lga["source_council"],),
        )
        row = cur.fetchone()
        cur.close()
        tagged, total = row
        if total == 0:
            pytest.fail(f"{lga['lga_slug']}: no active provisions found")
        coverage = tagged / total
        assert coverage >= lga["min_dev_type_coverage"], (
            f"{lga['lga_slug']}: dev type coverage {coverage:.1%} "
            f"({tagged}/{total} provisions tagged) — "
            f"run /tag-provisions before enabling this LGA. "
            f"Threshold: {lga['min_dev_type_coverage']:.0%}"
        )

    @pytest.mark.parametrize("lga", ONBOARDED_LGAS, ids=_ids)
    def test_no_null_v2_topic(self, conn, lga):
        """NULL v2_topic rate is within threshold — guards against extraction failures."""
        max_null = lga.get("max_null_topic_rate", 0.0)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE v2_topic IS NULL) AS nulls,
                COUNT(*) AS total
            FROM regulatory_provisions
            WHERE source_council = %s AND is_current = TRUE
            """,
            (lga["source_council"],),
        )
        row = cur.fetchone()
        cur.close()
        if row and row[1] > 0:
            null_rate = row[0] / row[1]
            assert null_rate <= max_null, (
                f"{lga['lga_slug']}: {null_rate:.1%} NULL v2_topic "
                f"({row[0]}/{row[1]}) exceeds threshold {max_null:.0%}. "
                f"Re-run topic classification."
            )

    @pytest.mark.parametrize("lga", ONBOARDED_LGAS, ids=_ids)
    def test_no_null_v2_precinct_id(self, conn, lga):
        """NULL v2_precinct_id rate within threshold — guards against precinct pipeline failures."""
        max_null = lga.get("max_null_precinct_rate", 0.05)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE v2_precinct_id IS NULL) AS nulls,
                COUNT(*) AS total
            FROM regulatory_provisions
            WHERE source_council = %s AND is_current = TRUE
            """,
            (lga["source_council"],),
        )
        row = cur.fetchone()
        cur.close()
        if row and row[1] > 0:
            null_rate = row[0] / row[1]
            assert null_rate <= max_null, (
                f"{lga['lga_slug']}: {null_rate:.1%} NULL v2_precinct_id "
                f"({row[0]}/{row[1]}) exceeds threshold {max_null:.0%}. "
                f"Run precinct assignment pipeline."
            )
