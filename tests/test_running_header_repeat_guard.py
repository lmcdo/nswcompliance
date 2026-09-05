"""Tests for is_running_header_repeat() in dcp_extract_changed.py -- the guard
that decides whether a heading match repeating the already-open section's own
number is a genuine running page-header, or a document reusing that number
much later for unrelated content (its own Appendices reusing the main body's
numbering scheme).

Pure decision-logic tests (no PDF I/O), per this module's own convention (see
sibling tests/test_section_divider_guard.py). Found live 2026-09-05 on
marrickville/part7-s3-sex-industry: a real second heading, "7.3.7 Appendix 3 -
Health standards...", appeared 12+ pages after the original 7.3.7 opened, and
the un-guarded version of this rule swallowed it as a repeated header, merging
7 real sections' worth of later content into the section still open.
"""
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
           "R2_BUCKET_NAME", "R2_ENDPOINT_URL", "R2_PUBLIC_URL"):
    os.environ.setdefault(_k, "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
sys.modules["dotenv"].load_dotenv = MagicMock()
try:
    from dcp_extract_changed import is_running_header_repeat  # noqa: E402
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v


class TestGenuineRunningHeader:
    def test_same_code_next_page_is_a_repeat(self):
        # "2.1 Urban Design" atop the very next page of section 2.1.
        assert is_running_header_repeat("2.1", "2.1", page_num=6, last_confirmed_page=5) is True

    def test_parent_prefix_is_a_repeat(self):
        # Marrickville prints the parent's running header atop pages of a child
        # section, e.g. "2.1" heading while inside "2.1.1.3".
        assert is_running_header_repeat("2.1.1.3", "2.1", page_num=6, last_confirmed_page=5) is True

    def test_same_page_confirms_immediately(self):
        assert is_running_header_repeat("7.3.7", "7.3.7", page_num=13, last_confirmed_page=13) is True

    def test_repeat_within_slack_gap(self):
        # A section spanning a blank/table-only page with no text match --
        # the header confirms again 2 pages later, still within tolerance.
        assert is_running_header_repeat("4.6", "4.6", page_num=10, last_confirmed_page=8) is True


class TestReusedNumberIsNotARepeat:
    def test_the_real_marrickville_sex_industry_case(self):
        # 7.3.7 opened on page 13; its own Appendix 3 reuses "7.3.7" on page
        # 23 -- 10 pages later. Must be treated as a NEW section.
        assert is_running_header_repeat("7.3.7", "7.3.7", page_num=23, last_confirmed_page=13) is False

    def test_just_past_the_slack_gap(self):
        assert is_running_header_repeat("4.6", "4.6", page_num=11, last_confirmed_page=8) is False

    def test_different_code_entirely_is_never_a_repeat(self):
        assert is_running_header_repeat("7.3.6", "7.3.7", page_num=21, last_confirmed_page=20) is False

    def test_child_code_is_not_a_parent_repeat(self):
        # The reverse direction of the parent-prefix case: being inside "2.1"
        # and seeing "2.1.1.3" is a genuinely deeper heading, not a repeat.
        assert is_running_header_repeat("2.1", "2.1.1.3", page_num=6, last_confirmed_page=5) is False
