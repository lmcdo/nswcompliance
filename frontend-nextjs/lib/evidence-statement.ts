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
export interface Evidence {
  law_version_date: string | null; headline: string | null; lga: string | null; notes: string[];
  exclusions: EvidenceExclusion[];
  // Optional: the page (Vercel) and the data (Railway) deploy separately, so an older response without these must still render.
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

/** True only for a payload with every part the page reads. A partial payload is a failure, never an empty page. */
export function isEvidence(x: unknown): x is Evidence {
  const r = x as Partial<Evidence> | null;
  const src = (s: unknown) => !!s && typeof s === 'object' && ['ok', 'none', 'unreadable'].includes((s as { status?: string }).status ?? '');
  const rows = (a: unknown, keys: string[]) => Array.isArray(a) && a.every((e) => !!e && typeof e === 'object' && keys.every((k) => k in (e as object)));
  // New optional parts may be absent (an older server), but one that is present in the wrong shape is a failure, never a silently missing section.
  const roadRulesOk = r?.road_rules === undefined || (!!r.road_rules && typeof r.road_rules === 'object'
    && (r.road_rules.status === 'unreadable' || (r.road_rules.status === 'ok' && rows(r.road_rules.rules, ['clause', 'quote', 'source_url']) && (r.road_rules.rules?.length ?? 0) > 0)));
  const optionalParts = roadRulesOk && (r?.manual_checks === undefined || rows(r.manual_checks, ['clause', 'law_words']))
    && (r?.summary === undefined || (!!r.summary && typeof r.summary === 'object' && typeof (r.summary as { line?: unknown }).line === 'string'));
  return !!r && typeof r === 'object' && optionalParts && rows(r.exclusions, ['para', 'clause', 'page', 'law_words', 'result_words', 'source_checked'])
    && Array.isArray(r.notes) && !!r.walk && typeof r.walk === 'object'
    && src(r.council_controls) && src(r.council_files)
    && rows(r.council_controls?.controls, ['council_words', 'page']) && rows(r.council_files?.files, ['chapter', 'version', 'current']);
}
