#!/usr/bin/env python3
"""
Check document types in SQLite source database to identify SEPP/LEP provisions
"""

import sqlite3
import pandas as pd
from collections import Counter

def analyze_document_types():
    """Analyze document types and authority levels in the source database"""
    
    # Connect to the database
    conn = sqlite3.connect('nsw_planning.db')
    
    try:
        # First, check what tables exist
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print('Available tables:')
        for table in tables:
            print(f'  - {table[0]}')
        
        # Check if regulatory_provisions table exists
        table_name = None
        if any('regulatory_provisions' in table[0] for table in tables):
            # Find the correct table name
            for table in tables:
                if 'regulatory_provisions' in table[0]:
                    table_name = table[0]
                    print(f'\nUsing table: {table_name}')
                    break
        
        if not table_name:
            print("No regulatory_provisions table found!")
            return
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f'\nColumns in {table_name}:')
        for col in columns:
            print(f'  - {col[1]} ({col[2]})')
        
        # Check distinct document_id values
        print(f'\n=== DOCUMENT ID ANALYSIS ===')
        cursor.execute(f"SELECT DISTINCT document_id FROM {table_name} ORDER BY document_id")
        document_ids = cursor.fetchall()
        
        print(f'Total distinct document_ids: {len(document_ids)}')
        print('\nAll document IDs:')
        
        sepp_docs = []
        lep_docs = []
        dcp_docs = []
        other_docs = []
        
        for doc_id in document_ids:
            doc_str = str(doc_id[0]) if doc_id[0] else 'NULL'
            print(f'  - {doc_str}')
            
            # Categorize documents
            doc_upper = doc_str.upper()
            if 'SEPP' in doc_upper:
                sepp_docs.append(doc_str)
            elif 'LEP' in doc_upper:
                lep_docs.append(doc_str)
            elif 'DCP' in doc_upper:
                dcp_docs.append(doc_str)
            else:
                other_docs.append(doc_str)
        
        # Print categorized results
        print(f'\n=== DOCUMENT CATEGORIZATION ===')
        print(f'SEPP documents: {len(sepp_docs)}')
        for doc in sepp_docs:
            print(f'  - {doc}')
            
        print(f'\nLEP documents: {len(lep_docs)}')
        for doc in lep_docs:
            print(f'  - {doc}')
            
        print(f'\nDCP documents: {len(dcp_docs)}')
        for doc in dcp_docs:
            print(f'  - {doc}')
            
        print(f'\nOther documents: {len(other_docs)}')
        for doc in other_docs:
            print(f'  - {doc}')
        
        # Count provisions by document type
        print(f'\n=== PROVISION COUNTS BY DOCUMENT TYPE ===')
        
        # Count SEPP provisions
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE document_id LIKE '%SEPP%'")
        sepp_count = cursor.fetchone()[0]
        print(f'SEPP provisions: {sepp_count}')
        
        # Count LEP provisions
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE document_id LIKE '%LEP%'")
        lep_count = cursor.fetchone()[0]
        print(f'LEP provisions: {lep_count}')
        
        # Count DCP provisions  
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE document_id LIKE '%DCP%'")
        dcp_count = cursor.fetchone()[0]
        print(f'DCP provisions: {dcp_count}')
        
        # Total provisions
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]
        print(f'Total provisions: {total_count}')
        
        # Check if SEPP/LEP provisions have zone data
        if sepp_count > 0 or lep_count > 0:
            print(f'\n=== ZONE DATA ANALYSIS FOR SEPP/LEP ===')
            
            # Check what columns might contain zone information
            zone_columns = [col[1] for col in columns if 'zone' in col[1].lower() or 'land_use' in col[1].lower()]
            print(f'Potential zone columns: {zone_columns}')
            
            if zone_columns:
                for col in zone_columns:
                    # Check SEPP provisions with zone data
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE document_id LIKE '%SEPP%' AND {col} IS NOT NULL AND {col} != ''")
                    sepp_zone_count = cursor.fetchone()[0]
                    
                    # Check LEP provisions with zone data  
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE document_id LIKE '%LEP%' AND {col} IS NOT NULL AND {col} != ''")
                    lep_zone_count = cursor.fetchone()[0]
                    
                    print(f'SEPP provisions with {col} data: {sepp_zone_count}')
                    print(f'LEP provisions with {col} data: {lep_zone_count}')
            
            # Check for setback-related columns
            setback_columns = [col[1] for col in columns if 'setback' in col[1].lower() or 'distance' in col[1].lower() or 'height' in col[1].lower()]
            print(f'\nPotential setback columns: {setback_columns}')
            
            if setback_columns:
                for col in setback_columns:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE document_id LIKE '%SEPP%' AND {col} IS NOT NULL AND {col} != ''")
                    sepp_setback_count = cursor.fetchone()[0]
                    
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE document_id LIKE '%LEP%' AND {col} IS NOT NULL AND {col} != ''")
                    lep_setback_count = cursor.fetchone()[0]
                    
                    print(f'SEPP provisions with {col} data: {sepp_setback_count}')
                    print(f'LEP provisions with {col} data: {lep_setback_count}')
        
        # Sample some SEPP/LEP provisions to see their structure
        if sepp_count > 0:
            print(f'\n=== SAMPLE SEPP PROVISIONS ===')
            cursor.execute(f"SELECT * FROM {table_name} WHERE document_id LIKE '%SEPP%' LIMIT 3")
            sepp_samples = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            
            for i, sample in enumerate(sepp_samples):
                print(f'\nSEPP Sample {i+1}:')
                for j, value in enumerate(sample):
                    if value is not None and str(value).strip():
                        print(f'  {col_names[j]}: {value}')
        
        if lep_count > 0:
            print(f'\n=== SAMPLE LEP PROVISIONS ===')
            cursor.execute(f"SELECT * FROM {table_name} WHERE document_id LIKE '%LEP%' LIMIT 3")
            lep_samples = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            
            for i, sample in enumerate(lep_samples):
                print(f'\nLEP Sample {i+1}:')
                for j, value in enumerate(sample):
                    if value is not None and str(value).strip():
                        print(f'  {col_names[j]}: {value}')
                        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    analyze_document_types()