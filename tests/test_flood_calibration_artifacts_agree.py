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
    """
    line = _headline(RESULT_MD.read_text(encoding="utf-8"))
    m = re.search(r"CI\s+(\d+\.\d+)\s*[\u2013-]\s*(\d+\.\d+)", line)
    assert m, f"no Wilson interval in headline: {line}"
    lo, hi = float(m.group(1)), float(m.group(2))
    assert lo == pytest.approx(float(result["wilson_lo"]), abs=0.001)
    assert hi == pytest.approx(float(result["wilson_hi"]), abs=0.001)


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
