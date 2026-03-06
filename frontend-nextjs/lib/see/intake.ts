// SEE Structured Intake — deterministic provision triage from factual inputs.
//
// Design rule: a provision is only excluded when its applicability trigger is
// factually IMPOSSIBLE given confirmed inputs, never merely unlikely.
// "unknown" always defaults to inclusion.
// Every exclusion traces to a confirmed factual answer stored in proposed_values.

export interface IntakeAnswers {
  /** Does the proposal create new impervious surfaces (deck, paving, slab, extension footprint)? */
  new_impervious_surfaces: 'yes' | 'no' | 'unknown';
  /** Does the proposal affect trees on the site (removal, works within 3m root zone)? */
  trees_affected: 'yes' | 'no' | 'unknown';
  /** Does the proposal include a new swimming pool or spa? */
  pool_or_spa: 'yes' | 'no' | 'unknown';
  /** Does the proposal include new or altered boundary fencing? */
  new_fencing: 'yes' | 'no' | 'unknown';
  /** Does the proposal include new parking, carport, garage, or driveway works? */
  new_parking_or_driveway: 'yes' | 'no' | 'unknown';
  /** Does the proposal include any new or altered signage? */
  new_signage: 'yes' | 'no' | 'unknown';
  // --- Auto-answerable from LEP/SEPP property data ---
  /** Is the site flood prone? Auto-answered from LEP Part 5 mapping. */
  flood_prone: 'yes' | 'no' | 'unknown';
  /** Is the site bushfire prone? Auto-answered from LEP Part 5 mapping. */
  bushfire_prone: 'yes' | 'no' | 'unknown';
  /** Does the site have acid sulfate soils? Auto-answered from LEP Part 5 mapping. */
  acid_sulfate_soils: 'yes' | 'no' | 'unknown';
  /** Is the site in a coastal management area? Auto-answered from SEPP (Resilience and Hazards) 2021. */
  coastal: 'yes' | 'no' | 'unknown';
  /** Is the site in a biodiversity area? Auto-answered from LEP Part 5 mapping. */
  biodiversity: 'yes' | 'no' | 'unknown';
  // --- New manual question ---
  /** Does the proposal include demolition of any structure? */
  demolition: 'yes' | 'no' | 'unknown';
}

/**
 * Describes the source of an auto-populated intake answer.
 * Displayed in the intake modal and carried through to the SEE audit trail.
 */
export interface AutoAnswerSource {
  /** The property data field path that drives this answer (for transparency). */
  propertyField: string;
  /** Legislative/data citation shown to the planner. */
  citation: string;
  /** One-sentence rationale for the SEE audit trail when answer is 'no'. */
  rationale: string;
}

/**
 * Maps auto-answerable intake fields to their property data source and citation.
 * Only fields that can be definitively answered from objective property data are listed.
 */
export const AUTO_ANSWER_SOURCES: Partial<Record<keyof IntakeAnswers, AutoAnswerSource>> = {
  flood_prone: {
    propertyField: 'constraints.floodProne',
    citation: 'LEP Part 5 — Flood Prone Land',
    rationale: 'Site confirmed not flood prone per LEP mapping',
  },
  bushfire_prone: {
    propertyField: 'constraints.bushfireProne',
    citation: 'LEP Part 5 — Bushfire Prone Land',
    rationale: 'Site confirmed not bushfire prone per LEP mapping',
  },
  acid_sulfate_soils: {
    propertyField: 'constraints.acidSulfateSoils',
    citation: 'LEP Part 5 — Acid Sulfate Soils',
    rationale: 'Site confirmed no acid sulfate soils per LEP mapping',
  },
  coastal: {
    propertyField: 'constraints.coastalEnvironment.inCoastalArea',
    citation: 'SEPP (Resilience and Hazards) 2021 — Coastal Management',
    rationale: 'Site confirmed not in coastal management area',
  },
  biodiversity: {
    propertyField: 'constraints.terrestrialBiodiversity.inBiodiversityArea',
    citation: 'LEP Part 5 — Terrestrial Biodiversity',
    rationale: 'Site confirmed no terrestrial biodiversity overlay',
  },
};

export interface IntakeQuestion {
  field: keyof IntakeAnswers;
  question: string;
  detail: string;
}

export const INTAKE_QUESTIONS: IntakeQuestion[] = [
  {
    field: 'new_impervious_surfaces',
    question: 'Does the proposal create new impervious surfaces?',
    detail: 'Decks, paving, concrete slabs, extension footprints, or any surface that sheds rather than absorbs water.',
  },
  {
    field: 'trees_affected',
    question: 'Does the proposal affect trees on the site?',
    detail: 'Tree removal, pruning, or works within the root zone (typically 3m radius) of any tree.',
  },
  {
    field: 'pool_or_spa',
    question: 'Does the proposal include a new swimming pool or spa?',
    detail: 'In-ground or above-ground pool, spa, or plunge pool.',
  },
  {
    field: 'new_fencing',
    question: 'Does the proposal include new or altered boundary fencing?',
    detail: 'New boundary fence, replacement fencing, retaining walls functioning as fences, or alterations to existing fencing.',
  },
  {
    field: 'new_parking_or_driveway',
    question: 'Does the proposal include new parking, carport, or driveway works?',
    detail: 'New carport, garage, off-street parking space, driveway crossover, or modification to existing parking.',
  },
  {
    field: 'new_signage',
    question: 'Does the proposal include any new or altered signage?',
    detail: 'Business identification signs, advertising structures, or any form of signage attached to or displayed from the property.',
  },
  {
    field: 'demolition',
    question: 'Does the proposal include demolition of any structure?',
    detail: 'Full or partial demolition of a building, outbuilding, garage, carport, or other structure.',
  },
];

// Topic-to-trigger map.
// Keys are the intake fields. Values are arrays of v2_topic strings (lowercased).
// A provision is excluded when its normalized topic appears here AND the intake answer is 'no'.
//
// Normalization mirrors the frontend: v2_topic?.toLowerCase().replace(/ /g, '_')
//
// Only add topics whose applicability is FACTUALLY IMPOSSIBLE when the trigger is absent.
const TRIGGER_TO_TOPICS: Record<keyof IntakeAnswers, string[]> = {
  new_impervious_surfaces: ['stormwater', 'drainage'],
  trees_affected: ['trees'],
  pool_or_spa: ['pool'],
  new_fencing: ['fencing', 'fence'],
  new_parking_or_driveway: ['parking', 'vehicle_access', 'carport'],
  new_signage: ['signage'],
  // Auto-answered from LEP/SEPP property data
  flood_prone: ['flooding'],
  bushfire_prone: ['bushfire'],
  acid_sulfate_soils: ['contamination', 'acid_sulfate'],
  coastal: ['coastal'],
  biodiversity: ['biodiversity'],
  // Manual
  demolition: ['demolition'],
};

// Reason strings shown in the auto-generated N/A note and SEE audit trail.
const TOPIC_EXCLUSION_REASONS: Record<string, string> = {
  stormwater: 'No new impervious surfaces confirmed',
  drainage: 'No new impervious surfaces confirmed',
  trees: 'No trees affected confirmed',
  pool: 'No pool or spa in proposal confirmed',
  fencing: 'No new fencing confirmed',
  fence: 'No new fencing confirmed',
  parking: 'No new parking or driveway works confirmed',
  vehicle_access: 'No new parking or driveway works confirmed',
  carport: 'No new parking or driveway works confirmed',
  signage: 'No signage in proposal confirmed',
  flooding: 'Site confirmed not flood prone (LEP Part 5)',
  bushfire: 'Site confirmed not bushfire prone (LEP Part 5)',
  contamination: 'Site confirmed no acid sulfate soils (LEP Part 5)',
  acid_sulfate: 'Site confirmed no acid sulfate soils (LEP Part 5)',
  coastal: 'Site confirmed not in coastal management area (SEPP Resilience and Hazards 2021)',
  biodiversity: 'Site confirmed no terrestrial biodiversity overlay (LEP Part 5)',
  demolition: 'No demolition works in proposal confirmed',
};

/**
 * Normalize a v2_topic value to match the frontend comparison key.
 * Mirrors: v2_topic?.toLowerCase().replace(/ /g, '_')
 */
export function normalizeTopicKey(topic: string | null | undefined): string {
  if (!topic) return '';
  return topic.toLowerCase().replace(/ /g, '_');
}

/**
 * Returns the set of normalized v2_topic values that can be auto-excluded
 * based on the confirmed intake answers.
 *
 * A topic is only added when the associated intake answer is explicitly 'no'.
 * 'unknown' and 'yes' leave the topic in the active set.
 */
export function getExcludableTopics(answers: IntakeAnswers): Set<string> {
  const excluded = new Set<string>();
  for (const [field, topics] of Object.entries(TRIGGER_TO_TOPICS)) {
    if (answers[field as keyof IntakeAnswers] === 'no') {
      for (const topic of topics) {
        excluded.add(topic);
      }
    }
  }
  return excluded;
}

/**
 * Returns a human-readable exclusion reason for a normalized topic.
 * Used in auto-generated N/A response_text notes.
 */
export function getTopicExclusionReason(normalizedTopic: string): string {
  return TOPIC_EXCLUSION_REASONS[normalizedTopic] || 'Excluded by intake triage';
}

/**
 * Returns true if the provision's v2_topic should be auto-excluded given these answers.
 */
export function isProvisionExcluded(
  v2Topic: string | null | undefined,
  answers: IntakeAnswers
): boolean {
  const normalized = normalizeTopicKey(v2Topic);
  if (!normalized) return false;
  return getExcludableTopics(answers).has(normalized);
}

/** Default intake answers — all unknown (inclusion bias, safest default). */
export const DEFAULT_INTAKE_ANSWERS: IntakeAnswers = {
  new_impervious_surfaces: 'unknown',
  trees_affected: 'unknown',
  pool_or_spa: 'unknown',
  new_fencing: 'unknown',
  new_parking_or_driveway: 'unknown',
  new_signage: 'unknown',
  flood_prone: 'unknown',
  bushfire_prone: 'unknown',
  acid_sulfate_soils: 'unknown',
  coastal: 'unknown',
  biodiversity: 'unknown',
  demolition: 'unknown',
};

/**
 * Auto-populates intake answers from property constraints fetched from NSW Planning Portal.
 * Only sets 'no' when the constraint is definitively absent — never sets 'yes' or 'unknown'.
 * Returns a partial — caller must merge over existing answers (existing answers always win).
 *
 * Usage:
 *   const autoAnswers = autoPopulateFromConstraints(propertyData.constraints);
 *   const merged = { ...DEFAULT_INTAKE_ANSWERS, ...autoAnswers, ...(savedAnswers ?? {}) };
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function autoPopulateFromConstraints(constraints: Record<string, any>): Partial<IntakeAnswers> {
  const result: Partial<IntakeAnswers> = {};
  if (constraints.floodProne === false) result.flood_prone = 'no';
  if (constraints.bushfireProne === false) result.bushfire_prone = 'no';
  // acidSulfateSoils is a string class or undefined/null — falsy means absent
  if (!constraints.acidSulfateSoils) result.acid_sulfate_soils = 'no';
  if (constraints.coastalEnvironment?.inCoastalArea === false) result.coastal = 'no';
  if (constraints.terrestrialBiodiversity?.inBiodiversityArea === false) result.biodiversity = 'no';
  return result;
}
