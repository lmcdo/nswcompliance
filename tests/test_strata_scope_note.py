"""Bug 4 Stage 2: the apartment/strata brief explains the absence of
development-capacity analysis instead of showing a silent blank.

Locks: each strata state yields the right scope note, the two messages are
distinct, and — critically — the user-facing copy stays clear of the banned
liability vocabulary (pre-pr-review.md check 5).
"""

import re

import pytest

from services.intelligence_brief import StrataType, _strata_scope_note

# pre-pr-review.md liability grep list
_BANNED = re.compile(
    r"\b(safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|"
    r"approved|guaranteed|certified|confirmed|verified|ensure|assure|accurate|"
    r"definitive|comprehensive|reliable)\b",
    re.IGNORECASE,
)


def test_apartment_has_scope_note():
    notes = _strata_scope_note(StrataType.APARTMENT)
    assert notes and "strata scheme" in notes[0]
    assert "not provided" in notes[0]


def test_ambiguous_has_distinct_scope_note():
    notes = _strata_scope_note(StrataType.AMBIGUOUS)
    assert notes and "could not be determined" in notes[0]
    assert notes != _strata_scope_note(StrataType.APARTMENT)


@pytest.mark.parametrize("st", [StrataType.DEVELOPMENT, StrataType.NOT_STRATA])
def test_non_apartment_states_have_no_note(st):
    assert _strata_scope_note(st) == []


@pytest.mark.parametrize("st", [StrataType.APARTMENT, StrataType.AMBIGUOUS])
def test_copy_has_no_banned_liability_language(st):
    for line in _strata_scope_note(st):
        m = _BANNED.search(line)
        assert m is None, f"banned liability term '{m.group()}' in scope note: {line!r}"


@pytest.mark.parametrize("st", [StrataType.APARTMENT, StrataType.AMBIGUOUS])
def test_scope_note_is_not_a_silent_blank(st):
    """The whole point of Stage 2: these states must produce text, not []."""
    notes = _strata_scope_note(st)
    assert notes
    assert all(isinstance(n, str) and n.strip() for n in notes)
