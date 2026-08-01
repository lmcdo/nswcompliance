// Pure helper functions for the SEE PDF document.
// No state, no React hooks, no side effects — safe to unit-test directly.

import { SectionAssessment } from '@/lib/see/types';
import { HOUSING_SEPP_ZONES } from '@/lib/regulatory-constants';

// ---------------------------------------------------------------------------
// String helpers
// ---------------------------------------------------------------------------

export function capitalizeFirst(str: string): string {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/** Returns true if value looks like a bare number (not already including a unit label) */
export function isNumeric(value: string | number | undefined): boolean {
  if (value === undefined || value === null) return false;
  return /^\d+(\.\d+)?$/.test(String(value).trim());
}

// ---------------------------------------------------------------------------
// PDF text helpers
// ---------------------------------------------------------------------------

export const PDF_NARRATIVE_MAX = 600;

/** Truncate text for PDF table cells to prevent cell overflow in react-pdf. */
export function truncateForPdf(text: string | null, max: number = PDF_NARRATIVE_MAX): string {
  if (!text) return '';
  return text.length > max ? text.substring(0, max) + '…' : text;
}

// ---------------------------------------------------------------------------
// Section-level model helpers
// ---------------------------------------------------------------------------

export function sectionStatusMeta(status: SectionAssessment['status']): { label: string; color: string } {
  switch (status) {
    case 'complies':       return { label: 'Complies',  color: '#15803d' };
    case 'varies':         return { label: 'Varies',    color: '#d97706' };
    case 'not_applicable': return { label: 'N/A',       color: '#6b7280' };
    case 'flagged':        return { label: 'Flagged',   color: '#dc2626' };
    default:               return { label: '—',         color: '#9ca3af' };
  }
}

// ---------------------------------------------------------------------------
// Development pathway determination
// ---------------------------------------------------------------------------

/**
 * Determines development pathway from property data.
 * Zone codes come from property.zone — never hardcoded comparisons beyond the SEPP schedule.
 */
export function determineDevelopmentPathway(
  zone: string,
  heritage_in_hca: boolean,
  heritage_item: boolean
): { pathway: string; reason: string } {
  if (heritage_item) {
    return {
      pathway: 'Development Application (DA)',
      reason: 'Heritage item — CDC and exempt development not permitted',
    };
  }
  if (heritage_in_hca) {
    return {
      pathway: 'Development Application (DA)',
      reason: 'Heritage conservation area — CDC and exempt development restricted',
    };
  }
  const zoneCode = zone.split(' ')[0];
  if (HOUSING_SEPP_ZONES.includes(zoneCode)) {
    return {
      pathway: 'Complying Development (CDC)',
      reason: `${zoneCode} zone — Housing SEPP 2021 CDC pathway available for eligible development`,
    };
  }
  return {
    pathway: 'Development Application (DA)',
    reason: `${zoneCode} zone — check exempt development criteria`,
  };
}
