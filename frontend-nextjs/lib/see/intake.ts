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
  /** Is the site in an ANEF aircraft noise zone? Auto-answered from SEPP (Transport Infrastructure) 2021. */
  acoustic_zone: 'yes' | 'no' | 'unknown';
  /** Is the site in a mine subsidence district? Auto-answered from SEPP (Resilience and Hazards) 2021 Ch.3. */
  mine_subsidence: 'yes' | 'no' | 'unknown';
  /** Is the site in a landslide risk area? Auto-answered from LEP Part 5. */
  landslide_risk: 'yes' | 'no' | 'unknown';
  /** Are there EPA-notified contaminated sites within 500m? Auto-answered from SEPP (Resilience and Hazards) 2021 Ch.4. */
  contaminated_land: 'yes' | 'no' | 'unknown';
  /** Is the site in a drinking water catchment area? Auto-answered from SEPP (Resilience and Hazards) 2021 Ch.2. */
  drinking_water_catchment: 'yes' | 'no' | 'unknown';
  // --- New manual question ---
  /** Does the proposal include demolition of any structure? */
  demolition: 'yes' | 'no' | 'unknown';
  // --- Numeric proposal values (for LEP compliance check) ---
  /** Proposed maximum building height in metres. Used to auto-populate LEP Clause 4.3 Proposal column. */
  proposed_height?: string;
  /** Proposed gross floor area in m². Used with lot area to auto-populate LEP Clause 4.4 Proposal column. */
  proposed_gfa?: string;
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
  /** One-sentence rationale when constraint is confirmed present (answer is 'yes'). */
  rationale_yes?: string;
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
    rationale_yes: 'Site is flood prone per LEP mapping — flood management provisions are in scope',
  },
  bushfire_prone: {
    propertyField: 'constraints.bushfireProne',
    citation: 'LEP Part 5 — Bushfire Prone Land',
    rationale: 'Site confirmed not bushfire prone per LEP mapping',
    rationale_yes: 'Site is bushfire prone per LEP mapping — bushfire provisions are in scope',
  },
  acid_sulfate_soils: {
    propertyField: 'constraints.acidSulfateSoils',
    citation: 'LEP Part 5 — Acid Sulfate Soils',
    rationale: 'Site confirmed no acid sulfate soils per LEP mapping',
    rationale_yes: 'Site has acid sulfate soils per LEP mapping — acid sulfate provisions are in scope',
  },
  coastal: {
    propertyField: 'constraints.coastalEnvironment.inCoastalArea',
    citation: 'SEPP (Resilience and Hazards) 2021 — Coastal Management',
    rationale: 'Site confirmed not in coastal management area',
    rationale_yes: 'Site is in a coastal management area — coastal provisions are in scope',
  },
  biodiversity: {
    propertyField: 'constraints.terrestrialBiodiversity.inBiodiversityArea',
    citation: 'LEP Part 5 — Terrestrial Biodiversity',
    rationale: 'Site confirmed no terrestrial biodiversity overlay',
    rationale_yes: 'Site is in a terrestrial biodiversity area — biodiversity provisions are in scope',
  },
  acoustic_zone: {
    propertyField: 'constraints.anefData.inAnefZone',
    citation: 'SEPP (Transport Infrastructure) 2021 — Aircraft Noise',
    rationale: 'Site confirmed not in ANEF aircraft noise zone per portal mapping',
    rationale_yes: 'Site is in an ANEF aircraft noise zone — acoustic provisions are in scope',
  },
  mine_subsidence: {
    propertyField: 'constraints.mineSubsidence.inDistrict',
    citation: 'SEPP (Resilience and Hazards) 2021 — Mine Subsidence Ch.3',
    rationale: 'Site confirmed not in mine subsidence district per portal mapping',
    rationale_yes: 'Site is in a mine subsidence district — mine subsidence provisions are in scope',
  },
  landslide_risk: {
    propertyField: 'constraints.landslideRisk.hasRisk',
    citation: 'LEP Part 5 — Landslide Risk',
    rationale: 'Site confirmed not in landslide risk area per LEP mapping',
    rationale_yes: 'Site is in a landslide risk area — landslide provisions are in scope',
  },
  contaminated_land: {
    propertyField: 'constraints.contaminatedLand.hasNotifiedSites',
    citation: 'SEPP (Resilience and Hazards) 2021 — Contaminated Land Ch.4',
    rationale: 'No EPA-notified contaminated sites within 500m confirmed per portal mapping',
    rationale_yes: 'EPA-notified contaminated sites within 500m — contamination provisions are in scope',
  },
  drinking_water_catchment: {
    propertyField: 'constraints.drinkingWaterCatchment.inCatchment',
    citation: 'SEPP (Resilience and Hazards) 2021 — Drinking Water Catchment Ch.2',
    rationale: 'Site confirmed not in drinking water catchment area per portal mapping',
    rationale_yes: 'Site is in a drinking water catchment area — drinking water provisions are in scope',
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

// ---------------------------------------------------------------------------
// Structural category exclusion map (DD-1, 2026-03-13)
// ---------------------------------------------------------------------------
// Provisions are excluded based on v2_structural_category (derived from the
// DCP's own hierarchy — chapter_key + section_header), NOT v2_topic (inferred
// from keywords). This is zero-inference and compliance-safe: a provision in
// "Privacy" that mentions parking is NOT a parking provision structurally.
//
// v2_structural_category values come from enrichment/config/structural_categories.py.
// They are already lowercase, no normalization needed.
//
// Provisions with null v2_structural_category are NEVER excluded (fail-open).
export const TRIGGER_TO_STRUCTURAL_CATEGORIES: Record<keyof IntakeAnswers, string[]> = {
  new_impervious_surfaces: ['stormwater', 'drainage'],
  trees_affected: ['trees'],
  pool_or_spa: ['pool'],
  new_fencing: ['fencing'],
  new_parking_or_driveway: ['parking'],
  new_signage: ['signage'],
  flood_prone: ['flooding'],
  bushfire_prone: ['bushfire'],
  acid_sulfate_soils: [],
  coastal: ['coastal'],
  biodiversity: ['biodiversity'],
  acoustic_zone: ['acoustic'],
  mine_subsidence: ['mine_subsidence'],
  landslide_risk: ['landslide'],
  contaminated_land: ['contamination'],
  drinking_water_catchment: ['drinking_water'],
  demolition: ['demolition'],
  proposed_height: [],
  proposed_gfa: [],
};

// Legacy topic-to-trigger map — SOFT UI ONLY (DCP browser filtering, display).
// DO NOT use for exclusion decisions. Use TRIGGER_TO_STRUCTURAL_CATEGORIES above.
export const TRIGGER_TO_TOPICS: Record<keyof IntakeAnswers, string[]> = {
  new_impervious_surfaces: ['stormwater', 'drainage'],
  trees_affected: ['trees'],
  pool_or_spa: ['pool'],
  new_fencing: ['fencing', 'fence'],
  new_parking_or_driveway: ['parking', 'vehicle_access', 'carport'],
  new_signage: ['signage'],
  // Auto-answered from LEP/SEPP property data
  flood_prone: ['flooding'],
  bushfire_prone: ['bushfire'],
  acid_sulfate_soils: ['acid_sulfate'], // 'contamination' removed: general site contamination != ASS (DB evidence: 0 provisions with acid_sulfate topic; contamination provisions need site investigation, not ASS mapping)
  coastal: ['coastal'],
  biodiversity: ['biodiversity'],
  acoustic_zone: ['acoustic', 'noise', 'anef'],
  mine_subsidence: ['mine_subsidence'],
  landslide_risk: ['landslide'],
  contaminated_land: [], // No DCP topic exclusion — general contamination requires site investigation regardless
  drinking_water_catchment: ['drinking_water'],
  // Manual
  demolition: ['demolition'],
  // Numeric proposal values — no topic exclusion, used for LEP compliance check only
  proposed_height: [],
  proposed_gfa: [],
};

// ---------------------------------------------------------------------------
// Topics intentionally NOT mapped to intake triggers (W2-4)
// ---------------------------------------------------------------------------
// These topics exist in the DB but cannot be auto-excluded without dev-type
// awareness, applicant input, or site-specific assessment. They always remain
// in the active provision set until the planner manually addresses them.
//
// 'heritage'       — always applies if heritage overlay; managed by HCA/item flags, not intake
// 'precinct'       — precinct-specific; managed by v2_precinct_id, not intake triggers
// 'site_analysis'  — general site context; applies to every DA
// 'height'         — numeric standard; applies to every built-form DA
// 'setbacks'       — character/site-specific; no factual trigger possible
// 'building_form'  — design-based; applies to every built-form DA
// 'residential'    — zone-based; applies whenever development is residential
// 'landscaping'    — design-based; applies to virtually every DA; dev-type dependent
// 'roofing'        — design-based; applies to every built-form DA
// 'access'         — general; applies to every DA
// 'building_design'— design-based; applies to every built-form DA
// 'waste'          — general; applies to every DA
// 'open_space'     — site-specific; applies when open space present
// 'bicycle_parking'— provision requirement (not site trigger); applies when parking provided
// 'commercial'     — zone-based; applies when commercial use present
// 'industrial'     — zone-based; applies when industrial use present
// 'environmental'  — catch-all; no factual trigger possible
// 'sustainability' — general; applies to every DA
// 'privacy'        — site-specific; context-dependent
// 'views'          — site-specific; no factual trigger possible
// 'solar'          — design-based; applies to every DA
// 'safety'         — general; applies to every DA
// 'density'        — numeric/zone-based; applies to every DA
// 'contamination'  — general site contamination; requires site investigation (NOT auto-excluded
//                    by acid_sulfate_soils=No — different category, different legislative trigger)
//
// Source: W2-1 DB query, 2026-03-07, Inner West councils (ashfield/marrickville/leichhardt)

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
  acid_sulfate: 'Site confirmed no acid sulfate soils (LEP Part 5)',
  coastal: 'Site confirmed not in coastal management area (SEPP Resilience and Hazards 2021)',
  biodiversity: 'Site confirmed no terrestrial biodiversity overlay (LEP Part 5)',
  acoustic: 'Site confirmed not in ANEF aircraft noise zone (SEPP Transport Infrastructure 2021)',
  noise: 'Site confirmed not in ANEF aircraft noise zone (SEPP Transport Infrastructure 2021)',
  anef: 'Site confirmed not in ANEF aircraft noise zone (SEPP Transport Infrastructure 2021)',
  mine_subsidence: 'Site confirmed not in mine subsidence district (SEPP Resilience and Hazards 2021 Ch.3)',
  landslide: 'Site confirmed not in landslide risk area (LEP Part 5)',
  drinking_water: 'Site confirmed not in drinking water catchment (SEPP Resilience and Hazards 2021 Ch.2)',
  demolition: 'No demolition works in proposal confirmed',
  // Works scope questionnaire — use-type exclusions
  commercial: 'No commercial or retail component confirmed',
  retail: 'No commercial or retail component confirmed',
  food_premises: 'No commercial or retail component confirmed',
  neighbourhood_shop: 'No commercial or retail component confirmed',
  boarding_house: 'No boarding house or co-living component confirmed',
  co_living: 'No boarding house or co-living component confirmed',
  multi_dwelling: 'No multi-dwelling or dual occupancy component confirmed',
  residential_flat: 'No multi-dwelling or dual occupancy component confirmed',
  dual_occupancy: 'No multi-dwelling or dual occupancy component confirmed',
  subdivision: 'No land subdivision in proposal confirmed',
  child_care: 'No child care, education, or community facility component confirmed',
  childcare: 'No child care, education, or community facility component confirmed',
  child_care_facility: 'No child care, education, or community facility component confirmed',
  education: 'No child care, education, or community facility component confirmed',
  community_facility: 'No child care, education, or community facility component confirmed',
  community_facilities: 'No child care, education, or community facility component confirmed',
  home_business: 'No home business or home industry component confirmed',
  home_industry: 'No home business or home industry component confirmed',
  home_occupation: 'No home business or home industry component confirmed',
  tourist_accommodation: 'No tourist, visitor, or short-term accommodation component confirmed',
  visitor_accommodation: 'No tourist, visitor, or short-term accommodation component confirmed',
  short_term_rental: 'No tourist, visitor, or short-term accommodation component confirmed',
  tourist: 'No tourist, visitor, or short-term accommodation component confirmed',
  serviced_apartment: 'No tourist, visitor, or short-term accommodation component confirmed',
  industrial: 'No industrial or warehouse use confirmed',
  warehouse: 'No industrial or warehouse use confirmed',
  light_industrial: 'No industrial or warehouse use confirmed',
  heavy_industrial: 'No industrial or warehouse use confirmed',
};

// Dev-mode parity assertion: every topic in TRIGGER_TO_TOPICS must have a TOPIC_EXCLUSION_REASONS entry.
// Catches mismatches at module load time during development.
if (process.env.NODE_ENV === 'development') {
  for (const [field, topics] of Object.entries(TRIGGER_TO_TOPICS)) {
    for (const topic of topics) {
      if (!(topic in TOPIC_EXCLUSION_REASONS)) {
        throw new Error(`[intake] TRIGGER_TO_TOPICS field "${field}" has topic "${topic}" with no entry in TOPIC_EXCLUSION_REASONS`);
      }
    }
  }
}

/**
 * Normalize a v2_topic value to match the frontend comparison key.
 * Mirrors: v2_topic?.toLowerCase().replace(/ /g, '_')
 */
export function normalizeTopicKey(topic: string | null | undefined): string {
  if (!topic) return '';
  return topic.toLowerCase().replace(/ /g, '_');
}

/**
 * Returns the set of structural categories that can be auto-excluded
 * based on the confirmed intake answers.
 *
 * Uses TRIGGER_TO_STRUCTURAL_CATEGORIES (DCP hierarchy, zero-inference)
 * instead of TRIGGER_TO_TOPICS (keyword-inferred, unsafe for exclusion).
 *
 * A category is only added when the associated intake answer is explicitly 'no'.
 * 'unknown' and 'yes' leave the category in the active set.
 */
export function getExcludableTopics(answers: IntakeAnswers): Set<string> {
  const excluded = new Set<string>();
  for (const [field, categories] of Object.entries(TRIGGER_TO_STRUCTURAL_CATEGORIES)) {
    if (answers[field as keyof IntakeAnswers] === 'no') {
      for (const cat of categories) {
        excluded.add(cat);
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
 * Returns true if the provision should be auto-excluded given these answers.
 *
 * Uses v2_structural_category (DCP hierarchy) for exclusion decisions.
 * Provisions with null structural category are never excluded (fail-open).
 */
export function isProvisionExcluded(
  structuralCategory: string | null | undefined,
  answers: IntakeAnswers
): boolean {
  if (!structuralCategory) return false;
  return getExcludableTopics(answers).has(structuralCategory);
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
  acoustic_zone: 'unknown',
  mine_subsidence: 'unknown',
  landslide_risk: 'unknown',
  contaminated_land: 'unknown',
  drinking_water_catchment: 'unknown',
  demolition: 'unknown',
  proposed_height: undefined,
  proposed_gfa: undefined,
};

/**
 * Auto-populates intake answers from property constraints fetched from NSW Planning Portal.
 * Sets 'no' when the constraint is definitively absent; 'yes' when definitively present.
 * Never sets 'unknown' — that is the default and means "not yet determined".
 * Returns a partial — caller must merge over existing answers (existing answers always win).
 *
 * Usage:
 *   const autoAnswers = autoPopulateFromConstraints(propertyData.constraints);
 *   const merged = { ...DEFAULT_INTAKE_ANSWERS, ...autoAnswers, ...(savedAnswers ?? {}) };
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function autoPopulateFromConstraints(constraints: Record<string, any>): Partial<IntakeAnswers> {
  const result: Partial<IntakeAnswers> = {};

  // --- Flood ---
  if (constraints.floodProne === false) result.flood_prone = 'no';
  else if (constraints.floodProne === true) result.flood_prone = 'yes';

  // --- Bushfire ---
  if (constraints.bushfireProne === false) result.bushfire_prone = 'no';
  else if (constraints.bushfireProne === true) result.bushfire_prone = 'yes';

  // acidSulfateSoils is a string class or undefined/null — falsy means absent, truthy means present.
  if (!constraints.acidSulfateSoils) result.acid_sulfate_soils = 'no';
  else result.acid_sulfate_soils = 'yes';

  // coastal/biodiversity: portal only sets inCoastalArea/inBiodiversityArea when the overlay IS found.
  // Absent (undefined/null) = layer not detected = site confirmed NOT in that area.
  if (constraints.coastalEnvironment?.inCoastalArea === true) result.coastal = 'yes';
  else result.coastal = 'no';

  if (constraints.terrestrialBiodiversity?.inBiodiversityArea === true) result.biodiversity = 'yes';
  else result.biodiversity = 'no';

  // anefData lives at propertyData.anefData (top level), not inside constraints.
  // Call sites must merge it in: autoPopulateFromConstraints({ ...constraints, anefData })
  if (constraints.anefData?.inAnefZone === true) result.acoustic_zone = 'yes';
  else if (constraints.anefData?.inAnefZone === false) result.acoustic_zone = 'no';
  // anefData absent = portal didn't return ANEF data; leave as 'unknown'.

  // Remaining LEP Part 5 / SEPP (Resilience and Hazards) 2021 constraints.
  // Portal only sets these when the overlay IS found — absent means confirmed not present.
  if (constraints.mineSubsidence?.inDistrict === true) result.mine_subsidence = 'yes';
  else result.mine_subsidence = 'no';

  if (constraints.landslideRisk?.hasRisk === true) result.landslide_risk = 'yes';
  else result.landslide_risk = 'no';

  if (constraints.contaminatedLand?.hasNotifiedSites === true) result.contaminated_land = 'yes';
  else result.contaminated_land = 'no';

  if (constraints.drinkingWaterCatchment?.inCatchment === true) result.drinking_water_catchment = 'yes';
  else result.drinking_water_catchment = 'no';

  return result;
}
