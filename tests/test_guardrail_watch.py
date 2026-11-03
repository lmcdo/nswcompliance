"""scripts/guardrail_watch.py: what it must report, and that it never fails quietly.

The fixture is the real escape line written on 2026-11-03 without opening the approved plan.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import guardrail_watch as gw  # noqa: E402

TODAY = """diff --git a/scripts/dcp_extract_changed.py b/scripts/dcp_extract_changed.py
--- a/scripts/dcp_extract_changed.py
+++ b/scripts/dcp_extract_changed.py
@@ -1,2 +1,3 @@
 x = 1
+        # prior-art-checked: reuse not viable because this reports this function's own
-        old = 2
diff --git a/.claude/settings.json b/.claude/settings.json
--- a/.claude/settings.json
+++ b/.claude/settings.json
@@ -1 +1 @@
+{"hooks": {}}
diff --git a/.claude/hooks/prior-art-guard.py b/.claude/hooks/prior-art-guard.py
deleted file mode 100644
--- a/.claude/hooks/prior-art-guard.py
+++ /dev/null
@@ -1 +0,0 @@
-print("guard")
"""


def test_the_real_escape_line_from_today_is_reported():
    guards, bypasses = gw.parse_diff(TODAY)
    assert ("scripts/dcp_extract_changed.py",
            "# prior-art-checked: reuse not viable because this reports this function's own") in bypasses


def test_a_settings_change_and_a_deleted_hook_are_both_reported():
    guards, _ = gw.parse_diff(TODAY)
    assert ".claude/settings.json" in guards
    assert ".claude/hooks/prior-art-guard.py" in guards      # deletion: +++ is /dev/null


def test_a_removed_escape_line_is_not_reported_as_added():
    _, bypasses = gw.parse_diff("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n"
                                "-# prior-art-checked: gone\n")
    assert bypasses == []


def test_an_ordinary_diff_reports_nothing():
    d = "diff --git a/scripts/a.py b/scripts/a.py\n--- a/scripts/a.py\n+++ b/scripts/a.py\n+x = 2\n"
    assert gw.message("push", *gw.parse_diff(d)) is None


def test_nothing_to_report_exits_0_without_sending(monkeypatch, capsys):
    monkeypatch.setattr(gw, "_git", lambda *a: "")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert gw.main(["--range", "a..b"]) == 0


def test_a_report_with_no_telegram_configured_fails_loudly(monkeypatch, capsys):
    monkeypatch.setattr(gw, "_git", lambda *a: TODAY)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert gw.main(["--range", "a..b"]) == 1
    assert "not delivered" in capsys.readouterr().out


def test_a_report_telegram_does_not_confirm_fails_loudly(monkeypatch):
    import verifyops_outside_ping as vop
    monkeypatch.setattr(gw, "_git", lambda *a: TODAY)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.setattr(vop, "send_telegram", lambda *a, **k: False)
    assert gw.main(["--range", "a..b"]) == 1


def test_a_confirmed_report_exits_0_and_names_every_item(monkeypatch):
    import verifyops_outside_ping as vop
    sent = []
    monkeypatch.setattr(gw, "_git", lambda *a: TODAY)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.setattr(vop, "send_telegram", lambda text, *a, **k: sent.append(text) or True)
    assert gw.main(["--range", "a..b"]) == 0
    assert "prior-art-checked" in sent[0] and ".claude/settings.json" in sent[0]


def test_deleting_the_ci_plan_check_is_a_guardrail_change():
    d = ("diff --git a/scripts/check_pr_plan_line.py b/scripts/check_pr_plan_line.py\n"
         "deleted file mode 100644\n--- a/scripts/check_pr_plan_line.py\n+++ /dev/null\n-x\n")
    assert "scripts/check_pr_plan_line.py" in gw.parse_diff(d)[0]


def test_a_push_is_read_commit_by_commit(monkeypatch):
    """Changed and reverted inside one push: the endpoint diff is empty, the commits are not."""
    calls = []
    monkeypatch.setattr(gw, "_git", lambda *a: calls.append(a) or "")
    gw.main(["--range", "a..b", "--print-only"])
    assert calls[0][:3] == ("log", "-p", "--first-parent")


def test_mentions_in_tests_reports_and_the_pattern_are_not_reported_but_real_use_is():
    """First alert (2026-11-03): 6 of 8 lines were mentions. Real use must still show."""
    def one(path, text):
        return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n+{text}\n"
    d = (one("tests/test_x.py", "# prior-art-checked: example in a test")
         + one(".qa/reports/feat__x.json", '"observed_red": "prior-art-checked: quoted"')
         + one("scripts/guardrail_watch.py",
               "    " + next(x for x in gw._OWN if x.startswith('r"prior-art-checked:')))
         + one("scripts/dcp_extract_changed.py", "# prior-art-checked: reuse not viable"))
    _, bypasses = gw.parse_diff(d)
    assert bypasses == [("scripts/dcp_extract_changed.py", "# prior-art-checked: reuse not viable")]


def _one(path, text):
    return "diff --git a/%s b/%s\n--- a/%s\n+++ b/%s\n+%s\n" % (path, path, path, path, text)


def test_a_real_skip_or_ignore_in_tests_is_still_reported():
    """Sol review: a test-directory skip IS a loosened guard, not a mention."""
    d = _one("tests/test_y.py", "@pytest.mark.skip(reason='flaky')") + _one("tests/conftest.py", "collect_ignore = ['test_z.py']")
    _, bypasses = gw.parse_diff(d)
    assert [f for f, _ in bypasses] == ["tests/test_y.py", "tests/conftest.py"]


def test_only_the_exact_pattern_lines_of_the_watcher_are_skipped():
    d = _one("scripts/guardrail_watch.py", '    r"RULE_WRITE_OK=|something_new",')
    assert gw.parse_diff(d)[1]                    # a new raw string with a token is reported
