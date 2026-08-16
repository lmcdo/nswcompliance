#!/usr/bin/env python3
"""
Final classification of remaining 156 provisions.
Based on manual review by Claude.
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

load_dotenv('frontend-nextjs/.env.local')

# Classifications: id -> (old_topic, new_topic, reason)
# NOT_ACTIONABLE = mark v2_is_actionable = false
# KEEP = topic is correct, just expand keyword list

FIXES = {
    # ACCESS - most are correct or should be general/precinct
    78540: ('access', 'NOT_ACTIONABLE', 'Section intro - mixed use definition'),
    79778: ('access', 'access', 'KEEP - transport balance'),
    80382: ('access', 'vehicle_access', 'Vehicle movement'),
    82966: ('access', 'access', 'KEEP - same as 79778'),
    83947: ('access', 'access', 'KEEP - same as 79778'),
    87387: ('access', 'precinct', 'Precinct description - Liverpool Rd'),
    87391: ('access', 'precinct', 'Precinct objectives'),

    # BUILDING_DESIGN - loading areas are vehicle_access, objectives are correct
    79830: ('building_design', 'vehicle_access', 'Loading/service areas'),
    80522: ('building_design', 'building_design', 'KEEP - design objectives'),
    80525: ('building_design', 'building_design', 'KEEP - design objectives'),
    80591: ('building_design', 'building_design', 'KEEP - design objectives'),
    80595: ('building_design', 'building_design', 'KEEP - design objectives'),
    80655: ('building_design', 'building_design', 'KEEP - design objectives'),
    80721: ('building_design', 'building_design', 'KEEP - design objectives'),
    80725: ('building_design', 'building_design', 'KEEP - design objectives'),
    80766: ('building_design', 'building_design', 'KEEP - design objectives'),
    83018: ('building_design', 'vehicle_access', 'Loading/service areas'),
    83999: ('building_design', 'vehicle_access', 'Loading/service areas'),

    # BUILDING_FORM - many are precinct or site-specific
    80072: ('building_form', 'NOT_ACTIONABLE', 'List fragment - encroachments'),
    80603: ('building_form', 'NOT_ACTIONABLE', 'Reference to SEPP65'),
    80800: ('building_form', 'precinct', 'Camperdown Ultimo precinct'),
    80846: ('building_form', 'sustainability', 'ESD principles'),
    80868: ('building_form', 'general', 'Lot amalgamation'),
    80910: ('building_form', 'site_analysis', 'Site opportunities/constraints'),
    80911: ('building_form', 'general', 'Design principles'),
    80943: ('building_form', 'energy', 'Electrical/mechanical requirements'),
    81091: ('building_form', 'general', 'Subdivision objectives'),
    81164: ('building_form', 'general', 'Public domain objectives'),
    83260: ('building_form', 'NOT_ACTIONABLE', 'List fragment - encroachments'),
    84241: ('building_form', 'NOT_ACTIONABLE', 'List fragment - encroachments'),
    86121: ('building_form', 'general', 'Mixed use compatibility'),
    86696: ('building_form', 'NOT_ACTIONABLE', 'Part 9 intro'),
    86703: ('building_form', 'precinct', 'Lewisham North precinct'),
    87077: ('building_form', 'precinct', 'Domain interface controls'),
    87248: ('building_form', 'precinct', 'Ashfield Town Centre'),
    87273: ('building_form', 'precinct', 'SEPP65 townscape'),
    87298: ('building_form', 'precinct', 'Ashfield West townscape'),
    87377: ('building_form', 'precinct', 'Area 2 character'),
    87381: ('building_form', 'precinct', 'Area 2 built form'),
    87385: ('building_form', 'precinct', 'Area 3 character'),
    87388: ('building_form', 'precinct', 'Rail overpass area'),
    87394: ('building_form', 'precinct', 'Parramatta Road DCP'),
    87465: ('building_form', 'precinct', 'Edward Street character'),
    87491: ('building_form', 'precinct', 'Adaptive reuse'),

    # FLOODING - these are correct, AHD is a flooding keyword
    80249: ('flooding', 'flooding', 'KEEP - AHD levels'),
    80261: ('flooding', 'flooding', 'KEEP - surface flows'),
    83437: ('flooding', 'flooding', 'KEEP - same as 80249'),
    83449: ('flooding', 'flooding', 'KEEP - same as 80261'),
    84418: ('flooding', 'flooding', 'KEEP - same as 80249'),
    84430: ('flooding', 'flooding', 'KEEP - same as 80261'),

    # HEIGHT - this is precinct-specific
    86970: ('height', 'precinct', 'Camperdown North precinct'),

    # HERITAGE - historical background is NOT_ACTIONABLE, controls are heritage
    81441: ('heritage', 'heritage', 'KEEP - additions guidance'),
    81482: ('heritage', 'heritage', 'KEEP - street frontage controls'),
    81541: ('heritage', 'heritage', 'KEEP - adaptive reuse'),
    81563: ('heritage', 'heritage', 'KEEP - demolition controls'),
    81647: ('heritage', 'NOT_ACTIONABLE', 'Historical description'),
    81664: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81694: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81743: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81744: ('heritage', 'NOT_ACTIONABLE', 'Historical image caption'),
    81746: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81748: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81750: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81767: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81781: ('heritage', 'NOT_ACTIONABLE', 'Street description'),
    81791: ('heritage', 'NOT_ACTIONABLE', 'Historical covenant'),
    81792: ('heritage', 'NOT_ACTIONABLE', 'Historical observation'),
    81813: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81869: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81871: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81872: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81909: ('heritage', 'NOT_ACTIONABLE', 'Street description'),
    81915: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81920: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81921: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81925: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81960: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81965: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    81967: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82027: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82031: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82033: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82038: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82039: ('heritage', 'NOT_ACTIONABLE', 'Recent streetscape work'),
    82050: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82069: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82070: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82113: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82117: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82181: ('heritage', 'heritage', 'KEEP - building elements'),
    82195: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82231: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82249: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82250: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82287: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82405: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82406: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82416: ('heritage', 'NOT_ACTIONABLE', 'Historical background'),
    82456: ('heritage', 'NOT_ACTIONABLE', 'Historical map caption'),
    82505: ('heritage', 'heritage', 'KEEP - non-significant elements'),

    # LANDSCAPING - ridgelines is general, others correct
    79632: ('landscaping', 'general', 'Natural features'),
    80429: ('landscaping', 'landscaping', 'KEEP - garden structures'),
    81173: ('landscaping', 'landscaping', 'KEEP - BASIX landscape'),
    81640: ('landscaping', 'landscaping', 'KEEP - hedge spec'),
    82820: ('landscaping', 'general', 'Same as 79632'),
    83801: ('landscaping', 'general', 'Same as 79632'),
    86710: ('landscaping', 'landscaping', 'KEEP - fauna corridor'),
    87241: ('landscaping', 'landscaping', 'KEEP - communal landscape'),

    # OPEN_SPACE - some are landscaping references
    79918: ('open_space', 'NOT_ACTIONABLE', 'Note - cross reference'),
    79931: ('open_space', 'open_space', 'KEEP - plaza requirements'),
    80404: ('open_space', 'open_space', 'KEEP - recreation spaces'),
    83106: ('open_space', 'NOT_ACTIONABLE', 'Same as 79918'),
    83119: ('open_space', 'open_space', 'KEEP - same as 79931'),
    84087: ('open_space', 'NOT_ACTIONABLE', 'Same as 79918'),
    84100: ('open_space', 'open_space', 'KEEP - same as 79931'),

    # SAFETY - correct
    80980: ('safety', 'safety', 'KEEP - CPTED objectives'),

    # SETBACKS - these are building alterations
    79590: ('setbacks', 'heritage', 'Heritage alterations'),
    79591: ('setbacks', 'heritage', 'Heritage typologies'),
    82778: ('setbacks', 'heritage', 'Same as 79590'),
    82779: ('setbacks', 'heritage', 'Same as 79591'),
    83759: ('setbacks', 'heritage', 'Same as 79590'),
    83760: ('setbacks', 'heritage', 'Same as 79591'),

    # SIGNAGE - correct
    80033: ('signage', 'signage', 'KEEP - banner size'),
    80053: ('signage', 'signage', 'KEEP - scaffolding ads'),
    83221: ('signage', 'signage', 'KEEP - same as 80033'),
    83241: ('signage', 'signage', 'KEEP - same as 80053'),
    84202: ('signage', 'signage', 'KEEP - same as 80033'),
    84222: ('signage', 'signage', 'KEEP - same as 80053'),

    # STORMWATER - many are correct
    80268: ('stormwater', 'stormwater', 'KEEP - impervious area'),
    80285: ('stormwater', 'stormwater', 'KEEP - roof drainage'),
    80290: ('stormwater', 'stormwater', 'KEEP - kerb connections'),
    80323: ('stormwater', 'stormwater', 'KEEP - controls reference'),
    83456: ('stormwater', 'stormwater', 'KEEP - same as 80268'),
    83473: ('stormwater', 'stormwater', 'KEEP - same as 80285'),
    83478: ('stormwater', 'stormwater', 'KEEP - same as 80290'),
    83511: ('stormwater', 'stormwater', 'KEEP - same as 80323'),
    84437: ('stormwater', 'stormwater', 'KEEP - same as 80268'),

    # VEHICLE_ACCESS
    79797: ('vehicle_access', 'vehicle_access', 'KEEP - turning areas'),
    79879: ('vehicle_access', 'parking', 'Parking space width'),
    82985: ('vehicle_access', 'vehicle_access', 'KEEP - same as 79797'),
    83067: ('vehicle_access', 'parking', 'Same as 79879'),
    83966: ('vehicle_access', 'vehicle_access', 'KEEP - same as 79797'),
    84048: ('vehicle_access', 'parking', 'Same as 79879'),

    # WASTE
    80437: ('waste', 'heritage', 'Sandstone kerbing - heritage'),
    81370: ('waste', 'heritage', 'Same as 80437'),
    83638: ('waste', 'heritage', 'Same as 80437'),
    83615: ('waste', 'waste', 'KEEP - waste management'),
    84604: ('waste', 'waste', 'KEEP - waste management'),
    84619: ('waste', 'heritage', 'Same as 80437'),
    87503: ('waste', 'waste', 'KEEP - waste management'),

    # WATER
    80285: ('water', 'stormwater', 'Roof drainage - stormwater'),
    80290: ('water', 'stormwater', 'Kerb connections - stormwater'),
    80323: ('water', 'stormwater', 'Controls reference - stormwater'),
    83473: ('water', 'stormwater', 'Same as 80285'),
    83478: ('water', 'stormwater', 'Same as 80290'),
    83511: ('water', 'stormwater', 'Same as 80323'),
    84454: ('water', 'stormwater', 'Roof drainage to street'),
    84492: ('water', 'NOT_ACTIONABLE', 'Reference to other controls'),

    # Missing 15
    78537: ('waste', 'NOT_ACTIONABLE', 'Section intro - commercial types'),
    79881: ('vehicle_access', 'vehicle_access', 'KEEP - swept path'),
    80145: ('stormwater', 'stormwater', 'KEEP - SWMMP requirement'),
    80168: ('waste', 'waste', 'KEEP - odour/drainage'),
    81279: ('waste', 'waste', 'KEEP - bin presentation'),
    81290: ('waste', 'waste', 'KEEP - ventilation'),
    83069: ('vehicle_access', 'vehicle_access', 'KEEP - same as 79881'),
    83333: ('stormwater', 'stormwater', 'KEEP - same as 80145'),
    83356: ('waste', 'waste', 'KEEP - same as 80168'),
    84050: ('vehicle_access', 'vehicle_access', 'KEEP - same as 79881'),
    84314: ('stormwater', 'stormwater', 'KEEP - same as 80145'),
    84337: ('waste', 'waste', 'KEEP - same as 80168'),
    84459: ('stormwater', 'stormwater', 'KEEP - kerb connections'),
}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()

    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()

    # Load failed IDs
    with open('scripts/checkpoints/phase1_failed.json', 'r') as f:
        failed_ids = set(json.load(f))

    print("=" * 60)
    print("FINAL 156 FIXES")
    print("=" * 60)

    # Analyze
    changes = []
    not_actionable = []
    keep_same = []
    missing = []

    for fid in failed_ids:
        if fid in FIXES:
            old, new, reason = FIXES[fid]
            if new == 'NOT_ACTIONABLE':
                not_actionable.append((fid, old, reason))
            elif 'KEEP' in reason:
                keep_same.append(fid)
            else:
                changes.append((fid, old, new, reason))
        else:
            missing.append(fid)

    print(f"\nTotal failed: {len(failed_ids)}")
    print(f"Classified: {len(FIXES)}")
    print(f"  - Topic changes: {len(changes)}")
    print(f"  - Mark NOT_ACTIONABLE: {len(not_actionable)}")
    print(f"  - Keep same (correct): {len(keep_same)}")
    print(f"Missing classification: {len(missing)}")

    if missing:
        print(f"\nMissing IDs: {missing[:20]}...")

    if args.execute and (changes or not_actionable):
        print("\nApplying...")

        # Backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'scripts/backups/final_156_{timestamp}.json'
        with open(backup_file, 'w') as f:
            json.dump({'changes': changes, 'not_actionable': not_actionable}, f, indent=2)
        print(f"Backup: {backup_file}")

        # Apply topic changes
        for fid, old, new, reason in changes:
            cur.execute(
                "UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s",
                (new, fid)
            )

        # Mark not actionable
        for fid, old, reason in not_actionable:
            cur.execute(
                "UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = %s",
                (fid,)
            )

        conn.commit()
        print(f"Applied {len(changes)} topic changes")
        print(f"Marked {len(not_actionable)} as not actionable")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
