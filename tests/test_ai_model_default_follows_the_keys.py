"""The default model's key was not set, and extraction had just become the default.

`AI_MODEL` defaulted to `"mistral"` unconditionally, and `_call_mistral` reads
`os.environ["MISTRAL_API_KEY"]` with no guard. That was survivable while extraction was
opt-in: nobody reached it without choosing to.

#1155 made LLM extraction the default on 2026-09-21. That put a bare `KeyError` on the
path every chapter now takes, in environments that have `ANTHROPIC_API_KEY` and
`OPENAI_API_KEY` but no `MISTRAL_API_KEY` — which is the local checkout and, as it
turned out, the Railway fleet too.

It is the same shape as the data-watch job that died on `os.environ["PGHOST"]` the same
night — a hard index into the environment for a variable the deployment does not supply
— and that one blocked every merge in the repository for three days before anybody
looked past the symptom.

Choosing by what IS configured means a correctly-provisioned environment just works.

WHAT I GOT WRONG WHILE WRITING THIS
-----------------------------------
Reading only the nightly `dcp-extract` service's variables, I concluded no provider key
existed anywhere and was about to ask for one. The keys were there the whole time, on
`dcp-extract-all`, together with `AI_EXTRACTION=1`. Two services, two jobs, deliberately
different configuration — and a negative claim made from one of them. The lesson is the
repo's own Prior-Art Four-Sweep rule applied to infrastructure: check every service
before saying a thing is not configured.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ai_extractor as ai  # noqa: E402

PROVIDER_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "MISTRAL_API_KEY")


@pytest.fixture
def no_keys(monkeypatch):
    for k in PROVIDER_KEYS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    return monkeypatch


class TestItPicksAModelWhoseKeyExists:
    @pytest.mark.parametrize("present,expected", [
        (["ANTHROPIC_API_KEY"], "sonnet"),
        (["OPENAI_API_KEY"], "sol"),
        (["MISTRAL_API_KEY"], "mistral"),
    ])
    def test_a_single_configured_provider_is_chosen(self, no_keys, present, expected):
        for k in present:
            no_keys.setenv(k, "x")
        assert ai._default_model() == expected

    def test_anthropic_wins_over_mistral(self, no_keys):
        """Not a price ranking. sonnet was hand-verified on a real chapter -- 49 of 49
        controls, every section number correct -- and mistral answered 429 on both
        attempts that have ever been made with it."""
        no_keys.setenv("ANTHROPIC_API_KEY", "x")
        no_keys.setenv("MISTRAL_API_KEY", "x")
        assert ai._default_model() == "sonnet"

    def test_openai_wins_over_mistral(self, no_keys):
        no_keys.setenv("OPENAI_API_KEY", "x")
        no_keys.setenv("MISTRAL_API_KEY", "x")
        assert ai._default_model() == "sol"

    def test_a_blank_key_does_not_count_as_configured(self, no_keys):
        """An empty string is how a deployment sets a variable it has not filled in."""
        no_keys.setenv("ANTHROPIC_API_KEY", "   ")
        no_keys.setenv("MISTRAL_API_KEY", "x")
        assert ai._default_model() == "mistral"


class TestNoProviderIsAnErrorThatExplainsItself:
    def test_it_raises_rather_than_guessing(self, no_keys):
        with pytest.raises(RuntimeError):
            ai._default_model()

    def test_the_message_names_every_key_it_looked_for(self, no_keys):
        """A KeyError names one variable and explains nothing. This is the whole
        difference between the two failure modes."""
        with pytest.raises(RuntimeError) as e:
            ai._default_model()
        msg = str(e.value)
        for key in PROVIDER_KEYS:
            assert key in msg, f"{key} is not named, so a reader cannot tell what to set"

    def test_the_message_names_the_escape_hatch(self, no_keys):
        with pytest.raises(RuntimeError) as e:
            ai._default_model()
        assert "AI_EXTRACTION=0" in str(e.value)


class TestAnExplicitChoiceStillWins:
    def test_ai_model_overrides_the_default(self, no_keys, monkeypatch):
        """Choosing by available key must not take the decision away from someone who
        has made it deliberately."""
        no_keys.setenv("ANTHROPIC_API_KEY", "x")
        src = (ROOT / "scripts" / "ai_extractor.py").read_text(encoding="utf-8")
        assert 'os.getenv("AI_MODEL") or _default_model()' in src, (
            "the explicit AI_MODEL setting is no longer consulted first")


class TestThePremise:
    def test_the_docstring_no_longer_says_off_by_default(self):
        """It said 'Enabled by AI_EXTRACTION=1; off by default' for a module that #1155
        made the default. A stale docstring on a switch is how the switch gets turned
        back."""
        src = (ROOT / "scripts" / "ai_extractor.py").read_text(encoding="utf-8")
        assert "off by default" not in src
        assert "AI_EXTRACTION=0" in src

    def test_every_preference_entry_names_a_real_provider(self):
        """A typo here would silently skip a configured provider and fall through to
        one that is not."""
        for name, _key in ai._MODEL_PREFERENCE:
            assert name in ai._PROVIDERS, f"{name} is not a known provider"


class TestAnUnkeyedDeploymentFallsBackRatherThanFailing:
    """Railway runs two extraction services with different jobs and different config.

    Measured 2026-09-21 with the Railway CLI, after wrongly concluding no provider key
    existed anywhere:

        dcp-extract-all   quarterly, full re-read   AI_EXTRACTION=1, ANTHROPIC_API_KEY,
                                                    MISTRAL_API_KEY   -- the LLM runs here
        dcp-extract       nightly, flagged chapters DATABASE_URL, R2_*, MODAL_OCR_*
                                                    and no provider key

    So the LLM extractor was never unused -- it is keyed and enabled on the service
    built for it. What was off was the CODE default, which the nightly service relies on
    to run the regex reader.

    Flipping that default globally therefore pointed the nightly job at a path its
    service is not keyed for. Failing there would have stopped every council's nightly
    extraction in order to enable something that cannot run on that service. It falls
    back instead -- loudly, because a fallback nobody can see is how the LLM extractor
    sat behind an opt-in flag for two months after it had been hand-verified.
    """

    def test_no_key_means_no_model_rather_than_an_exception(self, no_keys):
        """configured_model answers the question one step earlier than _default_model,
        where 'not available on this service' is a real state and not an error."""
        assert ai.configured_model() is None

    def test_a_key_still_selects_the_model(self, no_keys):
        no_keys.setenv("OPENAI_API_KEY", "x")
        assert ai.configured_model() == "sol"

    def test_the_extractor_falls_back_instead_of_raising(self):
        src = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
        assert "configured_model()" in src, (
            "the extractor no longer asks whether a provider is available, so an "
            "unkeyed service will raise instead of falling back")
        assert "NO provider key is set" in src, (
            "the fallback must announce itself; a silent one is how a capability "
            "stays off without anyone noticing")

    def test_the_fallback_names_what_to_set(self):
        src = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "MISTRAL_API_KEY"):
            assert key in src, f"the fallback message does not say to set {key}"

    def test_the_llm_path_says_which_model_it_used(self):
        """Two readers now run in the same fleet. Which one produced a chapter has to
        be readable from the run, or a regression is unattributable."""
        src = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
        assert "LLM document reader" in src
