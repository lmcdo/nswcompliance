/**
 * Housing Code standards (SEPP Exempt and Complying Development Codes 2008, Part 3)
 * read from the table `cdc_eligibility_standards` (code_name = 'housing_code').
 *
 * prior-art-checked: no TS code reads cdc_eligibility_standards bands (grep of frontend-nextjs: only a comment in preliminary-check); the Python screen reads only the 4 unbanded rows; the housing-sepp files are a different instrument.
 *
 * PURE module (no database, no React) so the API routes and the browser share
 * one parser and one selector. The loader lives in housing-code-standards-db.ts.
 *
 * Rules:
 *  - NO planning figure is typed here. Every number comes from a stored row.
 *  - A row's `conditionality` is the BAND, as free text. A STRICT parser turns it
 *    into numeric ranges. Anything it cannot fully parse, or that carries a
 *    structure/context qualifier this module does not model, makes the row
 *    UNUSABLE for a verdict. Unusable rows are still listed (clause) so the
 *    reader sees what was not modelled.
 *  - select() returns a value only when exactly one distinct stored value
 *    matches. Zero matches or conflicting values return null plus a reason.
 *    Callers must show "Not checked" for null, never pass or fail.
 */

export type Dimension = 'lot_area' | 'lot_width' | 'building_height';

/** Raw row, as stored. numeric_value may arrive as a string from pg. */
export interface StandardRow {
  id: number;
  code_name?: string;
  standard_type: string;
  numeric_value: number | string | null;
  text_value?: string | null;
  applicable_zones?: string[] | null;
  conditionality: string | null;
  ref_number: string | null;
  source_quote: string | null;
  source_provision_ids?: unknown;
  /** pdf_page of the first source provision (loader fills it in). */
  pdf_page?: number | null;
  /** Set by publicRow(): ref_number named a structure (the label itself is not exposed). */
  ref_names_structure?: boolean;
  effective_date?: string | null;
  is_active?: boolean;
  manual_verified?: boolean | null;
  stale_since?: string | null;
}

export interface Range {
  dimension: Dimension;
  lower: number;
  /** true for ">" bands: the lower bound itself is NOT in the band. */
  lowerExclusive: boolean;
  /** inclusive; null = open ended (">1,500 m2"). */
  upper: number | null;
}

/**
 * Structure contexts that are modelled. Each is an EXACT stored band text that
 * names what the standard applies to. Anything else naming a structure is
 * unusable.
 */
const STRUCTURE_BANDS: Record<string, string> = {
  'dwelling house and any attached development': 'dwelling_house_and_attached',
  'new dwelling house and attached development': 'new_dwelling_house_and_attached',
};

export interface ParsedRow {
  row: StandardRow;
  numericValue: number | null;
  usable: boolean;
  /** Why the row cannot drive a verdict (null when usable). */
  unusableReason: string | null;
  ranges: Range[];
  /** Modelled structure tag, or null when the row is not structure-specific. */
  structure: string | null;
  /** Citation shown to users: the clause, else 'Codes SEPP 2008, page N', else null. */
  citation: string | null;
}

/** Text that means the stored row cannot be paired with its band: never a verdict. */
const NEVER_VERDICT = /not paired in storage|values only|value-only row|bands in row|bands in other rows|heading not stored|read the quote/i;

/** Context/structure qualifiers this module does not model. */
const UNMODELLED_QUALIFIER =
  /corner lot|battle-?axe|parallel road|classified road|\blane\b|studio|detached|garage|carport|\bdeck\b|patio|pergola|terrace|verandah|cabana|\bshed\b|rainwater|shade|secondary road|public reserve|basement|boundary wall|fewer than|if no setback|average of/i;

/** Words in a ref_number that name a structure the standard is specific to. */
const REF_STRUCTURE_LABEL =
  /detached|garage|carport|\bdeck\b|patio|pergola|terrace|verandah|cabana|\bshed\b|rainwater|shade|studio|\blane\b|corner|battle-?axe|parallel|classified|secondary/i;

const NUM = '([\\d,]+(?:\\.\\d+)?)';
const UNIT = '(m2|m)?';
const BETWEEN = new RegExp(`^(>)?\\s*${NUM}\\s*${UNIT}\\s*-\\s*${NUM}\\s*${UNIT}$`, 'i');
const ABOVE = new RegExp(`^>\\s*${NUM}\\s*${UNIT}$`, 'i');
const DIMENSION_PREFIX =
  /^(lot area|lot size|lot width at building line|building height)\s+(.+)$/i;

function toNumber(s: string): number | null {
  const n = Number(s.replace(/,/g, ''));
  return Number.isFinite(n) ? n : null;
}

function dimensionOf(prefix: string): Dimension {
  const p = prefix.toLowerCase();
  if (p === 'lot area' || p === 'lot size') return 'lot_area';
  if (p === 'lot width at building line') return 'lot_width';
  return 'building_height';
}

function unitOk(dimension: Dimension, unit: string | undefined): boolean {
  if (!unit) return true;
  const u = unit.toLowerCase();
  return dimension === 'lot_area' ? u === 'm2' : u === 'm';
}

type BandResult =
  | { ok: true; ranges: Range[]; structure: string | null }
  | { ok: false; reason: string };

/**
 * Strict band parser. Clauses are joined by ';'. Returns ok:false for anything
 * it cannot fully account for.
 */
export function parseBand(text: string | null | undefined): BandResult {
  const raw = (text ?? '').trim();
  if (raw === '') return { ok: true, ranges: [], structure: null };
  if (NEVER_VERDICT.test(raw)) {
    return { ok: false, reason: 'band is not stored paired with its value' };
  }
  const structure = STRUCTURE_BANDS[raw.toLowerCase()];
  if (structure) return { ok: true, ranges: [], structure };
  if (UNMODELLED_QUALIFIER.test(raw)) {
    return { ok: false, reason: 'band names a structure or context that is not modelled' };
  }
  const ranges: Range[] = [];
  const seen = new Set<Dimension>();
  for (const part of raw.split(';')) {
    const clause = part.trim();
    const dim = DIMENSION_PREFIX.exec(clause);
    if (!dim) return { ok: false, reason: `band text not understood: "${clause}"` };
    const dimension = dimensionOf(dim[1]);
    if (seen.has(dimension)) return { ok: false, reason: `band repeats ${dimension}` };
    seen.add(dimension);
    const rest = dim[2].trim();
    const between = BETWEEN.exec(rest);
    if (between) {
      const lower = toNumber(between[2]);
      const upper = toNumber(between[4]);
      if (lower == null || upper == null || upper < lower) {
        return { ok: false, reason: `band range not valid: "${clause}"` };
      }
      if (!unitOk(dimension, between[3]) || !unitOk(dimension, between[5])) {
        return { ok: false, reason: `band unit does not fit ${dimension}: "${clause}"` };
      }
      ranges.push({ dimension, lower, lowerExclusive: between[1] === '>', upper });
      continue;
    }
    const above = ABOVE.exec(rest);
    if (above) {
      const lower = toNumber(above[1]);
      if (lower == null || !unitOk(dimension, above[2])) {
        return { ok: false, reason: `band range not valid: "${clause}"` };
      }
      ranges.push({ dimension, lower, lowerExclusive: true, upper: null });
      continue;
    }
    return { ok: false, reason: `band text not understood: "${clause}"` };
  }
  return { ok: true, ranges, structure: null };
}

const CLEAN_CLAUSE = /^(?:cl\.?\s*)?\d+(?:\.\d+)+(?:\([^)]*\))*/i;

/**
 * The only citation text ever shown or returned: the clause part of ref_number
 * when it starts with a clause number, else the stored PDF page, else null.
 * Internal labels in ref_number are never passed through.
 */
export function citationOf(row: StandardRow): string | null {
  const m = CLEAN_CLAUSE.exec((row.ref_number ?? '').trim());
  if (m) return m[0].trim();
  const page = Number(row.pdf_page);
  if (row.pdf_page != null && row.pdf_page !== undefined && Number.isInteger(page) && page > 0) {
    return `Codes SEPP 2008, page ${page}`;
  }
  return null;
}

export function refNamesStructure(row: StandardRow): boolean {
  if (typeof row.ref_names_structure === 'boolean') return row.ref_names_structure;
  return REF_STRUCTURE_LABEL.test((row.ref_number ?? '').replace(CLEAN_CLAUSE, ''));
}

/**
 * Row as returned by our API: ref_number is only ever the citation clause (or
 * null), never an internal label. Parsing the public row gives the same result.
 */
export function publicRow(row: StandardRow): StandardRow {
  const m = CLEAN_CLAUSE.exec((row.ref_number ?? '').trim());
  return { ...row, ref_names_structure: refNamesStructure(row), ref_number: m ? m[0].trim() : null };
}

/** Parse one stored row and decide whether it may drive a verdict. */
export function parseRow(row: StandardRow): ParsedRow {
  const numericValue =
    row.numeric_value == null || row.numeric_value === undefined || row.numeric_value === ''
      ? null
      : Number(row.numeric_value);
  const base = { row, numericValue: Number.isFinite(numericValue as number) ? numericValue : null };
  const citation = citationOf(row);
  const fail = (reason: string): ParsedRow => ({
    ...base, usable: false, unusableReason: reason, ranges: [], structure: null, citation,
  });

  if (base.numericValue == null) return fail('no stored number (value depends on other facts)');
  if (row.applicable_zones && row.applicable_zones.length > 0) {
    return fail('standard is limited to zones that are not modelled');
  }
  if (citation == null) return fail('no clause or page stored');
  if (refNamesStructure(row)) {
    return fail('clause label names a structure that is not modelled');
  }
  const band = parseBand(row.conditionality);
  if (!band.ok) return fail(band.reason);
  return {
    ...base, usable: true, unusableReason: null, ranges: band.ranges, structure: band.structure, citation,
  };
}

export function parseRows(rows: StandardRow[]): ParsedRow[] {
  return rows.map(parseRow);
}

export interface SelectContext {
  lotAreaM2?: number | null;
  lotWidthM?: number | null;
  buildingHeightM?: number | null;
  /** Structure tags that describe the proposal (see STRUCTURE_BANDS). */
  structures?: string[];
}

function inRange(r: Range, v: number): boolean {
  const aboveLower = r.lowerExclusive ? v > r.lower : v >= r.lower;
  const belowUpper = r.upper == null ? true : v <= r.upper;
  return aboveLower && belowUpper;
}

function valueFor(ctx: SelectContext, d: Dimension): number | null {
  const v = d === 'lot_area' ? ctx.lotAreaM2 : d === 'lot_width' ? ctx.lotWidthM : ctx.buildingHeightM;
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

const DIM_LABEL: Record<Dimension, string> = {
  lot_area: 'lot area',
  lot_width: 'lot width at building line',
  building_height: 'building height',
};

export interface SelectedStandard {
  ok: true;
  standardType: string;
  value: number;
  /** ref_number of the matching row(s), as stored. */
  clause: string;
  clauses: string[];
  /** Verbatim law text of the matching row. */
  quote: string;
  band: string | null;
  rowIds: number[];
  /** Clauses of stored rows of this type that were NOT modelled (may also apply). */
  unmodelledClauses: string[];
}

export interface NoStandard {
  ok: false;
  standardType: string;
  reason: string;
  /** Every stored clause for this type, so the reader can look them up. */
  storedClauses: string[];
}

export type Selection = SelectedStandard | NoStandard;

function clausesOf(rows: ParsedRow[]): string[] {
  return Array.from(new Set(rows.map((p) => p.citation).filter((c): c is string => !!c)));
}

export function select(parsed: ParsedRow[], standardType: string, ctx: SelectContext = {}): Selection {
  const ofType = parsed.filter((p) => p.row.standard_type === standardType);
  const storedClauses = clausesOf(ofType);
  const none = (reason: string): NoStandard => ({ ok: false, standardType, reason, storedClauses });

  if (ofType.length === 0) return none('no stored standard');
  const usable = ofType.filter((p) => p.usable);
  const unusable = ofType.filter((p) => !p.usable);
  if (usable.length === 0) {
    if (ofType.every((p) => p.citation == null)) return none('no clause or page stored');
    return none('the stored standards for this item cannot be applied to a proposal without more facts');
  }

  const matches: ParsedRow[] = [];
  const missing = new Set<Dimension>();
  let structureMismatch = false;
  for (const p of usable) {
    let ok = true;
    for (const r of p.ranges) {
      const v = valueFor(ctx, r.dimension);
      if (v == null) { missing.add(r.dimension); ok = false; break; }
      if (!inRange(r, v)) { ok = false; break; }
    }
    if (ok && p.structure && !(ctx.structures ?? []).includes(p.structure)) {
      structureMismatch = true;
      ok = false;
    }
    if (ok) matches.push(p);
  }

  if (matches.length === 0) {
    if (missing.size > 0) {
      return none(`enter ${Array.from(missing).map((d) => DIM_LABEL[d]).join(' and ')} to select a stored band`);
    }
    if (structureMismatch) return none('the stored standard is for a structure that does not match this proposal');
    return none('no stored band covers the entered values');
  }

  const distinct = Array.from(new Set(matches.map((m) => m.numericValue as number)));
  if (distinct.length > 1) {
    return none(`the stored standards conflict for these values (${clausesOf(matches).join(', ')})`);
  }
  const first = matches[0];
  return {
    ok: true,
    standardType,
    value: distinct[0],
    clause: clausesOf(matches).join('; '),
    clauses: clausesOf(matches),
    quote: first.row.source_quote ?? '',
    band: first.row.conditionality,
    rowIds: matches.map((m) => m.row.id),
    unmodelledClauses: clausesOf(unusable),
  };
}
