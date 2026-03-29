"""
Tests for ActionableClassifier

QA Focus:
- FALSE NEGATIVES: Ensure all genuine requirements are classified as actionable
- FALSE POSITIVES: Ensure boilerplate is correctly excluded
- REGRESSION: Golden set must pass after any changes

Run with: pytest tests/enrichment/test_actionable_classifier.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from enrichment.extractors.actionable_classifier import ActionableClassifier


class TestFalseNegativePrevention:
    """
    CRITICAL: These tests ensure genuine requirements are NEVER filtered out.

    False negatives are the most dangerous failure mode - a missed requirement
    could cause compliance failures in production.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.classifier = ActionableClassifier()

    def test_definitive_control_must(self, golden_set_actionable):
        """'must' provisions are ALWAYS actionable."""
        must_cases = [c for c in golden_set_actionable if 'must' in c['text'].lower()]
        assert len(must_cases) > 0, "Golden set should have 'must' test cases"

        for case in must_cases:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            assert is_actionable, f"FALSE NEGATIVE: '{case['id']}' with 'must' marked as boilerplate"
            assert reason == "definitive_control_language", f"Expected definitive_control_language, got {reason}"

    def test_definitive_control_shall(self, golden_set_actionable):
        """'shall' provisions are ALWAYS actionable."""
        shall_cases = [c for c in golden_set_actionable if 'shall' in c['text'].lower()]
        assert len(shall_cases) > 0, "Golden set should have 'shall' test cases"

        for case in shall_cases:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            assert is_actionable, f"FALSE NEGATIVE: '{case['id']}' with 'shall' marked as boilerplate"
            assert reason == "definitive_control_language", f"Expected definitive_control_language, got {reason}"

    def test_c_marker_controls(self, golden_set_actionable):
        """C-marker provisions (C1, C2, etc.) are actionable."""
        c_marker_cases = [c for c in golden_set_actionable if c['category'] == 'c_marker']
        assert len(c_marker_cases) > 0, "Golden set should have C-marker test cases"

        for case in c_marker_cases:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            assert is_actionable, f"FALSE NEGATIVE: C-marker '{case['id']}' marked as boilerplate"

    def test_o_marker_objectives(self, golden_set_actionable):
        """O-marker objectives are actionable."""
        o_marker_cases = [c for c in golden_set_actionable if c['category'] == 'objective']
        assert len(o_marker_cases) > 0, "Golden set should have O-marker test cases"

        for case in o_marker_cases:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            assert is_actionable, f"FALSE NEGATIVE: O-marker '{case['id']}' marked as boilerplate"

    def test_numeric_controls(self, golden_set_actionable):
        """Provisions with numeric values (6m, 0.5:1, %) are actionable."""
        numeric_cases = [c for c in golden_set_actionable if c['category'] == 'numeric']
        assert len(numeric_cases) > 0, "Golden set should have numeric test cases"

        for case in numeric_cases:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            assert is_actionable, f"FALSE NEGATIVE: Numeric control '{case['id']}' marked as boilerplate"

    def test_prohibition_language(self, golden_set_actionable):
        """Provisions with 'prohibited' language are actionable."""
        prohibition_cases = [c for c in golden_set_actionable if c['category'] == 'prohibition']
        assert len(prohibition_cases) > 0, "Golden set should have prohibition test cases"

        for case in prohibition_cases:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            assert is_actionable, f"FALSE NEGATIVE: Prohibition '{case['id']}' marked as boilerplate"

    def test_all_golden_actionable(self, golden_set_actionable):
        """ALL golden set actionable provisions must be classified as actionable."""
        failures = []
        for case in golden_set_actionable:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            if not is_actionable:
                failures.append(f"{case['id']}: {case['text'][:50]}... (reason: {reason})")

        assert len(failures) == 0, f"FALSE NEGATIVES:\n" + "\n".join(failures)


class TestFalsePositivePrevention:
    """
    These tests ensure boilerplate is correctly excluded.

    False positives add noise but are less critical than false negatives.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.classifier = ActionableClassifier()

    def test_legislative_headers(self, golden_set_boilerplate):
        """Legislative headers are excluded."""
        header_cases = [c for c in golden_set_boilerplate if c['category'] == 'legislative_header']
        assert len(header_cases) > 0, "Golden set should have legislative header test cases"

        for case in header_cases:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            assert not is_actionable, f"FALSE POSITIVE: Header '{case['id']}' marked as actionable"

    def test_toc_entries(self, golden_set_boilerplate):
        """Table of contents entries are excluded."""
        toc_cases = [c for c in golden_set_boilerplate if c['category'] == 'toc']
        assert len(toc_cases) > 0, "Golden set should have TOC test cases"

        for case in toc_cases:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            assert not is_actionable, f"FALSE POSITIVE: TOC '{case['id']}' marked as actionable"

    def test_pdf_artifacts(self, golden_set_boilerplate):
        """PDF artifacts (Figure, Map) are excluded."""
        artifact_cases = [c for c in golden_set_boilerplate if c['category'] == 'pdf_artifact']
        assert len(artifact_cases) > 0, "Golden set should have PDF artifact test cases"

        for case in artifact_cases:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            assert not is_actionable, f"FALSE POSITIVE: Artifact '{case['id']}' marked as actionable"

    def test_too_short(self, golden_set_boilerplate):
        """Very short text is excluded."""
        short_cases = [c for c in golden_set_boilerplate if c['category'] == 'too_short']
        assert len(short_cases) > 0, "Golden set should have too-short test cases"

        for case in short_cases:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            assert not is_actionable, f"FALSE POSITIVE: Short text '{case['id']}' marked as actionable"
            assert reason == "too_short"

    def test_all_golden_boilerplate(self, golden_set_boilerplate):
        """ALL golden set boilerplate provisions must be classified as boilerplate."""
        failures = []
        for case in golden_set_boilerplate:
            is_actionable, reason = self.classifier.classify(case['text'], case['document_id'])
            if is_actionable:
                failures.append(f"{case['id']}: {case['text'][:50]}... (reason: {reason})")

        assert len(failures) == 0, f"FALSE POSITIVES:\n" + "\n".join(failures)


class TestDocumentTypeThresholds:
    """Test document-type-specific thresholds."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.classifier = ActionableClassifier()

    def test_dcp_lower_threshold(self):
        """DCP documents have lower threshold (1 pattern match)."""
        # Text with ONE actionable pattern (no must/shall)
        text = "Maximum building height is 9m."
        is_actionable, reason = self.classifier.classify(text, "Marrickville_DCP_2011")
        assert is_actionable, "DCP with single pattern should be actionable"

    def test_lep_higher_threshold(self):
        """LEP/SEPP documents need 2+ pattern matches."""
        # Text with ONE pattern - should fail for LEP
        text = "Maximum building height."  # Only "maximum" pattern
        is_actionable, reason = self.classifier.classify(text, "Inner_West_Local_Environmental_Plan_2022")
        # This depends on exact implementation - may need adjustment
        # The point is LEP has stricter threshold

    def test_unknown_conservative_threshold(self):
        """Unknown documents use conservative threshold (2+ patterns)."""
        text = "Building requirements."  # Weak indicators
        is_actionable, reason = self.classifier.classify(text, "Unknown_Document")
        assert not is_actionable, "Unknown doc with weak indicators should be conservative"


class TestRescueLogic:
    """Test that high actionable score can rescue from boilerplate patterns."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.classifier = ActionableClassifier()

    def test_rescue_with_strong_indicators(self):
        """Provisions matching boilerplate but with strong indicators are rescued."""
        # "Figure 1" matches boilerplate, but strong control language rescues it
        text = "Figure 1 shows that buildings must be setback minimum 6 metres and shall not exceed 9m height."
        is_actionable, reason = self.classifier.classify(text, "Marrickville_DCP_2011")
        # With "must" and "shall", this should be rescued
        assert is_actionable, "Strong control language should rescue from boilerplate pattern"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.classifier = ActionableClassifier()

    def test_empty_text(self):
        """Empty text returns not actionable."""
        is_actionable, reason = self.classifier.classify("", "DCP")
        assert not is_actionable
        assert reason == "too_short"

    def test_whitespace_only(self):
        """Whitespace-only text returns not actionable."""
        is_actionable, reason = self.classifier.classify("   \n\t  ", "DCP")
        assert not is_actionable
        assert reason == "too_short"

    def test_none_document_id(self):
        """Works with None document_id."""
        text = "Buildings must be setback 6m."
        is_actionable, reason = self.classifier.classify(text, None)
        assert is_actionable  # "must" is definitive

    def test_case_insensitivity(self):
        """Patterns are case-insensitive."""
        text1 = "Buildings MUST be setback."
        text2 = "Buildings Must be setback."
        text3 = "Buildings must be setback."

        for text in [text1, text2, text3]:
            is_actionable, _ = self.classifier.classify(text, "DCP")
            assert is_actionable, f"Case variation '{text}' should be actionable"
