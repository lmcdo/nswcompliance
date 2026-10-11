// prior-art-checked: no shared SQL filter module exists in lib/ -- a grep for the
// heritage predicate and for exported SQL constants found nothing. The predicate
// lived as five hand-copied strings inside app/api/provisions/for-property/route.ts,
// and all five carried the same NULL bug.

/**
 * SQL predicate: this provision is NOT a heritage provision.
 *
 * A provision with no topic is not, by that fact, a heritage provision. The copies
 * this replaces compared `LOWER(v2_topic) != 'heritage'`, which evaluates to NULL --
 * not true -- when the topic is missing, so every untagged rule was silently dropped
 * for every non-heritage property. Found 2026-09-13 on Marrickville low-density
 * housing, where "4.1.6.3 C13 Maximum site coverage controls" was stored, current
 * and actionable, and never shown.
 *
 * Three parts, each measured on production before it was written:
 *   1. topic is heritage (any case)            -> excluded
 *   2. marker is heritage (any case)           -> excluded. Every stored marker is
 *      lowercase today; the old comparison was case-sensitive and would have let a
 *      'Heritage' marker through.
 *   3. NO topic AND the row comes from a chapter whose key names heritage -> excluded.
 *      An untagged rule inside a heritage chapter is the one kind that is plausibly
 *      heritage-only content; 58 current rows. Rows WITH a topic keep their previous
 *      behaviour, so this narrows nothing that was shown before. strpos rather than
 *      LIKE so the string carries no '%' for a driver to misread as a placeholder.
 *
 * tests/test_provision_sql_filters.py runs this exact string against real Postgres.
 * Keep it a single-line template literal -- that test reads it out of this file.
 */
export const NOT_HERITAGE_SQL = `(COALESCE(LOWER(v2_topic), '') != 'heritage' AND COALESCE(LOWER(v2_marker), '') != 'heritage' AND (v2_topic IS NOT NULL OR strpos(LOWER(COALESCE(source_chapter_key, '')), 'heritage') = 0))`;

/**
 * SQL predicate: this provision applies in the property's zone. `p` is the $n index of the
 * zone parameter.
 *
 * Kept: no zone limit recorded (NULL or empty array), 'ALL', or the property's zone listed.
 * Dropped: a rule whose own chapter limits it to other zones -- Marrickville Part 6
 * industrial (E4) on an R2 house. The route applied this to the use_specific layer only, so
 * 2,838 such rules reached every house in their council (served-answer audit 2026-10-11).
 * An EMPTY array is kept, not dropped: `'R2' = ANY('{}')` is false, and an undecided row
 * must not vanish silently.
 *
 * tests/test_provision_sql_filters.py runs this exact string against real Postgres.
 * Keep it a single-line template literal -- that test reads it out of this file.
 */
export const ZONE_APPLIES_SQL = (p: number): string => `(v2_applicable_zones IS NULL OR cardinality(v2_applicable_zones) = 0 OR $${p} = ANY(v2_applicable_zones) OR 'ALL' = ANY(v2_applicable_zones))`;
