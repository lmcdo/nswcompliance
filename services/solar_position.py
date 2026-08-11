# prior-art-checked: no module computes solar position anywhere in the repo.
# Sweep 2026-08-07 — Python (`services/ scripts/ src/ enrichment/`): the only
# sun geometry is `shadow_model.SHADOW_SCENARIOS`, five STORED constants;
# `solar_yield.py` is a Google Solar API pass-through and computes none;
# `terrain_analysis.py` matches "azimuth" for SLOPE aspect, not the sun.
# Frontend (`app/** components/ hooks/`): `bearingToCompass` renders a bearing,
# nothing derives one. So this is the single shared home, not a parallel one.
"""Solar position for the shadow product — and the ONE place local time becomes UTC.

WHY THIS MODULE EXISTS
----------------------
`shadow_model.SHADOW_SCENARIOS` stored a hand-computed ``hour_utc`` beside a
display label. Nothing tied the two together, so they drifted: the December
scenario carried ``hour_utc=2``, which is 13:00 in Sydney (AEDT, UTC+11) while
the label said "12:00". Four months and 538 stored reports were served with the
summer scenario modelled an hour late (measured 2026-08-07).

The fix is structural rather than arithmetical. A scenario now declares the
WALL-CLOCK time a customer reads, and the UTC instant is DERIVED from it through
the IANA database. There is no second number to keep in step, so the same defect
cannot recur by editing one of a pair.

METHOD
------
Sun position comes from ``suncalc`` — deliberately, because that is the exact
function ``pybdshadow`` calls internally to cast the shadow polygon
(``pybdshadow/pybdshadow.py:34,129``). Deriving the reported bearing from any
other library would let the Direction column and the drawn polygon disagree.

``suncalc`` is therefore not a new dependency: it has always been installed as a
``pybdshadow`` requirement. It is now declared explicitly (requirements.txt,
services/requirements.txt) because this module imports it directly, and a
transitive pin is not a contract.

**pvlib is NOT used here and must never be.** It is a TEST-ONLY dependency
(requirements-test.txt), used solely as the independent reference in
``tests/test_shadow_calibration.py``. It was named as our method on customer
surfaces for months while never being imported anywhere in the repo; PR #878 and
migration 064 removed those claims. Nothing in this module may reintroduce them.

CONVENTIONS
-----------
``suncalc`` reports azimuth in radians measured from SOUTH increasing toward
WEST. Converted to a compass bearing clockwise from north:

    shadow bearing (deg) = degrees(suncalc azimuth) mod 360
    sun azimuth  (deg)   = shadow bearing + 180 mod 360

The shadow points away from the sun, so ``degrees(suncalc.azimuth)`` IS the
shadow bearing with no further rotation. Verified against pvlib's NREL SPA at
eight points spanning the served NSW envelope: worst disagreement 0.18 deg in
altitude, 0.30 deg in bearing (2026-08-07).
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# The civil timezone every scenario's wall-clock label is resolved in.
#
# KNOWN LIMITATION, stated rather than assumed. IANA defines a SECOND zone for
# far-western NSW — `Australia/Broken_Hill`, UTC+9:30/+10:30 — which runs 30
# minutes behind Sydney. For a property in that region we therefore model
# 11:30 local while the report says 12:00: the same class of defect as the
# December daylight-saving bug this module was written to remove, one sixtieth
# the size.
#
# It is not fixed here, deliberately. Choosing the right zone needs the actual
# zone boundary, and drawing an approximate one from longitude would be
# inventing a real-world boundary — the thing the data-integrity rule forbids
# outright. Resolving it properly needs either a tz-boundary dataset or the
# LGA lookup this service already performs, and that is a scoped change with a
# ruling attached, not a silent guess.
#
# MEASURED EXPOSURE, 2026-08-07, all 538 stored shadow reports: ZERO fall west
# of longitude 143.0; the westernmost served property is at 144.95. So the
# limitation is real, currently unexercised, and pinned by
# tests/test_shadow_calibration.py::test_far_west_nsw_timezone_limitation_is_known
# so it cannot be forgotten if coverage moves west.
NSW_TZ = ZoneInfo("Australia/Sydney")

# Above this solar altitude the azimuth is ill-conditioned: near the zenith a
# fraction of a degree of altitude swings the bearing by many degrees, and the
# shadow it describes is a few centimetres long. Reported as unavailable rather
# than as a precise-looking number that is meaningless.
#   9 m building at 85 deg  ->  0.79 m of shadow.
AZIMUTH_ILL_CONDITIONED_ALTITUDE_DEG = 85.0

# Below this the sun is at or under the horizon: there is no shadow to bear.
MIN_USABLE_ALTITUDE_DEG = 0.0


def local_wall_clock_to_utc(year: int, month: int, day: int,
                            hour: int, minute: int = 0,
                            tz: ZoneInfo = NSW_TZ) -> datetime:
    """Convert a LOCAL wall-clock time to the UTC instant it names.

    This is the only place a shadow scenario's time becomes UTC. Daylight
    saving is resolved by the IANA database, not by an offset typed into a
    table, which is what made the December scenario an hour late.

    Args:
        year, month, day: calendar date in ``tz``.
        hour, minute: wall-clock time as a customer reads it (24-hour).
        tz: the civil timezone. Defaults to NSW.

    Returns:
        A timezone-aware ``datetime`` in UTC.
    """
    return datetime(year, month, day, hour, minute, tzinfo=tz).astimezone(timezone.utc)


def sun_position(dt_utc: datetime, lat: float, lng: float) -> tuple[float, float]:
    """Solar altitude and compass azimuth, in degrees, at an instant and place.

    Args:
        dt_utc: timezone-aware UTC instant.
        lat, lng: WGS84 degrees.

    Returns:
        ``(altitude_deg, azimuth_deg)`` — azimuth is a compass bearing
        clockwise from north (N=0, E=90, S=180, W=270).

    Raises:
        RuntimeError: if ``suncalc`` is not installed. Never returns a
            fabricated position; callers convert this into typed absence.
    """
    try:
        from suncalc import get_position
    except ImportError as e:  # pragma: no cover - dependency contract
        raise RuntimeError(
            "suncalc not installed — solar position cannot be computed") from e

    if dt_utc.tzinfo is None:
        raise ValueError("dt_utc must be timezone-aware; naive datetimes silently "
                         "assume the server's local zone")

    # suncalc takes (date, lng, lat) — longitude FIRST. Passing them in lat/lng
    # order returns a plausible-looking position for the wrong hemisphere.
    pos = get_position(dt_utc, lng, lat)

    # .get() with an explicit check, not pos["altitude"]: a suncalc release that
    # renamed either key would otherwise raise a bare KeyError from inside a
    # maths expression. Naming the failure lets the callers' typed-absence
    # handling do its job — the bearing goes absent and says why, rather than
    # the request 500-ing or, worse, math.degrees(None) surfacing as a TypeError
    # that reads like a coding bug rather than a dependency change.
    altitude_rad = pos.get("altitude")
    azimuth_rad = pos.get("azimuth")
    if altitude_rad is None or azimuth_rad is None:
        raise RuntimeError(
            f"suncalc returned no usable position for {dt_utc.isoformat()} at "
            f"({lat}, {lng}) — keys present: {sorted(pos)}")

    altitude_deg = math.degrees(altitude_rad)
    # suncalc azimuth: from SOUTH toward WEST. +180 puts it on a compass rose.
    azimuth_deg = (math.degrees(azimuth_rad) + 180.0) % 360.0
    return altitude_deg, azimuth_deg


def shadow_bearing_deg(dt_utc: datetime, lat: float, lng: float) -> Optional[float]:
    """Compass bearing the shadow FALLS TOWARD, or None when it is not meaningful.

    Returns None — never a number — when the sun is at or below the horizon, or
    so near the zenith that the bearing is ill-conditioned. A direction that
    cannot be stated is reported as absent, matching the typed-absence handling
    the rest of this pipeline uses for a computation that did not produce an
    answer.

    Args:
        dt_utc: timezone-aware UTC instant.
        lat, lng: WGS84 degrees.

    Returns:
        Bearing in degrees clockwise from north, or ``None``.
    """
    try:
        altitude_deg, azimuth_deg = sun_position(dt_utc, lat, lng)
    except Exception as e:
        logger.warning("shadow_bearing_deg: solar position unavailable: %s", e)
        return None

    if altitude_deg <= MIN_USABLE_ALTITUDE_DEG:
        logger.info("shadow_bearing_deg: sun below horizon (alt=%.2f deg) — no bearing",
                    altitude_deg)
        return None
    if altitude_deg >= AZIMUTH_ILL_CONDITIONED_ALTITUDE_DEG:
        logger.info("shadow_bearing_deg: sun near zenith (alt=%.2f deg) — bearing "
                    "ill-conditioned, reporting absent", altitude_deg)
        return None

    # The shadow points away from the sun.
    return round((azimuth_deg + 180.0) % 360.0, 1)


def max_shadow_length_m(height_m: float, altitude_deg: float) -> Optional[float]:
    """Longest shadow a vertical object of ``height_m`` can cast at this sun altitude.

    ``L = h / tan(altitude)``. Used as a PHYSICAL CEILING on reported reach:
    10 of 538 stored reports served a reach that exceeds it (one at 1,779 m from
    a 9 m building), which is a lot-geometry defect surfacing as an impossible
    measurement. Returns None when the sun is too low for a finite answer.
    """
    if altitude_deg <= MIN_USABLE_ALTITUDE_DEG or height_m <= 0:
        return None
    return height_m / math.tan(math.radians(altitude_deg))
