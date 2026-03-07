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
