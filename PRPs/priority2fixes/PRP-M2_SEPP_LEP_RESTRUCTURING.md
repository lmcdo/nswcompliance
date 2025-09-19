# PRP-M2: SEPP/LEP Data Restructuring Engine

## Objective
Extract and organize SEPP/LEP provisions from regulatory_provisions into dedicated tables optimized for PRP-Q2 development pathway intelligence.

## Scope
**Input:** PostgreSQL regulatory_provisions (22,105 records)
**Output:** Dedicated sepp_provisions and lep_provisions tables
**Time:** 30 minutes
**Verification:** Authority-based data extraction with automated proof

## Data Identification Strategy

Based on previous analysis, SEPP/LEP data exists within regulatory_provisions but needs extraction based on document sources and provision patterns.

## Implementation

### Restructuring Script: `execute_prp_m2.py`

```python
#!/usr/bin/env python3
"""
PRP-M2: SEPP/LEP Data Restructuring Engine
Extracts SEPP/LEP provisions into dedicated tables for pathway intelligence
"""

import psycopg2
import json
from datetime import datetime
from db_config import get_connection

class PRP_M2_Restructuring:
    def __init__(self):
        self.conn = get_connection()
        self.restructuring_report = {
            'start_time': datetime.now().isoformat(),
            'extraction_results': {},
            'table_creation': {},
            'total_sepp_extracted': 0,
            'total_lep_extracted': 0,
            'status': 'IN_PROGRESS'
        }

    def create_sepp_provisions_table(self):
        """Create optimized SEPP provisions table"""
        cursor = self.conn.cursor()

        sepp_schema = '''
        CREATE TABLE IF NOT EXISTS sepp_provisions (
            id SERIAL PRIMARY KEY,
            original_provision_id INTEGER REFERENCES regulatory_provisions(id),
            sepp_type TEXT NOT NULL,  -- 'Exempt and Complying', 'Housing', etc.
            sepp_number TEXT,         -- SEPP number/identifier
            provision_category TEXT,  -- 'exempt', 'complying', 'prohibited'
            development_type TEXT,
            zone_applicability TEXT,
            provision_text TEXT NOT NULL,
            ref_number TEXT,
            page_number INTEGER,
            section_header TEXT,
            classification_confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            extraction_method TEXT DEFAULT 'prp_m2_auto'
        )
        '''

        cursor.execute('DROP TABLE IF EXISTS sepp_provisions CASCADE')
        cursor.execute(sepp_schema)
        self.conn.commit()

        self.restructuring_report['table_creation']['sepp_provisions'] = {
            'status': 'created',
            'timestamp': datetime.now().isoformat()
        }

        print("✓ SEPP provisions table created")

    def create_lep_provisions_table(self):
        """Create optimized LEP provisions table"""
        cursor = self.conn.cursor()

        lep_schema = '''
        CREATE TABLE IF NOT EXISTS lep_provisions (
            id SERIAL PRIMARY KEY,
            original_provision_id INTEGER REFERENCES regulatory_provisions(id),
            lep_name TEXT NOT NULL,     -- 'Inner West LEP 2022', etc.
            lep_zone TEXT,              -- R1, R2, B1, etc.
            provision_category TEXT,    -- 'permitted', 'prohibited', 'consent'
            development_type TEXT,
            provision_text TEXT NOT NULL,
            ref_number TEXT,
            page_number INTEGER,
            section_header TEXT,
            classification_confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            extraction_method TEXT DEFAULT 'prp_m2_auto'
        )
        '''

        cursor.execute('DROP TABLE IF EXISTS lep_provisions CASCADE')
        cursor.execute(lep_schema)
        self.conn.commit()

        self.restructuring_report['table_creation']['lep_provisions'] = {
            'status': 'created',
            'timestamp': datetime.now().isoformat()
        }

        print("✓ LEP provisions table created")

    def extract_sepp_provisions(self):
        """Extract SEPP provisions using document analysis and pattern matching"""
        cursor = self.conn.cursor()

        # Strategy 1: Extract by document source
        cursor.execute('''
            SELECT rp.*, d.pdf_name
            FROM regulatory_provisions rp
            JOIN documents d ON rp.document_id = d.id
            WHERE d.pdf_name ILIKE '%sepp%'
               OR d.document_type ILIKE '%sepp%'
               OR rp.provision_text ILIKE '%state environmental planning policy%'
               OR rp.section_header ILIKE '%sepp%'
        ''')

        sepp_candidates = cursor.fetchall()

        # Strategy 2: Pattern-based identification
        cursor.execute('''
            SELECT *
            FROM regulatory_provisions
            WHERE provision_text ILIKE '%exempt development%'
               OR provision_text ILIKE '%complying development%'
               OR provision_text ILIKE '%sepp%'
               OR provision_text ILIKE '%state environmental planning%'
               OR ref_number ILIKE '%sepp%'
        ''')

        pattern_candidates = cursor.fetchall()

        # Combine and deduplicate
        all_candidates = {}
        for row in sepp_candidates + pattern_candidates:
            all_candidates[row[0]] = row  # Use ID as key to deduplicate

        print(f"Found {len(all_candidates)} SEPP provision candidates")

        # Insert into sepp_provisions table
        insert_sql = '''
            INSERT INTO sepp_provisions (
                original_provision_id, sepp_type, provision_category,
                development_type, zone_applicability, provision_text,
                ref_number, page_number, section_header, classification_confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''

        sepp_insertions = 0

        for provision_id, row in all_candidates.items():
            # Extract SEPP type and category from text
            provision_text = row[4] or ''  # provision_text column
            ref_number = row[3] or ''      # ref_number column

            # Determine SEPP type
            sepp_type = 'Unknown'
            if 'exempt and complying' in provision_text.lower():
                sepp_type = 'Exempt and Complying'
            elif 'housing' in provision_text.lower() and 'sepp' in provision_text.lower():
                sepp_type = 'Housing'
            elif 'sepp' in provision_text.lower():
                sepp_type = 'General SEPP'

            # Determine provision category
            category = 'general'
            if 'exempt development' in provision_text.lower():
                category = 'exempt'
            elif 'complying development' in provision_text.lower():
                category = 'complying'
            elif 'prohibited' in provision_text.lower():
                category = 'prohibited'

            cursor.execute(insert_sql, (
                row[0],          # original_provision_id
                sepp_type,       # sepp_type
                category,        # provision_category
                row[6] or '',    # development_type
                row[5] or '',    # zone_applicability (zone column)
                row[4],          # provision_text
                row[3],          # ref_number
                row[7],          # page_number
                row[8],          # section_header
                row[13] or 0.8   # classification_confidence
            ))

            sepp_insertions += 1

        self.conn.commit()

        self.restructuring_report['extraction_results']['sepp_provisions'] = {
            'candidates_found': len(all_candidates),
            'records_extracted': sepp_insertions,
            'extraction_success': sepp_insertions > 0
        }

        self.restructuring_report['total_sepp_extracted'] = sepp_insertions

        print(f"✓ Extracted {sepp_insertions:,} SEPP provisions")

    def extract_lep_provisions(self):
        """Extract LEP provisions using document analysis and pattern matching"""
        cursor = self.conn.cursor()

        # Strategy 1: Extract by document source and patterns
        cursor.execute('''
            SELECT rp.*, d.pdf_name
            FROM regulatory_provisions rp
            JOIN documents d ON rp.document_id = d.id
            WHERE d.pdf_name ILIKE '%lep%'
               OR d.pdf_name ILIKE '%local environmental plan%'
               OR d.document_type ILIKE '%lep%'
               OR rp.provision_text ILIKE '%local environmental plan%'
               OR rp.section_header ILIKE '%lep%'
        ''')

        lep_candidates = cursor.fetchall()

        # Strategy 2: Zone-based identification
        cursor.execute('''
            SELECT *
            FROM regulatory_provisions
            WHERE zone IS NOT NULL
              AND zone != ''
              AND (zone SIMILAR TO '[A-Z][0-9]+'  -- R1, B1, etc.
                   OR provision_text ILIKE '%zoning%'
                   OR provision_text ILIKE '%zone%'
                   OR provision_text ILIKE '%land use%')
        ''')

        zone_candidates = cursor.fetchall()

        # Combine and deduplicate
        all_candidates = {}
        for row in lep_candidates + zone_candidates:
            all_candidates[row[0]] = row

        print(f"Found {len(all_candidates)} LEP provision candidates")

        # Insert into lep_provisions table
        insert_sql = '''
            INSERT INTO lep_provisions (
                original_provision_id, lep_name, lep_zone, provision_category,
                development_type, provision_text, ref_number, page_number,
                section_header, classification_confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''

        lep_insertions = 0

        for provision_id, row in all_candidates.items():
            provision_text = row[4] or ''
            zone = row[5] or ''

            # Determine LEP name
            lep_name = 'Inner West LEP'
            if 'ashfield' in provision_text.lower():
                lep_name = 'Ashfield LEP'
            elif 'leichhardt' in provision_text.lower():
                lep_name = 'Leichhardt LEP'
            elif 'marrickville' in provision_text.lower():
                lep_name = 'Marrickville LEP'

            # Determine provision category
            category = 'general'
            if 'permitted without consent' in provision_text.lower():
                category = 'permitted'
            elif 'permitted with consent' in provision_text.lower():
                category = 'consent'
            elif 'prohibited' in provision_text.lower():
                category = 'prohibited'

            cursor.execute(insert_sql, (
                row[0],          # original_provision_id
                lep_name,        # lep_name
                zone,            # lep_zone
                category,        # provision_category
                row[6] or '',    # development_type
                row[4],          # provision_text
                row[3],          # ref_number
                row[7],          # page_number
                row[8],          # section_header
                row[13] or 0.8   # classification_confidence
            ))

            lep_insertions += 1

        self.conn.commit()

        self.restructuring_report['extraction_results']['lep_provisions'] = {
            'candidates_found': len(all_candidates),
            'records_extracted': lep_insertions,
            'extraction_success': lep_insertions > 0
        }

        self.restructuring_report['total_lep_extracted'] = lep_insertions

        print(f"✓ Extracted {lep_insertions:,} LEP provisions")

    def create_summary_views(self):
        """Create helpful views for Priority2Fix PRPs"""
        cursor = self.conn.cursor()

        # SEPP summary view
        sepp_view = '''
        CREATE OR REPLACE VIEW sepp_summary AS
        SELECT
            sepp_type,
            provision_category,
            COUNT(*) as provision_count,
            COUNT(DISTINCT development_type) as development_types,
            AVG(classification_confidence) as avg_confidence
        FROM sepp_provisions
        GROUP BY sepp_type, provision_category
        ORDER BY sepp_type, provision_category
        '''

        # LEP summary view
        lep_view = '''
        CREATE OR REPLACE VIEW lep_summary AS
        SELECT
            lep_name,
            lep_zone,
            provision_category,
            COUNT(*) as provision_count,
            COUNT(DISTINCT development_type) as development_types
        FROM lep_provisions
        GROUP BY lep_name, lep_zone, provision_category
        ORDER BY lep_name, lep_zone, provision_category
        '''

        cursor.execute(sepp_view)
        cursor.execute(lep_view)
        self.conn.commit()

        print("✓ Created summary views for analysis")

    def execute_restructuring(self):
        """Execute complete SEPP/LEP restructuring"""
        try:
            print("=== PRP-M2: SEPP/LEP RESTRUCTURING ===")

            # Create tables
            self.create_sepp_provisions_table()
            self.create_lep_provisions_table()

            # Extract data
            self.extract_sepp_provisions()
            self.extract_lep_provisions()

            # Create analysis views
            self.create_summary_views()

            self.restructuring_report['status'] = 'COMPLETED'
            self.restructuring_report['end_time'] = datetime.now().isoformat()

            # Save report
            with open('prp_m2_restructuring_report.json', 'w') as f:
                json.dump(self.restructuring_report, f, indent=2)

            print(f"\n✓ PRP-M2 COMPLETED")
            print(f"  SEPP provisions: {self.restructuring_report['total_sepp_extracted']:,}")
            print(f"  LEP provisions: {self.restructuring_report['total_lep_extracted']:,}")
            print(f"Report saved: prp_m2_restructuring_report.json")

        except Exception as e:
            self.restructuring_report['status'] = 'FAILED'
            self.restructuring_report['error'] = str(e)
            print(f"✗ PRP-M2 FAILED: {e}")
            raise

        finally:
            self.conn.close()

if __name__ == "__main__":
    restructurer = PRP_M2_Restructuring()
    restructurer.execute_restructuring()
```

### Verification Script: `verify_prp_m2.py`

```python
#!/usr/bin/env python3
"""
PRP-M2 Verification: Prove SEPP/LEP restructuring success
"""

import json
from db_config import get_connection

def verify_prp_m2():
    """Verify PRP-M2 completion with automated proof"""

    print("=== PRP-M2 VERIFICATION ===")

    # Load restructuring report
    try:
        with open('prp_m2_restructuring_report.json', 'r') as f:
            report = json.load(f)
    except FileNotFoundError:
        print("✗ FAILED: Restructuring report not found")
        return False

    # Check restructuring status
    if report['status'] != 'COMPLETED':
        print(f"✗ FAILED: Restructuring status = {report['status']}")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    verification_passed = True

    # Verify SEPP provisions table
    cursor.execute('SELECT COUNT(*) FROM sepp_provisions')
    sepp_count = cursor.fetchone()[0]

    if sepp_count >= 100:  # Expect at least 100 SEPP provisions
        print(f"✓ SEPP provisions: {sepp_count:,} records extracted")
    else:
        print(f"✗ SEPP provisions: Only {sepp_count:,} records (expected 100+)")
        verification_passed = False

    # Verify LEP provisions table
    cursor.execute('SELECT COUNT(*) FROM lep_provisions')
    lep_count = cursor.fetchone()[0]

    if lep_count >= 500:  # Expect at least 500 LEP provisions
        print(f"✓ LEP provisions: {lep_count:,} records extracted")
    else:
        print(f"✗ LEP provisions: Only {lep_count:,} records (expected 500+)")
        verification_passed = False

    # Verify data quality
    cursor.execute('SELECT COUNT(*) FROM sepp_provisions WHERE provision_text IS NOT NULL AND provision_text != \'\'')
    sepp_quality = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM lep_provisions WHERE provision_text IS NOT NULL AND provision_text != \'\'')
    lep_quality = cursor.fetchone()[0]

    if sepp_quality == sepp_count and lep_quality == lep_count:
        print(f"✓ Data quality: All records have provision text")
    else:
        print(f"✗ Data quality: Missing provision text in some records")
        verification_passed = False

    # Verify summary views
    try:
        cursor.execute('SELECT COUNT(*) FROM sepp_summary')
        sepp_summary_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM lep_summary')
        lep_summary_count = cursor.fetchone()[0]

        if sepp_summary_count > 0 and lep_summary_count > 0:
            print(f"✓ Summary views: SEPP ({sepp_summary_count}) LEP ({lep_summary_count})")
        else:
            print(f"✗ Summary views: Missing or empty")
            verification_passed = False

    except Exception as e:
        print(f"✗ Summary views: Error {e}")
        verification_passed = False

    # Test Priority2Fix readiness
    cursor.execute('''
        SELECT sepp_type, provision_category, COUNT(*)
        FROM sepp_provisions
        GROUP BY sepp_type, provision_category
        ORDER BY COUNT(*) DESC
        LIMIT 5
    ''')

    sepp_breakdown = cursor.fetchall()
    print(f"✓ SEPP breakdown ready for PRP-Q2:")
    for row in sepp_breakdown:
        print(f"  {row[0]} - {row[1]}: {row[2]:,} provisions")

    conn.close()

    # Final verification
    if verification_passed:
        print(f"\n✓ PRP-M2 VERIFICATION PASSED")
        print(f"  SEPP provisions: {sepp_count:,}")
        print(f"  LEP provisions: {lep_count:,}")
        print(f"  Ready for PRP-Q2 Development Pathway Intelligence")
        return True
    else:
        print(f"\n✗ PRP-M2 VERIFICATION FAILED")
        return False

if __name__ == "__main__":
    success = verify_prp_m2()
    exit(0 if success else 1)
```

## Expected Results

### Restructuring Report
```json
{
  "status": "COMPLETED",
  "total_sepp_extracted": 2186,
  "total_lep_extracted": 4481,
  "extraction_results": {
    "sepp_provisions": {"records_extracted": 2186, "extraction_success": true},
    "lep_provisions": {"records_extracted": 4481, "extraction_success": true}
  }
}
```

### Verification Output
```
✓ SEPP provisions: 2,186 records extracted
✓ LEP provisions: 4,481 records extracted
✓ Data quality: All records have provision text
✓ Summary views: SEPP (12) LEP (45)
✓ PRP-M2 VERIFICATION PASSED
```

## Success Criteria

1. **✓ SEPP provisions table** created with 2,000+ records
2. **✓ LEP provisions table** created with 4,000+ records
3. **✓ Data extraction quality** verified through automated checks
4. **✓ Summary views** ready for PRP-Q2 development pathway logic
5. **✓ Processing time < 30 minutes**

## Next Steps

After PRP-M2 completion:
1. Execute PRP-M3 (Service Architecture Unification)
2. Begin PRP-Q2 (Development Pathway Intelligence)

## Commands

```bash
# Execute restructuring
python execute_prp_m2.py

# Verify completion
python verify_prp_m2.py

# Check restructuring report
cat prp_m2_restructuring_report.json

# Analyze SEPP/LEP data
psql -U postgres -d nsw_planning -c "SELECT * FROM sepp_summary;"
psql -U postgres -d nsw_planning -c "SELECT * FROM lep_summary;"
```

---

**PRP-M2 provides the SEPP/LEP data structure required for PRP-Q2 development pathway intelligence.**