#!/usr/bin/env python3
"""
Enrichment Pipeline — the post-write phases that tag provisions.

Six phases, run in one mandatory order by run_standard_enrichment() and invoked
from scripts/dcp_commit_approved.py and scripts/dcp_extract_changed.py:
actionability, layer + topic, applicability, site condition, provision type,
applicability provenance. See STANDARD_ENRICHMENT_PHASES for why the order is
load-bearing.

Usage:
    python enrichment/pipeline.py --phase status
    python enrichment/pipeline.py --phase type [--limit 100] [--dry-run]

NOT HERE: numeric rule extraction. The `--phase numeric` this file used to offer
was deleted 2026-09-11 — it wrote v2_extracted_values / v2_enrichment_version /
v2_enriched_at, three columns that exist on no table. The live path writes
v2_extracted_rules and is a separate pipeline:

    python -m enrichment.rule_extraction_pipeline --phase deterministic --council <council>
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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enrichment.extractors.site_condition_tagger import SiteConditionTagger
from enrichment.extractors.type_classifier import TypeClassifier
from enrichment.extractors.applicability_tagger import (
    ApplicabilityTagger,
    TRUSTED_ALL_SOURCES,
)
from enrichment.extractors.layer_topic_tagger import LayerTopicTagger
from enrichment.extractors.actionable_classifier import ActionableClassifier
from enrichment.extractors.gemini_actionability_classifier import (
    GeminiActionabilityClassifier,
    is_performance_based_dcp,
)


ENRICHMENT_VERSION = "1.0.0"


def get_connection():
    """Get database connection."""
    return psycopg2.connect(os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL'))


# ── Gemini Stage-3 actionability (performance-based DCPs) ────────────────────
# OFF by default. Enable with DCP_GEMINI_STAGE3=1 + GEMINI_API_KEY. Performance-
# based DCPs (Ashfield Purpose/Performance-Criteria/Design-Solutions prose) are
# routed to the verbatim-verified Gemini classifier; every other doc uses the
# regex ActionableClassifier unchanged. Verdicts are cached in
# gemini_classification_cache so re-passes cost ~$0 and don't flap.

GEMINI_PROMPT_VERSION = "v1"


def _maybe_build_gemini():
    """Return a Gemini Stage-3 classifier, or None if disabled/unavailable.

    Any failure (flag off, no SDK, no API key) returns None and the pipeline
    falls back to the regex classifier for every provision — no behaviour change.
    """
    if os.getenv("DCP_GEMINI_STAGE3", "").lower() not in ("1", "true", "yes"):
        return None
    try:
        return GeminiActionabilityClassifier()
    except Exception as exc:
        print(f"[gemini] Stage-3 disabled — {exc}")
        return None


def _gemini_classify_cached(gemini, text, document_id, cur):
    """Classify via Gemini with a durable cache. Returns (is_actionable, reason).

    Cache key = sha256(text) + model + prompt_version. The verbatim-verification
    gate + conservative fallback live inside gemini.classify; unverified output
    always yields is_actionable=True.
    """
    import hashlib
    sha = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    model = getattr(gemini, "_model_name", "unknown")
    cur.execute(
        "SELECT is_actionable, reason FROM gemini_classification_cache "
        "WHERE text_sha256 = %s AND model_name = %s AND prompt_version = %s",
        (sha, model, GEMINI_PROMPT_VERSION),
    )
    row = cur.fetchone()
    if row is not None:
        return bool(row["is_actionable"]), (row.get("reason") or "gemini (cached)")

    result = gemini.classify(text, document_id, source_text=text)
    try:
        cur.execute(
            """
            INSERT INTO gemini_classification_cache
                (text_sha256, model_name, prompt_version, is_actionable, verified,
                 identified_text, char_start, char_end, reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (text_sha256, model_name, prompt_version) DO NOTHING
            """,
            (sha, model, GEMINI_PROMPT_VERSION, result.is_actionable, result.verified,
             result.identified_text, result.char_start, result.char_end, result.reason),
        )
    except Exception as exc:
        print(f"[gemini] cache write skipped — {exc}")
    return result.is_actionable, (result.reason or "gemini")


def _classify_one(prov, classifier, gemini, cur):
    """Route one provision: Gemini Stage-3 for performance-based DCPs, else regex."""
    document_id = prov.get("document_id") or ""
    if gemini is not None and is_performance_based_dcp(document_id):
        return _gemini_classify_cached(gemini, prov["provision_text"], document_id, cur)
    return classifier.classify(
        prov["provision_text"],
        document_id=prov["document_id"],
        section_header=prov["section_header"],
    )


def run_actionability_classification(
    limit: Optional[int] = None,
    dry_run: bool = False,
    batch_size: int = 1000,
    force_reprocess: bool = False,
) -> Dict[str, Any]:
    """Run actionability classification on provisions.

    This is Phase 0 of enrichment — must run before all other phases, which
    filter by v2_is_actionable = TRUE.

    Uses heading-based structural rules first (Controls → True, Objectives → False),
    then falls back to ActionableClassifier content analysis.

    By default only processes rows where v2_is_actionable IS NULL (new provisions).
    Set force_reprocess=True to also re-evaluate rows already marked FALSE against
    the current classifier rules. This is required whenever classifier logic is
    improved, to retroactively correct stale classifications. Rows already marked
    TRUE are never re-processed (they can only be widened, not narrowed, by
    classifier improvements — see ADR-001).

    Args:
        limit: Maximum number of provisions to process. None = all.
        dry_run: If True, classify but do not write results to the database.
        batch_size: Number of provisions to fetch and update per database round-trip.
        force_reprocess: If True, re-evaluate provisions already marked FALSE in
            addition to NULL rows. Use after classifier rule changes to eliminate
            stale false negatives. Default False to preserve existing behaviour
            for incremental runs.

    Returns:
        Dict with keys: total_processed, actionable, non_actionable, errors,
        and (when force_reprocess=True) flipped_to_actionable.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    classifier = ActionableClassifier()
    gemini = _maybe_build_gemini()
    if gemini is not None:
        print(f"[gemini] Stage-3 enabled ({gemini._model_name}) for performance-based DCPs")

    if force_reprocess:
        # Re-evaluate both NULL and existing FALSE rows.
        # TRUE rows are intentionally excluded — classifier improvements only
        # widen coverage, never retract it (conservative default per ADR-001).
        count_sql = """
            SELECT COUNT(*) as total
            FROM regulatory_provisions
            WHERE (v2_is_actionable IS NULL OR v2_is_actionable = false)
              AND provision_text IS NOT NULL
              AND provision_text != ''
        """
    else:
        count_sql = """
            SELECT COUNT(*) as total
            FROM regulatory_provisions
            WHERE v2_is_actionable IS NULL
              AND provision_text IS NOT NULL
              AND provision_text != ''
        """
    cur.execute(count_sql)
    total = cur.fetchone()['total']

    if limit:
        total = min(total, limit)

    print(f"Processing {total} provisions (force_reprocess={force_reprocess})...")
    print(f"Batch size: {batch_size}")
    print(f"Dry run: {dry_run}")
    print("=" * 60)

    stats: Dict[str, Any] = {
        "total_processed": 0,
        "actionable": 0,
        "non_actionable": 0,
        "errors": 0,
        "flipped_to_actionable": 0,
    }

    processed = 0

    # Pagination strategy differs between modes:
    #
    # Normal mode (NULL rows): always fetch from OFFSET 0. As rows are classified
    # they leave the NULL set, so the next batch is genuinely new rows.
    #
    # force_reprocess mode (NULL + FALSE rows): rows that stay false after
    # classification do NOT leave the target set, so re-fetching from OFFSET 0
    # would return the same rows indefinitely. Use keyset pagination instead:
    # advance by last-seen ID so every batch is a genuinely new window.
    last_id = 0

    while processed < total:
        if force_reprocess:
            fetch_sql = """
                SELECT id, provision_text, document_id, section_header,
                       v2_is_actionable as prior_value
                FROM regulatory_provisions
                WHERE (v2_is_actionable IS NULL OR v2_is_actionable = false)
                  AND provision_text IS NOT NULL
                  AND provision_text != ''
                  AND id > %s
                ORDER BY id
                LIMIT %s
            """
            cur.execute(fetch_sql, (last_id, batch_size))
        else:
            fetch_sql = """
                SELECT id, provision_text, document_id, section_header,
                       v2_is_actionable as prior_value
                FROM regulatory_provisions
                WHERE v2_is_actionable IS NULL
                  AND provision_text IS NOT NULL
                  AND provision_text != ''
                ORDER BY id
                LIMIT %s
            """
            cur.execute(fetch_sql, (batch_size,))
        provisions = cur.fetchall()

        if not provisions:
            break

        updates = []
        for prov in provisions:
            if limit and processed >= limit:
                break

            try:
                is_actionable, _ = _classify_one(prov, classifier, gemini, cur)
                updates.append((is_actionable, prov['id']))

                if is_actionable:
                    stats['actionable'] += 1
                    if force_reprocess and prov.get('prior_value') is False:
                        stats['flipped_to_actionable'] += 1
                else:
                    stats['non_actionable'] += 1

                processed += 1

            except Exception as e:
                print(f"Error processing provision {prov['id']}: {e}")
                stats['errors'] += 1
                processed += 1

        if updates and not dry_run:
            for is_actionable, prov_id in updates:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_is_actionable = %s
                    WHERE id = %s
                """, (is_actionable, prov_id))
            conn.commit()

        # Advance keyset cursor for force_reprocess mode.
        if force_reprocess and provisions:
            last_id = provisions[-1]['id']

        pct = (processed / total) * 100 if total > 0 else 100
        flip_info = f", Flipped false->true: {stats['flipped_to_actionable']}" if force_reprocess else ""
        print(f"Processed {processed}/{total} ({pct:.1f}%) - "
              f"Actionable: {stats['actionable']}, Non-actionable: {stats['non_actionable']}, "
              f"Errors: {stats['errors']}{flip_info}")

    stats['total_processed'] = processed
    cur.close()
    conn.close()

    return stats


def run_site_condition_tagging(
    limit: Optional[int] = None,
    dry_run: bool = False,
    batch_size: int = 1000,
    actionable_only: bool = True
) -> Dict[str, Any]:
    """
    Run site condition tagging on provisions.

    Tags provisions that require specific site conditions (heritage/flood/bushfire).
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    tagger = SiteConditionTagger()

    actionable_filter = "AND v2_is_actionable = true" if actionable_only else ""

    # Get count - only process provisions not yet tagged
    count_sql = f"""
        SELECT COUNT(*) as total
        FROM regulatory_provisions
        WHERE v2_site_condition_required IS NULL
          AND provision_text IS NOT NULL
          AND provision_text != ''
          {actionable_filter}
    """
    cur.execute(count_sql)
    total = cur.fetchone()['total']

    if limit:
        total = min(total, limit)

    print(f"Processing {total} provisions...")
    print(f"Batch size: {batch_size}")
    print(f"Dry run: {dry_run}")
    print("=" * 60)

    stats = {
        "total_processed": 0,
        "heritage": 0,
        "flood": 0,
        "bushfire": 0,
        "general": 0,
        "errors": 0,
    }

    processed = 0

    while processed < total:
        fetch_sql = f"""
            SELECT id, provision_text
            FROM regulatory_provisions
            WHERE v2_site_condition_required IS NULL
              AND provision_text IS NOT NULL
              AND provision_text != ''
              {actionable_filter}
            ORDER BY id
            LIMIT %s
        """
        cur.execute(fetch_sql, (batch_size,))
        provisions = cur.fetchall()

        if not provisions:
            break

        updates = []
        for prov in provisions:
            if limit and processed >= limit:
                break

            try:
                condition, confidence = tagger.tag(prov['provision_text'])

                # Store condition or 'none' for general provisions
                # Using 'none' instead of NULL so we know it's been processed
                db_value = condition if condition else 'none'
                updates.append((db_value, prov['id']))

                if condition == 'heritage':
                    stats['heritage'] += 1
                elif condition == 'flood':
                    stats['flood'] += 1
                elif condition == 'bushfire':
                    stats['bushfire'] += 1
                else:
                    stats['general'] += 1

                processed += 1

            except Exception as e:
                print(f"Error processing provision {prov['id']}: {e}")
                stats['errors'] += 1
                processed += 1

        # Apply updates
        if updates and not dry_run:
            for condition, prov_id in updates:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_site_condition_required = %s
                    WHERE id = %s
                """, (condition, prov_id))
            conn.commit()

        pct = (processed / total) * 100 if total > 0 else 100
        print(f"Processed {processed}/{total} ({pct:.1f}%) - "
              f"Heritage: {stats['heritage']}, Flood: {stats['flood']}, "
              f"Bushfire: {stats['bushfire']}, General: {stats['general']}")

    stats['total_processed'] = processed
    cur.close()
    conn.close()

    return stats


def run_type_classification(
    limit: Optional[int] = None,
    dry_run: bool = False,
    batch_size: int = 1000,
    actionable_only: bool = True
) -> Dict[str, Any]:
    """
    Run type classification on provisions.

    Classifies provisions as control/objective/definition/note/procedural.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    classifier = TypeClassifier()

    actionable_filter = "AND v2_is_actionable = true" if actionable_only else ""

    count_sql = f"""
        SELECT COUNT(*) as total
        FROM regulatory_provisions
        WHERE v2_provision_type IS NULL
          AND provision_text IS NOT NULL
          AND provision_text != ''
          {actionable_filter}
    """
    cur.execute(count_sql)
    total = cur.fetchone()['total']

    if limit:
        total = min(total, limit)

    print(f"Processing {total} provisions...")
    print(f"Batch size: {batch_size}")
    print(f"Dry run: {dry_run}")
    print("=" * 60)

    stats = {
        "total_processed": 0,
        "control": 0,
        "objective": 0,
        "definition": 0,
        "note": 0,
        "procedural": 0,
        "errors": 0,
    }

    processed = 0

    while processed < total:
        fetch_sql = f"""
            SELECT id, provision_text
            FROM regulatory_provisions
            WHERE v2_provision_type IS NULL
              AND provision_text IS NOT NULL
              AND provision_text != ''
              {actionable_filter}
            ORDER BY id
            LIMIT %s
        """
        cur.execute(fetch_sql, (batch_size,))
        provisions = cur.fetchall()

        if not provisions:
            break

        updates = []
        for prov in provisions:
            if limit and processed >= limit:
                break

            try:
                prov_type, confidence = classifier.classify(prov['provision_text'])
                updates.append((prov_type, prov['id']))
                stats[prov_type] = stats.get(prov_type, 0) + 1
                processed += 1

            except Exception as e:
                print(f"Error processing provision {prov['id']}: {e}")
                stats['errors'] += 1
                processed += 1

        if updates and not dry_run:
            for prov_type, prov_id in updates:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_provision_type = %s
                    WHERE id = %s
                """, (prov_type, prov_id))
            conn.commit()

        pct = (processed / total) * 100 if total > 0 else 100
        print(f"Processed {processed}/{total} ({pct:.1f}%) - "
              f"Control: {stats['control']}, Obj: {stats['objective']}, "
              f"Def: {stats['definition']}, Note: {stats['note']}, Proc: {stats['procedural']}")

    stats['total_processed'] = processed
    cur.close()
    conn.close()

    return stats


WILDCARD_ZONE = "ALL"


def keep_only_zones_valid_in_lga(zones, valid_zones):
    """Drop zone codes that do not exist in this row's LGA, before they are stored.

    DQ-30 RECURRENCE, measured 2026-09-10. Six freshly written ku_ring_gai rows were
    tagged 'B2' -- a code NSW retired in 2022, so nothing is zoned B2 any more and the
    row can never match a current-zone lookup. The August 2026 repair cleaned the rows
    that existed then; nothing guarded the WRITE, so the next extraction created more.

    The cause is not a bad zone list, it is a false positive:
    scripts/backfill_invalid_zone_codes.py records it as the tagger's blind text-regex
    fallback matching "Part B3" in DCP prose as zone B3. That is also why re-running
    the tagger repaired 0 of 241 rows -- it reproduces its own output, the same
    self-comparison that let the old "0% drift" check report success.

    Ground truth is lep_zone_coverage, queried live, NOT a table in this file. A
    committed constant would be hardcoded regulatory data and wrong within months --
    which LGAs are onboarded changes independently of deploys.

    Args:
        zones: the codes the tagger derived for this provision.
        valid_zones: upper-cased set of codes that exist in the row's LGA, or an
            EMPTY set when that LGA has no complete scrape.

    Returns:
        The surviving codes, or ['ALL'] if none survive -- the same honest
        "applicability undetermined" value backfill_invalid_zone_codes stores and the
        tagger itself produces when it finds no zone evidence, so this introduces no
        new semantic downstream.

        An EMPTY valid_zones means "we have not scraped this LGA", which is NOT
        evidence that any code is wrong. In that case the input is returned untouched.
        Emptying a council's zones over a coverage gap would be the guard doing the
        damage it exists to prevent.
    """
    if not valid_zones:
        return zones
    if not zones:
        return zones
    kept = [z for z in zones
            if isinstance(z, str) and (z.upper() in valid_zones or z.upper() == WILDCARD_ZONE)]
    return kept or [WILDCARD_ZONE]


def _load_zone_ground_truth(conn):
    """(per-LGA valid zone sets, slug -> LGA key) for the zone guard above.

    prior-art-checked: reuse, not reinvention. scripts/validate_zone_code_validity.py
    already resolves both -- including the part that is easy to get wrong, mapping an
    abolished council's slug to the CURRENT amalgamated LGA whose zones actually apply
    (Marrickville provisions are assessed against Inner West). Re-deriving that here
    would be a second copy free to drift from the checker that reports on it.

    Returns ({}, {}) on any failure. The caller then skips filtering entirely rather
    than treating "no ground truth" as "every code is invalid".
    """
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _scripts = str(_Path(__file__).resolve().parent.parent / "scripts")
        if _scripts not in _sys.path:
            _sys.path.insert(0, _scripts)
        from validate_zone_code_validity import load_ground_truth, load_slug_resolution
        cur = conn.cursor()
        truth = load_ground_truth(cur)
        slugs = load_slug_resolution(cur, truth)
        cur.close()
        return truth, slugs
    except Exception as exc:  # noqa: BLE001 — a missing checker must not stop tagging
        print(f"  [warn] zone ground truth unavailable ({exc}); zone validation SKIPPED "
              f"for this run. Retired codes can be written until this is fixed; "
              f"verify with python scripts/validate_zone_code_validity.py")
        return {}, {}


def run_applicability_tagging(
    limit: Optional[int] = None,
    dry_run: bool = False,
    batch_size: int = 1000,
    actionable_only: bool = True
) -> Dict[str, Any]:
    """
    Run applicability tagging on provisions.

    Tags provisions with applicable zones and development types.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    tagger = ApplicabilityTagger()

    # Loaded ONCE per run, not per row: lep_zone_coverage changes only when an LGA is
    # re-scraped. Empty on any failure, which makes the filter a no-op rather than
    # letting "no ground truth" read as "every code is invalid".
    _zone_truth, _zone_slugs = _load_zone_ground_truth(conn)
    if _zone_truth:
        print(f"Zone guard active: {len(_zone_truth)} LGAs with a complete zone list")

    actionable_filter = "AND v2_is_actionable = true" if actionable_only else ""

    count_sql = f"""
        SELECT COUNT(*) as total
        FROM regulatory_provisions
        WHERE v2_applicable_zones IS NULL
          AND provision_text IS NOT NULL
          AND provision_text != ''
          {actionable_filter}
    """
    cur.execute(count_sql)
    total = cur.fetchone()['total']

    if limit:
        total = min(total, limit)

    print(f"Processing {total} provisions...")
    print(f"Batch size: {batch_size}")
    print(f"Dry run: {dry_run}")
    print("=" * 60)

    stats = {
        "total_processed": 0,
        "with_specific_zones": 0,
        # Counts ALLs that were DEFAULTED rather than decided — the number this
        # provenance work exists to make answerable. Initialised here rather than
        # via .get(k, 0) so an explicit None can never reach `+ 1`.
        'undetermined_zone_all': 0,
        "with_specific_dev_types": 0,
        "all_zones": 0,
        "all_dev_types": 0,
        "errors": 0,
    }

    processed = 0

    while processed < total:
        fetch_sql = f"""
            SELECT id, provision_text, document_id, source_council
            FROM regulatory_provisions
            WHERE v2_applicable_zones IS NULL
              AND provision_text IS NOT NULL
              AND provision_text != ''
              {actionable_filter}
            ORDER BY id
            LIMIT %s
        """
        cur.execute(fetch_sql, (batch_size,))
        provisions = cur.fetchall()

        if not provisions:
            break

        updates = []
        for prov in provisions:
            if limit and processed >= limit:
                break

            try:
                zones, dev_types, prov_src = tagger.tag_with_provenance(
                    prov['provision_text'], prov['document_id'])

                # DQ-30: never STORE a code that does not exist in this row's LGA.
                # The tagger reads prose, and "Part B3" reads as zone B3. Filtering
                # here rather than inside the tagger keeps the tagger's provenance
                # honest about what the text said, while the stored value stays
                # answerable against lep_zone_coverage. Skipped entirely when the LGA
                # has no complete scrape -- see keep_only_zones_valid_in_lga.
                lga_key = _zone_slugs.get(prov.get('source_council'))
                filtered = keep_only_zones_valid_in_lga(zones, _zone_truth.get(lga_key, set()))
                if filtered != zones:
                    # `or 0`, not a .get default: a key present with value None
                    # would sail past the default and raise on None + 1.
                    stats['zones_dropped_not_in_lga'] = (
                        (stats.get('zones_dropped_not_in_lga') or 0) + 1)
                    print(f"  [zone-guard] provision {prov['id']} "
                          f"({prov.get('source_council')}): {zones} -> {filtered} "
                          f"(codes absent from lep_zone_coverage for {lga_key!r})")
                zones = filtered

                updates.append((zones, dev_types,
                                prov_src['zone_source'], prov_src['dev_type_source'],
                                prov['id']))
                # Track how many ALLs were DECIDED vs defaulted — the number the
                # whole provenance column exists to make answerable.
                if 'ALL' in zones and prov_src['zone_source'] not in TRUSTED_ALL_SOURCES:
                    stats['undetermined_zone_all'] += 1

                if 'ALL' not in zones:
                    stats['with_specific_zones'] += 1
                else:
                    stats['all_zones'] += 1

                if 'ALL' not in dev_types:
                    stats['with_specific_dev_types'] += 1
                else:
                    stats['all_dev_types'] += 1

                processed += 1

            except Exception as e:
                print(f"Error processing provision {prov['id']}: {e}")
                stats['errors'] += 1
                processed += 1

        if updates and not dry_run:
            for zones, dev_types, zone_src, dev_src, prov_id in updates:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_applicable_zones = %s,
                        v2_applicable_dev_types = %s,
                        v2_zone_source = %s,
                        v2_dev_type_source = %s
                    WHERE id = %s
                """, (zones, dev_types, zone_src, dev_src, prov_id))
            conn.commit()

        pct = (processed / total) * 100 if total > 0 else 100
        print(f"Processed {processed}/{total} ({pct:.1f}%) - "
              f"Specific zones: {stats['with_specific_zones']}, "
              f"Specific dev types: {stats['with_specific_dev_types']}, "
              f"UNDETERMINED zone ALL: {stats['undetermined_zone_all']}")

    stats['total_processed'] = processed
    cur.close()
    conn.close()

    return stats


def tags_reproduce(stored_zones, stored_dev_types,
                   recomputed_zones, recomputed_dev_types) -> bool:
    """Does today's config still produce exactly what is stored?

    Pure, so the rule that decides whether 20,948 rows get written can be
    tested without a database — the same reason #957 made its ratchet
    practices pure functions over two dicts.

    Set-equality on both axes, because array ORDER carries no meaning here and
    a reordering is not a disagreement. NULL and [] are treated alike: both mean
    "no values recorded", and a row cannot be said to disagree with itself over
    which empty it used.

    Deliberately strict in one direction: if the recomputed value is a STRICT
    SUBSET of what is stored — today's config says `retail_premises` where the
    row says `ALL` — that is a MISMATCH, not a refinement to be written. The
    stored tag is what the product currently serves, and quietly recording a
    source for a value we no longer derive would attach a justification to a
    claim the config contradicts.
    """
    return (set(stored_zones or []) == set(recomputed_zones or [])
            and set(stored_dev_types or []) == set(recomputed_dev_types or []))


def run_applicability_provenance(
    limit: Optional[int] = None,
    dry_run: bool = False,
    batch_size: int = 1000,
    actionable_only: bool = True
) -> Dict[str, Any]:
    """Recover WHY a row is tagged, for rows that were tagged before we recorded it.

    THE GAP THIS FILLS. 10,103 served provisions carry applicability tags and no
    v2_dev_type_source, so `['ALL']` on them cannot be told apart from a decision
    that it applies everywhere. `run_applicability_tagging` cannot reach them: it
    selects on `v2_applicable_zones IS NULL`, and zero of those rows match, so the
    phase reports "Processed: 0" and looks like a no-op rather than a miss. The
    rows were written before the provenance columns existed — nine scripts write
    v2_applicable_dev_types and not one writes a source.

    WHY THIS ONLY WRITES THE SOURCE COLUMNS. The configs may have moved since
    those scripts ran, so recomputing can legitimately produce DIFFERENT tags.
    Overwriting 10,103 live applicability decisions on that basis is CHOOSING a
    value, not removing a false claim, and that is the direction that needs the
    most care. So the recomputed tags are used only to ANSWER A QUESTION — does
    today's config still produce what is stored? — and never to replace them:

        match    -> the stored tags are reproducible, so the source that produced
                    them is knowable, and it is written.
        mismatch -> REFUSED. The row keeps its NULL source and is counted and
                    sampled, because "the config no longer agrees with this row"
                    is a finding for a human, not something to paper over by
                    writing a source that describes a value we did not store.

    So a mismatch leaves the row exactly as DQ-74 already counts it. The number
    falls by what we can prove and no further, which is the point.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    tagger = ApplicabilityTagger()

    # SCOPE, stated because the DB currency guard is right to ask. This filters
    # on v2_is_actionable and deliberately NOT on is_current: a superseded
    # version is still a row whose applicability was decided for a reason, and
    # leaving it unlabelled would keep the older record permanently
    # unattributable while its successor is explained. Nothing here is SERVED —
    # the phase writes provenance columns only — so the staleness this guard
    # exists to stop cannot arise from it. The consequence to know: this
    # examines every actionable version (20,948) while DQ-74 counts current
    # rows only (10,103), so the two numbers are not directly comparable.
    actionable_filter = "AND v2_is_actionable = true" if actionable_only else ""
    where = f"""
        WHERE v2_dev_type_source IS NULL
          AND v2_applicable_dev_types IS NOT NULL
          AND provision_text IS NOT NULL
          AND provision_text != ''
          {actionable_filter}
    """
    # is_current intentionally absent — see the scope note above.
    cur.execute(f"SELECT COUNT(*) AS total FROM regulatory_provisions {where}")
    total = cur.fetchone()['total']
    if limit:
        total = min(total, limit)

    print(f"Rows tagged but with no recorded source: {total}")
    print(f"Batch size: {batch_size}")
    print(f"Dry run: {dry_run}")
    print("=" * 60)

    stats = {
        "total_processed": 0, "matched": 0, "mismatched": 0, "errors": 0,
        "by_source": {}, "samples": [],
    }
    # Paginate by id, not by the NULL sentinel: a MISMATCH deliberately leaves
    # the source NULL, so a sentinel-driven loop would fetch those same rows
    # forever. This is the loop-invariant trap the pre-impl protocol asks about.
    last_id = 0
    while stats["total_processed"] < total:
        # Same `where` as the count above: filters v2_is_actionable, and
        # is_current is intentionally absent — see the scope note at the top of
        # this function. Paginated by id, never by the NULL sentinel, because a
        # REFUSED row keeps its NULL source and a sentinel loop would fetch it
        # forever.
        cur.execute(
            f"""SELECT id, provision_text, document_id,
                       v2_applicable_zones, v2_applicable_dev_types
                  FROM regulatory_provisions {where} AND id > %s
                 -- scope: the WHERE above carries the v2_is_actionable filter,
                 -- and is_current is deliberately absent. See the docstring.
                 ORDER BY id LIMIT %s""",
            (last_id, batch_size),
        )
        provisions = cur.fetchall()
        if not provisions:
            break

        writes = []
        for prov in provisions:
            last_id = prov['id']
            if limit and stats["total_processed"] >= limit:
                break
            try:
                zones, dev_types, src = tagger.tag_with_provenance(
                    prov['provision_text'], prov['document_id'])
                stored_dt = list(prov['v2_applicable_dev_types'] or [])
                stored_z = list(prov['v2_applicable_zones'] or [])
                if tags_reproduce(stored_z, stored_dt, zones, dev_types):
                    writes.append((src['zone_source'], src['dev_type_source'],
                                   prov['id']))
                    stats["matched"] += 1
                    k = src['dev_type_source']
                    stats["by_source"][k] = stats["by_source"].get(k, 0) + 1
                else:
                    stats["mismatched"] += 1
                    if len(stats["samples"]) < 10:
                        stats["samples"].append({
                            "id": prov['id'],
                            "document_id": prov['document_id'],
                            "stored_dev_types": stored_dt,
                            "recomputed_dev_types": sorted(dev_types),
                            "stored_zones": stored_z,
                            "recomputed_zones": sorted(zones),
                        })
            except Exception as e:
                print(f"Error on provision {prov['id']}: {e}")
                stats["errors"] += 1
            stats["total_processed"] += 1

        if writes and not dry_run:
            # ONLY the two source columns. v2_applicable_zones and
            # v2_applicable_dev_types are deliberately absent from this
            # statement — see the docstring.
            for zone_src, dev_src, prov_id in writes:
                cur.execute(
                    """UPDATE regulatory_provisions
                          SET v2_zone_source = %s, v2_dev_type_source = %s
                        WHERE id = %s""",
                    (zone_src, dev_src, prov_id))
            conn.commit()

        pct = (stats["total_processed"] / total) * 100 if total else 100
        print(f"Processed {stats['total_processed']}/{total} ({pct:.1f}%) - "
              f"matched {stats['matched']}, refused {stats['mismatched']}")

    cur.close()
    conn.close()
    return stats


def run_layer_tagging(
    limit: Optional[int] = None,
    dry_run: bool = False,
    batch_size: int = 1000,
    actionable_only: bool = True
) -> Dict[str, Any]:
    """
    Run layer + topic tagging on provisions (4-layer model).

    Tags provisions with:
    - v2_dcp_layer: generic | use_specific | condition | precinct
    - v2_dcp_part: Part 2.6, Part C Section 1, etc.
    - v2_topic: setbacks, parking, solar, etc.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    tagger = LayerTopicTagger()

    actionable_filter = "AND v2_is_actionable = true" if actionable_only else ""

    count_sql = f"""
        SELECT COUNT(*) as total
        FROM regulatory_provisions
        WHERE v2_dcp_layer IS NULL
          AND provision_text IS NOT NULL
          AND provision_text != ''
          {actionable_filter}
    """
    cur.execute(count_sql)
    total = cur.fetchone()['total']

    if limit:
        total = min(total, limit)

    print(f"Processing {total} provisions...")
    print(f"Batch size: {batch_size}")
    print(f"Dry run: {dry_run}")
    print("=" * 60)

    stats = {
        "total_processed": 0,
        "generic": 0,
        "use_specific": 0,
        "condition": 0,
        "precinct": 0,
        "with_topic": 0,
        "errors": 0,
    }

    processed = 0

    # Do NOT use OFFSET — rows are updated out of the WHERE clause each batch,
    # so OFFSET would skip ahead into a shrinking result. Always fetch from OFFSET 0.
    while processed < total:
        fetch_sql = f"""
            SELECT id, document_id, provision_text
            FROM regulatory_provisions
            WHERE v2_dcp_layer IS NULL
              AND provision_text IS NOT NULL
              AND provision_text != ''
              {actionable_filter}
            ORDER BY id
            LIMIT %s
        """
        cur.execute(fetch_sql, (batch_size,))
        provisions = cur.fetchall()

        if not provisions:
            break

        updates = []
        for prov in provisions:
            if limit and processed >= limit:
                break

            try:
                layer, part, topic = tagger.tag(prov['document_id'], prov['provision_text'])
                updates.append((layer, part, topic, prov['id']))

                stats[layer] = stats.get(layer, 0) + 1
                if topic:
                    stats['with_topic'] += 1

                processed += 1

            except Exception as e:
                print(f"Error processing provision {prov['id']}: {e}")
                stats['errors'] += 1
                processed += 1

        if updates and not dry_run:
            for layer, part, topic, prov_id in updates:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_dcp_layer = %s,
                        v2_dcp_part = %s,
                        v2_topic = %s
                    WHERE id = %s
                """, (layer, part, topic, prov_id))
            conn.commit()

        pct = (processed / total) * 100 if total > 0 else 100
        print(f"Processed {processed}/{total} ({pct:.1f}%) - "
              f"Generic: {stats['generic']}, Use: {stats['use_specific']}, "
              f"Condition: {stats['condition']}, Precinct: {stats['precinct']}, "
              f"With topic: {stats['with_topic']}")

    stats['total_processed'] = processed
    cur.close()
    conn.close()

    return stats


def get_enrichment_status() -> Dict[str, Any]:
    """Get current enrichment status."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN v2_is_actionable = true THEN 1 END) as actionable,
            COUNT(CASE WHEN v2_is_actionable = false THEN 1 END) as boilerplate,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_has_numeric_value = true THEN 1 END) as with_numeric,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_has_numeric_value = false THEN 1 END) as without_numeric,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_site_condition_required = 'heritage' THEN 1 END) as heritage,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_site_condition_required = 'flood' THEN 1 END) as flood,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_site_condition_required = 'bushfire' THEN 1 END) as bushfire,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_site_condition_required = 'none' THEN 1 END) as general_no_condition,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_site_condition_required IS NOT NULL THEN 1 END) as site_condition_tagged,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_provision_type IS NOT NULL THEN 1 END) as type_classified,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_provision_type = 'control' THEN 1 END) as type_control,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_provision_type = 'objective' THEN 1 END) as type_objective,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_provision_type = 'definition' THEN 1 END) as type_definition,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_provision_type = 'note' THEN 1 END) as type_note,
            COUNT(CASE WHEN v2_is_actionable = true AND v2_provision_type = 'procedural' THEN 1 END) as type_procedural
        FROM regulatory_provisions
    """)
    result = cur.fetchone()

    cur.close()
    conn.close()

    actionable = result['actionable']

    # `enriched`, `pending` and `enrichment_pct` USED TO BE HERE and are gone.
    # They counted `v2_enriched_at IS NOT NULL`, and that column exists on no
    # table in the database -- so this whole report raised UndefinedColumn and
    # `--phase status` had not run for as long as that was true. They are removed
    # rather than repointed at a surviving column: inventing a new definition of
    # "enriched" is choosing a value, where deleting a metric that measured
    # nothing only removes a claim. The live coverage signals are
    # site_condition_tagged and type_classified, already below.
    return {
        "total_provisions": result['total'],
        "actionable": actionable,
        "boilerplate": result['boilerplate'],
        "with_numeric_values": result['with_numeric'],
        "without_numeric_values": result['without_numeric'],
        "site_condition_tagged": result['site_condition_tagged'],
        "heritage": result['heritage'],
        "flood": result['flood'],
        "bushfire": result['bushfire'],
        "general_no_condition": result['general_no_condition'],
        "type_classified": result['type_classified'],
        "type_control": result['type_control'],
        "type_objective": result['type_objective'],
        "type_definition": result['type_definition'],
        "type_note": result['type_note'],
        "type_procedural": result['type_procedural'],
    }


#: The phases that run after provisions are written, in the ONLY order that works.
#:
#: WHY THIS LIST IS HERE AND NOT AT THE CALL SITES. It used to be three lines
#: copied into scripts/dcp_commit_approved.py AND scripts/dcp_extract_changed.py.
#: Two copies of an order that matters is two things to keep in step, and the
#: measurable result was that three phases which exist and work were called by
#: neither: v2_site_condition_required and v2_provision_type were NULL on 3,216
#: served rows each, and v2_dev_type_source on 1,142 (measured 2026-09-11).
#: Marrickville alone carried 2,326 of the provision_type gap -- 97% of its
#: served rows had no type, so the UI could not tell a control from a note.
#:
#: THE ORDER IS LOAD-BEARING, in two separate ways:
#:   1. run_actionability_classification MUST be first. Every phase after it
#:      filters on `v2_is_actionable = true`, so running it late means the others
#:      silently process nothing and report success.
#:   2. run_layer_tagging must come before any precinct derivation at the call
#:      site. A derived precinct key also sets v2_dcp_layer='precinct', and layer
#:      tagging would overwrite that if it ran afterwards (#1080).
#: The three appended phases write only their own columns and never v2_dcp_layer,
#: which is why appending was safe and reordering would not be.
#:
#: A SEVENTH PHASE, run_numeric_extraction, USED TO EXIST AND WAS DELETED
#: 2026-09-11. It filtered on `v2_enriched_at` and wrote `v2_extracted_values`,
#: `v2_enrichment_version` and `v2_enriched_at` -- three columns that exist on NO
#: table in this database. It targeted a four-column schema that was replaced by
#: the `v2_extracted_rules` + `v2_extraction_status` pair, which
#: enrichment/rule_extraction_pipeline.py owns and writes. It could not have run
#: since that schema changed, and repointing it would have created a SECOND writer
#: for a field another pipeline already owns -- the duplication that caused the
#: defect this list exists to prevent. If numeric rule extraction is wanted in this
#: sequence, wire that pipeline; do not resurrect the wrapper.
STANDARD_ENRICHMENT_PHASES = (
    ("actionability", "run_actionability_classification"),
    ("layer + topic", "run_layer_tagging"),
    ("applicability", "run_applicability_tagging"),
    ("site condition", "run_site_condition_tagging"),
    ("provision type", "run_type_classification"),
    ("applicability provenance", "run_applicability_provenance"),
)


def run_standard_enrichment(batch_size: int = 500, phases=None) -> Dict[str, Any]:
    """Run every post-write enrichment phase, in order, and report what each did.

    Each phase is fill-blanks-only -- every one selects on its own column being
    NULL -- so this is safe to run repeatedly and cannot overwrite a value a human
    or an earlier run established.

    ERROR ISOLATION IS THE POINT. A phase that raises must not stop the phases
    after it: the caller has already committed provisions to the live table, and
    "one tagger broke so five others never ran" is how a partial enrichment turns
    into a council that is invisible in the UI. Each phase is wrapped, its error
    recorded against its name, and the sequence continues.

    Returns {phase_name: stats-or-error-dict}. The caller decides what to do with
    a failure; this function's job is to run everything it can and hide nothing.
    """
    # `is None`, NOT `or`. An explicitly empty override means "run nothing", and
    # `phases or DEFAULT` would quietly turn that into "run all six against the
    # live database" -- the widest possible reading of the narrowest possible
    # instruction.
    selected = STANDARD_ENRICHMENT_PHASES if phases is None else phases
    results: Dict[str, Any] = {}
    for label, fn_name in selected:
        fn = globals().get(fn_name)
        if fn is None:
            # A renamed phase must be loud. Silently skipping it would recreate
            # the exact condition this function was written to end.
            results[label] = {"error": f"{fn_name} is not defined in enrichment.pipeline"}
            print(f"  [ERROR] {label}: {fn_name} is not defined")
            continue
        print(f"\n  -- {label} --")
        try:
            results[label] = fn(batch_size=batch_size)
        except Exception as exc:  # noqa: BLE001 — one phase must not stop the rest
            results[label] = {"error": f"{type(exc).__name__}: {exc}"}
            print(f"  [ERROR] {label} failed: {type(exc).__name__}: {exc}")
    failed = phase_failures(results)
    if failed:
        print(f"\n  enrichment finished with {len(failed)} failed phase(s): {', '.join(failed)}")
    return results


def phase_failures(results: Dict[str, Any]) -> list:
    """Phase labels that did not fully succeed. The ONE definition of that.

    A phase can fail in two different shapes and only one of them is an
    exception. run_type_classification and run_site_condition_tagging both count
    per-row failures into their own stats and return normally, so a run that
    errored on twelve provisions comes back as {'total_processed': 3372,
    'errors': 12} -- truthy, present, and with no 'error' key anywhere. A caller
    checking only for 'error' reports "enrichment complete" over those twelve
    rows, which is the silent-failure shape this whole change exists to remove.

    Both call sites use this rather than each writing their own comprehension,
    because two copies of "what counts as failed" is how the phase list itself
    came to be wrong in two files at once.
    """
    failed = []
    for label, stats in results.items():
        if not isinstance(stats, dict):
            # A phase that returns None, or a tuple, or anything else is a phase
            # whose result cannot be read -- which is not the same as a phase that
            # succeeded. Skipping it here would rebuild the silence this function
            # exists to remove, one level further in. Checked and NOT currently
            # possible: all six phases return a dict today. This is the guard for
            # the seventh, or for the day one of them changes shape.
            failed.append(f"{label} (unreadable result: {type(stats).__name__})")
            continue
        if stats.get("error"):
            failed.append(label)
        elif stats.get("errors"):  # a non-zero per-row error count
            failed.append(f"{label} ({stats['errors']} row error(s))")
    return failed


def main():
    parser = argparse.ArgumentParser(description="Run enrichment pipeline")
    parser.add_argument("--phase", choices=["actionability", "site_condition", "type", "applicability", "applicability_provenance", "layer", "status"], default="status",
                       help="Which phase to run (default: status)")
    parser.add_argument("--limit", type=int, help="Limit number of provisions to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't commit changes")
    parser.add_argument("--batch-size", type=int, default=500,
                       help="Batch size for processing (default: 500)")
    parser.add_argument("--all", action="store_true",
                       help="Process all provisions (including boilerplate)")

    args = parser.parse_args()

    if args.phase == "actionability":
        print("\n=== Running Actionability Classification (Phase 0) ===")
        print("(Processes provisions where v2_is_actionable IS NULL)")
        stats = run_actionability_classification(
            limit=args.limit,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
        print("\n=== Results ===")
        print(f"Processed: {stats['total_processed']:,}")
        print(f"Actionable: {stats['actionable']:,}")
        print(f"Non-actionable: {stats['non_actionable']:,}")
        print(f"Errors: {stats['errors']:,}")

        if args.dry_run:
            print("\n[DRY RUN - No changes committed]")

    elif args.phase == "status":
        status = get_enrichment_status()
        print("\n=== Enrichment Status ===")
        print(f"Total provisions: {status['total_provisions']:,}")
        print(f"  Actionable: {status['actionable']:,}")
        print(f"  Boilerplate: {status['boilerplate']:,}")
        print(f"\nNumeric extraction:")
        print(f"  With numeric values: {status['with_numeric_values']:,}")
        print(f"  Without numeric values: {status['without_numeric_values']:,}")
        print(f"\nSite conditions (tagged: {status['site_condition_tagged']:,}/{status['actionable']:,}):")
        print(f"  Heritage-specific: {status['heritage']:,}")
        print(f"  Flood-specific: {status['flood']:,}")
        print(f"  Bushfire-specific: {status['bushfire']:,}")
        print(f"  General (no condition): {status['general_no_condition']:,}")
        print(f"\nProvision types (classified: {status['type_classified']:,}/{status['actionable']:,}):")
        print(f"  Control: {status['type_control']:,}")
        print(f"  Objective: {status['type_objective']:,}")
        print(f"  Definition: {status['type_definition']:,}")
        print(f"  Note: {status['type_note']:,}")
        print(f"  Procedural: {status['type_procedural']:,}")

    elif args.phase == "site_condition":
        print("\n=== Running Site Condition Tagging ===")
        actionable_only = not args.all
        if actionable_only:
            print("(Processing actionable provisions only)")
        stats = run_site_condition_tagging(
            limit=args.limit,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            actionable_only=actionable_only
        )
        print("\n=== Results ===")
        print(f"Processed: {stats['total_processed']:,}")
        print(f"Heritage-specific: {stats['heritage']:,}")
        print(f"Flood-specific: {stats['flood']:,}")
        print(f"Bushfire-specific: {stats['bushfire']:,}")
        print(f"General (no condition): {stats['general']:,}")
        print(f"Errors: {stats['errors']:,}")

        if args.dry_run:
            print("\n[DRY RUN - No changes committed]")

    elif args.phase == "type":
        print("\n=== Running Type Classification ===")
        actionable_only = not args.all
        if actionable_only:
            print("(Processing actionable provisions only)")
        stats = run_type_classification(
            limit=args.limit,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            actionable_only=actionable_only
        )
        print("\n=== Results ===")
        print(f"Processed: {stats['total_processed']:,}")
        print(f"Control: {stats['control']:,}")
        print(f"Objective: {stats['objective']:,}")
        print(f"Definition: {stats['definition']:,}")
        print(f"Note: {stats['note']:,}")
        print(f"Procedural: {stats['procedural']:,}")
        print(f"Errors: {stats['errors']:,}")

        if args.dry_run:
            print("\n[DRY RUN - No changes committed]")

    elif args.phase == "applicability":
        print("\n=== Running Applicability Tagging ===")
        actionable_only = not args.all
        if actionable_only:
            print("(Processing actionable provisions only)")
        stats = run_applicability_tagging(
            limit=args.limit,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            actionable_only=actionable_only
        )
        print("\n=== Results ===")
        print(f"Processed: {stats['total_processed']:,}")
        print(f"With specific zones: {stats['with_specific_zones']:,}")
        print(f"With specific dev types: {stats['with_specific_dev_types']:,}")
        print(f"General (all zones): {stats['all_zones']:,}")
        print(f"General (all dev types): {stats['all_dev_types']:,}")
        print(f"Errors: {stats['errors']:,}")

        if args.dry_run:
            print("\n[DRY RUN - No changes committed]")

    elif args.phase == "applicability_provenance":
        print("\n=== Recovering applicability provenance ===")
        actionable_only = not args.all
        if actionable_only:
            print("(Processing actionable provisions only)")
        stats = run_applicability_provenance(
            limit=args.limit,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            actionable_only=actionable_only,
        )
        print("\n=== Results ===")
        print(f"Examined: {stats['total_processed']:,}")
        print(f"Reproducible, source recovered: {stats['matched']:,}")
        print(f"REFUSED - config no longer agrees: {stats['mismatched']:,}")
        print(f"Errors: {stats['errors']:,}")
        if stats['by_source']:
            print("\nRecovered sources:")
            for k, v in sorted(stats['by_source'].items(),
                               key=lambda kv: -kv[1]):
                print(f"  {k:20} {v:,}")
        if stats['samples']:
            print("\nRefused, first few — each is a row today's config would "
                  "tag differently than what is stored:")
            for s in stats['samples']:
                print(f"  id={s['id']} {str(s['document_id'])[:52]}")
                print(f"     stored dev_types: {s['stored_dev_types']}")
                print(f"     recomputed      : {s['recomputed_dev_types']}")
        if args.dry_run:
            print("\n[DRY RUN - No changes committed]")

    elif args.phase == "layer":
        print("\n=== Running Layer + Topic Tagging (4-Layer Model) ===")
        actionable_only = not args.all
        if actionable_only:
            print("(Processing actionable provisions only)")
        stats = run_layer_tagging(
            limit=args.limit,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            actionable_only=actionable_only
        )
        print("\n=== Results ===")
        print(f"Processed: {stats['total_processed']:,}")
        print(f"Layer distribution:")
        print(f"  Generic: {stats['generic']:,}")
        print(f"  Use-specific: {stats['use_specific']:,}")
        print(f"  Condition: {stats['condition']:,}")
        print(f"  Precinct: {stats['precinct']:,}")
        print(f"With topic assigned: {stats['with_topic']:,}")
        print(f"Errors: {stats['errors']:,}")

        if args.dry_run:
            print("\n[DRY RUN - No changes committed]")


if __name__ == "__main__":
    main()
