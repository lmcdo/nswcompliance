/**
 * Works scope questionnaire — captures what the proposal actually involves.
 *
 * Answers drive two things:
 * 1. Heritage element scope — which building elements are affected, used to filter
 *    heritage chapter controls to only those relevant to the works.
 * 2. Questionnaire-derived topic exclusions — auto-scope topics like boarding_house,
 *    commercial, multi_dwelling from scope when the proposal doesn't involve them.
 *    These are kept separate from manual topicAssertions so they auto-recalculate
 *    when answers change, without polluting the human-made assertion list.
 */

export interface WorksScopeAnswers {
  /** Heritage building elements the proposal affects. null = not yet answered. */
  heritage_elements: string[] | null;

  /** Does the proposal include any commercial, retail, or food premises component? */
  has_commercial: boolean | null;

  /** Does the proposal include a boarding house or co-living component? */
  has_boarding_house: boolean | null;

  /** Does the proposal include multi-dwelling, dual occupancy, or residential flat? */
  has_multi_dwelling: boolean | null;

  /** Does the proposal include land subdivision? */
  is_subdivision: boolean | null;

  /** Does the proposal include child care, education, or community facilities? */
  has_child_care: boolean | null;

  /** Does the proposal include a home business or home industry? */
  has_home_business: boolean | null;

  /** Does the proposal include tourist, visitor, or short-term accommodation? */
  has_tourist_accommodation: boolean | null;

  /** Does the proposal include any industrial or warehouse use? */
  has_industrial: boolean | null;
}

export const EMPTY_WORKS_SCOPE: WorksScopeAnswers = {
  heritage_elements: null,
  has_commercial: null,
  has_boarding_house: null,
  has_multi_dwelling: null,
  is_subdivision: null,
  has_child_care: null,
  has_home_business: null,
  has_tourist_accommodation: null,
  has_industrial: null,
};

/**
 * Heritage building elements — ordered for display.
 * Values match v2_heritage_element DB values.
 */
export const HERITAGE_ELEMENTS: { value: string; label: string }[] = [
  { value: 'facade',    label: 'Facade / front elevation' },
  { value: 'roof',      label: 'Roof (form or materials)' },
  { value: 'window',    label: 'Windows & doors' },
  { value: 'verandah',  label: 'Verandah or balcony' },
  { value: 'fence',     label: 'Fencing (boundary)' },
  { value: 'infill',    label: 'Rear addition / new structure' },
  { value: 'materials', label: 'Materials & finishes' },
  { value: 'demolition',label: 'Demolition of existing element' },
  { value: 'garden',    label: 'Garden / landscape' },
  { value: 'interior',  label: 'Interior (heritage item only)' },
];

/**
 * Maps WorksScopeAnswers fields to DB-level dev type slugs (v2_applicable_dev_types) that can
 * be auto-excluded when the answer is explicitly false.
 *
 * A provision is excluded if ALL of its v2_applicable_dev_types are in the exclusion set
 * (provisions with no dev types, i.e. null / ALL, are never excluded this way).
 *
 * More reliable than topic-based exclusion because it uses the same structured field
 * used for primary/secondary matching — works cross-LGA without relying on v2_topic text.
 */
export const SCOPE_DEV_TYPE_MAP: {
  field: keyof Omit<WorksScopeAnswers, 'heritage_elements'>;
  devTypes: string[];
  reason: string;
}[] = [
  {
    field: 'has_commercial',
    devTypes: [
      'commercial_premises', 'retail_premises', 'office_premises', 'food_and_drink_premises',
      'neighbourhood_shop', 'pub', 'hotel_or_motel_accommodation', 'serviced_apartment',
      'shop_top_housing', 'change_of_use',
    ],
    reason: 'No commercial or retail component confirmed',
  },
  {
    field: 'has_boarding_house',
    devTypes: ['boarding_house', 'co_living'],
    reason: 'No boarding house or co-living component confirmed',
  },
  {
    field: 'has_multi_dwelling',
    devTypes: [
      'multi_dwelling_housing', 'residential_flat_building', 'dual_occupancy',
      'dual_occupancy_attached', 'dual_occupancy_detached', 'manor_house',
    ],
    reason: 'No multi-dwelling or dual occupancy component confirmed',
  },
  {
    field: 'is_subdivision',
    devTypes: ['subdivision'],
    reason: 'No land subdivision in proposal confirmed',
  },
  {
    field: 'has_child_care',
    devTypes: ['child_care_centre', 'centre_based_childcare', 'educational_establishment'],
    reason: 'No child care, education, or community facility component confirmed',
  },
  {
    field: 'has_tourist_accommodation',
    devTypes: ['tourist_and_visitor_accommodation', 'hotel_or_motel_accommodation', 'serviced_apartment'],
    reason: 'No tourist, visitor, or short-term accommodation component confirmed',
  },
  {
    field: 'has_industrial',
    devTypes: ['industrial_development', 'light_industry', 'warehouse', 'heavy_industry'],
    reason: 'No industrial or warehouse use confirmed',
  },
];

/**
 * Derive questionnaire-driven dev type exclusions from works scope answers.
 * Returns a Set of dev type slugs whose family is confirmed absent.
 * A provision is excluded when ALL of its v2_applicable_dev_types are in this set.
 */
export function deriveQuestionnaireDevTypeExclusions(
  answers: WorksScopeAnswers | null,
): Set<string> {
  const excluded = new Set<string>();
  if (!answers) return excluded;
  for (const { field, devTypes } of SCOPE_DEV_TYPE_MAP) {
    if (answers[field] === false) {
      for (const dt of devTypes) excluded.add(dt);
    }
  }
  return excluded;
}

/**
 * Maps WorksScopeAnswers fields to v2_topic values that can be auto-excluded
 * when the answer is explicitly false.
 *
 * Only populated when answer is false (not null/true).
 * null = not answered → provisions stay in scope.
 * true = this type IS present → provisions stay in scope.
 * false = confirmed absent → topic can be excluded.
 */
export const SCOPE_TOPIC_MAP: {
  field: keyof Omit<WorksScopeAnswers, 'heritage_elements'>;
  topics: string[];
  reason: string;
}[] = [
  {
    field: 'has_commercial',
    topics: ['commercial', 'retail', 'food_premises', 'neighbourhood_shop'],
    reason: 'No commercial or retail component confirmed',
  },
  {
    field: 'has_boarding_house',
    topics: ['boarding_house', 'co_living'],
    reason: 'No boarding house or co-living component confirmed',
  },
  {
    field: 'has_multi_dwelling',
    topics: ['multi_dwelling', 'residential_flat', 'dual_occupancy'],
    reason: 'No multi-dwelling or dual occupancy component confirmed',
  },
  {
    field: 'is_subdivision',
    topics: ['subdivision'],
    reason: 'No land subdivision in proposal confirmed',
  },
  {
    field: 'has_child_care',
    topics: ['child_care', 'childcare', 'child_care_facility', 'education', 'community_facility', 'community_facilities'],
    reason: 'No child care, education, or community facility component confirmed',
  },
  {
    field: 'has_home_business',
    topics: ['home_business', 'home_industry', 'home_occupation'],
    reason: 'No home business or home industry component confirmed',
  },
  {
    field: 'has_tourist_accommodation',
    topics: ['tourist_accommodation', 'visitor_accommodation', 'short_term_rental', 'tourist', 'serviced_apartment'],
    reason: 'No tourist, visitor, or short-term accommodation component confirmed',
  },
  {
    field: 'has_industrial',
    topics: ['industrial', 'warehouse', 'light_industrial', 'heavy_industrial'],
    reason: 'No industrial or warehouse use confirmed',
  },
];

/**
 * Derive questionnaire-driven topic exclusions from works scope answers.
 * Returns a Map of topic → reason for topics that should be auto-scoped out.
 * Only includes topics where the answer is explicitly false.
 */
export function deriveQuestionnaireTopics(
  answers: WorksScopeAnswers | null,
): Map<string, string> {
  const excluded = new Map<string, string>();
  if (!answers) return excluded;

  for (const { field, topics, reason } of SCOPE_TOPIC_MAP) {
    if (answers[field] === false) {
      for (const topic of topics) {
        excluded.set(topic, reason);
      }
    }
  }

  return excluded;
}

/**
 * Returns true if any scope questions have been answered (even partially).
 * Used to determine whether to show the scope summary.
 */
export function hasScopeAnswers(answers: WorksScopeAnswers | null): boolean {
  if (!answers) return false;
  return (
    (answers.heritage_elements !== null && answers.heritage_elements.length > 0) ||
    answers.has_commercial !== null ||
    answers.has_boarding_house !== null ||
    answers.has_multi_dwelling !== null ||
    answers.is_subdivision !== null ||
    answers.has_child_care !== null ||
    answers.has_home_business !== null ||
    answers.has_tourist_accommodation !== null ||
    answers.has_industrial !== null
  );
}
