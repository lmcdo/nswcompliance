"""data_watch_telegram: failing live-data checks reach Telegram; a silent alarm turns the run red.

Real case: data-watch failed 3 nights running (2026-10-22..24) and only opened a GitHub issue nobody read.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import data_watch_telegram as t  # noqa: E402

WF = (ROOT / ".github" / "workflows" / "data-watch.yml").read_text(encoding="utf-8")


def _outcomes(**fail):
    return ",".join("failure" if n in fail.values() else "success" for n in t.NAMES)


def test_names_match_the_issue_step_exactly():
    block = WF[WF.index("const names = ["):WF.index("];", WF.index("const names = ["))]
    assert re.findall(r"'([^']+)'", block) == t.NAMES


def test_both_steps_read_the_same_outcomes():
    tg = WF[WF.index("- name: Send failing checks to Telegram"):WF.index("- name: Raise or clear the alarm")]
    issue = WF[WF.index("- name: Raise or clear the alarm"):]
    pick = lambda s: re.search(r"FAILED: >-\n\s+(.+)", s).group(1).strip()  # noqa: E731
    assert pick(tg) == pick(issue)


def test_failing_lists_only_failures():
    assert t.failing(_outcomes(a="defect ledger", b="served-answer quality")) == ["defect ledger",
                                                                                  "served-answer quality"]
    assert t.failing(_outcomes()) == []
    assert t.failing(",".join(["skipped"] * len(t.NAMES))) == [f"{n} (did not run)" for n in t.NAMES]


def test_a_step_that_never_ran_counts_as_failing():
    assert t.failing("") == [f"{n} (did not run)" for n in t.NAMES]
    assert t.failing("success") == [f"{n} (did not run)" for n in t.NAMES[1:]]


def test_red_without_telegram_fails_the_run(monkeypatch):
    monkeypatch.setenv("FAILED", _outcomes(a="defect ledger"))
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert t.main() == 1


def test_red_delivered_passes(monkeypatch):
    monkeypatch.setenv("FAILED", _outcomes(a="defect ledger"))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setattr(t, "send", lambda text, token, chat: "defect ledger" in text)
    assert t.main() == 0


def test_send_needs_ok_and_a_result(monkeypatch):
    class R:
        def __init__(self, body): self.body = body
        def read(self): return self.body
        def __enter__(self): return self
        def __exit__(self, *a): return False
    for body, want in [(json.dumps({"ok": True, "result": {"message_id": 1}}), True),
                       (json.dumps({"ok": False}), False), ("null", False)]:
        monkeypatch.setattr(t.urllib.request, "urlopen", lambda req, timeout: R(body.encode()))
        assert t.send("x", "T", "1") is want


def test_the_post_commit_run_is_scheduled():
    assert 'cron: "30 9 * * *"' in WF and 'cron: "0 20 * * *"' in WF
