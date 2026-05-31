#!/usr/bin/env python3
"""
Development Permissions Database Access Layer
Provides access to consolidated development type permissions for API integration
"""

from db_config import get_connection  # Unified PostgreSQL connection
import json
from typing import Dict, List, Optional, Tuple
import os
import psycopg2

class DevelopmentPermissionsDB:
    def __init__(self, db_path: Optional[str] = None):
        """Initialize development permissions database access"""
        if db_path is None:
            # Default to the main database path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(current_dir, '..', 'nsw_planning.db')
        else:
            self.db_path = db_path

    def get_zone_permissions(self, zone: str) -> Dict:
        """Get all development permissions for a zone from consolidated dataset"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Get all permissions for the zone, grouped by status
            cursor.execute("""
            SELECT DISTINCT development_type, provision_type, 'regulatory_provisions' as source_type, zone_confidence
            FROM regulatory_provisions
            WHERE zone = %s AND development_type IS NOT NULL AND is_current = true
            ORDER BY zone_confidence DESC, development_type
            LIMIT 50
            """, (zone,))

            results = cursor.fetchall()

            # Group by permission status
            permissions = {
                'permitted_without_consent': [],
                'permitted_with_consent': [],
                'prohibited': [],
                'source_summary': {},
                'total_combinations': len(results),
                'coverage_note': None
            }

            source_counts = {}

            for dev_type, provision_type, source_type, confidence in results:
                # Clean up development type names
                clean_dev_type = dev_type.strip() if dev_type else 'general'
                confidence = confidence or 0.5

                # Infer permission status from provision type
                if provision_type and 'permitted' in provision_type.lower():
                    category = 'permitted_without_consent'
                elif provision_type and ('consent' in provision_type.lower() or 'approval' in provision_type.lower()):
                    category = 'permitted_with_consent'
                elif provision_type and 'prohibited' in provision_type.lower():
                    category = 'prohibited'
                else:
                    # Default to consent required for unknown provisions
                    category = 'permitted_with_consent'

                permissions[category].append({
                    'development_type': clean_dev_type,
                    'source': source_type,
                    'confidence': confidence,
                    'provision_type': provision_type
                })

                # Track source distribution
                source_counts[source_type] = source_counts.get(source_type, 0) + 1

            permissions['source_summary'] = source_counts

            # Add coverage note
            if len(results) == 0:
                permissions['coverage_note'] = f"No development permissions found for zone {zone}"
            elif len(results) < 5:
                permissions['coverage_note'] = f"Limited coverage for zone {zone} - consider additional data sources"
            else:
                permissions['coverage_note'] = f"Good coverage for zone {zone} with {len(results)} combinations"

            return permissions

        except psycopg2.Error as e:
            return {
                'error': f'Database error: {str(e)}',
                'permitted_without_consent': [],
                'permitted_with_consent': [],
                'prohibited': [],
                'source_summary': {},
                'total_combinations': 0
            }
        finally:
            conn.close()

    def check_development_feasibility(self, zone: str, development_type: str) -> Dict:
        """Check if specific development type is allowed in zone"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Clean up development type (remove common variations)
            clean_dev_type = development_type.strip().lower()

            cursor.execute("""
            SELECT provision_text, 'regulatory_provisions' as source_type,
                   zone_confidence, provision_type
            FROM regulatory_provisions
            WHERE zone = %s AND (
                LOWER(development_type) = %s OR
                LOWER(development_type) LIKE %s OR
                LOWER(development_type) LIKE %s
            )
            AND is_current = true
            ORDER BY zone_confidence DESC
            LIMIT 5
            """, (zone, clean_dev_type, f'%{clean_dev_type}%', f'{clean_dev_type}%'))

            results = cursor.fetchall()

            if not results:
                return {
                    'development_type': development_type,
                    'zone': zone,
                    'permission_status': 'unknown',
                    'confidence': 'low',
                    'message': f'No specific permission found for {development_type} in {zone}',
                    'source_provision': None,
                    'alternatives': self._get_similar_development_types(cursor, zone, development_type)
                }

            # Return the highest confidence result
            best_result = results[0]
            provision_text, source_type, zone_confidence, provision_type = best_result

            # Determine confidence level based on zone_confidence
            zone_confidence = zone_confidence or 0.5
            if zone_confidence >= 0.9:
                confidence_level = 'high'
            elif zone_confidence >= 0.7:
                confidence_level = 'medium'
            else:
                confidence_level = 'low'

            # Infer permission status from provision text
            provision_lower = provision_text.lower()
            if 'permitted' in provision_lower and 'not permitted' not in provision_lower:
                permission_status = 'permitted'
            elif 'prohibited' in provision_lower or 'not permitted' in provision_lower:
                permission_status = 'prohibited'
            elif 'consent' in provision_lower:
                permission_status = 'consent_required'
            else:
                permission_status = 'assessment_required'

            return {
                'development_type': development_type,
                'zone': zone,
                'permission_status': permission_status,
                'confidence': confidence_level,
                'confidence_score': zone_confidence,
                'source_type': source_type,
                'provision_text': provision_text[:200] + '...' if len(provision_text) > 200 else provision_text,
                'provision_type': provision_type,
                'message': f'{development_type} in {zone} zone: {permission_status}',
                'total_provisions_found': len(results)
            }

        except psycopg2.Error as e:
            return {
                'development_type': development_type,
                'zone': zone,
                'permission_status': 'error',
                'confidence': 'low',
                'message': f'Database error: {str(e)}',
                'source_provision': None
            }
        finally:
            conn.close()

    def _get_similar_development_types(self, cursor, zone: str, development_type: str) -> List[str]:
        """Get similar development types that might be relevant"""
        try:
            # Look for partial matches in the same zone
            cursor.execute("""
            SELECT DISTINCT development_type
            FROM development_permissions
            WHERE zone = ? AND development_type IS NOT NULL
            LIMIT 5
            """, (zone,))

            results = cursor.fetchall()
            return [row[0].strip('[]"') for row in results]

        except psycopg2.Error:
            return []

    def get_basic_conditions(self, zone: str, dev_type: str) -> List[str]:
        """Return basic conditions from consolidated dataset"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
            SELECT conditions
            FROM development_permissions
            WHERE zone = ? AND development_type = ? AND conditions IS NOT NULL
            ORDER BY confidence_score DESC
            """, (zone, dev_type))

            results = cursor.fetchall()
            conditions = [row[0] for row in results if row[0] and row[0].strip()]

            return conditions[:3]  # Return up to 3 conditions

        except psycopg2.Error:
            return []
        finally:
            conn.close()

    def get_database_stats(self) -> Dict:
        """Get statistics about the development permissions database"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            stats = {}

            # Total combinations
            cursor.execute("SELECT COUNT(*) FROM development_permissions")
            stats['total_combinations'] = cursor.fetchone()[0]

            # Zone coverage
            cursor.execute("SELECT COUNT(DISTINCT zone) FROM development_permissions WHERE zone IS NOT NULL")
            stats['zones_covered'] = cursor.fetchone()[0]

            # Development type coverage
            cursor.execute("SELECT COUNT(DISTINCT development_type) FROM development_permissions WHERE development_type IS NOT NULL")
            stats['development_types_covered'] = cursor.fetchone()[0]

            # Source distribution
            cursor.execute("""
            SELECT source_type, COUNT(*) as count
            FROM development_permissions
            GROUP BY source_type
            """)
            stats['source_distribution'] = dict(cursor.fetchall())

            # Permission distribution
            cursor.execute("""
            SELECT permission_status, COUNT(*) as count
            FROM development_permissions
            WHERE permission_status IS NOT NULL
            GROUP BY permission_status
            """)
            stats['permission_distribution'] = dict(cursor.fetchall())

            return stats

        except psycopg2.Error as e:
            return {'error': f'Database error: {str(e)}'}
        finally:
            conn.close()

def test_development_permissions_db():
    """Test the development permissions database functionality"""
    db = DevelopmentPermissionsDB()

    print("=== Testing Development Permissions DB ===")

    # Test database stats
    print("\n1. Database Statistics:")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Test zone permissions
    print("\n2. Zone Permissions (R2):")
    r2_permissions = db.get_zone_permissions('R2')
    print(f"   Total combinations: {r2_permissions['total_combinations']}")
    print(f"   Permitted: {len(r2_permissions['permitted_without_consent'])}")
    print(f"   Consent required: {len(r2_permissions['permitted_with_consent'])}")
    print(f"   Prohibited: {len(r2_permissions['prohibited'])}")
    print(f"   Sources: {r2_permissions['source_summary']}")

    # Test feasibility check
    print("\n3. Feasibility Check (dwelling_house in R1):")
    feasibility = db.check_development_feasibility('R1', 'dwelling_house')
    print(f"   Result: {feasibility['permission_status']}")
    print(f"   Confidence: {feasibility['confidence']}")
    print(f"   Message: {feasibility['message']}")

    # Test feasibility check (prohibited case)
    print("\n4. Feasibility Check (general_industry in R1):")
    feasibility2 = db.check_development_feasibility('R1', 'general_industry')
    print(f"   Result: {feasibility2['permission_status']}")
    print(f"   Confidence: {feasibility2['confidence']}")
    print(f"   Message: {feasibility2['message']}")

if __name__ == '__main__':
    test_development_permissions_db()