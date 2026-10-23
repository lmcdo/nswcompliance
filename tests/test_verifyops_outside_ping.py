"""verifyops_outside_ping: verdicts, message, Telegram, healthchecks ping, end to end (no network)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verifyops_outside_ping as p  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "verifyops"
COVERAGE = FIX / "coverage_2026-10-23.txt"
RAILWAY = FIX / "railway_jobs_2026-10-23.txt"
HC = "https://hc-ping.com/x"
TG_OK = json.dumps({"ok": True, "result": {"message_id": 7}})


class FakePost:
    def __init__(self, tg=TG_OK, hc="OK", raises=False):
        self.calls: list[tuple[str, bytes | None]] = []
        self.tg, self.hc, self.raises = tg, hc, raises

    def __call__(self, url, data=None, *a, **k):
        self.calls.append((url, data))
        if self.raises:
            raise OSError("boom")
        return self.tg if "api.telegram.org" in url else self.hc


# 1-4 decide
def test_decide_all_zero_success():
    assert p.decide({"a": "0", "b": "0"}, None) == "success"


def test_decide_red_needs_telegram_true():
    r = {"a": "0", "b": "1"}
    assert p.decide(r, True) == "success"
    assert p.decide(r, False) == "fail"
    assert p.decide(r, None) == "fail"


def test_decide_could_not_look_fails_even_if_telegram_ok():
    assert p.decide({"a": "2", "b": "0"}, True) == "fail"


@pytest.mark.parametrize("rcs", [{"a": ""}, {"a": None}, {}])
def test_decide_missing_code_or_empty_fails(rcs):
    assert p.decide(rcs, True) == "fail"


def test_decide_whitespace_treated_as_code():
    assert p.decide({"a": " 1 "}, True) == "success"
    assert p.decide({"a": " 1 "}, False) == "fail"


# 5 message
def test_message_all_green_is_none():
    assert p.message({"a": "0", "b": "0"}, ["VERIFYOPS: x"]) is None


def test_message_real_fixtures():
    reports = [RAILWAY.read_text(encoding="utf-8"), COVERAGE.read_text(encoding="utf-8")]
    m = p.message({"ledger": "0", "coverage": "1", "railway": "1"}, reports)
    assert "coverage=1" in m and "ledger=0" in m
    assert "C = 0/547" in m
    assert "*|*|no_run_2d" in m
    assert "dcp-commit:" in m
    body = m.split("\n")[1:]
    more = [ln for ln in body if ln.startswith("... ") and "more lines" in ln]
    assert len(more) == 1
    assert len(body) - 1 <= p.MAX_LINES
    assert len(body) - 1 == p.MAX_LINES


def test_message_crashed_rc():
    m = p.message({"ledger": "", "coverage": None, "railway": "1"}, ["VERIFYOPS: x"])
    assert "ledger=crashed" in m and "coverage=crashed" in m and "railway=1" in m


# 6 send_telegram
def test_send_telegram_true_with_message_id():
    f = FakePost()
    assert p.send_telegram("hi", "TOK", "42", f) is True
    url, data = f.calls[0]
    assert url == "https://api.telegram.org/botTOK/sendMessage"
    assert json.loads(data) == {"chat_id": "42", "text": "hi"}


@pytest.mark.parametrize("ans", [
    json.dumps({"ok": True}),
    json.dumps({"ok": True, "result": {}}),
    json.dumps({"ok": False, "result": {"message_id": 1}}),
])
def test_send_telegram_false_on_bad_answer(ans):
    assert p.send_telegram("hi", "T", "1", FakePost(tg=ans)) is False


def test_send_telegram_false_on_raise():
    assert p.send_telegram("hi", "T", "1", FakePost(raises=True)) is False


def test_send_telegram_truncates_text():
    f = FakePost()
    p.send_telegram("x" * 9000, "T", "1", f)
    assert len(json.loads(f.calls[0][1])["text"]) <= 4000


# 7 ping
def test_ping_success_and_fail_urls():
    f = FakePost()
    assert p.ping(HC + "/", "success", f) is True
    assert f.calls[-1][0] == HC
    assert p.ping(HC + "/", "fail", f) is True
    assert f.calls[-1][0] == HC + "/fail"


def test_ping_not_found_is_false():
    assert p.ping(HC, "success", FakePost(hc="OK (not found)")) is False


def test_ping_raise_is_false():
    assert p.ping(HC, "success", FakePost(raises=True)) is False


# 8 main
def _env(monkeypatch, hc=HC, tg=True):
    for k in ("HC_PING_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        monkeypatch.delenv(k, raising=False)
    if hc:
        monkeypatch.setenv("HC_PING_URL", hc)
    if tg:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TOK")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")


def _args(ledger="0", coverage="1", railway="1"):
    return ["--rc", f"ledger={ledger}", "--rc", f"coverage={coverage}", "--rc", f"railway={railway}",
            "--report", str(RAILWAY), "--report", str(COVERAGE)]


def test_main_red_delivered_pings_success(monkeypatch):
    _env(monkeypatch)
    f = FakePost()
    assert p.main(_args(), post=f) == 0
    assert f.calls[0][0].startswith("https://api.telegram.org/botTOK/")
    assert f.calls[-1][0] == HC


def test_main_telegram_not_ok_pings_fail(monkeypatch):
    _env(monkeypatch)
    f = FakePost(tg=json.dumps({"ok": False}))
    assert p.main(_args(), post=f) == 0  # the /fail ping itself landed
    assert f.calls[-1][0] == HC + "/fail"


def test_main_could_not_look_pings_fail(monkeypatch):
    _env(monkeypatch)
    f = FakePost()
    p.main(_args(coverage="2"), post=f)
    assert f.calls[-1][0] == HC + "/fail"


def test_main_all_green_no_telegram(monkeypatch):
    _env(monkeypatch)
    f = FakePost()
    assert p.main(_args("0", "0", "0"), post=f) == 0
    assert not any("telegram" in u for u, _ in f.calls)
    assert [u for u, _ in f.calls] == [HC]


def test_main_no_hc_url_exits_1_without_posting(monkeypatch):
    _env(monkeypatch, hc=None)
    f = FakePost()
    assert p.main(_args(), post=f) == 1
    assert f.calls == []


def test_main_no_telegram_env_with_red_pings_fail(monkeypatch):
    _env(monkeypatch, tg=False)
    f = FakePost()
    p.main(_args(), post=f)
    assert f.calls[-1][0] == HC + "/fail"
    assert not any("telegram" in u for u, _ in f.calls)
