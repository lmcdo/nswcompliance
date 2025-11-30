/**
 * Council-Specific Configuration
 *
 * Each Inner West council (former LGAs) has a different DCP structure
 * that requires different UI/UX approaches for optimal professional use.
 */

export interface CouncilConfig {
  id: string;
  name: string;
  dcpCitation: string;
  dcpExplanation: string;
  totalProvisions: number;
  primaryLayer: 'generic' | 'precinct' | 'condition' | 'use_specific';
  zoneFilterEffective: boolean;
  devTypeFilterEffective: boolean;
  devTypeNote?: string; // Displayed when dev type has no effect
  availableDevTypes?: { id: string; name: string; count: number }[];
  topicFilterRequired: boolean;
  warningThreshold: number;
  resultGuidance: {
    DA_expected: string;
    CDC_expected: string;
  };
  suggestedTopics: string[];
  topicOrder: {
    certifier: string[];
    planner: string[];
  };
}

/**
 * Inner West LGA Overview - shown as collapsible header for all Inner West addresses
 */
export const INNER_WEST_OVERVIEW = `Inner West Council was formed in 2016 from three former councils: Ashfield, Leichhardt, and Marrickville. Each retains its own DCP with distinct approaches:

• Marrickville - zone-centric, provisions organised by zone type, most filterable
• Leichhardt - topic-centric, most provisions apply universally, highest volume
• Ashfield - development-type focused, heritage-heavy, use dropdown to filter

Your address determines which former council's DCP applies.`;

export const COUNCIL_CONFIGS: Record<string, CouncilConfig> = {
  marrickville: {
    id: 'marrickville',
    name: 'Marrickville',
    dcpCitation: 'Inner West Development Control Plan (Marrickville) 2011',
    dcpExplanation: 'Zone-centric DCP - unlike the others, this one has explicit chapters per zone type. Your zone is auto-detected from the address and filters results automatically. Development type dropdown not available - provisions are organised by zone chapter instead. All 48 suburb precincts have local character controls.\n\n• Part 4.1 (controls for R2 low density) • Part 4.2 (controls for R3/R4 multi-dwelling) • Part 5 (controls for business) • Part 6 (controls for industrial) • Part 8 (controls for heritage) • Part 9 (controls for 48 precincts)',
    totalProvisions: 1051,
    primaryLayer: 'precinct',
    zoneFilterEffective: true,
    devTypeFilterEffective: false,
    devTypeNote: 'For Marrickville Council DCP 2011, provisions apply broadly by topic rather than development type. For permitted uses in your zone, see the SEPP & LEP tab.',
    topicFilterRequired: false,
    warningThreshold: 300,
    resultGuidance: {
      DA_expected: '150-250',
      CDC_expected: '15-25',
    },
    suggestedTopics: ['setbacks', 'height', 'parking', 'heritage', 'building_form'],
    topicOrder: {
      certifier: ['setbacks', 'height', 'parking', 'landscaping', 'heritage', 'building_form', 'access', 'solar', 'privacy'],
      planner: ['building_form', 'heritage', 'height', 'setbacks', 'landscaping', 'parking', 'access'],
    },
  },

  leichhardt: {
    id: 'leichhardt',
    name: 'Leichhardt',
    dcpCitation: 'Inner West Development Control Plan (Leichhardt) 2013',
    dcpExplanation: 'Topic-centric DCP organised by theme - most provisions apply universally regardless of zone. Heritage controls are embedded throughout rather than in a separate chapter. Development type dropdown not available. Use topic filtering to navigate. 26 Distinctive Neighbourhoods in Part G provide area-specific character guidance.\n\n• Part C "Place" (controls for setbacks, heights, parking, landscaping - largest section) • Part D (controls for energy) • Part E (controls for water) • Part F (controls for food) • Part G (controls for 26 neighbourhoods)',
    totalProvisions: 2648,
    primaryLayer: 'generic',
    zoneFilterEffective: false,
    devTypeFilterEffective: false,
    devTypeNote: 'For Leichhardt Council DCP 2013, provisions apply universally by topic rather than development type. For permitted uses in your zone, see the SEPP & LEP tab.',
    topicFilterRequired: true,
    warningThreshold: 200,
    resultGuidance: {
      DA_expected: '50-100 (with topic)',
      CDC_expected: '15-25',
    },
    suggestedTopics: ['heritage', 'parking', 'building_form', 'landscaping', 'setbacks', 'height', 'trees'],
    topicOrder: {
      certifier: ['parking', 'setbacks', 'height', 'landscaping', 'building_form', 'heritage', 'access', 'trees'],
      planner: ['building_form', 'heritage', 'parking', 'landscaping', 'height', 'setbacks', 'trees'],
    },
  },

  ashfield: {
    id: 'ashfield',
    name: 'Ashfield',
    dcpCitation: 'Inner West Development Control Plan (Ashfield) 2016',
    dcpExplanation: 'Development-type focused DCP - heritage-heavy with a dedicated heritage chapter. Chapter F contains controls for dwelling houses, multi-dwelling housing, residential flat buildings, and other development types. Chapter C covers sustainability. 11 urban village precincts in Chapter D.\n\n• Chapter F (controls for development types) • Chapter E1 (controls for heritage) • Chapter C (controls for sustainability) • Chapter D (controls for specific precincts)',
    totalProvisions: 1526,
    primaryLayer: 'condition',
    zoneFilterEffective: true,
    devTypeFilterEffective: true,
    availableDevTypes: [
      { id: 'dwelling_house', name: 'Dwelling House', count: 57 },
      { id: 'multi_dwelling_housing', name: 'Multi Dwelling Housing', count: 52 },
      { id: 'residential_flat_building', name: 'Residential Flat Building', count: 49 },
      { id: 'shop_top_housing', name: 'Shop Top Housing', count: 40 },
      { id: 'food_and_drink_premises', name: 'Food & Drink Premises', count: 18 },
      { id: 'take_away_food', name: 'Take Away Food', count: 18 },
      { id: 'secondary_dwelling', name: 'Secondary Dwelling', count: 13 },
      { id: 'neighbourhood_centre', name: 'Neighbourhood Centre', count: 12 },
      { id: 'attached_dwelling', name: 'Attached Dwelling', count: 11 },
      { id: 'manor_house', name: 'Manor House', count: 11 },
      { id: 'neighbourhood_shop', name: 'Neighbourhood Shop', count: 11 },
      { id: 'townhouse', name: 'Townhouse', count: 11 },
      { id: 'business_park', name: 'Business Park', count: 5 },
      { id: 'commercial_core', name: 'Commercial Core', count: 4 },
      { id: 'shop', name: 'Shop', count: 4 },
      { id: 'boarding_house', name: 'Boarding House', count: 3 },
      { id: 'child_care_centre', name: 'Child Care Centre', count: 3 },
      { id: 'student_accommodation', name: 'Student Accommodation', count: 3 },
      { id: 'residential_care_facility', name: 'Residential Care Facility', count: 1 },
      { id: 'seniors_housing', name: 'Seniors Housing', count: 1 },
    ],
    topicFilterRequired: false,
    warningThreshold: 500,
    resultGuidance: {
      DA_expected: '300-450',
      CDC_expected: '1-5',
    },
    suggestedTopics: ['building_form', 'parking', 'trees', 'access', 'heritage', 'waste'],
    topicOrder: {
      certifier: ['parking', 'height', 'trees', 'access', 'building_form', 'heritage', 'waste'],
      planner: ['building_form', 'heritage', 'trees', 'parking', 'access'],
    },
  },
};

/**
 * Detect council from LGA or formerCouncil field
 */
export function detectCouncil(lga?: string, formerCouncil?: string): string | null {
  const council = (formerCouncil || '').toLowerCase();
  const lgaLower = (lga || '').toLowerCase();

  if (council.includes('marrickville') || lgaLower.includes('marrickville')) {
    return 'marrickville';
  }
  if (council.includes('leichhardt') || lgaLower.includes('leichhardt')) {
    return 'leichhardt';
  }
  if (council.includes('ashfield') || lgaLower.includes('ashfield')) {
    return 'ashfield';
  }

  // Default for Inner West if not specific
  if (lgaLower.includes('inner west')) {
    // Could try to detect from address/precinct, for now default to marrickville
    return null;
  }

  return null;
}

/**
 * Get council config, with fallback to marrickville defaults
 */
export function getCouncilConfig(councilId: string | null): CouncilConfig {
  if (councilId && COUNCIL_CONFIGS[councilId]) {
    return COUNCIL_CONFIGS[councilId];
  }
  // Default fallback
  return COUNCIL_CONFIGS.marrickville;
}

/**
 * Topic display labels
 */
export const TOPIC_LABELS: Record<string, string> = {
  setbacks: 'Setbacks',
  height: 'Height & Envelope',
  parking: 'Parking',
  heritage: 'Heritage',
  landscaping: 'Landscaping',
  building_form: 'Building Form & Character',
  solar: 'Solar Access',
  privacy: 'Privacy',
  access: 'Access & Movement',
  trees: 'Trees & Vegetation',
  waste: 'Waste Management',
  stormwater: 'Stormwater',
  flooding: 'Flooding',
  signage: 'Signage',
  fencing: 'Fencing',
  contamination: 'Site Contamination',
  views: 'Views',
  environmental: 'Environmental',
  wsud: 'Water Sensitive Urban Design',
  safety: 'Safety & Security',
  site_analysis: 'Site Analysis',
  open_space: 'Open Space',
  general: 'General',
  other: 'Other Requirements',
};

/**
 * Sort topics by professional priority order
 */
export function sortTopicsByPriority(
  topics: string[],
  councilId: string | null,
  mode: 'certifier' | 'planner' = 'certifier'
): string[] {
  const config = getCouncilConfig(councilId);
  const priorityOrder = config.topicOrder[mode];

  return [...topics].sort((a, b) => {
    const aIndex = priorityOrder.indexOf(a);
    const bIndex = priorityOrder.indexOf(b);

    // If both in priority list, sort by priority
    if (aIndex !== -1 && bIndex !== -1) {
      return aIndex - bIndex;
    }
    // Priority list items come first
    if (aIndex !== -1) return -1;
    if (bIndex !== -1) return 1;
    // Otherwise alphabetical
    return a.localeCompare(b);
  });
}
