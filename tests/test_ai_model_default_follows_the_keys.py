"""The default model's key was not set, and extraction had just become the default.

`AI_MODEL` defaulted to `"mistral"` unconditionally, and `_call_mistral` reads
`os.environ["MISTRAL_API_KEY"]` with no guard. That was survivable while extraction was
opt-in: nobody reached it without choosing to.

#1155 made LLM extraction the default on 2026-09-21. That put a bare `KeyError` on the
path every chapter now takes, in an environment where `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY` and `GEMINI_API_KEY` are set and `MISTRAL_API_KEY` is not.

It is the same shape as the data-watch job that died on `os.environ["PGHOST"]` the same
night — a hard index into the environment for a variable the deployment does not supply
— and that one blocked every merge in the repository for three days before anybody
looked past the symptom.

Choosing by what IS configured means a correctly-provisioned environment just works. An
environment with no provider key at all still fails, because it must, but it fails
naming every key it looked for rather than whichever happened to be read first.
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
