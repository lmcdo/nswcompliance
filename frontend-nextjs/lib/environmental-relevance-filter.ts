/**
 * Environmental Controls Relevance Filter
 *
 * Filters NSW Planning API environmental controls based on development type
 * and property characteristics to hide truly irrelevant controls while keeping
 * informational/edge case controls visible with appropriate context.
 *
 * Conservative approach: When in doubt, show the control.
 */

export interface EnvironmentalControl {
  Type?: string;
  Class?: string;
  'EPI Name'?: string;
  'Map Type'?: string;
  title?: string;
  [key: string]: any;
}

export interface FilterContext {
  developmentType: string;
  zone: string;
  isResidential: boolean;
  isCommercial: boolean;
  isIndustrial: boolean;
  isMixedUse: boolean;
}

export interface FilterResult {
  isRelevant: boolean;
  requiresAction: boolean;
  reason?: string;
  category?: 'basix' | 'environmental_overlay' | 'informational' | 'prohibition';
}

/**
 * Assess whether an environmental control is relevant to the property
 * and whether it requires action or is informational only
 */
export function assessControlRelevance(
  control: EnvironmentalControl,
  context: FilterContext
): FilterResult {
  const type = (control.Type || '').toLowerCase();
  const classValue = control.Class || '';
  const epiName = (control['EPI Name'] || '').toLowerCase();
  const title = (control.title || '').toLowerCase();

  // =============================================================================
  // BASIX - ALWAYS SHOW FOR RESIDENTIAL ZONES (based on zone, not dev type)
  // =============================================================================
  if (epiName.includes('sustainable buildings') && epiName.includes('2022')) {
    // BASIX requirements apply to:
    // - New residential dwellings
    // - Alterations > $50k to residential
    // - Mixed-use developments with residential component
    //
    // Show based on ZONE (R1-R5, B4 mixed use) rather than dev type dropdown
    // This ensures SEPP provisions display without requiring user interaction

    // Only hide for pure commercial/industrial zones
    if (context.isIndustrial) {
      return {
        isRelevant: false,
        requiresAction: false,
        reason: 'BASIX not applicable to industrial zones'
      };
    }

    // Show for residential, mixed-use, OR when zone detection is ambiguous
    // Conservative approach: show BASIX unless clearly industrial
    return {
      isRelevant: true,
      requiresAction: true,
      category: 'basix',
      reason: context.isResidential
        ? 'BASIX certificate required for new dwellings or alterations over $50,000'
        : 'BASIX may apply - check if development includes residential component'
    };
  }

  // =============================================================================
  // THERMAL ENERGY FROM WASTE - ONLY RELEVANT FOR INDUSTRIAL
  // =============================================================================
  if ((type.includes('thermal') && type.includes('waste')) ||
      (type.includes('thermal energy from waste')) ||
      (title.includes('thermal energy from waste'))) {

    if (context.isIndustrial) {
      return {
        isRelevant: true,
        requiresAction: true,
        category: 'prohibition',
        reason: 'Thermal energy from waste facilities prohibited in Greater Sydney'
      };
    }

    // NOT relevant for residential/commercial properties
    return {
      isRelevant: false,
      requiresAction: false,
      reason: 'Only applicable to industrial waste facility development'
    };
  }

  // =============================================================================
  // ACID SULFATE SOILS - RISK-BASED RELEVANCE
  // =============================================================================
  if (type.includes('acid sulfate') ||
      type.includes('ass') ||
      title.includes('acid sulfate')) {

    // Class 5 = Lowest risk, no management plan required
    if (classValue === 'Class 5' || classValue === '5') {
      return {
        isRelevant: true,
        requiresAction: false,
        category: 'informational',
        reason: 'Class 5 is lowest risk - no acid sulfate soil management plan required'
      };
    }

    // Class 1-4 = Management plan required
    if (classValue.match(/Class [1-4]|^[1-4]$/)) {
      return {
        isRelevant: true,
        requiresAction: true,
        category: 'environmental_overlay',
        reason: `${classValue} requires acid sulfate soil management plan before works below 1m depth`
      };
    }

    // Unknown class - show as precautionary measure
    return {
      isRelevant: true,
      requiresAction: true,
      category: 'environmental_overlay',
      reason: 'Acid sulfate soil assessment may be required - check with council'
    };
  }

  // =============================================================================
  // TREE CANOPY COVERAGE - INFORMATIONAL ONLY
  // =============================================================================
  if (type.includes('tree canopy') ||
      type.includes('canopy cover') ||
      title.includes('tree canopy')) {

    return {
      isRelevant: true,
      requiresAction: false,
      category: 'informational',
      reason: 'Reference data for tree preservation and vegetation management requirements'
    };
  }

  // =============================================================================
  // CONTAMINATED LAND - RISK-BASED RELEVANCE
  // =============================================================================
  if (type.includes('contaminated') ||
      type.includes('contamination') ||
      title.includes('contamination')) {

    // Class 5 or "Investigation Not Required" = No action needed
    if (classValue === 'Class 5' ||
        classValue.toLowerCase().includes('not required') ||
        classValue.toLowerCase().includes('nil')) {
      return {
        isRelevant: true,
        requiresAction: false,
        category: 'informational',
        reason: 'No contamination investigation required'
      };
    }

    // Any other classification requires action
    return {
      isRelevant: true,
      requiresAction: true,
      category: 'environmental_overlay',
      reason: 'Contamination assessment required before development'
    };
  }

  // =============================================================================
  // FLOOD/BUSHFIRE - ALWAYS RELEVANT (SHOWS CLEARANCE/CONSTRAINT)
  // =============================================================================
  if (type.includes('flood') ||
      type.includes('bushfire') ||
      type.includes('fire prone') ||
      title.includes('flood') ||
      title.includes('bushfire')) {

    return {
      isRelevant: true,
      requiresAction: true,
      category: 'environmental_overlay',
      reason: 'Flood/bushfire controls apply - additional requirements may be triggered'
    };
  }

  // =============================================================================
  // ABORIGINAL LAND COUNCIL - INFORMATIONAL
  // =============================================================================
  if (type.includes('aboriginal') ||
      title.includes('aboriginal land council')) {

    return {
      isRelevant: true,
      requiresAction: false,
      category: 'informational',
      reason: 'Aboriginal Land Council notification area - informational only'
    };
  }

  // =============================================================================
  // REGIONAL PLAN BOUNDARY - INFORMATIONAL
  // =============================================================================
  if (type.includes('regional plan') ||
      title.includes('regional plan boundary')) {

    return {
      isRelevant: false,
      requiresAction: false,
      reason: 'Regional plan boundary is administrative only - no direct development impact'
    };
  }

  // =============================================================================
  // DEFAULT: SHOW CONTROL (CONSERVATIVE APPROACH)
  // =============================================================================
  // If we don't recognize the control type, show it to avoid hiding
  // potentially important constraints
  return {
    isRelevant: true,
    requiresAction: true,
    category: 'environmental_overlay',
    reason: undefined
  };
}

/**
 * Create filter context from property data
 */
export function createFilterContext(
  developmentType: string,
  zone: string
): FilterContext {
  const zoneUpper = zone.toUpperCase();

  // Determine property use type from zone
  const isResidential = ['R1', 'R2', 'R3', 'R4', 'R5'].some(z => zoneUpper.startsWith(z));
  const isCommercial = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8'].some(z => zoneUpper.startsWith(z));
  const isIndustrial = ['IN1', 'IN2', 'IN3', 'IN4'].some(z => zoneUpper.startsWith(z));

  // Mixed use zones include B4, B8, and shop_top_housing development types
  const isMixedUse =
    ['B4', 'B8'].some(z => zoneUpper.startsWith(z)) ||
    developmentType.includes('shop_top') ||
    developmentType.includes('mixed');

  return {
    developmentType,
    zone,
    isResidential,
    isCommercial,
    isIndustrial,
    isMixedUse
  };
}

/**
 * Filter a list of environmental controls
 * Returns only relevant controls
 */
export function filterEnvironmentalControls(
  controls: EnvironmentalControl[],
  context: FilterContext
): Array<EnvironmentalControl & FilterResult> {
  return controls
    .map(control => {
      const result = assessControlRelevance(control, context);
      return {
        ...control,
        ...result
      };
    })
    .filter(control => control.isRelevant);
}

/**
 * Group filtered controls by action requirement
 */
export function groupControlsByAction(
  controls: Array<EnvironmentalControl & FilterResult>
) {
  const actionRequired = controls.filter(c => c.requiresAction);
  const informational = controls.filter(c => !c.requiresAction);

  return {
    actionRequired,
    informational,
    total: controls.length,
    actionCount: actionRequired.length,
    infoCount: informational.length
  };
}
