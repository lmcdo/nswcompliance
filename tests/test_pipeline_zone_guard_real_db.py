"""The zone guard's ground truth, checked against production rather than a fixture.

tests/test_zone_guard_at_write.py pins the FILTER with a fixture zone set. That
cannot tell you whether the fixture resembles reality — whether `B2` is genuinely
absent from Ku-ring-gai's live vocabulary, or whether the council slug even resolves
to an LGA the ground truth knows about. If the slug does not resolve, the valid set
comes back empty, the guard correctly does nothing, and the whole fix is a no-op that
passes every unit test.

    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_pipeline_zone_guard_real_db.py -o addopts=""

Skipped by default: conftest_mocks stubs psycopg2 unless PYTEST_REAL_DB=1.

Nothing here writes. Every test is a SELECT plus a pure function call.
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# prior-art-checked: reuse -- scripts/dq_db.py already solved "find the right .env
# from inside a worktree", where a naive load_dotenv('.env') falls through to
# localhost defaults because a worktree has no .env of its own.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

# NOT a new literal. zone_taxonomy is the single source for which codes are
# legacy, and it is broader than the business zones this bug surfaced -- it also
# covers IN1-IN4, so the guard is checked against every retired code, not just
# the ones that happened to show up on 2026-09-10. A local list here would be a
# second copy free to drift, which is the DQ-30 failure mode itself.
from enrichment.config.zone_taxonomy import LEGACY_ZONES  # noqa: E402

RETIRED_BUSINESS_CODES = tuple(LEGACY_ZONES)


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... "
            "pytest -m database tests/test_pipeline_zone_guard_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def _conn():
    import psycopg2
    return psycopg2.connect(
        os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"],
        connect_timeout=10,
    )


def _truth_and_slugs():
    from enrichment.pipeline import _load_zone_ground_truth
    conn = _conn()
    try:
        return _load_zone_ground_truth(conn)
    finally:
        conn.close()


class TestGroundTruthIsReal:
    def test_the_ground_truth_actually_loads(self):
        """It fails soft by design — an empty result makes the guard a silent no-op,
        so 'it loaded' is the one thing a unit test can never tell you."""
        _skip_if_no_real_db()
        truth, slugs = _truth_and_slugs()
        assert truth, (
            "lep_zone_coverage returned nothing. The guard degrades to a no-op and "
            "retired codes can be written again — silently."
        )
        assert slugs, "no council slug resolved to an LGA; the guard cannot fire"

    def test_the_council_that_produced_the_defect_resolves_to_an_lga(self):
        """ku_ring_gai wrote all six bad rows on 2026-09-10. If its slug does not
        resolve, its valid set is empty and the guard is off for exactly the council
        that needs it."""
        _skip_if_no_real_db()
        truth, slugs = _truth_and_slugs()
        key = slugs.get("ku_ring_gai")
        assert key, "ku_ring_gai does not resolve to any LGA in the ground truth"
        assert truth.get(key), f"resolved to {key!r} but that LGA has no zone list"


class TestTheRetiredCodesAreGenuinelyRetired:
    def test_no_lga_still_lists_a_retired_business_zone(self):
        """The premise of the whole fix, stated as a falsifiable claim.

        If some LGA legitimately still lists B2, dropping it would be destroying good
        data — and this test says so instead of the guard quietly eating rows.
        """
        _skip_if_no_real_db()
        truth, _ = _truth_and_slugs()
        offenders = {
            lga: sorted(set(zones) & set(RETIRED_BUSINESS_CODES))
            for lga, zones in truth.items()
            if set(zones) & set(RETIRED_BUSINESS_CODES)
        }
        assert not offenders, (
            f"lep_zone_coverage still lists retired business zones for {offenders}. "
            f"Either the scrape is stale or these codes are not retired after all — "
            f"in which case this guard is destroying valid data."
        )

    def test_the_guard_drops_b2_for_the_real_kuringgai_vocabulary(self):
        """End to end on live data: the actual defect value, the actual zone list."""
        _skip_if_no_real_db()
        from enrichment.pipeline import keep_only_zones_valid_in_lga
        truth, slugs = _truth_and_slugs()
        valid = truth[slugs["ku_ring_gai"]]

        assert keep_only_zones_valid_in_lga(["B2"], valid) == ["ALL"]

        # Confusable negative on the same live set: a zone Ku-ring-gai really has
        # must survive, otherwise the guard is just deleting everything.
        real = sorted(valid)[0]
        assert keep_only_zones_valid_in_lga([real], valid) == [real], (
            f"{real} is in Ku-ring-gai's live zone list and must not be dropped"
        )


class TestBlastRadius:
    """How far can this reach? Measured, not assumed."""

    def test_the_guard_never_touches_a_row_that_already_has_zones(self):
        """The containment that makes everything else safe.

        run_applicability_tagging selects `WHERE v2_applicable_zones IS NULL`, so the
        guard only ever sees rows being written for the FIRST time. Existing rows are
        untouched no matter what the guard would have decided about them.

        An earlier version of this file asserted the guard was a no-op on all stored
        rows and FAILED, reporting 33 canterbury_bankstown rows it "would rewrite".
        That was a simulation of something the code cannot do -- those rows have
        zones, so the tagger never selects them. Pinning the real containment instead.
        """
        _skip_if_no_real_db()
        import pathlib as _p
        src = (_p.Path(__file__).resolve().parent.parent
               / "enrichment" / "pipeline.py").read_text(encoding="utf-8")
        body = src[src.index("def run_applicability_tagging("):]
        fetch = body[body.index("SELECT id, provision_text, document_id"):]
        fetch = fetch[:fetch.index("ORDER BY id")]
        assert "v2_applicable_zones IS NULL" in fetch, (
            "the tagger no longer restricts itself to un-tagged rows; the guard's "
            "blast radius is now every provision, which this PR never measured"
        )

    def test_any_change_the_guard_makes_is_a_strict_narrowing(self):
        """The direction of the edit is what bounds the damage.

        Removing a code that does not exist in the LGA cannot invent applicability;
        adding or substituting one could. So the invariant is: the output is always a
        subset of the input, or exactly ['ALL'] when nothing survives. Checked against
        every distinct stored combination in production, not a fixture.

        This also surfaces, without failing, that the guard WOULD narrow some rows if
        they were ever re-tagged -- canterbury_bankstown stores one more residential
        code than its live list actually contains. That is the guard working as
        designed on a code the LGA does not have, not a false positive; it is
        recorded in the QA report's residual risk rather than hidden.
        """
        _skip_if_no_real_db()
        from enrichment.pipeline import keep_only_zones_valid_in_lga
        truth, slugs = _truth_and_slugs()

        conn = _conn()
        try:
            cur = conn.cursor()
            cur.execute("SET statement_timeout = '30s'")
            cur.execute(
                """
                SELECT source_council, v2_applicable_zones, count(*)
                  FROM regulatory_provisions
                 WHERE is_current AND v2_is_actionable
                   AND v2_applicable_zones IS NOT NULL
                   AND source_council IS NOT NULL
                 GROUP BY 1, 2
                """
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        violations = []
        narrowed = 0
        for council, zones, n in rows:
            valid = truth.get(slugs.get(council), set())
            if not valid:
                continue
            before = list(zones)
            after = keep_only_zones_valid_in_lga(before, valid)
            if after == before:
                continue
            narrowed += n
            if after != ["ALL"] and not set(after).issubset(set(before)):
                violations.append((council, before, after, n))

        assert not violations, (
            f"the guard produced codes that were not in the input: {violations[:5]}. "
            f"It must only ever remove."
        )
        print(f"  [measured] {narrowed} stored rows WOULD narrow if re-tagged "
              f"(they are not re-tagged -- see the containment test above)")
