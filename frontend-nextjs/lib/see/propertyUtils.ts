/**
 * Pure utility functions for property constraint interpretation.
 * All functions are deterministic and have no side effects.
 */

/** Compute maximum GFA from an FSR ratio and lot area. */
export function calculateGFA(fsr: number, lotArea: number): number {
  return Math.round(fsr * lotArea);
}

export interface AnefStatusConfig {
  label: string;
  badgeClass: string;
  iconColor: string;
}

/** Display config for an ANEF building acceptability status value. */
export function anefStatusConfig(
  status: 'acceptable' | 'conditional' | 'unacceptable'
): AnefStatusConfig {
  switch (status) {
    case 'acceptable':
      return {
        label: 'Acceptable',
        badgeClass: 'bg-green-100 text-green-800 border border-green-200',
        iconColor: 'text-green-600',
      };
    case 'conditional':
      return {
        label: 'Conditional',
        badgeClass: 'bg-amber-100 text-amber-800 border border-amber-200',
        iconColor: 'text-amber-600',
      };
    case 'unacceptable':
      return {
        label: 'Unacceptable',
        badgeClass: 'bg-red-100 text-red-800 border border-red-200',
        iconColor: 'text-red-600',
      };
  }
}

/** Plain-English annotation for a flood blockType string. */
export function floodBlockTypeAnnotation(blockType: string): string {
  const t = blockType.toLowerCase();
  if (t.includes('floodway')) {
    return 'Floodway — high flood risk; development is restricted; evacuation assessment required.';
  }
  if (t.includes('flood planning')) {
    return 'Flood Planning Area — comply with floor level, materials, and evacuation route requirements.';
  }
  return 'Flood prone land — flood risk assessment required.';
}

export interface BushfireCategoryAnnotation {
  annotation: string;
  cdcBlocked: boolean;
}

/** Plain-English annotation for a bushfire category string. */
export function bushfireCategoryAnnotation(category: string): BushfireCategoryAnnotation {
  const c = category.toLowerCase();
  if (c.includes('flame zone') || c.includes('inner protection')) {
    return {
      annotation: 'Flame Zone — CDC not available; BAL report required; RFS consultation likely required (integrated development).',
      cdcBlocked: true,
    };
  }
  if (c.includes('asset protection')) {
    return {
      annotation: 'Asset Protection Zone — BAL assessment required; construction standards apply.',
      cdcBlocked: false,
    };
  }
  if (c.includes('vegetation buffer')) {
    return {
      annotation: 'Vegetation Buffer — BAL assessment may be required; moderate construction requirements.',
      cdcBlocked: false,
    };
  }
  return {
    annotation: 'Bushfire prone land — bushfire assessment required (Planning for Bush Fire Protection 2019).',
    cdcBlocked: false,
  };
}

// ── X2: ANEF building acceptability derivation ───────────────────────────────

export interface AnefBuildingAcceptabilityRow {
  buildingType: string;
  displayName: string;
  status: 'acceptable' | 'conditional' | 'unacceptable';
}

/**
 * Derive ANEF building acceptability from ANEF level using AS 2021-2015 Table 2.1.
 * Returns null if level is null (not in ANEF zone).
 *
 * Thresholds (AS 2021-2015):
 *   Residential, Hotels:  <25 acceptable, 25-29 conditional, >=30 unacceptable
 *   Schools:              <25 acceptable, >=25 unacceptable
 *   Hospitals:            <20 acceptable, 20-24 conditional, >=25 unacceptable
 *   Commercial:           <30 acceptable, >=30 conditional
 */
export function deriveAnefBuildingAcceptability(
  anefLevel: number | null
): AnefBuildingAcceptabilityRow[] | null {
  if (anefLevel === null || anefLevel === undefined) return null;

  const status = (
    acceptable: boolean,
    conditional: boolean
  ): 'acceptable' | 'conditional' | 'unacceptable' =>
    acceptable ? 'acceptable' : conditional ? 'conditional' : 'unacceptable';

  return [
    {
      buildingType: 'residential',
      displayName: 'Residential Dwellings',
      status: status(anefLevel < 25, anefLevel < 30),
    },
    {
      buildingType: 'aged_care',
      displayName: 'Aged Care / Retirement',
      status: status(anefLevel < 25, anefLevel < 30),
    },
    {
      buildingType: 'school',
      displayName: 'Schools',
      status: status(anefLevel < 25, false),
    },
    {
      buildingType: 'hospital',
      displayName: 'Hospitals',
      status: status(anefLevel < 20, anefLevel < 25),
    },
    {
      buildingType: 'hotel',
      displayName: 'Hotels / Motels',
      status: status(anefLevel < 25, anefLevel < 30),
    },
    {
      buildingType: 'commercial',
      displayName: 'Commercial / Retail',
      status: status(anefLevel < 30, true),
    },
  ];
}

// ── X4: LMR frontage check ────────────────────────────────────────────────────

/** SEPP Housing 2021 minimum frontage for LMR development types. */
export const LMR_FRONTAGE_MINIMUMS = {
  dual_occupancy: { minM: 12, label: 'Dual Occupancy' },
  manor_house: { minM: 12, label: 'Manor House' },
  multi_dwelling: { minM: 15, label: 'Multi Dwelling Housing' },
} as const;

export interface LmrFrontageStatus {
  /** Development types excluded by this frontage */
  excluded: Array<{ devType: string; label: string; minimumM: number }>;
  /** Development types that meet the frontage requirement */
  eligible: Array<{ devType: string; label: string; minimumM: number }>;
}

/**
 * Check which LMR development types are excluded by the lot frontage.
 * Returns lists of excluded and eligible types.
 */
export function lmrFrontageStatus(frontageM: number): LmrFrontageStatus {
  const excluded: LmrFrontageStatus['excluded'] = [];
  const eligible: LmrFrontageStatus['eligible'] = [];
  for (const [devType, { minM, label }] of Object.entries(LMR_FRONTAGE_MINIMUMS)) {
    if (frontageM < minM) {
      excluded.push({ devType, label, minimumM: minM });
    } else {
      eligible.push({ devType, label, minimumM: minM });
    }
  }
  return { excluded, eligible };
}

// ── X7: Road classification alert ────────────────────────────────────────────

export interface RoadImpactInfo {
  /** True when road hierarchy warrants a planning alert */
  isHighImpact: boolean;
  /** Plain-English annotation for planner */
  annotation: string;
}

/**
 * Return impact info for a road functional_hierarchy string.
 * High impact = Motorway, Primary Road, Arterial Road.
 * When distanceMeters is provided and > 5, uses proximity language instead of "frontage".
 */
export function roadHierarchyAnnotation(hierarchy: string, distanceMeters?: number): RoadImpactInfo {
  const h = hierarchy.toLowerCase();
  const isFrontage = distanceMeters === undefined || distanceMeters <= 5;
  const dist = distanceMeters !== undefined ? Math.round(distanceMeters) : null;

  if (h.includes('motorway')) {
    return {
      isHighImpact: true,
      annotation: isFrontage
        ? 'Motorway frontage — TfNSW consultation required; restricted driveway access; traffic noise assessment required.'
        : `Within ${dist}m of a Motorway — TfNSW consultation likely required; traffic noise assessment required.`,
    };
  }
  if (h.includes('primary')) {
    return {
      isHighImpact: true,
      annotation: isFrontage
        ? 'Primary Road frontage — TfNSW consultation likely required; traffic noise assessment required.'
        : `Within ${dist}m of a Primary Road — TfNSW consultation likely required; traffic noise assessment required.`,
    };
  }
  if (h.includes('arterial')) {
    return {
      isHighImpact: true,
      annotation: isFrontage
        ? 'Arterial Road frontage — traffic noise assessment likely required; access restrictions may apply.'
        : `Within ${dist}m of an Arterial Road — traffic noise assessment likely required.`,
    };
  }
  return { isHighImpact: false, annotation: '' };
}
