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

export const COUNCIL_CONFIGS: Record<string, CouncilConfig> = {
  marrickville: {
    id: 'marrickville',
    name: 'Marrickville',
    dcpCitation: 'Inner West Development Control Plan (Marrickville) 2011',
    dcpExplanation: '46 suburb precincts (Parts 1-9 etc.) each with local character controls. Balanced across layers: 30% precinct-specific (green), 32% zone-specific (blue), 26% general (grey). Zone and dev-type filters both effective here.',
    totalProvisions: 1051,
    primaryLayer: 'precinct',
    zoneFilterEffective: true,
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
    dcpExplanation: '26 suburbs in Part G with local character controls. Heavily general (grey): 77% apply LGA-wide. Zone filtering ineffective (2% blue). Dev-type filter is key here (81% are dev-type specific). 21% have precinct controls (green). Use topic filter to manage volume.',
    totalProvisions: 2989,
    primaryLayer: 'generic',
    zoneFilterEffective: false,
    topicFilterRequired: true,
    warningThreshold: 200,
    resultGuidance: {
      DA_expected: '50-100 (with topic)',
      CDC_expected: '15-25',
    },
    suggestedTopics: ['parking', 'building_form', 'landscaping', 'heritage', 'setbacks', 'height'],
    topicOrder: {
      certifier: ['parking', 'setbacks', 'height', 'landscaping', 'building_form', 'heritage', 'access'],
      planner: ['building_form', 'heritage', 'parking', 'landscaping', 'height', 'setbacks'],
    },
  },

  ashfield: {
    id: 'ashfield',
    name: 'Ashfield',
    dcpCitation: 'Inner West Development Control Plan (Ashfield) 2016',
    dcpExplanation: '11 urban villages in Chapter D (specific areas only, 13% green). Site conditions dominate: 59% are heritage/flood controls (amber) - check Heritage topic for these. 28% general (grey). Zone filtering ineffective (2% blue). Dev-type moderate (33%).',
    totalProvisions: 1526,
    primaryLayer: 'condition',
    zoneFilterEffective: false,
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
