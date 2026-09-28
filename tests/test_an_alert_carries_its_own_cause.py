"""One stray backslash was the entire content of five production alerts.

WHAT HAPPENED
-------------
`run_monitors.py` ships the last 2,000 bytes of a failing child's **stderr** in its
Telegram alert. `enrichment/config/parramatta_config.py` had a plain `\"\"\"` docstring
containing ``re.sub(r'\\.?\\d+$','',...)`` as prose. Python reports `\\.` and `\\d` as
invalid escape sequences at import, on stderr — so every alert from every extraction
run arrived looking like this:

    🚨 dcp-extract failed (exit 1)
    Env missing: []
    /app/enrichment/config/parramatta_config.py:58: SyntaxWarning: invalid escape
      sequence '\\.'

The real cause, found only by reading the Railway logs by hand, was
`429 credit_balance_exhausted` on all 11 chapters. None of that reached the alert.
The prompt that opened this work counted **four** separate alerts whose whole content
was this one character; the one on 2026-09-28 was the fifth.

An alert that names the wrong cause is worse than no alert. It is read once, found
useless, and then ignored — which is the same end state as silence, reached faster.

WHY THIS TEST IS SCOPED TO enrichment/config/
---------------------------------------------
Eleven other files in the repo carry invalid escape sequences (measured 2026-09-28).
They are **deliberately not covered here**, and listing them was checked rather than
assumed:

  - `scripts/dq_probe_live.py` — `'\\m...\\M'` are PostgreSQL word-boundary operators
    inside a SQL string, not Python escapes. The SQL is correct; Python preserves an
    unrecognised escape verbatim.
  - `services/universal_regulatory_engine.py` — `.replace('_', '\\s+')` builds a regex
    and works for the same reason.
  - nine in the retired-scripts archive and a strategy folder — not deployed, not
    imported by any monitor. (Named in prose, not as a path: tests/test_archive_is_not_live_code.py forbids that literal path string outside
    the archive itself, so that the scanner exemption cannot be quietly widened.)

None is a bug, and none is on a path that can reach an alert. Widening this test to
the whole repo would turn a targeted guard into a cleanup mandate over code the
"don't touch pre-existing dead code" rule says to leave alone. `enrichment/config/`
is the set the extractor imports on every run, so it is the set whose noise reaches
stderr while a chapter is failing.

WHY A WARNING, NOT AN IMPORT
----------------------------
The files are compiled, never imported: importing the extraction config pulls the
extraction stack, which the mocked pre-push environment does not have. A gate that
cannot run at the gate is not a gate.

HOW THE DETECTOR WAS VERIFIED
-----------------------------
The first version of this sweep reported **zero** files, including the one that was
provably warning in production. The bug: `warnings.simplefilter()` REPLACES the whole
filter list rather than adding to it, so a second `simplefilter('error', SyntaxWarning)`
call silently discarded the `DeprecationWarning` rule set the line before — and on
Python 3.11 an invalid escape is a DeprecationWarning, so nothing was escalated and
every file read clean. `record=True` + a single `simplefilter('always')` is used here
instead, and `test_the_detector_catches_a_known_bad_string` proves it fires on input
known to be wrong (`memory/feedback-search-plus-check-amplifies-leaks.md`: test on
known-wrong AND known-right before trusting a sweep).
"""
from __future__ import annotations

import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "enrichment" / "config"

#: A docstring whose prose contains a regex. The exact shape that caused the incident.
KNOWN_BAD = '"""prose mentioning re.sub(r\'\\.?\\d+$\')"""'
KNOWN_GOOD = 'r"""prose mentioning re.sub(r\'\\.?\\d+$\')"""'


def invalid_escapes(source: str, name: str) -> list[tuple[str, int | None]]:
    """Every invalid-escape warning `source` raises at compile time.

    Python version matters and is the reason this returns warnings rather than
    catching an exception: 3.11 raises DeprecationWarning for an invalid escape and
    3.12+ raises SyntaxWarning. Recording every warning and filtering by message
    covers both, so a local run and the Railway container agree.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            compile(source, name, "exec")
        except SyntaxError:
            return []
    return [(str(w.message), w.lineno) for w in caught
            if "invalid escape" in str(w.message)]


class TestTheDetectorItselfWorks:
    """A sweep that cannot fail is not evidence. This one silently reported zero."""

    def test_the_detector_catches_a_known_bad_string(self):
        assert invalid_escapes(KNOWN_BAD, "known_bad.py"), (
            "the detector does not fire on input that is known to be wrong, so its "
            "verdict on real files means nothing"
        )

    def test_the_detector_passes_a_known_good_string(self):
        """Same text, raw docstring. A detector that fires on everything is no better
        than one that fires on nothing."""
        assert invalid_escapes(KNOWN_GOOD, "known_good.py") == []


class TestTheExtractionConfigsCarryNoStderrNoise:
    def test_the_config_dir_exists(self):
        assert CONFIG_DIR.is_dir(), (
            f"{CONFIG_DIR} is gone, so this guard silently covers nothing")

    def test_no_config_file_emits_an_invalid_escape(self):
        offenders = {}
        for path in sorted(CONFIG_DIR.rglob("*.py")):
            source = path.read_bytes().decode("utf-8", errors="replace")
            hits = invalid_escapes(source, str(path))
            if hits:
                offenders[path.relative_to(ROOT).as_posix()] = hits
        assert not offenders, (
            "these files print a warning to stderr on every extraction run, and "
            "run_monitors.py ships the last 2,000 bytes of stderr as the alert body — "
            "so this noise replaces the real failure cause. Prefix the docstring with "
            f"r, or escape the backslash: {offenders}"
        )

    def test_the_file_that_caused_the_incident_is_covered(self):
        """Named explicitly. A guard over a directory silently stops covering the case
        it was written for if that file is ever moved."""
        culprit = CONFIG_DIR / "parramatta_config.py"
        assert culprit.exists(), (
            "parramatta_config.py moved; this guard no longer covers the file whose "
            "stray backslash was the entire content of five production alerts")
        assert invalid_escapes(
            culprit.read_bytes().decode("utf-8", errors="replace"), str(culprit)) == []

    def test_the_docstring_prose_was_kept_not_deleted(self):
        """The fix must be `r\"\"\"`, not deleting the sentence. That sentence explains
        why the progressive strip is safe, which is load-bearing knowledge about how a
        page footer avoids inheriting a heritage Part."""
        text = (CONFIG_DIR / "parramatta_config.py").read_bytes().decode(
            "utf-8", errors="replace")
        assert "re.sub(r'" in text, (
            "the regex prose was removed rather than the docstring made raw — the "
            "warning is gone and so is the explanation")
        assert text.lstrip().startswith('r"""'), (
            "the docstring is not raw, so the fix was made some other way and the "
            "warning can return with the next edit")
