/**
 * Plan brief: the council plan's own clauses, shown for a "Your project" row that has no proven figure.
 *
 * prior-art-checked: lib/project-summary.ts builds the proven-figure rows (DCP_ROW_SPECS) and shows "not found" when a row is
 * empty; lib/may-apply-query.ts serves withheld-area rows. Nothing served the plan's own clauses for a (council, project type,
 * rule type) when no proven figure exists. This module only groups rows that the API already proved (page, council words).
 */

export const BRIEF_DEV_TYPES = [
  'dwelling_house', 'dual_occupancy', 'secondary_dwelling', 'multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing',
] as const;
export type BriefDevType = (typeof BRIEF_DEV_TYPES)[number];

export type ZoneGroup = 'R2' | 'R3' | 'R4' | 'B' | 'ANY'; // noqa: zone-codes -- the brief build's own group labels (project_brief_rows.zone_group), not a regulatory lookup
export const BRIEF_TEXT_LIMIT = 1500;   // characters of one clause shown (was 600: it cut tables off)
export const BRIEF_ROW_LIMIT = 5;      // stored per row
export const BRIEF_FIRST_SHOWN = 3;    // shown before "show more"

/** One brief row = one "Your project" row (same keys as DCP_ROW_SPECS where one exists). */
export interface BriefRowSpec { key: string; label: string; types: string[] }
export const BRIEF_ROWS: BriefRowSpec[] = [
  { key: 'front', label: 'Front setback', types: ['front_setback'] },
  { key: 'side', label: 'Side setback', types: ['side_setback'] },
  { key: 'rear', label: 'Rear setback', types: ['rear_setback'] },
  { key: 'secondary', label: 'Setback to a second street (corner lots)', types: ['secondary_street_setback'] },
  { key: 'coverage', label: 'Site coverage', types: ['max_site_coverage'] },
  { key: 'landscape', label: 'Landscaped area and deep soil', types: ['landscaping_min', 'deep_soil_min'] },
  { key: 'pos', label: 'Private open space', types: ['private_open_space'] },
  { key: 'parking', label: 'Car parking', types: ['car_parking'] },
  { key: 'height', label: 'Building height', types: ['max_height'] },
];

/** Zone code -> the zone group the brief was built for. Anything else uses the 'ANY' build (zone-specific scope ignored). */
export function zoneGroup(zone: string | null | undefined): ZoneGroup {
  const z = (zone ?? '').trim().toUpperCase().split(/[\s:]/)[0];
  if (z === 'R2' || z === 'R3' || z === 'R4') return z; // noqa: zone-codes -- maps a lot's zone onto the brief build's group labels
  if (/^(B\d|MU\d|E1)$/.test(z)) return 'B';
  return 'ANY';
}

export function isBriefDevType(v: string | null | undefined): v is BriefDevType {
  return !!v && (BRIEF_DEV_TYPES as readonly string[]).includes(v);
}

/** A clause as the API serves it (council's words, page proof already applied by the route). */
export interface BriefItem {
  id: number;
  verdict: 'APPLIES' | 'MIGHT';
  text: string;
  page: number | null;
  pageLabel: string | null;
  clauseLabel: string | null;
  sectionHeader: string | null;
  chapterKey: string | null;
  /** The plan's own name for the chapter this clause sits in, so the reader can see which part of the plan it comes from. */
  chapterLabel?: string | null;
  pageProven: boolean;
  /** Link to the council's plan, opened at the page when the address is a PDF; null when we hold no address. */
  url?: string | null;
  /** The page number the link opens at (null when the link cannot name a page). */
  urlPage?: number | null;
  /** For a fragment or an opener ('... that:', 'in accordance with the following table'): the clauses that follow it on the page. */
  continues?: string[];
}
export interface BriefRow { key: string; label: string; items: BriefItem[] }

export interface StoredBriefRow { row_type: string; rank: number; item: BriefItem }

/** Group stored rows into display rows, in BRIEF_ROWS order. Rows whose key is in `provenKeys` are left out (the proven figure wins). */
export function shapeBriefRows(stored: StoredBriefRow[], provenKeys: ReadonlySet<string> = new Set()): BriefRow[] {
  return BRIEF_ROWS
    .filter((spec) => !provenKeys.has(spec.key))
    .map((spec) => {
      const items = stored
        .filter((r) => spec.types.includes(r.row_type))
        .sort((a, b) => spec.types.indexOf(a.row_type) - spec.types.indexOf(b.row_type) || a.rank - b.rank)
        .map((r) => r.item)
        .filter((it, i, all) => all.findIndex((o) => o.id === it.id) === i)   // one clause once, even if it answers two types
        .slice(0, BRIEF_ROW_LIMIT);
      return { key: spec.key, label: spec.label, items };
    });
}

/** Words next to every clause: indicative, never "verified". */
export const BRIEF_NOTE =
  "From the plan's own words, picked for your project type. Indicative only: read the clause and check the plan before you rely on it.";
export const BRIEF_EMPTY_TEXT = 'No matching clause found in this chapter. Open the plan.';
export const BRIEF_TAG_APPLIES = 'Applies';
export const BRIEF_TAG_MAY = 'May apply';


/** The link to the plan at the page: only a PDF address can take a #page anchor (same rule as DcpNotCoveredNotice). */
export function planLink(url: string | null | undefined, page: number | null | undefined): { href: string; page: number | null } | null {
  if (!url) return null;
  const isPdf = /\.pdf(\?|#|$)/i.test(url);
  if (isPdf && typeof page === 'number' && page > 0 && !url.includes('#')) return { href: `${url}#page=${page}`, page };
  return { href: url, page: null };
}

/** Collapse spaces but KEEP line breaks, so a table the plan printed as rows stays rows. */
export function tidyText(raw: string | null | undefined, limit = BRIEF_TEXT_LIMIT): string {
  return String(raw ?? '').replace(/[\t\f\v ]+/g, ' ').replace(/ *\n */g, '\n').replace(/\n{3,}/g, '\n\n').trim().slice(0, limit);
}

/** A clause that leaves its figure to what follows: ends with a colon, or points to a table or list below, or is only a fragment. */
const OPENER = /(:\s*$)|following (table|controls|requirements|standards)|as follows|in accordance with (the )?(table|figure)|refer to (table|figure)|shown in (table|figure)/i;
export function needsFollowOn(text: string): boolean {
  const body = text.replace(/^#.*?\n/, '').replace(/\s+/g, ' ').trim();
  // a short clause that holds a figure is complete; a clause that names a table but holds no figure points at the table rows that follow
  return (body.length < 90 && !/\d/.test(body)) || OPENER.test(body) || (/\btable\b/i.test(body) && !/\d/.test(body));
}

/** Rows of a printed table: two or more lines that each hold two or more ' | ' separated cells. */
export function tableRows(text: string): string[][] | null {
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  const rows = lines.map((l) => l.split('|').map((c) => c.trim())).filter((c) => c.length >= 2 && c.some(Boolean));
  return rows.length >= 2 && rows.length >= lines.length * 0.6 ? rows : null;
}


/** Which councils, project type and zone group the plan brief is served for (shared/brief-scope.json). */
export type BriefScope = { councils: readonly string[]; dev_type: string; zone_group: string; excluded_provision_ids: readonly number[] };

/** The brief is shown only where its first five clauses per topic have been read against the council's own section headings. */
export function inBriefScope(scope: BriefScope, council: string, devType: string, group: string): boolean {
  return scope.councils.includes(council) && devType === scope.dev_type && group === scope.zone_group;
}

/** Drop clauses the scope file skips (another building type, a named place, an ancillary structure) and renumber the rest 1..n
 *  per topic, so the next best clause moves up. Nothing is deleted from the table. */
export function dropExcluded(stored: StoredBriefRow[], excluded: ReadonlySet<number>): StoredBriefRow[] {
  const kept = stored.filter((r) => !excluded.has(r.item.id));
  const byTopic = new Map<string, StoredBriefRow[]>();
  for (const r of kept) byTopic.set(r.row_type, [...(byTopic.get(r.row_type) ?? []), r]);
  const out: StoredBriefRow[] = [];
  byTopic.forEach((list) => {
    list.sort((a, b) => a.rank - b.rank).forEach((r, i) => out.push({ ...r, rank: i + 1 }));
  });
  return out;
}

/** Where a clause sits in the plan: the chapter's name, then the section heading when it adds something. */
export function whereInPlan(item: { chapterLabel?: string | null; sectionHeader?: string | null }): string {
  const chapter = String(item.chapterLabel ?? '').replace(/\s+/g, ' ').trim();
  const section = String(item.sectionHeader ?? '').replace(/^#+\s*/, '').replace(/\s+/g, ' ').trim().slice(0, 120);
  return [chapter, section && section !== chapter ? section : ''].filter(Boolean).join(' \u203a ');
}
