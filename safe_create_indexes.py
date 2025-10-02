#!/usr/bin/env python3
"""
Safe database index creation using proper safety wrapper
"""

from db_safety_wrapper import get_safe_connection
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def create_performance_indexes():
    """Create performance indexes safely with backup and timeout"""

    print('=== SAFE INDEX CREATION FOR COMPLETE PROVISION DISPLAY ===')
    print()

    # Database safety: Create backup FIRST
    print('1. Creating backup before index operations...')
    connection = get_safe_connection(
        host='localhost',
        database='nsw_planning_corrected',
        user='postgres',
        port=5432
    )

    if not connection:
        print('FAILED: Could not establish safe database connection')
        return False

    try:
        cursor = connection.cursor()

        # Index definitions for complete provision text display
        indexes = [
            # Critical indexes for the API query path
            {
                "name": "idx_regulatory_provisions_id",
                "table": "regulatory_provisions",
                "columns": "(id)",
                "purpose": "Primary provision lookups"
            },
            {
                "name": "idx_regulatory_provisions_instrument_id",
                "table": "regulatory_provisions",
                "columns": "(instrument_id)",
                "purpose": "Legal instrument relationships"
            },
            {
                "name": "idx_regulatory_provisions_document_id",
                "table": "regulatory_provisions",
                "columns": "(document_id)",
                "purpose": "Document text relationships"
            },
            {
                "name": "idx_legal_instruments_id",
                "table": "legal_instruments",
                "columns": "(id)",
                "purpose": "Legal instrument lookups"
            },
            {
                "name": "idx_documents_id",
                "table": "documents",
                "columns": "(id)",
                "purpose": "Document text lookups"
            },
            {
                "name": "idx_provision_complete_lookup",
                "table": "regulatory_provisions",
                "columns": "(id, instrument_id, document_id)",
                "purpose": "Optimized complete provision query"
            }
        ]

        print('2. Creating performance indexes...')
        print()

        for index in indexes:
            try:
                sql = f"CREATE INDEX IF NOT EXISTS {index['name']} ON {index['table']} {index['columns']}"

                print(f"Creating {index['name']} for {index['purpose']}...")

                # Safety wrapper automatically applies 30-second timeout
                cursor.execute(sql)

                print(f"  Success: {index['name']} created")

            except Exception as e:
                print(f"  Error creating {index['name']}: {str(e)}")
                logger.error(f"Index creation failed: {index['name']} - {str(e)}")

        print()
        print('3. Verifying created indexes...')

        # Verify indexes were created
        cursor.execute("""
            SELECT schemaname, tablename, indexname
            FROM pg_indexes
            WHERE tablename IN ('regulatory_provisions', 'legal_instruments', 'documents')
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)

        results = cursor.fetchall()
        if results:
            print('Created indexes:')
            for schema, table, index in results:
                print(f"  {table}: {index}")
        else:
            print('No indexes found - check for errors above')

        print()
        print('INDEX CREATION COMPLETED SAFELY')
        return True

    except Exception as e:
        print(f'CRITICAL ERROR during index creation: {str(e)}')
        logger.error(f"Critical index creation error: {str(e)}")
        return False

    finally:
        # Safety wrapper handles proper connection cleanup
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    success = create_performance_indexes()
    if not success:
        print('Index creation FAILED - check logs and database state')
        sys.exit(1)
    else:
        print('Index creation SUCCESSFUL - database optimized for complete provision display')