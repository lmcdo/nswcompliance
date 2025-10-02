"""
Populate SEPP relationship tables with existing data
"""
from db_config import get_connection

def populate_sepp_metadata():
    """Insert metadata for all SEPPs in the database"""
    c = get_connection()
    cur = c.cursor()

    sepps = [
        {
            'name': 'Sustainable Buildings SEPP 2022',
            'doc_id': 'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation',
            'commenced': '2023-10-01',
            'epi': '2022-0521'
        },
        {
            'name': 'Transport and Infrastructure SEPP 2021',
            'doc_id': 'State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021___NSW_Legislation',
            'commenced': '2021-12-01',
            'epi': '2021-0732'
        },
        {
            'name': 'Planning Systems SEPP 2021',
            'doc_id': 'State_Environmental_Planning_Policy_(Planning_Systems)_2021___NSW_Legislation',
            'commenced': '2021-12-01',
            'epi': '2021-0733'
        },
        {
            'name': 'Housing SEPP 2021',
            'doc_id': 'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation',
            'commenced': '2021-12-01',
            'epi': '2021-0714'
        },
        {
            'name': 'Biodiversity and Conservation SEPP 2021',
            'doc_id': 'State_Environmental_Planning_Policy_(Biodiversity_and_Conservation)_2021___NSW_Legislation',
            'commenced': '2021-12-01',
            'epi': '2021-0722'
        },
        {
            'name': 'Resilience and Hazards SEPP 2021',
            'doc_id': 'State_Environmental_Planning_Policy_(Resilience_and_Hazards)_2021___NSW_Legislation',
            'commenced': '2021-12-01',
            'epi': '2021-0730'
        },
    ]

    for sepp in sepps:
        cur.execute("""
            INSERT INTO sepp_metadata (sepp_name, document_id, commenced_date, epi_number)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (sepp_name) DO UPDATE
            SET document_id = EXCLUDED.document_id,
                commenced_date = EXCLUDED.commenced_date,
                epi_number = EXCLUDED.epi_number
            RETURNING id
        """, (sepp['name'], sepp['doc_id'], sepp['commenced'], sepp['epi']))

        sepp_id = cur.fetchone()[0]
        print(f"✓ Inserted/Updated: {sepp['name']} (ID: {sepp_id})")

    c.commit()
    c.close()

def populate_sepp_amendments():
    """Insert known SEPP amendments"""
    c = get_connection()
    cur = c.cursor()

    # Get Transport & Infrastructure SEPP ID
    cur.execute("SELECT id FROM sepp_metadata WHERE sepp_name = 'Transport and Infrastructure SEPP 2021'")
    ti_sepp_id = cur.fetchone()[0]

    amendments = [
        {
            'name': 'Thermal Energy from Waste Amendment 2022',
            'base_sepp_id': ti_sepp_id,
            'commenced': '2022-12-16',
            'published': '2022-12-16',
            'epi': '2022-825',
            'type': 'prohibits',
            'affected_ids': [18945, 19101, 19195],  # Planning Systems provisions
            'summary': 'Bans thermal energy from waste facilities in Greater Sydney with limited exceptions'
        }
    ]

    for amend in amendments:
        cur.execute("""
            INSERT INTO sepp_amendments (
                amendment_name, base_sepp_id, commenced_date, published_date,
                epi_number, amendment_type, affected_provision_ids, summary
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            amend['name'], amend['base_sepp_id'], amend['commenced'],
            amend['published'], amend['epi'], amend['type'],
            amend['affected_ids'], amend['summary']
        ))

        amend_id = cur.fetchone()[0]
        print(f"✓ Inserted Amendment: {amend['name']} (ID: {amend_id})")

    c.commit()
    c.close()

def populate_sepp_maps():
    """Insert known SEPP maps"""
    c = get_connection()
    cur = c.cursor()

    # Get SEPP IDs
    cur.execute("SELECT id FROM sepp_metadata WHERE sepp_name = 'Sustainable Buildings SEPP 2022'")
    sb_sepp_id = cur.fetchone()[0]

    cur.execute("SELECT id FROM sepp_metadata WHERE sepp_name = 'Transport and Infrastructure SEPP 2021'")
    ti_sepp_id = cur.fetchone()[0]

    maps = [
        {
            'name': 'Thermal Energy from Waste Prohibition Map - Greater Sydney',
            'type': 'TEW',
            'sepp_id': ti_sepp_id,
            'provision_ids': [18945, 19101, 19195],
            'scope': 'Greater Sydney',
            'lgas': ['Inner West', 'Sydney', 'Canterbury-Bankstown', 'Central Coast']
        },
        {
            'name': 'SEPP (Sustainable Buildings) 2022 Climate Zones for BASIX Alterations Map',
            'type': 'BAL',
            'sepp_id': sb_sepp_id,
            'provision_ids': [6166, 6177],
            'scope': 'NSW-wide'
        },
        {
            'name': 'SEPP (Sustainable Buildings) 2022 Climate Zones for BASIX Buildings Map',
            'type': 'CLM',
            'sepp_id': sb_sepp_id,
            'provision_ids': [6100, 6105, 6109, 6113, 6134, 6136, 6141, 6142, 6169, 6172],
            'scope': 'NSW-wide'
        },
        {
            'name': 'Water Use Map',
            'type': 'WUM',
            'sepp_id': sb_sepp_id,
            'provision_ids': [6107, 6130, 6131, 6174],
            'scope': 'NSW-wide'
        }
    ]

    for map_data in maps:
        cur.execute("""
            INSERT INTO sepp_maps (
                map_name, map_type, sepp_metadata_id, provision_ids,
                geographic_scope, applies_to_lgas
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (map_name, map_type) DO UPDATE
            SET provision_ids = EXCLUDED.provision_ids
            RETURNING id
        """, (
            map_data['name'], map_data['type'], map_data['sepp_id'],
            map_data['provision_ids'], map_data.get('scope'),
            map_data.get('lgas')
        ))

        map_id = cur.fetchone()[0]
        print(f"✓ Inserted Map: {map_data['name']} (ID: {map_id})")

    c.commit()
    c.close()

def populate_climate_zones():
    """Insert known climate zones for Inner West"""
    c = get_connection()
    cur = c.cursor()

    # Get BAL and CLM map IDs
    cur.execute("SELECT id FROM sepp_maps WHERE map_type = 'BAL'")
    bal_map_id = cur.fetchone()[0]

    cur.execute("SELECT id FROM sepp_maps WHERE map_type = 'CLM'")
    clm_map_id = cur.fetchone()[0]

    zones = [
        {
            'zone_number': 5,
            'zone_name': 'INNER WEST',
            'map_id': bal_map_id,
            'map_type': 'BAL',
            'lgas': ['Inner West'],
            'suburbs': ['Marrickville', 'Newtown', 'Leichhardt']
        },
        {
            'zone_number': 2049,
            'zone_name': None,
            'map_id': clm_map_id,
            'map_type': 'CLM',
            'lgas': ['Inner West'],
            'suburbs': ['Marrickville', 'Newtown', 'Leichhardt']
        }
    ]

    for zone in zones:
        cur.execute("""
            INSERT INTO climate_zones (
                zone_number, zone_name, sepp_map_id, map_type, lgas, suburbs
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            zone['zone_number'], zone['zone_name'], zone['map_id'],
            zone['map_type'], zone['lgas'], zone['suburbs']
        ))

        zone_id = cur.fetchone()[0]
        print(f"✓ Inserted Climate Zone: {zone['zone_number']} (ID: {zone_id})")

    c.commit()
    c.close()

def populate_water_use_zones():
    """Insert water use zones"""
    c = get_connection()
    cur = c.cursor()

    # Get Water Use Map ID
    cur.execute("SELECT id FROM sepp_maps WHERE map_type = 'WUM'")
    wum_map_id = cur.fetchone()[0]

    zones = [
        {
            'area': 'Area B',
            'percentage': 40,
            'map_id': wum_map_id,
            'lgas': ['Inner West', 'Sydney', 'Canterbury-Bankstown'],
            'provision_id': 6131
        },
        {
            'area': 'Area A',
            'percentage': 10,
            'map_id': wum_map_id,
            'lgas': ['Central Coast', 'Wollongong'],
            'provision_id': 6130
        }
    ]

    for zone in zones:
        cur.execute("""
            INSERT INTO water_use_zones (
                area_designation, reduction_percentage, sepp_map_id, lgas, provision_id
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            zone['area'], zone['percentage'], zone['map_id'],
            zone['lgas'], zone['provision_id']
        ))

        zone_id = cur.fetchone()[0]
        print(f"✓ Inserted Water Use Zone: {zone['area']} - {zone['percentage']}% (ID: {zone_id})")

    c.commit()
    c.close()

def update_regulatory_provisions():
    """Link existing provisions to SEPP metadata"""
    c = get_connection()
    cur = c.cursor()

    # Get all SEPP metadata
    cur.execute("SELECT id, document_id FROM sepp_metadata")
    sepp_mappings = {row[1]: row[0] for row in cur.fetchall()}

    updated_count = 0
    for doc_id, sepp_id in sepp_mappings.items():
        cur.execute("""
            UPDATE regulatory_provisions
            SET sepp_metadata_id = %s
            WHERE document_id = %s
        """, (sepp_id, doc_id))

        updated_count += cur.rowcount

    print(f"✓ Updated {updated_count} regulatory provisions with SEPP metadata links")

    c.commit()
    c.close()

if __name__ == '__main__':
    print("=== POPULATING SEPP RELATIONSHIP TABLES ===\n")

    print("1. Populating SEPP Metadata...")
    populate_sepp_metadata()
    print()

    print("2. Populating SEPP Amendments...")
    populate_sepp_amendments()
    print()

    print("3. Populating SEPP Maps...")
    populate_sepp_maps()
    print()

    print("4. Populating Climate Zones...")
    populate_climate_zones()
    print()

    print("5. Populating Water Use Zones...")
    populate_water_use_zones()
    print()

    print("6. Updating Regulatory Provisions...")
    update_regulatory_provisions()
    print()

    print("✅ COMPLETE! Database structure properly linked.")