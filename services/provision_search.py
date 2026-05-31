#!/usr/bin/env python3
"""
Provision Search Service
Provides intelligent search and filtering for regulatory provisions from the database
"""

import argparse
import json
import sqlite3
import sys
import time
from typing import Dict, List, Optional
import os

def get_database_path():
    """Get the path to the NSW planning database"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'nsw_planning.db')
    if os.path.exists(db_path):
        return db_path

    # Try alternative paths
    alt_paths = [
        os.path.join(current_dir, '..', 'nsw_planning.db'),
        os.path.join(current_dir, '..', 'database', 'nsw_planning.db')
    ]

    for path in alt_paths:
        if os.path.exists(path):
            return path

    return None

def search_provisions(
    query: str,
    document_types: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    zones: Optional[List[str]] = None,
    development_types: Optional[List[str]] = None,
    limit: int = 50
) -> Dict:
    """Search regulatory provisions in the database"""

    start_time = time.time()
    db_path = get_database_path()

    if not db_path:
        return {
            "provisions": [],
            "total_count": 0,
            "search_metadata": {
                "query": query,
                "filters_applied": {
                    "document_types": document_types,
                    "categories": categories,
                    "zones": zones,
                    "development_types": development_types
                },
                "search_time_ms": 0,
                "error": "Database not found"
            }
        }

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build the search query
        base_query = """
        SELECT
            id,
            clause_number,
            clause_title,
            content,
            document_type,
            document_name,
            authority_level,
            category,
            subcategory
        FROM regulatory_provisions
        WHERE 1=1
        """

        params = []

        # Add text search
        if query and query.strip():
            base_query += " AND (content LIKE ? OR clause_title LIKE ? OR clause_number LIKE ?)"
            search_term = f"%{query.strip()}%"
            params.extend([search_term, search_term, search_term])

        # Add document type filter
        if document_types:
            placeholders = ','.join(['?' for _ in document_types])
            base_query += f" AND document_type IN ({placeholders})"
            params.extend(document_types)

        # Add category filter
        if categories:
            placeholders = ','.join(['?' for _ in categories])
            base_query += f" AND category IN ({placeholders})"
            params.extend(categories)

        # Add limit
        base_query += f" ORDER BY clause_number LIMIT {limit}"

        print(f"Executing query: {base_query}", file=sys.stderr)
        print(f"With params: {params}", file=sys.stderr)

        cursor.execute(base_query, params)
        rows = cursor.fetchall()

        # Convert to dictionaries
        provisions = []
        for row in rows:
            provisions.append({
                "id": row["id"],
                "clause_number": row["clause_number"],
                "clause_title": row["clause_title"],
                "content": row["content"],
                "document_type": row["document_type"],
                "document_name": row["document_name"],
                "authority_level": row["authority_level"],
                "category": row["category"],
                "subcategory": row["subcategory"]
            })

        # Get total count
        count_query = base_query.replace("SELECT id,clause_number,clause_title,content,document_type,document_name,authority_level,category,subcategory", "SELECT COUNT(*)")
        count_query = count_query.replace(f" ORDER BY clause_number LIMIT {limit}", "")
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        conn.close()

        search_time_ms = int((time.time() - start_time) * 1000)

        return {
            "provisions": provisions,
            "total_count": total_count,
            "search_metadata": {
                "query": query,
                "filters_applied": {
                    "document_types": document_types,
                    "categories": categories,
                    "zones": zones,
                    "development_types": development_types
                },
                "search_time_ms": search_time_ms,
                "database_path": db_path
            }
        }

    except Exception as e:
        return {
            "provisions": [],
            "total_count": 0,
            "search_metadata": {
                "query": query,
                "filters_applied": {
                    "document_types": document_types,
                    "categories": categories,
                    "zones": zones,
                    "development_types": development_types
                },
                "search_time_ms": 0,
                "error": str(e)
            }
        }

def main():
    parser = argparse.ArgumentParser(description='Search regulatory provisions')
    parser.add_argument('--query', required=True, help='Search query')
    parser.add_argument('--document-types', help='Comma-separated document types')
    parser.add_argument('--categories', help='Comma-separated categories')
    parser.add_argument('--zones', help='Comma-separated zones')
    parser.add_argument('--development-types', help='Comma-separated development types')
    parser.add_argument('--format', default='json', help='Output format (json)')
    parser.add_argument('--limit', type=int, default=50, help='Result limit')

    args = parser.parse_args()

    # Parse filters
    document_types = args.document_types.split(',') if args.document_types else None
    categories = args.categories.split(',') if args.categories else None
    zones = args.zones.split(',') if args.zones else None
    development_types = args.development_types.split(',') if args.development_types else None

    # Perform search
    result = search_provisions(
        query=args.query,
        document_types=document_types,
        categories=categories,
        zones=zones,
        development_types=development_types,
        limit=args.limit
    )

    # Output result
    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print(f"Found {result['total_count']} provisions")
        for provision in result['provisions']:
            print(f"- {provision['clause_number']}: {provision['clause_title']}")

if __name__ == '__main__':
    main()