"""
Provision Version Tracking Module

This module provides functions for tracking provision changes and creating
version history when provisions are modified.

Functions:
    calculate_text_hash: Calculate SHA-256 hash of provision text
    detect_provision_changes: Compare existing vs new provisions
    update_provision_with_versioning: Update provision and create new version
    mark_provision_deleted: Mark a provision as deleted
"""

import hashlib
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime


def calculate_text_hash(text: str) -> str:
    """
    Calculate SHA-256 hash of provision text for change detection.

    Args:
        text: The provision text to hash

    Returns:
        Hex string of SHA-256 hash
    """
    if not text:
        return hashlib.sha256(b'').hexdigest()
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def detect_provision_changes(
    existing_provisions: List[Dict[str, Any]],
    new_provisions: List[Dict[str, Any]],
    match_key_func=None
) -> Dict[str, List]:
    """
    Compare existing vs new provisions to detect changes.

    This function identifies:
    - Modified: provisions where text changed
    - Created: new provisions not in existing
    - Deleted: existing provisions not in new
    - Unchanged: provisions with identical text

    Args:
        existing_provisions: List of provisions from database
        new_provisions: List of provisions from extraction
        match_key_func: Function to generate match key (default: document_id + ref_number)

    Returns:
        Dict with keys: modified, created, deleted, unchanged
        Each contains list of provision matches
    """
    if match_key_func is None:
        match_key_func = lambda p: (p.get('document_id', ''), p.get('ref_number', ''))

    # Create lookups
    existing_lookup = {}
    for prov in existing_provisions:
        key = match_key_func(prov)
        existing_lookup[key] = prov

    new_lookup = {}
    for prov in new_provisions:
        key = match_key_func(prov)
        new_lookup[key] = prov

    results = {
        'modified': [],
        'created': [],
        'deleted': [],
        'unchanged': []
    }

    # Check new provisions against existing
    for key, new_prov in new_lookup.items():
        if key in existing_lookup:
            existing = existing_lookup[key]

            # Calculate hashes
            existing_hash = existing.get('text_hash_current')
            if not existing_hash:
                existing_hash = calculate_text_hash(existing.get('provision_text', ''))

            new_hash = calculate_text_hash(new_prov.get('provision_text', ''))

            # Compare hashes
            if existing_hash != new_hash:
                results['modified'].append({
                    'provision_id': existing.get('id'),
                    'document_id': existing.get('document_id'),
                    'ref_number': existing.get('ref_number'),
                    'old_text': existing.get('provision_text', ''),
                    'old_hash': existing_hash,
                    'new_text': new_prov.get('provision_text', ''),
                    'new_hash': new_hash,
                    'new_metadata': new_prov
                })
            else:
                results['unchanged'].append({
                    'provision_id': existing.get('id'),
                    'document_id': existing.get('document_id'),
                    'ref_number': existing.get('ref_number')
                })
        else:
            # New provision
            results['created'].append({
                'document_id': new_prov.get('document_id', ''),
                'ref_number': new_prov.get('ref_number', ''),
                'text': new_prov.get('provision_text', ''),
                'metadata': new_prov
            })

    # Check for deleted provisions
    for key, existing in existing_lookup.items():
        if key not in new_lookup:
            results['deleted'].append({
                'provision_id': existing.get('id'),
                'document_id': existing.get('document_id'),
                'ref_number': existing.get('ref_number'),
                'text': existing.get('provision_text', '')
            })

    return results


def update_provision_with_versioning(
    cur,
    provision_id: int,
    old_text: str,
    old_hash: str,
    new_text: str,
    new_metadata: Dict[str, Any],
    document_id: str,
    amendment_ref: Optional[str] = None
) -> Tuple[bool, Optional[int]]:
    """
    Update a provision and create a new version record.

    This function:
    1. Checks if text actually changed (via hash comparison)
    2. Closes the current version (sets effective_to)
    3. Creates a new version record
    4. Updates the provision in regulatory_provisions
    5. Logs the change in provision_change_log

    Args:
        cur: Database cursor
        provision_id: ID of provision to update
        old_text: Current provision text
        old_hash: Hash of current text
        new_text: New provision text
        new_metadata: Dict with new metadata (v2_topic, zones, etc.)
        document_id: Document ID triggering the change
        amendment_ref: Optional amendment reference

    Returns:
        Tuple of (was_changed: bool, new_version_id: int or None)
    """
    # Calculate new hash
    new_hash = calculate_text_hash(new_text)

    # Skip if unchanged
    if new_hash == old_hash:
        return (False, None)

    # Get current version
    cur.execute("""
        SELECT version_number, id FROM provision_versions
        WHERE provision_id = %s AND effective_to IS NULL
        ORDER BY version_number DESC LIMIT 1
    """, (provision_id,))

    current_version_row = cur.fetchone()
    current_version_num = current_version_row[0] if current_version_row else 0
    current_version_id = current_version_row[1] if current_version_row else None
    new_version_num = current_version_num + 1

    # Close current version
    if current_version_id:
        cur.execute("""
            UPDATE provision_versions
            SET effective_to = NOW()
            WHERE id = %s
        """, (current_version_id,))

    # Create new version
    cur.execute("""
        INSERT INTO provision_versions (
            provision_id, version_number, provision_text, provision_type,
            v2_topic, v2_applicable_zones, v2_applicable_dev_types,
            v2_has_numeric_value, effective_from, effective_to,
            change_type, text_hash, extracted_from_document,
            extraction_method, change_summary
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NULL,
                  'modified', %s, %s, 'extraction_pipeline', %s)
        RETURNING id
    """, (
        provision_id,
        new_version_num,
        new_text,
        new_metadata.get('provision_type'),
        new_metadata.get('v2_topic'),
        new_metadata.get('v2_applicable_zones'),
        new_metadata.get('v2_applicable_dev_types'),
        new_metadata.get('v2_has_numeric_value'),
        new_hash,
        document_id,
        f"Updated from {amendment_ref}" if amendment_ref else "Text modified"
    ))

    new_version_id = cur.fetchone()[0]

    # Update provision
    cur.execute("""
        UPDATE regulatory_provisions
        SET provision_text = %s,
            provision_type = COALESCE(%s, provision_type),
            v2_topic = COALESCE(%s, v2_topic),
            v2_applicable_zones = COALESCE(%s, v2_applicable_zones),
            v2_applicable_dev_types = COALESCE(%s, v2_applicable_dev_types),
            v2_has_numeric_value = COALESCE(%s, v2_has_numeric_value),
            current_version_id = %s,
            last_modified_date = NOW(),
            version_count = %s,
            text_hash_current = %s,
            last_updated = NOW()
        WHERE id = %s
    """, (
        new_text,
        new_metadata.get('provision_type'),
        new_metadata.get('v2_topic'),
        new_metadata.get('v2_applicable_zones'),
        new_metadata.get('v2_applicable_dev_types'),
        new_metadata.get('v2_has_numeric_value'),
        new_version_id,
        new_version_num,
        new_hash,
        provision_id
    ))

    # Log change
    cur.execute("""
        INSERT INTO provision_change_log (
            provision_id, version_from, version_to, change_type,
            fields_changed, triggered_by_document, amendment_reference
        ) VALUES (%s, %s, %s, 'text_modified', ARRAY['provision_text'], %s, %s)
    """, (
        provision_id,
        current_version_id,
        new_version_id,
        document_id,
        amendment_ref
    ))

    return (True, new_version_id)


def mark_provision_deleted(
    cur,
    provision_id: int,
    document_id: str,
    amendment_ref: Optional[str] = None
) -> bool:
    """
    Mark a provision as deleted by creating a 'deleted' version.

    Args:
        cur: Database cursor
        provision_id: ID of provision to mark deleted
        document_id: Document ID triggering the deletion
        amendment_ref: Optional amendment reference

    Returns:
        True if successful
    """
    # Get current version
    cur.execute("""
        SELECT version_number, id, provision_text, text_hash
        FROM provision_versions
        WHERE provision_id = %s AND effective_to IS NULL
        ORDER BY version_number DESC LIMIT 1
    """, (provision_id,))

    current_version_row = cur.fetchone()
    if not current_version_row:
        return False

    current_version_num, current_version_id, provision_text, text_hash = current_version_row
    new_version_num = current_version_num + 1

    # Close current version
    cur.execute("""
        UPDATE provision_versions
        SET effective_to = NOW()
        WHERE id = %s
    """, (current_version_id,))

    # Create deleted version
    cur.execute("""
        INSERT INTO provision_versions (
            provision_id, version_number, provision_text,
            effective_from, effective_to, change_type, text_hash,
            extracted_from_document, extraction_method, change_summary
        ) VALUES (%s, %s, %s, NOW(), NULL, 'deleted', %s, %s, 'extraction_pipeline', %s)
        RETURNING id
    """, (
        provision_id,
        new_version_num,
        provision_text,  # Keep last known text
        text_hash,
        document_id,
        f"Deleted via {amendment_ref}" if amendment_ref else "Provision removed"
    ))

    deleted_version_id = cur.fetchone()[0]

    # Update provision
    cur.execute("""
        UPDATE regulatory_provisions
        SET is_current = FALSE,
            current_version_id = %s,
            last_modified_date = NOW(),
            version_count = %s,
            last_updated = NOW()
        WHERE id = %s
    """, (deleted_version_id, new_version_num, provision_id))

    # Log deletion
    cur.execute("""
        INSERT INTO provision_change_log (
            provision_id, version_from, version_to, change_type,
            triggered_by_document, amendment_reference
        ) VALUES (%s, %s, %s, 'deleted', %s, %s)
    """, (
        provision_id,
        current_version_id,
        deleted_version_id,
        document_id,
        amendment_ref
    ))

    return True


def create_initial_version(
    cur,
    provision_id: int,
    provision_text: str,
    metadata: Dict[str, Any],
    document_id: str
) -> int:
    """
    Create the initial version 1 for a newly inserted provision.

    Args:
        cur: Database cursor
        provision_id: ID of newly inserted provision
        provision_text: Initial provision text
        metadata: Dict with metadata (v2_topic, zones, etc.)
        document_id: Document ID

    Returns:
        ID of created version record
    """
    text_hash = calculate_text_hash(provision_text)

    cur.execute("""
        INSERT INTO provision_versions (
            provision_id, version_number, provision_text, provision_type,
            v2_topic, v2_applicable_zones, v2_applicable_dev_types,
            v2_has_numeric_value, effective_from, effective_to,
            change_type, text_hash, extracted_from_document,
            extraction_method
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NULL,
                  'created', %s, %s, 'extraction_pipeline')
        RETURNING id
    """, (
        provision_id,
        1,  # version_number
        provision_text,
        metadata.get('provision_type'),
        metadata.get('v2_topic'),
        metadata.get('v2_applicable_zones'),
        metadata.get('v2_applicable_dev_types'),
        metadata.get('v2_has_numeric_value'),
        text_hash,
        document_id
    ))

    version_id = cur.fetchone()[0]

    # Update provision with version reference
    cur.execute("""
        UPDATE regulatory_provisions
        SET current_version_id = %s,
            first_seen_date = NOW(),
            last_modified_date = NOW(),
            version_count = 1,
            is_current = TRUE,
            text_hash_current = %s
        WHERE id = %s
    """, (version_id, text_hash, provision_id))

    return version_id
