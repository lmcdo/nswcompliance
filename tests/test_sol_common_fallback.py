"""sol_common.chat falls back to DeepSeek via OpenRouter only when OpenAI has no credits (user 2026-10-18)."""
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sol_common  # noqa: E402


def _fake_openai(monkeypatch, fail_openai_with=None):
    calls = []

    class Completions:
        def __init__(self, base_url):
            self.base_url = base_url

        def create(self, **kw):
            calls.append((self.base_url, kw["model"]))
            if self.base_url is None and fail_openai_with:
                raise RuntimeError(fail_openai_with)
            msg = types.SimpleNamespace(content='{"findings": []}')
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    class OpenAI:
        def __init__(self, api_key, timeout, max_retries, base_url=None):
            self.chat = types.SimpleNamespace(completions=Completions(base_url))

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=OpenAI))
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    return calls


def test_no_credit_falls_back_to_deepseek(monkeypatch):
    calls = _fake_openai(monkeypatch, "Error code: 429 - {'code': 'credit_balance_exhausted'}")
    out = sol_common.chat([{"role": "user", "content": "x"}], "gpt-5.6-sol", "sk", json_mode=True)
    assert out == '{"findings": []}'
    assert calls == [(None, "gpt-5.6-sol"), (sol_common.OPENROUTER_BASE_URL, sol_common.FALLBACK_MODEL)]


def test_other_errors_do_not_fall_back(monkeypatch):
    calls = _fake_openai(monkeypatch, "AuthenticationError: invalid key")
    with pytest.raises(SystemExit):
        sol_common.chat([{"role": "user", "content": "x"}], "gpt-5.6-sol", "sk")
    assert calls == [(None, "gpt-5.6-sol")]


def test_an_openrouter_model_goes_straight_to_openrouter(monkeypatch):
    calls = _fake_openai(monkeypatch)
    sol_common.chat([{"role": "user", "content": "x"}], "deepseek/deepseek-v3.2", "sk")
    assert calls == [(sol_common.OPENROUTER_BASE_URL, "deepseek/deepseek-v3.2")]


def test_last_model_names_the_model_that_answered(monkeypatch):
    _fake_openai(monkeypatch, "credit_balance_exhausted")
    sol_common.chat([{"role": "user", "content": "x"}], "gpt-5.6-sol", "sk")
    assert sol_common.LAST_MODEL == sol_common.FALLBACK_MODEL
