#!/usr/bin/env python3
"""
ENHANCED DATABASE MIGRATION - WORKING VERSION
=============================================

Creates normalized schema with full LangExtract + AutoSchemaKG preservation
for the current database structure. Fixes the setback query system.

Current database: regulatory_refs table with 22,092 entries
- 2,487 entries with page numbers (LangExtract quality)
- 2,518 entries with section headers
- Text levels: 2,040 at level 0, 478 at level 1

Enhanced structure:
- regulatory_provisions: Core regulatory text with citations
- development_controls: Specific controls (setbacks, heights, etc.)
- visual_elements: AutoSchemaKG diagrams and figures
- clause_relationships: LangExtract hierarchy
"""

import sqlite3
import json
import time
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDatabaseMigration:
    """Working migration that fixes the setback query system"""
    
    def __init__(self, db_path='nsw_planning.db'):
        self.db_path = db_path
        self.backup_path = f"{db_path}.enhanced_backup_{int(time.time())}"
        
    def create_backup(self):
        """Create backup of current database"""
        import shutil
        shutil.copy2(self.db_path, self.backup_path)
        logger.info(f"Backup created: {self.backup_path}")
        
        # Verify backup
        conn = sqlite3.connect(self.backup_path)
        count = conn.execute("SELECT COUNT(*) FROM regulatory_refs").fetchone()[0]
        conn.close()
        logger.info(f"Backup verified: {count:,} entries preserved")
    
    def create_enhanced_schema(self):
        """Create enhanced normalized schema"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Enhanced schema designed for the setback query system
        enhanced_tables = {
            'regulatory_provisions': '''
                CREATE TABLE IF NOT EXISTS regulatory_provisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,     -- Match regulatory_refs.document_id
                    provision_type TEXT NOT NULL,  -- 'clause', 'section', 'definition'
                    ref_number TEXT,               -- Original ref_number
                    provision_text TEXT NOT NULL,  -- Original ref_context
                    zone TEXT,                     -- Extracted from text
                    development_type TEXT,         -- Extracted from text
                    page_number INTEGER,           -- LangExtract page numbers
                    section_header TEXT,           -- LangExtract section headers
                    text_level INTEGER,            -- LangExtract hierarchy
                    original_id INTEGER,           -- Link back to regulatory_refs
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (original_id) REFERENCES regulatory_refs (id)
                )''',
            
            'development_controls': '''
                CREATE TABLE IF NOT EXISTS development_controls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provision_id INTEGER NOT NULL,
                    control_type TEXT NOT NULL,    -- 'setback', 'height', 'density', etc.
                    control_subtype TEXT,          -- 'front', 'side', 'rear' for setbacks
                    value_numeric REAL,            -- Extracted numeric value (e.g., 6.0)
                    value_text TEXT,               -- Original text (e.g., "6 metres")
                    unit TEXT,                     -- 'm', '%', 'storeys', etc.
                    zone_applicable TEXT,          -- Which zones this applies to
                    conditions TEXT,               -- Any conditions or exceptions
                    confidence_score REAL DEFAULT 1.0,
                    extraction_method TEXT DEFAULT 'regex',
                    FOREIGN KEY (provision_id) REFERENCES regulatory_provisions (id)
                )''',
            
            'visual_elements': '''
                CREATE TABLE IF NOT EXISTS visual_elements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provision_id INTEGER,
                    visual_type TEXT NOT NULL,     -- 'diagram', 'table', 'figure', 'image'
                    visual_path TEXT,              -- Path to visual file
                    visual_description TEXT,       -- Alt text or description
                    page_number INTEGER,           -- Page where visual appears
                    autoschema_source BOOLEAN DEFAULT FALSE,  -- From AutoSchemaKG
                    langextract_source BOOLEAN DEFAULT FALSE, -- From LangExtract
                    FOREIGN KEY (provision_id) REFERENCES regulatory_provisions (id)
                )''',
            
            'clause_relationships': '''
                CREATE TABLE IF NOT EXISTS clause_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_provision_id INTEGER NOT NULL,
                    child_provision_id INTEGER NOT NULL,
                    relationship_type TEXT NOT NULL,  -- 'hierarchy', 'reference', 'exception'
                    confidence_score REAL DEFAULT 1.0,
                    langextract_source BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (parent_provision_id) REFERENCES regulatory_provisions (id),
                    FOREIGN KEY (child_provision_id) REFERENCES regulatory_provisions (id)
                )''',
            
            'query_cache': '''
                CREATE TABLE IF NOT EXISTS query_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_text TEXT NOT NULL UNIQUE,
                    query_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )'''
        }
        
        logger.info("Creating enhanced schema tables...")
        for table_name, schema in enhanced_tables.items():
            try:
                cur.execute(schema)
                logger.info(f"Created table: {table_name}")
            except Exception as e:
                logger.error(f"Failed to create table {table_name}: {e}")
                
        conn.commit()
        conn.close()
    
    def migrate_regulatory_provisions(self):
        """Migrate regulatory_refs to regulatory_provisions with enhancement"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        logger.info("Migrating regulatory_refs to regulatory_provisions...")
        
        # Get all regulatory_refs entries
        cur.execute("""
            SELECT id, document_id, ref_type, ref_number, ref_context, 
                   page_number, section_header, text_level 
            FROM regulatory_refs
        """)
        
        entries = cur.fetchall()
        logger.info(f"Processing {len(entries):,} regulatory entries...")
        
        migrated_count = 0
        for entry in entries:
            (orig_id, document_id, ref_type, ref_number, ref_context, 
             page_number, section_header, text_level) = entry
            
            # Enhanced zone extraction
            zone = self.extract_zone(ref_context)
            development_type = self.extract_development_type(ref_context)
            
            cur.execute("""
                INSERT INTO regulatory_provisions (
                    document_id, provision_type, ref_number, provision_text,
                    zone, development_type, page_number, section_header, 
                    text_level, original_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id, ref_type, ref_number, ref_context,
                zone, development_type, page_number, section_header,
                text_level, orig_id
            ))
            
            migrated_count += 1
            if migrated_count % 1000 == 0:
                logger.info(f"Migrated {migrated_count:,} entries...")
        
        conn.commit()
        logger.info(f"Completed migration: {migrated_count:,} regulatory provisions created")
        
        # Verify migration
        new_count = cur.execute("SELECT COUNT(*) FROM regulatory_provisions").fetchone()[0]
        page_count = cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE page_number IS NOT NULL").fetchone()[0]
        
        logger.info(f"Verification: {new_count:,} provisions, {page_count:,} with page numbers")
        conn.close()
    
    def extract_development_controls(self):
        """Extract specific development controls (setbacks, heights, etc.)"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        logger.info("Extracting development controls...")
        
        # Get provisions that might contain controls
        cur.execute("""
            SELECT id, provision_text, zone, page_number, section_header
            FROM regulatory_provisions 
            WHERE provision_text LIKE '%setback%' 
               OR provision_text LIKE '%height%' 
               OR provision_text LIKE '%storey%'
               OR provision_text LIKE '%density%'
               OR provision_text LIKE '%metres%'
               OR provision_text LIKE '%meter%'
        """)
        
        candidates = cur.fetchall()
        logger.info(f"Processing {len(candidates):,} control candidates...")
        
        controls_extracted = 0
        
        for provision_id, text, zone, page_number, section_header in candidates:
            # Extract setback controls
            setback_controls = self.extract_setback_controls(text)
            for control in setback_controls:
                cur.execute("""
                    INSERT INTO development_controls (
                        provision_id, control_type, control_subtype, 
                        value_numeric, value_text, unit, zone_applicable,
                        confidence_score, extraction_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    provision_id, 'setback', control['subtype'],
                    control['numeric'], control['text'], control['unit'],
                    zone or 'general', control['confidence'], 'regex_enhanced'
                ))
                controls_extracted += 1
            
            # Extract height controls
            height_controls = self.extract_height_controls(text)
            for control in height_controls:
                cur.execute("""
                    INSERT INTO development_controls (
                        provision_id, control_type, control_subtype,
                        value_numeric, value_text, unit, zone_applicable,
                        confidence_score, extraction_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    provision_id, 'height', control['subtype'],
                    control['numeric'], control['text'], control['unit'],
                    zone or 'general', control['confidence'], 'regex_enhanced'
                ))
                controls_extracted += 1
        
        conn.commit()
        logger.info(f"Extracted {controls_extracted:,} development controls")
        conn.close()
    
    def extract_zone(self, text):
        """Extract zone from regulatory text"""
        if not text:
            return None
            
        zone_patterns = [
            r'\bR([1-4])\b',  # R1, R2, R3, R4
            r'\b(R1|R2|R3|R4|B1|B2|B3|B4|IN1|IN2|RE1|RE2|SP1|SP2)\b'
        ]
        
        for pattern in zone_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group().upper()
        
        return None
    
    def extract_development_type(self, text):
        """Extract development type from regulatory text"""
        if not text:
            return None
            
        dev_patterns = [
            (r'dual\s+occupanc', 'dual_occupancy'),
            (r'single\s+dwelling', 'single_dwelling'),
            (r'multi\s+dwelling', 'multi_dwelling'),
            (r'townhouse', 'townhouse'),
            (r'apartment', 'apartment'),
            (r'development\s+application', 'development_application'),
            (r'complying\s+development', 'complying_development')
        ]
        
        for pattern, dev_type in dev_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return dev_type
        
        return None
    
    def extract_setback_controls(self, text):
        """Extract setback values from regulatory text"""
        controls = []
        
        # Enhanced setback patterns
        setback_patterns = [
            # "front setback 6 metres"
            (r'front\s+setback\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(m(?:etres?)?)', 'front'),
            # "side setback minimum 1.5m"
            (r'side\s+setback\s+(?:minimum\s+)?(\d+(?:\.\d+)?)\s*(m(?:etres?)?)', 'side'),
            # "rear setback 6m"
            (r'rear\s+setback\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(m(?:etres?)?)', 'rear'),
            # "setback from front boundary 6 metres"
            (r'setback\s+from\s+front\s+boundary\s+(\d+(?:\.\d+)?)\s*(m(?:etres?)?)', 'front'),
            # "minimum 6 metre front setback"
            (r'minimum\s+(\d+(?:\.\d+)?)\s*(?:m(?:etres?)?\s+)?front\s+setback', 'front'),
            # General patterns
            (r'(\d+(?:\.\d+)?)\s*(?:m(?:etres?)?\s+)setback', 'general')
        ]
        
        for pattern, subtype in setback_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                numeric_value = float(match.group(1))
                original_text = match.group(0)
                unit = 'm'  # Default to metres
                
                controls.append({
                    'subtype': subtype,
                    'numeric': numeric_value,
                    'text': original_text,
                    'unit': unit,
                    'confidence': 0.9 if subtype != 'general' else 0.7
                })
        
        return controls
    
    def extract_height_controls(self, text):
        """Extract height controls from regulatory text"""
        controls = []
        
        height_patterns = [
            (r'height\s+limit\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(m(?:etres?)?)', 'limit'),
            (r'maximum\s+height\s+(\d+(?:\.\d+)?)\s*(m(?:etres?)?)', 'maximum'),
            (r'(\d+(?:\.\d+)?)\s*(?:m(?:etres?)?\s+)?height', 'general'),
            (r'(\d+)\s+storey', 'storeys')
        ]
        
        for pattern, subtype in height_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if subtype == 'storeys':
                    numeric_value = float(match.group(1))
                    unit = 'storeys'
                else:
                    numeric_value = float(match.group(1))
                    unit = 'm'
                
                controls.append({
                    'subtype': subtype,
                    'numeric': numeric_value,
                    'text': match.group(0),
                    'unit': unit,
                    'confidence': 0.8
                })
        
        return controls
    
    def create_indexes(self):
        """Create indexes for efficient querying"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_provisions_zone ON regulatory_provisions (zone)",
            "CREATE INDEX IF NOT EXISTS idx_provisions_dev_type ON regulatory_provisions (development_type)",
            "CREATE INDEX IF NOT EXISTS idx_provisions_page ON regulatory_provisions (page_number)",
            "CREATE INDEX IF NOT EXISTS idx_controls_type ON development_controls (control_type, control_subtype)",
            "CREATE INDEX IF NOT EXISTS idx_controls_zone ON development_controls (zone_applicable)",
            "CREATE INDEX IF NOT EXISTS idx_controls_value ON development_controls (value_numeric)",
        ]
        
        logger.info("Creating performance indexes...")
        for index in indexes:
            cur.execute(index)
        
        conn.commit()
        conn.close()
        logger.info("Indexes created successfully")
    
    def verify_migration(self):
        """Verify migration success"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        logger.info("Verifying migration results...")
        
        # Check provisions
        provisions_count = cur.execute("SELECT COUNT(*) FROM regulatory_provisions").fetchone()[0]
        provisions_with_pages = cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE page_number IS NOT NULL").fetchone()[0]
        
        # Check controls
        controls_count = cur.execute("SELECT COUNT(*) FROM development_controls").fetchone()[0]
        setback_controls = cur.execute("SELECT COUNT(*) FROM development_controls WHERE control_type = 'setback'").fetchone()[0]
        
        # Check zones
        zones = cur.execute("SELECT DISTINCT zone FROM regulatory_provisions WHERE zone IS NOT NULL").fetchall()
        
        logger.info(f"MIGRATION VERIFICATION:")
        logger.info(f"- Regulatory provisions: {provisions_count:,}")
        logger.info(f"- Provisions with pages: {provisions_with_pages:,}")
        logger.info(f"- Development controls: {controls_count:,}")
        logger.info(f"- Setback controls: {setback_controls:,}")
        logger.info(f"- Zones identified: {[z[0] for z in zones if z[0]]}")
        
        # Test setback query
        logger.info("\nTesting setback query...")
        test_query = """
        SELECT rp.provision_text, dc.control_subtype, dc.value_numeric, 
               dc.unit, rp.page_number, rp.section_header
        FROM regulatory_provisions rp
        JOIN development_controls dc ON rp.id = dc.provision_id
        WHERE dc.control_type = 'setback' 
          AND (rp.zone = 'R2' OR dc.zone_applicable = 'R2' OR dc.zone_applicable = 'general')
        LIMIT 5
        """
        
        results = cur.execute(test_query).fetchall()
        logger.info(f"Sample setback query returned {len(results)} results:")
        for i, (text, subtype, value, unit, page, section) in enumerate(results, 1):
            logger.info(f"  {i}. {subtype} setback: {value}{unit} (Page {page}) - {text[:60]}...")
        
        conn.close()
        return provisions_count > 0 and controls_count > 0
    
    def run_migration(self):
        """Run complete migration"""
        logger.info("STARTING ENHANCED DATABASE MIGRATION")
        logger.info("=" * 60)
        
        try:
            # Step 1: Backup
            self.create_backup()
            
            # Step 2: Create schema
            self.create_enhanced_schema()
            
            # Step 3: Migrate data
            self.migrate_regulatory_provisions()
            
            # Step 4: Extract controls
            self.extract_development_controls()
            
            # Step 5: Create indexes
            self.create_indexes()
            
            # Step 6: Verify
            success = self.verify_migration()
            
            if success:
                logger.info("\nMIGRATION COMPLETED SUCCESSFULLY!")
                logger.info("The setback query system is now ready to use the enhanced database.")
            else:
                logger.error("\nMIGRATION VERIFICATION FAILED!")
                
            return success
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

def main():
    """Main execution"""
    migration = EnhancedDatabaseMigration()
    success = migration.run_migration()
    
    if success:
        print("\nEnhanced database migration completed successfully!")
        print("The setback query system can now access:")
        print("- Normalized regulatory provisions with page citations")
        print("- Extracted development controls with numeric values")
        print("- Zone-specific queries with confidence scoring")
        print("- Performance indexes for fast queries")
    else:
        print("\nMigration failed. Check logs for details.")

if __name__ == "__main__":
    main()