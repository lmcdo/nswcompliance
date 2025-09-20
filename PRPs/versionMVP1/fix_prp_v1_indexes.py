#!/usr/bin/env python3
"""
Fix PRP-V1 by adding missing indexes
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from db_config import get_connection

def add_missing_indexes():
    """Add the missing indexes for PRP-V1 completion"""

    print("Adding missing indexes for PRP-V1 completion...")

    indexes = [
        ("idx_provisions_version", "regulatory_provisions", "version_id, is_current"),
        ("idx_controls_version", "development_controls", "version_id, is_current"),
        ("idx_standards_version", "quantitative_standards", "version_id, is_current")
    ]

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            for index_name, table_name, columns in indexes:
                sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns});"
                cursor.execute(sql)
                print(f"Created {index_name}")

            conn.commit()
            print("All indexes created successfully")

        conn.close()
        print("Database connection closed")
        return True

    except Exception as e:
        print(f"Error creating indexes: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = add_missing_indexes()
    sys.exit(0 if success else 1)