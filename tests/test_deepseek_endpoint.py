"""The DeepSeek reader calls DeepSeek directly when DEEPSEEK_API_KEY is set, else OpenRouter (scripts/ai_extractor.py).

2026-10-18: OpenRouter stalled reads for ~15 minutes twice; the user asked to go direct.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import ai_extractor as ax  # noqa: E402


def test_the_direct_key_routes_to_deepseek_with_its_output_limit(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.delenv("AI_MODEL_ID", raising=False)
    assert ax.deepseek_endpoint() == (ax.DEEPSEEK_DIRECT_URL, "ds-key", "deepseek-chat", 8192)


def test_without_the_direct_key_openrouter_is_used_as_before(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.delenv("AI_MODEL_ID", raising=False)
    url, key, model, max_tokens = ax.deepseek_endpoint()
    assert "openrouter.ai" in url and key == "or-key" and model == ax.DEEPSEEK_MODEL and max_tokens == 16000


def test_no_key_at_all_says_which_keys_it_needs(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY or OPENROUTER_API_KEY"):
        ax.deepseek_endpoint()


def test_an_empty_model_override_keeps_the_default(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
    monkeypatch.setenv("AI_MODEL_ID", "")
    assert ax.deepseek_endpoint()[2] == "deepseek-chat"
