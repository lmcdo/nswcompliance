/**
 * Whether the road check actually established the corner status, and which DCP rows only
 * apply on a corner. A failed road query returns isCornerLot=false WITH an error: that is
 * "we could not tell", never "not a corner" (Winston Hills, 2026-10-19).
 */
import type { CornerLotResult } from './corner-lot-detection';

export type CornerStatus = 'corner' | 'not_corner' | 'unknown';

export function cornerStatus(cl: CornerLotResult | null | undefined): CornerStatus {
  if (!cl || cl.error || cl.confidence !== 1) return 'unknown';
  return cl.isCornerLot ? 'corner' : 'not_corner';
}

/** Plain-words sentence for the property summary. */
export function cornerSentence(status: CornerStatus): string {
  if (status === 'corner') return 'This lot is on a corner (it faces two roads).';
  if (status === 'not_corner') return 'This lot is not on a corner (it faces one road).';
  return "We couldn't reach the NSW road map, so we can't tell yet whether this lot is on a corner.";
}

const CORNER_ROW = /corner|secondary (street|road|frontage)/i;

/** A DCP row that applies only to corner lots, by its control type or its own condition text. */
export function isCornerOnlyRow(row: { control_type?: string | null; condition?: string | null }): boolean {
  return row.control_type === 'secondary_street_setback' || CORNER_ROW.test(row.condition ?? '');
}

/** Text shown on such a row when the road check found this lot is not on a corner. */
export const NOT_CORNER_ROW_NOTE = 'Applies only to corner lots — this lot is not on a corner.';
