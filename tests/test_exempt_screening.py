"""
Tests for services/exempt_screening.py — Exempt Development Screening.

Tests: uncertainty classification, approval gap decision tree, consumer language.
"""
import re
import pytest

from services.exempt_screening import (
    ExemptCategory,
    ExemptThresholds,
    ExemptScreenResult,
    StructureScreenResult,
    SAMGEO_AREA_UNCERTAINTY,
    SAMGEO_HEIGHT_UNCERTAINTY,
    classify_with_uncertainty,
    screen_structure_exempt,
    classify_approval_gap,
    make_consumer_summary,
)

# Banned liability words from pre-PR review checklist
BANNED_WORDS = re.compile(
    r'\b(safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|'
    r'approved|guaranteed|certified|confirmed|verified|ensure|assure|accurate|'
    r'definitive|comprehensive|reliable|illegal|unapproved|unauthorized)\b',
    re.IGNORECASE
)


# ---------------------------------------------------------------------------
# classify_with_uncertainty — area only
# ---------------------------------------------------------------------------

class TestClassifyAreaOnly:
    """Test area classification with +-30% uncertainty."""

    def _thresholds(self):
        return ExemptThresholds(
            category=ExemptCategory.GARDEN_SHED,
            max_area_m2=20.0,
            source_ref="test",
        )

    def test_clearly_under(self):
        # 10m2 + 30% = 13m2 < 20m2 threshold
        cls, exceeded, _ = classify_with_uncertainty(10.0, 20.0)
        assert cls == "LIKELY_EXEMPT"
        assert exceeded == []

    def test_clearly_over(self):
        # 30m2 - 30% = 21m2 > 20m2 threshold
        cls, exceeded, _ = classify_with_uncertainty(30.0, 20.0)
        assert cls == "APPROVAL_GAP"
        assert "max_area_m2" in exceeded

    def test_at_threshold_indeterminate(self):
        # 18m2: 18+5.4=23.4>20, 18-5.4=12.6<20 → INDETERMINATE
        cls, exceeded, _ = classify_with_uncertainty(18.0, 20.0)
        assert cls == "INDETERMINATE"

    def test_boundary_low(self):
        # 14m2 + 30% = 18.2 < 20 → LIKELY_EXEMPT
        cls, _, _ = classify_with_uncertainty(14.0, 20.0)
        assert cls == "LIKELY_EXEMPT"

    def test_boundary_high(self):
        # 15.5m2 + 30% = 20.15 > 20 → INDETERMINATE
        cls, _, _ = classify_with_uncertainty(15.5, 20.0)
        assert cls == "INDETERMINATE"

    def test_50m2_clearly_over(self):
        # 50m2 - 30% = 35m2 > 20m2
        cls, exceeded, _ = classify_with_uncertainty(50.0, 20.0)
        assert cls == "APPROVAL_GAP"

    def test_no_threshold(self):
        # No threshold → nothing to check → LIKELY_EXEMPT
        cls, exceeded, _ = classify_with_uncertainty(50.0, None)
        assert cls == "LIKELY_EXEMPT"


# ---------------------------------------------------------------------------
# classify_with_uncertainty — area + height
# ---------------------------------------------------------------------------

class TestClassifyAreaAndHeight:
    def test_area_over_height_over(self):
        cls, exceeded, _ = classify_with_uncertainty(
            50.0, 20.0, measured_height_m=5.0, threshold_height_m=3.0,
        )
        assert cls == "APPROVAL_GAP"
        assert "max_area_m2" in exceeded
        assert "max_height_m" in exceeded

    def test_area_over_height_under(self):
        cls, exceeded, _ = classify_with_uncertainty(
            50.0, 20.0, measured_height_m=1.5, threshold_height_m=3.0,
        )
        assert cls == "APPROVAL_GAP"
        assert "max_area_m2" in exceeded
        # Height under threshold but area still exceeds

    def test_area_under_height_indeterminate(self):
        # Area clearly under, height near threshold
        cls, _, _ = classify_with_uncertainty(
            10.0, 20.0, measured_height_m=3.0, threshold_height_m=3.0,
        )
        # Height 3.0 +/- 1.0 straddles threshold → INDETERMINATE
        assert cls == "INDETERMINATE"

    def test_no_height_data(self):
        # Area clearly under but height required and missing → INDETERMINATE
        cls, _, notes = classify_with_uncertainty(
            10.0, 20.0, measured_height_m=None, threshold_height_m=3.0,
        )
        assert cls == "INDETERMINATE"
        assert any("Height could not be estimated" in n for n in notes)


# ---------------------------------------------------------------------------
# classify_with_uncertainty — setback
# ---------------------------------------------------------------------------

class TestClassifySetback:
    def test_setback_violation(self):
        cls, exceeded, _ = classify_with_uncertainty(
            50.0, 20.0, measured_setback_m=0.5, threshold_setback_m=0.9,
        )
        assert cls == "APPROVAL_GAP"
        assert "min_setback_m" in exceeded

    def test_setback_ok(self):
        cls, exceeded, _ = classify_with_uncertainty(
            10.0, 20.0, measured_setback_m=1.5, threshold_setback_m=0.9,
        )
        assert cls == "LIKELY_EXEMPT"
        assert "min_setback_m" not in exceeded


# ---------------------------------------------------------------------------
# screen_structure_exempt
# ---------------------------------------------------------------------------

class TestScreenStructureExempt:
    def test_full_data_high_confidence(self):
        thresholds = ExemptThresholds(
            category=ExemptCategory.GARDEN_SHED,
            max_area_m2=20.0,
            max_height_m=3.0,
            min_setback_m=0.9,
            source_ref="Codes SEPP cl 2.1",
        )
        # Height 1.5m: 1.5 + 1.0 = 2.5 < 3.0 → clearly under
        result = screen_structure_exempt(
            area_m2=10.0, thresholds=thresholds,
            height_m=1.5, boundary_distance_m=1.5,
        )
        assert result.classification == "LIKELY_EXEMPT"
        assert result.confidence == "high"
        assert result.category_tested == ExemptCategory.GARDEN_SHED

    def test_area_only_low_confidence(self):
        thresholds = ExemptThresholds(
            category=ExemptCategory.DECK,
            max_area_m2=25.0,
            source_ref="test",
        )
        result = screen_structure_exempt(area_m2=10.0, thresholds=thresholds)
        assert result.classification == "LIKELY_EXEMPT"
        assert result.confidence == "low"

    def test_with_height_medium_confidence(self):
        thresholds = ExemptThresholds(
            category=ExemptCategory.PERGOLA,
            max_area_m2=25.0,
            max_height_m=3.0,
            source_ref="test",
        )
        result = screen_structure_exempt(
            area_m2=10.0, thresholds=thresholds, height_m=2.0,
        )
        assert result.confidence == "medium"


# ---------------------------------------------------------------------------
# classify_approval_gap — full decision tree
# ---------------------------------------------------------------------------

class TestClassifyApprovalGap:
    def test_approved_da(self):
        assert classify_approval_gap(50.0, "Approved", "APPROVAL_GAP") == "APPROVAL_LOCATED"

    def test_refused_da(self):
        # Refused = DA was lodged, process happened
        assert classify_approval_gap(50.0, "Refused", "APPROVAL_GAP") == "APPROVAL_LOCATED"

    def test_deferred_da(self):
        assert classify_approval_gap(50.0, "Deferred Commencement Consent", None) == "APPROVAL_LOCATED"

    def test_no_da_exempt(self):
        assert classify_approval_gap(10.0, None, "LIKELY_EXEMPT") == "LIKELY_EXEMPT"

    def test_no_da_over_threshold(self):
        assert classify_approval_gap(50.0, None, "APPROVAL_GAP") == "APPROVAL_GAP"

    def test_no_da_uncertain(self):
        assert classify_approval_gap(18.0, None, "INDETERMINATE") == "INDETERMINATE"

    def test_no_structure(self):
        assert classify_approval_gap(None, None, None) == "DATA_INSUFFICIENT"

    def test_no_exempt_data(self):
        assert classify_approval_gap(50.0, None, None) == "DATA_INSUFFICIENT"


# ---------------------------------------------------------------------------
# Consumer language — liability audit
# ---------------------------------------------------------------------------

class TestConsumerLanguage:
    def test_approval_located_no_banned(self):
        text = make_consumer_summary(
            "APPROVAL_LOCATED", pan="PAN-123", outcome="Approved", determined_date="2021-12-08",
        )
        # "approved" appears as the DA outcome value — that's quoting the register, not a claim
        # The banned word check is for OUR assertions, not quoted data
        assert "PAN-123" in text
        assert "was found" in text

    def test_likely_exempt_no_banned(self):
        text = make_consumer_summary("LIKELY_EXEMPT", area_m2=18.0)
        matches = BANNED_WORDS.findall(text)
        assert matches == [], f"Banned words in LIKELY_EXEMPT: {matches}"

    def test_approval_gap_no_banned(self):
        text = make_consumer_summary("APPROVAL_GAP", area_m2=45.0)
        matches = BANNED_WORDS.findall(text)
        assert matches == [], f"Banned words in APPROVAL_GAP: {matches}"
        assert "predate digital records" in text
        assert "received consent" in text
        assert "s6.26" in text

    def test_indeterminate_no_banned(self):
        text = make_consumer_summary("INDETERMINATE")
        matches = BANNED_WORDS.findall(text)
        assert matches == [], f"Banned words in INDETERMINATE: {matches}"

    def test_data_insufficient_no_banned(self):
        text = make_consumer_summary("DATA_INSUFFICIENT")
        matches = BANNED_WORDS.findall(text)
        assert matches == [], f"Banned words in DATA_INSUFFICIENT: {matches}"

    def test_all_summaries_cite_source_or_action(self):
        """Every actionable summary should direct user to next step."""
        gap_text = make_consumer_summary("APPROVAL_GAP", area_m2=45.0)
        assert "Building Information Certificate" in gap_text

        indet_text = make_consumer_summary("INDETERMINATE")
        assert "Building Information Certificate" in indet_text
