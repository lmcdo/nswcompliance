/**
 * Prospector filter state — URL param parsing/serialisation and API body builders.
 * Pure functions, no React. Mirrors LotSearchSchema in app/api/lot-search/route.ts.
 */

export const PAGE_SIZE = 50;

export type TriState = 'any' | 'yes' | 'no';
export type ConfidenceFilter = 'any' | 'low' | 'medium' | 'high';
export type OrderDir = 'asc' | 'desc';

/** UI-sortable columns → lot_search_index column names (API whitelist). */
export const ORDER_COLUMNS = {
  ca_realistic_gfa_m2: 'GFA (m²)',
  lot_area_m2: 'Area (m²)',
  ca_realistic_dwellings: 'Dwellings',
  lep_fsr: 'FSR',
  lep_height_m: 'Height (m)',
} as const;

export type OrderCol = keyof typeof ORDER_COLUMNS;

export interface ProspectorFilters {
  lga_name: string;
  zone_codes: string[];
  min_area_m2: number | null;
  max_area_m2: number | null;
  min_gfa_m2: number | null;
  max_gfa_m2: number | null;
  min_dwellings: number | null;
  heritage: TriState;
  flood_prone: TriState;
  bushfire_prone: TriState;
  min_confidence: ConfidenceFilter;
  binding_constraint: string[];
  order_by: OrderCol;
  order_dir: OrderDir;
  page: number; // 1-based
}

export const DEFAULT_FILTERS: ProspectorFilters = {
  lga_name: 'INNER WEST',
  zone_codes: [],
  min_area_m2: null,
  max_area_m2: null,
  min_gfa_m2: null,
  max_gfa_m2: null,
  min_dwellings: null,
  heritage: 'any',
  flood_prone: 'any',
  bushfire_prone: 'any',
  min_confidence: 'any',
  binding_constraint: [],
  order_by: 'ca_realistic_gfa_m2',
  order_dir: 'desc',
  page: 1,
};

// ---------------------------------------------------------------------------
// Parsing helpers
// ---------------------------------------------------------------------------

function parsePositiveNumber(value: string | null): number | null {
  const trimmed = value?.trim() ?? '';
  if (trimmed === '') return null;
  const n = Number(trimmed);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function parsePositiveInt(value: string | null): number | null {
  const n = parsePositiveNumber(value);
  return n != null ? Math.floor(n) : null;
}

function parseTriState(value: string | null): TriState {
  return value === 'yes' || value === 'no' ? value : 'any';
}

function parseList(value: string | null): string[] {
  if (!value) return [];
  return value
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

/** Parse URL search params into a complete filter state. Invalid values fall back to defaults. */
export function parseFilters(params: URLSearchParams): ProspectorFilters {
  const orderByRaw = params.get('order_by');
  const order_by: OrderCol =
    orderByRaw != null && orderByRaw in ORDER_COLUMNS
      ? (orderByRaw as OrderCol)
      : DEFAULT_FILTERS.order_by;

  const confidenceRaw = params.get('min_confidence');
  const min_confidence: ConfidenceFilter =
    confidenceRaw === 'low' || confidenceRaw === 'medium' || confidenceRaw === 'high'
      ? confidenceRaw
      : 'any';

  const pageRaw = parsePositiveInt(params.get('page'));

  return {
    lga_name: params.get('lga') || DEFAULT_FILTERS.lga_name,
    zone_codes: parseList(params.get('zones')),
    min_area_m2: parsePositiveNumber(params.get('min_area')),
    max_area_m2: parsePositiveNumber(params.get('max_area')),
    min_gfa_m2: parsePositiveNumber(params.get('min_gfa')),
    max_gfa_m2: parsePositiveNumber(params.get('max_gfa')),
    min_dwellings: parsePositiveInt(params.get('min_dwellings')),
    heritage: parseTriState(params.get('heritage')),
    flood_prone: parseTriState(params.get('flood')),
    bushfire_prone: parseTriState(params.get('bushfire')),
    min_confidence,
    binding_constraint: parseList(params.get('binding')),
    order_by,
    order_dir: params.get('order_dir') === 'asc' ? 'asc' : 'desc',
    page: pageRaw ?? 1,
  };
}

/** Serialise filter state to URL search params. Defaults are omitted to keep URLs short. */
export function serializeFilters(filters: ProspectorFilters): URLSearchParams {
  const params = new URLSearchParams();

  if (filters.lga_name !== DEFAULT_FILTERS.lga_name) params.set('lga', filters.lga_name);
  if (filters.zone_codes.length > 0) params.set('zones', filters.zone_codes.join(','));
  if (filters.min_area_m2 != null) params.set('min_area', String(filters.min_area_m2));
  if (filters.max_area_m2 != null) params.set('max_area', String(filters.max_area_m2));
  if (filters.min_gfa_m2 != null) params.set('min_gfa', String(filters.min_gfa_m2));
  if (filters.max_gfa_m2 != null) params.set('max_gfa', String(filters.max_gfa_m2));
  if (filters.min_dwellings != null) params.set('min_dwellings', String(filters.min_dwellings));
  if (filters.heritage !== 'any') params.set('heritage', filters.heritage);
  if (filters.flood_prone !== 'any') params.set('flood', filters.flood_prone);
  if (filters.bushfire_prone !== 'any') params.set('bushfire', filters.bushfire_prone);
  if (filters.min_confidence !== 'any') params.set('min_confidence', filters.min_confidence);
  if (filters.binding_constraint.length > 0)
    params.set('binding', filters.binding_constraint.join(','));
  if (filters.order_by !== DEFAULT_FILTERS.order_by) params.set('order_by', filters.order_by);
  if (filters.order_dir !== DEFAULT_FILTERS.order_dir) params.set('order_dir', filters.order_dir);
  if (filters.page > 1) params.set('page', String(filters.page));

  return params;
}

// ---------------------------------------------------------------------------
// API body builders
// ---------------------------------------------------------------------------

function triStateToBoolean(value: TriState): boolean | undefined {
  if (value === 'yes') return true;
  if (value === 'no') return false;
  return undefined;
}

/** Shared filter fields for both search and summary modes. */
function buildFilterFields(filters: ProspectorFilters): Record<string, unknown> {
  const body: Record<string, unknown> = { lga_name: filters.lga_name };

  if (filters.zone_codes.length > 0) body.zone_codes = filters.zone_codes;
  if (filters.min_area_m2 != null) body.min_area_m2 = filters.min_area_m2;
  if (filters.max_area_m2 != null) body.max_area_m2 = filters.max_area_m2;
  if (filters.min_gfa_m2 != null) body.min_gfa_m2 = filters.min_gfa_m2;
  if (filters.max_gfa_m2 != null) body.max_gfa_m2 = filters.max_gfa_m2;
  if (filters.min_dwellings != null) body.min_dwellings = filters.min_dwellings;

  const heritage = triStateToBoolean(filters.heritage);
  if (heritage !== undefined) body.heritage = heritage;
  const flood = triStateToBoolean(filters.flood_prone);
  if (flood !== undefined) body.flood_prone = flood;
  const bushfire = triStateToBoolean(filters.bushfire_prone);
  if (bushfire !== undefined) body.bushfire_prone = bushfire;

  if (filters.min_confidence !== 'any') body.min_confidence = filters.min_confidence;
  if (filters.binding_constraint.length > 0) body.binding_constraint = filters.binding_constraint;

  return body;
}

/** Build POST body for paginated search mode. */
export function buildSearchBody(filters: ProspectorFilters): Record<string, unknown> {
  return {
    ...buildFilterFields(filters),
    limit: PAGE_SIZE,
    offset: (filters.page - 1) * PAGE_SIZE,
    order_by: filters.order_by,
    order_dir: filters.order_dir,
  };
}

/** Build POST body for summary mode (no pagination or ordering). */
export function buildSummaryBody(filters: ProspectorFilters): Record<string, unknown> {
  return buildFilterFields(filters);
}

// ---------------------------------------------------------------------------
// Response types (mirror route.ts response shapes)
// ---------------------------------------------------------------------------

export interface LotResult {
  lotidstring: string;
  lga_name: string;
  zone_code: string | null;
  lot_area_m2: number | null;
  lep_height_m: number | null;
  lep_fsr: number | null;
  // null = the overlay was never resolved for this lot. NOT "no heritage",
  // "not flood prone" or "not bushfire prone". Typed so a consumer cannot
  // assume two states, and so `=== false` keeps meaning something.
  heritage: boolean | null;
  flood_prone: boolean | null;
  bushfire_prone: boolean | null;
  bushfire_category: string | null;
  ca_dev_type: string | null;
  ca_realistic_gfa_m2: number | null;
  ca_realistic_dwellings: number | null;
  ca_binding_constraint: string | null;
  ca_confidence: string | null;
  ca_effective_height_m: number | null;
  ca_effective_fsr: number | null;
  ca_buildable_footprint_m2: number | null;
  ca_setback_front_m: number | null;
  ca_setback_rear_m: number | null;
  ca_setback_side_m: number | null;
  ca_gaps: unknown;
}

export interface SearchResponse {
  lots: LotResult[];
  total_count: number;
  query_ms: number;
}

export interface DistributionEntry {
  count: number;
  [key: string]: unknown;
}

export interface SummaryResponse {
  index_refreshed_at: string | null;
  total_lots: number;
  lots_with_ca: number;
  avg_area_m2: number | null;
  avg_gfa_m2: number | null;
  median_gfa_m2: number | null;
  p25_gfa_m2: number | null;
  p75_gfa_m2: number | null;
  avg_dwellings: number | null;
  heritage_count: number;
  flood_count: number;
  bushfire_count: number;
  confidence_high: number;
  confidence_medium: number;
  confidence_low: number;
  zone_distribution: Array<{ zone_code: string; count: number }>;
  binding_distribution: Array<{ ca_binding_constraint: string; count: number }>;
  dev_type_distribution: Array<{ ca_dev_type: string; count: number }>;
  query_ms: number;
}
