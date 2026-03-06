/**
 * Canonical numeric measurement pattern for planning regulation provisions.
 * Matches numeric values followed by planning units (m, m², ha, %, etc.)
 * with word boundaries to avoid partial matches within text.
 *
 * Exported for use in provision filtering, topic stats, and tests.
 */
export const NUMERIC_MEASUREMENT_RE =
  /\b\d+(?:\.\d+)?\s*(?:m²|m|mm|cm|km|%|metres?|meters?|centimètres?|centimeters?|sqm|square mètres?|ha|hectares?)(?!\w)/i;
