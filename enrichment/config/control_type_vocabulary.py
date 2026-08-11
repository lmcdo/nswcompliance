"""Canonical vocabulary for ``dcp_setback_controls.control_type``.

Single source of truth for the control_type slugs that may be written to
``dcp_setback_controls``. Every writer (extractors, onboarding scripts) MUST
emit a canonical slug — normalise extractor/loader output through
:func:`normalize_control_type` before insert. The database enforces this with a
CHECK constraint (see ``migrations/enforce_control_type_vocabulary.sql``); a
non-canonical slug fails the insert loudly rather than drifting silently.

Why this exists: three copies of ``map_control_type`` in the extractors had
drifted (``site_coverage_max``/``height_max``/``floor_area_max`` vs the
DB/display convention ``max_site_coverage``/``max_height``), and one-off insert
scripts used ``landscaped_area_min`` where others used ``landscaping_min``. The
variant rows were invisible to the capacity engine and mis-grouped in the UI.

To add a NEW control type: add it to ``CANONICAL_CONTROL_TYPES`` (and to
``MAXIMUM_CONTROL_TYPES`` if it is a ceiling), then extend the CHECK constraint
via a migration. Keep in sync with the TypeScript maps in
``frontend-nextjs/app/api/dcp/structured-controls/route.ts``.
"""
from __future__ import annotations

# Canonical slug -> (display category, human label). Mirrors the TS route maps.
CANONICAL_CONTROL_TYPES: dict[str, tuple[str, str]] = {
    # Setbacks
    "front_setback": ("Setbacks", "Front setback"),
    # The corner-lot setback to the secondary street. Distinct from
    # front_setback because it is a different requirement with a different
    # value (DQ-40: 20 rows served a 2-4m secondary setback as the 4.5-6m
    # primary), and from side_setback because the boundary faces a road.
    # Added by migration 054, applied 2026-08-02.
    "secondary_street_setback": ("Setbacks", "Secondary street setback"),
    "side_setback": ("Setbacks", "Side setback"),
    "rear_setback": ("Setbacks", "Rear setback"),
    "separation_from_dwelling": ("Setbacks", "Separation from dwelling"),
    # Parking
    "car_parking": ("Parking", "Car parking"),
    "bicycle_parking": ("Parking", "Bicycle parking"),
    "driveway_width": ("Parking", "Minimum driveway width"),
    "driveway_gradient": ("Parking", "Maximum driveway gradient"),
    # Bulk / envelope
    "max_site_coverage": ("Site Coverage", "Maximum site coverage"),
    "max_height": ("Height", "Maximum height"),
    "max_floor_area": ("Floor Area", "Maximum floor area"),
    # Landscaping & canopy
    "landscaping_min": ("Landscaping & Canopy", "Minimum landscaped area"),
    "front_setback_landscaping": ("Landscaping & Canopy", "Front setback landscaping"),
    "deep_soil_min": ("Landscaping & Canopy", "Minimum deep soil zone"),
    "tree_canopy_min": ("Landscaping & Canopy", "Tree canopy coverage"),
    # Open space
    "communal_open_space_min": ("Open Space", "Communal open space"),
    "private_open_space": ("Open Space", "Private open space"),
    # Amenity
    "solar_access_hours": ("Solar & Amenity", "Solar access (hours)"),
    "privacy_separation": ("Privacy", "Privacy separation"),
    "fencing_height_max": ("Fencing", "Maximum fence height"),
    "dwelling_size_min": ("Dwelling Size", "Minimum dwelling size"),
}

# Ceilings — rendered "<=" (value stored in value_min). Everything else is a floor.
MAXIMUM_CONTROL_TYPES: frozenset[str] = frozenset({
    "max_site_coverage",
    "max_height",
    "max_floor_area",
    "fencing_height_max",
    "driveway_gradient",
})

# Known variant slugs -> canonical. These are the drifts we have observed and
# eliminated; the normaliser auto-corrects them so a re-run cannot reintroduce them.
CONTROL_TYPE_ALIASES: dict[str, str] = {
    "landscaped_area_min": "landscaping_min",
    "communal_open_space": "communal_open_space_min",
    "height_max": "max_height",
    "height_storeys_max": "max_height",
    "site_coverage_max": "max_site_coverage",
    "floor_area_max": "max_floor_area",
}

CANONICAL_SET: frozenset[str] = frozenset(CANONICAL_CONTROL_TYPES)


class UnknownControlTypeError(ValueError):
    """Raised when a control_type is neither canonical nor a known alias."""


def normalize_control_type(control_type: str | None, *, strict: bool = True) -> str | None:
    """Return the canonical control_type for ``control_type``.

    - ``None`` -> ``None`` (nothing to normalise; caller skips the row).
    - already canonical -> unchanged.
    - a known alias -> its canonical form.
    - anything else -> raise :class:`UnknownControlTypeError` when ``strict``,
      else return ``None`` so the caller drops the row rather than persisting a
      slug the DB constraint would reject.
    """
    if control_type is None:
        return None
    ct = control_type.strip()
    if ct in CANONICAL_SET:
        return ct
    if ct in CONTROL_TYPE_ALIASES:
        return CONTROL_TYPE_ALIASES[ct]
    if strict:
        raise UnknownControlTypeError(
            f"'{control_type}' is not a canonical control_type. Add it to "
            f"CANONICAL_CONTROL_TYPES (+ MAXIMUM_CONTROL_TYPES if a ceiling) and "
            f"extend the CHECK constraint, or map it in CONTROL_TYPE_ALIASES."
        )
    return None


def is_maximum(control_type: str) -> bool:
    """True if the control's single value is a ceiling (rendered '<=')."""
    return normalize_control_type(control_type) in MAXIMUM_CONTROL_TYPES
