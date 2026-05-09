#!/usr/bin/env python3
"""
Rule Extraction Pipeline — deterministic stage (2a) + validation (2c).

Processes provisions through:
  1. Compliance type classification
  2. Numeric value extraction → ExtractedRule format
  3. Cross-reference detection
  4. Spatial component flagging
  5. Validation gates

Provisions that pass deterministic extraction are marked COMPLETE.
Provisions that need LLM interpretation are marked for Stage 2b.
Provisions that fail validation after LLM retry go to human review.

Usage:
    python enrichment/rule_extraction_pipeline.py --dry-run --limit 100
    python enrichment/rule_extraction_pipeline.py --phase deterministic
    python enrichment/rule_extraction_pipeline.py --review
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enrichment.extractors.numeric_extractor import NumericExtractor
from enrichment.extractors.compliance_type_classifier import classify_compliance_type
from enrichment.extractors.reference_extractor import extract_references, detect_spatial_component
from enrichment.extractors.rule_schema import (
    ExtractedRule, RuleCondition, RuleReference,
    ExtractionStatus, ComplianceType, ExtractionMethod, ExtractionConfidence,
    validate_provision_rules,
)


PIPELINE_VERSION = "2.0.0"


def get_connection():
    """Get database connection."""
    return psycopg2.connect(os.getenv('SUPABASE_DB_URL'))


# ============================================================================
# STAGE 2a: DETERMINISTIC EXTRACTION
# ============================================================================

def deterministic_extract(
    text: str,
    has_numeric_value: Optional[bool] = None,
    section_header: Optional[str] = None,
) -> List[dict]:
    """
    Run all deterministic extractors on a provision and produce ExtractedRule dicts.

    This is Stage 2a of the pipeline — no LLM, instant, 100% reliable for what
    it covers. Returns an array of ExtractedRule dicts (may be empty).
    """
    rules = []
    extractor = NumericExtractor()

    # 1. Classify compliance type
    compliance_type, ct_reason = classify_compliance_type(
        text,
        has_numeric_value=has_numeric_value,
        section_header=section_header,
    )

    # 2. Extract numeric values and convert to ExtractedRule format
    numeric_result = extractor.extract(text)
    if numeric_result["has_numeric"] and numeric_result["values"]:
        for val in numeric_result["values"]:
            rule = ExtractedRule(
                compliance_type=ComplianceType.NUMERIC_CHECK.value,
                extraction_method=ExtractionMethod.REGEX.value,
                extraction_confidence=ExtractionConfidence.HIGH.value,
                value_type=val.get("value_type"),
                value_min=val.get("value_min"),
                value_max=val.get("value_max"),
                value_exact=val.get("value_exact"),
                unit=val.get("unit"),
                context=val.get("context"),
                raw_match=val.get("raw_match", "")[:500],
            )
            rules.append(rule.to_dict())

    # 3. Extract cross-references
    refs = extract_references(text)

    # 4. Detect spatial components
    has_spatial = detect_spatial_component(text)

    # 5. If no numeric rules were extracted, create a single rule with
    #    compliance type + any references/spatial info
    if not rules:
        rule = ExtractedRule(
            compliance_type=compliance_type,
            extraction_method=ExtractionMethod.HEADING_RULE.value,
            extraction_confidence=(
                ExtractionConfidence.HIGH.value
                if ct_reason.startswith("heading_") or ct_reason == "prohibition_language"
                else ExtractionConfidence.MEDIUM.value
            ),
        )
        if has_spatial:
            rule.has_spatial_component = True
        if refs:
            rule.references = [RuleReference(**r) for r in refs]
        rules.append(rule.to_dict())
    else:
        # Attach refs and spatial to the first numeric rule
        if refs:
            rules[0]["references"] = refs
        if has_spatial:
            rules[0]["has_spatial_component"] = True

    return rules


def is_extraction_complete(rules: List[dict], text: str) -> bool:
    """
    Decide whether deterministic extraction is sufficient or LLM is needed.

    Complete if:
    - Has numeric values extracted with high confidence
    - OR is classified as binary_prohibition (no values needed)
    - OR is classified as procedural (no values needed)

    Needs LLM if:
    - Classified as numeric_check but no values extracted
    - Classified as merit_assessment with conditional language
    - Has cross-references that might change the requirement
    """
    if not rules:
        return False

    first_rule = rules[0]
    ct = first_rule.get("compliance_type")

    # Prohibitions and procedural rules are complete without values
    if ct in (ComplianceType.BINARY_PROHIBITION.value, ComplianceType.PROCEDURAL.value):
        return True

    # Numeric check with values = complete
    if ct == ComplianceType.NUMERIC_CHECK.value:
        has_values = any(
            r.get("value_min") is not None or
            r.get("value_max") is not None or
            r.get("value_exact") is not None
            for r in rules
        )
        if has_values:
            return True

    # Merit assessment with no conditional language = complete
    # (nothing more to extract — it's genuinely subjective)
    if ct == ComplianceType.MERIT_ASSESSMENT.value:
        import re
        has_conditional = bool(re.search(
            r'\b(unless|except\s+where|provided\s+that|whichever|subject\s+to)',
            text, re.IGNORECASE
        ))
        if not has_conditional:
            return True

    return False


# ============================================================================
# STAGE 2c: VALIDATION GATE
# ============================================================================

def validate_and_decide(
    rules: List[dict],
    provision_id: int,
    provision_text: str,
    source: str,
) -> dict:
    """
    Validate extracted rules and decide the extraction status.

    Returns dict with:
      - rules: validated/cleaned rules
      - status: ExtractionStatus value
      - errors: validation errors (if any)
    """
    errors = validate_provision_rules(rules)

    if not errors:
        return {
            "rules": rules,
            "status": (
                ExtractionStatus.COMPLETE.value
                if source == "deterministic"
                else ExtractionStatus.LLM_COMPLETE.value
            ),
            "errors": [],
        }

    return {
        "rules": rules,
        "status": ExtractionStatus.REVIEW_NEEDED.value,
        "errors": errors,
        "provision_id": provision_id,
        "provision_text": provision_text[:500],
    }


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def process_provision(provision: dict) -> dict:
    """
    Process a single provision through the full pipeline.

    Stage 2a (deterministic) → validation gate → complete or flag.
    Stage 2b (LLM) is NOT implemented here — that's a separate module.
    """
    text = provision.get("provision_text", "")
    prov_id = provision["id"]

    if not text or len(text.strip()) < 10:
        return {
            "rules": [],
            "status": ExtractionStatus.SKIPPED.value,
            "errors": [],
        }

    # Stage 2a: deterministic extraction
    rules = deterministic_extract(
        text,
        has_numeric_value=provision.get("v2_has_numeric_value"),
        section_header=provision.get("section_header"),
    )

    # Check completeness
    if is_extraction_complete(rules, text):
        result = validate_and_decide(rules, prov_id, text, source="deterministic")
        return result

    # Not complete — needs LLM (Stage 2b) or human review
    # For now, validate what we have and mark appropriately
    errors = validate_provision_rules(rules)
    return {
        "rules": rules,
        "status": ExtractionStatus.REVIEW_NEEDED.value,
        "errors": errors,
        "needs_llm": True,
    }


def run_batch(
    limit: Optional[int] = None,
    dry_run: bool = False,
    batch_size: int = 500,
) -> dict:
    """
    Run deterministic extraction on all actionable provisions.

    Returns stats and writes review queue file.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Count provisions to process
    cur.execute("""
        SELECT COUNT(*) as total
        FROM regulatory_provisions
        WHERE is_current = true
          AND v2_is_actionable = true
          AND provision_text IS NOT NULL
          AND provision_text != ''
    """)
    total = cur.fetchone()["total"]
    if limit:
        total = min(total, limit)

    print(f"=== Rule Extraction Pipeline v{PIPELINE_VERSION} ===")
    print(f"Provisions to process: {total:,}")
    print(f"Batch size: {batch_size}")
    print(f"Dry run: {dry_run}")
    print("=" * 60)

    stats = {
        "total": 0,
        "complete": 0,
        "needs_llm": 0,
        "review_needed": 0,
        "skipped": 0,
        "errors": 0,
    }
    review_queue = []
    processed = 0

    while processed < total:
        cur.execute("""
            SELECT id, provision_text, v2_has_numeric_value, section_header,
                   v2_topic, source_council, document_id
            FROM regulatory_provisions
            WHERE is_current = true
              AND v2_is_actionable = true
              AND provision_text IS NOT NULL
              AND provision_text != ''
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (batch_size, processed))
        provisions = cur.fetchall()

        if not provisions:
            break

        batch_updates = []
        for prov in provisions:
            if limit and processed >= limit:
                break

            try:
                result = process_provision(dict(prov))
                status = result["status"]
                rules = result["rules"]

                stats["total"] += 1
                if status == ExtractionStatus.COMPLETE.value:
                    stats["complete"] += 1
                elif result.get("needs_llm"):
                    stats["needs_llm"] += 1
                elif status == ExtractionStatus.REVIEW_NEEDED.value:
                    stats["review_needed"] += 1
                    review_queue.append({
                        "provision_id": prov["id"],
                        "council": prov.get("source_council", "unknown"),
                        "topic": prov.get("v2_topic"),
                        "text": (prov["provision_text"] or "")[:500],
                        "attempted_rules": rules,
                        "validation_errors": result.get("errors", []),
                    })
                elif status == ExtractionStatus.SKIPPED.value:
                    stats["skipped"] += 1

                batch_updates.append({
                    "id": prov["id"],
                    "rules": json.dumps(rules),
                    "status": status,
                })
                processed += 1

            except Exception as e:
                print(f"  ERROR provision {prov['id']}: {e}")
                stats["errors"] += 1
                processed += 1

        # Write to DB
        if batch_updates and not dry_run:
            for upd in batch_updates:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_extracted_rules = %s,
                        v2_extraction_status = %s
                    WHERE id = %s
                """, (upd["rules"], upd["status"], upd["id"]))
            conn.commit()

        pct = (processed / total * 100) if total > 0 else 100
        print(
            f"  {processed:,}/{total:,} ({pct:.0f}%) — "
            f"complete={stats['complete']:,} "
            f"needs_llm={stats['needs_llm']:,} "
            f"review={stats['review_needed']:,}"
        )

    cur.close()
    conn.close()

    # Write review queue
    if review_queue:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        review_path = f"enrichment/review_queue_{ts}.json"
        with open(review_path, "w") as f:
            json.dump(review_queue, f, indent=2, default=str)
        print(f"\n{len(review_queue)} provisions need review -> {review_path}")

    # Summary
    print("\n=== Results ===")
    print(f"Total processed: {stats['total']:,}")
    print(f"  Complete (deterministic): {stats['complete']:,}")
    print(f"  Needs LLM (Stage 2b):    {stats['needs_llm']:,}")
    print(f"  Needs human review:      {stats['review_needed']:,}")
    print(f"  Skipped:                 {stats['skipped']:,}")
    print(f"  Errors:                  {stats['errors']:,}")
    if dry_run:
        print("\n[DRY RUN — no changes committed]")

    return stats


# ============================================================================
# HUMAN REVIEW CLI
# ============================================================================

def run_review():
    """Interactive CLI for reviewing provisions that need human attention."""
    import glob

    # Find latest review queue
    files = sorted(glob.glob("enrichment/review_queue_*.json"), reverse=True)
    if not files:
        print("No review queue files found.")
        return

    latest = files[0]
    print(f"Loading review queue: {latest}")

    with open(latest) as f:
        queue = json.load(f)

    print(f"{len(queue)} provisions to review\n")

    reviewed = 0
    for i, item in enumerate(queue):
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(queue)}] Provision {item['provision_id']}")
        print(f"Council: {item.get('council', '?')} | Topic: {item.get('topic', '?')}")
        print(f"{'='*60}")
        print(f"\nTEXT:\n{item['text']}")
        print(f"\nATTEMPTED RULES:\n{json.dumps(item['attempted_rules'], indent=2)}")
        if item.get("validation_errors"):
            print(f"\nVALIDATION ERRORS:\n" + "\n".join(f"  - {e}" for e in item["validation_errors"]))

        print("\nActions: [s]kip  [a]ccept as-is  [u]nextractable  [q]uit")
        action = input("> ").strip().lower()

        if action == "q":
            break
        elif action == "a":
            reviewed += 1
            print("  Accepted.")
        elif action == "u":
            reviewed += 1
            print("  Marked unextractable.")
        else:
            print("  Skipped.")

    print(f"\nReviewed {reviewed}/{len(queue)} provisions.")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Rule Extraction Pipeline — deterministic + validation"
    )
    parser.add_argument(
        "--phase", choices=["deterministic", "review", "status"],
        default="status",
        help="Phase to run (default: status)"
    )
    parser.add_argument("--limit", type=int, help="Max provisions to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't commit changes")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size")

    args = parser.parse_args()

    if args.phase == "deterministic":
        run_batch(
            limit=args.limit,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
    elif args.phase == "review":
        run_review()
    elif args.phase == "status":
        print("Run with --phase deterministic to start extraction.")
        print("Run with --phase review to review flagged provisions.")


if __name__ == "__main__":
    main()
