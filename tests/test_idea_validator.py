"""Tests for idea_validator — KE parsing, report formatting, JSON extraction."""

import json
import os
import tempfile

import pytest

from scripts.idea_validator import (
    _extract_json,
    format_report,
    parse_ke_data,
)


# ── KE Data Parsing ──────────────────────────────────────────────────


class TestParseKEData:
    def test_standard_csv(self, tmp_path):
        csv_file = tmp_path / "keywords.csv"
        csv_file.write_text(
            "Keyword,Vol,CPC,Competition\n"
            "plumbing software,1300,39.00,0.85\n"
            "plumber quoting app,480,12.50,0.42\n"
            "flat rate plumbing,2200,5.20,0.65\n"
        )
        result = parse_ke_data(str(csv_file))
        assert result["keyword_count"] == 3
        assert result["total_monthly_volume"] == 1300 + 480 + 2200
        assert result["max_cpc"] == 39.00
        assert result["top_by_volume"][0]["keyword"] == "flat rate plumbing"

    def test_formatted_volume_with_commas(self, tmp_path):
        csv_file = tmp_path / "keywords.csv"
        csv_file.write_text(
            "Keyword,Vol,CPC,Competition\n"
            "genealogy research,\"12,500\",2.10,0.30\n"
        )
        result = parse_ke_data(str(csv_file))
        assert result["total_monthly_volume"] == 12500

    def test_cpc_with_dollar_sign(self, tmp_path):
        csv_file = tmp_path / "keywords.csv"
        csv_file.write_text(
            "Keyword,Vol,CPC,Competition\n"
            "plumber software,500,$39.00,0.42\n"
        )
        result = parse_ke_data(str(csv_file))
        assert result["avg_cpc"] == 39.00

    def test_empty_csv(self, tmp_path):
        csv_file = tmp_path / "keywords.csv"
        csv_file.write_text("Keyword,Vol,CPC,Competition\n")
        result = parse_ke_data(str(csv_file))
        assert result == {}

    def test_missing_file(self):
        result = parse_ke_data("/nonexistent/path.csv")
        assert result == {}

    def test_high_intent_count(self, tmp_path):
        csv_file = tmp_path / "keywords.csv"
        csv_file.write_text(
            "Keyword,Vol,CPC,Competition\n"
            "cheap plumbing,500,0.80,0.2\n"
            "plumber pricing software,200,15.00,0.9\n"
            "flat rate book plumbing,100,39.00,0.8\n"
        )
        result = parse_ke_data(str(csv_file))
        assert result["high_intent_keywords"] == 2  # CPC > $2


# ── JSON Extraction ───────────────────────────────────────────────────


class TestExtractJSON:
    def test_plain_json(self):
        text = '{"key": "value"}'
        assert _extract_json(text) == {"key": "value"}

    def test_json_with_markdown_fences(self):
        text = '```json\n{"key": "value"}\n```'
        assert _extract_json(text) == {"key": "value"}

    def test_json_with_plain_fences(self):
        text = '```\n{"key": "value"}\n```'
        assert _extract_json(text) == {"key": "value"}

    def test_json_with_whitespace(self):
        text = '\n  {"key": "value"}  \n'
        assert _extract_json(text) == {"key": "value"}


# ── Report Formatting ─────────────────────────────────────────────────


class TestFormatReport:
    def _make_analysis(self, verdict="PASS"):
        return {
            "overall_verdict": verdict,
            "overall_summary": "Test summary.",
            "checks": [
                {"name": "competitor_depth", "verdict": "PASS",
                 "summary": "No major competitor found.", "evidence": ["Evidence 1"]},
                {"name": "data_access", "verdict": "CAUTION",
                 "summary": "API is gated.", "evidence": ["TOS restricts commercial use"]},
                {"name": "incumbent_ai_roadmap", "verdict": "PASS",
                 "summary": "No AI plans found.", "evidence": []},
                {"name": "cold_start", "verdict": "PASS",
                 "summary": "Day 1 value exists.", "evidence": ["Pre-loaded data"]},
                {"name": "support_model_fit", "verdict": "PASS",
                 "summary": "Self-serve demographic.", "evidence": ["Tech-savvy users"]},
            ],
            "scores": {
                "demand": 7, "defensibility": 4, "solo_founder_fit": 8,
                "time_to_first_revenue_weeks": 6, "llm_leverage_depth": 9,
            },
            "what_could_go_wrong": ["Competitor copies feature", "API rate limits"],
            "next_steps": ["Trial competitor product", "Apply for API access"],
        }

    def test_report_contains_verdict(self):
        report = format_report("test idea", {}, self._make_analysis("KILL"), {}, 0, "standard")
        assert "VERDICT: KILL" in report

    def test_report_contains_all_checks(self):
        report = format_report("test idea", {}, self._make_analysis(), {}, 0, "standard")
        assert "Competitor Depth" in report
        assert "Data Access" in report
        assert "Incumbent Ai Roadmap" in report
        assert "Cold Start" in report
        assert "Support Model Fit" in report

    def test_report_contains_scores(self):
        report = format_report("test idea", {}, self._make_analysis(), {}, 0, "standard")
        assert "7/10" in report  # demand
        assert "~6 weeks" in report

    def test_report_contains_ke_data(self):
        ke = {"keyword_count": 5, "total_monthly_volume": 10000,
              "avg_cpc": 5.50, "max_cpc": 39.00, "high_intent_keywords": 3,
              "top_by_volume": [{"keyword": "test kw", "volume": 5000, "cpc": 5.5}]}
        report = format_report("test idea", {}, self._make_analysis(), ke, 0, "standard")
        assert "10,000" in report
        assert "$5.50" in report

    def test_report_contains_what_could_go_wrong(self):
        report = format_report("test idea", {}, self._make_analysis(), {}, 0, "standard")
        assert "Competitor copies feature" in report

    def test_report_contains_next_steps(self):
        report = format_report("test idea", {}, self._make_analysis(), {}, 0, "standard")
        assert "Trial competitor product" in report

    def test_report_contains_decomposition(self):
        decomp = {"target_customer": "solo plumbers", "core_value_prop": "fast quoting",
                   "data_dependencies": ["BLS data"], "incumbent_platforms": ["Jobber"],
                   "support_model_expectation": "phone/text"}
        report = format_report("test idea", decomp, self._make_analysis(), {}, 0, "standard")
        assert "solo plumbers" in report
        assert "BLS data" in report
