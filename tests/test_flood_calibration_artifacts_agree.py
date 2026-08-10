"""The published calibration figures must match the run that produced them.

WHY THIS EXISTS
---------------
`docs/qa/flood-calibration-2022-result.md` published **recall 0.857, 6 of 7
points** while the JSON it cites in its own first paragraph recorded **34 of 38,
recall 0.895**. Two incompatible sample sizes, recall values and confidence
intervals were presented as the same run, and the 6-of-7 figure was copied on
into `docs/PRODUCT_ASSURANCE_POSITION.md` — the page written for an outside
reader.

Re-running `scripts/run_flood_calibration_2022.py` at seed 20220228 reproduces
the JSON byte-identically, so the JSON was the reproducible artifact and the
markdown carried an intermediate run that was never refreshed. The VERDICT was
the same either way, which is the only reason this was a documentation defect
rather than a wrong conclusion — next time the gap could fall the other way.

A human transcribing numbers between two files will make this mistake again.
This test removes the opportunity: the prose has to agree with the evidence it
cites, or CI says so.

WHAT IT DOES NOT CHECK
----------------------
That the calibration is CORRECT. It checks that the published figures match the
committed result. A wrong run, faithfully transcribed, still passes here — the
falsifiability of the run itself lives in the pre-committed pass mark, not here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RESULT_JSON = ROOT / "docs" / "qa" / "flood-calibration-2022-result.json"
RESULT_MD = ROOT / "docs" / "qa" / "flood-calibration-2022-result.md"
ASSURANCE_MD = ROOT / "docs" / "PRODUCT_ASSURANCE_POSITION.md"

pytestmark = pytest.mark.skipif(
    not RESULT_JSON.exists(),
    reason="flood calibration result not present in this checkout",
)


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads(RESULT_JSON.read_text(encoding="utf-8"))


def _headline(md: str) -> str:
    """The Verdict blockquote — the figure a reader actually takes away."""
    m = re.search(r"^> \*\*RECALL .*$", md, re.M)
    assert m, "no '> **RECALL ...' headline found in the result markdown"
    return m.group(0)


def test_headline_recall_matches_the_run(result):
    line = _headline(RESULT_MD.read_text(encoding="utf-8"))
    m = re.search(r"RECALL\s+(\d+\.\d+)", line)
    assert m, f"no recall figure in headline: {line}"
    published = float(m.group(1))
    actual = round(float(result["recall"]), 3)
    assert published == pytest.approx(actual, abs=0.0005), (
        f"markdown publishes recall {published} but "
        f"{RESULT_JSON.name} records {actual}"
    )


def test_headline_sample_size_matches_the_run(result):
    line = _headline(RESULT_MD.read_text(encoding="utf-8"))
    m = re.search(r"(\d+)\s+of\s+(\d+)\s+scored points", line)
    assert m, f"no 'N of M scored points' in headline: {line}"
    hits, scored = int(m.group(1)), int(m.group(2))
    assert hits == result["hits"], (
        f"markdown says {hits} hits, JSON records {result['hits']}"
    )
    assert scored == result["n_scored"], (
        f"markdown says {scored} scored, JSON records {result['n_scored']}"
    )


def test_headline_interval_matches_the_run(result):
    """A confidence interval is the honest part of a small sample.

    Publishing a wider or narrower one than the run produced misstates exactly
    the thing a reader should be looking at.

    BOTH intervals are pinned, by label. The headline used to carry only
    Wilson, which assumes 37 independent trials \u2014 an assumption this run
    disproves, since both misses fall inside one AOI cluster. Leading with the
    narrower interval would mean publishing the flattering assumption after
    seeing it fail, so the cluster interval governs and both must be quoted.
    """
    line = _headline(RESULT_MD.read_text(encoding="utf-8"))
    for label, lo_key, hi_key in (("Cluster", "cluster_lo", "cluster_hi"),
                                  ("Wilson", "wilson_lo", "wilson_hi")):
        m = re.search(
            rf"{label}\s+95% CI\s+(\d+\.\d+)\s*[\u2013-]\s*(\d+\.\d+)", line)
        assert m, f"no {label} interval in headline: {line}"
        assert float(m.group(1)) == pytest.approx(float(result[lo_key]), abs=0.001), (
            f"{label} lower bound in the headline does not match the run")
        assert float(m.group(2)) == pytest.approx(float(result[hi_key]), abs=0.001), (
            f"{label} upper bound in the headline does not match the run")


def test_the_governing_interval_is_the_conservative_one(result):
    """The verdict must not be computed from the narrower interval.

    Wilson is narrower here because it assumes independence. If a future change
    quietly reverts the verdict to Wilson's bound, a result could be declared a
    PASS on an assumption the same run disproves.
    """
    assert float(result["cluster_lo"]) <= float(result["wilson_lo"]) + 1e-9, (
        "the cluster lower bound is no longer the conservative one \u2014 check "
        "whether clustering still reflects how the misses are distributed"
    )
    if result["verdict"] == "PASS":
        assert float(result["cluster_lo"]) >= float(result["pass_mark"]), (
            "PASS was declared without the CLUSTER lower bound clearing the mark"
        )


def test_pass_mark_matches_the_precommitted_value(result):
    line = _headline(RESULT_MD.read_text(encoding="utf-8"))
    m = re.search(r"[Pp]ass mark\s+(\d+\.\d+)", line)
    assert m, f"no pass mark in headline: {line}"
    assert float(m.group(1)) == pytest.approx(float(result["pass_mark"]))


def test_verdict_matches_the_run(result):
    md = RESULT_MD.read_text(encoding="utf-8")
    assert result["verdict"].lower() in md.lower(), (
        f"markdown does not state the JSON verdict {result['verdict']!r}"
    )


@pytest.mark.skipif(not ASSURANCE_MD.exists(), reason="assurance page absent")
def test_assurance_page_quotes_the_same_figures(result):
    """The outward-facing page is the one that matters most.

    It duplicated the stale 6-of-7 figure, so a reader following its own
    citation would have found different numbers. Whatever it quotes must come
    from the committed run.
    """
    text = ASSURANCE_MD.read_text(encoding="utf-8")
    hits, scored = result["hits"], result["n_scored"]
    assert f"{hits} of {scored} points" in text, (
        f"assurance page does not quote '{hits} of {scored} points' from the run"
    )
    assert f"{round(float(result['recall']), 3)}" in text, (
        "assurance page does not quote the run's recall"
    )


def test_every_miss_is_enumerated(result):
    """The report named ONE miss; the artifact holds FOUR.

    Understating a failure count by four in a document written to be relied on
    is the same class of defect as the headline mismatch — and worse here,
    because the four misses turned out to share a cause (Richmond Valley holds
    zero flood polygons) that a single named miss completely hid.

    Each miss must appear in the prose by its coordinates, so adding a miss to
    the run forces it into the write-up.
    """
    md = RESULT_MD.read_text(encoding="utf-8")
    misses = [r for r in result["results"] if r.get("hit") is False]
    assert misses, "no misses in the artifact — this test needs rewriting if that is real"
    for m in misses:
        coord = f"{m['lat']:.4f}, {m['lng']:.4f}"
        alt = f"{m['lat']:.4f},{m['lng']:.4f}"
        assert coord in md or alt in md, (
            f"miss at {coord} is in the artifact but not named in the report"
        )


def test_the_report_states_the_true_miss_count(result):
    """Guards the specific sentence that was wrong.

    'The one miss' as a heading, when there are four, is not a rounding error —
    it is the reader being told the failure is isolated when it is a cluster.
    """
    md = RESULT_MD.read_text(encoding="utf-8").lower()
    n = len([r for r in result["results"] if r.get("hit") is False])
    assert "## the one miss" not in md, (
        f"report still headed 'The one miss' but the artifact records {n}"
    )


# --- the gap these tests had themselves -----------------------------------
#
# Everything above pins the HEADLINE line. When the reference was corrected for
# polygon holes and the run moved from 34/38 to 35/37, all of it passed while
# the "What this licenses" block — the one sentence written to be quoted
# externally — still published 34 of 38 and CI 0.76-0.96. A guard that checks
# one line of a document full of quotable numbers is a guard with a hole in it.
#
# The fix is not "also pin the licensed block", which would leave the next
# section unguarded in the same way. It is to sweep the WHOLE document for
# sample-size claims and allow stale ones only where a stale number is the
# point: the correction banners and the run-history table.


def test_the_licensed_statement_quotes_the_run(result):
    """The sentence marked for external quotation is the highest-stakes one.

    It is explicitly offered to outside readers, so a superseded figure here
    travels further than anywhere else in the document.
    """
    md = RESULT_MD.read_text(encoding="utf-8")
    m = re.search(r"\*\*Licensed:\*\*\s*\*\"(.+?)\"\*", md, re.S)
    assert m, "no '**Licensed:** \"...\"' block found — has it been renamed?"
    licensed = m.group(1)

    hits, scored = result["hits"], result["n_scored"]
    assert f"{hits} of {scored} points" in licensed, (
        f"the licensed statement does not quote the run: expected "
        f"'{hits} of {scored} points', got:\n{licensed}"
    )
    for bound in ("wilson_lo", "wilson_hi"):
        assert f"{float(result[bound]):.3f}" in licensed, (
            f"the licensed statement omits or misquotes {bound} "
            f"({float(result[bound]):.3f}):\n{licensed}"
        )


def _stale_allowed(line: str) -> bool:
    """Contexts where quoting a superseded figure is the intended content.

    Correction banners (blockquotes) and the run-history table exist precisely
    to record what the number used to be. Nowhere else may.
    """
    stripped = line.lstrip()
    return stripped.startswith(">") or stripped.startswith("|")


def test_no_superseded_sample_size_survives_outside_a_correction(result):
    """Sweep every 'N of M points' claim in the document.

    This is the test that would have caught the licensed statement, and it
    catches the next one too — a new section quoting an old figure fails here
    without anyone remembering to extend the list.
    """
    current = f"{result['hits']} of {result['n_scored']} points"
    offenders = []
    for n, line in enumerate(RESULT_MD.read_text(encoding="utf-8").splitlines(), 1):
        if _stale_allowed(line):
            continue
        for m in re.finditer(r"\b(\d+) of (\d+) points\b", line):
            if m.group(0) != current:
                offenders.append(f"  line {n}: '{m.group(0)}' -- {line.strip()[:90]}")
    assert not offenders, (
        f"superseded sample sizes published outside a correction banner or the\n"
        f"history table (current run is '{current}'):\n" + "\n".join(offenders)
    )


def test_the_harness_actually_ran(result):
    """A run of all-errors must never be published as recall 0.

    `scored` includes errored points by design (a product that cannot answer
    has not answered), which meant the `if not scored:` abort was dead code —
    `False is not None`. A total outage would have published 'recall 0.000,
    VERDICT FAIL'. The runner now guards on executions, and these fields are
    what make that visible in the artifact rather than only in the source.
    """
    assert "n_executed" in result, (
        "the result carries no n_executed field, so a reader cannot tell a "
        "measured zero from a dead harness — the guard has been removed or "
        "the artifact predates it"
    )
    assert result["n_executed"] > 0, "no point executed; this must abort, not publish"
    assert result["n_executed"] + result["n_errored"] == result["n_sampled"], (
        f"executions ({result['n_executed']}) + errors ({result['n_errored']}) "
        f"!= sampled ({result['n_sampled']}) — the counters do not account for "
        f"every point, which is how an error count of a structural zero hid"
    )


_NUMBER_WORDS = {
    30: "thirty", 31: "thirty-one", 32: "thirty-two", 33: "thirty-three",
    34: "thirty-four", 35: "thirty-five", 36: "thirty-six", 37: "thirty-seven",
    38: "thirty-eight", 39: "thirty-nine", 40: "forty",
}


def test_no_superseded_sample_size_in_prose(result):
    """The sweep above matches 'N of M points'. Prose does not use that form.

    "Thirty-eight points is still too few to decide" survived the corrected run
    AND the first sweep, because it spells the number out and omits the
    numerator. A reader taking the sample size from the narrative rather than
    the headline gets the wrong denominator for a 35-of-37 result.

    So: any 'NN points' or spelled-out 'thirty-eight points' claim outside a
    correction banner or the history table must be the current scored count.
    """
    scored = result["n_scored"]
    wrong_digits = {n for n in range(20, 60) if n != scored}
    wrong_words = {w for n, w in _NUMBER_WORDS.items() if n != scored}

    offenders = []
    for ln, line in enumerate(RESULT_MD.read_text(encoding="utf-8").splitlines(), 1):
        if _stale_allowed(line):
            continue
        low = line.lower()
        for m in re.finditer(r"\b(\d{2}) (?:scored )?points\b", low):
            if int(m.group(1)) in wrong_digits:
                offenders.append(f"  line {ln}: '{m.group(0)}' -- {line.strip()[:80]}")
        for w in wrong_words:
            if re.search(rf"\b{w} (?:scored )?points\b", low):
                offenders.append(f"  line {ln}: '{w} points' -- {line.strip()[:80]}")
    assert not offenders, (
        f"sample-size claims in prose disagree with the run ({scored} scored "
        f"points):\n" + "\n".join(offenders)
    )
