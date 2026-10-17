/**
 * Which built-form figures show upper-level setbacks for the precincts an address is in.
 * The legend labels lifted off those figures are withheld from the rules list; this points
 * the reader at the figure instead. Data: data/frontage-setback-figures.json, built by
 * scripts/frontage_setback_figures.py.
 *
 * prior-art-checked: lib/not-covered.ts lists withheld chapters council-wide; nothing in lib/
 * maps a precinct to a figure page.
 */

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
    if (currentPaths[ch.chapter_key] !== ch.r2_path) continue;
    for (const f of ch.figures) {
      const applies =
        f.precinct_id !== null ? precincts.has(f.precinct_id) : chapterKeys.has(ch.chapter_key);
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
