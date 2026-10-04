/**
 * HTML tables inside provision text (DQ-125).
 *
 * prior-art-checked: lib/provision-text-formatter.ts has no notion of HTML tags (grep <table|<tr|<td
 * returns nothing), and lib/sanitize.ts only serves the dangerouslySetInnerHTML views. The served
 * provisions list printed the extractor's table markup as literal tags: 1,064 served rules held 2,538
 * tables (measured 2026-10-04), every one closed and carrying no tag but table/thead/tbody/tr/th/td.
 *
 * The cells are the council's own values (e.g. a side-setback table: Ground 0.9m, First 0.9m,
 * Second 1.5m), so the tables are parsed and shown as tables -- stripping the tags would separate
 * each value from its row label. Parsing builds plain strings for React to render; no HTML is
 * ever injected, so nothing here needs sanitising.
 */

export interface ProvisionTable {
  head: string[][];
  body: string[][];
}

export type ProvisionSegment =
  | { kind: 'text'; text: string }
  | { kind: 'table'; table: ProvisionTable };

const TABLE_RE = /<table\b[^>]*>([\s\S]*?)<\/table>/gi;
const ROW_RE = /<tr\b[^>]*>([\s\S]*?)<\/tr>/gi;
const CELL_RE = /<(t[hd])\b[^>]*>([\s\S]*?)<\/\1>/gi;

const ENTITIES: Record<string, string> = {
  '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'", '&apos;': "'", '&nbsp;': ' ',
};

function cellText(raw: string): string {
  return raw
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<[^>]+>/g, '')
    .replace(/&(amp|lt|gt|quot|#39|apos|nbsp);/g, (m) => ENTITIES[m] ?? m)
    .replace(/\s+/g, ' ')
    .trim();
}

/** True when the text carries at least one table this module can parse. */
export function hasProvisionTable(text: string | null | undefined): boolean {
  return !!text && /<table\b[\s\S]*?<\/table>/i.test(text);
}

function parseTable(inner: string): ProvisionTable {
  const theadEnd = inner.search(/<\/thead>/i);
  const head: string[][] = [];
  const body: string[][] = [];
  for (const rowMatch of inner.matchAll(ROW_RE)) {
    const cells: string[] = [];
    let allTh = true;
    for (const cellMatch of rowMatch[1].matchAll(CELL_RE)) {
      if (cellMatch[1].toLowerCase() !== 'th') allTh = false;
      cells.push(cellText(cellMatch[2]));
    }
    if (cells.length === 0) continue;
    const inThead = theadEnd >= 0 && (rowMatch.index ?? 0) < theadEnd;
    (inThead || (allTh && body.length === 0) ? head : body).push(cells);
  }
  return dropEmptyColumns({ head, body });
}

/** A column with no text in any row carries nothing; removing it loses no value. */
function dropEmptyColumns(t: ProvisionTable): ProvisionTable {
  const rows = [...t.head, ...t.body];
  const width = Math.max(0, ...rows.map((r) => r.length));
  const keep: number[] = [];
  for (let c = 0; c < width; c++) {
    if (rows.some((r) => (r[c] ?? '') !== '')) keep.push(c);
  }
  const pick = (r: string[]) => keep.map((c) => r[c] ?? '');
  return { head: t.head.map(pick), body: t.body.map(pick) };
}

/** Split provision text into prose and table segments, in order. Text without tables is one segment. */
export function splitProvisionTables(text: string): ProvisionSegment[] {
  const out: ProvisionSegment[] = [];
  let last = 0;
  for (const m of text.matchAll(TABLE_RE)) {
    const start = m.index ?? 0;
    const before = text.slice(last, start);
    if (before.trim()) out.push({ kind: 'text', text: before });
    const table = parseTable(m[1]);
    if (table.head.length + table.body.length > 0) out.push({ kind: 'table', table });
    last = start + m[0].length;
  }
  const rest = text.slice(last);
  if (rest.trim() || out.length === 0) out.push({ kind: 'text', text: rest });
  return out;
}

/**
 * The same text with each table written as plain rows, cells joined by ' | ', for views that print
 * text only (collapsed previews, the PDF export).
 */
export function provisionTablesToPlainText(text: string | null | undefined): string {
  if (!text || !hasProvisionTable(text)) return text ?? '';
  return splitProvisionTables(text)
    .map((seg) =>
      seg.kind === 'text'
        ? seg.text
        : '\n' + [...seg.table.head, ...seg.table.body]
            .map((r) => r.filter((c) => c !== '').join(' | '))
            .filter((line) => line !== '')
            .join('\n') + '\n'
    )
    .join('');
}
