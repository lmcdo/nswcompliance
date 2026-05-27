"""
Shared LGA lookup for satellite pipelines.

All satellite products call lookup_lga(lat, lng, conn) to resolve:
  - lga_name: display name (e.g. "Canterbury-Bankstown")
  - lga_slug: DB key for dcp_setback_controls (e.g. "canterbury_bankstown")

Source: spatial_overlays WHERE layer_type='height' — covers 75 LGAs.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# lga_name (from spatial_overlays) → lga_slug (for dcp_setback_controls)
# Only LGAs with confirmed DCP setback rows are listed here.
# All others get a slug derived from normalising the lga_name.
# ---------------------------------------------------------------------------

_LGA_NAME_TO_SLUG: dict[str, str] = {
    "inner west":           "inner_west",
    "canterbury-bankstown": "canterbury_bankstown",
    "blacktown":            "blacktown",
    "campbelltown":         "campbelltown",
    "liverpool":            "liverpool",
    "hornsby":              "hornsby",
    "northern beaches":     "northern_beaches",
    "penrith":              "penrith",
    "waverley":             "waverley",
    "woollahra":            "woollahra",
    "ku-ring-gai":          "ku_ring_gai",
    # Not yet complete in dcp_setback_controls:
    # "parramatta":         "parramatta",
    # "cumberland":         "cumberland",
}

# Inner West post-2016 amalgamation — suburb → former council slug.
# DCP setback controls are stored per former council area.
_IW_SUBURB_TO_FORMER: dict[str, str] = {
    # Marrickville — includes boundary suburbs because this mapping is ONLY
    # consulted after PostGIS has confirmed the point is within Inner West LGA.
    # Safe to map here: PostGIS already excluded City of Sydney addresses.
    "marrickville": "marrickville", "sydenham": "marrickville", "tempe": "marrickville",
    "dulwich hill": "marrickville", "st peters": "marrickville", "newtown": "marrickville",
    "erskineville": "marrickville", "enmore": "marrickville",
    "stanmore": "marrickville", "petersham": "marrickville", "lewisham": "marrickville",
    "camperdown": "marrickville",
    # NOTE: glebe and alexandria are NOT included — they are entirely in City of Sydney
    # Leichhardt
    "leichhardt": "leichhardt", "annandale": "leichhardt", "balmain": "leichhardt",
    "rozelle": "leichhardt", "lilyfield": "leichhardt", "forest lodge": "leichhardt",
    "birchgrove": "leichhardt", "balmain east": "leichhardt",
    # Ashfield
    "ashfield": "ashfield", "summer hill": "ashfield", "haberfield": "ashfield",
    "croydon": "ashfield", "croydon park": "ashfield",
}


def _normalise_slug(name: str) -> str:
    """Normalise an LGA name to a slug: lowercase, spaces/hyphens → underscores."""
    return re.sub(r"[\s\-]+", "_", name.strip().lower())


def lookup_lga(
    lat: float,
    lng: float,
    conn,
    address: Optional[str] = None,
) -> dict:
    """
    Resolve LGA from coordinates via spatial_overlays height layer.

    Returns:
      {
        "lga_name": "Canterbury-Bankstown",  # display name
        "lga_slug": "canterbury_bankstown",  # DB key for dcp_setback_controls
        "has_dcp_setbacks": True,            # whether slug is in _LGA_NAME_TO_SLUG
      }

    Returns {"lga_name": None, "lga_slug": None, "has_dcp_setbacks": False}
    if lookup fails or no data.
    """
    empty = {"lga_name": None, "lga_slug": None, "has_dcp_setbacks": False}

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT lga_name FROM spatial_overlays
                WHERE layer_type = 'height'
                  AND ST_Contains(
                        geom,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                      )
                LIMIT 1
                """,
                (lng, lat),
            )
            row = cur.fetchone()
    except Exception as e:
        logger.warning(f"LGA lookup failed: {e}")
        return empty

    if not row or not row[0]:
        return empty

    lga_name = row[0].strip()
    lga_lower = lga_name.lower()

    # Check explicit mapping first
    slug = _LGA_NAME_TO_SLUG.get(lga_lower)

    # Inner West disambiguation
    if lga_lower == "inner west" and address:
        suburb = _extract_suburb(address)
        if suburb and suburb in _IW_SUBURB_TO_FORMER:
            slug = _IW_SUBURB_TO_FORMER[suburb]

    has_dcp = slug is not None

    # Fallback: derive slug from name
    if slug is None:
        slug = _normalise_slug(lga_name)

    return {
        "lga_name": lga_name,
        "lga_slug": slug,
        "has_dcp_setbacks": has_dcp,
    }


def _extract_suburb(address: str) -> Optional[str]:
    """
    Extract suburb from an address string.
    Expects format: "123 Street Name, SUBURB NSW 2000" or similar.
    """
    if not address:
        return None
    # Try to find suburb between the last comma and "NSW"
    m = re.search(r",\s*([A-Za-z\s]+?)\s+NSW\b", address, re.IGNORECASE)
    if m:
        return m.group(1).strip().lower()
    # Fallback: second-to-last segment before postcode
    parts = [p.strip() for p in address.replace(",", " ").split() if p.strip()]
    for i, p in enumerate(parts):
        if p.upper() == "NSW" and i > 0:
            # Walk back to find the suburb (skip street number/name)
            return parts[i - 1].lower()
    return None
