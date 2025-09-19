#!/usr/bin/env python3
"""
Analyze all SQLite databases to find the best source for investigation
"""

from db_config import get_connection  # Unified PostgreSQL connection
import os
from datetime import datetime
from pathlib import Path

def analyze_sqlite_database(db_path):
    """Analyze a single SQLite database"""
    
    print(f"\n{'='*60}")
    print(f"ANALYZING: {db_path}")
    print(f"{'='*60}")
    
    try:
        # Check file info
        stat = Path(db_path).stat()
        print(f"File size: {stat.st_size:,} bytes")
        print(f"Modified: {datetime.fromtimestamp(stat.st_mtime)}")
        
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Get all tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cur.fetchall()]
        print(f"Tables ({len(tables)}): {', '.join(tables)}")
        
        # Focus on regulatory_provisions if it exists
        if 'regulatory_provisions' in tables:
            print(f"\n--- REGULATORY_PROVISIONS ANALYSIS ---")
            
            # Total count
            cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
            total = cur.fetchone()[0]
            print(f"Total provisions: {total:,}")
            
            # Check for zones
            cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL")
            with_zones = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NULL") 
            null_zones = cur.fetchone()[0]
            print(f"With zones: {with_zones:,} ({with_zones/total*100:.1f}%)")
            print(f"NULL zones: {null_zones:,} ({null_zones/total*100:.1f}%)")
            
            # Zone distribution
            cur.execute("SELECT zone, COUNT(*) as count FROM regulatory_provisions WHERE zone IS NOT NULL GROUP BY zone ORDER BY count DESC LIMIT 10")
            zones = cur.fetchall()
            print(f"Top zones:")
            for zone, count in zones:
                print(f"  {zone}: {count:,}")
            
            # Check classification_confidence (the suspected culprit)
            cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE classification_confidence IS NULL")
            null_confidence = cur.fetchone()[0]
            print(f"NULL classification_confidence: {null_confidence:,} ({null_confidence/total*100:.1f}%)")
            
            # Check other key fields
            cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_type IS NULL")
            null_type = cur.fetchone()[0]
            print(f"NULL provision_type: {null_type:,} ({null_type/total*100:.1f}%)")
            
            cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE ref_number IS NULL")
            null_ref = cur.fetchone()[0] 
            print(f"NULL ref_number: {null_ref:,} ({null_ref/total*100:.1f}%)")
            
            # Sample data to see actual values
            print(f"\n--- SAMPLE DATA ---")
            cur.execute("SELECT id, zone, provision_type, classification_confidence, ref_number FROM regulatory_provisions WHERE zone IS NOT NULL LIMIT 3")
            samples = cur.fetchall()
            for sample in samples:
                print(f"ID {sample[0]}: zone={sample[1]}, type={sample[2]}, conf={sample[3]}, ref={sample[4]}")
        
        # Check quantitative_standards table (used in migration)
        if 'quantitative_standards' in tables:
            print(f"\n--- QUANTITATIVE_STANDARDS ANALYSIS ---")
            cur.execute("SELECT COUNT(*) FROM quantitative_standards")
            qs_total = cur.fetchone()[0]
            print(f"Total quantitative standards: {qs_total:,}")
            
            cur.execute("SELECT COUNT(*) FROM quantitative_standards WHERE confidence_score IS NULL")
            null_qs_conf = cur.fetchone()[0]
            print(f"NULL confidence_score: {null_qs_conf:,} ({null_qs_conf/qs_total*100:.1f}%)")
        
        conn.close()
        
        return {
            'path': db_path,
            'accessible': True,
            'file_size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'total_provisions': total if 'regulatory_provisions' in tables else 0,
            'provisions_with_zones': with_zones if 'regulatory_provisions' in tables else 0,
            'null_classification_confidence': null_confidence if 'regulatory_provisions' in tables else 0,
            'tables': tables,
            'recommended': False
        }
        
    except Exception as e:
        print(f"ERROR: {e}")
        return {
            'path': db_path,
            'accessible': False,
            'error': str(e)
        }

def main():
    """Analyze all SQLite databases"""
    
    print("SQLITE DATABASE ANALYSIS")
    print("Analyzing all .db files to find best data source...")
    
    # Find all .db files
    db_files = []
    for file in os.listdir('.'):
        if file.endswith('.db'):
            db_files.append(file)
    
    print(f"Found {len(db_files)} SQLite databases:")
    for db in db_files:
        print(f"  {db}")
    
    # Analyze each database
    results = []
    for db_file in db_files:
        result = analyze_sqlite_database(db_file)
        results.append(result)
    
    # Generate recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    
    accessible_dbs = [r for r in results if r.get('accessible', False)]
    
    if not accessible_dbs:
        print("❌ No accessible databases found!")
        return False
    
    # Find the database with the most provisions
    best_db = max(accessible_dbs, key=lambda x: x.get('total_provisions', 0))
    best_db['recommended'] = True
    
    print(f"RECOMMENDED DATABASE: {best_db['path']}")
    print(f"  Total provisions: {best_db['total_provisions']:,}")
    print(f"  Provisions with zones: {best_db['provisions_with_zones']:,}")
    print(f"  NULL classification_confidence: {best_db['null_classification_confidence']:,}")
    print(f"  File size: {best_db['file_size']:,} bytes")
    print(f"  Last modified: {best_db['modified']}")
    
    # Check data quality
    if best_db['null_classification_confidence'] == 0:
        print(f"✅ EXCELLENT: No NULL classification_confidence values!")
        print(f"   This database may not have the '0' error issue")
    elif best_db['null_classification_confidence'] < best_db['total_provisions'] * 0.1:
        print(f"⚠️  GOOD: Only {best_db['null_classification_confidence']/best_db['total_provisions']*100:.1f}% NULL classification_confidence")
    else:
        print(f"🚨 POOR: {best_db['null_classification_confidence']/best_db['total_provisions']*100:.1f}% NULL classification_confidence")
        print(f"   This is likely the source of the '0' errors")
    
    # Summary comparison
    print(f"\n--- ALL DATABASES SUMMARY ---")
    for result in accessible_dbs:
        status = "⭐ RECOMMENDED" if result.get('recommended') else ""
        print(f"{result['path']}: {result['total_provisions']:,} provisions, {result['provisions_with_zones']:,} with zones {status}")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)