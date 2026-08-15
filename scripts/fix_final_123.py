#!/usr/bin/env python3
"""Fix the final 123 provisions."""
import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

with open('scripts/checkpoints/phase1_failed.json', 'r') as f:
    failed_ids = json.load(f)

# Manual classifications based on review
NOT_ACTIONABLE = [
    # Descriptions, history, context
    80370, 80373, 80374, 80376, 80385, 80389, 80401, 80419, 80420, 80426, 80428,
    80477, 80478, 80481, 80485, 80638, 80641, 80750, 80752, 80753, 80792, 80794,
    80860, 80866,
    # Cross-references and scope statements
    80632, 80633, 80634, 80694, 80695, 80747, 80748, 80787, 80788, 80790, 80796, 80797,
    80863, 80864,
    # General/precinct descriptions
    87248, 87352, 87361, 87363, 87366, 87368, 87371, 87373, 87376, 87387, 87390,
    87394, 87396, 87397, 87451, 87453, 87456, 87471, 87479, 87490, 87493,
    # Procedural/admin
    81210, 81300, 81305, 81348,
    # Lists/fragments
    81187, 81188, 81256, 81369, 81372,
]

# Topic changes
TOPIC_CHANGES = {
    # access
    81004: 'access',  # balcony for disability - correct

    # energy
    80946: 'energy',  # heating systems - correct
    81169: 'energy',  # BASIX
    81174: 'energy',  # BCA energy
    81175: 'energy',  # alterations energy

    # general -> specific topics
    79631: 'general',  # subdivision - keep general
    82819: 'general',  # same
    83800: 'general',  # same

    # precinct - landscape features
    80442: 'landscaping',  # Wharf Road landscape features
    80447: 'precinct',  # escarpment - keep precinct
    80449: 'precinct',  # rock edges - keep precinct
    87077: 'precinct',  # domain interface - keep

    # stormwater
    81071: 'stormwater',  # separators - correct

    # vehicle_access
    81063: 'vehicle_access',  # turning bays - correct

    # site_specific that are actual controls
    80432: 'site_specific',  # address list - keep
    80507: 'views',  # protect views
    80509: 'building_design',  # awnings
    80543: 'parking',  # parking rates
    80546: 'vehicle_access',  # loading
    80550: 'sustainability',  # sustainability
    80553: 'access',  # active transport
    80559: 'sustainability',  # sustainability criteria
    80589: 'setbacks',  # building envelopes
    80607: 'building_design',  # balcony design
    80621: 'sustainability',  # sustainability
    80669: 'building_design',  # balcony design
    80677: 'sustainability',  # greenstar
    80687: 'parking',  # parking rates
    80707: 'building_design',  # awnings
    80772: 'building_design',  # facade design
    80786: 'site_specific',  # site specific intro - keep
    80807: 'general',  # boarding house amenity
    80810: 'general',  # room sizes
    80811: 'general',  # kitchenette
    80813: 'general',  # communal kitchen
    80814: 'general',  # sink requirements
    80816: 'general',  # storage
    80826: 'general',  # bathroom ratios
    80828: 'general',  # laundry
    80874: 'general',  # no residential at ground
    80888: 'building_design',  # ground floor treatment
    80890: 'general',  # noise
    80899: 'sustainability',  # ESD

    # Performance criteria
    87146: 'height',  # wall height
    87148: 'setbacks',  # setbacks
    87154: 'privacy',  # rear laneways surveillance
    87158: 'parking',  # carparking
    87171: 'energy',  # wood burning
    87188: 'general',  # staffing
    87212: 'general',  # waiting area
    87240: 'general',  # land dedication
    87250: 'general',  # major development requirements
    87297: 'general',  # SEPP65 controls
    87314: 'general',  # noise levels
    87405: 'vehicle_access',  # street closure
}

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

print(f"NOT_ACTIONABLE: {len(NOT_ACTIONABLE)}")
print(f"Topic changes: {len(TOPIC_CHANGES)}")

if args.execute:
    print("\nApplying...")

    for pid in NOT_ACTIONABLE:
        cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = %s", (pid,))

    for pid, new_topic in TOPIC_CHANGES.items():
        cur.execute("UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s", (new_topic, pid))

    conn.commit()
    print("Done!")

cur.close()
conn.close()
