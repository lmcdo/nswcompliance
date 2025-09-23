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
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
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

        current = self.get_current_version(document_type, document_identifier)

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM versions.document_versions
                WHERE document_type = %s
                  AND document_identifier = %s
                  AND version_status = %s
                ORDER BY effective_date DESC
                LIMIT 1
            """, (document_type.value, document_identifier, VersionStatus.PREVIOUS.value))

            row = cursor.fetchone()
            previous = DocumentVersion(**row) if row else None

        return current, previous

    def get_version_statistics(self) -> Dict[str, any]:
        """Get version tracking statistics"""
        self._ensure_connection()

        with self.conn.cursor() as cursor:
            stats = {}

            # Total versions by type
            cursor.execute("""
                SELECT document_type, version_status, COUNT(*)
                FROM versions.document_versions
                GROUP BY document_type, version_status
                ORDER BY document_type, version_status
            """)
            version_counts = cursor.fetchall()
            stats['version_counts'] = [
                {'type': row[0], 'status': row[1], 'count': row[2]}
                for row in version_counts
            ]

            # Recent version changes
            cursor.execute("""
                SELECT document_type, document_identifier, version_number, effective_date
                FROM versions.document_versions
                WHERE version_status = 'CURRENT'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            recent_versions = cursor.fetchall()
            stats['recent_versions'] = [
                {
                    'type': row[0],
                    'identifier': row[1],
                    'version': row[2],
                    'effective_date': row[3].isoformat() if row[3] else None
                }
                for row in recent_versions
            ]

            # Version coverage by document type
            cursor.execute("""
                SELECT document_type, COUNT(DISTINCT document_identifier) as document_count
                FROM versions.document_versions
                GROUP BY document_type
            """)
            coverage = cursor.fetchall()
            stats['document_coverage'] = [
                {'type': row[0], 'document_count': row[1]}
                for row in coverage
            ]

        return stats

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()