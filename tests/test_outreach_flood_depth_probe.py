"""Claim 7's production depth probe judges the answer, not the fact that an answer came back.

prior-art-checked: tests for the new scripts/outreach_flood_depth_probe.py; no existing test calls the production
flood route.

The unit cases feed judge() production-shaped bodies. The fixture below is trimmed from the answer production gave
for the Tweed point on 2026-09-14 (persist=false), so a PASS here is a PASS on the real shape.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import outreach_flood_depth_probe as probe  # noqa: E402

TWEED_ANSWER = {"outputs": {"flood_studies": [{
    "study_key": "tweed", "study_name": "Tweed Valley Flood Study Update 2024", "source": "Tweed Shire Council / BMT",
    "design": {"20pct": {"depth_m": 0.58, "level_m_ahd": 1.4}, "1pct": {"depth_m": 2.01, "level_m_ahd": 2.82}},
    "historical": {"2022": {"depth_m": 2.78, "level_m_ahd": 3.6}}}]}}


def test_the_recorded_production_answer_passes():
    verdict, detail = probe.judge("tweed", 2.008, TWEED_ANSWER)
    assert verdict == probe.PASS, detail


def test_an_answer_that_names_a_level_only_study_fails():
    """Confusable negative: Hawkesbury answers with a flood LEVEL and no depth; a named study is not a depth."""
    body = {"outputs": {"flood_studies": [{"study_key": "hawkesbury",
                                           "design": {"1pct": {"depth_m": None, "level_m_ahd": 17.3}}}]}}
    verdict, detail = probe.judge("tweed", 2.008, body)
    assert verdict == probe.FAIL and "not named" in detail


def test_the_study_named_without_a_depth_fails():
    body = {"outputs": {"flood_studies": [{"study_key": "tweed",
                                           "design": {"1pct": {"depth_m": None, "level_m_ahd": 2.82}}}]}}
    verdict, detail = probe.judge("tweed", 2.008, body)
    assert verdict == probe.FAIL and "without a 1% AEP depth" in detail


def test_a_depth_from_the_wrong_cell_fails():
    body = {"outputs": {"flood_studies": [{"study_key": "tweed", "design": {"1pct": {"depth_m": 2.31}}}]}}
    assert probe.judge("tweed", 2.008, body)[0] == probe.FAIL


def test_no_flood_studies_at_all_fails():
    """The degraded answer when a host has no rasters: the route still returns 200 with an empty list."""
    assert probe.judge("tweed", 2.008, {"outputs": {"flood_studies": []}})[0] == probe.FAIL


def test_the_points_cover_exactly_the_studies_that_answer_depth():
    """Tied to the same source the published floodDepthStudies count is checked against."""
    import verify_coverage_stats as vcs

    keys = probe.depth_study_keys()
    assert keys == {p[0] for p in probe.POINTS}
    assert len(keys) == vcs.live_flood_depth_study_count()


def test_unreachable_is_unknown_and_an_http_error_is_a_failure(monkeypatch):
    monkeypatch.setattr(probe, "ask", lambda s, lat, lng: (None, "production could not be reached (timeout)", False))
    assert probe.flood_depth_delivered_in_production()[0] == probe.UNKNOWN
    monkeypatch.setattr(probe, "ask", lambda s, lat, lng: (None, "production returned HTTP 500", True))
    assert probe.flood_depth_delivered_in_production()[0] == probe.FAIL


def test_one_study_failing_fails_the_claim_even_when_others_pass(monkeypatch):
    def answer(study, lat, lng):
        if study == "redbank":
            return {"outputs": {"flood_studies": []}}, "", True
        expected = {p[0]: p[3] for p in probe.POINTS}[study]
        return {"outputs": {"flood_studies": [{"study_key": study, "design": {"1pct": {"depth_m": expected}}}]}}, "", True
    monkeypatch.setattr(probe, "ask", answer)
    verdict, detail = probe.flood_depth_delivered_in_production()
    assert verdict == probe.FAIL and "redbank: not named" in detail


@pytest.mark.parametrize("body", [
    [],
    [{"outputs": {}}],
    {"outputs": []},
    {"outputs": ["flood_studies"]},
    {"outputs": {"flood_studies": {"study_key": "tweed"}}},
    {"outputs": {"flood_studies": [{"study_key": "tweed", "design": ["1pct"]}]}},
    {"outputs": {"flood_studies": [{"study_key": "tweed", "design": {"1pct": 2.01}}]}},
])
def test_valid_json_of_the_wrong_shape_fails_rather_than_raising(body):
    assert probe.judge("tweed", 2.008, body)[0] == probe.FAIL


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity"])
def test_a_non_finite_depth_fails(raw):
    """json.loads accepts these tokens, and abs(NaN - expected) > tolerance is False."""
    body = json.loads('{"outputs": {"flood_studies": [{"study_key": "tweed", "design": {"1pct": {"depth_m": %s}}}]}}'
                      % raw)
    verdict, detail = probe.judge("tweed", 2.008, body)
    assert verdict == probe.FAIL and "without a 1% AEP depth" in detail


def _all_depths_correct(study, lat, lng):
    expected = {p[0]: p[3] for p in probe.POINTS}[study]
    return {"outputs": {"flood_studies": [{"study_key": study, "design": {"1pct": {"depth_m": expected}}}]}}, "", True


def test_correct_answers_from_a_host_other_than_production_are_unknown_not_a_pass(monkeypatch):
    monkeypatch.setattr(probe, "ask", _all_depths_correct)
    monkeypatch.setattr(probe, "PRODUCTION_API", "https://staging.example.com")
    verdict, detail = probe.flood_depth_delivered_in_production()
    assert verdict == probe.UNKNOWN and "not the production host" in detail


def test_the_production_host_with_a_trailing_slash_still_passes(monkeypatch):
    """Confusable negative for the host guard: the same origin written with a trailing slash is production."""
    monkeypatch.setattr(probe, "ask", _all_depths_correct)
    monkeypatch.setattr(probe, "PRODUCTION_API", probe.CANONICAL_PRODUCTION_API + "/")
    assert probe.flood_depth_delivered_in_production()[0] == probe.PASS


@pytest.mark.integration
def test_production_delivers_depth_for_every_depth_study():
    """The real layer: one POST per study to the production route, persist=false."""
    verdict, detail = probe.flood_depth_delivered_in_production()
    if verdict == probe.UNKNOWN:
        pytest.skip(detail)
    assert verdict == probe.PASS, detail
