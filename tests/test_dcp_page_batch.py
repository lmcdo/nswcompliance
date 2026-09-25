"""The batch path settles pages with the same checks as the one-at-a-time tool."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import dcp_page_batch as B  # noqa: E402
from test_dcp_page_reread import _ctx, RULE  # noqa: E402


def test_the_live_signature_changes_when_a_rule_changes():
    a = [("r1", "text one", "d"), ("r2", "text two", "d")]
    assert B.live_signature(a) == B.live_signature(list(reversed(a)))
    assert B.live_signature(a) != B.live_signature([("r1", "text ONE", "d"), ("r2", "text two", "d")])


def test_a_request_line_is_a_chat_completion_with_the_page_attached():
    x = B.request("c/x|3|read|1", "gpt-5.4-mini", b"%PDF", "prompt")
    assert x["url"] == "/v1/chat/completions" and x["body"]["model"] == "gpt-5.4-mini"
    parts = x["body"]["messages"][0]["content"]
    assert parts[0]["type"] == "file" and parts[1]["text"] == "prompt"
    assert B.chapter_of("c/x|3|read|1") == "c/x"


def test_a_label_answer_that_does_not_prove_goes_to_the_strong_model():
    ctx = _ctx()
    entry = {"read": [], "label": {"1": ["Doc__x__3_2 C14"]}}
    wrong = {B.cid("c/x", 1, "label", 1): json.dumps({"labels": [{"i": 1, "code": "3.4 C99"}]})}
    _got, _labels, retry = B.judge(ctx, "c/x", entry, wrong)
    assert retry == {(1, "label")}
    right = {B.cid("c/x", 1, "label", 1): json.dumps({"labels": [{"i": 1, "code": "3.3 C13"}]})}
    _got, labels, retry = B.judge(ctx, "c/x", entry, right)
    assert retry == set() and labels["Doc__x__3_2 C14"]["code"] == "3.3 C13"


def test_a_round_two_answer_is_final_even_when_it_fails():
    ctx = _ctx()
    entry = {"read": [], "label": {"1": ["Doc__x__3_2 C14"]}}
    answers = {B.cid("c/x", 1, "label", 1): "{}",
               B.cid("c/x", 1, "label", 2): json.dumps({"labels": [{"i": 1, "code": "3.4 C99"}]})}
    assert B.judge(ctx, "c/x", entry, answers)[2] == set()


def test_a_read_page_whose_rules_came_back_missing_goes_to_the_strong_model():
    ctx = _ctx()
    ctx["page_lines"] = {1: [RULE + f" and must meet the maximum {i}" for i in range(6)]}
    entry = {"read": [1], "label": {}}
    empty = {B.cid("c/x", 1, "read", 1): json.dumps({"provisions": []})}
    assert B.judge(ctx, "c/x", entry, empty)[2] == {(1, "read")}
