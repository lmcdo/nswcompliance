#!/usr/bin/env python3
"""
Import procedural guidance, application checklists, and getting started guides to Supabase.

Usage:
    python scripts/procedural/import_procedural.py
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values, Json

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXTRACTED_DIR = PROJECT_ROOT / "scripts" / "procedural" / "extracted"

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def create_tables(conn):
    """Create tables if they don't exist."""
    cur = conn.cursor()

    # Read and execute procedural guidance migration
    migration_path = PROJECT_ROOT / "migrations" / "create_procedural_guidance.sql"
    if migration_path.exists():
        with open(migration_path, 'r') as f:
            sql = f.read()
        cur.execute(sql)
        conn.commit()
        print("[OK] Procedural guidance tables created/verified")
    else:
        print("[WARN] Procedural guidance migration file not found, assuming tables exist")

    # Read and execute guides migration
    guides_migration_path = PROJECT_ROOT / "migrations" / "create_getting_started_guides.sql"
    if guides_migration_path.exists():
        with open(guides_migration_path, 'r') as f:
            sql = f.read()
        cur.execute(sql)
        conn.commit()
        print("[OK] Getting started guides table created/verified")
    else:
        print("[WARN] Guides migration file not found, assuming table exists")

    cur.close()


def import_pathway_guidance(conn):
    """Import pathway guidance Q&A pairs."""
    guidance_path = EXTRACTED_DIR / "pathway_guidance.json"

    if not guidance_path.exists():
        print(f"[ERROR] File not found: {guidance_path}")
        return 0

    with open(guidance_path, 'r', encoding='utf-8') as f:
        guidance_data = json.load(f)

    cur = conn.cursor()

    # Clear existing data (optional - comment out if you want to preserve)
    cur.execute("DELETE FROM procedural_guidance")

    # Insert new data
    insert_sql = """
        INSERT INTO procedural_guidance (
            question_pattern,
            question_normalized,
            question_category,
            answer_summary,
            answer_detailed,
            answer_conditions,
            source_document,
            source_url,
            source_section,
            last_verified,
            follow_up_questions,
            related_question_ids,
            applies_to_cdc,
            applies_to_da,
            applies_to_dev_types,
            extraction_confidence,
            manual_verified
        ) VALUES %s
        ON CONFLICT (question_normalized, source_document) DO UPDATE SET
            question_pattern = EXCLUDED.question_pattern,
            question_category = EXCLUDED.question_category,
            answer_summary = EXCLUDED.answer_summary,
            answer_detailed = EXCLUDED.answer_detailed,
            answer_conditions = EXCLUDED.answer_conditions,
            source_url = EXCLUDED.source_url,
            source_section = EXCLUDED.source_section,
            last_verified = EXCLUDED.last_verified,
            follow_up_questions = EXCLUDED.follow_up_questions,
            related_question_ids = EXCLUDED.related_question_ids,
            applies_to_cdc = EXCLUDED.applies_to_cdc,
            applies_to_da = EXCLUDED.applies_to_da,
            applies_to_dev_types = EXCLUDED.applies_to_dev_types,
            extraction_confidence = EXCLUDED.extraction_confidence,
            manual_verified = EXCLUDED.manual_verified,
            updated_at = NOW()
    """

    values = []
    for item in guidance_data:
        values.append((
            item['question_pattern'],
            item['question_normalized'],
            item['question_category'],
            item['answer_summary'],
            item['answer_detailed'],
            item.get('answer_conditions'),
            item['source_document'],
            item.get('source_url'),
            item.get('source_section'),
            item.get('last_verified'),
            item.get('follow_up_questions'),
            item.get('related_question_ids'),
            item.get('applies_to_cdc', True),
            item.get('applies_to_da', True),
            item.get('applies_to_dev_types'),
            item.get('extraction_confidence', 1.0),
            item.get('manual_verified', False),
        ))

    execute_values(cur, insert_sql, values)
    conn.commit()

    # Verify count
    cur.execute("SELECT COUNT(*) FROM procedural_guidance")
    count = cur.fetchone()[0]

    cur.close()
    return count


def import_checklists(conn):
    """Import application checklists."""
    checklist_path = EXTRACTED_DIR / "application_checklists.json"

    if not checklist_path.exists():
        print(f"[ERROR] File not found: {checklist_path}")
        return 0

    with open(checklist_path, 'r', encoding='utf-8') as f:
        checklist_data = json.load(f)

    cur = conn.cursor()

    # Clear existing data
    cur.execute("DELETE FROM application_checklists")

    # Insert new data
    insert_sql = """
        INSERT INTO application_checklists (
            checklist_name,
            pathway,
            development_type,
            item_order,
            item_name,
            item_description,
            item_required,
            item_conditions,
            source_document,
            source_url
        ) VALUES %s
        ON CONFLICT (checklist_name, item_order) DO UPDATE SET
            pathway = EXCLUDED.pathway,
            development_type = EXCLUDED.development_type,
            item_name = EXCLUDED.item_name,
            item_description = EXCLUDED.item_description,
            item_required = EXCLUDED.item_required,
            item_conditions = EXCLUDED.item_conditions,
            source_document = EXCLUDED.source_document,
            source_url = EXCLUDED.source_url
    """

    values = []
    for checklist in checklist_data:
        for item in checklist['items']:
            values.append((
                checklist['checklist_name'],
                checklist['pathway'],
                checklist.get('development_type'),
                item['item_order'],
                item['item_name'],
                item.get('item_description'),
                item.get('item_required', True),
                item.get('item_conditions'),
                checklist.get('source_document'),
                checklist.get('source_url'),
            ))

    execute_values(cur, insert_sql, values)
    conn.commit()

    # Verify count
    cur.execute("SELECT COUNT(*) FROM application_checklists")
    count = cur.fetchone()[0]

    cur.close()
    return count


def import_guides(conn):
    """Import getting started guides."""
    guides_path = EXTRACTED_DIR / "getting_started_guides.json"

    if not guides_path.exists():
        print(f"[SKIP] File not found: {guides_path}")
        return 0

    with open(guides_path, 'r', encoding='utf-8') as f:
        guides_data = json.load(f)

    cur = conn.cursor()

    # Clear existing data
    cur.execute("DELETE FROM getting_started_guides")

    # Insert new data
    insert_sql = """
        INSERT INTO getting_started_guides (
            guide_id,
            title,
            slug,
            target_user,
            typical_timeline,
            typical_cost_range,
            eligibility,
            steps,
            common_pitfalls,
            related_qa_ids,
            related_checklist_ids,
            source_document,
            source_url,
            last_verified,
            display_order,
            is_published
        ) VALUES %s
        ON CONFLICT (guide_id) DO UPDATE SET
            title = EXCLUDED.title,
            slug = EXCLUDED.slug,
            target_user = EXCLUDED.target_user,
            typical_timeline = EXCLUDED.typical_timeline,
            typical_cost_range = EXCLUDED.typical_cost_range,
            eligibility = EXCLUDED.eligibility,
            steps = EXCLUDED.steps,
            common_pitfalls = EXCLUDED.common_pitfalls,
            related_qa_ids = EXCLUDED.related_qa_ids,
            related_checklist_ids = EXCLUDED.related_checklist_ids,
            source_document = EXCLUDED.source_document,
            source_url = EXCLUDED.source_url,
            last_verified = EXCLUDED.last_verified,
            display_order = EXCLUDED.display_order,
            is_published = EXCLUDED.is_published,
            updated_at = NOW()
    """

    values = []
    for idx, guide in enumerate(guides_data):
        values.append((
            guide['guide_id'],
            guide['title'],
            guide['slug'],
            guide['target_user'],
            guide.get('typical_timeline'),
            guide.get('typical_cost_range'),
            Json(guide.get('eligibility')) if guide.get('eligibility') else None,
            Json(guide['steps']),
            Json(guide.get('common_pitfalls')) if guide.get('common_pitfalls') else None,
            guide.get('related_qa_ids'),
            guide.get('related_checklist_ids'),
            guide.get('source_document'),
            guide.get('source_url'),
            guide.get('last_verified'),
            guide.get('display_order', idx),
            guide.get('is_published', True),
        ))

    execute_values(cur, insert_sql, values)
    conn.commit()

    # Verify count
    cur.execute("SELECT COUNT(*) FROM getting_started_guides")
    count = cur.fetchone()[0]

    cur.close()
    return count


def main():
    """Main import function."""
    print("=" * 70)
    print("IMPORT PROCEDURAL GUIDANCE TO SUPABASE")
    print("=" * 70)
    print()

    # Connect to database
    print("Connecting to database...")
    conn = get_db_connection()
    print("[OK] Connected")
    print()

    # Create tables
    print("Creating/verifying tables...")
    create_tables(conn)
    print()

    # Import pathway guidance
    print("Importing pathway guidance...")
    guidance_count = import_pathway_guidance(conn)
    print(f"[OK] Imported {guidance_count} Q&A pairs")
    print()

    # Import checklists
    print("Importing application checklists...")
    checklist_count = import_checklists(conn)
    print(f"[OK] Imported {checklist_count} checklist items")
    print()

    # Import guides
    print("Importing getting started guides...")
    guides_count = import_guides(conn)
    print(f"[OK] Imported {guides_count} guides")
    print()

    # Summary
    print("=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"  Pathway Guidance: {guidance_count} Q&A pairs")
    print(f"  Checklists:       {checklist_count} items")
    print(f"  Guides:           {guides_count} guides")
    print(f"  Total:            {guidance_count + checklist_count + guides_count} records")
    print("=" * 70)

    conn.close()


if __name__ == "__main__":
    main()
