#!/usr/bin/env python3
import sqlite3
import json

def verify_database():
    conn = sqlite3.connect('nsw_planning.db')
    cur = conn.cursor()
    
    print("=== ACTUAL DATABASE CONTENT VERIFICATION ===")
    
    # 1. Count setback records
    setbacks = cur.execute("SELECT COUNT(*) FROM development_controls WHERE control_type = 'setback'").fetchone()[0]
    print(f"Total setback records: {setbacks}")
    
    # 2. Show sample setback values
    sample_setbacks = cur.execute("""
        SELECT dc.value_numeric, dc.value_text, rp.document_id 
        FROM development_controls dc 
        JOIN regulatory_provisions rp ON dc.provision_id = rp.id 
        WHERE dc.control_type = 'setback' AND dc.value_numeric > 0
        LIMIT 5
    """).fetchall()
    
    print("Sample setback values:")
    for val_num, val_text, doc in sample_setbacks:
        print(f"  {val_num}m - '{val_text}' from {doc[:50]}...")
    
    # 3. Count connected requirements
    total_provisions = cur.execute("SELECT COUNT(*) FROM regulatory_provisions").fetchone()[0]
    print(f"Total regulatory provisions: {total_provisions}")
    
    # 4. Count development controls by type
    control_types = cur.execute("""
        SELECT control_type, COUNT(*) as count 
        FROM development_controls 
        GROUP BY control_type 
        ORDER BY count DESC
    """).fetchall()
    
    print("Development controls by type:")
    for ctrl_type, count in control_types:
        print(f"  {ctrl_type}: {count}")
    
    # 5. Check visual elements table
    try:
        visual_count = cur.execute("SELECT COUNT(*) FROM visual_elements").fetchone()[0]
        print(f"Total visual elements: {visual_count}")
        
        # Sample visual elements
        visuals = cur.execute("SELECT visual_type, file_path FROM visual_elements LIMIT 3").fetchall()
        if visuals:
            print("Sample visual elements:")
            for vtype, path in visuals:
                print(f"  {vtype}: {path}")
    except:
        print("Visual elements table not found or empty")
    
    conn.close()
    return {
        'setback_count': setbacks,
        'total_provisions': total_provisions,
        'sample_setbacks': sample_setbacks
    }

if __name__ == "__main__":
    verify_database()