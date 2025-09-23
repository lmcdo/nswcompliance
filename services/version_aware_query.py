#!/usr/bin/env python3
"""
Version-aware query wrapper for regulatory provisions
"""

from typing import Optional, List, Dict
from datetime import date
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
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

            # Add version filtering
            if as_at_date:
                # Get provisions valid at specific date
                base_query += """
                    AND (dv.effective_date <= %s)
                    AND (dv.superseded_date IS NULL OR dv.superseded_date > %s)
                """
                params.extend([as_at_date, as_at_date])
            elif version == "current":
                # Get only current provisions
                base_query += " AND (rp.is_current IS NULL OR rp.is_current = true)"
            elif version == "previous":
                # Get previous version provisions
                base_query += " AND dv.version_status = 'PREVIOUS'"
            elif version == "all":
                # No version filtering
                pass
            else:
                # Specific version number
                base_query += " AND dv.version_number = %s"
                params.append(version)

            base_query += " ORDER BY rp.id"

            cursor.execute(base_query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_development_controls(zone: Optional[str] = None,
                               version: str = "current",
                               as_at_date: Optional[date] = None) -> List[Dict]:
        """Get development controls with version filtering"""

        conn = get_connection()
        with conn.cursor() as cursor:
            base_query = """
                SELECT
                    dc.*,
                    dv.version_number,
                    dv.effective_date,
                    dv.version_status
                FROM development_controls dc
                LEFT JOIN versions.document_versions dv ON dc.version_id = dv.id
                WHERE 1=1
            """

            params = []

            # Add zone filter
            if zone:
                base_query += " AND dc.zone = %s"
                params.append(zone)

            # Add version filtering (same logic as provisions)
            if as_at_date:
                base_query += """
                    AND (dv.effective_date <= %s)
                    AND (dv.superseded_date IS NULL OR dv.superseded_date > %s)
                """
                params.extend([as_at_date, as_at_date])
            elif version == "current":
                base_query += " AND (dc.is_current IS NULL OR dc.is_current = true)"
            elif version == "previous":
                base_query += " AND dv.version_status = 'PREVIOUS'"
            elif version == "all":
                pass
            else:
                base_query += " AND dv.version_number = %s"
                params.append(version)

            base_query += " ORDER BY dc.id"

            cursor.execute(base_query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_quantitative_standards(zone: Optional[str] = None,
                                 development_type: Optional[str] = None,
                                 version: str = "current",
                                 as_at_date: Optional[date] = None) -> List[Dict]:
        """Get quantitative standards with version filtering"""

        conn = get_connection()
        with conn.cursor() as cursor:
            base_query = """
                SELECT
                    qs.*,
                    dv.version_number,
                    dv.effective_date,
                    dv.version_status
                FROM quantitative_standards qs
                LEFT JOIN versions.document_versions dv ON qs.version_id = dv.id
                WHERE 1=1
            """

            params = []

            # Add zone filter
            if zone:
                base_query += " AND qs.zone = %s"
                params.append(zone)

            # Add development type filter
            if development_type:
                base_query += " AND qs.development_type = %s"
                params.append(development_type)

            # Add version filtering
            if as_at_date:
                base_query += """
                    AND (dv.effective_date <= %s)
                    AND (dv.superseded_date IS NULL OR dv.superseded_date > %s)
                """
                params.extend([as_at_date, as_at_date])
            elif version == "current":
                base_query += " AND (qs.is_current IS NULL OR qs.is_current = true)"
            elif version == "previous":
                base_query += " AND dv.version_status = 'PREVIOUS'"
            elif version == "all":
                pass
            else:
                base_query += " AND dv.version_number = %s"
                params.append(version)

            base_query += " ORDER BY qs.id"

            cursor.execute(base_query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_version_summary(document_type: Optional[str] = None) -> List[Dict]:
        """Get summary of available versions"""

        conn = get_connection()
        with conn.cursor() as cursor:
            base_query = """
                SELECT
                    document_type,
                    document_identifier,
                    version_number,
                    version_status,
                    effective_date,
                    superseded_date,
                    created_at
                FROM versions.document_versions
                WHERE 1=1
            """

            params = []

            if document_type:
                base_query += " AND document_type = %s"
                params.append(document_type)

            base_query += """
                ORDER BY document_type, document_identifier,
                         CASE version_status
                           WHEN 'CURRENT' THEN 1
                           WHEN 'PREVIOUS' THEN 2
                           WHEN 'ARCHIVED' THEN 3
                         END,
                         effective_date DESC
            """

            cursor.execute(base_query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def count_provisions_by_version(document_type: Optional[str] = None) -> Dict[str, int]:
        """Count provisions by version status"""

        conn = get_connection()
        with conn.cursor() as cursor:
            base_query = """
                SELECT
                    COALESCE(dv.version_status, 'UNVERSIONED') as version_status,
                    COUNT(*) as provision_count
                FROM regulatory_provisions rp
                LEFT JOIN versions.document_versions dv ON rp.version_id = dv.id
                WHERE 1=1
            """

            params = []

            if document_type:
                base_query += " AND dv.document_type = %s"
                params.append(document_type)

            base_query += " GROUP BY dv.version_status ORDER BY version_status"

            cursor.execute(base_query, params)
            return {row[0]: row[1] for row in cursor.fetchall()}

    @staticmethod
    def get_version_changes(document_identifier: str,
                          limit: int = 10) -> List[Dict]:
        """Get version change history for a document"""

        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    al.action,
                    al.action_details,
                    al.performed_at,
                    al.performed_by,
                    dv.version_number,
                    dv.document_type
                FROM versions.version_audit_log al
                JOIN versions.document_versions dv ON al.version_id = dv.id
                WHERE dv.document_identifier = %s
                ORDER BY al.performed_at DESC
                LIMIT %s
            """, (document_identifier, limit))

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]