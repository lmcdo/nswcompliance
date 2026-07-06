"""Golden-sentence tests for DA determination results in the conveyancing PDF.

The OnlineDA API reports "Determined" without the result; the DA tracking
MapServer (services/da_outcome.py, already used by the Intelligence Brief)
carries ASSESMENT_RESULT. These tests lock the join and the exact summary
wording, and — critically — that a failed lookup produces NO result claim.

Pure-logic: no live HTTP, no reportlab.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from generate_conveyancing_report import (  # noqa: E402
    build_da_outcome_summary,
    enrich_das_with_outcomes,
)


def _da(number: str, status: str = "Determined") -> dict:
    return {
        "number": number,
        "address": "1 Test St",
        "description": "Dwelling",
        "status": status,
        "lodged": "2026-01-01",
        "distance_m": 50,
    }


class TestEnrichDasWithOutcomes:
    def test_matching_pan_gets_result_verbatim(self):
        das = enrich_das_with_outcomes(
            [_da("PAN-1"), _da("PAN-2")],
            {"PAN-1": "Refused", "PAN-2": "Deferred Commencement Consent"},
        )
        assert das[0]["outcome"] == "Refused"
        assert das[1]["outcome"] == "Deferred Commencement Consent"

    def test_unmatched_pan_gets_none(self):
        das = enrich_das_with_outcomes([_da("PAN-9")], {"PAN-1": "Refused"})
        assert das[0]["outcome"] is None

    def test_failed_lookup_marks_all_rows_none(self):
        """None map (failed lookup) → no row may carry a result claim."""
        das = enrich_das_with_outcomes([_da("PAN-1"), _da("PAN-2")], None)
        assert all(d["outcome"] is None for d in das)

    def test_whitespace_pan_matches_trimmed(self):
        das = enrich_das_with_outcomes([_da(" PAN-1 ")], {"PAN-1": "Refused"})
        # row "number" is trimmed for lookup only — enrichment still lands
        assert das[0]["outcome"] == "Refused"

    def test_none_das_passthrough(self):
        """das=None (failed DA fetch) stays None — renders "Not assessed"."""
        assert enrich_das_with_outcomes(None, {"PAN-1": "Refused"}) is None

    def test_empty_string_result_is_none(self):
        das = enrich_das_with_outcomes([_da("PAN-1")], {"PAN-1": ""})
        assert das[0]["outcome"] is None


class TestBuildDaOutcomeSummary:
    def test_counts_results_verbatim_lowercased(self):
        das = enrich_das_with_outcomes(
            [_da("PAN-1"), _da("PAN-2"), _da("PAN-3")],
            {"PAN-1": "Approved", "PAN-2": "Approved", "PAN-3": "Refused"},
        )
        s = build_da_outcome_summary(das)
        assert "for the 3 application(s) shown" in s
        assert "2 approved" in s
        assert "1 refused" in s
        assert "no recorded result" not in s

    def test_rows_without_result_reported_as_pending(self):
        das = enrich_das_with_outcomes(
            [_da("PAN-1"), _da("PAN-2")],
            {"PAN-1": "Approved"},
        )
        s = build_da_outcome_summary(das)
        assert "1 approved" in s
        assert "1 with no recorded result" in s

    def test_no_results_at_all_returns_none(self):
        """Mutation check: a failed lookup must yield NO sentence, not zeros."""
        das = enrich_das_with_outcomes([_da("PAN-1")], None)
        assert build_da_outcome_summary(das) is None

    def test_empty_and_none_inputs_return_none(self):
        assert build_da_outcome_summary([]) is None
        assert build_da_outcome_summary(None) is None

    def test_unusual_result_value_passes_through_verbatim(self):
        """Unknown future values must not be dropped or reworded."""
        das = enrich_das_with_outcomes(
            [_da("PAN-1")], {"PAN-1": "Withdrawn By Applicant"},
        )
        s = build_da_outcome_summary(das)
        assert "1 withdrawn by applicant" in s

    def test_summary_names_the_source(self):
        das = enrich_das_with_outcomes([_da("PAN-1")], {"PAN-1": "Refused"})
        s = build_da_outcome_summary(das)
        assert "NSW Planning Portal application tracker" in s
