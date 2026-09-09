"""A stuck chapter has THREE states, and the alert must not merge two of them.

The 2026-09-09 Telegram alert listed 36 chapters as "stuck >48h", three of
which extraction SKIPS on purpose every single run (the 30MB guard in
extract_chapter). They were labelled "awaiting extraction" beside a runbook
line saying to run extraction. Running it skips them again. A list where some
items cannot be cleared by the action the list prescribes stops being read.

These tests are string and arithmetic only -- no database, no clock.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _watchdog():
    """Import the watchdog without its module-level DB connection.

    dcp_watchdog.py connects at import time, so it cannot simply be imported in
    a unit test. The two helpers under test are pure, so they are read out of
    the source and executed in isolation -- which also proves they carry no
    hidden dependency on the connection.
    """
    src = (ROOT / "scripts" / "dcp_watchdog.py").read_text(encoding="utf-8")
    m = re.search(r"^OVERSIZED_PDF_SKIP_BYTES\s*=", src, re.MULTILINE)
    assert m, "OVERSIZED_PDF_SKIP_BYTES assignment not found in dcp_watchdog.py"
    start = m.start()
    end = src.index("# \u2500\u2500 Check 1")
    ns: dict = {}
    exec(compile(src[start:end], "dcp_watchdog_helpers", "exec"), ns)  # noqa: S102
    for name in ("stuck_blocked_line", "is_oversized", "OVERSIZED_PDF_SKIP_BYTES"):
        assert name in ns, f"{name} missing from the extracted helper block"
    return ns


WD = _watchdog()
MB = 1024 * 1024


def test_the_watchdog_threshold_equals_the_extractors():
    """The alert must agree with the thing that actually does the skipping.

    Duplicated constants drift -- this repo has the receipts (the DQ-76 repair
    and its probe carried different brace classes and 103 rows sat unrepaired
    while the metric read 0). The watchdog says 'blocked' about a decision
    extract_chapter makes, so if the extractor's guard moves and this does not,
    the alert starts lying in one direction or the other.
    """
    src = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
    m = re.search(r"^OVERSIZED_PDF_SKIP_BYTES\s*=\s*(.+)$", src, re.MULTILINE)
    assert m, "OVERSIZED_PDF_SKIP_BYTES not found in dcp_extract_changed.py"
    assert eval(m.group(1).split("#")[0].strip()) == WD["OVERSIZED_PDF_SKIP_BYTES"]  # noqa: S307


@pytest.mark.parametrize("size,expected", [
    (139_006_750, True),    # canterbury_bankstown/chapter-7-6, the row that crashed prod
    (117_829_367, True),    # chapter-6-2, same council, same risk
    (32_888_474, True),     # chapter-7-5, just over
    (30 * MB + 1, True),    # the boundary itself, one byte over
    (30 * MB, False),       # exactly at it -- the guard is >, not >=
    (20_607_908, False),    # ashfield/chapter-d, measured fine in production
    (0, False),
])
def test_is_oversized_matches_the_measured_chapters(size, expected):
    assert WD["is_oversized"](size) is expected


def test_an_unmeasured_size_is_not_reported_as_blocked():
    """NULL content length is UNKNOWN, and unknown is not the same as blocked.

    The confusable negative for this guard. A chapter the monitor has never
    sized would, on a naive `size > threshold` written against None, either
    crash or silently compare as small. Neither is the answer: it must fall
    through to ordinary awaiting-extraction, because telling someone a chapter
    is permanently blocked on a size nobody measured is the worse error -- it
    parks real work as impossible.
    """
    assert WD["is_oversized"](None) is False


def test_the_blocked_line_says_the_action_will_not_work():
    """The whole point is that the line must not read as a to-do."""
    line = WD["stuck_blocked_line"]("canterbury_bankstown", "chapter-7-6-belmore-and-lakemba",
                                    139_006_750)
    assert "canterbury_bankstown/chapter-7-6-belmore-and-lakemba" in line
    assert "133MB" in line, line          # 139,006,750 bytes rendered in MiB
    assert "BLOCKED" in line
    assert "skip it again" in line
    assert "DQ-98" in line
    # It must NOT read as ordinary pending work.
    assert "awaiting extraction" not in line
