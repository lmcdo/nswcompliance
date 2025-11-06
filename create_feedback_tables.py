#!/usr/bin/env python3
"""
Script to create feedback tables in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

def create_feedback_tables():
    """Create feedback tables by running the SQL script"""

    try:
        # Read the SQL file
        with open('create_feedback_tables.sql', 'r') as f:
            sql_content = f.read()

        # Connect to database
        conn = get_dict_connection()
        cursor = conn.cursor()

        print("Creating feedback tables...")

        # Execute the SQL
        cursor.execute(sql_content)

        # Commit the transaction
        conn.commit()

        print("Feedback tables created successfully!")

        # Verify tables were created
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND (table_name LIKE '%feedback%' OR table_name LIKE '%vote%' OR table_name LIKE '%metric%' OR table_name LIKE '%review_queue%')
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print("\nCreated tables:")
        for table in tables:
            print(f"  - {table['table_name']}")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"Error creating feedback tables: {e}")
        return False

if __name__ == "__main__":
    success = create_feedback_tables()
    sys.exit(0 if success else 1)