"""A row of mirrored word salad reached a human and asked them to confirm a number in it.

Found 2026-09-23 from a screenshot of the live review queue. The row's own text
read ``kcabtes m0.2`` -- "setback" spelled backwards -- beside
``nimm0.4 xamm0.41`` and ``OOMBATHROOM``, and the UI asked a reviewer whether
0.41 was correct. There is no judgement to make about that. The PDF is laid out
right-to-left in places, usually inside a figure or a table, and whole words come
back mirrored.

`_AUTO_REJECT_REASONS` held three reasons -- garbled_glyphs, junk_ref,
emptied_by_strip -- and none of them names this, so the row became `pending`.
§5.2's rule is the opposite: a row that cannot be PROVEN is rejected and the
chapter retries; only genuine ambiguity reaches a person, and it arrives carrying
its evidence.

WHY THE DETECTOR IS EVIDENCE-BASED AND NOT A SUBSTRING PROBE
------------------------------------------------------------
The obvious version -- look for 'kcabtes', 'nimm', 'xamm' as substrings --
matched 40 SERVED rows on 2026-09-23 of which only 5 were genuinely reversed: a
35/40 false-positive rate, because those letter runs occur inside ordinary words.
Shipping that as an auto-REJECT would have thrown away real controls. A token
counts only when its own reversal is a word this domain uses and the token
itself is not, and only when two independent such tokens appear in one provision.

MUTATION NOTE. The threshold and the vocabulary are both load-bearing:
  * drop to one token and `test_a_single_mirrored_looking_token_is_not_enough`
    fails -- one hit can be a surname or an acronym.
  * swap the domain vocabulary for a general dictionary and the reversible
    English pairs below start firing on ordinary prose.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.dcp_extract_changed import (  # noqa: E402
    _AUTO_REJECT_REASONS,
    classify_row_fidelity,
    reversed_text_tokens,
)

#: The real thing, from served city_of_sydney provision id=95623.
REAL_FIGURE_LABEL = (
    "# 5.2.5 Pedestrian and bike networks Section 5 Figure 5.51 Local Street "
    "Sydney DCP 2012 - December 2012 5.2-8 etis yradnuob htaptoof )devap("
)

#: The row from the screenshot that prompted this, id=69817.
REAL_TABLE_MIRROR = (
    "# 12.0 Rear courtyard kcabtes m0.2 nimm4.0mmin BEDROOMBEDROOM "
    "OOMBATHROOM tnorf m0 yradnuob"
)


class TestItCatchesTheRealThing:
    def test_a_mirrored_figure_label_is_detected(self):
        found = {t.lower() for t in reversed_text_tokens(REAL_FIGURE_LABEL)}
        assert {"etis", "yradnuob", "htaptoof"} <= found

    def test_a_mirrored_table_is_detected(self):
        found = {t.lower() for t in reversed_text_tokens(REAL_TABLE_MIRROR)}
        assert "kcabtes" in found and "yradnuob" in found

    def test_it_is_rejected_rather_than_queued_for_a_person(self):
        """The whole point. `pending` means a human is asked to rule on word
        salad; `failed` with this reason means the chapter retries."""
        verdict, reason = classify_row_fidelity("6A.4", None, REAL_FIGURE_LABEL, "added")
        assert verdict == "failed"
        assert "reversed_text" in reason

    def test_the_reason_is_in_the_auto_reject_set(self):
        """A reason that fails but is not in this set still lands on a human.
        `dcp_extract_changed` computes `auto_reject = fidelity == 'failed' and
        reason_tags <= _AUTO_REJECT_REASONS`, so membership is what decides."""
        assert "reversed_text" in _AUTO_REJECT_REASONS


class TestItDoesNotFireOnRealText:
    @pytest.mark.parametrize("text", [
        # Ordinary control prose, dense with the very words the detector mirrors.
        "The minimum front setback to the street boundary is 4.5 metres, measured "
        "to the building line. Rear setbacks for a habitable room are 6 metres.",
        # A figure caption that is NOT mirrored.
        "Figure 5.51 Local Street: site boundary, footpath (paved), and driveway "
        "crossing shown for a multi-dwelling development.",
        # Numbers and units, no prose at all.
        "4.0 m min; 12.0 m max; 9.0 m; 6.0 m; 4.0 m",
        "",
    ])
    def test_clean_text_produces_nothing(self, text):
        assert reversed_text_tokens(text) == []

    @pytest.mark.parametrize("word", ["drawer", "reward", "straw", "warts",
                                      "desserts", "stressed", "stop", "pots",
                                      "level", "civic", "rotator"])
    def test_ordinary_reversible_english_does_not_fire(self, word):
        """The confusable negative for the VOCABULARY choice. English is full of
        words that reverse into other words, and palindromes reverse into
        themselves. A general dictionary would make every one of these a hit;
        a domain vocabulary makes none of them one."""
        assert reversed_text_tokens(f"The {word} must comply with this control.") == []

    def test_a_single_mirrored_looking_token_is_not_enough(self):
        """The confusable negative for the THRESHOLD. One hit can be a surname,
        a product name or an acronym that happens to mirror a planning word.
        Every real instance measured carries three or more."""
        one = "The etis plan referenced in Schedule 2 applies to this land."
        assert len(reversed_text_tokens(one)) == 1
        verdict, reason = classify_row_fidelity("2.1", None, one, "added")
        assert verdict == "ok" or "reversed_text" not in (reason or "")

    def test_the_same_word_twice_is_still_one_signal(self):
        """Two OCCURRENCES of one token are not two independent words -- a
        repeated figure label would otherwise trip the gate on its own."""
        twice = "etis and etis again, nothing else here."
        verdict, reason = classify_row_fidelity("2.1", None, twice, "added")
        assert "reversed_text" not in (reason or "")


class TestTheRemovalExemption:
    def test_deleting_a_mirrored_provision_is_not_auto_rejected(self):
        """Identical reasoning to junk_ref's exemption, which is documented
        beside it: the row that DELETES a mirrored provision carries its text,
        so auto-rejecting the clean-up freezes the chapter it is cleaning.
        Measured 2026-09-18, two such rows held a 105-row chapter."""
        verdict, reason = classify_row_fidelity(
            "5.2.5", REAL_FIGURE_LABEL, None, "removed")
        assert "reversed_text" not in (reason or "")
