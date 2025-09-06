#!/bin/bash
# PRP-D: Complete Database Factorization Automation Script
# This script executes the entire PRP-D process with full verification

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log file
LOGFILE="prp_d_execution_$(date +%Y%m%d_%H%M%S).log"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOGFILE"
}

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}$message${NC}" | tee -a "$LOGFILE"
}

# Function to check if command succeeded
check_success() {
    if [ $? -eq 0 ]; then
        print_status "$GREEN" "✅ $1 - SUCCESS"
        return 0
    else
        print_status "$RED" "❌ $1 - FAILED"
        print_status "$RED" "Check $LOGFILE for details"
        exit 1
    fi
}

# Function to verify table exists and has minimum records
verify_table() {
    local table=$1
    local min_records=$2
    local description=$3
    
    ./venv_linux/Scripts/python.exe -c "
import sqlite3
conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()
try:
    cursor.execute('SELECT COUNT(*) FROM $table')
    count = cursor.fetchone()[0]
    if count >= $min_records:
        print(f'✅ $description: {count:,} records (≥$min_records expected)')
        exit(0)
    else:
        print(f'❌ $description: {count:,} records (<$min_records minimum)')
        exit(1)
except Exception as e:
    print(f'❌ $description: Error - {e}')
    exit(1)
finally:
    conn.close()
" >> "$LOGFILE" 2>&1
    
    return $?
}

print_status "$BLUE" "=========================================="
print_status "$BLUE" "🚀 STARTING PRP-D DATABASE FACTORIZATION"
print_status "$BLUE" "=========================================="
log "PRP-D execution started"

# Create required directories
mkdir -p migration_markers prp_scripts
log "Created directories: migration_markers, prp_scripts"

# ============================================================================
# PHASE 1: PRE-MIGRATION VERIFICATION
# ============================================================================
print_status "$YELLOW" "\n📋 PHASE 1: PRE-MIGRATION VERIFICATION"

# Backup database
BACKUP_NAME="nsw_planning_backup_$(date +%Y%m%d_%H%M%S).db"
cp nsw_planning.db "$BACKUP_NAME"
check_success "Database backup created: $BACKUP_NAME"

# Verify AutoSchemaKG file exists
if [ -f "autoschemakg_output_ollama_final/kg_extraction/llama3.1_8b_nsw_planning_docs_output_20250829000809_1_in_1.json" ]; then
    FILESIZE=$(stat -c%s "autoschemakg_output_ollama_final/kg_extraction/llama3.1_8b_nsw_planning_docs_output_20250829000809_1_in_1.json")
    print_status "$GREEN" "✅ AutoSchemaKG file found: $FILESIZE bytes"
else
    print_status "$RED" "❌ AutoSchemaKG file missing - cannot proceed"
    exit 1
fi

# Initial database state
./venv_linux/Scripts/python.exe -c "
import sqlite3
conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

tables = ['regulatory_refs', 'regulatory_provisions', 'kg_entities', 'kg_relationships', 'development_controls']
print('PRE-MIGRATION DATABASE STATE:')
for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f'  {table}: {count:,}')

conn.close()
" >> "$LOGFILE" 2>&1

print_status "$GREEN" "✅ Phase 1 Complete - Ready for migration"

# ============================================================================
# PHASE 2: AUTOSCHEMAKG IMPORT
# ============================================================================
print_status "$YELLOW" "\n🧠 PHASE 2: AUTOSCHEMAKG IMPORT"

# Create import script
cat > prp_scripts/import_autoschemakg.py << 'EOF'
#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime

def import_autoschemakg_relationships():
    print("IMPORTING AUTOSCHEMAKG RELATIONSHIPS")
    print("=" * 50)
    
    # Load AutoSchemaKG data
    print("Loading AutoSchemaKG extraction file...")
    with open('autoschemakg_output_ollama_final/kg_extraction/llama3.1_8b_nsw_planning_docs_output_20250829000809_1_in_1.json', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    documents = []
    for line in lines:
        if line.strip():
            try:
                documents.append(json.loads(line))
            except:
                continue
    
    print(f"Loaded {len(documents)} documents with relationships")
    
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Create entity mapping
    entity_id_map = {}
    entities_imported = 0
    
    # Import entities first
    print("Importing entities...")
    
    for doc in documents:
        doc_id = doc.get('id', '')
        
        # Extract unique entities from relationships
        for rel in doc.get('entity_relation_dict', []):
            head = rel.get('Head', '').strip()
            tail = rel.get('Tail', '').strip()
            
            # Create entities if not exists
            for entity_name in [head, tail]:
                if entity_name and entity_name not in entity_id_map:
                    cursor.execute('''
                        INSERT INTO kg_entities 
                        (entity_type, entity_name, document_id, original_ref_type, extraction_timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', ('autoschemakg_entity', entity_name, doc_id, 'autoschemakg_import', datetime.now().isoformat()))
                    
                    entity_id_map[entity_name] = cursor.lastrowid
                    entities_imported += 1
    
    print(f"Imported {entities_imported} unique entities")
    
    # Import relationships
    print("Importing relationships...")
    relationships_imported = 0
    
    for doc in documents:
        doc_id = doc.get('id', '')
        
        # Import entity-to-entity relationships
        for rel in doc.get('entity_relation_dict', []):
            head = rel.get('Head', '').strip()
            relation = rel.get('Relation', '').strip()
            tail = rel.get('Tail', '').strip()
            
            if head and tail and relation:
                subject_entity_id = entity_id_map.get(head)
                object_entity_id = entity_id_map.get(tail)
                
                if subject_entity_id and object_entity_id:
                    cursor.execute('''
                        INSERT INTO kg_relationships 
                        (subject_text, predicate, object_text, subject_entity_id, 
                         object_entity_id, document_id, original_ref_type, 
                         extraction_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (head, relation, tail, subject_entity_id, object_entity_id,
                          doc_id, 'autoschemakg_entity_relation', datetime.now().isoformat()))
                    relationships_imported += 1
        
        # Import event relationships for temporal/causal analysis
        for rel in doc.get('event_relation_dict', []):
            head = rel.get('Head', '').strip()
            relation = rel.get('Relation', '').strip() 
            tail = rel.get('Tail', '').strip()
            
            if head and tail and relation:
                cursor.execute('''
                    INSERT INTO kg_relationships
                    (subject_text, predicate, object_text, document_id, 
                     original_ref_type, extraction_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (head, relation, tail, doc_id, 
                      'autoschemakg_event_relation', datetime.now().isoformat()))
                relationships_imported += 1
    
    conn.commit()
    
    # Verification
    cursor.execute("SELECT COUNT(*) FROM kg_entities")
    final_entities = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM kg_relationships")
    final_relationships = cursor.fetchone()[0]
    
    print(f"\nIMPORT COMPLETED:")
    print(f"  Entities in kg_entities: {final_entities:,}")
    print(f"  Relationships in kg_relationships: {final_relationships:,}")
    
    conn.close()
    
    # Create completion marker
    with open('migration_markers/autoschemakg_import_completed.marker', 'w') as f:
        f.write(f"AutoSchemaKG import completed: {datetime.now().isoformat()}\n")
        f.write(f"Entities imported: {final_entities}\n")
        f.write(f"Relationships imported: {final_relationships}\n")
        f.write("Status: SUCCESS\n")
    
    return final_entities, final_relationships

if __name__ == "__main__":
    entities, relationships = import_autoschemakg_relationships()
    
    if relationships >= 4000:
        print("✅ AUTOSCHEMAKG IMPORT SUCCESSFUL")
        exit(0)
    else:
        print("❌ AUTOSCHEMAKG IMPORT FAILED - INSUFFICIENT DATA")
        exit(1)
EOF

# Execute AutoSchemaKG import
./venv_linux/Scripts/python.exe prp_scripts/import_autoschemakg.py >> "$LOGFILE" 2>&1
check_success "AutoSchemaKG import"

# Verify import success
verify_table "kg_entities" 1000 "kg_entities"
check_success "kg_entities verification"

verify_table "kg_relationships" 4000 "kg_relationships" 
check_success "kg_relationships verification"

print_status "$GREEN" "✅ Phase 2 Complete - AutoSchemaKG imported"

# ============================================================================
# PHASE 3: DATABASE FACTORIZATION  
# ============================================================================
print_status "$YELLOW" "\n🔧 PHASE 3: DATABASE FACTORIZATION"

# Create factorization script
cat > prp_scripts/factorize_database.py << 'EOF'
#!/usr/bin/env python3
import sqlite3
from datetime import datetime

def factorize_regulatory_refs():
    print("FACTORIZING regulatory_refs INTO NORMALIZED TABLES")
    print("=" * 60)
    
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Get original count
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
    original_count = cursor.fetchone()[0]
    print(f"Original regulatory_refs count: {original_count:,}")
    
    factorization_stats = {}
    
    # STEP 1: Move FORMAL PROVISIONS
    print("\n1. Creating regulatory_provisions_clean...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regulatory_provisions_clean AS
        SELECT 
            id, document_id, ref_type as provision_type, ref_number, 
            ref_context as provision_text, page_number, section_header, 
            text_level, 'formal_provision' as category
        FROM regulatory_refs 
        WHERE ref_type LIKE 'formal_%' 
           OR ref_type LIKE 'provision_%'
           OR ref_type = 'clause|section'
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions_clean")
    provisions_count = cursor.fetchone()[0]
    factorization_stats['regulatory_provisions_clean'] = provisions_count
    print(f"   Moved {provisions_count:,} formal provisions")
    
    # STEP 2: Move CONTEXTUAL GUIDANCE
    print("\n2. Creating contextual_guidance_real...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contextual_guidance_real AS
        SELECT 
            id, document_id, ref_type as guidance_type, ref_number as guidance_title,
            ref_context as guidance_text, page_number, section_header, 
            text_level, 'contextual_guidance' as category
        FROM regulatory_refs
        WHERE ref_type LIKE 'context_%'
           OR ref_type LIKE 'informal_%'
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM contextual_guidance_real")
    guidance_count = cursor.fetchone()[0]
    factorization_stats['contextual_guidance_real'] = guidance_count
    print(f"   Moved {guidance_count:,} contextual guidance entries")
    
    # STEP 3: Move VISUAL ELEMENTS
    print("\n3. Creating visual_elements_real...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visual_elements_real AS
        SELECT 
            id, document_id, ref_type as visual_type,
            ref_context as visual_description, page_number, section_header,
            ref_number as visual_caption, 'visual_element' as category
        FROM regulatory_refs
        WHERE ref_type LIKE 'autoschema_%'
           OR ref_type = 'visual_reference'
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM visual_elements_real")
    visual_count = cursor.fetchone()[0]
    factorization_stats['visual_elements_real'] = visual_count
    print(f"   Moved {visual_count:,} visual elements")
    
    # STEP 4: Enhance development_controls
    print("\n4. Enhancing development_controls...")
    cursor.execute('''
        INSERT OR IGNORE INTO development_controls 
        (provision_id, control_type, control_subtype, value_text, unit, 
         zone_applicable, conditions, confidence_score, extraction_method)
        SELECT 
            rpc.id, 
            CASE 
                WHEN rpc.provision_text LIKE '%height%' THEN 'height'
                WHEN rpc.provision_text LIKE '%setback%' THEN 'setback' 
                WHEN rpc.provision_text LIKE '%FSR%' OR rpc.provision_text LIKE '%floor space%' THEN 'fsr'
                WHEN rpc.provision_text LIKE '%parking%' THEN 'parking'
                ELSE 'general'
            END as control_type,
            'extracted' as control_subtype,
            rpc.provision_text as value_text,
            CASE 
                WHEN rpc.provision_text LIKE '%metre%' OR rpc.provision_text LIKE '%meter%' THEN 'm'
                WHEN rpc.provision_text LIKE '%storey%' OR rpc.provision_text LIKE '%story%' THEN 'storeys'
                ELSE 'text'
            END as unit,
            'general' as zone_applicable,
            'extracted from provisions' as conditions,
            0.8 as confidence_score,
            'factorization_script' as extraction_method
        FROM regulatory_provisions_clean rpc
        WHERE rpc.provision_type LIKE 'provision_%'
        AND (rpc.provision_text LIKE '%height%' 
             OR rpc.provision_text LIKE '%setback%'
             OR rpc.provision_text LIKE '%FSR%'
             OR rpc.provision_text LIKE '%parking%')
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM development_controls")
    enhanced_controls = cursor.fetchone()[0]
    factorization_stats['development_controls_enhanced'] = enhanced_controls
    print(f"   Enhanced development_controls to {enhanced_controls:,} entries")
    
    # STEP 5: Create regulatory_refs_core
    print("\n5. Creating regulatory_refs_core...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regulatory_refs_core AS
        SELECT * FROM regulatory_refs
        WHERE ref_type NOT LIKE 'formal_%'
          AND ref_type NOT LIKE 'provision_%'
          AND ref_type NOT LIKE 'context_%'
          AND ref_type NOT LIKE 'informal_%'
          AND ref_type NOT LIKE 'relationship_%'
          AND ref_type NOT LIKE 'autoschema_%'
          AND ref_type != 'visual_reference'
          AND ref_type != 'clause|section'
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs_core")
    core_count = cursor.fetchone()[0]
    factorization_stats['regulatory_refs_core'] = core_count
    print(f"   Remaining core references: {core_count:,}")
    
    # Verification
    total_factorized = sum(factorization_stats.values())
    print(f"\nFACTORIZATION VERIFICATION:")
    print(f"   Original regulatory_refs: {original_count:,}")
    print(f"   Total factorized: {total_factorized:,}")
    print(f"   Data preservation: {total_factorized/original_count*100:.1f}%")
    
    if total_factorized >= original_count * 0.95:
        print("   ✅ FACTORIZATION DATA PRESERVATION: ACCEPTABLE")
    else:
        print("   ❌ FACTORIZATION DATA LOSS: CRITICAL ERROR")
        return False
    
    conn.commit()
    
    # Create completion marker
    with open('migration_markers/factorization_completed.marker', 'w') as f:
        f.write(f"Database factorization completed: {datetime.now().isoformat()}\n")
        f.write(f"Original regulatory_refs: {original_count}\n")
        f.write(f"Total factorized: {total_factorized}\n")
        for table, count in factorization_stats.items():
            f.write(f"{table}: {count}\n")
        f.write("Status: SUCCESS\n")
    
    conn.close()
    return True

if __name__ == "__main__":
    success = factorize_regulatory_refs()
    
    if success:
        print("✅ DATABASE FACTORIZATION SUCCESSFUL")
        exit(0)
    else:
        print("❌ DATABASE FACTORIZATION FAILED")
        exit(1)
EOF

# Execute factorization
./venv_linux/Scripts/python.exe prp_scripts/factorize_database.py >> "$LOGFILE" 2>&1
check_success "Database factorization"

# Verify factorization results
verify_table "regulatory_provisions_clean" 7000 "regulatory_provisions_clean"
check_success "regulatory_provisions_clean verification"

verify_table "contextual_guidance_real" 4000 "contextual_guidance_real"
check_success "contextual_guidance_real verification"

print_status "$GREEN" "✅ Phase 3 Complete - Database factorized"

# ============================================================================
# PHASE 4: INDEXING AND OPTIMIZATION
# ============================================================================
print_status "$YELLOW" "\n⚡ PHASE 4: INDEXING AND OPTIMIZATION"

# Create indexes
./venv_linux/Scripts/python.exe -c "
import sqlite3
conn = sqlite3.connect('nsw_planning.db')

indexes = [
    'CREATE INDEX IF NOT EXISTS idx_reg_prov_clean_doc_id ON regulatory_provisions_clean(document_id)',
    'CREATE INDEX IF NOT EXISTS idx_reg_prov_clean_type ON regulatory_provisions_clean(provision_type)',
    'CREATE INDEX IF NOT EXISTS idx_dev_controls_type ON development_controls(control_type)',
    'CREATE INDEX IF NOT EXISTS idx_dev_controls_provision ON development_controls(provision_id)',
    'CREATE INDEX IF NOT EXISTS idx_kg_rel_subject_entity ON kg_relationships(subject_entity_id)',
    'CREATE INDEX IF NOT EXISTS idx_kg_rel_object_entity ON kg_relationships(object_entity_id)',
    'CREATE INDEX IF NOT EXISTS idx_kg_rel_predicate ON kg_relationships(predicate)',
    'CREATE INDEX IF NOT EXISTS idx_kg_entities_name ON kg_entities(entity_name)',
    'CREATE INDEX IF NOT EXISTS idx_context_guid_type ON contextual_guidance_real(guidance_type)'
]

created = 0
for index_sql in indexes:
    try:
        conn.execute(index_sql)
        created += 1
    except Exception as e:
        print(f'Index error: {e}')

conn.commit()
conn.close()
print(f'✅ Created {created} performance indexes')
" >> "$LOGFILE" 2>&1

check_success "Performance indexing"
print_status "$GREEN" "✅ Phase 4 Complete - Performance optimized"

# ============================================================================
# PHASE 5: FINAL VERIFICATION
# ============================================================================
print_status "$YELLOW" "\n🔍 PHASE 5: FINAL VERIFICATION"

# Create verification script
cat > prp_scripts/verify_completion.py << 'EOF'
#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime

def verify_complete_migration():
    print("COMPLETE MIGRATION VERIFICATION")
    print("=" * 60)
    
    # Check marker files
    required_markers = [
        'migration_markers/autoschemakg_import_completed.marker',
        'migration_markers/factorization_completed.marker'
    ]
    
    print("\n1. CHECKING COMPLETION MARKERS:")
    for marker in required_markers:
        if os.path.exists(marker):
            print(f"   ✅ {marker}")
        else:
            print(f"   ❌ MISSING: {marker}")
            return False
    
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Verify table populations
    print("\n2. VERIFYING TABLE POPULATIONS:")
    expected_populations = {
        'kg_entities': 1000,
        'kg_relationships': 4000,
        'regulatory_provisions_clean': 7000,
        'contextual_guidance_real': 4000,
        'development_controls': 200,
        'visual_elements_real': 1900
    }
    
    verification_passed = True
    
    for table, min_expected in expected_populations.items():
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            if count >= min_expected:
                print(f"   ✅ {table}: {count:,} (expected ≥{min_expected:,})")
            else:
                print(f"   ❌ {table}: {count:,} (expected ≥{min_expected:,}) - INSUFFICIENT")
                verification_passed = False
        except Exception as e:
            print(f"   ❌ {table}: ERROR - {e}")
            verification_passed = False
    
    # Test semantic queries
    print("\n3. TESTING SEMANTIC QUERY CAPABILITY:")
    try:
        cursor.execute('''
            SELECT COUNT(*) FROM kg_relationships kr
            JOIN kg_entities e1 ON kr.subject_entity_id = e1.id
            JOIN kg_entities e2 ON kr.object_entity_id = e2.id
            WHERE kr.predicate IN ('protect', 'requires', 'must', 'limited by')
        ''')
        traversal_results = cursor.fetchone()[0]
        
        if traversal_results >= 100:
            print(f"   ✅ Graph traversal working: {traversal_results:,} semantic relationships")
        else:
            print(f"   ❌ Graph traversal insufficient: {traversal_results:,} relationships")
            verification_passed = False
            
    except Exception as e:
        print(f"   ❌ Graph traversal error: {e}")
        verification_passed = False
    
    conn.close()
    
    if verification_passed:
        print(f"\n{'='*60}")
        print("✅ ALL VERIFICATION TESTS PASSED")
        print("✅ DATABASE FACTORIZATION AND OPTIMIZATION COMPLETE")
        
        # Create final completion marker
        with open('migration_markers/PRP_D_COMPLETE.marker', 'w') as f:
            f.write(f"PRP-D Database Factorization COMPLETED: {datetime.now().isoformat()}\n")
            f.write("All verification tests passed\n")
            f.write("Database ready for intelligent compliance queries\n")
            f.write("Status: SUCCESS\n")
        
        return True
    else:
        print("❌ VERIFICATION FAILED - MIGRATION INCOMPLETE")
        return False

if __name__ == "__main__":
    success = verify_complete_migration()
    exit(0 if success else 1)
EOF

# Execute verification
./venv_linux/Scripts/python.exe prp_scripts/verify_completion.py >> "$LOGFILE" 2>&1
check_success "Final verification"

# ============================================================================
# COMPLETION STATUS
# ============================================================================

if [ -f "migration_markers/PRP_D_COMPLETE.marker" ]; then
    print_status "$GREEN" "\n🎉 PRP-D DATABASE FACTORIZATION COMPLETE! 🎉"
    print_status "$GREEN" "============================================="
    
    # Show completion summary
    ./venv_linux/Scripts/python.exe -c "
import sqlite3
conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

print('FINAL DATABASE STATE:')
tables = [
    ('kg_entities', 'AutoSchemaKG entities'),
    ('kg_relationships', 'AutoSchemaKG relationships'),
    ('regulatory_provisions_clean', 'Formal provisions'),
    ('contextual_guidance_real', 'Contextual guidance'),
    ('development_controls', 'Development controls'),
    ('visual_elements_real', 'Visual elements'),
    ('regulatory_refs', 'Original regulatory_refs (should be unchanged)')
]

for table, desc in tables:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'  {desc}: {count:,}')
    except:
        print(f'  {desc}: TABLE NOT FOUND')

conn.close()
" | tee -a "$LOGFILE"
    
    print_status "$GREEN" "============================================="
    print_status "$GREEN" "✅ AutoSchemaKG imported successfully"
    print_status "$GREEN" "✅ Database factorized into normalized tables"
    print_status "$GREEN" "✅ Query performance optimized with indexes"
    print_status "$GREEN" "✅ Intelligent compliance queries enabled"
    print_status "$GREEN" "✅ All verification tests passed"
    print_status "$GREEN" ""
    print_status "$GREEN" "DATABASE NOW READY FOR INTELLIGENT DEVELOPMENT COMPLIANCE QUERIES"
    print_status "$GREEN" "============================================="
    
    log "PRP-D execution completed successfully"
    print_status "$BLUE" "📋 Execution log saved to: $LOGFILE"
    print_status "$BLUE" "📋 Database backup saved to: $BACKUP_NAME"
    
    exit 0
else
    print_status "$RED" "❌ PRP-D EXECUTION FAILED"
    print_status "$RED" "Check $LOGFILE for detailed error information"
    print_status "$RED" "Database backup available at: $BACKUP_NAME"
    
    log "PRP-D execution failed"
    exit 1
fi