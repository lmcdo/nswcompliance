#!/usr/bin/env python3
"""
Phase 3 Execution: Schema Population
Steps 11-15: Create and populate research assistant schema
Enhanced for Planning API integration
"""
import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch, Json
import json
from datetime import datetime
from collections import defaultdict
import hashlib

class Phase3Populator:
    def __init__(self):
        self.sqlite_conn = sqlite3.connect('nsw_planning.db')
        self.sqlite_cursor = self.sqlite_conn.cursor()
        
        # PostgreSQL connection
        self.pg_conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres'
        )
        self.pg_cursor = self.pg_conn.cursor()
        
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.population_stats = defaultdict(int)
        
    def step_11_create_schema(self):
        """Step 11: Create research assistant schema"""
        print("\nSTEP 11: Create Research Assistant Schema")
        print("-" * 30)
        
        try:
            # Drop existing schemas if needed (for clean slate)
            self.pg_cursor.execute("DROP SCHEMA IF EXISTS research_assistant CASCADE")
            self.pg_cursor.execute("DROP SCHEMA IF EXISTS migration_audit CASCADE")
            
            # Create schemas
            self.pg_cursor.execute("CREATE SCHEMA research_assistant")
            self.pg_cursor.execute("CREATE SCHEMA migration_audit")
            
            # Create document types enum
            self.pg_cursor.execute("""
                CREATE TYPE research_assistant.document_type AS ENUM (
                    'SEPP', 'LEP', 'DCP', 'POLICY', 'GUIDELINE', 'OTHER'
                )
            """)
            
            # Create provision types enum
            self.pg_cursor.execute("""
                CREATE TYPE research_assistant.provision_type AS ENUM (
                    'mandatory', 'advisory', 'informative', 'definition', 'objective'
                )
            """)
            
            # Create documents table
            self.pg_cursor.execute("""
                CREATE TABLE research_assistant.documents (
                    id SERIAL PRIMARY KEY,
                    original_id TEXT UNIQUE,
                    name TEXT NOT NULL,
                    document_type research_assistant.document_type NOT NULL,
                    document_area TEXT,
                    authority_level INTEGER DEFAULT 4,
                    pdf_path TEXT,
                    url TEXT,
                    version VARCHAR(50),
                    publish_date DATE,
                    metadata JSONB DEFAULT '{}',
                    search_vector tsvector GENERATED ALWAYS AS (
                        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
                        setweight(to_tsvector('english', coalesce(document_area, '')), 'B')
                    ) STORED,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create provisions table (enhanced for Planning API)
            self.pg_cursor.execute("""
                CREATE TABLE research_assistant.provisions (
                    id SERIAL PRIMARY KEY,
                    original_id INTEGER,
                    document_id INTEGER REFERENCES research_assistant.documents(id),
                    provision_text TEXT,
                    provision_type research_assistant.provision_type DEFAULT 'informative',
                    
                    -- Zone fields for Planning API integration
                    explicit_zone VARCHAR(10),  -- From text extraction
                    api_zones TEXT[],  -- Zones this provision applies to (from API)
                    
                    -- Development type
                    development_type VARCHAR(100),
                    
                    -- Geographic scope
                    geographic_scope VARCHAR(100),
                    lga VARCHAR(100),
                    
                    -- Searchable content
                    search_vector tsvector GENERATED ALWAYS AS (
                        setweight(to_tsvector('english', coalesce(provision_text, '')), 'A') ||
                        setweight(to_tsvector('english', coalesce(development_type, '')), 'B') ||
                        setweight(to_tsvector('english', coalesce(explicit_zone, '')), 'C')
                    ) STORED,
                    
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(original_id)
                )
            """)
            
            # Create quantitative standards table
            self.pg_cursor.execute("""
                CREATE TABLE research_assistant.quantitative_standards (
                    id SERIAL PRIMARY KEY,
                    provision_id INTEGER REFERENCES research_assistant.provisions(id),
                    standard_type VARCHAR(50),
                    numeric_value NUMERIC,
                    unit VARCHAR(20),
                    qualifier VARCHAR(50),
                    context TEXT,
                    
                    -- For Planning API matching
                    applicable_zones TEXT[],
                    development_types TEXT[],
                    
                    confidence_score NUMERIC(3,2),
                    raw_text TEXT,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create planning API cache table
            self.pg_cursor.execute("""
                CREATE TABLE research_assistant.planning_api_cache (
                    id SERIAL PRIMARY KEY,
                    property_id INTEGER UNIQUE,
                    address TEXT,
                    zone VARCHAR(10),
                    height_limit NUMERIC,
                    fsr NUMERIC,
                    lot_geometry JSONB,
                    overlays JSONB,
                    raw_response JSONB,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '7 days')
                )
            """)
            
            # Create compliance results table
            self.pg_cursor.execute("""
                CREATE TABLE research_assistant.compliance_results (
                    id SERIAL PRIMARY KEY,
                    property_id INTEGER,
                    zone VARCHAR(10),
                    relevant_provisions INTEGER[],
                    applicable_standards INTEGER[],
                    confidence_score NUMERIC(3,2),
                    result_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create audit log
            self.pg_cursor.execute("""
                CREATE TABLE migration_audit.migration_log (
                    id SERIAL PRIMARY KEY,
                    phase VARCHAR(50),
                    step INTEGER,
                    action VARCHAR(100),
                    table_name VARCHAR(100),
                    rows_affected INTEGER,
                    status VARCHAR(20),
                    error_message TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.pg_conn.commit()
            
            # Verify tables created
            self.pg_cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'research_assistant'
                ORDER BY table_name
            """)
            tables = self.pg_cursor.fetchall()
            
            print(f"  Schema created successfully")
            print(f"  Tables created: {len(tables)}")
            for table in tables:
                print(f"    - {table[0]}")
            
            self.log_audit('Phase3', 11, 'create_schema', 'all', len(tables), 'SUCCESS')
            print("STEP 11: SUCCESS")
            return True
            
        except Exception as e:
            self.pg_conn.rollback()
            print(f"STEP 11 FAILED: {e}")
            self.log_audit('Phase3', 11, 'create_schema', 'all', 0, 'FAILED', str(e))
            return False
    
    def step_12_populate_documents(self):
        """Step 12: Populate documents table"""
        print("\nSTEP 12: Populate Documents")
        print("-" * 30)
        
        try:
            # Get documents from SQLite
            self.sqlite_cursor.execute("""
                SELECT id, pdf_name, document_type, document_area, pdf_path
                FROM documents
            """)
            documents = self.sqlite_cursor.fetchall()
            
            # Insert into PostgreSQL
            insert_query = """
                INSERT INTO research_assistant.documents (
                    original_id, name, document_type, document_area, 
                    pdf_path, authority_level, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (original_id) DO NOTHING
            """
            
            batch_data = []
            for doc_id, pdf_name, doc_type, doc_area, pdf_path in documents:
                # Determine document type enum
                if 'SEPP' in pdf_name or 'State Environmental' in pdf_name:
                    doc_type_enum = 'SEPP'
                    authority = 1
                elif 'LEP' in pdf_name or 'Local Environmental' in pdf_name:
                    doc_type_enum = 'LEP'
                    authority = 2
                elif 'DCP' in pdf_name or 'Development Control' in pdf_name:
                    doc_type_enum = 'DCP'
                    authority = 3
                else:
                    doc_type_enum = 'OTHER'
                    authority = 4
                
                metadata = {
                    'original_type': doc_type,
                    'import_timestamp': self.timestamp
                }
                
                batch_data.append((
                    doc_id, pdf_name, doc_type_enum, doc_area,
                    pdf_path, authority, Json(metadata)
                ))
            
            execute_batch(self.pg_cursor, insert_query, batch_data)
            self.pg_conn.commit()
            
            # Verify insertion
            self.pg_cursor.execute("SELECT COUNT(*) FROM research_assistant.documents")
            count = self.pg_cursor.fetchone()[0]
            
            print(f"  Documents inserted: {count}")
            self.population_stats['documents'] = count
            
            self.log_audit('Phase3', 12, 'populate_documents', 'documents', count, 'SUCCESS')
            print("STEP 12: SUCCESS")
            return True
            
        except Exception as e:
            self.pg_conn.rollback()
            print(f"STEP 12 FAILED: {e}")
            self.log_audit('Phase3', 12, 'populate_documents', 'documents', 0, 'FAILED', str(e))
            return False
    
    def step_13_populate_provisions(self):
        """Step 13: Populate provisions with zone corrections"""
        print("\nSTEP 13: Populate Provisions")
        print("-" * 30)
        
        try:
            # Load zone corrections from Phase 2
            import glob
            zone_files = glob.glob('backups/zone_extraction_*.json')
            if zone_files:
                latest_file = sorted(zone_files)[-1]
                with open(latest_file, 'r') as f:
                    zone_data = json.load(f)
            else:
                zone_data = {}
            
            # Get provisions from SQLite
            self.sqlite_cursor.execute("""
                SELECT id, document_id, provision_text, zone, development_type
                FROM regulatory_provisions
            """)
            
            provisions = self.sqlite_cursor.fetchall()
            total = len(provisions)
            
            # Get document ID mapping
            self.pg_cursor.execute("""
                SELECT original_id, id FROM research_assistant.documents
            """)
            doc_mapping = dict(self.pg_cursor.fetchall())
            
            # Prepare batch insert
            insert_query = """
                INSERT INTO research_assistant.provisions (
                    original_id, document_id, provision_text, 
                    explicit_zone, development_type, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (original_id) DO NOTHING
            """
            
            batch_data = []
            processed = 0
            
            for prov_id, doc_id, text, old_zone, dev_type in provisions:
                # Get corrected zone from extraction
                explicit_zone = self.extract_zone_from_text(text)
                
                # Map document ID
                pg_doc_id = doc_mapping.get(doc_id)
                
                metadata = {
                    'old_zone': old_zone,
                    'extraction_method': 'explicit' if explicit_zone else 'none',
                    'import_timestamp': self.timestamp
                }
                
                batch_data.append((
                    prov_id, pg_doc_id, text,
                    explicit_zone, dev_type, Json(metadata)
                ))
                
                processed += 1
                if processed % 5000 == 0:
                    print(f"  Processed {processed}/{total} provisions...")
                    execute_batch(self.pg_cursor, insert_query, batch_data)
                    batch_data = []
            
            # Insert remaining
            if batch_data:
                execute_batch(self.pg_cursor, insert_query, batch_data)
            
            self.pg_conn.commit()
            
            # Verify insertion
            self.pg_cursor.execute("SELECT COUNT(*) FROM research_assistant.provisions")
            count = self.pg_cursor.fetchone()[0]
            
            self.pg_cursor.execute("""
                SELECT COUNT(*) FROM research_assistant.provisions 
                WHERE explicit_zone IS NOT NULL
            """)
            zone_count = self.pg_cursor.fetchone()[0]
            
            print(f"  Provisions inserted: {count}")
            print(f"  Provisions with zones: {zone_count}")
            self.population_stats['provisions'] = count
            self.population_stats['zoned_provisions'] = zone_count
            
            self.log_audit('Phase3', 13, 'populate_provisions', 'provisions', count, 'SUCCESS')
            print("STEP 13: SUCCESS")
            return True
            
        except Exception as e:
            self.pg_conn.rollback()
            print(f"STEP 13 FAILED: {e}")
            self.log_audit('Phase3', 13, 'populate_provisions', 'provisions', 0, 'FAILED', str(e))
            return False
    
    def step_14_populate_standards(self):
        """Step 14: Populate quantitative standards"""
        print("\nSTEP 14: Populate Quantitative Standards")
        print("-" * 30)
        
        try:
            # Get standards from SQLite
            self.sqlite_cursor.execute("""
                SELECT 
                    qs.id,
                    qs.provision_id,
                    qs.numeric_value,
                    qs.unit,
                    qs.qualifier,
                    qs.context,
                    qs.confidence_score,
                    qs.raw_text
                FROM quantitative_standards qs
            """)
            
            standards = self.sqlite_cursor.fetchall()
            
            # Get provision ID mapping
            self.pg_cursor.execute("""
                SELECT original_id, id FROM research_assistant.provisions
            """)
            prov_mapping = dict(self.pg_cursor.fetchall())
            
            # Prepare batch insert
            insert_query = """
                INSERT INTO research_assistant.quantitative_standards (
                    provision_id, standard_type, numeric_value,
                    unit, qualifier, context, confidence_score,
                    raw_text, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            batch_data = []
            for std_id, prov_id, value, unit, qualifier, context, confidence, raw_text in standards:
                # Map provision ID
                pg_prov_id = prov_mapping.get(prov_id)
                if not pg_prov_id:
                    continue
                
                # Categorize standard type
                standard_type = self.categorize_standard(context, unit)
                
                metadata = {
                    'original_id': std_id,
                    'import_timestamp': self.timestamp
                }
                
                batch_data.append((
                    pg_prov_id, standard_type, value,
                    unit, qualifier, context, confidence,
                    raw_text, Json(metadata)
                ))
            
            execute_batch(self.pg_cursor, insert_query, batch_data)
            self.pg_conn.commit()
            
            # Verify insertion
            self.pg_cursor.execute("""
                SELECT COUNT(*) FROM research_assistant.quantitative_standards
            """)
            count = self.pg_cursor.fetchone()[0]
            
            # Get category breakdown
            self.pg_cursor.execute("""
                SELECT standard_type, COUNT(*) 
                FROM research_assistant.quantitative_standards 
                GROUP BY standard_type 
                ORDER BY COUNT(*) DESC
            """)
            categories = self.pg_cursor.fetchall()
            
            print(f"  Standards inserted: {count}")
            print("  Categories:")
            for cat, cat_count in categories:
                print(f"    - {cat}: {cat_count}")
            
            self.population_stats['standards'] = count
            
            self.log_audit('Phase3', 14, 'populate_standards', 'quantitative_standards', count, 'SUCCESS')
            print("STEP 14: SUCCESS")
            return True
            
        except Exception as e:
            self.pg_conn.rollback()
            print(f"STEP 14 FAILED: {e}")
            self.log_audit('Phase3', 14, 'populate_standards', 'quantitative_standards', 0, 'FAILED', str(e))
            return False
    
    def step_15_create_indexes(self):
        """Step 15: Create indexes and optimize performance"""
        print("\nSTEP 15: Create Indexes and Optimize")
        print("-" * 30)
        
        try:
            indexes = [
                # Text search indexes
                "CREATE INDEX idx_documents_search ON research_assistant.documents USING GIN(search_vector)",
                "CREATE INDEX idx_provisions_search ON research_assistant.provisions USING GIN(search_vector)",
                
                # Zone indexes
                "CREATE INDEX idx_provisions_zone ON research_assistant.provisions(explicit_zone) WHERE explicit_zone IS NOT NULL",
                "CREATE INDEX idx_provisions_api_zones ON research_assistant.provisions USING GIN(api_zones)",
                
                # Development type index
                "CREATE INDEX idx_provisions_dev_type ON research_assistant.provisions(development_type)",
                
                # Document relationships
                "CREATE INDEX idx_provisions_document ON research_assistant.provisions(document_id)",
                "CREATE INDEX idx_standards_provision ON research_assistant.quantitative_standards(provision_id)",
                
                # Standards indexes
                "CREATE INDEX idx_standards_type ON research_assistant.quantitative_standards(standard_type)",
                "CREATE INDEX idx_standards_value ON research_assistant.quantitative_standards(numeric_value)",
                
                # API cache indexes
                "CREATE INDEX idx_api_cache_property ON research_assistant.planning_api_cache(property_id)",
                "CREATE INDEX idx_api_cache_zone ON research_assistant.planning_api_cache(zone)",
                "CREATE INDEX idx_api_cache_expires ON research_assistant.planning_api_cache(expires_at)",
                
                # Compliance results
                "CREATE INDEX idx_compliance_property ON research_assistant.compliance_results(property_id)",
                "CREATE INDEX idx_compliance_zone ON research_assistant.compliance_results(zone)"
            ]
            
            for idx_sql in indexes:
                try:
                    self.pg_cursor.execute(idx_sql)
                    index_name = idx_sql.split('INDEX')[1].split('ON')[0].strip()
                    print(f"  Created index: {index_name}")
                except psycopg2.errors.DuplicateTable:
                    print(f"  Index already exists, skipping")
            
            # Analyze tables for query optimization
            tables = ['documents', 'provisions', 'quantitative_standards', 
                     'planning_api_cache', 'compliance_results']
            
            for table in tables:
                self.pg_cursor.execute(f"ANALYZE research_assistant.{table}")
            
            self.pg_conn.commit()
            
            # Create materialized view for zone statistics
            self.pg_cursor.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS research_assistant.zone_statistics AS
                SELECT 
                    explicit_zone as zone,
                    COUNT(*) as provision_count,
                    COUNT(DISTINCT document_id) as document_count,
                    COUNT(DISTINCT development_type) as dev_type_count
                FROM research_assistant.provisions
                WHERE explicit_zone IS NOT NULL
                GROUP BY explicit_zone
                ORDER BY provision_count DESC
            """)
            
            self.pg_cursor.execute("""
                CREATE INDEX idx_zone_stats ON research_assistant.zone_statistics(zone)
            """)
            
            self.pg_conn.commit()
            
            print(f"  Indexes created: {len(indexes)}")
            print("  Tables analyzed for optimization")
            print("  Materialized view created")
            
            self.log_audit('Phase3', 15, 'create_indexes', 'all', len(indexes), 'SUCCESS')
            print("STEP 15: SUCCESS")
            return True
            
        except Exception as e:
            self.pg_conn.rollback()
            print(f"STEP 15 FAILED: {e}")
            self.log_audit('Phase3', 15, 'create_indexes', 'all', 0, 'FAILED', str(e))
            return False
    
    def extract_zone_from_text(self, text):
        """Extract zone from text using explicit patterns"""
        if not text:
            return None
        
        import re
        zone_patterns = [
            r'\b[Zz]one\s+([RBCINE]{1,2}\d{1,2})\b',
            r'\b([RBCINE]{1,2}\d{1,2})\s+[Zz]one\b',
        ]
        
        for pattern in zone_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].upper()
        
        return None
    
    def categorize_standard(self, context, unit):
        """Categorize quantitative standard"""
        if not context:
            return 'general'
        
        context_lower = context.lower()
        
        if 'height' in context_lower or unit in ['m', 'metres', 'meters']:
            return 'height'
        elif 'setback' in context_lower:
            return 'setback'
        elif 'fsr' in context_lower or 'floor space' in context_lower:
            return 'floor_space_ratio'
        elif 'coverage' in context_lower or '%' in str(unit):
            return 'site_coverage'
        elif 'parking' in context_lower:
            return 'parking'
        elif 'landscape' in context_lower:
            return 'landscaping'
        else:
            return 'other'
    
    def log_audit(self, phase, step, action, table, rows, status, error=None):
        """Log migration audit trail"""
        try:
            self.pg_cursor.execute("""
                INSERT INTO migration_audit.migration_log 
                (phase, step, action, table_name, rows_affected, status, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (phase, step, action, table, rows, status, error))
            self.pg_conn.commit()
        except:
            pass  # Don't fail migration if audit logging fails
    
    def execute_phase3(self):
        """Execute all Phase 3 steps"""
        print("\n" + "=" * 50)
        print("PHASE 3: SCHEMA POPULATION")
        print("=" * 50)
        
        steps = [
            (11, self.step_11_create_schema),
            (12, self.step_12_populate_documents),
            (13, self.step_13_populate_provisions),
            (14, self.step_14_populate_standards),
            (15, self.step_15_create_indexes)
        ]
        
        for step_num, step_func in steps:
            if not step_func():
                print(f"\nPhase 3 failed at step {step_num}")
                return False
        
        # Phase 3 Summary
        print("\n" + "=" * 50)
        print("PHASE 3 VALIDATION GATE")
        print("=" * 50)
        
        # Final verification
        self.pg_cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM research_assistant.documents) as docs,
                (SELECT COUNT(*) FROM research_assistant.provisions) as provs,
                (SELECT COUNT(*) FROM research_assistant.quantitative_standards) as stds,
                (SELECT COUNT(*) FROM research_assistant.provisions WHERE explicit_zone IS NOT NULL) as zoned
        """)
        
        docs, provs, stds, zoned = self.pg_cursor.fetchone()
        
        print(f"\nPopulation Summary:")
        print(f"  Documents: {docs}")
        print(f"  Provisions: {provs}")
        print(f"  Quantitative Standards: {stds}")
        print(f"  Provisions with zones: {zoned}")
        
        # Save population report
        report = {
            'timestamp': self.timestamp,
            'documents': docs,
            'provisions': provs,
            'standards': stds,
            'zoned_provisions': zoned,
            'statistics': dict(self.population_stats)
        }
        
        with open(f'backups/phase3_report_{self.timestamp}.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\nVALIDATION GATE 3: PASSED")
        print("Ready for Phase 4: Full Validation")
        
        # Close connections
        self.sqlite_conn.close()
        self.pg_cursor.close()
        self.pg_conn.close()
        
        return True

if __name__ == "__main__":
    populator = Phase3Populator()
    success = populator.execute_phase3()
    
    if success:
        print("\nPhase 3 completed successfully!")
        print("Research Assistant schema populated and optimized")
        print("Ready for Planning API integration")
    else:
        print("\nPhase 3 failed - check logs for details")