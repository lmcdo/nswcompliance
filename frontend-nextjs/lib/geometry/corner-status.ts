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

// "non-corner lots" is not a corner row, but "excluding non-corner lots" is.
const CORNER_ROW =
  /(?<!non-)(?<!non )corner|\b(?:exclud(?:e|es|ing|ed)|except(?: for)?|other than)\s+(?:(?:the|a|an|any|all|those|that|lots?|allotments?|sites?|properties|land|on|of|which|are)\s+){0,3}?non[- ]corner|\bnot (?:applicable|apply|applying) (?:to|for)\s+(?:(?:the|a|an|any|all|those|that|lots?|allotments?|sites?|properties|land|on|of|which|are)\s+){0,3}?non[- ]corner|secondary (street|road|frontage)/i;
// "excluding corner lots" / "applies to non-corner lots" is a rule FOR non-corner lots (Sol, #1377).
// Same wording rules as services/constraint_arithmetic.py _EXCLUDES_CORNER. The excluded thing must be
// the corner lot itself (only words like "the", "all", "lots on" between), so "Other than garages, corner
// lots must..." stays corner-only (Sol, 2026-10-20).
const EXCLUDES_CORNER =
  /\b(?:exclud(?:e|es|ing|ed)|except(?: for)?|other than)\s+(?:(?:the|a|an|any|all|those|that|lots?|allotments?|sites?|properties|land|on|of|which|are)\s+){0,3}?(?<!non-)(?<!non )corner|\bnot (?:applicable|apply|applying) (?:to|for)\s+(?:(?:the|a|an|any|all|those|that|lots?|allotments?|sites?|properties|land|on|of|which|are)\s+){0,3}?(?<!non-)(?<!non )corner|(?<!not )\b(?:appl(?:y|ies|ying|icable)|only)\s+(?:to|for|on)\s+(?:all\s+)?non[- ]corner|^\s*(?:for|on)\s+(?:all\s+)?non[- ]corner/i;

/** A DCP row that applies only to corner lots, by its control type or its own condition text. */
export function isCornerOnlyRow(row: { control_type?: string | null; condition?: string | null }): boolean {
  const cond = row.condition ?? '';
  if (EXCLUDES_CORNER.test(cond)) return false;
  return row.control_type === 'secondary_street_setback' || CORNER_ROW.test(cond);
}

/** Text shown on such a row when the road check found this lot is not on a corner. */
export const NOT_CORNER_ROW_NOTE = 'Applies only to corner lots — this lot is not on a corner.';
