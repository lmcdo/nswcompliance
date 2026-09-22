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
}

__all__ = [
    'ASHFIELD_CONFIG',
    'LEICHHARDT_CONFIG',
    'MARRICKVILLE_CONFIG',
    'CANTERBURY_BANKSTOWN_CONFIG',
    'WAVERLEY_CONFIG',
    'WOOLLAHRA_CONFIG',
    'CITY_OF_SYDNEY_CONFIG',
    'KU_RING_GAI_CONFIG',
    'COUNCIL_CONFIGS',
]
