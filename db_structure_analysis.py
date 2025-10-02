#!/usr/bin/env python3
"""
Database Structure Analysis for NSW Planning Data
Analyzes all tables and their content for planner research deployment
"""

import sqlite3
import json

def analyze_database_structure():
    conn = sqlite3.connect('nsw_planning.db')
    cur = conn.cursor()

    # Get all tables
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()

    analysis = {
        'total_tables': len(tables),
        'tables': []
    }

    for table_name in tables:
        table = table_name[0]
        try:
            # Get row count
            count = cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]

            # Get column info
            cols = cur.execute(f'PRAGMA table_info({table})').fetchall()
            columns = [{'name': col[1], 'type': col[2]} for col in cols]

            # Sample some data if table has records
            sample_data = []
            if count > 0:
                try:
                    sample = cur.execute(f'SELECT * FROM {table} LIMIT 2').fetchall()
                    sample_data = [list(row) for row in sample]
                except:
                    sample_data = []

            table_info = {
                'name': table,
                'row_count': count,
                'columns': columns,
                'sample_data': sample_data[:1] if sample_data else []  # Just first row
            }

            analysis['tables'].append(table_info)

        except Exception as e:
            analysis['tables'].append({
                'name': table,
                'row_count': 'ERROR',
                'error': str(e),
                'columns': [],
                'sample_data': []
            })

    # Sort by row count
    analysis['tables'].sort(key=lambda x: x['row_count'] if isinstance(x['row_count'], int) else 0, reverse=True)

    conn.close()
    return analysis

def identify_planner_relevant_tables(analysis):
    """Identify which tables are most relevant for planner research"""

    planner_relevant = {
        'provision_text': [],
        'development_rules': [],
        'spatial_mapping': [],
        'compliance_logic': [],
        'reference_data': []
    }

    for table in analysis['tables']:
        table_name = table['name'].lower()
        columns = [col['name'].lower() for col in table['columns']]

        # Categorize tables by planner research value
        if any(keyword in table_name for keyword in ['provision', 'regulatory', 'clause']):
            if table['row_count'] > 0:
                planner_relevant['provision_text'].append(table)

        elif any(keyword in table_name for keyword in ['development', 'control', 'setback', 'zone']):
            if table['row_count'] > 0:
                planner_relevant['development_rules'].append(table)

        elif any(keyword in table_name for keyword in ['kg_', 'relationship', 'entity']):
            if table['row_count'] > 0:
                planner_relevant['spatial_mapping'].append(table)

        elif any(keyword in table_name for keyword in ['compliance', 'verification', 'validation']):
            if table['row_count'] > 0:
                planner_relevant['compliance_logic'].append(table)

        elif any(keyword in table_name for keyword in ['document', 'sepp', 'override']):
            if table['row_count'] > 0:
                planner_relevant['reference_data'].append(table)

    return planner_relevant

if __name__ == '__main__':
    print("=== NSW PLANNING DATABASE STRUCTURE ANALYSIS ===\n")

    analysis = analyze_database_structure()

    print(f"Total tables: {analysis['total_tables']}\n")

    print("=== ALL TABLES (by row count) ===")
    for table in analysis['tables']:
        print(f"{table['name']}: {table['row_count']} records")
        if table['columns']:
            col_names = [col['name'] for col in table['columns'][:6]]
            print(f"  Columns: {', '.join(col_names)}")
        print()

    print("\n=== PLANNER RESEARCH RELEVANCE ===")
    relevant = identify_planner_relevant_tables(analysis)

    for category, tables in relevant.items():
        if tables:
            print(f"\n{category.upper().replace('_', ' ')}:")
            for table in tables:
                print(f"  {table['name']}: {table['row_count']} records")
                if table['sample_data']:
                    print(f"    Sample: {str(table['sample_data'][0])[:100]}...")

    # Save full analysis to file
    with open('database_structure_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2, default=str)

    print(f"\nFull analysis saved to: database_structure_analysis.json")