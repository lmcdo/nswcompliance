/**
 * Plan brief: the council plan's own clauses, shown for a "Your project" row that has no proven figure.
 *
 * prior-art-checked: lib/project-summary.ts builds the proven-figure rows (DCP_ROW_SPECS) and shows "not found" when a row is
 * empty; lib/may-apply-query.ts serves withheld-area rows. Nothing served the plan's own clauses for a (council, project type,
 * rule type) when no proven figure exists. This module only groups rows that the API already proved (page, council words).
 */

import { inferSectionNumberFromHeader } from '@/lib/see/sectionKey';

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


/** The link to the plan at the page: only a PDF address can take a #page anchor (same rule as DcpNotCoveredNotice). */
export function planLink(url: string | null | undefined, page: number | null | undefined): { href: string; page: number | null } | null {
  if (!url) return null;
  const isPdf = /\.pdf(\?|#|$)/i.test(url);
  if (isPdf && typeof page === 'number' && page > 0 && !url.includes('#')) return { href: `${url}#page=${page}`, page };
  return { href: url, page: null };
}

/** Collapse spaces but KEEP line breaks, so a table the plan printed as rows stays rows. */
/**
 * The clause label to print for a stored rule. The caller still prints it only when the clause is proven
 * (withServedCitation / citationIsShown), so this chooses WHICH label, never WHETHER to show one.
 *  1. a numeric section number at the start of the heading ("3.2.3"): the existing behaviour, unchanged;
 *  2. else a dotted lettered heading code ("DS3.3", "4A.2", "14B.10");
 *  3. else the tail of ref_number, which is the label the checker judged ("...__3_1_2 a" -> "3.1.2 a", "C1 1_2_1 a" -> "C1 1.2.1 a", "O17").
 * Null when none of them reads as a clause label ("Prescriptive Measures", "Part 8", an empty heading).
 */
export function briefClauseLabel(sectionHeader: string | null | undefined, refNumber: string | null | undefined): string | null {
  const fromHeader = inferSectionNumberFromHeader(sectionHeader);
  if (fromHeader) return fromHeader;
  const dotted = String(sectionHeader ?? '').trim().match(/^([A-Z]{1,2}\d+[A-Z]?(?:\.\d+)+|\d+[A-Z](?:\.\d+)+)(?=\s|$)/);
  if (dotted) return dotted[1];
  const tail = String(refNumber ?? '').split('__').pop()?.trim().replace(/~\d+$/, '') ?? '';
  // Only an anchored clause identifier (and an optional "a" / "(a)" item suffix) is returned, never the text after it.
  const id = tail.match(/^((?:[A-Za-z]{1,2}\d+[A-Za-z]? )?\d[\dA-Za-z]*(?:_\d[\dA-Za-z]*)*|[A-Za-z]{1,2}\d+[A-Za-z]?(?:_\d+[A-Za-z]?)*)(?: ([a-z]{1,2}|\([a-z0-9]+\)))?(?= |$)/);
  if (!id || /^\d{4,}$/.test(id[1])) return null;          // a year or a long bare number is metadata, not a clause
  return id[1].replace(/_/g, '.') + (id[2] ? ` ${id[2]}` : '');
}

export function tidyText(raw: string | null | undefined, limit = BRIEF_TEXT_LIMIT): string {
  return String(raw ?? '').replace(/[\t\f\v ]+/g, ' ').replace(/ *\n */g, '\n').replace(/\n{3,}/g, '\n\n').trim().slice(0, limit);
}

/** A clause that leaves its figure to what follows: ends with a colon, or points to a table or list below, or is only a fragment. */
const OPENER = /(:\s*$)|following (table|controls|requirements|standards)|as follows|in accordance with (the )?(table|figure)|refer to (table|figure)|shown in (table|figure)/i;
export function needsFollowOn(text: string): boolean {
  const body = text.replace(/^#.*?\n/, '').replace(/\s+/g, ' ').trim();
  // The digits in a table or figure NAME ("Table 3.1.2-a") are not a figure: Hornsby 3.1.2 a said "comply with Table 3.1.2-a" and was judged complete.
  const withoutNames = body.replace(/\b(?:table|figure)\s+[0-9a-z][\w.\-]*/gi, '');
  // a short clause that holds a figure is complete; a clause that names a table but holds no figure points at the table rows that follow
  return (body.length < 90 && !/\d/.test(body)) || OPENER.test(body) || (/\btable\b/i.test(body) && !/\d/.test(withoutNames));
}

/** The rule before table names were read as names: when no table can be found, only these clauses go on to show the next clauses on
 *  the page. A clause that is new to needsFollowOn (it names a table and states no figure) shows a table or nothing, never unrelated clauses. */
export function showsNextClauses(text: string): boolean {
  const body = text.replace(/^#.*?\n/, '').replace(/\s+/g, ' ').trim();
  return (body.length < 90 && !/\d/.test(body)) || OPENER.test(body) || (/\btable\b/i.test(body) && !/\d/.test(body));
}

const POINTS_AT_TABLE = /(?:following|below|above|next|this)\s+table|table\s+(?:below|follows|above)|in the table|the table\b/i;
const TABLE_CAPTION =/^\s*table\s+[0-9a-z][\w.\-]*\s*[:–—\-]/i;

/** The table inside a clause that also holds prose (Hornsby 3.1.2 h: a paragraph, then "a | b" rows, then the caption): the rows and
 *  their caption line, copied as printed, or null when the clause holds no table. A verbatim slice of the stored text, never a rewrite. */
export function tablePart(text: string): string | null {
  const lines = String(text ?? '').split('\n');
  const isRow = (l: string) => l.includes(' | ');
  const first = lines.findIndex(isRow);
  if (first < 0) return null;
  let last = first;
  for (let i = first + 1; i < lines.length; i++) if (isRow(lines[i])) last = i;
  if (lines.slice(first, last + 1).filter(isRow).length < 2) return null;
  const from = first > 0 && TABLE_CAPTION.test(lines[first - 1]) ? first - 1 : first;
  const to = last + 1 < lines.length && TABLE_CAPTION.test(lines[last + 1]) ? last + 1 : last;
  return lines.slice(from, to + 1).join('\n').trim();
}

/** Of the tables that follow a clause on its page, the one the clause names (by caption), else, when it names none ("the following
 *  table"), the first. A clause that names a table that is not among them gets null, never some other table. */
export function tableFor(clauseText: string, tables: readonly string[]): string | null {
  if (tables.length === 0) return null;
  const named = /\btable\s+([0-9][\w.\-]*)/i.exec(clauseText);
  // no table named: only a clause that points at one ("the following table", "the table below") takes the first that follows
  if (!named) return POINTS_AT_TABLE.test(clauseText) ? tables[0] : null;
  const token = named[1].replace(/[.\-]+$/, '').toLowerCase();
  const caption = (t: string) => t.split('\n').find((l) => TABLE_CAPTION.test(l)) ?? '';
  return tables.find((t) => caption(t).toLowerCase().includes(token)) ?? null;
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
