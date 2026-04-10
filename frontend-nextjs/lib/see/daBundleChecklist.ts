/**
 * DA Documentation Bundle Checklist
 *
 * Given property attributes and proposed development type, returns the
 * complete list of DA documents required, with status and trigger explanation.
 *
 * Status:
 *   required  — definitively required based on known site/dev conditions
 *   likely    — probably required; planner should confirm
 *   not_required — definitively not required based on known conditions
 *   unknown   — cannot determine without drawings or further information
 */

export type ChecklistStatus = 'required' | 'likely' | 'not_required' | 'unknown';

export interface ChecklistItem {
  document: string;
  description: string;
  status: ChecklistStatus;
  trigger: string;
  cost_range?: string;
  who?: string;
}

export interface DaBundleInputs {
  devType: string;
  zone?: string | null;
  /** True if site is a heritage item or in a HCA */
  isHeritage?: boolean;
  /** HCA name if applicable */
  hcaName?: string | null;
  /** Lot area in m² */
  lotArea?: number | null;
  /** From intake: flood_prone */
  floodProne?: 'yes' | 'no' | 'unknown';
  /** From intake: bushfire_prone */
  bushfireProne?: 'yes' | 'no' | 'unknown';
  /** From intake: contaminated_land */
  contaminatedLand?: 'yes' | 'no' | 'unknown';
  /** Proposed number of storeys (if known from works scope) */
  proposedStoreys?: number | null;
  /** Proposed number of dwellings (if multi-unit) */
  proposedDwellings?: number | null;
}

const RESIDENTIAL_DEV_TYPES = new Set([
  'dwelling_house', 'dual_occupancy', 'secondary_dwelling',
  'multi_dwelling_housing', 'residential_flat_building',
  'shop_top_housing', 'seniors_housing',
]);

const COMMERCIAL_DEV_TYPES = new Set([
  'commercial_premises', 'retail_premises', 'office_premises',
  'business_premises', 'food_and_drink_premises',
  'entertainment_facility', 'pub', 'hotel_or_motel_accommodation',
]);

function isResidential(devType: string): boolean {
  return RESIDENTIAL_DEV_TYPES.has(devType) ||
    devType.includes('dwelling') || devType.includes('residential');
}

function isCommercial(devType: string): boolean {
  return COMMERCIAL_DEV_TYPES.has(devType) ||
    devType.includes('commercial') || devType.includes('retail') ||
    devType.includes('office');
}

function isEntertainment(devType: string): boolean {
  return devType.includes('entertainment') || devType.includes('pub') ||
    devType.includes('food_and_drink') || devType.includes('hotel');
}

function isMultiUnit(devType: string, proposedDwellings?: number | null): boolean {
  return devType === 'multi_dwelling_housing' ||
    devType === 'residential_flat_building' ||
    devType === 'shop_top_housing' ||
    (proposedDwellings != null && proposedDwellings >= 4);
}

/**
 * Generate the DA bundle checklist for a given property and development type.
 */
export function getDaBundleChecklist(inputs: DaBundleInputs): ChecklistItem[] {
  const {
    devType,
    isHeritage = false,
    hcaName,
    lotArea,
    floodProne = 'unknown',
    bushfireProne = 'unknown',
    contaminatedLand = 'unknown',
    proposedStoreys,
    proposedDwellings,
  } = inputs;

  const residential = isResidential(devType);
  const commercial = isCommercial(devType);
  const entertainment = isEntertainment(devType);
  const multiUnit = isMultiUnit(devType, proposedDwellings);
  const tallBuilding = proposedStoreys != null ? proposedStoreys >= 3 : null;
  const largeSite = lotArea != null ? lotArea >= 500 : null;

  const items: ChecklistItem[] = [];

  // --- Always required ---

  items.push({
    document: 'Development Application Form',
    description: 'Completed DA lodgement form via NSW Planning Portal',
    status: 'required',
    trigger: 'All DAs',
  });

  items.push({
    document: 'Statement of Environmental Effects (SEE)',
    description: 'Demonstrates consideration of all applicable planning controls. Must address SEPP, LEP, and DCP provisions.',
    status: 'required',
    trigger: 'All DAs',
    cost_range: '$2,000–$8,000',
    who: 'Town planner',
  });

  items.push({
    document: 'Architectural drawings',
    description: 'Site plan, floor plans, elevations, sections drawn to scale',
    status: 'required',
    trigger: 'All DAs',
    cost_range: '$8,000–$20,000',
    who: 'Architect',
  });

  items.push({
    document: 'Survey plan',
    description: 'Registered surveyor plan showing lot boundaries, levels, and existing structures',
    status: 'required',
    trigger: 'All DAs',
    cost_range: '$1,000–$3,000',
    who: 'Licensed surveyor',
  });

  items.push({
    document: 'Waste management plan',
    description: 'Describes construction and operational waste management',
    status: 'required',
    trigger: 'All DAs',
    who: 'Planner (typically bundled with SEE)',
  });

  // --- BASIX ---
  if (residential) {
    items.push({
      document: 'BASIX Certificate',
      description: 'Building Sustainability Index certificate confirming thermal comfort, water, and energy targets',
      status: 'required',
      trigger: 'All residential development',
      cost_range: '$300',
      who: 'Any accredited assessor (eplanning.nsw.gov.au)',
    });
  }

  // --- Shadow diagrams ---
  if (residential) {
    items.push({
      document: 'Shadow diagrams',
      description: 'Shows shadows cast at 9am, 12pm, 3pm on 21 June. Required to demonstrate solar access compliance.',
      status: 'required',
      trigger: 'Any addition or new structure that may overshadow adjoining properties',
      who: 'Architect (typically bundled with drawings)',
    });
  }

  // --- Heritage Impact Statement ---
  if (isHeritage) {
    items.push({
      document: 'Heritage Impact Statement (HIS)',
      description: hcaName
        ? `Required for works affecting the ${hcaName} Heritage Conservation Area. Must follow NSW Heritage Office guidelines.`
        : 'Required for works affecting a heritage item or Heritage Conservation Area. Must follow NSW Heritage Office guidelines.',
      status: 'required',
      trigger: isHeritage ? 'Property is a heritage item or within a Heritage Conservation Area' : 'Heritage item or HCA',
      cost_range: '$2,000–$8,000',
      who: 'Planner or heritage consultant',
    });
  }

  // --- Stormwater/drainage report ---
  if (largeSite === true) {
    items.push({
      document: 'Stormwater management plan',
      description: 'Engineering design for on-site detention, drainage, and water quality',
      status: 'required',
      trigger: `Lot area ${lotArea?.toFixed(0)}m² — exceeds 500m² threshold`,
      cost_range: '$1,000–$3,000',
      who: 'Civil engineer',
    });
  } else if (largeSite === null) {
    items.push({
      document: 'Stormwater management plan',
      description: 'Engineering design for on-site detention, drainage, and water quality',
      status: 'likely',
      trigger: 'Site area >500m² or steep gradient — lot area not confirmed',
      cost_range: '$1,000–$3,000',
      who: 'Civil engineer',
    });
  }

  // --- Arborist report ---
  items.push({
    document: 'Arborist report',
    description: 'Assessment of trees >200mm DBH that may be affected by proposed works',
    status: 'likely',
    trigger: 'Required if any tree >200mm DBH is within or near the works area. Check site inspection.',
    cost_range: '$800–$2,000',
    who: 'Certified arborist',
  });

  // --- SEPP 65 design review ---
  if (multiUnit && (tallBuilding === true || tallBuilding === null)) {
    items.push({
      document: 'SEPP 65 Design Review Statement',
      description: 'Independent design review by an Architect (SEPP Housing / SEPP 65)',
      status: tallBuilding === true ? 'required' : 'likely',
      trigger: tallBuilding === true
        ? `Multi-unit residential, ${proposedStoreys} storeys — triggers SEPP 65 design review`
        : 'Multi-unit residential — required if 3+ storeys or 4+ dwellings (confirm with proposed design)',
      cost_range: '$2,000–$5,000',
      who: 'Architect with design review panel',
    });
  }

  // --- Clause 4.6 variation ---
  items.push({
    document: 'Clause 4.6 variation request',
    description: 'Justification for non-compliance with a development standard (height, FSR, setback). Legally structured document.',
    status: 'unknown',
    trigger: 'Required if any DCP or LEP development standard is exceeded — cannot determine without proposed measurements from drawings',
    cost_range: '$3,000–$10,000',
    who: 'Planner or planning solicitor',
  });

  // --- Contamination report ---
  if (contaminatedLand === 'yes') {
    items.push({
      document: 'Preliminary contamination investigation',
      description: 'Phase 1/Phase 2 site investigation for potentially contaminated land',
      status: 'required',
      trigger: 'EPA-notified contaminated site within 500m confirmed via portal mapping',
      cost_range: '$2,000–$8,000',
      who: 'Environmental consultant',
    });
  } else if (contaminatedLand === 'unknown') {
    items.push({
      document: 'Preliminary contamination investigation',
      description: 'Phase 1/Phase 2 site investigation for potentially contaminated land',
      status: 'likely',
      trigger: 'Contamination status unknown — check if former industrial use or EPA-notified site within 500m',
      cost_range: '$2,000–$8,000',
      who: 'Environmental consultant',
    });
  }

  // --- Flood report ---
  if (floodProne === 'yes') {
    items.push({
      document: 'Flood impact assessment',
      description: 'Hydraulic assessment of flood risk, floor levels, and evacuation',
      status: 'required',
      trigger: 'Site confirmed flood prone per LEP Part 5 mapping',
      cost_range: '$2,000–$5,000',
      who: 'Hydraulic engineer',
    });
  }

  // --- Bushfire report ---
  if (bushfireProne === 'yes') {
    items.push({
      document: 'Bushfire attack level (BAL) assessment',
      description: 'Determines bushfire attack level and applicable construction requirements',
      status: 'required',
      trigger: 'Site confirmed bushfire prone per LEP Part 5 mapping',
      cost_range: '$500–$1,500',
      who: 'Accredited bushfire consultant',
    });
  }

  // --- Traffic impact ---
  if (commercial) {
    items.push({
      document: 'Traffic impact assessment',
      description: 'Analysis of vehicle movements and parking demand',
      status: devType.includes('large') ? 'required' : 'likely',
      trigger: 'Commercial development — required if >50 vehicle movements/day or significant parking changes',
      cost_range: '$3,000–$8,000',
      who: 'Traffic engineer',
    });
  }

  // --- Acoustic report ---
  if (entertainment || devType.includes('pub') || devType.includes('music')) {
    items.push({
      document: 'Acoustic report',
      description: 'Noise impact assessment for entertainment or food/drink premises',
      status: 'required',
      trigger: 'Entertainment facility or food and drink premises with amplified sound',
      cost_range: '$2,000–$4,000',
      who: 'Acoustic engineer',
    });
  } else if (commercial) {
    items.push({
      document: 'Acoustic report',
      description: 'Noise impact assessment',
      status: 'likely',
      trigger: 'Commercial use — required if noise-generating activities proposed',
      cost_range: '$2,000–$4,000',
      who: 'Acoustic engineer',
    });
  }

  return items;
}

/** Count items by status */
export function summariseChecklist(items: ChecklistItem[]): Record<ChecklistStatus, number> {
  const counts: Record<ChecklistStatus, number> = {
    required: 0, likely: 0, not_required: 0, unknown: 0,
  };
  for (const item of items) counts[item.status]++;
  return counts;
}
