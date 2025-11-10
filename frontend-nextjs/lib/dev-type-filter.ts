/**
 * Development Type Filtering - Strategy 4: Hybrid Multi-Signal
 *
 * Combines multiple signals with confidence weighting to intelligently filter
 * DCP requirements by development type.
 *
 * Accuracy: 75-85% (based on analysis in DEV_TYPE_FILTERING_COMPREHENSIVE_ANALYSIS.md)
 * Approach: Conservative (zero false negatives, acceptable false positives)
 */

export interface FilterableRequirement {
  id: number;
  category: string;
  requirement_text: string;
  verbatim_source_text?: string;
  part_number?: string;
  part_name?: string;
  section_header?: string;
  subcategory?: string;
}

interface Signal {
  applies: boolean;
  confidence: number;
  source: string;
}

// ============================================================================
// Phase 1: Category-Based Exclusions (70% confidence)
// ============================================================================

const CATEGORY_EXCLUSIONS: Record<string, string[]> = {
  residential: [
    'signage',              // Commercial signage requirements
    'loading_dock',         // Commercial/industrial loading
    'outdoor_dining',       // Commercial outdoor seating
    'shop_front',           // Commercial storefronts
    'commercial_premises',  // Commercial-specific controls
  ],
  commercial: [
    'private_open_space',   // Residential-specific open space
    'solar_access',         // Residential solar requirements
    'bedroom_size',         // Residential bedroom standards
    'apartment_mix',        // Residential apartment mix
    'dwelling_size',        // Residential dwelling size
  ],
  industrial: [
    'private_open_space',
    'solar_access',
    'bedroom_size',
    'balcony',
  ],
  childcare: [
    'bedroom_size',         // Not residential dwelling
    'apartment_mix',        // Not multi-res
    'dwelling_size',        // Not residential dwelling
    'loading_dock',         // Not commercial loading
    'shop_front',           // Not retail
    'outdoor_dining',       // Not food/drink premises
  ],
  mixed_use: [
    // Intentionally minimal exclusions - these developments need both residential AND commercial controls
  ],
};

const RESIDENTIAL_DEV_TYPES = [
  'dwelling_house',
  'secondary_dwelling',
  'dual_occupancy',
  'multi_dwelling_housing',
  'multi_dwelling',              // Dropdown variant (shortened form)
  'residential_flat_building',
  'residential_flat',            // Dropdown variant (shortened form)
  'boarding_house',              // Missing from original list
  'manor_house',
  'attached_dwelling',
  'semi_detached_dwelling',
];

const COMMERCIAL_DEV_TYPES = [
  'commercial',                  // Generic catch-all from dropdown
  'commercial_premises',         // Standard NSW LEP term
  'shop',
  'business_premises',
  'office_premises',
  'retail_premises',
  'food_and_drink_premises',
  'restaurant',
  'cafe',
];

const INDUSTRIAL_DEV_TYPES = [
  'light_industrial',
  'general_industrial',
  'warehouse',
  'industrial_premises',
];

// Special use types that need custom handling
const CHILDCARE_DEV_TYPES = [
  'child_care',
  'child_care_centre',
  'early_education_and_care_facility',
];

// Mixed-use types that need both residential AND commercial controls
const MIXED_USE_DEV_TYPES = [
  'shop_top_housing',
  'mixed_use_development',
];

// ============================================================================
// Phase 2: Explicit Text Patterns (90% confidence)
// ============================================================================

const EXPLICIT_RESIDENTIAL_PATTERNS = [
  /\bresidential areas?\b/i,
  /\bresidential zones?\b/i,
  /\bresidential properties\b/i,
  /\bdwellings?\b/i,
  /\bresidential accommodation\b/i,
  /\bin or abutting residential\b/i,
];

const EXPLICIT_COMMERCIAL_PATTERNS = [
  /\bcommercial areas?\b/i,
  /\bcommercial zones?\b/i,
  /\bcommercial premises\b/i,
  /\bshops?\b/i,
  /\bbusinesses?\b/i,
  /\bretail\b/i,
];

const EXPLICIT_INDUSTRIAL_PATTERNS = [
  /\bindustrial areas?\b/i,
  /\bindustrial zones?\b/i,
  /\bindustrial premises\b/i,
  /\bfactories\b/i,
  /\bwarehouses?\b/i,
];

const EXPLICIT_CHILDCARE_PATTERNS = [
  /\bchild care\b/i,
  /\bchildcare\b/i,
  /\bearly education\b/i,
  /\bday care\b/i,
  /\bnursery\b/i,
];

const EXPLICIT_MIXED_USE_PATTERNS = [
  /\bmixed use\b/i,
  /\bshop top\b/i,
  /\bresidential and commercial\b/i,
];

// ============================================================================
// Phase 3: Section Name Hints (60% confidence)
// ============================================================================

const SECTION_NAME_RESIDENTIAL_HINTS = [
  /residential/i,
  /dwelling/i,
  /apartment/i,
  /housing/i,
];

const SECTION_NAME_COMMERCIAL_HINTS = [
  /commercial/i,
  /shop/i,
  /business/i,
  /retail/i,
];

const SECTION_NAME_INDUSTRIAL_HINTS = [
  /industrial/i,
  /warehouse/i,
  /factory/i,
];

const SECTION_NAME_CHILDCARE_HINTS = [
  /child care/i,
  /childcare/i,
  /early education/i,
  /day care/i,
];

const SECTION_NAME_MIXED_USE_HINTS = [
  /mixed use/i,
  /shop top/i,
];

// ============================================================================
// Phase 4: Keyword Density (50% confidence)
// ============================================================================

const RESIDENTIAL_KEYWORDS = ['dwelling', 'house', 'apartment', 'bedroom', 'balcony', 'unit', 'flat'];
const COMMERCIAL_KEYWORDS = ['shop', 'business', 'retail', 'office', 'commercial', 'customer', 'trading'];
const INDUSTRIAL_KEYWORDS = ['warehouse', 'factory', 'industrial', 'loading', 'storage', 'manufacturing'];
const CHILDCARE_KEYWORDS = ['children', 'child', 'care', 'education', 'play', 'supervision'];
const MIXED_USE_KEYWORDS = ['mixed', 'shop top', 'residential and commercial', 'upper floor'];

// ============================================================================
// Main Filtering Logic
// ============================================================================

/**
 * Calculate whether a requirement applies to the given development type
 * using hybrid multi-signal approach
 */
function calculateApplicability(
  requirement: FilterableRequirement,
  developmentType: string
): boolean {
  const signals: Signal[] = [];

  // Determine dev type category
  let devTypeCategory: 'residential' | 'commercial' | 'industrial' | 'childcare' | 'mixed_use' | 'unknown' = 'unknown';
  if (RESIDENTIAL_DEV_TYPES.includes(developmentType)) {
    devTypeCategory = 'residential';
  } else if (COMMERCIAL_DEV_TYPES.includes(developmentType)) {
    devTypeCategory = 'commercial';
  } else if (INDUSTRIAL_DEV_TYPES.includes(developmentType)) {
    devTypeCategory = 'industrial';
  } else if (CHILDCARE_DEV_TYPES.includes(developmentType)) {
    devTypeCategory = 'childcare';
  } else if (MIXED_USE_DEV_TYPES.includes(developmentType)) {
    devTypeCategory = 'mixed_use';
  } else {
    // Log unrecognized types for debugging
    console.warn(`⚠️ Unrecognized development type: "${developmentType}" - defaulting to show all requirements`);
  }

  // Signal 1: Category-based defaults (70% confidence)
  const excludedCategories = CATEGORY_EXCLUSIONS[devTypeCategory] || [];
  if (excludedCategories.includes(requirement.category.toLowerCase())) {
    signals.push({
      applies: false,
      confidence: 0.7,
      source: `category_exclusion_${devTypeCategory}`,
    });
  }

  // Signal 2: Explicit text mentions (90% confidence)
  const verbatimText = requirement.verbatim_source_text || requirement.requirement_text;

  if (devTypeCategory === 'residential') {
    for (const pattern of EXPLICIT_RESIDENTIAL_PATTERNS) {
      if (pattern.test(verbatimText)) {
        signals.push({
          applies: true,
          confidence: 0.9,
          source: 'explicit_residential_mention',
        });
        break;
      }
    }
  } else if (devTypeCategory === 'commercial') {
    for (const pattern of EXPLICIT_COMMERCIAL_PATTERNS) {
      if (pattern.test(verbatimText)) {
        signals.push({
          applies: true,
          confidence: 0.9,
          source: 'explicit_commercial_mention',
        });
        break;
      }
    }
  } else if (devTypeCategory === 'industrial') {
    for (const pattern of EXPLICIT_INDUSTRIAL_PATTERNS) {
      if (pattern.test(verbatimText)) {
        signals.push({
          applies: true,
          confidence: 0.9,
          source: 'explicit_industrial_mention',
        });
        break;
      }
    }
  } else if (devTypeCategory === 'childcare') {
    for (const pattern of EXPLICIT_CHILDCARE_PATTERNS) {
      if (pattern.test(verbatimText)) {
        signals.push({
          applies: true,
          confidence: 0.9,
          source: 'explicit_childcare_mention',
        });
        break;
      }
    }
  } else if (devTypeCategory === 'mixed_use') {
    for (const pattern of EXPLICIT_MIXED_USE_PATTERNS) {
      if (pattern.test(verbatimText)) {
        signals.push({
          applies: true,
          confidence: 0.9,
          source: 'explicit_mixed_use_mention',
        });
        break;
      }
    }
  }

  // Signal 3: Section name analysis (60% confidence)
  const sectionText = [
    requirement.part_name,
    requirement.section_header,
    requirement.subcategory,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (devTypeCategory === 'residential') {
    for (const hint of SECTION_NAME_RESIDENTIAL_HINTS) {
      if (hint.test(sectionText)) {
        signals.push({
          applies: true,
          confidence: 0.6,
          source: 'section_name_residential_hint',
        });
        break;
      }
    }
  } else if (devTypeCategory === 'commercial') {
    for (const hint of SECTION_NAME_COMMERCIAL_HINTS) {
      if (hint.test(sectionText)) {
        signals.push({
          applies: true,
          confidence: 0.6,
          source: 'section_name_commercial_hint',
        });
        break;
      }
    }
  } else if (devTypeCategory === 'industrial') {
    for (const hint of SECTION_NAME_INDUSTRIAL_HINTS) {
      if (hint.test(sectionText)) {
        signals.push({
          applies: true,
          confidence: 0.6,
          source: 'section_name_industrial_hint',
        });
        break;
      }
    }
  } else if (devTypeCategory === 'childcare') {
    for (const hint of SECTION_NAME_CHILDCARE_HINTS) {
      if (hint.test(sectionText)) {
        signals.push({
          applies: true,
          confidence: 0.6,
          source: 'section_name_childcare_hint',
        });
        break;
      }
    }
  } else if (devTypeCategory === 'mixed_use') {
    for (const hint of SECTION_NAME_MIXED_USE_HINTS) {
      if (hint.test(sectionText)) {
        signals.push({
          applies: true,
          confidence: 0.6,
          source: 'section_name_mixed_use_hint',
        });
        break;
      }
    }
  }

  // Signal 4: Keyword density (50% confidence)
  const allText = `${verbatimText} ${sectionText}`.toLowerCase();
  let keywordCount = 0;
  let targetKeywords: string[] = [];

  if (devTypeCategory === 'residential') {
    targetKeywords = RESIDENTIAL_KEYWORDS;
  } else if (devTypeCategory === 'commercial') {
    targetKeywords = COMMERCIAL_KEYWORDS;
  } else if (devTypeCategory === 'industrial') {
    targetKeywords = INDUSTRIAL_KEYWORDS;
  } else if (devTypeCategory === 'childcare') {
    targetKeywords = CHILDCARE_KEYWORDS;
  } else if (devTypeCategory === 'mixed_use') {
    targetKeywords = MIXED_USE_KEYWORDS;
  }

  for (const keyword of targetKeywords) {
    if (allText.includes(keyword)) {
      keywordCount++;
    }
  }

  if (keywordCount >= 2) {
    signals.push({
      applies: true,
      confidence: 0.5,
      source: 'keyword_density',
    });
  }

  // ============================================================================
  // Confidence Aggregation
  // ============================================================================

  // Default: SHOW (conservative - no false negatives)
  if (signals.length === 0) {
    return true;
  }

  // If any high-confidence signal says "exclude", exclude
  for (const signal of signals) {
    if (!signal.applies && signal.confidence >= 0.7) {
      return false;
    }
  }

  // If any high-confidence signal says "include", include
  for (const signal of signals) {
    if (signal.applies && signal.confidence >= 0.9) {
      return true;
    }
  }

  // Weighted average of all signals
  const totalConfidence = signals.reduce((sum, s) => sum + s.confidence, 0);
  const weightedApplies = signals.reduce(
    (sum, s) => sum + (s.applies ? s.confidence : 0),
    0
  );

  return weightedApplies / totalConfidence > 0.5;
}

/**
 * Filter DCP requirements by development type using hybrid multi-signal approach
 *
 * @param requirements - Array of requirements to filter
 * @param developmentType - Target development type (e.g., 'dwelling_house', 'shop')
 * @returns Filtered array of requirements
 */
export function filterRequirementsByDevType<T extends FilterableRequirement>(
  requirements: T[],
  developmentType: string
): T[] {
  // Unknown dev type -> show all (conservative)
  if (!developmentType) {
    return requirements;
  }

  const devTypeLower = developmentType.toLowerCase();

  // Filter requirements
  const filtered = requirements.filter((req) =>
    calculateApplicability(req, devTypeLower)
  );

  const removedCount = requirements.length - filtered.length;
  const removalPercent = ((removedCount / requirements.length) * 100).toFixed(1);

  console.log(`[Dev Type Filter] ${developmentType}:`);
  console.log(`  Input: ${requirements.length} requirements`);
  console.log(`  Output: ${filtered.length} requirements`);
  console.log(`  Removed: ${removedCount} (${removalPercent}%)`);

  return filtered;
}
