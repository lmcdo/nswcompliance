// prior-art-checked: no module reduces the LEP map figures and the DCP structured
// controls into one "Your project" table. This file only SELECTS and PASSES
// THROUGH values that already exist (constraints from the Planning Portal,
// /api/dcp/structured-controls rows). It holds no planning figure of its own.

import { formatValue, noNumberLabel, shortCitation, type StructuredControl } from '@/components/compliance/DcpStructuredControls';

export const NOT_FOUND_TEXT = 'Not found in our data — check the plan';
export const NO_CONTROLS_FOR_TYPE_TEXT = 'We have no key controls for this project type yet';

export interface SummaryEntry {
  /** Sub-label, set only when a row draws on more than one control type. */
  label: string | null;
  /** The plan's figure exactly as the source gives it (already formatted by the existing helpers). */
  figure: string;
  /** A single number to compare with, or null when the source has none / has a range. */
  number: number | null;
  unit: string | null;
  /** "maximum" / "minimum" from the source's own marker, or null when unknown. */
  limit: 'maximum' | 'minimum' | null;
  document: string | null;
  clause: string | null;
  page: number | null;
  citation: string;
  url: string | null;
  words: string | null;
  condition: string | null;
}

export interface SummaryRow {
  key: string;
  label: string;
  source: 'LEP' | 'DCP';
  entries: SummaryEntry[];
  /** Link to the plan, shown with "not found". */
  planUrl: string | null;
}

export interface LepInputs {
  maxHeight: number | null | undefined;
  maxFsr: number | null | undefined;
  minLotSize: number | null | undefined;
  /** Name and link of the LEP, from the Land Zoning Map layer. */
  lepName: string | null;
  legislationUrl: string | null;
}

interface DcpRowSpec { key: string; label: string; types: string[] }

export const DCP_ROW_SPECS: DcpRowSpec[] = [
  { key: 'front', label: 'Front setback', types: ['front_setback'] },
  { key: 'side', label: 'Side setback', types: ['side_setback'] },
  { key: 'rear', label: 'Rear setback', types: ['rear_setback'] },
  { key: 'coverage', label: 'Site coverage', types: ['max_site_coverage'] },
  { key: 'landscape', label: 'Landscaped area and deep soil', types: ['landscaped_area_min', 'landscaping_min', 'deep_soil_min'] },
  { key: 'pos', label: 'Private open space', types: ['private_open_space'] },
  { key: 'parking', label: 'Car parking', types: ['car_parking'] },
  { key: 'solar', label: 'Solar access', types: ['solar_access_hours'] },
];

export interface ControlsPayload {
  has_controls: boolean;
  dcp_name?: string | null;
  categories: Array<{ controls: StructuredControl[] }>;
}

/** The single number a control states, or null for a range / no number. */
export function singleNumber(c: Pick<StructuredControl, 'value_min' | 'value_max'>): number | null {
  const { value_min: a, value_max: b } = c;
  if (a !== null && b !== null) return a === b ? a : null;
  if (a !== null) return a;
  if (b !== null) return b;
  return null;
}

function dcpEntry(c: StructuredControl, withLabel: boolean): SummaryEntry {
  const numeric = c.value_min !== null || c.value_max !== null;
  // A ceiling is marked by the API's own direction field ('max'); everything else is a floor.
  const limit: SummaryEntry['limit'] = numeric ? (c.direction === 'max' ? 'maximum' : 'minimum') : null;
  return {
    label: withLabel ? c.control_label : null,
    figure: numeric ? formatValue(c) : noNumberLabel(c),
    number: numeric ? singleNumber(c) : null,
    unit: c.unit,
    limit,
    document: c.dcp_name,
    clause: c.section_ref,
    page: c.pdf_page,
    citation: shortCitation(c),
    url: c.pdf_url,
    words: c.source_text,
    condition: c.condition,
  };
}

export function buildDcpRows(payload: ControlsPayload | null | undefined): SummaryRow[] {
  const all: StructuredControl[] = payload?.has_controls ? payload.categories.flatMap((cat) => cat.controls) : [];
  const planUrl = all.find((c) => c.pdf_url)?.pdf_url ?? null;
  return DCP_ROW_SPECS.map((spec) => {
    const matched = spec.types.flatMap((t) => all.filter((c) => c.control_type === t));
    return {
      key: spec.key,
      label: spec.label,
      source: 'DCP' as const,
      entries: matched.map((c) => dcpEntry(c, spec.types.length > 1)),
      planUrl,
    };
  });
}

function lepEntry(figure: string, number: number, unit: string, limit: 'maximum' | 'minimum', lep: LepInputs): SummaryEntry {
  return {
    label: null,
    figure,
    number,
    unit,
    limit,
    document: lep.lepName,
    clause: null,
    page: null,
    citation: 'LEP map',
    url: lep.legislationUrl,
    words: null,
    condition: null,
  };
}

export function buildLepRows(lep: LepInputs): SummaryRow[] {
  const rows: SummaryRow[] = [];
  const add = (key: string, label: string, entry: SummaryEntry | null) =>
    rows.push({ key, label, source: 'LEP', entries: entry ? [entry] : [], planUrl: lep.legislationUrl });
  add('height', 'Building height', lep.maxHeight ? lepEntry(`${lep.maxHeight} m`, lep.maxHeight, 'm', 'maximum', lep) : null);
  add('fsr', 'Floor space ratio', lep.maxFsr ? lepEntry(`${lep.maxFsr}:1`, lep.maxFsr, ':1', 'maximum', lep) : null);
  add('minlot', 'Minimum lot size', lep.minLotSize ? lepEntry(`${lep.minLotSize} m²`, lep.minLotSize, 'm²', 'minimum', lep) : null);
  return rows;
}

export type Comparison =
  | { kind: 'none' }
  | { kind: 'invalid' }
  | { kind: 'result'; relation: 'above' | 'below' | 'equal'; text: string };

/** Plain arithmetic on the passed-through number. No pass / fail wording. */
export function compareFigure(planNumber: number | null, input: string): Comparison {
  if (planNumber == null) return { kind: 'none' };
  const trimmed = input.trim();
  if (trimmed === '') return { kind: 'none' };
  const mine = Number(trimmed);
  if (!Number.isFinite(mine)) return { kind: 'invalid' };
  const relation = mine > planNumber ? 'above' : mine < planNumber ? 'below' : 'equal';
  const text = relation === 'equal'
    ? "Your figure is equal to the plan's figure."
    : `Your figure is ${relation} the plan's figure.`;
  return { kind: 'result', relation, text };
}

export function limitSentence(limit: SummaryEntry['limit']): string | null {
  return limit ? `The plan's figure is a ${limit}.` : null;
}

// ── "Triggered by your site" ─────────────────────────────────────────────────

export interface SiteFlag { key: string; label: string; detail: string | null; source: string; url: string | null }
export interface SiteFlagResult { flags: SiteFlag[]; unchecked: string[] }

/** Loose shape of the constraints fields read here (all optional; see PlanningConstraints). */
export interface FlagConstraints {
  floodProne?: boolean | null;
  floodMapNote?: string;
  heritage?: boolean;
  heritageItemName?: string;
  heritageLegislativeClause?: string;
  heritageLegislationUrl?: string;
  bushfireProne?: boolean;
  bushfireCategory?: string | null;
  acidSulfateSoils?: string;
  mineSubsidence?: { inDistrict: boolean; districtName?: string } | null;
  landslideRisk?: { hasRisk: boolean; layClass?: string } | null;
  greenweb?: { onGreenweb: boolean; categories: string[] } | null;
  greenwebUnchecked?: string;
  railOrBusyRoad?: { adjoins: boolean; roads: string[]; rail: boolean } | null;
  railOrBusyRoadUnchecked?: string;
  classifiedRoad?: { state: boolean; classified: boolean; roads: Array<{ roadNumber: string; roadName: string | null; roadClass: string }> } | null;
  classifiedRoadUnchecked?: string;
}

export function buildSiteFlags(c: FlagConstraints | null | undefined): SiteFlagResult {
  const flags: SiteFlag[] = [];
  const unchecked: string[] = [];
  if (!c) return { flags, unchecked };
  if (c.floodProne === true) {
    flags.push({ key: 'flood', label: 'Flood', detail: c.floodMapNote ?? null, source: "Council's Flood Planning Map", url: null });
  }
  if (c.heritage === true) {
    flags.push({
      key: 'heritage', label: 'Heritage',
      detail: [c.heritageItemName, c.heritageLegislativeClause].filter(Boolean).join(' — ') || null,
      source: 'Heritage map in the Local Environmental Plan', url: c.heritageLegislationUrl ?? null,
    });
  }
  if (c.bushfireProne === true) {
    flags.push({ key: 'bushfire', label: 'Bush fire prone land', detail: c.bushfireCategory ?? null, source: 'NSW Bush Fire Prone Land map', url: null });
  }
  if (typeof c.acidSulfateSoils === 'string' && c.acidSulfateSoils.trim() !== '') {
    flags.push({ key: 'acid', label: 'Acid sulfate soils', detail: `Map class: ${c.acidSulfateSoils}`, source: 'Acid Sulfate Soils Map', url: null });
  }
  if (c.mineSubsidence?.inDistrict) {
    flags.push({ key: 'mine', label: 'Mine subsidence district', detail: c.mineSubsidence.districtName ?? null, source: 'Mine Subsidence District map', url: null });
  }
  if (c.landslideRisk?.hasRisk) {
    flags.push({ key: 'landslide', label: 'Landslide risk', detail: c.landslideRisk.layClass ?? null, source: 'Landslide Risk Land map', url: null });
  }
  if (c.greenweb?.onGreenweb) {
    flags.push({ key: 'greenweb', label: 'Greenweb', detail: c.greenweb.categories.join(', ') || null, source: 'Ku-ring-gai DCP Greenweb map', url: null });
  }
  if (c.greenwebUnchecked) unchecked.push(c.greenwebUnchecked);
  if (c.railOrBusyRoad?.adjoins) {
    const parts = [...c.railOrBusyRoad.roads, ...(c.railOrBusyRoad.rail ? ['Railway land'] : [])];
    flags.push({ key: 'railroad', label: 'Next to a railway or busy road', detail: parts.join(', ') || null, source: 'Ku-ring-gai DCP busy roads and rail list', url: null });
  }
  if (c.railOrBusyRoadUnchecked) unchecked.push(c.railOrBusyRoadUnchecked);
  if (c.classifiedRoad && (c.classifiedRoad.state || c.classifiedRoad.classified)) {
    const roads = c.classifiedRoad.roads.map((r) => [r.roadNumber, r.roadName, r.roadClass].filter(Boolean).join(' ')).join('; ');
    flags.push({ key: 'classified', label: 'Next to a State or classified road', detail: roads || null, source: 'Transport for NSW road classification', url: null });
  }
  if (c.classifiedRoadUnchecked) unchecked.push(c.classifiedRoadUnchecked);
  return { flags, unchecked };
}
