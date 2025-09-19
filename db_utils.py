#!/usr/bin/env python3
"""
Unified Database Utilities for NSW Compliance Engine
Provides consistent PostgreSQL access for all services
"""

from db_config import get_connection
import psycopg2
from typing import List, Dict, Any, Optional
import json

class UnifiedDatabaseClient:
    """Unified database client for all compliance engine services"""

    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute query and return results"""
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        return cursor.fetchall()

    def execute_single(self, query: str, params: tuple = None) -> Optional[tuple]:
        """Execute query and return single result"""
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        return cursor.fetchone()

    def execute_count(self, table: str, where_clause: str = "", params: tuple = None) -> int:
        """Execute count query"""
        query = f"SELECT COUNT(*) FROM {table}"
        if where_clause:
            query += f" WHERE {where_clause}"

        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        return cursor.fetchone()[0]

    def get_regulatory_provisions(self, zone: str = None, development_type: str = None) -> List[Dict]:
        """Get regulatory provisions with optional filtering"""
        query = "SELECT * FROM regulatory_provisions WHERE 1=1"
        params = []

        if zone:
            query += " AND zone = %s"
            params.append(zone)

        if development_type:
            query += " AND development_type = %s"
            params.append(development_type)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_sepp_provisions(self, sepp_type: str = None, category: str = None) -> List[Dict]:
        """Get SEPP provisions with optional filtering"""
        query = "SELECT * FROM sepp_provisions WHERE 1=1"
        params = []

        if sepp_type:
            query += " AND sepp_type = %s"
            params.append(sepp_type)

        if category:
            query += " AND provision_category = %s"
            params.append(category)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_development_controls(self, zone: str = None) -> List[Dict]:
        """Get development controls with optional zone filtering"""
        query = "SELECT * FROM development_controls WHERE 1=1"
        params = []

        if zone:
            query += " AND zone_applicable = %s"
            params.append(zone)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_quantitative_standards(self, development_type: str = None) -> List[Dict]:
        """Get quantitative standards with optional filtering"""
        query = "SELECT * FROM quantitative_standards WHERE 1=1"
        params = []

        if development_type:
            query += " AND development_type = %s"
            params.append(development_type)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Convenience functions for backward compatibility
def get_regulatory_provisions(*args, **kwargs):
    """Backward compatibility function"""
    with UnifiedDatabaseClient() as db:
        return db.get_regulatory_provisions(*args, **kwargs)

def get_development_controls(*args, **kwargs):
    """Backward compatibility function"""
    with UnifiedDatabaseClient() as db:
        return db.get_development_controls(*args, **kwargs)

def get_quantitative_standards(*args, **kwargs):
    """Backward compatibility function"""
    with UnifiedDatabaseClient() as db:
        return db.get_quantitative_standards(*args, **kwargs)

def test_unified_database():
    """Test unified database connectivity"""
    try:
        with UnifiedDatabaseClient() as db:
            # Test each major table
            reg_count = db.execute_count('regulatory_provisions')
            dev_count = db.execute_count('development_controls')
            quant_count = db.execute_count('quantitative_standards')

            print(f"SUCCESS Unified database test passed:")
            print(f"  Regulatory provisions: {reg_count:,}")
            print(f"  Development controls: {dev_count:,}")
            print(f"  Quantitative standards: {quant_count:,}")

            return True

    except Exception as e:
        print(f"FAILED Unified database test failed: {e}")
        return False

if __name__ == "__main__":
    test_unified_database()
