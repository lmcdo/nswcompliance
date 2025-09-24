#!/usr/bin/env python3
"""
CORRECTED SQLite to PostgreSQL Migration
Fixes all type mismatches and restores relationships
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

def migrate_with_correct_types():
    """Re-migrate with proper type mapping"""

    sqlite_db = 'nsw_planning.db'

    # First connect to postgres to create database
    admin_config = {
        'host': 'localhost',
        'database': 'postgres',  # Admin database
        'user': 'postgres',
        'password': 'postgres',
        'port': '5432'
    }

    pg_config = {
        'host': 'localhost',
        'database': 'nsw_planning_corrected',  # New database
        'user': 'postgres',
        'password': 'postgres',
        'port': '5432'
    }

    print('Creating new database nsw_planning_corrected...')

    # Create new database
    try:
        admin_conn = psycopg2.connect(**admin_config)
        admin_conn.autocommit = True
        admin_cursor = admin_conn.cursor()
        admin_cursor.execute("DROP DATABASE IF EXISTS nsw_planning_corrected")
        admin_cursor.execute("CREATE DATABASE nsw_planning_corrected")
        admin_cursor.close()
        admin_conn.close()
        print('Database created successfully')
    except Exception as e:
        print(f'Database creation error: {e}')
        return

    print('Starting corrected migration...')

    with sqlite3.connect(sqlite_db) as sqlite_conn:
        sqlite_cursor = sqlite_conn.cursor()

        # Get table list
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in sqlite_cursor.fetchall()]

        with psycopg2.connect(**pg_config) as pg_conn:
            pg_cursor = pg_conn.cursor()

            # Create legal instrument schema first
            legal_schema = '''
        -- Legal Instruments Master Table
        CREATE TABLE IF NOT EXISTS legal_instruments (
            id SERIAL PRIMARY KEY,
            instrument_code VARCHAR(100) UNIQUE NOT NULL,
            instrument_type TEXT CHECK (instrument_type IN ('SEPP', 'LEP', 'DCP', 'REP', 'SREP')) NOT NULL,
            legal_precedence INTEGER NOT NULL,
            title TEXT NOT NULL,
            gazettal_date DATE,
            effective_date DATE,
            status TEXT CHECK (status IN ('current', 'repealed', 'superseded', 'draft')) DEFAULT 'current',
            version_number VARCHAR(20),
            parent_instrument_id INTEGER REFERENCES legal_instruments(id),
            jurisdiction TEXT,
            authority TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Legal Precedence Index
        CREATE INDEX IF NOT EXISTS idx_legal_instruments_precedence
        ON legal_instruments(legal_precedence, instrument_type);

        -- Status Index
        CREATE INDEX IF NOT EXISTS idx_legal_instruments_status
        ON legal_instruments(status, effective_date);

        -- Instrument Relationships (SEPP overrides LEP, etc.)
        CREATE TABLE IF NOT EXISTS instrument_relationships (
            id SERIAL PRIMARY KEY,
            superior_instrument_id INTEGER REFERENCES legal_instruments(id),
            subordinate_instrument_id INTEGER REFERENCES legal_instruments(id),
            relationship_type TEXT CHECK (relationship_type IN ('overrides', 'supplements', 'amends', 'repeals')),
            scope_description TEXT,
            confidence_score DECIMAL(5,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Zone Classifications
        CREATE TABLE IF NOT EXISTS zone_classifications (
            id SERIAL PRIMARY KEY,
            zone_code VARCHAR(20) UNIQUE NOT NULL,
            zone_name TEXT NOT NULL,
            zone_category TEXT,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE
        );

        -- Development Types Registry
        CREATE TABLE IF NOT EXISTS development_types (
            id SERIAL PRIMARY KEY,
            type_code VARCHAR(100) UNIQUE NOT NULL,
            type_name TEXT NOT NULL,
            category TEXT,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE
        );
        '''

            pg_cursor.execute(legal_schema)

            for table_name in tables:
                print(f'Migrating {table_name}...')

                # Get table structure
                sqlite_cursor.execute(f'PRAGMA table_info({table_name})')
                columns = sqlite_cursor.fetchall()

                # Drop existing table if exists
                pg_cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')

                # Create table with correct types
                create_sql = f'CREATE TABLE "{table_name}" ('
                column_defs = []

                for col in columns:
                    col_id, col_name, sqlite_type, not_null, default_value, pk = col
                    pg_type = map_sqlite_to_postgresql_type(sqlite_type, col_name)

                    col_def = f'"{col_name}" {pg_type}'

                    if pk:
                        if pg_type == 'INTEGER':
                            col_def = f'"{col_name}" SERIAL PRIMARY KEY'
                        else:
                            col_def += ' PRIMARY KEY'
                    # Skip NOT NULL constraints to avoid migration issues with existing data

                    if default_value and not pk and str(default_value).strip():
                        try:
                            if pg_type in ['TEXT', 'VARCHAR']:
                                # Escape single quotes in string defaults
                                escaped_default = str(default_value).replace("'", "''")
                                col_def += f" DEFAULT '{escaped_default}'"
                            elif pg_type == 'BOOLEAN':
                                # Handle boolean defaults
                                if str(default_value).lower() in ['1', 'true', 't', 'yes']:
                                    col_def += " DEFAULT TRUE"
                                else:
                                    col_def += " DEFAULT FALSE"
                            else:
                                col_def += f" DEFAULT {default_value}"
                        except Exception as e:
                            print(f"Warning: Skipping default for {col_name}: {e}")

                    column_defs.append(col_def)

                create_sql += ', '.join(column_defs) + ')'
                pg_cursor.execute(create_sql)

                # Migrate data with proper type conversion
                sqlite_cursor.execute(f'SELECT * FROM "{table_name}"')
                data = sqlite_cursor.fetchall()

                if data:
                    # Get column names for INSERT
                    col_names = [col[1] for col in columns]
                    placeholders = ', '.join(['%s'] * len(col_names))
                    column_names = ", ".join([f'"{col}"' for col in col_names])
                    insert_sql = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'

                    # Convert data with proper typing
                    converted_data = []
                    for row in data:
                        converted_row = []
                        for i, (value, col_info) in enumerate(zip(row, columns)):
                            col_name = col_info[1]
                            sqlite_type = col_info[2]
                            pg_type = map_sqlite_to_postgresql_type(sqlite_type, col_name)

                            # Convert value based on target type
                            if value is None:
                                converted_row.append(None)
                            elif pg_type in ['INTEGER', 'SERIAL']:
                                try:
                                    converted_row.append(int(float(str(value))))
                                except (ValueError, TypeError):
                                    converted_row.append(None)
                            elif pg_type in ['DECIMAL', 'NUMERIC']:
                                try:
                                    # Only convert if value looks numeric
                                    str_value = str(value).strip()
                                    if str_value.replace('.', '').replace('-', '').isdigit():
                                        converted_row.append(float(str_value))
                                    else:
                                        # Non-numeric data - convert to NULL
                                        converted_row.append(None)
                                except (ValueError, TypeError):
                                    converted_row.append(None)
                            elif pg_type == 'BOOLEAN':
                                if isinstance(value, str):
                                    converted_row.append(value.lower() in ['true', '1', 'yes', 't'])
                                else:
                                    converted_row.append(bool(value))
                            elif pg_type in ['TIMESTAMP', 'DATE']:
                                if value and str(value) != '':
                                    try:
                                        # Handle Unix timestamp
                                        if isinstance(value, (int, float)) or str(value).replace('.', '').isdigit():
                                            timestamp = float(value)
                                            converted_row.append(datetime.fromtimestamp(timestamp).isoformat())
                                        else:
                                            # Handle string datetime
                                            converted_row.append(str(value))
                                    except (ValueError, OverflowError, OSError):
                                        converted_row.append(None)
                                else:
                                    converted_row.append(None)
                            else:
                                converted_row.append(str(value) if value is not None else None)

                        converted_data.append(tuple(converted_row))

                    # Insert converted data
                    if table_name == 'verified_compliance_rules' and converted_data:
                        print(f"DEBUG: First row of {table_name}: {converted_data[0]}")
                        print(f"DEBUG: Column names: {col_names}")
                    pg_cursor.executemany(insert_sql, converted_data)

                print(f'  Migrated {len(data) if data else 0} records')

            # Add foreign key constraints after all tables are created
            add_foreign_keys(sqlite_conn, pg_cursor)

            # Create additional indexes
            create_performance_indexes(pg_cursor)

            pg_conn.commit()

    print('Migration completed successfully!')

def map_sqlite_to_postgresql_type(sqlite_type, column_name=None):
    """Proper type mapping"""

    clean_type = sqlite_type.upper().strip() if sqlite_type else 'TEXT'

    # Special column-based mapping
    if column_name:
        col_lower = column_name.lower()
        if col_lower.endswith('_id') and col_lower != 'document_id':
            return 'INTEGER'
        if 'timestamp' in col_lower or 'created_at' in col_lower:
            return 'TIMESTAMP'
        if col_lower in ['page_number', 'text_level', 'precedence', 'level']:
            return 'INTEGER'
        # Force text for status/verification columns that contain text values
        if col_lower in ['verified_status', 'status', 'verification_method', 'verified', 'method', 'confidence']:
            return 'TEXT'
        # Only numeric confidence/score columns
        if ('confidence_score' in col_lower or 'quality_score' in col_lower) and col_lower not in ['confidence']:
            return 'DECIMAL(5,4)'

    type_mapping = {
        'INTEGER': 'INTEGER',
        'REAL': 'DECIMAL(10,4)',
        'BOOLEAN': 'BOOLEAN',
        'DATETIME': 'TIMESTAMP',
        'TIMESTAMP': 'TIMESTAMP',
        'TEXT': 'TEXT'
    }

    return type_mapping.get(clean_type, 'TEXT')

def add_foreign_keys(sqlite_conn, pg_cursor):
    """Add foreign key constraints based on SQLite schema"""

    # Key relationships we know exist
    foreign_keys = [
        {
            'table': 'development_controls',
            'column': 'provision_id',
            'ref_table': 'regulatory_provisions',
            'ref_column': 'id'
        },
        {
            'table': 'sepp_lep_overrides',
            'column': 'sepp_provision_id',
            'ref_table': 'regulatory_provisions',
            'ref_column': 'id'
        },
        {
            'table': 'quantitative_standards',
            'column': 'provision_id',
            'ref_table': 'regulatory_provisions',
            'ref_column': 'id'
        }
    ]

    for fk in foreign_keys:
        try:
            constraint_name = f'fk_{fk["table"]}_{fk["column"]}'
            alter_sql = f'''
                ALTER TABLE "{fk["table"]}"
                ADD CONSTRAINT {constraint_name}
                FOREIGN KEY ("{fk["column"]}")
                REFERENCES "{fk["ref_table"]}"("{fk["ref_column"]}")
                ON DELETE CASCADE
            '''
            pg_cursor.execute(alter_sql)
            print(f'Added foreign key: {constraint_name}')
        except Exception as e:
            print(f'Warning: Could not add FK {constraint_name}: {e}')

def create_performance_indexes(pg_cursor):
    """Create indexes for better performance"""

    indexes = [
        'CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_document ON regulatory_provisions(document_id)',
        'CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_zone ON regulatory_provisions(zone)',
        'CREATE INDEX IF NOT EXISTS idx_development_controls_type ON development_controls(control_type)',
        'CREATE INDEX IF NOT EXISTS idx_development_controls_zone ON development_controls(zone_applicable)',
        'CREATE INDEX IF NOT EXISTS idx_sepp_overrides_provision ON sepp_lep_overrides(sepp_provision_id)',
        'CREATE INDEX IF NOT EXISTS idx_kg_relationships_subject ON kg_relationships(subject_entity_id)',
        'CREATE INDEX IF NOT EXISTS idx_kg_relationships_object ON kg_relationships(object_entity_id)'
    ]

    for index_sql in indexes:
        try:
            pg_cursor.execute(index_sql)
        except Exception as e:
            print(f'Warning: Could not create index: {e}')

if __name__ == "__main__":
    migrate_with_correct_types()
        