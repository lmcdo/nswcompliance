"""Shadow calibration — the served sun geometry against an INDEPENDENT reference.

WHAT THIS IS
------------
The shadow product is pure geometry: its answer can be checked exactly against
an outside source. Until now it never was. Five hand-typed constants and a
hand-computed UTC offset were served for four months across 538 reports with no
committed artefact behind them.

THE REFERENCE, AND WHY IT IS INDEPENDENT
----------------------------------------
Production computes sun position with ``suncalc`` — deliberately, because that
is the function ``pybdshadow`` calls internally to cast the polygon, so the
reported bearing and the drawn shadow cannot diverge. ``suncalc`` implements the
Meeus/SunCalc formulation.

The reference here is ``pvlib``'s NREL Solar Position Algorithm (Reda & Andreas
2004) — a different algorithm by different authors, not the same formula
rearranged.

**pvlib is a TEST-ONLY dependency.** It is declared in requirements-test.txt,
which is the file CI actually installs (.github/workflows/gates.yml:66,151,244).
It is deliberately ABSENT from services/requirements.txt, the container
manifest, so it cannot reach production. pvlib was named as our method on three
customer surfaces for months while never being imported anywhere in the repo;
PR #878 and migration 064 removed those claims and nothing may reintroduce them.

THIS TEST MUST NEVER SKIP
-------------------------
``import pvlib`` and ``import suncalc`` are plain module-scope imports. There is
no ``pytest.importorskip``. If either library is absent, collection ERRORS and
the build goes red — it does not quietly pass. That is the entire point: #880's
finding was a library declared in a file nothing read, which turned four safety
checks into decoration for months. A calibration test that can silently not-run
is worse than no calibration, because it comes with a badge.

THE PASS MARK — PRE-COMMITTED 2026-08-07, BEFORE THE FIRST RUN
--------------------------------------------------------------
Written down before any result was seen so it cannot be renegotiated afterwards:

    solar altitude          |ours - pvlib| <= 0.50 deg, everywhere
    solar azimuth/bearing   |ours - pvlib| <= 0.50 deg, where altitude <= 85 deg
    azimuth above 85 deg    NOT asserted — ill-conditioned near the zenith; the
                            exemption is named in the fixture, never silent
    local wall-clock label  EXACT to the minute. Zero tolerance: arithmetic.

Justification for 0.50 deg: the worst observed suncalc-vs-pvlib disagreement
across the served NSW envelope is 0.30 deg in bearing and 0.18 deg in altitude,
so this is ~1.7x the noise floor. Every defect this suite exists to catch clears
it by a wide margin — a daylight-saving error moves the bearing ~60 deg, the old
December constant was out 11.2 deg at the median, a hemisphere error would be
180 deg. In consequence terms 0.50 deg of altitude is under 0.8 m of shadow
length for a 9 m building at the June 9am altitude, and 0.50 deg is 1/90th of
the 45-degree compass bucket the PDF actually renders.

IF EXCEEDED: the build is red. There is no baseline, no ratchet and no xfail.
The scenario table stops rendering a direction rather than rendering an
unverified one.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

# HARD imports — no importorskip. See "THIS TEST MUST NEVER SKIP" above.
import pvlib
import pandas as pd
import suncalc

from services.shadow_model import (
    SCENARIO_YEAR, SHADOW_SCENARIOS, _SCENARIO_MAP, scenario_shadow_bearing_deg,
)
from services.solar_position import (
    AZIMUTH_ILL_CONDITIONED_ALTITUDE_DEG, NSW_TZ, local_wall_clock_to_utc,
    max_shadow_length_m, sun_position,
)

# ---------------------------------------------------------------------------
# The pre-committed pass mark
# ---------------------------------------------------------------------------
ALTITUDE_TOLERANCE_DEG = 0.50
AZIMUTH_TOLERANCE_DEG = 0.50

# Fixture points spanning the envelope `geometry_checks.check_point_nsw` admits
# (lat -38.0..-27.5, lng 140.5..160.0), plus the four locations that bound the
# 538 stored reports actually served. Real places, real coordinates — nothing
# invented.
NSW_POINTS = [
    ("Sydney CBD",       -33.8688, 151.2093),
    ("Byron Bay",        -28.6400, 153.6100),
    ("Broken Hill",      -31.9600, 141.4700),
    ("Bega",             -36.6700, 149.8400),
    ("Tweed Heads",      -28.1787, 153.5500),
    ("Wollongong",       -34.4250, 150.8931),
    ("NSW envelope SW",  -38.0000, 140.5000),
    ("NSW envelope NE",  -27.5000, 160.0000),
]


def _pvlib_reference(dt_utc: datetime, lat: float, lng: float) -> tuple[float, float]:
    """(altitude_deg, azimuth_deg) from pvlib's NREL SPA. The independent side."""
    frame = pvlib.solarposition.get_solarposition(
        pd.DatetimeIndex([dt_utc]), lat, lng)
    return (float(frame["apparent_elevation"].iloc[0]),
            float(frame["azimuth"].iloc[0]))


def _angular_difference(a: float, b: float) -> float:
    """Smallest signed difference a-b on a circle, in degrees."""
    return (a - b + 180.0) % 360.0 - 180.0


# ---------------------------------------------------------------------------
# Guard: the reference must be REAL, not a mock that agrees with everything
# ---------------------------------------------------------------------------

def test_reference_library_is_real_not_a_mock():
    """conftest_mocks stubs absent libraries with MagicMock. A MagicMock reference
    would compare equal to anything and certify a broken calculation. Pin that
    the reference returns genuine floats and a physically correct value."""
    assert isinstance(pvlib.__version__, str), "pvlib is not the real library"
    assert not type(pvlib).__name__.startswith("MagicMock")
    assert not type(suncalc).__name__.startswith("MagicMock")

    # Southern-hemisphere summer solstice, solar noon-ish: the sun must be high.
    altitude, azimuth = _pvlib_reference(
        datetime(2025, 12, 21, 1, 0, tzinfo=timezone.utc), -33.8688, 151.2093)
    assert isinstance(altitude, float) and isinstance(azimuth, float)
    assert 60.0 < altitude < 90.0, (
        f"reference returned a physically wrong altitude {altitude} for Sydney "
        f"near summer solstice noon — the reference itself is broken")


# ---------------------------------------------------------------------------
# DEFECT 1 — daylight saving. Zero tolerance.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario", SHADOW_SCENARIOS, ids=lambda s: s.key)
def test_modelled_instant_matches_its_own_label_exactly(scenario):
    """The UTC instant a scenario models MUST convert back to the wall-clock time
    it advertises. `dec21_12pm` stored hour_utc=2 — 13:00 AEDT — while labelling
    itself 12:00, so every one of the 538 stored reports modelled the summer
    scenario an hour late. Exact to the minute; this is arithmetic."""
    instant = scenario.instant_utc(SCENARIO_YEAR)
    local = instant.astimezone(NSW_TZ)

    assert local.strftime("%H:%M") == scenario.time_local, (
        f"{scenario.key} models {local:%Y-%m-%d %H:%M} {local.tzname()} but is "
        f"labelled {scenario.time_local} — the DST defect has returned")
    assert (local.year, local.month, local.day) == (SCENARIO_YEAR, scenario.month, scenario.day)


def test_december_is_aedt_and_june_is_aest():
    """Pins the specific timezone transition the old table got wrong. June and
    September fall in AEST (UTC+10); December falls in AEDT (UTC+11) because NSW
    daylight saving starts the first Sunday in October."""
    offsets = {}
    for scenario in SHADOW_SCENARIOS:
        local = scenario.instant_utc(SCENARIO_YEAR).astimezone(NSW_TZ)
        offsets[scenario.key] = local.utcoffset().total_seconds() / 3600.0

    assert offsets["jun21_9am"] == 10.0
    assert offsets["jun21_12pm"] == 10.0
    assert offsets["jun21_3pm"] == 10.0
    assert offsets["sep21_12pm"] == 10.0, (
        "21 September precedes the October DST start — must still be AEST")
    assert offsets["dec21_12pm"] == 11.0, (
        "21 December is inside NSW daylight saving — must be AEDT (UTC+11). "
        "This is the exact defect that made the summer scenario an hour late")


def test_december_instant_is_not_the_old_broken_one():
    """Regression pin with a hard-coded expected value. The old table produced
    2025-12-21T02:00Z (13:00 AEDT); the correct instant for a 12:00 label is
    2025-12-21T01:00Z."""
    instant = _SCENARIO_MAP["dec21_12pm"].instant_utc(SCENARIO_YEAR)
    assert instant == datetime(2025, 12, 21, 1, 0, tzinfo=timezone.utc)
    assert instant != datetime(2025, 12, 21, 2, 0, tzinfo=timezone.utc)


def test_june_9am_rolls_back_to_the_previous_utc_day():
    """9am AEST on 21 June is 23:00 UTC on 20 June. The old code carried a
    hand-written special case for this; tz conversion must produce it unaided."""
    instant = _SCENARIO_MAP["jun21_9am"].instant_utc(SCENARIO_YEAR)
    assert instant == datetime(2025, 6, 20, 23, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# DEFECTS 2 + 3 — the sun geometry itself, against the independent reference
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("place,lat,lng", NSW_POINTS, ids=[p[0] for p in NSW_POINTS])
@pytest.mark.parametrize("scenario", SHADOW_SCENARIOS, ids=lambda s: s.key)
def test_sun_position_matches_independent_reference(scenario, place, lat, lng):
    """THE calibration. Our production sun position vs pvlib's NREL SPA, at every
    scenario x every corner of the served envelope — 40 comparisons."""
    instant = scenario.instant_utc(SCENARIO_YEAR)
    ours_altitude, ours_azimuth = sun_position(instant, lat, lng)
    ref_altitude, ref_azimuth = _pvlib_reference(instant, lat, lng)

    altitude_error = abs(ours_altitude - ref_altitude)
    assert altitude_error <= ALTITUDE_TOLERANCE_DEG, (
        f"{scenario.key} at {place}: solar altitude {ours_altitude:.4f} vs "
        f"reference {ref_altitude:.4f} — off by {altitude_error:.4f} deg, "
        f"tolerance {ALTITUDE_TOLERANCE_DEG}")

    if ref_altitude > AZIMUTH_ILL_CONDITIONED_ALTITUDE_DEG:
        # DELIBERATELY NOT pytest.skip. Near the zenith the azimuth swings wildly
        # for a fraction of a degree of altitude, so comparing it proves nothing
        # — but a skip renders green and would be indistinguishable from the
        # test not running at all (#880's finding, and the skip ratchet counts
        # every one). So the exemption is itself an ASSERTION: production must
        # report the bearing as ABSENT here, which is the behaviour the
        # ill-conditioning threshold exists to produce. Altitude is asserted
        # above regardless.
        assert scenario_shadow_bearing_deg(
            scenario.key, lat, lng, SCENARIO_YEAR) is None, (
            f"{scenario.key} at {place}: solar altitude {ref_altitude:.2f} deg is "
            f"above the {AZIMUTH_ILL_CONDITIONED_ALTITUDE_DEG} deg ill-conditioning "
            f"threshold, so a bearing must not be served")
        return

    azimuth_error = abs(_angular_difference(ours_azimuth, ref_azimuth))
    assert azimuth_error <= AZIMUTH_TOLERANCE_DEG, (
        f"{scenario.key} at {place}: solar azimuth {ours_azimuth:.4f} vs "
        f"reference {ref_azimuth:.4f} — off by {azimuth_error:.4f} deg, "
        f"tolerance {AZIMUTH_TOLERANCE_DEG}")


@pytest.mark.parametrize("place,lat,lng", NSW_POINTS, ids=[p[0] for p in NSW_POINTS])
@pytest.mark.parametrize("scenario", SHADOW_SCENARIOS, ids=lambda s: s.key)
def test_shadow_bearing_is_opposite_the_sun(scenario, place, lat, lng):
    """The served `shadow_direction_deg` must be the reference sun azimuth turned
    180 deg. This is what a customer reads in the PDF Direction column."""
    bearing = scenario_shadow_bearing_deg(
        scenario.key, lat, lng, year=SCENARIO_YEAR)
    instant = scenario.instant_utc(SCENARIO_YEAR)
    ref_altitude, ref_azimuth = _pvlib_reference(instant, lat, lng)

    if ref_altitude > AZIMUTH_ILL_CONDITIONED_ALTITUDE_DEG or ref_altitude <= 0:
        assert bearing is None, (
            f"{scenario.key} at {place}: solar altitude {ref_altitude:.2f} deg "
            f"makes the bearing meaningless, but {bearing} was served. An "
            f"unusable direction must be absent, never a number")
        return

    assert bearing is not None, (
        f"{scenario.key} at {place}: no bearing served despite a usable sun "
        f"altitude of {ref_altitude:.2f} deg")
    expected = (ref_azimuth + 180.0) % 360.0
    error = abs(_angular_difference(bearing, expected))
    assert error <= AZIMUTH_TOLERANCE_DEG, (
        f"{scenario.key} at {place}: shadow bearing {bearing:.2f} vs expected "
        f"{expected:.2f} (reference sun azimuth {ref_azimuth:.2f} + 180) — off "
        f"by {error:.2f} deg")


def test_bearing_actually_varies_by_address():
    """The defect being fixed: one stored constant served for every address.
    A per-address computation must produce DIFFERENT bearings at different
    places. Pins that the fix is real and not a renamed constant."""
    for scenario in SHADOW_SCENARIOS:
        bearings = {
            place: scenario_shadow_bearing_deg(scenario.key, lat, lng, SCENARIO_YEAR)
            for place, lat, lng in NSW_POINTS
        }
        usable = [b for b in bearings.values() if b is not None]
        if len(usable) < 2:
            continue
        assert max(usable) - min(usable) > 1.0, (
            f"{scenario.key}: bearing is effectively constant across the whole "
            f"NSW envelope ({bearings}) — the per-address fix is not in effect")


def test_the_old_december_constant_would_now_fail():
    """The retired constants, asserted as wrong where they were wrong. Four
    reproduced suncalc at Sydney CBD to <=0.09 deg and were real; 183.0 for
    December matched no computable instant. Documents the finding so the number
    cannot quietly return."""
    retired = {
        "jun21_9am": 222.6, "jun21_12pm": 179.2, "jun21_3pm": 136.3,
        "sep21_12pm": 175.0, "dec21_12pm": 183.0,
    }
    lat, lng = -33.8688, 151.2093  # the CBD point they were calibrated at

    for key in ("jun21_9am", "jun21_12pm", "jun21_3pm", "sep21_12pm"):
        bearing = scenario_shadow_bearing_deg(key, lat, lng, SCENARIO_YEAR)
        assert bearing is not None
        assert abs(_angular_difference(retired[key], bearing)) < 0.5, (
            f"{key}: the retired constant {retired[key]} should still agree at "
            f"the CBD — got {bearing}")

    december = scenario_shadow_bearing_deg("dec21_12pm", lat, lng, SCENARIO_YEAR)
    assert december is not None
    assert abs(_angular_difference(retired["dec21_12pm"], december)) > 5.0, (
        f"the retired December constant 183.0 was out by more than 5 deg; it now "
        f"computes {december}. If this assertion fails, 183.0 has been restored")


# ---------------------------------------------------------------------------
# DEFECT 4 — the Southern Hemisphere caveat, open since April. Closed here.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("place,lat,lng", NSW_POINTS, ids=[p[0] for p in NSW_POINTS])
@pytest.mark.parametrize("scenario_key", ["jun21_12pm", "sep21_12pm", "dec21_12pm"])
def test_noon_sun_is_north_and_shadow_falls_south(scenario_key, place, lat, lng):
    """NSW lies entirely south of the Tropic of Capricorn (-23.44), so at local
    noon the sun is always north of the zenith and the shadow always falls
    southward. Asserted against the REFERENCE, across season and latitude."""
    instant = _SCENARIO_MAP[scenario_key].instant_utc(SCENARIO_YEAR)
    ref_altitude, ref_azimuth = _pvlib_reference(instant, lat, lng)

    assert ref_altitude > 0, f"sun below horizon at {place} for {scenario_key}"
    assert ref_azimuth < 90.0 or ref_azimuth > 270.0, (
        f"{scenario_key} at {place}: sun azimuth {ref_azimuth:.2f} is not "
        f"northward — the Southern Hemisphere assumption is violated")

    shadow_bearing = (ref_azimuth + 180.0) % 360.0
    assert 90.0 < shadow_bearing < 270.0, (
        f"{scenario_key} at {place}: shadow bearing {shadow_bearing:.2f} does "
        f"not fall southward")


def test_far_west_nsw_timezone_limitation_is_known():
    """Far-western NSW keeps `Australia/Broken_Hill` (UTC+9:30), 30 minutes behind
    Sydney, so a property there is modelled at 11:30 local while the report says
    12:00. This test does not assert the defect away — it PINS its size and the
    fact that we resolve every coordinate in the Sydney zone, so the limitation
    stays visible and quantified instead of being rediscovered later.

    Not fixed here because picking the right zone requires the real boundary,
    and approximating one from longitude would be inventing a real-world
    boundary. Exposure measured 2026-08-07: 0 of 538 stored reports fall west of
    longitude 143.0 (westernmost served property 144.95)."""
    far_west = ZoneInfo("Australia/Broken_Hill")
    for month, day in ((6, 21), (12, 21)):
        sydney_instant = datetime(SCENARIO_YEAR, month, day, 12, 0, tzinfo=NSW_TZ)
        far_west_instant = datetime(SCENARIO_YEAR, month, day, 12, 0, tzinfo=far_west)
        offset_minutes = (far_west_instant - sydney_instant).total_seconds() / 60
        assert offset_minutes == 30, (
            f"the far-west NSW zone is no longer 30 minutes behind Sydney on "
            f"{day}/{month} (now {offset_minutes:+.0f} min) — the documented size "
            f"of this limitation has changed and services/solar_position.py needs "
            f"updating")

    # And confirm we really do resolve everything in the Sydney zone, so this
    # test is describing the code as it stands rather than an intention.
    assert str(NSW_TZ) == "Australia/Sydney"


def test_nsw_envelope_stays_south_of_the_tropic():
    """The structural reason the assertion above holds. If the served envelope
    ever moved north of -23.44, the noon sun could sit south of the zenith and
    every 'shadows fall southward' statement would need revisiting."""
    from services.geometry_checks import NSW_LAT_MAX
    TROPIC_OF_CAPRICORN = -23.44
    assert NSW_LAT_MAX < TROPIC_OF_CAPRICORN, (
        f"the served envelope now reaches {NSW_LAT_MAX}, north of the Tropic of "
        f"Capricorn — the southward-shadow claim no longer holds by construction")


# ---------------------------------------------------------------------------
# DEFECT 6 — the physical ceiling on reported reach
# ---------------------------------------------------------------------------

def test_shadow_length_ceiling_matches_trigonometry():
    """L = h/tan(altitude), checked against hand-computed values."""
    assert max_shadow_length_m(9.0, 45.0) == pytest.approx(9.0, abs=1e-6)
    assert max_shadow_length_m(9.0, 18.97) == pytest.approx(26.19, abs=0.05)
    assert max_shadow_length_m(10.0, 90.0) == pytest.approx(0.0, abs=1e-9)
    assert max_shadow_length_m(9.0, 0.0) is None, "sun on the horizon has no finite ceiling"
    assert max_shadow_length_m(0.0, 45.0) is None, "a zero-height building casts nothing"


def test_stored_1779m_reach_is_impossible_at_its_own_sun_altitude():
    """The worst stored value, pinned. 42 Audley St Petersham served a 1,779.5 m
    reach from a 9 m building at the June 9am scenario, where the ceiling is
    ~26 m — a factor of 67. Reproduces the arithmetic that condemns it."""
    lat, lng = -33.8949, 151.1543  # Petersham
    instant = _SCENARIO_MAP["jun21_9am"].instant_utc(SCENARIO_YEAR)
    altitude, _ = sun_position(instant, lat, lng)
    ceiling = max_shadow_length_m(9.0, altitude)

    assert ceiling is not None and ceiling < 40.0, (
        f"ceiling for a 9 m building at {altitude:.2f} deg is {ceiling}")
    assert 1779.5 > ceiling * 1.25, (
        "the stored 1,779.5 m reach must exceed the plausibility threshold")


# ---------------------------------------------------------------------------
# Convention pins — the errors that produce a plausible number for the wrong place
# ---------------------------------------------------------------------------

def test_suncalc_argument_order_is_lng_then_lat():
    """suncalc takes (date, lng, lat). Swapping them returns a real position for
    the wrong hemisphere — a silent wrong answer, not a crash. Pins that
    `sun_position` passes them the right way round."""
    instant = datetime(2025, 6, 21, 2, 0, tzinfo=timezone.utc)
    lat, lng = -33.8688, 151.2093

    ours_altitude, _ = sun_position(instant, lat, lng)
    swapped = suncalc.get_position(instant, lat, lng)  # deliberately wrong order
    swapped_altitude = math.degrees(swapped["altitude"])

    ref_altitude, _ = _pvlib_reference(instant, lat, lng)
    assert abs(ours_altitude - ref_altitude) <= ALTITUDE_TOLERANCE_DEG
    assert abs(swapped_altitude - ref_altitude) > 10.0, (
        "swapping lat/lng no longer produces a detectably different answer — "
        "this test can no longer prove the argument order is right")


def test_naive_datetime_is_refused():
    """A naive datetime silently assumes the server's local zone — which on a
    developer's Windows box is AEST and in CI is UTC, so the same code would
    produce different shadows in different environments."""
    with pytest.raises(ValueError, match="timezone-aware"):
        sun_position(datetime(2025, 6, 21, 2, 0), -33.8688, 151.2093)


def test_local_wall_clock_conversion_is_dst_aware():
    """The primitive underneath every scenario instant."""
    assert local_wall_clock_to_utc(2025, 6, 21, 12, 0) == \
        datetime(2025, 6, 21, 2, 0, tzinfo=timezone.utc)   # AEST, UTC+10
    assert local_wall_clock_to_utc(2025, 12, 21, 12, 0) == \
        datetime(2025, 12, 21, 1, 0, tzinfo=timezone.utc)  # AEDT, UTC+11
    # The transition days themselves: DST starts 05 Oct 2025, ends 06 Apr 2025.
    assert local_wall_clock_to_utc(2025, 10, 6, 12, 0) == \
        datetime(2025, 10, 6, 1, 0, tzinfo=timezone.utc)   # day after the start
    assert local_wall_clock_to_utc(2025, 4, 7, 12, 0) == \
        datetime(2025, 4, 7, 2, 0, tzinfo=timezone.utc)    # day after the end


def test_time_local_label_is_derived_not_stored():
    """`time_local` is a property computed from local_hour/local_minute, so a
    label can no longer contradict the hour it names."""
    for scenario in SHADOW_SCENARIOS:
        assert scenario.time_local == f"{scenario.local_hour:02d}:{scenario.local_minute:02d}"
    assert not hasattr(_SCENARIO_MAP["dec21_12pm"], "hour_utc"), (
        "hour_utc has returned — the hand-computed offset that caused the DST "
        "defect must stay gone")
    assert not hasattr(_SCENARIO_MAP["dec21_12pm"], "direction_deg"), (
        "direction_deg has returned as a stored constant")
