"""Google Solar reports energy at the panel. The meter records less.

WHY THIS FILE EXISTS
--------------------
`services/solar_yield.py` sums Google Solar's per-panel `yearlyEnergyDcKwh` —
DC energy, before the inverter. That figure was surfaced as "Calculated yield
… kWh/year" with nothing anywhere saying DC, and then monetised. On a typical
20-panel roof at 9,000 kWh DC it overstated the annual saving by 16.4%, showed
payback at 6.4 years against 7.5, and reported a ten-year return of $2,420
where the figure was $671 — the system cost is subtracted afterwards, so the
whole error lands on the margin.

The failure this guards is not "the label is missing". It is that a number
correct for one basis was doing work that only the other basis supports.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from services.solar_yield import (  # noqa: E402
    DC_TO_DELIVERED,
    DELIVERED_LOSS_PCT,
    DELIVERY_BASIS,
    PVWATTS_DEFAULT_SYSTEM_LOSS,
    PVWATTS_INVERTER_EFFICIENCY,
    delivered_kwh,
)


class TestDeliveredIsAlwaysLessThanDC:
    @pytest.mark.parametrize("dc", [1.0, 9000.0, 12345.6, 250000.0])
    def test_strictly_lower_for_any_positive_input(self, dc):
        """The whole point. If this ever passes at equality the derate has been
        neutralised and the DC figure is being presented as delivered again."""
        assert delivered_kwh(dc) < dc

    def test_the_factor_is_the_published_pvwatts_default(self):
        """Pinned to the SOURCE, not to a number someone liked. NREL PVWatts v8
        publishes 14.08% total system losses. If a future edit nudges this, the
        test fails and the edit has to argue with the citation."""
        assert PVWATTS_DEFAULT_SYSTEM_LOSS == pytest.approx(0.1408)

    def test_the_inverter_is_a_SEPARATE_factor(self):
        """The correction adversarial review forced.

        PVWatts' 14.08% does NOT include the inverter — PVWatts models inverter
        efficiency as its own parameter, default 96%. The first version of this
        change applied only the 14.08% and still overstated delivered output by
        about 4%. Both factors are required to get from DC at the panel to AC
        at the meter, and this pins that they are BOTH applied rather than one
        quietly standing in for the pair.
        """
        assert PVWATTS_INVERTER_EFFICIENCY == pytest.approx(0.96)
        assert DC_TO_DELIVERED == pytest.approx(0.8592 * 0.96)
        assert DC_TO_DELIVERED < 1.0 - PVWATTS_DEFAULT_SYSTEM_LOSS, (
            "the inverter factor is not being applied — this is the exact "
            "regression that leaves delivered output ~4% too high"
        )

    def test_the_stated_percentage_matches_the_arithmetic(self):
        """The copy says 'about 18%'. If the factors change and the sentence
        does not, the number and the words disagree on the same screen."""
        assert DELIVERED_LOSS_PCT == 18
        assert "18%" in DELIVERY_BASIS

    def test_the_worked_case_that_started_this(self):
        dc = 9000.0
        assert delivered_kwh(dc) == pytest.approx(7423.5, abs=0.5)


class TestAbsenceStaysAbsent:
    def test_none_in_none_out(self):
        """None must NOT become 0.0. A zero renders as a real roof that
        generates nothing, which is a wrong answer wearing a number; None
        renders as 'not established'."""
        assert delivered_kwh(None) is None

    def test_zero_stays_zero(self):
        assert delivered_kwh(0.0) == 0.0


class TestTheBasisIsStatedAndUsable:
    def test_it_names_dc_the_factor_and_the_authority(self):
        """A caveat a reader cannot act on is decoration. It has to say what
        the two numbers are, how far apart, on whose authority, and what to do
        next."""
        b = DELIVERY_BASIS.lower()
        assert "dc" in b
        assert "14.08" in b
        assert "pvwatts" in b
        assert "installer" in b, "must tell the reader where the real number comes from"

    def test_it_is_plain_english_not_a_disclaimer(self):
        assert "inverter" in DELIVERY_BASIS.lower()
        assert len(DELIVERY_BASIS) > 80


class TestTheFrontendMirrorsCannotDiverge:
    """There is ONE TypeScript implementation, and the surfaces import it.

    The first version of this change put the conversion inline on four
    surfaces. Adversarial review then found the four copies disagreeing three
    separate ways: one rejected a numeric string, one treated a real zero as a
    missing field, one claimed a DC conversion that had not happened. Four
    implementations of one rule IS the defect, so the copies were collapsed
    into frontend-nextjs/lib/solar/delivered.ts.

    What is left to guard is therefore structural and checkable: exactly one
    definition, everybody imports it, nobody re-derives the factor inline. That
    runs in pytest, which runs in CI, rather than in jest, which cannot run
    from a bare worktree.
    """

    SHARED = "frontend-nextjs/lib/solar/delivered.ts"
    MIRRORS = [
        "frontend-nextjs/app/api/reports/solar-yield/generate/route.ts",
        "frontend-nextjs/lib/pdf/solar-yield-report.tsx",
        "frontend-nextjs/components/tools/SolarYieldTool.tsx",
        "frontend-nextjs/app/reports/intelligence-brief/page.tsx",
    ]

    def test_there_is_exactly_one_typescript_definition(self):
        definers = []
        for p in (_ROOT / "frontend-nextjs").rglob("*.ts*"):
            if "node_modules" in str(p):
                continue
            if "DC_TO_DELIVERED =" in p.read_text(encoding="utf-8", errors="replace"):
                definers.append(str(p.relative_to(_ROOT)).replace("\\", "/"))
        assert definers == [self.SHARED], (
            f"the conversion must be defined once, in {self.SHARED}. Found: {definers}"
        )

    def test_every_surface_imports_the_shared_module(self):
        missing = [
            rel for rel in self.MIRRORS
            if "lib/solar/delivered" not in
               (_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        ]
        assert not missing, (
            "these surfaces do not import the shared conversion, so they are "
            "computing delivered energy their own way: " + str(missing)
        )

    def test_no_surface_re_derives_the_factor_inline(self):
        """0.1408 outside the shared module means a second implementation is
        growing back — which is exactly how the four copies drifted apart."""
        offenders = []
        for rel in self.MIRRORS:
            text = (_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                if "0.1408" in line and not line.strip().startswith("//"):
                    offenders.append(f"{rel}:{n}")
        assert not offenders, (
            "the loss factor is being re-derived outside the shared module: "
            + str(offenders)
        )

    def test_the_shared_module_carries_both_authority_figures(self):
        text = (_ROOT / self.SHARED).read_text(encoding="utf-8", errors="replace")
        for figure in (f"{PVWATTS_DEFAULT_SYSTEM_LOSS}", f"{PVWATTS_INVERTER_EFFICIENCY}"):
            assert figure in text, (
                f"{self.SHARED} no longer carries {figure} from "
                f"services/solar_yield.py, so backend and surface disagree"
            )

    def test_no_surface_still_monetises_the_dc_figure_directly(self):
        """The original defect, pinned by shape rather than by memory: a rate
        MULTIPLIED BY annual_kwh_estimate.

        The first version of this test asked whether the DC field and a rate
        appeared on the same line, and it fired on a template literal that
        legitimately prints the DC figure as context while computing the dollar
        from the delivered one. Co-occurrence is not the defect; the
        multiplication is. Same correction as the control-subject rule earlier
        today — make it structural, not lexical, or the list fills with entries
        that are fine and stops being read.
        """
        import re
        RATE = r"(?:RETAIL_RATE|FEED_IN_RATE|FEED_IN_TARIFF|0\.32|0\.06)"
        PATTERNS = [
            re.compile(rf"annual_kwh_estimate\s*\)?\s*\*\s*{RATE}"),
            re.compile(rf"{RATE}\s*\*\s*[^;]*annual_kwh_estimate"),
        ]
        offenders = []
        for rel in self.MIRRORS:
            for n, line in enumerate(
                (_ROOT / rel).read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                s = line.strip()
                if s.startswith(("//", "*", "/*")):
                    continue
                if any(p.search(s) for p in PATTERNS):
                    offenders.append(f"{rel}:{n}")
        assert not offenders, (
            "a money figure is being derived from the DC number again: " + str(offenders)
        )

    def test_that_guard_can_actually_fire(self):
        """CONTROL. The rule above must reject the line the code used to carry,
        or it is a test that can only pass."""
        import re
        RATE = r"(?:RETAIL_RATE|FEED_IN_RATE|FEED_IN_TARIFF|0\.32|0\.06)"
        pat = re.compile(rf"annual_kwh_estimate\s*\)?\s*\*\s*{RATE}")
        was = "Math.round(o.annual_kwh_estimate * RETAIL_RATE).toLocaleString('en-AU')"
        now = "Math.round(deliveredKwh * RETAIL_RATE).toLocaleString('en-AU')"
        assert pat.search(was), "the guard fails to recognise the original defect"
        assert not pat.search(now), "the guard would reject the corrected line"


def test_the_rule_can_say_yes_and_no():
    """Control case.

    Several assertions above compare against a constant, which a mutant that
    sets DC_TO_DELIVERED = 1.0 would fail — but a mutant that returns the input
    unchanged while leaving the constant alone would slip past a test that only
    reads the constant. So pin the BEHAVIOUR and the CONSTANT together, in one
    place, in both directions.
    """
    assert delivered_kwh(1000.0) != 1000.0          # it must actually derate
    # abs=0.05 because the function rounds to 0.1 kWh; the tolerance is the
    # rounding step, not slack that would let a wrong factor through — 0.05 kWh
    # is far tighter than the 4% the missing inverter factor cost.
    assert delivered_kwh(1000.0) == pytest.approx(1000.0 * DC_TO_DELIVERED, abs=0.05)
