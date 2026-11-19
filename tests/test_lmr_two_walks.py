"""The crossings-only walk is shown BESIDE the normal walk and never changes the answer (services/lmr_area_decision.py)."""
import json
import re

from services import lmr_area_decision as d
from tests.test_lmr_area_decision import FACTS, lot


def ans(m):
    return d.decide(m, FACTS)


def verdict(a):
    """Everything that decides the answer, with the added crossings-only lines removed."""
    return re.sub(r'"crossings_only[a-z_]*": ("[^"]*"|[0-9.]+),? ?', "", json.dumps(a, default=str, sort_keys=True))


def text(a):
    return json.dumps(a, default=str)


def safe(m=1100.0, valid=True, reason=""):
    return {"m": m if valid else None, "valid": valid, "reason": reason}


def test_no_second_walk_means_no_crossings_line_and_the_same_answer():
    base = ans(lot())
    assert "crossings_only" not in text(base)
    assert text(ans(lot(walk_safe=None))) == text(base)


def test_second_walk_is_shown_with_the_difference_and_never_changes_the_verdict():
    base = ans(lot())
    two = ans(lot(walk_safe=safe(1100.0)))
    assert verdict(two) == verdict(base)                       # 450 m normal walk stays a yes even though the safe walk is over the limit
    t = text(two)
    assert "crossings_only_walk_m" in t and "1100" in t and "+650 m compared with the normal walk" in t
    assert "Check the crossings on the ground" in t


def test_same_walk_says_so():
    assert "the same as the normal walk" in text(ans(lot(walk_safe=safe(450.0))))


def test_unmeasurable_second_walk_gives_its_reason_not_a_number():
    a = ans(lot(walk_safe=safe(valid=False, reason="there is a footpath next to the lot, but the map has no route")))
    t = text(a)
    assert "could not be measured: there is a footpath next to the lot" in t and "crossings_only_walk_m" not in t
    assert verdict(a) == verdict(ans(lot()))


def test_when_the_normal_walk_is_unavailable_the_second_walk_is_still_shown_without_a_difference():
    a = ans(lot(walk={"m": None, "valid": False, "reason": "no footpath within 40 m"}, walk_safe=safe(900.0)))
    t = text(a)
    assert "about 900 m" in t and "compared with the normal walk" not in t


def test_a_bad_second_walk_value_is_ignored_rather_than_crashing():
    for bad in ("x", 5, True, {"m": "nine", "valid": True}, {"m": True, "valid": True}):
        a = ans(lot(walk_safe=bad))
        assert verdict(a) == verdict(ans(lot()))
