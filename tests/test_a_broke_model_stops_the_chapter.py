"""A model that cannot run must stop the chapter, not hand it to the regex reader.

WHAT HAPPENED, 2026-09-27
-------------------------
`dcp-extract` ran nightly and alerted `🚨 dcp-extract failed (exit 1)`. The cause
was `429 credit_balance_exhausted` from the provider: 11 of 11 chapters failed
*after* downloading from R2 successfully. The alert carried none of that -- it
ships the last 2,000 bytes of stderr, which was a `SyntaxWarning` from an
unrelated config file.

The failure mode this file exists to prevent is the QUIET one, which would have
been far worse than the loud one: a chosen model fails on billing, and the
chapter is read instead by the regex/geometry reader -- which needs per-council
config, cannot read a two-column council, and has produced junk section codes on
every council that lacked it. The provisions would then be committed as a normal
re-extraction, with no error anywhere, from a reader nobody chose.

THE DISTINCTION BEING LOCKED
----------------------------
Two states look similar and must behave differently, and conflating them is how
this would regress:

  NO PROVIDER KEY AT ALL -> fall back to the regex reader, loudly.
      Deliberate, and tested in tests/test_ai_model_default_follows_the_keys.py.
      The nightly Railway service was never keyed, and failing hard there would
      have stopped every council's extraction to enable something that could not
      run on that service.

  A KEY IS PRESENT AND THE PROVIDER REFUSES -> raise. Stop the chapter.
      This one. A model was chosen, so the regex reader's per-council config was
      not consulted and its page maps were skipped. Falling back here is not a
      degraded read, it is a DIFFERENT reader silently substituted mid-run.

MEASURED CONFIGURATION THIS GUARDS, read from Railway 2026-09-28
----------------------------------------------------------------
    dcp-extract       AI_MODEL=sol   OPENAI_API_KEY set     <- correct shape
    dcp-extract-all   AI_MODEL unset  ANTHROPIC_API_KEY + MISTRAL_API_KEY,
                                      and NO OPENAI_API_KEY

So `dcp-extract-all` resolves to `sonnet` by preference order, against an
Anthropic account that answered "You have no credits remaining" on 2026-09-27.
That service cannot reach `sol` at all -- it has no OpenAI key. The env repair is
a production change and belongs to the operator; what is enforced here is that
when it does fail, it fails.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# `scripts.ai_extractor`, NOT a bare `import ai_extractor`. Both spellings work
# because scripts/ is on sys.path in this repo, and they produce TWO SEPARATE
# module objects -- so patching one leaves the other untouched. dcp_extract_changed
# does `from scripts.ai_extractor import ai_extract_chapter` inside extract(), so
# the package spelling is the one whose attributes it reads. Getting this wrong made
# two of the tests below pass on a FileNotFoundError instead of on the behaviour
# they claim to check, which is a test that proves nothing.
import scripts.ai_extractor as ai  # noqa: E402
import scripts.dcp_extract_changed as dec  # noqa: E402


class _RateLimit(Exception):
    """Shaped like the provider SDK's 429: the retry test reads `status_code`."""

    status_code = 429

    def __init__(self, msg="429 credit_balance_exhausted"):
        super().__init__(msg)


@pytest.fixture
def ai_on(monkeypatch):
    """AI extraction enabled with exactly one provider key present."""
    monkeypatch.delenv("AI_EXTRACTION", raising=False)  # default is ON
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "MISTRAL_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(ai.time, "sleep", lambda _s: None)  # no real backoff
    return monkeypatch


def _extractor() -> dec.DCPExtractor:
    """A DCPExtractor over a path that is never opened on the LLM path.

    The constructor does not read the file, and `extract()` reaches
    ai_extract_chapter before anything touches it -- so if the PDF is ever
    opened, that itself means the regex reader ran.
    """
    return dec.DCPExtractor(Path("does-not-exist.pdf"), "doc-1", council="marrickville")


class TestAProviderRefusalStopsTheChapter:
    def test_extract_raises_rather_than_returning_sections(self, ai_on, monkeypatch):
        monkeypatch.setattr(ai, "ai_extract_chapter",
                            lambda *a, **k: (_ for _ in ()).throw(_RateLimit()))
        with pytest.raises(Exception) as exc:
            _extractor().extract()
        assert "429" in str(exc.value) or isinstance(exc.value, _RateLimit)

    def test_the_regex_reader_is_never_reached(self, ai_on, monkeypatch):
        """The whole point. If `_extract_sequential` runs, a chapter has been read by
        a reader nobody chose, and the result would commit as a normal re-extraction."""
        ran: list[int] = []
        monkeypatch.setattr(dec.DCPExtractor, "_extract_sequential",
                            lambda self: ran.append(1) or [])
        monkeypatch.setattr(ai, "ai_extract_chapter",
                            lambda *a, **k: (_ for _ in ()).throw(_RateLimit()))
        with pytest.raises(Exception):
            _extractor().extract()
        assert ran == [], "the chapter fell back to the regex/geometry reader"

    def test_reader_used_is_not_relabelled_regex(self, ai_on, monkeypatch):
        """`reader_used` decides downstream whether the two-column warning applies.
        A failed LLM read that reports itself as the regex reader would move a
        chapter into the wrong evidence class."""
        ext = _extractor()
        monkeypatch.setattr(ai, "ai_extract_chapter",
                            lambda *a, **k: (_ for _ in ()).throw(_RateLimit()))
        with pytest.raises(Exception):
            ext.extract()
        assert ext.reader_used != "regex"
        assert ext.reader_used == "llm:sonnet"

    def test_the_pdf_is_never_opened(self, ai_on, monkeypatch):
        """A nonexistent path. Any fallback would raise FileNotFoundError instead of
        the provider's error, so the error type itself proves no fallback happened."""
        monkeypatch.setattr(ai, "ai_extract_chapter",
                            lambda *a, **k: (_ for _ in ()).throw(_RateLimit()))
        with pytest.raises(_RateLimit):
            _extractor().extract()


class TestChunkLossAlsoStopsTheChapter:
    """The other way a model can produce a wrong answer instead of no answer."""

    def test_chunk_loss_propagates(self, ai_on, monkeypatch):
        monkeypatch.setattr(
            ai, "ai_extract_chapter",
            lambda *a, **k: (_ for _ in ()).throw(ai.ChunkLoss("2 of 5 chunks")))
        with pytest.raises(ai.ChunkLoss):
            _extractor().extract()

    def test_chunk_loss_does_not_fall_back_either(self, ai_on, monkeypatch):
        ran: list[int] = []
        monkeypatch.setattr(dec.DCPExtractor, "_extract_sequential",
                            lambda self: ran.append(1) or [])
        monkeypatch.setattr(
            ai, "ai_extract_chapter",
            lambda *a, **k: (_ for _ in ()).throw(ai.ChunkLoss("2 of 5 chunks")))
        with pytest.raises(ai.ChunkLoss):
            _extractor().extract()
        assert ran == []


class TestARetryableErrorThatNeverClearsStillRaises:
    """A 429 is retryable, and credit exhaustion is a 429 that will never clear.

    Retrying it is harmless; SWALLOWING it after the retries would not be. The
    worst possible outcome is returning an empty section list, because zero
    provisions from a real chapter reads downstream as a chapter that legitimately
    lost its content.
    """

    def test_a_persistent_429_raises_out_of_call_with_retry(self, ai_on, monkeypatch):
        calls: list[int] = []

        def _always_429(pdf_bytes, prompt):
            calls.append(1)
            raise _RateLimit()

        monkeypatch.setitem(ai._PROVIDERS, "sonnet", _always_429)
        with pytest.raises(_RateLimit):
            ai._call_with_retry("sonnet", b"%PDF-", "prompt")
        assert len(calls) == ai._MAX_RETRIES, (
            "a retryable error must exhaust its retries before raising"
        )

    def test_it_does_not_return_an_empty_list(self, ai_on, monkeypatch):
        """Explicit, because `return []` is the mutation this test class exists for."""
        monkeypatch.setitem(
            ai._PROVIDERS, "sonnet",
            lambda p, pr: (_ for _ in ()).throw(_RateLimit()))
        try:
            result = ai._call_with_retry("sonnet", b"%PDF-", "prompt")
        except Exception:
            return  # raising is the required behaviour
        pytest.fail(f"a permanently-429 provider returned {result!r} instead of raising")

    def test_a_429_is_classified_retryable(self, ai_on):
        assert ai._is_retryable(_RateLimit()) is True


class TestANamedModelWithoutItsKeyDoesNotSubstituteAnother:
    """`AI_MODEL` bypasses the preference list entirely, so the key check that
    protects the default cannot protect an explicit choice.

    `AI_MODEL=sol` with no `OPENAI_API_KEY` must raise -- not quietly use the
    Anthropic key that happens to be present, and not fall through to the regex
    reader. Which model read a chapter has to be true, or a later regression is
    unattributable.
    """

    def test_sol_without_its_key_is_not_an_available_reader(self, ai_on, monkeypatch):
        """`llm_reader_available()` is the production decision, and it is what keeps a
        named-but-unkeyed model from bypassing a council's hand-built page map. Asserted
        through that function rather than by calling `_call_sol`: tests/conftest.py
        replaces every provider entry point with a refusal so the suite can never
        phone a paid API, so a direct call would prove only that the ban works."""
        monkeypatch.setenv("AI_MODEL", "sol")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert dec.llm_reader_available() is False

    def test_sol_with_its_key_is_available(self, ai_on, monkeypatch):
        monkeypatch.setenv("AI_MODEL", "sol")
        monkeypatch.setenv("OPENAI_API_KEY", "x")
        assert dec.llm_reader_available() is True

    def test_the_anthropic_key_does_not_make_sol_available(self, ai_on, monkeypatch):
        """ANTHROPIC_API_KEY is set by the fixture. A named model must not be reported
        available on the strength of a DIFFERENT provider's key."""
        monkeypatch.setenv("AI_MODEL", "sol")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert dec.llm_reader_available() is False
        monkeypatch.delenv("AI_MODEL")
        assert dec.llm_reader_available() is True  # unnamed: sonnet IS keyed

    def test_the_guard_names_the_key_it_needs(self):
        """The runtime error a keyless sol run produces has to say what to set."""
        src = (ROOT / "scripts" / "ai_extractor.py").read_text(encoding="utf-8")
        assert "AI_MODEL=sol needs OPENAI_API_KEY" in src

    def test_it_does_not_switch_to_the_configured_provider(self, ai_on, monkeypatch):
        """ANTHROPIC_API_KEY is set by the fixture. A named model must not borrow it."""
        monkeypatch.setenv("AI_MODEL", "sol")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        called: list[str] = []
        monkeypatch.setitem(ai._PROVIDERS, "sonnet",
                            lambda p, pr: called.append("sonnet") or "[]")
        with pytest.raises(Exception):
            ai.ai_extract_chapter(Path("does-not-exist.pdf"), "marrickville")
        assert called == [], "an explicit AI_MODEL was silently replaced"

    def test_an_unknown_model_name_raises_rather_than_defaulting(self, ai_on):
        with pytest.raises(ValueError) as exc:
            ai._call_with_retry("gpt-imaginary", b"%PDF-", "prompt")
        assert "Unknown AI_MODEL" in str(exc.value)


class TestTheDeliberateFallbackIsStillThere:
    """Guarding the distinction from the other side: narrowing the no-key fallback
    would stop every council's nightly extraction on the unkeyed service."""

    def test_no_key_at_all_still_falls_back_to_regex(self, monkeypatch):
        for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "MISTRAL_API_KEY"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.delenv("AI_MODEL", raising=False)
        monkeypatch.delenv("AI_EXTRACTION", raising=False)
        ran: list[int] = []
        monkeypatch.setattr(dec.DCPExtractor, "_extract_sequential",
                            lambda self: ran.append(1) or [])
        monkeypatch.setattr(dec.DCPExtractor, "_maybe_route_via_ocr", lambda self: None)
        ext = _extractor()
        ext.extract()
        assert ran == [1]
        assert ext.reader_used == "regex"

    def test_and_says_so_out_loud(self, monkeypatch, capsys):
        for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "MISTRAL_API_KEY"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.delenv("AI_MODEL", raising=False)
        monkeypatch.delenv("AI_EXTRACTION", raising=False)
        monkeypatch.setattr(dec.DCPExtractor, "_extract_sequential", lambda self: [])
        monkeypatch.setattr(dec.DCPExtractor, "_maybe_route_via_ocr", lambda self: None)
        _extractor().extract()
        assert "NO provider key is set" in capsys.readouterr().out
