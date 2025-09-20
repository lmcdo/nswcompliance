# PRP-V2: Version Service Layer

## Objective
Implement a Python service layer for managing document versions, providing clean abstractions for version operations.

## Prerequisites
- PRP-V1 completed (database schema created)
- Python environment with psycopg2, pydantic
- Database connection configured

## Implementation

### File: services/version_manager.py
```python
#!/usr/bin/env python3
"""
Version Management Service for NSW Planning Documents
Handles version tracking for SEPP, LEP, and DCP documents
"""

from typing import Optional, List, Dict, Literal, Tuple
from datetime import date, datetime
from enum import Enum
import logging
import json
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
from db_config import get_connection

logger = logging.getLogger(__name__)

class DocumentType(str, Enum):
    SEPP = "SEPP"
    LEP = "LEP"
    DCP = "DCP"

class VersionStatus(str, Enum):
    CURRENT = "CURRENT"
    PREVIOUS = "PREVIOUS"
    ARCHIVED = "ARCHIVED"

class DocumentVersion(BaseModel):
    """Document version model"""
    id: Optional[int] = None
    document_type: DocumentType
    document_identifier: str
    version_number: str
    version_status: VersionStatus
    effective_date: date
    superseded_date: Optional[date] = None
    document_url: Optional[str] = None
    change_summary: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    created_by: str = "system"

class VersionManager:
    """Manages document versions in the database"""

    def __init__(self):
        self.conn = None
        self._ensure_connection()

    def _ensure_connection(self):
        """Ensure database connection is active"""
        if not self.conn or self.conn.closed:
            self.conn = get_connection()

    def get_current_version(self,
                          document_type: DocumentType,
                          document_identifier: str) -> Optional[DocumentVersion]:
        """Get the current version of a document"""
        self._ensure_connection()

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM versions.document_versions
                WHERE document_type = %s
                  AND document_identifier = %s
                  AND version_status = %s
                LIMIT 1
            """, (document_type.value, document_identifier, VersionStatus.CURRENT.value))

            row = cursor.fetchone()
            if row:
                return DocumentVersion(**row)
            return None

    def get_version_at_date(self,
                          document_type: DocumentType,
                          document_identifier: str,
                          target_date: date) -> Optional[DocumentVersion]:
        """Get version that was effective at a specific date"""
        self._ensure_connection()

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM versions.document_versions
                WHERE document_type = %s
                  AND document_identifier = %s
                  AND effective_date <= %s
                  AND (superseded_date IS NULL OR superseded_date > %s)
                ORDER BY effective_date DESC
                LIMIT 1
            """, (document_type.value, document_identifier, target_date, target_date))

            row = cursor.fetchone()
            if row:
                return DocumentVersion(**row)
            return None

    def create_new_version(self,
                         document_type: DocumentType,
                         document_identifier: str,
                         version_number: str,
                         effective_date: date,
                         document_url: Optional[str] = None,
                         change_summary: Optional[str] = None,
                         created_by: str = "system") -> DocumentVersion:
        """Create a new version, archiving the current one"""
        self._ensure_connection()

        with self.conn.cursor() as cursor:
            # Begin transaction
            cursor.execute("BEGIN")

            try:
                # Archive current version to previous
                cursor.execute("""
                    UPDATE versions.document_versions
                    SET version_status = %s,
                        superseded_date = %s
                    WHERE document_type = %s
                      AND document_identifier = %s
                      AND version_status = %s
                """, (VersionStatus.PREVIOUS.value, effective_date,
                     document_type.value, document_identifier, VersionStatus.CURRENT.value))

                # Archive previous version to archived
                cursor.execute("""
                    UPDATE versions.document_versions
                    SET version_status = %s
                    WHERE document_type = %s
                      AND document_identifier = %s
                      AND version_status = %s
                      AND id != (
                          SELECT id FROM versions.document_versions
                          WHERE document_type = %s
                            AND document_identifier = %s
                            AND version_status = %s
                          ORDER BY effective_date DESC
                          LIMIT 1
                      )
                """, (VersionStatus.ARCHIVED.value, document_type.value, document_identifier,
                     VersionStatus.PREVIOUS.value, document_type.value, document_identifier,
                     VersionStatus.PREVIOUS.value))

                # Insert new current version
                cursor.execute("""
                    INSERT INTO versions.document_versions
                    (document_type, document_identifier, version_number, version_status,
                     effective_date, document_url, change_summary, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (document_type.value, document_identifier, version_number,
                     VersionStatus.CURRENT.value, effective_date, document_url,
                     change_summary, created_by))

                new_version = cursor.fetchone()

                # Update regulatory provisions to reference new version
                cursor.execute("""
                    UPDATE regulatory_provisions
                    SET version_id = %s,
                        is_current = true,
                        version_effective_date = %s
                    WHERE document_id LIKE %s
                      AND is_current = true
                """, (new_version[0], effective_date, f'%{document_identifier}%'))

                # Commit transaction
                cursor.execute("COMMIT")

                logger.info(f"Created new version {version_number} for {document_identifier}")
                return self.get_current_version(document_type, document_identifier)

            except Exception as e:
                cursor.execute("ROLLBACK")
                logger.error(f"Failed to create version: {e}")
                raise

    def get_version_comparison(self,
                             document_type: DocumentType,
                             document_identifier: str) -> Tuple[Optional[DocumentVersion],
                                                                Optional[DocumentVersion]]:
        """Get current and previous versions for comparison"""
        self._ensure_connection()

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM versions.document_versions
                WHERE document_type = %s
                  AND document_identifier = %s
                  AND version_status IN (%s, %s)
                ORDER BY
                  CASE version_status
                    WHEN %s THEN 1
                    WHEN %s THEN 2
                  END
            """, (document_type.value, document_identifier,
                 VersionStatus.CURRENT.value, VersionStatus.PREVIOUS.value,
                 VersionStatus.CURRENT.value, VersionStatus.PREVIOUS.value))

            rows = cursor.fetchall()
            current = DocumentVersion(**rows[0]) if len(rows) > 0 else None
            previous = DocumentVersion(**rows[1]) if len(rows) > 1 else None

            return current, previous

    def bulk_mark_provisions_version(self,
                                   version_id: int,
                                   provision_ids: List[int],
                                   is_current: bool = True):
        """Mark multiple provisions with a version"""
        self._ensure_connection()

        with self.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE regulatory_provisions
                SET version_id = %s,
                    is_current = %s
                WHERE id = ANY(%s)
            """, (version_id, is_current, provision_ids))

            self.conn.commit()
            logger.info(f"Updated {cursor.rowcount} provisions with version {version_id}")

    def get_version_statistics(self) -> Dict:
        """Get statistics about versions in the system"""
        self._ensure_connection()

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT
                    document_type,
                    COUNT(CASE WHEN version_status = 'CURRENT' THEN 1 END) as current_count,
                    COUNT(CASE WHEN version_status = 'PREVIOUS' THEN 1 END) as previous_count,
                    COUNT(CASE WHEN version_status = 'ARCHIVED' THEN 1 END) as archived_count,
                    COUNT(*) as total_versions
                FROM versions.document_versions
                GROUP BY document_type
            """)

            stats = cursor.fetchall()
            return {row['document_type']: dict(row) for row in stats}

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
```

### File: services/version_aware_query.py
```python
#!/usr/bin/env python3
"""
Version-aware query wrapper for regulatory provisions
"""

from typing import Optional, List, Dict
from datetime import date
from db_config import get_connection
import logging

logger = logging.getLogger(__name__)

class VersionAwareQuery:
    """Wraps existing queries with version awareness"""

    @staticmethod
    def get_provisions(document_id: Optional[str] = None,
                       version: str = "current",
                       as_at_date: Optional[date] = None) -> List[Dict]:
        """Get provisions with version filtering"""

        conn = get_connection()
        with conn.cursor() as cursor:
            base_query = """
                SELECT
                    rp.*,
                    dv.version_number,
                    dv.effective_date,
                    dv.version_status
                FROM regulatory_provisions rp
                LEFT JOIN versions.document_versions dv ON rp.version_id = dv.id
                WHERE 1=1
            """

            params = []

            # Add document filter
            if document_id:
                base_query += " AND rp.document_id = %s"
                params.append(document_id)

            # Add version filter
            if as_at_date:
                base_query += """
                    AND dv.effective_date <= %s
                    AND (dv.superseded_date IS NULL OR dv.superseded_date > %s)
                """
                params.extend([as_at_date, as_at_date])
            elif version == "current":
                base_query += " AND rp.is_current = true"
            elif version == "previous":
                base_query += " AND dv.version_status = 'PREVIOUS'"

            cursor.execute(base_query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def validate_provision_version(provision_id: int,
                                  target_date: date) -> bool:
        """Check if a provision was valid at a specific date"""

        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM regulatory_provisions rp
                JOIN versions.document_versions dv ON rp.version_id = dv.id
                WHERE rp.id = %s
                  AND dv.effective_date <= %s
                  AND (dv.superseded_date IS NULL OR dv.superseded_date > %s)
            """, (provision_id, target_date, target_date))

            count = cursor.fetchone()[0]
            return count > 0
```

## Verification Checklist

### Service Implementation
- [ ] VersionManager class created
- [ ] All CRUD operations working
- [ ] Version transitions handled correctly
- [ ] Transaction rollback on errors
- [ ] Logging implemented

### Query Wrapper
- [ ] Version-aware queries working
- [ ] Date-based filtering accurate
- [ ] Backward compatibility maintained
- [ ] Performance acceptable

### Error Handling
- [ ] Database connection errors handled
- [ ] Transaction failures rolled back
- [ ] Meaningful error messages
- [ ] No data corruption on failure

## Testing Commands

```python
# Test version creation
from services.version_manager import VersionManager, DocumentType

vm = VersionManager()
version = vm.create_new_version(
    DocumentType.LEP,
    "Inner-West-LEP-2022",
    "v1.1",
    date(2024, 3, 1),
    change_summary="March 2024 amendments"
)
print(f"Created version: {version.version_number}")

# Test version retrieval
current = vm.get_current_version(DocumentType.LEP, "Inner-West-LEP-2022")
print(f"Current version: {current.version_number}")

# Test date-based query
old_version = vm.get_version_at_date(
    DocumentType.LEP,
    "Inner-West-LEP-2022",
    date(2023, 6, 1)
)
print(f"Version at June 2023: {old_version.version_number if old_version else 'None'}")
```

## Success Criteria

1. ✅ Version creation completes in <500ms
2. ✅ Version queries return in <100ms
3. ✅ Provisions correctly linked to versions
4. ✅ Audit log captures all operations
5. ✅ No breaking changes to existing code

## Next Steps

1. Run `verify_v2_service.py` to validate service
2. Proceed to PRP-V3_API_INTEGRATION.md
3. Update execution log with results