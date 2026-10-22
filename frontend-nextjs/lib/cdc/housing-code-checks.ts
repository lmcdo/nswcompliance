/**
 * CDC calculator checks. Every required figure comes from
 * select() in housing-code-standards.ts (stored rows). A check with no
 * selectable stored standard is "not_checked": no number, no pass, no fail.
 *
 * prior-art-checked: extends the new housing-code-standards module; no other evaluator exists.
 */

import { select, type ParsedRow, type SelectContext, type Selection } from './housing-code-standards';

export type CheckStatus = 'pass' | 'fail' | 'not_checked';

export type CdcDevelopmentType = 'new_dwelling' | 'alteration' | 'addition' | 'secondary_dwelling';

export type CheckKey =
  | 'front' | 'sideLeft' | 'sideRight' | 'rear'
  | 'siteCoverage' | 'landscapedArea' | 'buildingHeight' | 'storeys' | 'parking';

/** All numeric inputs are optional: blank means "not entered", never zero. */
export interface CdcCheckInput {
  developmentType?: CdcDevelopmentType | null;
  lotAreaM2?: number | null;
  /** Lot width AT THE BUILDING LINE (the stored bands use this, not the shorter side). */
  lotWidthM?: number | null;
  setbacks?: {
    front?: number | null;
    sideLeft?: number | null;
    sideRight?: number | null;
    rear?: number | null;
  } | null;
  hasUpperFloorHabitableRooms?: boolean | null;
  siteCoveragePercent?: number | null;
  landscapedAreaPercent?: number | null;
  buildingHeightMeters?: number | null;
  storeys?: number | null;
  parkingSpaces?: number | null;
}

export interface CdcCheck {
  key: CheckKey;
  label: string;
  status: CheckStatus;
  comparison: 'min' | 'max';
  unit: string;
  proposed: number | null;
  /** null unless a stored standard was selected. */
  required: number | null;
  /** positive = room to spare; null when not checked. */
  margin: number | null;
  /** Stored clause(s), as stored. null when no standard was selected. */
  clause: string | null;
  /** Verbatim law text of the selected row. */
  quote: string | null;
  /** Why the check is "Not checked". */
  reason: string | null;
  /** Every clause stored for this kind of standard (for the reader to look up). */
  storedClauses: string[];
  /** Stored rows of this kind that were not modelled and might also apply. */
  unmodelledClauses: string[];
}

function finite(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

/** Structure tags for the proposal. Secondary dwellings (detached) are not modelled. */
function structuresFor(t: CdcDevelopmentType | null | undefined): string[] {
  if (t === 'new_dwelling') return ['dwelling_house_and_attached', 'new_dwelling_house_and_attached'];
  if (t === 'addition' || t === 'alteration') return ['dwelling_house_and_attached'];
  return [];
}

interface Spec {
  key: CheckKey;
  label: string;
  comparison: 'min' | 'max';
  unit: string;
  proposed: number | null;
  /** standard_type to look up, or null = the table holds no such standard. */
  standardType: string | null;
  ctx: SelectContext;
  /** Set when the stored bands cannot be applied to what was entered. */
  blockedReason?: string;
}

function evaluate(parsed: ParsedRow[], spec: Spec): CdcCheck {
  const base = {
    key: spec.key, label: spec.label, comparison: spec.comparison, unit: spec.unit,
    proposed: spec.proposed, required: null, margin: null, clause: null, quote: null,
    storedClauses: [] as string[], unmodelledClauses: [] as string[],
  };
  const notChecked = (reason: string, sel?: Selection): CdcCheck => ({
    ...base, status: 'not_checked', reason,
    storedClauses: sel && !sel.ok ? sel.storedClauses : [],
  });

  if (spec.standardType == null) return notChecked('Not checked: no stored standard');
  if (spec.proposed == null) return notChecked('Not checked: no value entered');
  if (spec.blockedReason) {
    const sel = select(parsed, spec.standardType, {});
    return notChecked(`Not checked: ${spec.blockedReason}`, sel);
  }
  const sel = select(parsed, spec.standardType, spec.ctx);
  if (!sel.ok) return notChecked(`Not checked: ${sel.reason}`, sel);

  const required = sel.value;
  const pass = spec.comparison === 'min' ? spec.proposed >= required : spec.proposed <= required;
  const diff = spec.comparison === 'min' ? spec.proposed - required : required - spec.proposed;
  return {
    ...base,
    status: pass ? 'pass' : 'fail',
    required,
    margin: Math.round(diff * 100) / 100,
    clause: sel.clause,
    quote: sel.quote,
    reason: null,
    storedClauses: sel.clauses,
    unmodelledClauses: sel.unmodelledClauses,
  };
}

/** Run every calculator check against the parsed stored rows. */
export function evaluateCdcChecks(
  input: CdcCheckInput,
  parsed: ParsedRow[],
  unavailableReason?: string | null
): CdcCheck[] {
  const sb = input.setbacks ?? {};
  const lotAreaM2 = finite(input.lotAreaM2);
  const lotWidthM = finite(input.lotWidthM);
  const height = finite(input.buildingHeightMeters);
  const upper = input.hasUpperFloorHabitableRooms === true;
  const structures = structuresFor(input.developmentType);

  // Stored rear bands for an upper level are not modelled, and the entered
  // height does not say how tall the rear part is: do not apply a ground-level band.
  const rearBlocked = upper
    ? 'stored rear-setback bands for upper levels are not modelled'
    : undefined;

  const sideCtx: SelectContext = { lotWidthM, buildingHeightM: height };
  const rearCtx: SelectContext = { lotAreaM2, buildingHeightM: height };

  const specs: Spec[] = [
    { key: 'front', label: 'Front setback', comparison: 'min', unit: 'm', proposed: finite(sb.front),
      standardType: 'min_front_setback_m', ctx: { lotAreaM2 } },
    { key: 'sideLeft', label: 'Side setback (left)', comparison: 'min', unit: 'm', proposed: finite(sb.sideLeft),
      standardType: 'min_side_setback_m', ctx: sideCtx },
    { key: 'sideRight', label: 'Side setback (right)', comparison: 'min', unit: 'm', proposed: finite(sb.sideRight),
      standardType: 'min_side_setback_m', ctx: sideCtx },
    { key: 'rear', label: 'Rear setback', comparison: 'min', unit: 'm', proposed: finite(sb.rear),
      standardType: 'min_rear_setback_m', ctx: rearCtx, blockedReason: rearBlocked },
    { key: 'siteCoverage', label: 'Site coverage', comparison: 'max', unit: '%',
      proposed: finite(input.siteCoveragePercent), standardType: null, ctx: {} },
    { key: 'landscapedArea', label: 'Landscaped area', comparison: 'min', unit: '%',
      proposed: finite(input.landscapedAreaPercent), standardType: 'min_landscaped_area_pct',
      ctx: { lotAreaM2, structures } },
    { key: 'buildingHeight', label: 'Building height', comparison: 'max', unit: 'm', proposed: height,
      standardType: 'max_height_m', ctx: { structures } },
    { key: 'storeys', label: 'Storeys', comparison: 'max', unit: '', proposed: finite(input.storeys),
      standardType: 'max_storeys', ctx: { structures } },
    { key: 'parking', label: 'Car parking spaces', comparison: 'min', unit: '',
      proposed: finite(input.parkingSpaces), standardType: 'min_car_parking_spaces',
      ctx: { lotWidthM } },
  ];
  if (unavailableReason) {
    return specs.map((s) => ({
      ...evaluate([], s),
      status: 'not_checked' as const,
      reason: `Not checked: ${unavailableReason}`,
    }));
  }
  return specs.map((s) => evaluate(parsed, s));
}

export interface CdcCheckSummary {
  total: number;
  pass: number;
  fail: number;
  notChecked: number;
  /** true only when every check was decided and passed. */
  allPass: boolean;
}

export function summariseChecks(checks: CdcCheck[]): CdcCheckSummary {
  const pass = checks.filter((c) => c.status === 'pass').length;
  const fail = checks.filter((c) => c.status === 'fail').length;
  const notChecked = checks.filter((c) => c.status === 'not_checked').length;
  return { total: checks.length, pass, fail, notChecked, allPass: checks.length > 0 && pass === checks.length };
}

/** Plain-text clause label: stored clause with the instrument name. */
export function clauseLabel(clause: string | null): string | null {
  if (!clause) return null;
  return clause.startsWith('Codes SEPP') ? clause : `Codes SEPP 2008, ${clause}`;
}
