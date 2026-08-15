#!/usr/bin/env python3
"""
AI-Assisted Topic Taggers for Leichhardt DCP

Tier 2: Economical (Claude Haiku batch)
- Batch 50 provisions per API call
- ~$0.30 total for 1,566 provisions
- Accuracy: ~92-95%

Tier 3: Optimal (Claude Sonnet individual)
- Individual classification with full context
- ~$27 total for 1,566 provisions
- Accuracy: ~97-99%

Tier 4: Best Possible (Claude Opus with examples)
- Few-shot learning with verified examples
- ~$138 total for 1,566 provisions
- Accuracy: ~99%+

Usage:
    python scripts/optimal_topic_tagger_ai.py --tier 2 --dry-run
    python scripts/optimal_topic_tagger_ai.py --tier 3 --sample 20
"""

import os
import json
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

# Load env
env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)


@dataclass
class ClassificationResult:
    provision_id: int
    topic: str
    confidence: float
    reasoning: str
    alternatives: List[str] = None


# Valid topics for Leichhardt DCP
VALID_TOPICS = [
    'access', 'advertising', 'bicycle_parking', 'building_design',
    'building_form', 'contamination', 'density', 'energy',
    'environmental', 'fencing', 'flooding', 'general', 'height',
    'heritage', 'landscaping', 'mixed_use', 'open_space', 'parking',
    'privacy', 'residential', 'roofing', 'safety', 'setbacks',
    'signage', 'site_analysis', 'site_specific', 'solar',
    'stormwater', 'sustainability', 'trees', 'vehicle_access',
    'views', 'waste_management', 'water',
]


# ============================================================================
# TIER 2: ECONOMICAL - Claude Haiku Batch Processing
# ============================================================================

TIER2_SYSTEM_PROMPT = """You are a planning document classifier for the Leichhardt Development Control Plan (DCP).

Your task is to assign the most appropriate topic to each provision based on its content.

Valid topics:
- access: Pedestrian access, disability access, driveways, entries
- building_design: Architectural design, facades, materials, articulation
- building_form: Built form, bulk and scale, streetscape character, massing
- contamination: Site contamination, remediation, hazardous materials
- density: FSR, dwelling density, lot sizes, subdivision
- energy: Energy efficiency, solar panels, thermal performance
- fencing: Front fences, boundary fences, fence heights
- flooding: Flood prone land, flood planning levels
- general: Administrative provisions, definitions, objectives without specific topic
- height: Building height, storeys, height limits
- heritage: Heritage items, conservation areas, contributory buildings
- landscaping: Landscape plans, planting, deep soil, gardens
- mixed_use: Commercial/retail in mixed developments
- open_space: Private open space, communal open space, courtyards
- parking: Car parking, parking rates, garages
- privacy: Visual privacy, overlooking, screening
- residential: Dwelling requirements, bedroom sizes, amenity
- roofing: Roof design, pitch, materials
- safety: CPTED, crime prevention, surveillance
- setbacks: Front/side/rear setbacks, building lines
- signage: Business signage, advertising signs
- site_analysis: Site analysis requirements, context analysis
- site_specific: Site-specific provisions, masterplan areas
- solar: Solar access, overshadowing, sunlight
- stormwater: Stormwater management, drainage, OSD, WSUD
- sustainability: Environmental sustainability, green building
- trees: Tree preservation, significant trees, canopy
- vehicle_access: Driveways, crossovers, vehicle manoeuvring
- views: View sharing, view corridors, outlook
- waste_management: Waste storage, bin areas, recycling
- water: Water management, rainwater, water efficiency

Respond with a JSON array of objects with: id, topic, confidence (0-1)"""


TIER2_USER_TEMPLATE = """Classify these provisions. Return JSON array only.

{provisions_json}"""


async def tier2_classify_batch(
    provisions: List[Dict],
    client,  # Anthropic client
    batch_size: int = 50
) -> List[ClassificationResult]:
    """
    Tier 2: Batch classification with Claude Haiku

    Cost estimate: ~$0.30 for 1,566 provisions
    - Input: ~25k tokens/batch × 32 batches = 800k tokens × $0.25/MTok = $0.20
    - Output: ~2k tokens/batch × 32 batches = 64k tokens × $1.25/MTok = $0.08
    """
    results = []

    # Process in batches
    for i in range(0, len(provisions), batch_size):
        batch = provisions[i:i + batch_size]

        # Format provisions for API
        provisions_for_api = [
            {"id": p['id'], "text": (p['provision_text'] or '')[:500]}
            for p in batch
        ]

        response = await client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=4096,
            system=TIER2_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": TIER2_USER_TEMPLATE.format(
                    provisions_json=json.dumps(provisions_for_api, indent=2)
                )
            }]
        )

        # Parse response
        try:
            classifications = json.loads(response.content[0].text)
            for c in classifications:
                results.append(ClassificationResult(
                    provision_id=c['id'],
                    topic=c['topic'],
                    confidence=c.get('confidence', 0.8),
                    reasoning='batch_classification'
                ))
        except json.JSONDecodeError:
            print(f"Failed to parse batch {i//batch_size}")

        # Rate limiting
        await asyncio.sleep(0.5)

    return results


# ============================================================================
# TIER 3: OPTIMAL - Claude Sonnet Individual Classification
# ============================================================================

TIER3_SYSTEM_PROMPT = """You are an expert classifier for the Leichhardt Development Control Plan (DCP).

Analyze each provision carefully and assign the most appropriate topic. Consider:
1. The primary subject matter of the provision
2. Key terminology and phrases
3. The regulatory intent
4. What aspect of development it controls

Valid topics: {topics}

Respond with JSON: {{"topic": "...", "confidence": 0.0-1.0, "reasoning": "...", "alternatives": ["...", "..."]}}"""


TIER3_USER_TEMPLATE = """Classify this DCP provision:

Part: {part}
Page: {page}

Text:
{text}

What topic best describes this provision?"""


async def tier3_classify_individual(
    provision: Dict,
    client,  # Anthropic client
) -> ClassificationResult:
    """
    Tier 3: Individual classification with Claude Sonnet

    Cost estimate: ~$27 for 1,566 provisions
    - Input: ~1k tokens × 1,566 = 1.5M tokens × $3/MTok = $4.50
    - Output: ~200 tokens × 1,566 = 313k tokens × $15/MTok = $4.70
    - With retries/overhead: ~$27 total
    """
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=TIER3_SYSTEM_PROMPT.format(topics=", ".join(VALID_TOPICS)),
        messages=[{
            "role": "user",
            "content": TIER3_USER_TEMPLATE.format(
                part=provision.get('v2_dcp_part', 'Unknown'),
                page=provision.get('pdf_page', 'Unknown'),
                text=(provision.get('provision_text') or '')[:1000]
            )
        }]
    )

    try:
        result = json.loads(response.content[0].text)
        return ClassificationResult(
            provision_id=provision['id'],
            topic=result['topic'],
            confidence=result['confidence'],
            reasoning=result['reasoning'],
            alternatives=result.get('alternatives', [])
        )
    except (json.JSONDecodeError, KeyError) as e:
        return ClassificationResult(
            provision_id=provision['id'],
            topic='general',
            confidence=0.5,
            reasoning=f'parse_error: {e}'
        )


# ============================================================================
# TIER 4: BEST POSSIBLE - Claude Opus with Few-Shot Examples
# ============================================================================

TIER4_EXAMPLES = """
Example 1:
Text: "C3 A minimum of 1 car space must be provided for each dwelling."
Classification: {"topic": "parking", "confidence": 0.99, "reasoning": "C3 marker maps to parking, content confirms car space requirements"}

Example 2:
Text: "Development within a heritage conservation area must be compatible with the character of the area."
Classification: {"topic": "heritage", "confidence": 0.98, "reasoning": "Explicitly about heritage conservation areas and character compatibility"}

Example 3:
Text: "The maximum building height must not exceed that shown on the Height of Buildings Map."
Classification: {"topic": "height", "confidence": 0.99, "reasoning": "Directly specifies maximum building height control"}

Example 4:
Text: "O1 To ensure development is designed to minimize overlooking of private open spaces."
Classification: {"topic": "privacy", "confidence": 0.95, "reasoning": "Objective about minimizing overlooking, which is a privacy concern"}

Example 5:
Text: "This section applies to sites identified in Figure G1."
Classification: {"topic": "site_specific", "confidence": 0.90, "reasoning": "Administrative provision introducing site-specific controls, no specific topic content"}

Example 6:
Text: "Trees with a trunk diameter greater than 200mm must not be removed without Council approval."
Classification: {"topic": "trees", "confidence": 0.98, "reasoning": "Specific control about tree removal based on trunk diameter"}

Example 7:
Text: "The applicant must submit a Site Audit Statement prepared by an accredited site auditor."
Classification: {"topic": "contamination", "confidence": 0.95, "reasoning": "Site Audit Statements are specifically for contaminated land assessment"}
"""

TIER4_SYSTEM_PROMPT = f"""You are an expert classifier for the Leichhardt Development Control Plan (DCP).

You have deep expertise in NSW planning law and development controls. Analyze each provision with precision.

{TIER4_EXAMPLES}

Valid topics: {{topics}}

Consider:
1. C markers (C1-C55) have specific topic mappings - use them when present
2. Look for specific planning terminology that indicates the topic
3. Consider the regulatory purpose of the provision
4. When ambiguous, prefer the more specific topic over 'general'
5. 'site_specific' is for provisions about particular sites/masterplan areas

Respond with JSON only: {{"topic": "...", "confidence": 0.0-1.0, "reasoning": "...", "alternatives": ["..."]}}"""


async def tier4_classify_opus(
    provision: Dict,
    client,  # Anthropic client
) -> ClassificationResult:
    """
    Tier 4: Best possible with Claude Opus + few-shot examples

    Cost estimate: ~$138 for 1,566 provisions
    - Input: ~2k tokens × 1,566 = 3.1M tokens × $15/MTok = $46.50
    - Output: ~200 tokens × 1,566 = 313k tokens × $75/MTok = $23.50
    - With examples overhead: ~$138 total
    """
    response = await client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=500,
        system=TIER4_SYSTEM_PROMPT.format(topics=", ".join(VALID_TOPICS)),
        messages=[{
            "role": "user",
            "content": TIER3_USER_TEMPLATE.format(
                part=provision.get('v2_dcp_part', 'Unknown'),
                page=provision.get('pdf_page', 'Unknown'),
                text=(provision.get('provision_text') or '')[:1500]
            )
        }]
    )

    try:
        result = json.loads(response.content[0].text)
        return ClassificationResult(
            provision_id=provision['id'],
            topic=result['topic'],
            confidence=result['confidence'],
            reasoning=result['reasoning'],
            alternatives=result.get('alternatives', [])
        )
    except (json.JSONDecodeError, KeyError) as e:
        return ClassificationResult(
            provision_id=provision['id'],
            topic='general',
            confidence=0.5,
            reasoning=f'parse_error: {e}'
        )


# ============================================================================
# HYBRID APPROACH (RECOMMENDED)
# ============================================================================

async def hybrid_classify(
    provisions: List[Dict],
    client,
    programmatic_tagger,  # From optimal_topic_tagger_programmatic.py
) -> List[ClassificationResult]:
    """
    Hybrid approach: Programmatic first, AI for uncertain cases

    Strategy:
    1. Run programmatic tagger on all provisions
    2. For high-confidence results (>0.85), keep programmatic result
    3. For medium-confidence (0.6-0.85), use Haiku batch
    4. For low-confidence (<0.6), use Sonnet individual

    Estimated cost for 1,566 provisions:
    - ~80% high confidence: $0 (programmatic)
    - ~15% medium confidence: ~200 provisions × Haiku = ~$0.05
    - ~5% low confidence: ~80 provisions × Sonnet = ~$2
    Total: ~$2-3
    """
    results = []
    medium_confidence = []
    low_confidence = []

    # Step 1: Programmatic classification
    for p in provisions:
        prog_result = programmatic_tagger.extract_topic(
            p['provision_text'],
            p.get('v2_dcp_part'),
            p.get('pdf_page')
        )

        if prog_result.confidence >= 0.85:
            results.append(ClassificationResult(
                provision_id=p['id'],
                topic=prog_result.topic,
                confidence=prog_result.confidence,
                reasoning=f'programmatic:{prog_result.method}'
            ))
        elif prog_result.confidence >= 0.6:
            medium_confidence.append(p)
        else:
            low_confidence.append(p)

    print(f"Programmatic: {len(results)} high confidence")
    print(f"Need Haiku batch: {len(medium_confidence)}")
    print(f"Need Sonnet individual: {len(low_confidence)}")

    # Step 2: Haiku batch for medium confidence
    if medium_confidence:
        haiku_results = await tier2_classify_batch(medium_confidence, client)
        results.extend(haiku_results)

    # Step 3: Sonnet for low confidence
    for p in low_confidence:
        sonnet_result = await tier3_classify_individual(p, client)
        results.append(sonnet_result)
        await asyncio.sleep(0.2)  # Rate limiting

    return results


# ============================================================================
# MAIN
# ============================================================================

def get_provisions(limit: int = None) -> List[Dict]:
    """Get provisions from database"""
    db_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)

    with conn.cursor() as cur:
        query = """
            SELECT id, provision_text, v2_dcp_part, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%%Leichhardt%%'
              AND is_current = TRUE
            ORDER BY id
        """
        if limit:
            query += f" LIMIT {limit}"
        cur.execute(query)
        return cur.fetchall()


def print_cost_comparison():
    """Print cost comparison for different tiers"""
    print("""
================================================================================
                    TOPIC TAGGER COST COMPARISON
================================================================================

 Tier | Method                    | Cost      | Accuracy | Speed
------|---------------------------|-----------|----------|--------------------
  1   | Programmatic (no AI)      | $0        | ~85-90%  | 1000 prov/sec
  2   | Claude Haiku batch        | ~$0.30    | ~92-95%  | 50 prov/sec
  3   | Claude Sonnet individual  | ~$27      | ~97-99%  | 2 prov/sec
  4   | Claude Opus few-shot      | ~$138     | ~99%+    | 1 prov/sec
------|---------------------------|-----------|----------|--------------------
 BEST | Hybrid (Prog + AI)        | ~$2-3     | ~95-97%  | 100 prov/sec avg
================================================================================

RECOMMENDATION: Use Hybrid approach
- Free for most provisions (programmatic handles ~80%)
- AI only for ambiguous cases
- Best cost/accuracy tradeoff
""")


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--tier', type=int, choices=[2, 3, 4], default=2)
    parser.add_argument('--sample', type=int, default=10, help='Number of provisions to test')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--cost', action='store_true', help='Show cost comparison')
    args = parser.parse_args()

    if args.cost:
        print_cost_comparison()
        return

    # Get sample provisions
    provisions = get_provisions(limit=args.sample)
    print(f"Testing with {len(provisions)} provisions")

    if args.dry_run:
        print("\n[DRY RUN] Would classify provisions with tier", args.tier)
        for p in provisions[:5]:
            text = (p['provision_text'] or '')[:80]
            print(f"  ID {p['id']}: {text}...")
        return

    # Initialize Anthropic client
    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic()
    except ImportError:
        print("Install anthropic: pip install anthropic")
        return

    # Run classification
    if args.tier == 2:
        results = await tier2_classify_batch(provisions, client)
    elif args.tier == 3:
        results = []
        for p in provisions:
            r = await tier3_classify_individual(p, client)
            results.append(r)
            print(f"  {p['id']}: {r.topic} ({r.confidence:.2f}) - {r.reasoning[:50]}")
            await asyncio.sleep(0.5)
    elif args.tier == 4:
        results = []
        for p in provisions:
            r = await tier4_classify_opus(p, client)
            results.append(r)
            print(f"  {p['id']}: {r.topic} ({r.confidence:.2f}) - {r.reasoning[:50]}")
            await asyncio.sleep(0.5)

    # Summary
    print(f"\nClassified {len(results)} provisions")
    from collections import Counter
    topic_counts = Counter(r.topic for r in results)
    print("Topic distribution:")
    for topic, count in topic_counts.most_common(10):
        print(f"  {topic}: {count}")


if __name__ == '__main__':
    asyncio.run(main())
