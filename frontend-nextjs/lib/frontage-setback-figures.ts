/**
 * Which built-form figures show upper-level setbacks for the precincts an address is in.
 * The legend labels lifted off those figures are withheld from the rules list; this points
 * the reader at the figure instead. Data: data/frontage-setback-figures.json, built by
 * scripts/frontage_setback_figures.py.
 *
 * prior-art-checked: lib/not-covered.ts lists withheld chapters council-wide; nothing in lib/
 * maps a precinct to a figure page.
 */

import { captureServerException } from '@/lib/posthog-server';

export interface FrontageFigureEntry {
  precinct_id: string | null;
  page: number;
  figure: string | null;
}

export interface FrontageChapter {
  chapter_key: string;
  r2_path: string;
  pdf_sha256?: string;
  pdf_url: string;
  figures: FrontageFigureEntry[];
}

export interface FrontageFigureData {
  council: string;
  chapters: FrontageChapter[];
}

export interface FrontageFigureItem {
  chapter_key: string;
  page: number;
  figure: string | null;
  pdf_url: string;
}

/**
 * Fails closed: a chapter whose current PDF is not the one the pages were read from
 * contributes nothing.
 */
export function frontageSetbackFigures(
  data: FrontageFigureData,
  council: string | null,
  precinctIds: string[],
  currentPaths: Record<string, string | null>,
  chapterKeysOfPrecincts: string[],
): FrontageFigureItem[] {
  if (!council || council !== data.council) return [];
  const precincts = new Set(precinctIds);
  const chapterKeys = new Set(chapterKeysOfPrecincts);
  const seen = new Set<string>();
  const out: FrontageFigureItem[] = [];
  for (const ch of data.chapters) {
    if (currentPaths[ch.chapter_key] !== ch.r2_path || !ch.pdf_url) continue;   // no link without a PDF URL
    for (const f of ch.figures) {
      // a figure keyed to the centre ('14E') applies to its sub-precincts ('14E_L3') too
      const p = f.precinct_id;
      const applies = p !== null
        ? precincts.has(p) || precinctIds.some((id) => id.startsWith(`${p}_`))
        : chapterKeys.has(ch.chapter_key);
      if (!applies) continue;
      const key = `${ch.chapter_key}|${f.page}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({
        chapter_key: ch.chapter_key,
        page: f.page,
        figure: f.figure,
        pdf_url: `${ch.pdf_url}#page=${f.page}`,
      });
    }
  }
  return out.sort((a, b) =>
    a.chapter_key === b.chapter_key ? a.page - b.page : a.chapter_key < b.chapter_key ? -1 : 1,
  );
}

export function frontageSetbackNote(items: FrontageFigureItem[] | null | undefined): string | null {
  if (!items || items.length === 0) return null;
  const parts = items.map((i) =>
    i.figure ? `see Figure ${i.figure}, page ${i.page}` : `see page ${i.page}`,
  );
  // "see" appears once at the front: "...centre: see Figure A, page 1; Figure B, page 2"
  const joined = parts.map((p, idx) => (idx === 0 ? p : p.replace(/^see /, ''))).join('; ');
  return `Upper-level setbacks apply to some street frontages in this centre: ${joined}`;
}

type Query = (sql: string, params: unknown[]) => Promise<{ rows: Record<string, unknown>[] }>;

/**
 * The route's two read-only lookups, then frontageSetbackFigures. A failure is reported and returned as
 * failed: true, so the page says the figures could not be loaded; the rules response is unchanged.
 */
export interface FrontageFigureResult {
  items: FrontageFigureItem[];
  /** true when the lookup failed: the page says so instead of looking like "no figures" */
  failed: boolean;
}

export async function loadFrontageSetbackFigures(
  query: Query,
  data: FrontageFigureData,
  council: string | null | undefined,
  precinctIdCsv: string | null | undefined,
): Promise<FrontageFigureResult> {
  const precinctIds = (precinctIdCsv ?? '').split(',').map((s) => s.trim()).filter(Boolean);
  if (!council || council !== data.council || precinctIds.length === 0) return { items: [], failed: false };
  try {
    const reg = await query(
      `SELECT chapter_key, r2_current_path FROM dcp_chapter_registry
       WHERE is_active AND council = $1 AND chapter_key = ANY($2)`,
      [data.council, data.chapters.map((c) => c.chapter_key)],
    );
    const chs = await query(
      `SELECT DISTINCT source_chapter_key FROM regulatory_provisions
       WHERE source_council = $1 AND is_current AND v2_precinct_id = ANY($2::text[])`,
      [data.council, precinctIds],
    );
    const currentPaths: Record<string, string | null> = {};
    for (const r of reg.rows) currentPaths[String(r.chapter_key)] = (r.r2_current_path as string | null) ?? null;
    const keys = chs.rows.map((r) => r.source_chapter_key).filter((k): k is string => typeof k === 'string');
    return { items: frontageSetbackFigures(data, council, precinctIds, currentPaths, keys), failed: false };
  } catch (err) {
    console.error('[frontage figures] lookup failed:', err);
    captureServerException(err, { endpoint: '/api/provisions/for-property', part: 'frontage_setback_figures' });
    return { items: [], failed: true };
  }
}
