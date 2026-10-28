"""Known answers for the flood signal, from real saved customer checks.

The fixture (tests/fixtures/flood_known_answers.json) is built by
`python scripts/flood_signal_regression.py --build-fixture`: every case is a
real address and its real saved inputs, chosen by query, never typed.

'positive' must give low or above; 'no_signal' must give none or unavailable.
Cases the rule got wrong when the fixture was built are xfail(strict=True):
the 6 where Copernicus EMSR567 alone decides the level (an 86,349 km2 shape
that holds the activation's whole mapped area, not its flood extent). strict
means the fix must make them pass, and the marker must then be removed --
a fix that leaves them failing, or a regression that brings the old rule back,
both turn this file red.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.flood_truth import _compute_flood_signal

FIXTURE = Path(__file__).parent / "fixtures" / "flood_known_answers.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
LEVEL = {"unavailable": 0, "none": 0, "low": 1, "moderate": 2, "elevated": 3}

_EMS_ALONE = pytest.mark.xfail(
    strict=True,
    reason="EMSR567 alone gives moderate/elevated; fixed by the flood-signal rule PR",
)


# Only these groups may be expected-wrong. Any other case wrong at build time is
# a bad fixture (or a broken rule), never an expected failure.
EXPECTED_WRONG_GROUPS = {"ems_alone_ridge_over_80m", "ems_alone_any"}


def _params(expected_classes: set):
    out = []
    for c in CASES:
        if c["expect"] not in expected_classes:
            continue
        # strict xfail only where the case really is wrong today; a case in the
        # same group that is already right must keep passing.
        wrong = c["group"] in EXPECTED_WRONG_GROUPS and c["correct_at_build"] is False
        marks = [_EMS_ALONE] if wrong else []
        out.append(pytest.param(c, id=f"{c['group']}:{c['case_id']}", marks=marks))
    return out


def test_only_ems_alone_cases_are_expected_wrong():
    """A rebuild while the rule is broken must not turn real failures into xfails."""
    bad = [(c["group"], c["case_id"]) for c in CASES
           if c["correct_at_build"] is False and c["group"] not in EXPECTED_WRONG_GROUPS]
    assert bad == []


def test_fixture_holds_no_customer_address():
    for c in CASES:
        assert "address" not in c and "address_council" not in c["inputs"]


def test_fixture_covers_every_group():
    """A shrunken fixture can only flatter the rule: fail if a group went missing."""
    groups = {c["group"] for c in CASES}
    assert groups >= {
        "epi_overlay", "council_fpa", "hawkesbury_1pct", "ems_alone_ridge_over_80m",
        "ems_alone_any", "no_evidence", "nsw_2022_real_extent",
    }
    # 19 at build on 2026-10-28: the database held only one saved check with
    # no flood evidence at all, so 'no_evidence' has 1 case, not 3.
    assert len(CASES) >= 19


@pytest.mark.parametrize("case", _params({"positive"}))
def test_flood_evidence_gives_a_signal(case):
    assert LEVEL[_compute_flood_signal(case["inputs"])] >= 1, case["positives"]


@pytest.mark.parametrize("case", _params({"no_signal"}))
def test_no_flood_evidence_gives_no_signal(case):
    assert LEVEL[_compute_flood_signal(case["inputs"])] == 0, case["positives"]
