"""A finding adjudicated once must not block the next push forever.

The gate blocked one branch four times running on 2026-08-10. It kept no record
of what it had already raised, so a finding that had been read, verified and
dealt with could come back on the next run and block again, indistinguishable
from something new.

These tests cover the record itself. The deliberate coarseness of the key
(file + category, no line, no summary text) is the design decision most likely
to be quietly "improved" later into something that matches nothing, so it is
pinned here with the reason.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_SRC = ROOT / "scripts" / "cross_review.py"

pytestmark = pytest.mark.skipif(not _SRC.exists(), reason="cross_review.py not present")


def _mod():
    spec = importlib.util.spec_from_file_location("cross_review_under_test", _SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def cr():
    return _mod()


def test_the_same_defect_reworded_still_matches(cr):
    """The whole point. Sol is non-deterministic prose.

    The identical defect comes back described differently on the next run. If
    the key included the summary text it would match almost nothing and the
    record would be decorative.
    """
    a = {"file": "services/flood.py", "category": "null-guard", "line": 40,
         "summary": "Unguarded null in the flood signal path"}
    b = {"file": "services/flood.py", "category": "null-guard", "line": 118,
         "summary": "A missing overlay yields None and is rendered as a clean negative"}
    assert cr.finding_key(a) == cr.finding_key(b)


def test_a_different_file_or_category_is_a_different_finding(cr):
    base = {"file": "services/flood.py", "category": "null-guard"}
    assert cr.finding_key(base) != cr.finding_key({**base, "file": "services/solar.py"})
    assert cr.finding_key(base) != cr.finding_key({**base, "category": "silent-failure"})


def test_missing_fields_do_not_collapse_everything_into_one_key(cr):
    """A malformed finding must not become a key that matches other malformed
    ones and grants them all amnesty in one go."""
    assert cr.finding_key({}) == "?::?"
    assert cr.finding_key({"file": "a.py"}) != cr.finding_key({"file": "b.py"})


def test_an_absent_record_grants_no_amnesty(cr, tmp_path):
    assert cr.load_adjudicated(None) == set()
    assert cr.load_adjudicated(tmp_path / "nope.json") == set()


def test_a_corrupt_record_grants_no_amnesty(cr, tmp_path, capsys):
    """Fail CLOSED. A truncated or hand-edited file must not silently mean
    'everything has already been adjudicated' — that would disable the gate
    while leaving it looking enabled."""
    p = tmp_path / "broken.json"
    p.write_text("{not json", encoding="utf-8")
    assert cr.load_adjudicated(p) == set()
    assert "unreadable" in capsys.readouterr().out


def test_a_record_round_trips(cr, tmp_path):
    p = tmp_path / "rec.json"
    keys = ["a.py::null-guard", "b.py::db-filter"]
    p.write_text(json.dumps({"keys": keys}), encoding="utf-8")
    assert cr.load_adjudicated(p) == set(keys)


# ── Verdicts ────────────────────────────────────────────────────────────────
# The record answered "was this finding seen?" and never "was it right?", so
# campaign §7 finding 6 — promote a gate to blocking once an observed
# false-positive rate justifies it — had an input that was discarded by design.
# Measured on disk 2026-08-16: 40 branch records, 114 findings, 0 verdicts.


def test_every_v1_record_on_disk_still_grants_its_amnesty(cr, tmp_path):
    """The format change must not re-block a branch mid-cycle.

    All 40 live records are v1 ``{"keys": [...]}``. A v2-only reader would treat
    every one of them as empty, and every finding already dealt with would gate
    again — the exact loop the record was built to end.
    """
    p = tmp_path / "v1.json"
    p.write_text(json.dumps({"keys": ["a.py::null-guard"]}), encoding="utf-8")
    assert cr.load_adjudicated(p) == {"a.py::null-guard"}
    assert cr.load_record(p)["a.py::null-guard"]["verdict"] == cr.VERDICT_UNREVIEWED


def test_a_seen_finding_is_not_a_judged_finding(cr, tmp_path):
    """The defect itself, pinned. Reading a v1 record must NOT let those 114
    findings count as evidence in either direction."""
    p = tmp_path / "v1.json"
    p.write_text(json.dumps({"keys": ["a.py::x", "b.py::y"]}), encoding="utf-8")
    verdicts = {e["verdict"] for e in cr.load_record(p).values()}
    assert verdicts == {cr.VERDICT_UNREVIEWED}
    report = cr.verdict_report(p)
    assert "NO RATE" in report


@pytest.mark.parametrize("text,verdict,reason", [
    ("wrong: the guard at line 40 covers it", "false_positive", "the guard at line 40 covers it"),
    ("WRONG: case is not significant", "false_positive", "case is not significant"),
    ("fp: shorthand", "false_positive", "shorthand"),
    ("real: correct, but out of scope here", "real", "correct, but out of scope here"),
    ("valid: same thing", "real", "same thing"),
])
def test_a_prefixed_override_scores(cr, text, verdict, reason):
    assert cr.parse_verdict(text) == (verdict, reason)


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "this finding is about a path that cannot be reached",
    "note: I disagree",              # a colon, but not a verdict word
    "maybe-wrong: hedged",           # near-miss prefix
])
def test_an_unprefixed_override_is_never_guessed_into_a_bucket(cr, text):
    """The single most dangerous thing this could do is infer a verdict.

    A rate assembled from guesses is worse than no rate: it reads as measured.
    The reason is still kept — it is just not scored.
    """
    verdict, reason = cr.parse_verdict(text)
    assert verdict == cr.VERDICT_UNREVIEWED
    assert reason == text.strip()


def test_a_reason_containing_a_colon_survives_intact(cr):
    verdict, reason = cr.parse_verdict("wrong: see services/a.py:40 — guarded there")
    assert verdict == cr.VERDICT_FALSE_POSITIVE
    assert reason == "see services/a.py:40 — guarded there"


def test_an_out_of_vocab_verdict_is_not_trusted_as_an_adjudication(cr, tmp_path):
    """A hand-edited or future-format record must fall back to unreviewed, not
    be counted. Counting an unrecognised string as a judgement is how a
    denominator gets quietly inflated."""
    p = tmp_path / "v2.json"
    p.write_text(json.dumps({"version": 2, "findings": {
        "a.py::x": {"verdict": "probably-fine"},
    }}), encoding="utf-8")
    assert cr.load_record(p)["a.py::x"]["verdict"] == cr.VERDICT_UNREVIEWED
    # Still known, so still no amnesty change.
    assert cr.load_adjudicated(p) == {"a.py::x"}


def test_a_verdict_does_not_change_what_gates(cr, tmp_path):
    """Deliberate: verdicts are evidence for a policy decision, not a second
    amnesty rule. A finding judged `real` and one judged `false_positive` must
    both stay non-gating, exactly as an unjudged one does."""
    p = tmp_path / "v2.json"
    p.write_text(json.dumps({"version": 2, "findings": {
        "a.py::x": {"verdict": "real"},
        "b.py::y": {"verdict": "false_positive"},
        "c.py::z": {"verdict": "unreviewed"},
    }}), encoding="utf-8")
    assert cr.load_adjudicated(p) == {"a.py::x", "b.py::y", "c.py::z"}


def test_a_verdict_only_lands_on_what_actually_blocked(cr, tmp_path):
    """An override justifies the finding that stopped the push, not every
    finding the branch has ever seen. Applying it broadly would fabricate
    adjudications nobody made."""
    p = tmp_path / "v2.json"
    p.write_text(json.dumps({"version": 2, "findings": {
        "blocked.py::correctness": {"verdict": "unreviewed", "awaiting_verdict": True},
        "advisory.py::other": {"verdict": "unreviewed", "awaiting_verdict": False},
    }}), encoding="utf-8")

    cr._apply_verdict(p, "wrong: guarded at line 40", branch="feat/x")

    rec = cr.load_record(p)
    assert rec["blocked.py::correctness"]["verdict"] == cr.VERDICT_FALSE_POSITIVE
    assert rec["advisory.py::other"]["verdict"] == cr.VERDICT_UNREVIEWED
    assert rec["blocked.py::correctness"]["awaiting_verdict"] is False


def _two_pending(tmp_path, name="rec.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"version": 2, "findings": {
        "a.py::correctness": {"verdict": "unreviewed", "severity": "high",
                              "awaiting_verdict": True},
        "b.py::null-guard": {"verdict": "unreviewed", "severity": "high",
                             "awaiting_verdict": True},
    }}), encoding="utf-8")
    return p


def test_one_reason_cannot_judge_two_findings(cr, tmp_path, capsys):
    """Found by the cross-reviewer on this very change, and it was right.

    Two HIGH findings block, one real and one wrong. A single `wrong:` reason
    would file BOTH as false positives — corrupting the rate in the direction
    that argues for weakening the gate, off evidence nobody actually gave.
    """
    p = _two_pending(tmp_path)
    cr._apply_verdict(p, "wrong: guarded at line 40", branch="feat/x")

    rec = cr.load_record(p)
    assert {e["verdict"] for e in rec.values()} == {cr.VERDICT_UNREVIEWED}
    assert "NOT SCORED" in capsys.readouterr().out
    # Nothing may reach the ledger: an unscored note is not evidence.
    assert not cr.ledger_path(p).exists()


def test_the_operators_reason_is_kept_even_when_it_cannot_be_scored(cr, tmp_path):
    """Refusing to score must not mean discarding what they wrote — that is the
    original defect (the override was echoed and thrown away) in a new place."""
    p = _two_pending(tmp_path)
    cr._apply_verdict(p, "wrong: both of these are about a dead path", branch="feat/x")

    rec = cr.load_record(p)
    for entry in rec.values():
        assert entry["reason"] == "both of these are about a dead path"
        assert entry["awaiting_verdict"] is True    # still owed a judgement


def test_naming_the_finding_scores_only_that_one(cr, tmp_path):
    p = _two_pending(tmp_path)
    cr._apply_verdict(p, "a.py::correctness=wrong: guarded at line 40", branch="feat/x")

    rec = cr.load_record(p)
    assert rec["a.py::correctness"]["verdict"] == cr.VERDICT_FALSE_POSITIVE
    assert rec["a.py::correctness"]["awaiting_verdict"] is False
    # The other is untouched and still owed a verdict.
    assert rec["b.py::null-guard"]["verdict"] == cr.VERDICT_UNREVIEWED
    assert rec["b.py::null-guard"]["awaiting_verdict"] is True
    assert len(cr.read_ledger(cr.ledger_path(p))) == 1


def test_each_finding_can_be_given_a_different_verdict(cr, tmp_path):
    """The case the shared-verdict bug got wrong: one real, one wrong."""
    p = _two_pending(tmp_path)
    cr._apply_verdict(p, "a.py::correctness=wrong: unreachable", branch="feat/x")
    cr._apply_verdict(p, "b.py::null-guard=real: fixed in the next commit", branch="feat/x")

    rec = cr.load_record(p)
    assert rec["a.py::correctness"]["verdict"] == cr.VERDICT_FALSE_POSITIVE
    assert rec["b.py::null-guard"]["verdict"] == cr.VERDICT_REAL
    verdicts = {r["key"]: r["verdict"] for r in cr.read_ledger(cr.ledger_path(p))}
    assert verdicts == {"a.py::correctness": "false_positive",
                        "b.py::null-guard": "real"}


def test_a_single_pending_finding_still_takes_a_bare_reason(cr, tmp_path):
    """The common case must stay ergonomic — one blocked finding, one reason,
    no key to type. Requiring the key always would push people to --no-verify."""
    p = tmp_path / "one.json"
    p.write_text(json.dumps({"version": 2, "findings": {
        "a.py::correctness": {"verdict": "unreviewed", "awaiting_verdict": True},
    }}), encoding="utf-8")
    cr._apply_verdict(p, "wrong: guarded at line 40", branch="feat/x")
    assert cr.load_record(p)["a.py::correctness"]["verdict"] == cr.VERDICT_FALSE_POSITIVE


def test_a_key_naming_something_not_pending_is_not_silently_applied(cr, tmp_path, capsys):
    """A typo'd or stale key must not fall through to 'apply to everything'."""
    p = _two_pending(tmp_path)
    cr._apply_verdict(p, "typo.py::correctness=wrong: nope", branch="feat/x")

    rec = cr.load_record(p)
    assert {e["verdict"] for e in rec.values()} == {cr.VERDICT_UNREVIEWED}
    assert "NOT SCORED" in capsys.readouterr().out


def test_a_stale_key_is_refused_even_when_only_one_finding_is_pending(cr, tmp_path, capsys):
    """The gap the two-pending test above was hiding.

    With one finding pending, an unmatched target used to read as "no target"
    and the override was applied to whatever happened to be pending — clearing
    that finding's pending flag with no verdict and no error, while the operator
    believed they had judged a different one. The multi-pending refusal masked
    it; nothing covered the single-pending path.
    """
    p = tmp_path / "one.json"
    p.write_text(json.dumps({"version": 2, "findings": {
        "a.py::correctness": {"verdict": "unreviewed", "awaiting_verdict": True},
    }}), encoding="utf-8")

    cr._apply_verdict(p, "typo.py::correctness=wrong: nope", branch="feat/x")

    entry = cr.load_record(p)["a.py::correctness"]
    assert entry["verdict"] == cr.VERDICT_UNREVIEWED
    assert entry["awaiting_verdict"] is True, (
        "the finding stopped awaiting a verdict without ever receiving one"
    )
    assert entry["reason"] == "", "a reason aimed at another finding was stored here"
    out = capsys.readouterr().out
    assert "NOT SCORED" in out and "typo.py::correctness" in out
    assert not cr.ledger_path(p).exists()


def test_split_target_tells_absent_from_unmatched(cr):
    """Two states was the bug; three is the fix. Pinned directly, because the
    difference is invisible from the outside until it goes wrong."""
    pending = ["a.py::correctness"]
    assert cr.split_target("a.py::correctness=wrong: x", pending) == (
        "a.py::correctness", "wrong: x", "matched")
    assert cr.split_target("wrong: no key here", pending) == (
        None, "wrong: no key here", "none")
    assert cr.split_target("b.py::null-guard=wrong: x", pending)[2] == "unmatched"


def test_a_plain_reason_mentioning_a_path_is_not_read_as_a_target(cr):
    """The false-positive risk of the regex above: prose must stay prose."""
    pending = ["a.py::correctness"]
    for text in ("wrong: see services/a.py::x for the guard",
                 "real: a.py::correctness is right, fixing later",
                 "the value == the other value"):
        assert cr.split_target(text, pending)[2] in ("none", "matched")


def test_an_override_with_nothing_pending_records_nothing(cr, tmp_path, capsys):
    """Refuse rather than guess: with no pending finding there is no subject for
    the verdict, and attaching it to something would be an invention."""
    p = tmp_path / "v2.json"
    p.write_text(json.dumps({"version": 2, "findings": {
        "a.py::x": {"verdict": "unreviewed", "awaiting_verdict": False},
    }}), encoding="utf-8")

    cr._apply_verdict(p, "wrong: nothing to attach this to", branch="feat/x")

    assert cr.load_record(p)["a.py::x"]["verdict"] == cr.VERDICT_UNREVIEWED
    assert "nothing recorded" in capsys.readouterr().out
    assert not cr.ledger_path(p).exists()


def test_the_ledger_accumulates_across_branches(cr, tmp_path):
    """The per-branch record dies with the branch on purpose. A false-positive
    RATE needs a denominator that does not, so verdicts (not amnesty) also go to
    a shared ledger."""
    for branch in ("feat/a", "feat/b"):
        p = tmp_path / f"{branch.replace('/', '-')}.json"
        p.write_text(json.dumps({"version": 2, "findings": {
            "x.py::correctness": {"verdict": "unreviewed", "awaiting_verdict": True},
        }}), encoding="utf-8")
        cr._apply_verdict(p, "wrong: not reachable", branch=branch)

    rows = cr.read_ledger(tmp_path / "verdicts.jsonl")
    assert len(rows) == 2
    assert {r["branch"] for r in rows} == {"feat/a", "feat/b"}
    assert {r["verdict"] for r in rows} == {"false_positive"}


def test_the_same_finding_rejudged_on_one_branch_is_one_datum(cr, tmp_path):
    """Otherwise a single contested finding, overridden three times while a
    branch churns, would count three times toward the rate."""
    p = tmp_path / "rec.json"
    ledger = cr.ledger_path(p)
    ledger.write_text("".join(json.dumps(r) + "\n" for r in [
        {"branch": "feat/a", "key": "x.py::c", "verdict": "false_positive"},
        {"branch": "feat/a", "key": "x.py::c", "verdict": "real"},
    ]), encoding="utf-8")

    report = cr.verdict_report(p)
    assert "2 appended, 1 distinct" in report
    # The later verdict wins, so it is 1 real / 0 false positive, not 1 of each.
    assert "real        : 1" in report
    assert "false pos.  : 0" in report


def test_no_percentage_is_printed_from_a_sample_too_small_to_mean_one(cr, tmp_path):
    """The whole point of the stale-prior lesson. Four reviews is an anecdote;
    printing '25%' is what turns an anecdote into a rule that outlives it."""
    p = tmp_path / "rec.json"
    rows = [{"branch": f"b{i}", "key": "x.py::c",
             "verdict": "false_positive" if i == 0 else "real"} for i in range(4)]
    cr.ledger_path(p).write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    report = cr.verdict_report(p)
    assert "NO RATE" in report
    assert "%" not in report.split("NO RATE")[0].split("adjudicated :")[-1]
    assert "adjudicated : 4" in report


def test_a_rate_is_only_ever_printed_with_its_denominator(cr, tmp_path):
    p = tmp_path / "rec.json"
    rows = [{"branch": f"b{i}", "key": "x.py::c",
             "verdict": "false_positive" if i < 5 else "real"}
            for i in range(cr.MIN_SAMPLE_FOR_RATE)]
    cr.ledger_path(p).write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    report = cr.verdict_report(p)
    assert f"5/{cr.MIN_SAMPLE_FOR_RATE} = 25%" in report
    assert "denominator" in report


def test_unreviewed_findings_never_enter_the_rate(cr, tmp_path):
    """A raised-but-never-judged finding is evidence of nothing. Counting it as
    real would flatter the reviewer; counting it as a false positive would
    justify weakening the gate. It is reported separately and excluded."""
    p = tmp_path / "rec.json"
    rows = ([{"branch": f"u{i}", "key": "x.py::c", "verdict": "unreviewed"}
             for i in range(30)]
            + [{"branch": "j1", "key": "y.py::c", "verdict": "real"}])
    cr.ledger_path(p).write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    report = cr.verdict_report(p)
    assert "unreviewed  : 30" in report
    assert "adjudicated : 1" in report
    assert "NO RATE" in report      # 1 judged, not 31


def test_a_corrupt_ledger_line_does_not_take_the_report_down(cr, tmp_path):
    p = tmp_path / "rec.json"
    cr.ledger_path(p).write_text(
        '{"branch":"a","key":"x.py::c","verdict":"real"}\n'
        "{not json\n"
        "\n"
        '"a string, not an object"\n',
        encoding="utf-8")
    assert "real        : 1" in cr.verdict_report(p)


def test_an_empty_ledger_reports_zero_rather_than_looking_clean(cr, tmp_path):
    """A machine with no ledger must not read as 'no false positives observed'.
    The path is printed so an empty report is legible as empty."""
    p = tmp_path / "rec.json"
    report = cr.verdict_report(p)
    assert "adjudicated : 0" in report
    assert "NO RATE" in report
    assert str(cr.ledger_path(p)) in report


def test_the_report_shows_observation_against_judgement(cr, tmp_path):
    """"1 adjudicated" means something different beside 3 observed than beside
    300. The gap between the two IS the defect being fixed here, so the report
    has to show both or it hides its own subject."""
    (tmp_path / "feat-a.json").write_text(
        json.dumps({"keys": ["a.py::x", "b.py::y"]}), encoding="utf-8")
    (tmp_path / "feat-b.json").write_text(
        json.dumps({"keys": ["c.py::z"]}), encoding="utf-8")

    report = cr.verdict_report(tmp_path / "feat-a.json")
    assert "observed    : 3" in report
    assert "adjudicated : 0" in report


def test_only_fresh_findings_gate(cr, tmp_path):
    """The split that makes the loop terminate.

    Two findings, one already adjudicated. Only the new one may gate; the
    repeat is still reported, because being repeated is not evidence that it is
    fixed — but it must not block a second time on its own.
    """
    known = {"services/flood.py::null-guard"}
    findings = [
        {"file": "services/flood.py", "category": "null-guard", "severity": "high"},
        {"file": "services/solar.py", "category": "silent-failure", "severity": "high"},
    ]
    fresh = [f for f in findings if cr.finding_key(f) not in known]
    repeats = [f for f in findings if cr.finding_key(f) in known]

    assert [f["file"] for f in fresh] == ["services/solar.py"]
    assert [f["file"] for f in repeats] == ["services/flood.py"]

    # And once the new one is adjudicated too, nothing is left to gate.
    known |= {cr.finding_key(f) for f in findings}
    assert [f for f in findings if cr.finding_key(f) not in known] == []
