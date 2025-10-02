#!/usr/bin/env python3

import sqlite3
import os
import glob

def get_db_info(db_path):
    """Get information about an SQLite database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        total_rows = 0
        table_info = []

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                total_rows += count
                if count > 0:
                    table_info.append((table, count))
            except Exception as e:
                table_info.append((table, f"Error: {e}"))

        conn.close()

        return {
            'path': db_path,
            'tables': len(tables),
            'total_rows': total_rows,
            'table_info': table_info
        }

    except Exception as e:
        return {
            'path': db_path,
            'error': str(e)
        }

def check_all_sqlite_dbs():
    """Check all SQLite databases for data"""

    # Find all SQLite databases
    db_patterns = [
        '*.db',
        '*.sqlite',
        '*.sqlite3',
        'backups/*.db',
        'backups/*/*.db',
        'PRPs/*/*.db',
        'services/*.db'
    ]

    db_files = []
    for pattern in db_patterns:
        db_files.extend(glob.glob(pattern))

    print('=== SQLITE DATABASE ANALYSIS ===')
    print(f'Found {len(db_files)} SQLite database files')
    print()

    db_results = []

    for db_file in db_files:
        if os.path.exists(db_file):
            size_mb = os.path.getsize(db_file) / (1024 * 1024)
            print(f'=== {db_file} ===')
            print(f'File size: {size_mb:.2f} MB')

            info = get_db_info(db_file)
            db_results.append(info)

            if 'error' in info:
                print(f'Error: {info["error"]}')
            else:
                print(f'Tables: {info["tables"]}')
                print(f'Total rows: {info["total_rows"]:,}')

                if info['table_info']:
                    print('Populated tables:')
                    for table, count in sorted(info['table_info'], key=lambda x: x[1] if isinstance(x[1], int) else 0, reverse=True):
                        if isinstance(count, int) and count > 0:
                            print(f'  {table}: {count:,} rows')
            print()

    # Find the database with the most data
    max_rows = 0
    best_db = None

    for db in db_results:
        if 'total_rows' in db and db['total_rows'] > max_rows:
            max_rows = db['total_rows']
            best_db = db

    if best_db:
        print('=== LARGEST DATABASE ===')
        print(f'Path: {best_db["path"]}')
        print(f'Total rows: {best_db["total_rows"]:,}')
        print(f'Tables: {best_db["tables"]}')
        print()

        # Get detailed info about the largest database
        print('=== DETAILED ANALYSIS OF LARGEST DATABASE ===')
        analyze_detailed_db(best_db['path'])

def analyze_detailed_db(db_path):
    """Analyze the largest database in detail"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables with row counts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]

                if count > 0:
                    print(f'\n--- TABLE: {table} ---')
                    print(f'Rows: {count:,}')

                    # Get column info
                    cursor.execute(f"PRAGMA table_info(`{table}`)")
                    columns = cursor.fetchall()
                    print(f'Columns: {", ".join([col[1] for col in columns[:5]])}...')

                    # Get sample data
                    cursor.execute(f"SELECT * FROM `{table}` LIMIT 2")
                    samples = cursor.fetchall()
                    if samples:
                        print('Sample data:')
                        for i, sample in enumerate(samples):
                            print(f'  Row {i+1}: {str(sample)[:100]}...')

            except Exception as e:
                print(f'Error analyzing table {table}: {e}')

        conn.close()

    except Exception as e:
        print(f'Error analyzing database: {e}')

if __name__ == "__main__":
    check_all_sqlite_dbs()