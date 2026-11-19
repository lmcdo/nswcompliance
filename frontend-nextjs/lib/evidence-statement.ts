// Shape of GET /api/housing-sepp/evidence (built in services/evidence_statement.py). prior-art-checked: no existing type for it (grep lib/ hooks/, 2026-11-20).

export interface EvidenceExclusion {
  para: string; clause: string; page: number; law_words: string; result: string; result_words: string;
  detail: string | null; source_checked: string; not_seen?: string | null;
}
export interface EvidenceControl {
  control_type: string | null; requirement: string | null; council_words: string | null; clause: string | null; clause_shown: boolean; page: number | null;
}
export interface EvidenceFile {
  chapter: string; version: string; held_from: string | null; replaced_on: string | null; current: boolean;
  council_file_date: string | null; council_file_date_note: string | null;
}
export interface Evidence {
  law_version_date: string | null; headline: string | null; lga: string | null; notes: string[];
  exclusions: EvidenceExclusion[];
  walk: { clause: string | null; page: number | null; anchor: string | null; limit_m: number | null; walk_low_m: number | null; walk_high_m: number | null; detail: string | null; heuristic: string | null };
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
  return !!r && typeof r === 'object' && Array.isArray(r.exclusions) && Array.isArray(r.notes) && !!r.walk && typeof r.walk === 'object'
    && src(r.council_controls) && src(r.council_files)
    && Array.isArray(r.council_controls?.controls) && Array.isArray(r.council_files?.files);
}
