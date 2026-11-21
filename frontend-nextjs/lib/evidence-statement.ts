// Shape of GET /api/housing-sepp/evidence (built in services/evidence_statement.py). prior-art-checked: no existing type for it (grep lib/ hooks/, 2026-11-20).

export interface EvidenceExclusion {
  para: string; clause: string; page: number; law_words: string; result: string; result_words: string;
  detail: string | null; source_checked: string; not_seen?: string | null;
}
export interface VersionCheck { version: string; verdict: string; result_words: string; checked_page: number | null; stale: boolean }
export interface EvidenceControl {
  version_checks?: { status: 'ok' | 'none' | 'unreadable'; versions: VersionCheck[] };
  label?: string | null; control_type: string | null; requirement: string | null; council_words: string | null; clause: string | null; clause_shown: boolean; page: number | null;
}
export interface EvidenceFile {
  chapter: string; version: string; held_from: string | null; replaced_on: string | null; current: boolean;
  council_file_date: string | null; council_file_date_note: string | null;
}
/** A paragraph the tool did not clear, so a person has to look. Built from the exclusion rows in services/evidence_statement.py. */
export interface ManualCheck {
  clause: string | null; page: number | null; law_words: string | null; result_words: string | null; detail: string | null; not_seen?: string | null;
}
/** NSW Road Rules wording, word for word from the saved text (services/evidence_statement.py road_rules()). */
export interface RoadRule { clause: string; heading: string | null; quote: string; source_url: string }
export interface RoadRules { status: 'ok' | 'unreadable'; reason?: string; instrument?: string | null; copied_on?: string | null; note?: string | null; rules?: RoadRule[] }
/** The walk drawn as a line (services/lmr_route_map.py). Points are [lat, lon]. A route is present only when it is the walk the page shows. */
export type LatLon = [number, number];
export interface RouteDestination { name: string | null; kind: 'entrance' | 'station_outline' | 'town_centre_edge' }
export interface RouteEntrance { lat: number; lon: number; name: string | null; exact: boolean }
export interface RouteLine {
  length_m: number; walk_m: number; points: LatLon[]; entrance: RouteEntrance | null; destination: RouteDestination;
  busy_road_points: LatLon[]; osm_extract: string | null;
}
export interface RouteMap {
  status: 'ok' | 'unavailable'; reason?: string | null;
  lot?: { lat: number; lon: number }; entrance?: RouteEntrance | null; destination?: RouteDestination; destinations_differ?: boolean;
  careful?: RouteLine | null; careful_note?: string | null; normal?: RouteLine | null; normal_note?: string | null;
  attribution?: string | null; note?: string | null;
}
export interface Evidence {
  law_version_date: string | null; headline: string | null; lga: string | null; notes: string[];
  exclusions: EvidenceExclusion[];
  // Optional: the page (Vercel) and the data (Railway) deploy separately, so an older response without these must still render.
  route_map?: RouteMap | null;
  road_rules?: RoadRules;
  summary?: { total: number; counts: Record<string, number>; line: string };
  manual_checks?: ManualCheck[];
  walk: {
    clause: string | null; page: number | null; anchor: string | null; limit_m: number | null; walk_low_m: number | null; walk_high_m: number | null; detail: string | null; heuristic: string | null;
    margin_low_m?: number | null; margin_high_m?: number | null; entrance_unmapped_extra_m?: number | null;
    crossings_only_walk_m?: number | null; crossings_only_note?: string | null;
  };
  council_controls: { status: 'ok' | 'none' | 'unreadable'; reason?: string; as_at_line?: string | null; controls: EvidenceControl[] };
  council_files: { status: 'ok' | 'none' | 'unreadable'; reason?: string; files: EvidenceFile[] };
}

/** The proxy address for a point, or null when either coordinate is not a number. */
export function evidenceUrl(lat: string | null, lng: string | null): string | null {
  const ok = (v: string | null) => typeof v === 'string' && v.trim() !== '' && Number.isFinite(Number(v));
  return ok(lat) && ok(lng) ? `/api/housing-sepp/evidence?lat=${encodeURIComponent(String(lat))}&lng=${encodeURIComponent(String(lng))}` : null;
}

const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const isLatLon = (p: unknown): p is LatLon => Array.isArray(p) && p.length === 2 && finite(p[0]) && finite(p[1]) && Math.abs(p[0]) <= 90 && Math.abs(p[1]) <= 180;
const optString = (v: unknown) => v === undefined || v === null || typeof v === 'string';   // printed as text, so an object here would crash the page

const destinationOk = (d: unknown): boolean => !!d && typeof d === 'object'
  && ['entrance', 'station_outline', 'town_centre_edge'].includes((d as Partial<RouteDestination>).kind as string) && optString((d as Partial<RouteDestination>).name);

function routeLineOk(l: unknown): boolean {
  if (!l || typeof l !== 'object') return false;
  const x = l as Partial<RouteLine>;
  const e = x.entrance as Partial<RouteEntrance> | null | undefined;
  return finite(x.length_m) && finite(x.walk_m) && Array.isArray(x.points) && x.points.length >= 2 && x.points.every(isLatLon)
    && Array.isArray(x.busy_road_points) && x.busy_road_points.every(isLatLon)
    && destinationOk(x.destination)
    && (e === null || e === undefined || (typeof e === 'object' && finite(e.lat) && finite(e.lon) && optString(e.name)))
    && optString(x.osm_extract);
}

/** A route map that is present must be well formed: a malformed one shows the error line, never a missing or half-drawn map. */
export function routeMapOk(rm: unknown): boolean {
  if (rm === undefined || rm === null) return true;   // an older server, or no map for this lot
  if (typeof rm !== 'object') return false;
  const m = rm as Partial<RouteMap>;
  if (!optString(m.reason) || !optString(m.careful_note) || !optString(m.normal_note) || !optString(m.attribution) || !optString(m.note)) return false;
  if (m.destination !== undefined && m.destination !== null && !destinationOk(m.destination)) return false;   // the figure prefers this one, so it is checked too
  if (m.destinations_differ !== undefined && typeof m.destinations_differ !== 'boolean') return false;
  if (m.status === 'unavailable') return true;
  if (m.status !== 'ok') return false;
  const drawn = [m.careful, m.normal].filter((l) => l !== null && l !== undefined);
  return drawn.length > 0 && drawn.every(routeLineOk);
}

/** True only for a payload with every part the page reads. A partial payload is a failure, never an empty page. */
export function isEvidence(x: unknown): x is Evidence {
  const r = x as Partial<Evidence> | null;
  const src = (s: unknown) => !!s && typeof s === 'object' && ['ok', 'none', 'unreadable'].includes((s as { status?: string }).status ?? '');
  const rows = (a: unknown, keys: string[]) => Array.isArray(a) && a.every((e) => !!e && typeof e === 'object' && keys.every((k) => k in (e as object)));
  // New optional parts may be absent (an older server), but one that is present in the wrong shape is a failure, never a silently missing section.
  // A legal quotation must be real text with its clause and source: a null or empty quote would print an empty quotation under a valid-looking citation.
  const text = (v: unknown) => typeof v === 'string' && v.trim() !== '';
  const optText = (v: unknown) => v === undefined || v === null || typeof v === 'string';   // printed as text, so an object here would crash the page
  const roadRuleOk = (e: unknown) => !!e && typeof e === 'object' && text((e as { clause?: unknown }).clause) && text((e as { quote?: unknown }).quote) && text((e as { source_url?: unknown }).source_url)
    && optText((e as { heading?: unknown }).heading);
  const roadRulesOk = r?.road_rules === undefined || (!!r.road_rules && typeof r.road_rules === 'object'
    && optText(r.road_rules.reason) && optText(r.road_rules.instrument) && optText(r.road_rules.copied_on)
    && (r.road_rules.status === 'unreadable' || (r.road_rules.status === 'ok' && Array.isArray(r.road_rules.rules) && r.road_rules.rules.length > 0 && r.road_rules.rules.every(roadRuleOk))));
  const optionalParts = roadRulesOk && routeMapOk(r?.route_map) && (r?.manual_checks === undefined || rows(r.manual_checks, ['clause', 'law_words']))
    && (r?.summary === undefined || (!!r.summary && typeof r.summary === 'object' && typeof (r.summary as { line?: unknown }).line === 'string'));
  return !!r && typeof r === 'object' && optionalParts && rows(r.exclusions, ['para', 'clause', 'page', 'law_words', 'result_words', 'source_checked'])
    && Array.isArray(r.notes) && !!r.walk && typeof r.walk === 'object'
    && src(r.council_controls) && src(r.council_files)
    && rows(r.council_controls?.controls, ['council_words', 'page']) && rows(r.council_files?.files, ['chapter', 'version', 'current']);
}
