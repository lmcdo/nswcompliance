from db_safety_wrapper import get_safe_connection

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== UPDATING CLAUSE 4.3 AND 4.4 WITH COMPLETE TEXT ===")

    # Complete clause texts from the original extraction
    complete_clause_43 = """4.3 Height of buildings

(1) The objectives of this clause are as follows— (a) to ensure the height of buildings is compatible with the character of the locality, (b) to minimise adverse impacts on local amenity, (c) to provide an appropriate transition between buildings of different heights.

(2) The height of a building on any land is not to exceed the maximum height shown for the land on the Height of Buildings Map."""

    complete_clause_44 = """4.4 Floor space ratio

(1) The objectives of this clause are as follows— (a) to establish a maximum floor space ratio to enable appropriate development density, (b) to ensure development density reflects its locality, (c) to provide an appropriate transition between development of different densities, (d) to minimise adverse impacts on local amenity, (e) to increase the tree canopy and to protect the use and enjoyment of private properties and the public domain.

(2) The maximum floor space ratio for a building on any land is not to exceed the floor space ratio shown for the land on the Floor Space Ratio Map."""

    try:
        # 1. Update clause 4.3 (ID: 17479)
        print("1. Updating Clause 4.3 (Height of Buildings)...")

        cur.execute("""
            UPDATE regulatory_provisions
            SET provision_text = %s
            WHERE id = %s
        """, (complete_clause_43, 17479))

        print(f"   Updated clause 4.3 with {len(complete_clause_43)} characters")

        # 2. Update clause 4.4 (ID: 17473)
        print("2. Updating Clause 4.4 (Floor Space Ratio)...")

        cur.execute("""
            UPDATE regulatory_provisions
            SET provision_text = %s
            WHERE id = %s
        """, (complete_clause_44, 17473))

        print(f"   Updated clause 4.4 with {len(complete_clause_44)} characters")

        # 3. Also update the duplicate clause 4.4 (ID: 39578)
        print("3. Updating duplicate Clause 4.4 (ID: 39578)...")

        cur.execute("""
            UPDATE regulatory_provisions
            SET provision_text = %s
            WHERE id = %s
        """, (complete_clause_44, 39578))

        print(f"   Updated duplicate clause 4.4")

        # Commit the changes
        conn.commit()
        print("\n✅ Successfully committed all updates to database")

        # 4. Verify the updates
        print("\n4. VERIFYING UPDATES:")
        print("-" * 50)

        # Check clause 4.3
        cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = %s", (17479,))
        result = cur.fetchone()
        if result:
            text_len = len(result[0])
            print(f"Clause 4.3 (ID 17479): {text_len} characters")
            print(f"   Preview: {result[0][:100]}...")

        # Check clause 4.4
        cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = %s", (17473,))
        result = cur.fetchone()
        if result:
            text_len = len(result[0])
            print(f"Clause 4.4 (ID 17473): {text_len} characters")
            print(f"   Preview: {result[0][:100]}...")

        print("\n✅ Database update completed successfully!")

    except Exception as e:
        print(f"❌ Error updating database: {e}")
        conn.rollback()

    conn.close()

print("\nUpdate script completed.")