#!/usr/bin/env python3

import sqlite3

def check_connected_requirements():
    conn = sqlite3.connect('nsw_planning.db')
    cur = conn.cursor()
    
    # Check what documents actually have development controls
    docs_with_controls = cur.execute("""
        SELECT rp.document_id, dc.control_type, COUNT(*) as count
        FROM regulatory_provisions rp
        JOIN development_controls dc ON rp.id = dc.provision_id
        GROUP BY rp.document_id, dc.control_type
        ORDER BY count DESC
    """).fetchall()
    
    print("Documents with development controls:")
    for doc, control_type, count in docs_with_controls:
        print(f"  {doc} - {control_type}: {count}")
    
    print("\nSetback documents specifically:")
    setback_docs = cur.execute("""
        SELECT DISTINCT rp.document_id, rp.section_header
        FROM regulatory_provisions rp
        JOIN development_controls dc ON rp.id = dc.provision_id
        WHERE dc.control_type = 'setback'
    """).fetchall()
    
    for doc, section in setback_docs:
        print(f"  {doc} / {section}")
    
    # Check for any non-setback controls in these sections
    print("\nNon-setback controls in setback document sections:")
    for doc, section in setback_docs[:3]:  # Check first 3
        other_controls = cur.execute("""
            SELECT dc.control_type, dc.control_subtype, COUNT(*) as count
            FROM development_controls dc
            JOIN regulatory_provisions rp ON dc.provision_id = rp.id  
            WHERE rp.document_id = ? AND rp.section_header = ?
              AND dc.control_type != 'setback'
            GROUP BY dc.control_type, dc.control_subtype
        """, (doc, section)).fetchall()
        
        if other_controls:
            print(f"  {doc}/{section}:")
            for ctrl_type, subtype, count in other_controls:
                print(f"    {ctrl_type} ({subtype}): {count}")
        else:
            print(f"  {doc}/{section}: No other controls found")
    
    conn.close()

if __name__ == "__main__":
    check_connected_requirements()