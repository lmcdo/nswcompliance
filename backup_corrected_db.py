#!/usr/bin/env python3
"""
Backup the corrected PostgreSQL database safely
"""

import subprocess
import os
from datetime import datetime

def backup_corrected_database():
    """Create backup of nsw_planning_corrected database"""

    print('=== BACKING UP CORRECTED DATABASE ===')
    print()

    # Create backup directory if it doesn't exist
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f'Created backup directory: {backup_dir}')

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'{backup_dir}/nsw_planning_corrected_backup_{timestamp}.sql'

    print(f'Creating backup: {backup_filename}')

    try:
        # Use pg_dump to create backup
        # Note: This requires pg_dump to be in PATH or specify full path
        cmd = [
            'pg_dump',
            '-h', 'localhost',
            '-U', 'postgres',
            '-d', 'nsw_planning_corrected',
            '-f', backup_filename,
            '--verbose',
            '--create',
            '--clean'
        ]

        print('Running pg_dump...')
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Check if backup file was created and has content
            if os.path.exists(backup_filename) and os.path.getsize(backup_filename) > 0:
                file_size = os.path.getsize(backup_filename) / (1024 * 1024)  # MB
                print(f'SUCCESS: Backup created successfully')
                print(f'  File: {backup_filename}')
                print(f'  Size: {file_size:.2f} MB')

                # Also create a compressed version
                try:
                    import gzip
                    compressed_filename = f'{backup_filename}.gz'
                    with open(backup_filename, 'rb') as f_in:
                        with gzip.open(compressed_filename, 'wb') as f_out:
                            f_out.writelines(f_in)

                    compressed_size = os.path.getsize(compressed_filename) / (1024 * 1024)
                    print(f'  Compressed: {compressed_filename}')
                    print(f'  Compressed size: {compressed_size:.2f} MB')

                except Exception as e:
                    print(f'Warning: Could not create compressed backup: {e}')

                return True
            else:
                print('ERROR: Backup file was not created or is empty')
                return False
        else:
            print(f'ERROR: pg_dump failed with return code {result.returncode}')
            print(f'Error output: {result.stderr}')
            return False

    except FileNotFoundError:
        print('ERROR: pg_dump command not found')
        print('Alternative: Manual backup using database connection')
        return create_manual_backup(backup_filename)
    except Exception as e:
        print(f'ERROR: Backup failed - {str(e)}')
        return False

def create_manual_backup(backup_filename):
    """Create backup using Python database connection if pg_dump not available"""

    print('Attempting manual backup using Python...')

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning_corrected',
            user='postgres',
            password='postgres',
            port='5432'
        )

        with open(backup_filename, 'w', encoding='utf-8') as backup_file:
            backup_file.write('-- PostgreSQL Database Backup\n')
            backup_file.write('-- Database: nsw_planning_corrected\n')
            backup_file.write(f'-- Created: {datetime.now()}\n')
            backup_file.write('-- Method: Python manual backup\n\n')

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get all table names
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row['table_name'] for row in cursor.fetchall()]

            print(f'Backing up {len(tables)} tables...')

            for table in tables:
                print(f'  Backing up table: {table}')

                # Get table structure
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """)
                columns = cursor.fetchall()

                # Write CREATE TABLE statement
                backup_file.write(f'\n-- Table: {table}\n')
                backup_file.write(f'DROP TABLE IF EXISTS "{table}" CASCADE;\n')

                col_defs = []
                for col in columns:
                    col_def = f'"{col["column_name"]}" {col["data_type"]}'
                    if col["is_nullable"] == 'NO':
                        col_def += ' NOT NULL'
                    if col["column_default"]:
                        col_def += f' DEFAULT {col["column_default"]}'
                    col_defs.append(col_def)

                backup_file.write(f'CREATE TABLE "{table}" (\n')
                backup_file.write(',\n'.join([f'  {col_def}' for col_def in col_defs]))
                backup_file.write('\n);\n\n')

                # Get record count for progress
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                record_count = cursor.fetchone()[0]

                if record_count > 0:
                    print(f'    {record_count} records')
                    backup_file.write(f'-- Data for table {table} ({record_count} records)\n')

                    # For large tables, process in chunks
                    chunk_size = 1000
                    offset = 0

                    while offset < record_count:
                        cursor.execute(f'SELECT * FROM "{table}" LIMIT {chunk_size} OFFSET {offset}')
                        rows = cursor.fetchall()

                        if rows:
                            col_names = list(rows[0].keys())
                            col_names_quoted = [f'"{col}"' for col in col_names]
                            backup_file.write(f'INSERT INTO "{table}" ({", ".join(col_names_quoted)}) VALUES\n')

                            values_list = []
                            for row in rows:
                                values = []
                                for col in col_names:
                                    value = row[col]
                                    if value is None:
                                        values.append('NULL')
                                    elif isinstance(value, str):
                                        # Escape single quotes
                                        escaped = value.replace("'", "''")
                                        values.append(f"'{escaped}'")
                                    else:
                                        values.append(str(value))
                                values_list.append(f'({", ".join(values)})')

                            backup_file.write(',\n'.join(values_list))
                            backup_file.write(';\n\n')

                        offset += chunk_size

        cursor.close()
        conn.close()

        # Check backup file size
        if os.path.exists(backup_filename) and os.path.getsize(backup_filename) > 0:
            file_size = os.path.getsize(backup_filename) / (1024 * 1024)
            print(f'Manual backup completed: {file_size:.2f} MB')
            return True
        else:
            print('ERROR: Manual backup failed')
            return False

    except Exception as e:
        print(f'ERROR: Manual backup failed - {str(e)}')
        return False

if __name__ == "__main__":
    success = backup_corrected_database()
    if success:
        print('\nDatabase backup completed successfully!')
    else:
        print('\nDatabase backup FAILED!')
        exit(1)