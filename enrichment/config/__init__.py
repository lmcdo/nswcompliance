"""
DCP Configuration Files

Each council's DCP has a unique structure that determines how provisions
apply to different zones, development types, and site conditions.

These configs map document_id patterns to applicability rules, ensuring
provisions are correctly filtered for each property.

COUNCIL_CONFIGS: Registry for config-driven tagging (Waverley + new LGAs).
Keyed by council name substring (matched against document_id lowercase).
Inner West councils (marrickville, leichhardt, ashfield) are NOT in this
registry — they use dedicated _tag_x() methods in LayerTopicTagger because
their document_ids encode structural info directly (not provision_text headings).
"""

from .ashfield_config import ASHFIELD_CONFIG
from .leichhardt_config import LEICHHARDT_CONFIG
from .marrickville_config import MARRICKVILLE_CONFIG
from .waverley_config import WAVERLEY_CONFIG
from .woollahra_config import WOOLLAHRA_CONFIG
from .city_of_sydney_config import CITY_OF_SYDNEY_CONFIG
from .ku_ring_gai_config import KU_RING_GAI_CONFIG
from .canterbury_bankstown_config import CANTERBURY_BANKSTOWN_CONFIG
from .campbelltown_config import CAMPBELLTOWN_CONFIG
from .blacktown_config import BLACKTOWN_CONFIG
from .penrith_config import PENRITH_CONFIG
from .hornsby_config import HORNSBY_CONFIG
from .georges_river_config import GEORGES_RIVER_CONFIG
from .northern_beaches_config import NORTHERN_BEACHES_CONFIG
from .parramatta_config import PARRAMATTA_CONFIG
from .wollongong_config import WOLLONGONG_CONFIG

# Registry for config-driven LayerTopicTagger dispatch.
# Keys are substrings matched against document_id.lower().
# Order does not matter — looked up by exact key match.
COUNCIL_CONFIGS: dict[str, dict] = {
    "waverley":      WAVERLEY_CONFIG,
    "woollahra":     WOOLLAHRA_CONFIG,
    "city_of_sydney": CITY_OF_SYDNEY_CONFIG,
    "sydney_dcp":     CITY_OF_SYDNEY_CONFIG,   # alias: document_id is "Sydney_DCP_2012__..."
    "ku_ring_gai":   KU_RING_GAI_CONFIG,
    "ku-ring-gai":   KU_RING_GAI_CONFIG,   # alias: document_id is "Ku-ring-gai_DCP_2024__..."
    # document_id is "Canterbury-Bankstown_DCP_2023__chapter_7_6_..." -- HYPHENATED,
    # so the underscored spelling is registered too rather than assumed absent.
    "canterbury-bankstown": CANTERBURY_BANKSTOWN_CONFIG,
    "canterbury_bankstown": CANTERBURY_BANKSTOWN_CONFIG,
    # document_id is "Campbelltown_(Sustainable_City)_DCP_2015__campbelltown_dcp_part3_low_medium".
    # No hyphenated spelling exists for this council, so only one key is registered.
    "campbelltown": CAMPBELLTOWN_CONFIG,
    # Added 2026-09-23 (DQ-105). document_ids are "Blacktown_DCP_2015__...",
    # "Penrith_DCP_2014__...", "Hornsby_DCP_2024__...",
    # "Georges_River_DCP_2021__..." -- all underscored, no hyphenated spelling
    # exists for any of the four, checked against the served document_ids.
    "blacktown": BLACKTOWN_CONFIG,
    "penrith": PENRITH_CONFIG,
    "hornsby": HORNSBY_CONFIG,
    "georges_river": GEORGES_RIVER_CONFIG,
    # Whole-DCP document: keys on the PART code in each rule's own section
    # reference via the `parts` path, not on document_id. See its docstring.
    "warringah": NORTHERN_BEACHES_CONFIG,
    "northern_beaches": NORTHERN_BEACHES_CONFIG,
    # Also a whole-DCP document, also the `parts` path, but keyed on NUMBERED
    # parts (1-17) rather than letters. See its docstring for why nothing in
    # it narrows: bare-number misreads resolve to a Part directly.
    "parramatta": PARRAMATTA_CONFIG,
    "wollongong": WOLLONGONG_CONFIG,
}

__all__ = [
    'ASHFIELD_CONFIG',
    'LEICHHARDT_CONFIG',
    'MARRICKVILLE_CONFIG',
    'CANTERBURY_BANKSTOWN_CONFIG',
    'CAMPBELLTOWN_CONFIG',
    'PARRAMATTA_CONFIG',
    'WOLLONGONG_CONFIG',
    'BLACKTOWN_CONFIG',
    'PENRITH_CONFIG',
    'HORNSBY_CONFIG',
    'GEORGES_RIVER_CONFIG',
    'NORTHERN_BEACHES_CONFIG',
    'WAVERLEY_CONFIG',
    'WOOLLAHRA_CONFIG',
    'CITY_OF_SYDNEY_CONFIG',
    'KU_RING_GAI_CONFIG',
    'COUNCIL_CONFIGS',
]
