#!/usr/bin/env python3
"""
Apply pattern-based topic fixes based on Claude's manual review.

Patterns identified:
1. "9.X.X Existing character" -> precinct
2. "9.X.X Desired future character" -> precinct
3. Site descriptions (area, bounded by) -> NOT_ACTIONABLE
4. Section intros (X.X Introduction, X.X Purpose) -> NOT_ACTIONABLE
5. Contamination keywords (hydrocarbon, soil vapour, remediation) -> contamination
6. Stormwater keywords (SWMMP, drainage, kerb, impervious) -> stormwater
7. Waste keywords (bins, garbage, collection) -> waste
8. Flooding keywords (AHD, flood level, surface flows) -> flooding
"""
import os
import sys
import re
import json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

import psycopg2
from psycopg2.extras import RealDictCursor


# Pattern rules: (regex/keyword, new_topic, description)
PATTERN_RULES = [
    # =========================================================================
    # PRECINCT PATTERNS
    # =========================================================================
    (r'^\d+\.\d+\.?\d*\s+Existing character', 'precinct', 'Existing character section'),
    (r'^\d+\.\d+\.?\d*\s+Desired future character', 'precinct', 'Desired future character section'),
    (r'^9\.\d+\s+', 'precinct', 'Part 9 precinct section'),
    (r'^9\.47\.\d+', 'precinct', 'Victoria Road Precinct section'),
    (r'Sub-Precincts|sub-precincts', 'precinct', 'Sub-precinct section'),
    (r'Future land use.*NB|Key land uses outcomes', 'precinct', 'Precinct land use'),
    (r'Noise Policy.*Precinct', 'precinct', 'Precinct noise policy'),
    (r'Desired Future Character and Controls for the Distinctive Neighbourhood', 'precinct', 'Distinctive Neighbourhood controls'),
    (r'Distinctive Neighbourhood', 'precinct', 'Distinctive Neighbourhood'),

    # =========================================================================
    # NOT_ACTIONABLE - Definitions, intros, fragments
    # =========================================================================
    (r'^Restoration means', 'NOT_ACTIONABLE', 'Definition'),
    (r'^Reinstatement.*means', 'NOT_ACTIONABLE', 'Definition'),
    (r'^Infill development includes', 'NOT_ACTIONABLE', 'Definition'),
    (r'^Original finishes or materials are', 'NOT_ACTIONABLE', 'Definition'),
    (r'The wall/s of the building that front', 'NOT_ACTIONABLE', 'Definition'),
    (r'^Character:', 'NOT_ACTIONABLE', 'Definition of character'),
    (r'^Form:', 'NOT_ACTIONABLE', 'Definition of form'),
    (r'A green wall is either free-standing', 'NOT_ACTIONABLE', 'Definition of green wall'),
    (r'^\d+\.\d+\s+Introduction', 'NOT_ACTIONABLE', 'Section introduction'),
    (r'^\d+\.\d+\s+Purpose', 'NOT_ACTIONABLE', 'Section purpose'),
    (r'^2\.3 Site and Context Analysis', 'NOT_ACTIONABLE', 'Section intro'),
    (r'^2\.3\.1 Purpose of site', 'NOT_ACTIONABLE', 'Section intro'),
    (r'^4\.1 This section forms part of', 'NOT_ACTIONABLE', 'Section scope'),
    (r'provisions of Part C Section 1', 'NOT_ACTIONABLE', 'Cross-reference'),
    (r'The site has a combined area of approximately', 'NOT_ACTIONABLE', 'Site description'),
    (r'The site is located on the', 'NOT_ACTIONABLE', 'Site location description'),
    (r'^Note:', 'NOT_ACTIONABLE', 'Just a note'),
    (r'^a\. new residential and non-residential buildings', 'NOT_ACTIONABLE', 'Applicability list'),
    (r'^b\. proposed changes to existing buildings', 'NOT_ACTIONABLE', 'List fragment'),
    (r'^a\. for multiple occupancy tenancies', 'NOT_ACTIONABLE', 'List fragment'),
    (r'^a\. balconies and verandahs', 'NOT_ACTIONABLE', 'List fragment'),
    (r'^a\. existing site conditions', 'NOT_ACTIONABLE', 'List fragment'),
    (r'^a\. are functional', 'NOT_ACTIONABLE', 'List fragment'),
    (r'^a\. complements the character', 'NOT_ACTIONABLE', 'List fragment'),
    (r'^b\. sampling and analysis', 'NOT_ACTIONABLE', 'List fragment'),
    (r'^e\. is public accessible', 'NOT_ACTIONABLE', 'List fragment'),
    (r'^f\. create spaces which are well lit', 'NOT_ACTIONABLE', 'List fragment'),
    (r'^a\)\s*Green fa', 'NOT_ACTIONABLE', 'Definition of green facade'),
    (r'^b\)\s*Green wall:', 'NOT_ACTIONABLE', 'Definition of green wall'),
    (r'Additions at first floor.*shall be of a scale', 'building_form', 'Additions scale (not contamination)'),
    (r'vegetation.*SEPP applies', 'NOT_ACTIONABLE', 'SEPP reference'),
    (r'Council will.*promote urban design', 'NOT_ACTIONABLE', 'General statement'),
    (r'^6\.3 Multi Unit Industrial', 'NOT_ACTIONABLE', 'Section intro'),
    (r'Site and context analysis is a critical', 'site_analysis', 'Site analysis guidance'),
    (r'^2 New allotments shall be consistent', 'general', 'Subdivision control'),

    # =========================================================================
    # HERITAGE - retain original, archaeological, historic styles
    # =========================================================================
    (r'retain.*original|reconstruct original|original form', 'heritage', 'Heritage retention'),
    (r'front two rooms|major form.*scale.*materials', 'heritage', 'Heritage alterations'),
    (r'archaeological.*significant|aboriginal.*archaeological', 'heritage', 'Archaeological heritage'),
    (r'The following applies to.*aboriginal.*archaeological', 'heritage', 'Archaeological heritage'),
    (r'addition.*can be seen from.*street', 'heritage', 'Heritage streetscape'),
    (r'roof form.*chimneys|internal walls.*roof form', 'heritage', 'Heritage roof elements'),
    (r'remain separate from.*main roof slope', 'heritage', 'Heritage roof additions'),
    (r'front verandah.*original building', 'heritage', 'Heritage verandah'),
    (r'original.*materials|original.*joinery|original.*verandah', 'heritage', 'Heritage original elements'),
    (r'Victorian.*Italianate|Federation.*Queen Anne|California Bungalow|Inter-war', 'heritage', 'Heritage architectural style'),
    (r'aesthetic significance|streetscape.*consistent|heritage significance', 'heritage', 'Heritage significance'),
    (r'demolition.*significant elements|retain.*significant', 'heritage', 'Heritage retention controls'),
    (r'controls.*street frontage|visible from.*street', 'heritage', 'Heritage streetscape controls'),
    (r'subdivision.*1880|subdivision.*1911|Victorian period', 'heritage', 'Heritage history'),
    (r'awning level|streetfront presentation', 'heritage', 'Heritage streetfront'),
    (r'addition.*well-designed|addition.*can be seen', 'heritage', 'Heritage additions'),
    (r'controls.*street frontage.*existing building', 'heritage', 'Heritage street controls'),
    (r'adapted for new uses|guided by.*significance', 'heritage', 'Heritage adaptation'),
    (r'recovery of.*significant.*forms|removing.*inappropriate addition', 'heritage', 'Heritage recovery'),
    (r'hedges along.*property boundaries', 'landscaping', 'Landscaping hedges (not heritage)'),
    (r'Robert Campbell.*Estate|Rev Richard Johnson|granted in 1796', 'NOT_ACTIONABLE', 'Historical background'),
    (r'^Medium height.*hedges', 'landscaping', 'Hedge specification'),

    # =========================================================================
    # BUILDING FORM / DESIGN
    # =========================================================================
    (r'basement wall|basement proposal|geotechnical|structural engineer', 'building_form', 'Basement engineering'),
    (r'subsurface flow|subsoil drainage', 'building_form', 'Subsurface engineering'),
    (r'corner sites.*compatible|delineates.*old and new', 'building_design', 'Corner site design'),
    (r'address each street frontage|featureless walls', 'building_design', 'Facade design'),
    (r'balconies.*verandahs.*awnings|protective structures.*balconies', 'building_design', 'Awning/balcony design'),
    (r'established character.*locality|view-sharing principles', 'precinct', 'Precinct character objectives'),
    (r'recreation activities.*play|pedestrian access.*facilitate', 'open_space', 'Open space/access objectives'),
    (r'character.*street.*topography|houses.*stepping down', 'precinct', 'Precinct character description'),
    (r'garden structures.*conservatories|gazebos.*ornaments', 'landscaping', 'Garden structures'),
    (r'shape.*form.*escarpment|escarpment.*retained', 'precinct', 'Precinct escarpment'),
    (r'visual prominence.*natural landscape|ridgelines.*rock outcrops', 'landscaping', 'Natural landscape'),
    (r'Independent Site Auditing|Site Audit Statement', 'contamination', 'Site auditing'),
    (r'natural rock edges.*retained|rock edges.*intact form', 'precinct', 'Precinct rock retention'),
    (r'new character.*compatible|new character.*site shall', 'precinct', 'Precinct new character'),
    (r'buildings.*high quality appearance|fronts.*backs.*tops.*buildings', 'building_design', 'Building design objectives'),
    (r'encroachments.*airspace.*road|encroachments.*Council roads', 'building_form', 'Building encroachment'),
    (r'green roofs|food production.*building insulation|fauna.*flora.*microclimates', 'sustainability', 'Green roof/sustainability'),

    # =========================================================================
    # SOLAR / ORIENTATION
    # =========================================================================
    (r'north facing.*living areas|lot orientation.*north', 'solar', 'Solar orientation'),

    # =========================================================================
    # CONTAMINATION
    # =========================================================================
    (r'hydrocarbon|soil vapour|volatile emissions|remediation work|contaminated|soil sampling', 'contamination', 'Contamination keywords'),
    (r'sampling and analysis of.*fill', 'contamination', 'Fill material sampling'),
    (r'Preliminary Site Investigation|site history.*limited', 'contamination', 'Site investigation'),
    (r'level of investigation.*remediation|past uses of the site', 'contamination', 'Remediation investigation'),

    # =========================================================================
    # OPEN SPACE
    # =========================================================================
    (r'minimum area of 10%.*site|trees.*seating.*lighting', 'open_space', 'Open space requirements'),

    # =========================================================================
    # LANDSCAPING - green walls, vegetation
    # =========================================================================
    (r'green wall|green fa[cç]ade|living wall|climbing plants', 'landscaping', 'Green wall/facade'),
    (r'topographic.*landscape features|escarpment.*rock.*trees', 'landscaping', 'Landscape features'),
    (r'Landscape treatment.*communal|native plants', 'landscaping', 'Landscape treatment'),
    (r'landscape documentation|BASIX.*landscape', 'landscaping', 'Landscape documentation'),
    (r'fauna.*lighting.*nocturnal|GreenWay Corridor', 'landscaping', 'Landscape corridor'),
    (r'communal landscape area', 'landscaping', 'Communal landscape'),

    # =========================================================================
    # TREES
    # =========================================================================
    (r'cut down.*vegetation|fell.*tree|poison.*tree|branch failure|limb fall', 'trees', 'Tree management'),
    (r'species.*susceptibility|longevity.*species', 'trees', 'Tree species'),
    (r'likelihood of branch failure', 'trees', 'Tree risk'),
    (r'uproot.*kill.*poison.*ringbark', 'trees', 'Tree removal'),
    (r'lop or otherwise remove.*vegetation', 'trees', 'Tree pruning'),

    # =========================================================================
    # PARKING
    # =========================================================================
    (r'car share|parking space|garage door', 'parking', 'Parking keywords'),
    (r'Car share spaces', 'parking', 'Car share parking'),
    (r'storage of bins|number of bins', 'waste', 'Bin storage (not parking)'),

    # =========================================================================
    # VEHICLE ACCESS
    # =========================================================================
    (r'turning area|swept path|loading zone|service vehicle|delivery vehicle', 'vehicle_access', 'Vehicle access keywords'),

    # =========================================================================
    # STORMWATER / WATER
    # =========================================================================
    (r'SWMMP|stormwater|kerb and gutter|impervious area|on-site detention|OSD', 'stormwater', 'Stormwater keywords'),
    (r'odour.*drainage system', 'waste', 'Waste drainage'),

    # =========================================================================
    # WASTE
    # =========================================================================
    (r'\bbins?\b.*storage|\bgarbage\b|\bwaste\b.*collection|\brecycling\b', 'waste', 'Waste keywords'),

    # =========================================================================
    # FLOODING
    # =========================================================================
    (r'AHD|flood level|flood planning|surface flows|flood prone', 'flooding', 'Flooding keywords'),

    # =========================================================================
    # SETBACKS
    # =========================================================================
    (r'setback pattern|maintain.*setback|boundary setback', 'setbacks', 'Setback patterns'),

    # =========================================================================
    # SIGNAGE
    # =========================================================================
    (r'banner|advertisement.*scaffolding|advertising sign', 'signage', 'Signage patterns'),

    # =========================================================================
    # ACCESS
    # =========================================================================
    (r'public transport.*pedestrians.*cycling', 'access', 'Multi-modal access'),

    # =========================================================================
    # GENERAL / ENVIRONMENTAL
    # =========================================================================
    (r'sustainable housing practices', 'general', 'General sustainability'),
    (r'This section applies to the portion', 'general', 'Section scope'),
    (r'Wide Lane.*width|laneway boundary|laneway hierarchy', 'general', 'Laneway controls'),
    (r'rock features|endemic.*area', 'environmental', 'Environmental features'),
]


def classify_by_pattern(text: str) -> tuple:
    """Classify text using pattern rules. Returns (topic, rule_desc) or (None, None)."""
    if not text:
        return None, None

    for pattern, topic, desc in PATTERN_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return topic, desc

    return None, None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()

    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("=" * 60)
    print("PATTERN-BASED TOPIC FIX")
    print("=" * 60)

    # Load failed IDs
    with open('scripts/checkpoints/phase1_failed.json', 'r') as f:
        failed_ids = json.load(f)

    # Get provisions
    cur.execute('''
        SELECT id, v2_topic, provision_text
        FROM regulatory_provisions
        WHERE id = ANY(%s)
    ''', (failed_ids,))

    provisions = cur.fetchall()
    print(f"\nFailed provisions: {len(provisions)}")

    if args.limit:
        provisions = provisions[:args.limit]

    # Classify
    changes = []
    not_actionable = []
    no_match = []

    for prov in provisions:
        text = prov['provision_text'][:500] if prov.get('provision_text') else ''
        old_topic = prov['v2_topic']

        new_topic, rule = classify_by_pattern(text)

        if new_topic == 'NOT_ACTIONABLE':
            not_actionable.append((prov['id'], old_topic, rule))
        elif new_topic and new_topic != old_topic:
            changes.append((prov['id'], old_topic, new_topic, rule))
        elif new_topic == old_topic:
            pass  # Already correct
        else:
            no_match.append(prov['id'])

    print(f"\nResults:")
    print(f"  Topic changes: {len(changes)}")
    print(f"  Mark NOT_ACTIONABLE: {len(not_actionable)}")
    print(f"  No pattern match: {len(no_match)}")

    # Show samples
    if changes[:15]:
        print(f"\nSample topic changes:")
        for pid, old, new, rule in changes[:15]:
            print(f"  ID {pid}: {old} -> {new} ({rule})")

    if not_actionable[:10]:
        print(f"\nSample NOT_ACTIONABLE:")
        for pid, old, rule in not_actionable[:10]:
            print(f"  ID {pid}: was {old} ({rule})")

    # Apply
    if args.execute and (changes or not_actionable):
        print("\nApplying changes...")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'scripts/backups/pattern_fix_{timestamp}.json'
        backup_data = {
            'changes': changes,
            'not_actionable': not_actionable,
        }
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        print(f"Backup: {backup_file}")

        # Apply topic changes
        for pid, old, new, rule in changes:
            cur.execute(
                "UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s",
                (new, pid)
            )

        # Mark not actionable
        for pid, old, rule in not_actionable:
            cur.execute(
                "UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = %s",
                (pid,)
            )

        conn.commit()
        print(f"Applied {len(changes)} topic changes")
        print(f"Marked {len(not_actionable)} as not actionable")

    cur.close()
    conn.close()
    print("\nDone!")


if __name__ == '__main__':
    main()
