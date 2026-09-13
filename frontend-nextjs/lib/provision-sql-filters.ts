// prior-art-checked: no shared SQL filter module exists in lib/ -- a grep for the
// heritage predicate and for exported SQL constants found nothing. The predicate
// lived as five hand-copied strings inside app/api/provisions/for-property/route.ts,
// and all five carried the same NULL bug.

/**
 * SQL predicate: this provision is NOT a heritage provision.
 *
 * A provision with no topic is not a heritage provision. The copies this replaces
 * compared `LOWER(v2_topic) != 'heritage'`, which evaluates to NULL -- not true --
 * when the topic is missing, so every untagged rule was silently dropped for every
 * non-heritage property. Found 2026-09-13 on Marrickville low-density housing, where
 * "4.1.6.3 C13 Maximum site coverage controls" was stored, current and actionable,
 * and never shown.
 *
 * Measure the reach with:
 *   SELECT count(*) FROM regulatory_provisions
 *   WHERE is_current AND v2_is_actionable AND v2_topic IS NULL
 *     AND (v2_marker IS NULL OR v2_marker != 'heritage');
 *
 * tests/test_provision_sql_filters.py runs this exact string against real Postgres.
 * Keep it a single-line template literal -- that test reads it out of this file.
 */
export const NOT_HERITAGE_SQL = `(COALESCE(LOWER(v2_topic), '') != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))`;
