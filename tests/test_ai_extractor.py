"""Tests for the pure helpers of the AI extraction engine (scripts/ai_extractor.py).

The provider calls (Haiku/Mistral) hit the network and aren't unit-tested; the
chunking, JSON parsing, dedupe, and section-shape mapping are pure and are.
"""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ai_extractor import (  # noqa: E402
    chunk_ranges, parse_provisions, dedupe_provisions, provisions_to_sections,
    _call_with_retry, _is_retryable, _PROVIDERS,
    _call_and_parse_with_empty_retry,
    coverage_gap, truncation_rate, COVERAGE_MIN_TOC,
)
import ai_extractor as _ai_extractor_mod  # noqa: E402


class TestChunkRanges:
    def test_covers_all_pages(self):
        r = chunk_ranges(197, 12)
        assert r[0] == (0, 12) and r[-1] == (192, 197)
        assert sum(b - a for a, b in r) == 197

    def test_exact_multiple(self):
        assert chunk_ranges(24, 12) == [(0, 12), (12, 24)]

    def test_empty_and_degenerate(self):
        assert chunk_ranges(0, 12) == []
        assert chunk_ranges(10, 0) == []


class TestParseProvisions:
    def test_object_wrapper(self):
        out = parse_provisions('{"provisions": [{"code": "1.1", "title": "A", "text": "x"}]}')
        assert out == [{"code": "1.1", "title": "A", "text": "x"}]

    def test_bare_array(self):
        assert parse_provisions('[{"code": "1.2"}]') == [{"code": "1.2"}]

    def test_code_fenced(self):
        assert parse_provisions('```json\n{"provisions": [{"code": "2.1"}]}\n```') == [{"code": "2.1"}]

    def test_garbage_and_empty(self):
        assert parse_provisions("not json at all") == []
        assert parse_provisions("") == []
        assert parse_provisions(None) == []

    def test_filters_non_dicts(self):
        assert parse_provisions('{"provisions": [{"code":"1"}, "junk", 3]}') == [{"code": "1"}]


class TestDedupe:
    def test_dedupes_by_code_keeps_first(self):
        out = dedupe_provisions([{"code": "1.1", "title": "first"},
                                 {"code": "1.1", "title": "dup"},
                                 {"code": "1.2"}])
        assert out == [{"code": "1.1", "title": "first"}, {"code": "1.2"}]

    def test_drops_blank_codes(self):
        assert dedupe_provisions([{"code": ""}, {"title": "no code"}, {"code": "  "}]) == []


class TestToSections:
    def test_maps_to_extractor_shape(self):
        secs = provisions_to_sections([{"code": "1.1", "title": "Background", "text": "body", "page": 9}])
        s = secs[0]
        assert s["section_number"] == "1.1"
        assert s["section_title"] == "Background"
        assert s["content"] == "body"
        assert s["tables"] == [] and s["page_start"] == 9 and s["page_end"] == 9 and s["pages"] == [9]

    def test_page_defaults_and_bad_page(self):
        assert provisions_to_sections([{"code": "2"}])[0]["page_start"] == 1
        assert provisions_to_sections([{"code": "2", "page": "x"}])[0]["page_start"] == 1

    def test_drops_codeless(self):
        assert provisions_to_sections([{"title": "no code", "text": "x"}]) == []


class TestCoverageGap:
    def _toc(self, n):  # a TOC of n distinct top-level codes (>= COVERAGE_MIN_TOC)
        return {f"{i}.1" for i in range(1, n + 1)}

    def test_sub_provisions_count_as_covered(self):
        toc = self._toc(10)  # 1.1 .. 10.1
        # extracted has each section only as sub-codes (1.1.1 etc.) — still covered
        extracted = {f"{i}.1.{j}" for i in range(1, 11) for j in (1, 2)}
        ratio, missing = coverage_gap(extracted, toc)
        assert ratio == 0.0 and missing == []

    def test_missing_sections_flagged(self):
        toc = self._toc(10)
        extracted = {f"{i}.1" for i in range(1, 5)}  # only 4 of 10 covered
        ratio, missing = coverage_gap(extracted, toc)
        assert ratio == 0.6
        assert "10.1" in missing

    def test_small_toc_never_judged(self):
        # below COVERAGE_MIN_TOC -> no opinion (avoids false positives on tiny chapters)
        toc = {f"{i}.1" for i in range(1, COVERAGE_MIN_TOC)}
        assert coverage_gap(set(), toc) == (0.0, [])

    def test_section_space_subitem_codes_count_as_covered(self):
        # regression: the AI emits "<section> <objective/control>" (e.g. "C4.1 O1"),
        # which must cover TOC section "C4.1". Before the fix this false-fired 100%.
        toc = {f"C4.{i}" for i in range(1, 11)}  # C4.1 .. C4.10
        extracted = {f"C4.{i} {sub}" for i in range(1, 11) for sub in ("O1", "C1", "C2")}
        ratio, missing = coverage_gap(extracted, toc)
        assert ratio == 0.0 and missing == []

    def test_bare_subitem_codes_do_not_cover_sections(self):
        # the real leichhardt failure: controls coded as bare "C1".."C38" (section
        # attribution lost across chunks) must NOT be credited to any TOC section.
        toc = {f"C4.{i}" for i in range(1, 11)}
        extracted = {f"C{i}" for i in range(1, 39)}  # C1..C38, no section prefix
        ratio, missing = coverage_gap(extracted, toc)
        assert ratio == 1.0 and len(missing) == 10


class TestSectionThreading:
    def test_build_prompt_without_section_is_base(self):
        from ai_extractor import PROMPT, _build_prompt
        assert _build_prompt(None) == PROMPT
        assert _build_prompt("") == PROMPT

    def test_build_prompt_carries_section(self):
        from ai_extractor import PROMPT, _build_prompt
        p = _build_prompt("C4.9")
        assert p != PROMPT and "C4.9" in p

    def test_section_regex_matches_real_sections_not_bare_items(self):
        from ai_extractor import _SECTION_RE
        for good in ("C4.9", "3.1", "A2.10.1", "C1.0"):
            assert _SECTION_RE.match(good), good
        for bad in ("C1", "O1", "C44", "C7", ""):
            assert not _SECTION_RE.match(bad), bad

    def test_prompt_requires_section_qualified_codes(self):
        from ai_extractor import PROMPT
        # regression: the prompt must explicitly forbid bare codes
        assert "section-qualified" in PROMPT.lower()
        assert "never a bare" in PROMPT.lower()


class TestTruncationRate:
    def test_ellipsis_flagged(self):
        rate, n = truncation_rate([
            "A full, complete provision that clearly is not truncated at all here.",
            "This one is cut off mid sentence and ends with...",
            "…",
        ])
        assert n == 2 and rate == 2 / 3

    def test_short_text_flagged_but_bare_refs_exempt(self):
        rate, n = truncation_rate([
            "See clause 3.2 for details",                    # bare ref -> exempt
            "x",                                             # too short -> flagged
            "A perfectly reasonable length provision body here that is fine.",
        ])
        assert n == 1

    def test_empty(self):
        assert truncation_rate([]) == (0.0, 0)


_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")


class TestSuspectReasonNewGuards:
    """suspect_reason lives in dcp_extract_changed; import it with heavy deps stubbed."""

    def test_coverage_and_truncation_surface(self):
        # import suspect_reason under the heavy-dep stubs
        _saved = {k: sys.modules.get(k) for k in _STUBS}
        for k in _STUBS:
            sys.modules[k] = MagicMock()
        sys.modules["dotenv"].load_dotenv = MagicMock()
        os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
        for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
            os.environ.setdefault(_k, "x")
        try:
            from dcp_extract_changed import suspect_reason
        finally:
            for k, v in _saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        cov = {"diff": {"status": "ok"}, "schema_fail": False,
               "coverage_fail": True, "coverage_missing": 8, "coverage_toc": 27}
        trunc = {"diff": {"status": "ok"}, "schema_fail": False, "coverage_fail": False,
                 "truncation_fail": True, "truncation_flagged": 5, "total_provisions": 30}
        assert suspect_reason(cov).startswith("coverage_fail")
        assert suspect_reason(trunc).startswith("truncation_fail")
        assert suspect_reason({"diff": {"status": "ok"}, "schema_fail": False}) is None


class TestFidelityGateIsDecoupled:
    """The one check that compares our output against the SOURCE document ran on
    12 of 19,649 review-queue rows ever — 0.06% — because it was gated on
    AI_EXTRACTION, a flag that also swaps the entire deterministic extractor for
    an LLM. Nobody was going to enable that in production just to get
    verification, so verification never ran.
    """

    @staticmethod
    def _load():
        _saved = {k: sys.modules.get(k) for k in _STUBS}
        for k in _STUBS:
            sys.modules[k] = MagicMock()
        sys.modules["dotenv"].load_dotenv = MagicMock()
        os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
        for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
            os.environ.setdefault(_k, "x")
        try:
            import dcp_extract_changed as mod
        finally:
            for k, v in _saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        return mod

    def test_it_runs_with_AI_EXTRACTION_UNSET(self, monkeypatch):
        """The whole point. This is the production configuration — AI_EXTRACTION
        is not set on the Railway dcp-extract service."""
        mod = self._load()
        monkeypatch.delenv("AI_EXTRACTION", raising=False)
        monkeypatch.delenv("DCP_FIDELITY_GATE", raising=False)
        assert mod.fidelity_gate_enabled() is True

    def test_it_does_not_depend_on_AI_EXTRACTION_either_way(self, monkeypatch):
        monkeypatch.delenv("DCP_FIDELITY_GATE", raising=False)
        mod = self._load()
        for val in ("1", "0", "true", "", "yes"):
            monkeypatch.setenv("AI_EXTRACTION", val)
            assert mod.fidelity_gate_enabled() is True, f"AI_EXTRACTION={val!r} must not decide this"

    def test_explicit_opt_out_is_honoured(self, monkeypatch):
        mod = self._load()
        for val in ("0", "false", "no", "off", "OFF", " 0 "):
            monkeypatch.setenv("DCP_FIDELITY_GATE", val)
            assert mod.fidelity_gate_enabled() is False, val

    def test_anything_else_leaves_it_ON(self, monkeypatch):
        """Opt-OUT, not opt-in: a typo must not silently disable verification."""
        mod = self._load()
        for val in ("", "1", "true", "on", "yes", "maybe", "TRUE"):
            monkeypatch.setenv("DCP_FIDELITY_GATE", val)
            assert mod.fidelity_gate_enabled() is True, val

    def test_the_call_site_no_longer_reads_AI_EXTRACTION(self):
        """Structural: the grading block must be gated on the new predicate.
        Three OTHER AI_EXTRACTION sites are legitimate and must survive — it
        swaps the extractor, selects that path per council, and runs railguards
        that only mean anything for LLM output."""
        mod = self._load()
        src = __import__("pathlib").Path(mod.__file__).read_text(encoding="utf-8")
        code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
        assert "if fidelity_gate_enabled():" in code
        assert code.count('os.getenv("AI_EXTRACTION", "").strip().lower()') == 3, (
            "expected exactly the three legitimate AI_EXTRACTION sites to remain"
        )


class TestOcrCallIsBounded:
    """A scalar requests timeout cannot bound this call.

    Measured 2026-08-14 on the live sweep: an ESTABLISHED socket to the Modal
    endpoint sat open 2472s against timeout=1800 and never fired, at 0.00s CPU.
    `timeout=N` is the maximum gap BETWEEN BYTES and resets on every byte, so a
    server that dribbles anything holds the nightly extraction open forever.

    These tests drive a REAL server that dribbles and never finishes. Asserting
    on the constant instead would pass against the broken code, because the old
    code also had a large number in it — the number was never the defect.
    """

    @staticmethod
    def _load():
        _saved = {k: sys.modules.get(k) for k in _STUBS}
        for k in _STUBS:
            sys.modules[k] = MagicMock()
        sys.modules["dotenv"].load_dotenv = MagicMock()
        os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
        for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
            os.environ.setdefault(_k, "x")
        try:
            import dcp_extract_changed as mod
        finally:
            for k, v in _saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        return mod

    @staticmethod
    def _serve(handler_cls):
        import http.server, threading
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv, f"http://127.0.0.1:{srv.server_port}/"

    @staticmethod
    def _real_requests():
        """⚠ conftest_mocks.py stubs `requests` for the whole suite so pure-logic
        tests run without native deps. These tests must drive a REAL socket — with
        the stub in place `requests.post(...)` returns a MagicMock that answers
        instantly, so a broken, unbounded implementation would sail through and
        the test would prove nothing. (It did: two of these passed against the
        mock before this was added.) Restore the genuine module for the call.
        """
        import contextlib, importlib

        @contextlib.contextmanager
        def _ctx():
            saved = sys.modules.pop("requests", None)
            try:
                real = importlib.import_module("requests")
                assert not isinstance(real, MagicMock), "requests is still stubbed"
                yield real
            finally:
                if saved is not None:
                    sys.modules["requests"] = saved
                else:
                    sys.modules.pop("requests", None)
        return _ctx()

    def test_a_SILENT_server_is_abandoned_within_the_read_timeout(self, tmp_path, monkeypatch):
        """The failure that actually bites: the endpoint stops responding.

        This is what the (connect, read) tuple buys. The old scalar timeout=1800
        made this wait 30 MINUTES; it now gives up after OCR_READ_TIMEOUT.

        ⚠ The OTHER failure — a server that dribbles forever — is deliberately
        NOT tested here, because it cannot be fixed in-thread. Three mechanisms
        were built and measured on 2026-08-14 and all three failed; the note in
        fetch_ocr_page_texts records them so nobody retries. Bounding that case
        needs an external subprocess cap (plan item P6.0). A test asserting a
        behaviour the code cannot have would be a test that lies.
        """
        import http.server, time

        class Silent(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                time.sleep(120)      # headers, then nothing

            def log_message(self, *a):
                pass

        mod = self._load()
        srv, url = self._serve(Silent)
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        monkeypatch.setenv("MODAL_OCR_URL", url)
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        monkeypatch.setattr(mod, "OCR_READ_TIMEOUT", 2)
        try:
            t0 = time.monotonic()
            with self._real_requests():
                out = mod.fetch_ocr_page_texts(pdf, expected_pages=1)
            elapsed = time.monotonic() - t0
        finally:
            srv.shutdown()
        assert out is None, "a silent endpoint must not yield OCR text"
        assert elapsed < 20, (
            f"waited {elapsed:.0f}s on a silent server against a 2s read timeout"
        )

    def test_a_healthy_server_still_returns_its_pages(self, tmp_path, monkeypatch):
        """The bound must not break the working path."""
        import http.server, json
        payload = json.dumps({"pages": ["page one text"]}).encode()

        class Ok(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *a):
                pass

        mod = self._load()
        srv, url = self._serve(Ok)
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        monkeypatch.setenv("MODAL_OCR_URL", url)
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        try:
            with self._real_requests():
                out = mod.fetch_ocr_page_texts(pdf, expected_pages=1)
        finally:
            srv.shutdown()
        assert out is not None and len(out) == 1

    def test_page_count_mismatch_still_refuses(self, tmp_path, monkeypatch):
        """The #836 guard must survive the rewrite: a short response would serve
        OCR text against the wrong source pages."""
        import http.server, json
        payload = json.dumps({"pages": ["a", "b"]}).encode()

        class Short(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *a):
                pass

        mod = self._load()
        srv, url = self._serve(Short)
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        monkeypatch.setenv("MODAL_OCR_URL", url)
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        try:
            with self._real_requests():
                assert mod.fetch_ocr_page_texts(pdf, expected_pages=5) is None
        finally:
            srv.shutdown()

    def test_the_timeout_is_a_tuple_not_a_scalar(self):
        """Structural backstop. A scalar cannot express 'fail fast on silence'
        and is what made the live hang invisible."""
        mod = self._load()
        src = __import__("pathlib").Path(mod.__file__).read_text(encoding="utf-8")
        lines = [l for l in src.splitlines() if not l.lstrip().startswith("#")]
        code = "\n".join(lines)
        assert "timeout=(OCR_CONNECT_TIMEOUT, OCR_READ_TIMEOUT)" in code
        # strip comments first: the WHY-note quotes the old value, and matching
        # prose would make this pass or fail on documentation rather than code.
        import re as _re
        assert not _re.search(r"timeout=\d", code), "a scalar timeout cannot bound a dribbling response"


class TestSplitPageAtHeadings:
    """_extract_sequential took ONE heading per page, so a page holding
    2.11.3 / 2.11.4 / 2.11.4.1 yielded only 2.11.3 and the other two clauses
    collided onto it. Marrickville part2-s11-fencing: 88 headings in the text,
    4 sections out, every clause under __preamble_*.
    """

    @staticmethod
    def _load():
        _saved = {k: sys.modules.get(k) for k in _STUBS}
        for k in _STUBS:
            sys.modules[k] = MagicMock()
        sys.modules["dotenv"].load_dotenv = MagicMock()
        os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
        for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
            os.environ.setdefault(_k, "x")
        try:
            from dcp_extract_changed import (
                split_page_at_headings, MULTI_HEADING_COUNCILS,
                COUNCIL_SECTION_RE_OVERRIDES,
            )
        finally:
            for k, v in _saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        return split_page_at_headings, MULTI_HEADING_COUNCILS, COUNCIL_SECTION_RE_OVERRIDES

    def test_zero_and_one_heading_pages_are_returned_untouched(self):
        """Bit-identical to the old behaviour, so non-split pages cannot regress."""
        split, _, res = self._load()
        rx = res["marrickville"]
        assert split("just body text\nno headings here", rx) == ["just body text\nno headings here"]
        one = "2.11.1 Fencing Objectives\nsome body text"
        assert split(one, rx) == [one]

    def test_three_headings_split_into_pre_plus_one_block_each(self):
        split, _, res = self._load()
        rx = res["marrickville"]
        page = ("carry-over from the previous page\n"
                "2.11.3 Front Fences\nbody three\n"
                "2.11.4 Side Fences\nbody four\n"
                "2.11.4.1 Corner Lots\nbody four one\n")
        segs = split(page, rx)
        assert len(segs) == 4, segs
        assert segs[0].strip() == "carry-over from the previous page"
        assert segs[1].startswith("2.11.3") and "body three" in segs[1]
        assert segs[2].startswith("2.11.4 ") and "body four" in segs[2]
        assert segs[3].startswith("2.11.4.1")

    def test_a_block_does_not_carry_the_next_blocks_body(self):
        """The whole point: content must land under its own clause."""
        split, _, res = self._load()
        rx = res["marrickville"]
        page = "2.11.3 Front Fences\nMAX HEIGHT 1.2m\n2.11.4 Side Fences\nMAX HEIGHT 1.8m\n"
        segs = split(page, rx)
        assert "1.8m" not in segs[1], "2.11.3 must not absorb 2.11.4's value"
        assert "1.2m" not in segs[2], "2.11.4 must not absorb 2.11.3's value"

    def test_a_page_opening_on_a_heading_has_an_empty_carry_over(self):
        split, _, res = self._load()
        rx = res["marrickville"]
        segs = split("2.11.3 Front Fences\nbody\n2.11.4 Side Fences\nbody\n", rx)
        assert segs[0] == ""

    def test_the_split_is_opt_in_and_marrickville_only(self):
        """Blast radius. Leichhardt and Parramatta were probed read-only and
        extract correctly today, so widening this needs a measurement first."""
        _, councils, _ = self._load()
        assert councils == {"marrickville"}

    def test_marrickville_section_re_no_longer_admits_clause_markers(self):
        """C8/O9 as 'sections' is what pushed body pages over the TOC guard."""
        _, _, res = self._load()
        rx = res["marrickville"]
        assert rx.search("C8 Some control text here") is None
        assert rx.search("O9 Some objective text here") is None
        assert rx.search("2.11.3 Front Fences") is not None


class TestSuspectAlertDedup:
    """The same two chapters alerted byte-identically every day 1–13 Aug 2026.

    An alert with no memory cannot tell "this is new" from "this is still true",
    so the channel stopped being read — and the numeric-value-change alerts
    sharing it went unactioned for weeks.
    """

    @staticmethod
    def _load():
        _saved = {k: sys.modules.get(k) for k in _STUBS}
        for k in _STUBS:
            sys.modules[k] = MagicMock()
        sys.modules["dotenv"].load_dotenv = MagicMock()
        os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
        for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
            os.environ.setdefault(_k, "x")
        try:
            from dcp_extract_changed import suspect_alert_key, unalerted_suspects
        finally:
            for k, v in _saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        return suspect_alert_key, unalerted_suspects

    @staticmethod
    def _ch(council, key, content_hash, missing=8):
        return {"council": council, "chapter_key": key, "content_hash": content_hash,
                "diff": {"status": "ok"}, "schema_fail": False,
                "coverage_fail": True, "coverage_missing": missing, "coverage_toc": 27}

    def test_an_unchanged_condition_alerts_once_then_never_again(self):
        key_of, unalerted = self._load()
        ch = self._ch("hornsby", "part-1-general", "aaa")
        assert unalerted([ch], {}) == [ch], "first sighting must alert"
        seen = {("hornsby", "part-1-general"): key_of(ch)}
        assert unalerted([ch], seen) == [], "an unchanged condition must not re-alert"

    def test_a_changed_pdf_re_alerts(self):
        key_of, unalerted = self._load()
        old = self._ch("hornsby", "part-1-general", "aaa")
        new = self._ch("hornsby", "part-1-general", "bbb")
        seen = {("hornsby", "part-1-general"): key_of(old)}
        assert unalerted([new], seen) == [new], "a new content_hash is new information"

    def test_a_changed_FAILURE_MODE_re_alerts_on_the_same_pdf(self):
        """Hash-only keying would silence this, and it is the case that matters:
        same document, now failing worse."""
        key_of, unalerted = self._load()
        old = self._ch("hornsby", "part-1-general", "aaa", missing=8)
        worse = self._ch("hornsby", "part-1-general", "aaa", missing=99)
        assert key_of(old) != key_of(worse)
        seen = {("hornsby", "part-1-general"): key_of(old)}
        assert unalerted([worse], seen) == [worse]

    def test_suppression_is_per_chapter_not_global(self):
        key_of, unalerted = self._load()
        a = self._ch("hornsby", "part-1-general", "aaa")
        b = self._ch("city_of_sydney", "section-3", "ccc")
        seen = {("hornsby", "part-1-general"): key_of(a)}
        assert unalerted([a, b], seen) == [b], "one chapter's silence must not mute another"

    def test_an_IDENTICAL_condition_on_a_DIFFERENT_chapter_still_alerts(self):
        """The discriminator between per-chapter and global suppression.

        Two chapters can carry the same content_hash (duplicate source PDFs are
        real in dcp_chapter_registry) and the same reason, hence the same key.
        Looking the key up globally instead of per (council, chapter_key) would
        silence the second chapter, which has never been alerted about. The
        weaker version of this test passed against exactly that mutation.
        """
        key_of, unalerted = self._load()
        a = self._ch("hornsby", "part-1-general", "same-pdf-hash")
        b = self._ch("blacktown", "part-a-car-parking", "same-pdf-hash")
        assert key_of(a) == key_of(b), "same hash + same reason => same key, by construction"
        seen = {("hornsby", "part-1-general"): key_of(a)}
        assert unalerted([a, b], seen) == [b], (
            "a chapter nobody has been told about must alert, even when an "
            "identical condition elsewhere has already been reported"
        )

    def test_a_non_suspect_chapter_has_no_key_and_never_alerts(self):
        key_of, unalerted = self._load()
        clean = {"council": "x", "chapter_key": "y", "content_hash": "h",
                 "diff": {"status": "ok"}, "schema_fail": False}
        assert key_of(clean) is None
        assert unalerted([clean], {}) == []


class TestRetry:
    def test_unknown_model_raises(self):
        try:
            _call_with_retry("does-not-exist", b"%PDF")
            assert False, "should have raised"
        except ValueError as e:
            assert "Unknown AI_MODEL" in str(e)

    def test_retryable_classification(self):
        import urllib.error
        err429 = urllib.error.HTTPError("u", 429, "rate", {}, None)
        err400 = urllib.error.HTTPError("u", 400, "bad", {}, None)
        assert _is_retryable(err429) is True
        assert _is_retryable(err400) is False
        assert _is_retryable(ValueError("x")) is False


class TestRetryableTimeouts:
    def test_read_timeout_is_retryable(self):
        import urllib.error
        from ai_extractor import _is_retryable
        # the chapter-d failure mode: a socket read timeout
        assert _is_retryable(TimeoutError("read timed out")) is True
        assert _is_retryable(urllib.error.URLError("timed out")) is True

    def test_http_500_retryable_400_not(self):
        import urllib.error
        from ai_extractor import _is_retryable
        e500 = urllib.error.HTTPError("u", 503, "x", {}, None)
        e400 = urllib.error.HTTPError("u", 400, "x", {}, None)
        assert _is_retryable(e500) is True
        assert _is_retryable(e400) is False


class TestSonnetProvider:
    """AI_MODEL=sonnet, added 2026-09-05 after Haiku's real-chapter mislabeling
    rate proved too high for unreviewed sections."""

    def test_sonnet_is_a_known_provider(self):
        assert "sonnet" in _PROVIDERS
        assert "haiku" in _PROVIDERS and "mistral" in _PROVIDERS

    def test_unknown_model_message_lists_sonnet(self):
        try:
            _call_with_retry("does-not-exist", b"%PDF")
            assert False, "should have raised"
        except ValueError as e:
            assert "sonnet" in str(e)


class TestAnthropicThinkingBlock:
    """Some Claude models prepend a ThinkingBlock (no .text) before the real
    response; content[0].text broke on it. Measured live 2026-09-05 calling
    claude-sonnet-5 -- AttributeError: 'ThinkingBlock' object has no attribute
    'text'."""

    def _stub_anthropic(self, monkeypatch, blocks):
        class _Msg:
            content = blocks

        class _Messages:
            def create(self, **kwargs):
                return _Msg()

        class _Client:
            def __init__(self):
                self.messages = _Messages()

        stub = MagicMock()
        stub.Anthropic = _Client
        monkeypatch.setitem(sys.modules, "anthropic", stub)

    def test_finds_text_block_after_a_thinking_block(self, monkeypatch):
        thinking = MagicMock(spec=[])  # no .text attribute at all, like ThinkingBlock
        text_block = MagicMock()
        text_block.text = '{"provisions": []}'
        self._stub_anthropic(monkeypatch, [thinking, text_block])
        result = _ai_extractor_mod._call_anthropic(b"%PDF", "prompt", "claude-sonnet-5")
        assert result == '{"provisions": []}'

    def test_plain_text_first_block_still_works(self, monkeypatch):
        text_block = MagicMock()
        text_block.text = "plain response"
        self._stub_anthropic(monkeypatch, [text_block])
        result = _ai_extractor_mod._call_anthropic(b"%PDF", "prompt", "claude-haiku-4-5")
        assert result == "plain response"

    def test_no_text_block_at_all_returns_empty_not_a_crash(self, monkeypatch):
        thinking = MagicMock(spec=[])
        self._stub_anthropic(monkeypatch, [thinking])
        result = _ai_extractor_mod._call_anthropic(b"%PDF", "prompt", "claude-sonnet-5")
        assert result == ""

    def test_max_tokens_leaves_room_for_thinking_plus_a_real_answer(self, monkeypatch):
        # Measured live 2026-09-05: a dense 23-page chunk's extended thinking
        # alone consumed the full 8000-token budget (thinking_tokens=8000,
        # stop_reason='max_tokens') before any answer was written -- content
        # held ONLY a ThinkingBlock. 20000 left room for ~16k of thinking AND
        # an 11k-char JSON answer on that same chunk. Also stays under 32000,
        # where the SDK refuses a non-streaming call outright ('Streaming is
        # required for operations that may take longer than 10 minutes').
        captured = {}

        class _Msg:
            content = [MagicMock(text="ok")]

        class _Messages:
            def create(self, **kwargs):
                captured.update(kwargs)
                return _Msg()

        class _Client:
            def __init__(self):
                self.messages = _Messages()

        stub = MagicMock()
        stub.Anthropic = _Client
        monkeypatch.setitem(sys.modules, "anthropic", stub)
        _ai_extractor_mod._call_anthropic(b"%PDF", "prompt", "claude-sonnet-5")
        assert captured["max_tokens"] == 20000
        assert captured["max_tokens"] < 32000


class TestEmptyParseRetry:
    """A non-trivial response that parses to zero provisions is retried (very
    likely truncated/malformed JSON), but a genuinely short empty-chunk
    response is accepted immediately. Measured live 2026-09-05: the identical
    chunk request, re-sent, returned 0 then 46 correctly-parsed provisions."""

    def test_retries_a_nontrivial_response_that_parses_empty(self, monkeypatch):
        calls = {"n": 0}
        long_but_empty = "x" * 300  # non-trivial length, parses to nothing
        good = '{"provisions": [{"code": "1.1", "title": "T", "text": "body"}]}'

        def fake_call_with_retry(model, pdf_bytes, prompt):
            calls["n"] += 1
            return long_but_empty if calls["n"] == 1 else good

        monkeypatch.setattr(_ai_extractor_mod, "_call_with_retry", fake_call_with_retry)
        provs = _call_and_parse_with_empty_retry("sonnet", b"%PDF", "prompt")
        assert calls["n"] == 2
        assert len(provs) == 1 and provs[0]["code"] == "1.1"

    def test_a_genuinely_short_empty_response_is_not_retried(self, monkeypatch):
        calls = {"n": 0}

        def fake_call_with_retry(model, pdf_bytes, prompt):
            calls["n"] += 1
            return '{"provisions": []}'  # short, genuinely empty

        monkeypatch.setattr(_ai_extractor_mod, "_call_with_retry", fake_call_with_retry)
        provs = _call_and_parse_with_empty_retry("sonnet", b"%PDF", "prompt")
        assert calls["n"] == 1
        assert provs == []

    def test_gives_up_after_max_retries_and_returns_empty(self, monkeypatch):
        calls = {"n": 0}
        long_but_empty = "x" * 300

        def fake_call_with_retry(model, pdf_bytes, prompt):
            calls["n"] += 1
            return long_but_empty

        monkeypatch.setattr(_ai_extractor_mod, "_call_with_retry", fake_call_with_retry)
        provs = _call_and_parse_with_empty_retry("sonnet", b"%PDF", "prompt")
        assert provs == []
        assert calls["n"] == 1 + _ai_extractor_mod._EMPTY_PARSE_MAX_RETRIES
