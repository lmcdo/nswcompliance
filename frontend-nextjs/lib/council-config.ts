/**
 * Council-Specific Configuration
 *
 * Each Inner West council (former LGAs) has a different DCP structure
 * that requires different UI/UX approaches for optimal professional use.
 */

export interface CategoryGroup {
  label: string;
  categories: string[];  // LLM categories in this group
  showSubcategories: boolean;  // Whether to show individual categories
  priority: number;  // Display order (lower = higher priority)
}

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
  // Council-specific layer labels
  layerLabels: {
    generic: string;
    use_specific: string;
    condition: string;
    precinct: string;
  };
  // Hide layers with 0 or minimal provisions
  hideLayers?: ('generic' | 'use_specific' | 'condition' | 'precinct')[];
  // Category groupings for UI display
  categoryGroups: Record<string, CategoryGroup>;
}

/**
 * Inner West LGA Overview - shown as collapsible header for all Inner West addresses
 */
export const INNER_WEST_OVERVIEW = `Inner West Council was formed in 2016 from three former councils: Ashfield, Leichhardt, and Marrickville. Each retains its own DCP with distinct organizational approaches. Your address determines which former council's DCP applies.

MARRICKVILLE (1,866 provisions) has chapters for residential, commercial, and industrial development, but the majority of provisions are in Part 2 Generic Provisions which apply universally regardless of development type. Heritage has a dedicated chapter (Part 8) covering 37 Heritage Conservation Areas. Precinct Character controls (Part 9) cover 48 suburb areas with desired future character statements. Use topic filters to navigate - development type filtering is not effective here.

LEICHHARDT (3,355 provisions) is topic-centric with the highest provision count. Unlike Marrickville and Ashfield, the development type filter is effective here - selecting Commercial or Industrial hides approximately 2,000 residential-only provisions. Heritage provisions are distributed across multiple topics rather than consolidated in a dedicated chapter. The 26 Distinctive Neighbourhood controls provide character guidance for specific areas.

ASHFIELD (1,892 provisions) is heritage-focused with Chapter E1 providing extensive controls for Heritage Conservation Areas including conservation principles, character assessment, building form, and materials guidance. Most provisions (69%) apply broadly to all development types, so development type filtering is not effective. The 11 Village Precinct controls cover urban village areas with local character guidance. Use topic filters to navigate.`;

export const COUNCIL_CONFIGS: Record<string, CouncilConfig> = {
  marrickville: {
    id: 'marrickville',
    name: 'Marrickville',
    dcpCitation: 'Inner West Development Control Plan (Marrickville) 2011',
    dcpExplanation: 'Marrickville DCP is organized by development type with separate chapters for residential (Part 4), commercial (Part 5), and industrial (Part 6). Your zone determines which chapter applies, but the majority of provisions are in Part 2 Generic Provisions which apply universally to all development.\n\n[Base Controls] (Part 2) cover 25 topics including parking, landscaping, solar access, and urban design. [Heritage] has a dedicated chapter (Part 8) with detailed controls for heritage items and 37 Heritage Conservation Areas - filtered to your property\'s HCA. [Precinct Character] controls (Part 9) cover 48 suburb Precincts with desired future character statements - filtered to your address.\n\nUse topic filters to navigate. Development type filtering is not available as provisions apply broadly by topic.',
    totalProvisions: 1866,
    primaryLayer: 'generic',
    zoneFilterEffective: false,
    devTypeFilterEffective: false,
    devTypeNote: 'Marrickville provisions are organized by topic (Part 2) rather than development type. Your zone determines which Part applies but most controls are universal.',
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
    layerLabels: {
      generic: 'Base Controls',
      use_specific: 'Zone Controls',
      condition: 'Heritage',
      precinct: 'Precinct Character',
    },
    categoryGroups: {
      heritage: {
        label: 'Heritage',
        categories: ['heritage', 'character'],
        showSubcategories: false,
        priority: 1,
      },
      building: {
        label: 'Building Form',
        categories: ['building_form', 'building_height'],
        showSubcategories: false,
        priority: 2,
      },
      setbacks: {
        label: 'Setbacks',
        categories: ['setbacks', 'setback_front'],
        showSubcategories: false,
        priority: 3,
      },
      landscaping: {
        label: 'Landscaping',
        categories: ['landscaping', 'biodiversity'],
        showSubcategories: false,
        priority: 4,
      },
      sustainability: {
        label: 'Sustainability',
        categories: ['sustainability', 'energy_efficiency', 'solar_access'],
        showSubcategories: false,
        priority: 5,
      },
      parking: {
        label: 'Parking & Access',
        categories: ['parking', 'accessibility', 'transport'],
        showSubcategories: false,
        priority: 6,
      },
      signage: {
        label: 'Signage',
        categories: ['signage'],
        showSubcategories: false,
        priority: 7,
      },
      water: {
        label: 'Water & Stormwater',
        categories: ['stormwater', 'water_management'],
        showSubcategories: false,
        priority: 8,
      },
      other: {
        label: 'Other',
        categories: ['other', 'subdivision', 'da_requirements', 'safety', 'fencing', 'environmental', 'land_use', 'health_wellbeing', 'streetscape', 'acoustic', 'amenity', 'privacy', 'location'],
        showSubcategories: false,
        priority: 99,
      },
    },
  },

  leichhardt: {
    id: 'leichhardt',
    name: 'Leichhardt',
    dcpCitation: 'Inner West Development Control Plan (Leichhardt) 2013',
    dcpExplanation: 'Unlike Marrickville (zone-based) or Ashfield (heritage-focused), Leichhardt is topic-centric with the highest provision count (3,355). Most provisions are [Universal] controls that apply broadly.\n\n[Heritage] provisions cover heritage items and conservation areas but are distributed across topics rather than in a dedicated chapter - look under both Heritage and Character topics. [Distinct Neighbourhood] controls cover 26 areas - filtered to your address, with Universal controls applying where Neighbourhood controls are silent.\n\nDCP STRUCTURE: Part C "Place" (setbacks, heights, parking, landscaping - largest section) • Part D (energy) • Part E (water) • Part F (food premises) • Part G (26 Distinct Neighbourhoods)\n\n1. USE THE DROPDOWN TO FILTER BY PROJECT TYPE:\n• Residential = houses, apartments, granny flats, duplexes (~2,750 provisions)\n• Commercial = shops, offices, cafes, restaurants (~660 provisions)\n• Industrial = factories, warehouses (~780 provisions)\nSelecting Commercial or Industrial hides ~2,000 residential-only provisions. Selecting Residential only hides ~600 commercial/industrial provisions - most of this DCP is residential-focused.\n\n2. Select the topics you are interested in to further refine your search.',
    totalProvisions: 3355,
    primaryLayer: 'generic',
    zoneFilterEffective: false,
    devTypeFilterEffective: true,
    availableDevTypes: [
      { id: 'residential', name: 'Residential (all types)', count: 2756 },
      { id: 'commercial', name: 'Commercial / Retail', count: 660 },
      { id: 'industrial', name: 'Industrial / Warehouse', count: 779 },
    ],
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
    layerLabels: {
      generic: 'Universal',
      use_specific: 'Zone',
      condition: 'Heritage',
      precinct: 'Distinct Neighbourhood',
    },
    hideLayers: ['use_specific'],
    categoryGroups: {
      environmental: {
        label: 'Environmental',
        categories: ['contamination', 'water_management', 'stormwater', 'drainage', 'flood_management', 'environmental', 'biodiversity'],
        showSubcategories: false,
        priority: 1,
      },
      parking: {
        label: 'Parking & Access',
        categories: ['parking', 'accessibility'],
        showSubcategories: false,
        priority: 2,
      },
      waste: {
        label: 'Waste',
        categories: ['waste_management'],
        showSubcategories: false,
        priority: 3,
      },
      safety: {
        label: 'Safety',
        categories: ['safety'],
        showSubcategories: false,
        priority: 4,
      },
      landscaping: {
        label: 'Landscaping & Trees',
        categories: ['landscaping', 'tree_preservation', 'deep_soil', 'open_space'],
        showSubcategories: false,
        priority: 5,
      },
      character: {
        label: 'Character & Heritage',
        categories: ['character', 'heritage', 'streetscape'],
        showSubcategories: false,
        priority: 6,
      },
      building: {
        label: 'Building',
        categories: ['building_form', 'building_height', 'privacy', 'acoustic'],
        showSubcategories: false,
        priority: 7,
      },
      sustainability: {
        label: 'Sustainability',
        categories: ['sustainability', 'energy_efficiency', 'solar_access'],
        showSubcategories: false,
        priority: 8,
      },
      signage: {
        label: 'Signage',
        categories: ['signage'],
        showSubcategories: false,
        priority: 9,
      },
      setbacks: {
        label: 'Setbacks',
        categories: ['setbacks', 'setback_front', 'setback_side', 'setback_rear'],
        showSubcategories: false,
        priority: 10,
      },
      other: {
        label: 'Other',
        categories: ['other', 'da_requirements', 'social_impact', 'public_domain', 'health_wellbeing', 'subdivision', 'public_art', 'site_coverage', 'amenity'],
        showSubcategories: false,
        priority: 99,
      },
    },
  },

  ashfield: {
    id: 'ashfield',
    name: 'Ashfield',
    dcpCitation: 'Inner West Development Control Plan (Ashfield) 2016',
    dcpExplanation: 'Ashfield DCP is heritage-focused with Chapter E1 providing extensive controls for Heritage Conservation Areas. Chapter F covers development categories and Chapter D provides guidance for 11 Village Precincts. Most provisions (69%) apply broadly across all development types.\n\n[Base Controls] in Chapter A cover general requirements. [Heritage] (Chapter E1) is the most detailed section with conservation principles, character assessment, building form, and materials guidance for each HCA - filtered to your property\'s HCA. [Village Precinct] controls (Chapter D) cover 11 urban village areas - filtered to your address.\n\nUse topic filters to navigate. Development type filtering is not effective as most provisions apply broadly.',
    totalProvisions: 1892,
    primaryLayer: 'condition',
    zoneFilterEffective: false,
    devTypeFilterEffective: false,
    devTypeNote: 'Ashfield provisions apply broadly (69% tagged as ALL development types). Use topic filters instead.',
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
    layerLabels: {
      generic: 'Base Controls',
      use_specific: 'Dev Type',
      condition: 'Heritage',
      precinct: 'Village Precinct',
    },
    hideLayers: ['use_specific'],
    categoryGroups: {
      heritage: {
        label: 'Heritage & Character',
        categories: ['heritage', 'character', 'streetscape'],
        showSubcategories: false,
        priority: 1,
      },
      setbacks: {
        label: 'Setbacks',
        categories: ['setback_front', 'setback_side', 'setback_rear', 'setbacks'],
        showSubcategories: true,  // Ashfield certifiers need front/side/rear distinction
        priority: 2,
      },
      building: {
        label: 'Building',
        categories: ['building_form', 'building_height'],
        showSubcategories: false,
        priority: 3,
      },
      parking: {
        label: 'Parking & Access',
        categories: ['parking', 'accessibility'],
        showSubcategories: false,
        priority: 4,
      },
      landscaping: {
        label: 'Landscaping & Trees',
        categories: ['landscaping', 'tree_preservation'],
        showSubcategories: false,
        priority: 5,
      },
      safety: {
        label: 'Safety & Privacy',
        categories: ['safety', 'privacy', 'fencing'],
        showSubcategories: false,
        priority: 6,
      },
      waste: {
        label: 'Waste',
        categories: ['waste_management'],
        showSubcategories: false,
        priority: 7,
      },
      water: {
        label: 'Water & Stormwater',
        categories: ['stormwater', 'water_management'],
        showSubcategories: false,
        priority: 8,
      },
      sustainability: {
        label: 'Sustainability',
        categories: ['sustainability', 'solar_access'],
        showSubcategories: false,
        priority: 9,
      },
      signage: {
        label: 'Signage',
        categories: ['signage'],
        showSubcategories: false,
        priority: 10,
      },
      site: {
        label: 'Site Controls',
        categories: ['site_area', 'site_coverage', 'deep_soil', 'open_space'],
        showSubcategories: false,
        priority: 11,
      },
      other: {
        label: 'Other',
        categories: ['other', 'da_requirements', 'subdivision', 'acoustic', 'location', 'biodiversity', 'contamination', 'environmental', 'amenity'],
        showSubcategories: false,
        priority: 99,
      },
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
  setback_front: 'Front Setback',
  setback_side: 'Side Setback',
  setback_rear: 'Rear Setback',
  height: 'Height & Envelope',
  building_height: 'Building Height',
  parking: 'Parking',
  heritage: 'Heritage',
  landscaping: 'Landscaping',
  building_form: 'Building Form & Character',
  solar: 'Solar Access',
  solar_access: 'Solar Access',
  privacy: 'Privacy',
  access: 'Access & Movement',
  accessibility: 'Accessibility',
  trees: 'Trees & Vegetation',
  tree_preservation: 'Tree Preservation',
  waste: 'Waste Management',
  waste_management: 'Waste Management',
  stormwater: 'Stormwater',
  water_management: 'Water Management',
  flooding: 'Flooding',
  flood_management: 'Flood Management',
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
  streetscape: 'Streetscape',
  subdivision: 'Subdivision',
  character: 'Character',
  sustainability: 'Sustainability',
  energy_efficiency: 'Energy Efficiency',
  biodiversity: 'Biodiversity',
  transport: 'Transport',
  amenity: 'Amenity',
  acoustic: 'Acoustic',
  health_wellbeing: 'Health & Wellbeing',
  land_use: 'Land Use',
  location: 'Location',
  da_requirements: 'DA Requirements',
  drainage: 'Drainage',
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

/**
 * Get category groups sorted by priority
 */
export function getSortedCategoryGroups(councilId: string | null): Array<{
  key: string;
  group: CategoryGroup;
}> {
  const config = getCouncilConfig(councilId);
  return Object.entries(config.categoryGroups)
    .map(([key, group]) => ({ key, group }))
    .sort((a, b) => a.group.priority - b.group.priority);
}

/**
 * Find which group a category belongs to
 */
export function getCategoryGroup(
  category: string,
  councilId: string | null
): { groupKey: string; group: CategoryGroup } | null {
  const config = getCouncilConfig(councilId);
  const lowerCategory = category.toLowerCase();

  for (const [groupKey, group] of Object.entries(config.categoryGroups)) {
    if (group.categories.includes(lowerCategory)) {
      return { groupKey, group };
    }
  }

  // Default to 'other' group if not found
  if (config.categoryGroups.other) {
    return { groupKey: 'other', group: config.categoryGroups.other };
  }

  return null;
}

/**
 * Group provisions by category group
 */
export function groupProvisionsByCategory<T extends { category?: string }>(
  provisions: T[],
  councilId: string | null
): Record<string, { group: CategoryGroup; provisions: T[]; subcategories: Record<string, T[]> }> {
  const config = getCouncilConfig(councilId);
  const grouped: Record<string, { group: CategoryGroup; provisions: T[]; subcategories: Record<string, T[]> }> = {};

  // Initialize all groups
  for (const [groupKey, group] of Object.entries(config.categoryGroups)) {
    grouped[groupKey] = { group, provisions: [], subcategories: {} };
  }

  // Assign provisions to groups
  for (const provision of provisions) {
    const category = (provision.category || 'other').toLowerCase();
    const result = getCategoryGroup(category, councilId);

    if (result) {
      const { groupKey, group } = result;
      grouped[groupKey].provisions.push(provision);

      // Track subcategories if group shows them
      if (group.showSubcategories) {
        if (!grouped[groupKey].subcategories[category]) {
          grouped[groupKey].subcategories[category] = [];
        }
        grouped[groupKey].subcategories[category].push(provision);
      }
    }
  }

  return grouped;
}

/**
 * Category display labels (for subcategories)
 */
export const CATEGORY_LABELS: Record<string, string> = {
  setback_front: 'Front Setback',
  setback_side: 'Side Setback',
  setback_rear: 'Rear Setback',
  setbacks: 'General Setbacks',
  building_form: 'Building Form',
  building_height: 'Building Height',
  tree_preservation: 'Tree Preservation',
  waste_management: 'Waste Management',
  water_management: 'Water Management',
  solar_access: 'Solar Access',
  site_area: 'Site Area',
  site_coverage: 'Site Coverage',
  deep_soil: 'Deep Soil',
  open_space: 'Open Space',
  da_requirements: 'DA Requirements',
  health_wellbeing: 'Health & Wellbeing',
  flood_management: 'Flood Management',
  energy_efficiency: 'Energy Efficiency',
  social_impact: 'Social Impact',
  public_domain: 'Public Domain',
  public_art: 'Public Art',
};
