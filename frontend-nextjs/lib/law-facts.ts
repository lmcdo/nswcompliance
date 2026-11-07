/**
 * State-law figures for the low-and-mid-rise / TOD feature, read from the `law_facts` table.
 *
 * Every figure here arrives with its clause, PDF page, the sentence it came from and the law version date, and is
 * proven equal to the saved law text by `python scripts/load_law_facts.py --check` (ledger row DQ-151). Nothing in
 * this file types a planning figure: when the figures are not available the text says so and links to the section.
 *
 * prior-art-checked: no existing code reads law_facts (grep frontend-nextjs/ and services/, 2026-11-07). The nearest
 * surface is /api/sepp/parking-provisions (regulatory_provisions, parking cards); it holds none of the Chapter 5 figures.
 */

/** The only facts the website reads. A fact not listed here is not served. */
export const LAW_FACT_KEYS = [
  'tod_height_residential_flat_building_m',
  'tod_height_seniors_or_shop_top_m',
  'tod_fsr',
  'lmr_outer_distance',
  'lmr_inner_distance',
  'accessible_area_rail_distance',
  'accessible_area_bus_distance',
  'accessible_area_bus_min_per_hour',
] as const;

export type LawFactKey = (typeof LAW_FACT_KEYS)[number];

/** Families of facts served by key prefix: one fact per section of the law, so the list is whatever the saved law contains. */
export const LAW_FACT_PREFIXES = ['parking_min_', 'tod_affordable_parking_'] as const;

export interface LawFact {
  value: number | string;
  unit: string | null;
  clause: string;
  pdfPage: number;
  quote: string;
  lawVersionDate: string;
  /** What the extractor recorded beside the figure: for a parking minimum, the section heading and the subsection it sits in. */
  extra?: Record<string, unknown>;
}

export type LawFacts = Partial<Record<string, LawFact>>;

export interface LawFactsResponse {
  available: boolean;
  instrument: string;
  facts: LawFacts;
}

/** A row of the law_facts table as the route selects it. */
export interface LawFactRow {
  fact_key: string;
  value: unknown;
  value_number: string | number | null;
  unit: string | null;
  clause: string;
  pdf_page: number;
  quote: string;
  law_version_date: string | Date;
  extra?: unknown;
}

const isoDate = (d: string | Date): string => (d instanceof Date ? d.toISOString().slice(0, 10) : String(d).slice(0, 10));

/**
 * Turn table rows into the served facts. A row with no usable value is dropped (never served as 0 or empty), and a key the
 * website does not read is ignored.
 */
export function rowsToFacts(rows: LawFactRow[]): LawFacts {
  const out: LawFacts = {};
  for (const r of rows) {
    const wanted = (LAW_FACT_KEYS as readonly string[]).includes(r.fact_key) || LAW_FACT_PREFIXES.some((p) => r.fact_key.startsWith(p));
    if (!wanted) continue;
    const n = r.value_number == null ? null : Number(r.value_number);
    const value = typeof r.value === 'string' && r.value?.trim() !== '' ? r.value : n != null && Number.isFinite(n) ? n : null;
    if (value == null || !r.clause || !r.pdf_page || !r.quote) continue;
    out[r.fact_key] = {
      value,
      unit: r.unit,
      clause: r.clause,
      pdfPage: Number(r.pdf_page),
      quote: r.quote,
      lawVersionDate: isoDate(r.law_version_date),
      extra: r.extra && typeof r.extra === 'object' ? (r.extra as Record<string, unknown>) : undefined,
    };
  }
  return out;
}

/**
 * The sentence the TOD panel shows for section 155's height and floor space ratio standards, built from the stored figures.
 * Returns null when any of the three is missing, so the caller falls back to a sentence with no numbers in it.
 */
export function todStandardsSentence(facts: LawFacts | null | undefined): string | null {
  const rfb = facts?.tod_height_residential_flat_building_m;
  const other = facts?.tod_height_seniors_or_shop_top_m;
  const fsr = facts?.tod_fsr;
  if (!rfb || !other || !fsr) return null;
  return (
    'Section 155 identifies height and floor space ratio standards that differ by what is proposed — ' +
    `${rfb.value}m for a residential flat building (${rfb.clause}, page ${rfb.pdfPage}), ` +
    `${other.value}m for seniors or shop top housing (${other.clause}, page ${other.pdfPage}), and a floor space ratio of ` +
    `${fsr.value} for those types in a relevant residential or employment zone (${fsr.clause}, page ${fsr.pdfPage}). ` +
    `Law as at ${rfb.lawVersionDate}.`
  );
}

/**
 * The distances in the law's definition of "accessible area" (Schedule 10 dictionary): walking distance to a station entrance, a light rail
 * platform or a ferry wharf, and walking distance to a bus stop with a regular service. Null unless BOTH distances were read, so a caller
 * that gets null makes no distance claim at all.
 */
export function accessibleAreaLimits(
  facts: LawFacts | null | undefined,
): { railM: number; busM: number; busPerHour: number | null; clause: string; pdfPage: number; lawVersionDate: string } | null {
  const rail = facts?.accessible_area_rail_distance;
  const bus = facts?.accessible_area_bus_distance;
  if (!rail || !bus) return null;
  const railM = Number(rail.value);
  const busM = Number(bus.value);
  if (!Number.isFinite(railM) || !Number.isFinite(busM) || railM <= 0 || busM <= 0) return null;
  const perHour = Number(facts?.accessible_area_bus_min_per_hour?.value);
  const busPerHour = Number.isFinite(perHour) && perHour > 0 ? perHour : null;
  return { railM, busM, busPerHour, clause: 'Schedule 10 dictionary, accessible area', pdfPage: rail.pdfPage, lawVersionDate: rail.lawVersionDate };
}

export interface ParkingRate {
  key: string;
  label: string;
  rate: number;
  clause: string;
  pdfPage: number;
  lawVersionDate: string;
}

/**
 * Chapter 6 parking minimums per dwelling, one for each section of the law that states one. The development form is read from the stored
 * section heading and subsection text (never typed here); a rate with no usable figure is dropped. Empty when none are stored, so the page
 * then shows no parking rate at all.
 */
export function reformParkingRates(facts: LawFacts | null | undefined): ParkingRate[] {
  const out: ParkingRate[] = [];
  for (const [key, f] of Object.entries(facts ?? {})) {
    if (!f || !key.startsWith('parking_min_')) continue;
    const rate = Number(f.value);
    if (!Number.isFinite(rate) || rate <= 0) continue;
    const applies = String(f.extra?.applies_to ?? '');
    const heading = String(f.extra?.section_heading ?? '');
    const purposes = /purposes of ([^—]+?)\s*—/.exec(applies)?.[1]?.trim();
    const tail = heading.includes('—') ? heading.slice(heading.indexOf('—') + 1).trim() : heading.trim();
    const label = purposes || tail;
    if (!label) continue;
    out.push({ key, label, rate, clause: f.clause, pdfPage: f.pdfPage, lawVersionDate: f.lawVersionDate });
  }
  return out.sort((a, b) => a.pdfPage - b.pdfPage || a.key.localeCompare(b.key));
}

export interface TodParkingRate {
  key: string;
  bedrooms: number;
  orMore: boolean;
  rate: number;
  clause: string;
  pdfPage: number;
  lawVersionDate: string;
}

/**
 * Chapter 5 affordable-housing parking per dwelling, by bedroom count, read ONLY from the stored law facts (`tod_affordable_parking_<n>_bed`,
 * `..._<n>_plus_bed`). Empty when the facts are missing, so the page then shows no figure rather than one from another source.
 */
export function todAffordableParkingRates(facts: LawFacts | null | undefined): TodParkingRate[] {
  const out: TodParkingRate[] = [];
  for (const [key, f] of Object.entries(facts ?? {})) {
    const m = /^tod_affordable_parking_(\d+)(_plus)?_bed$/.exec(key);
    if (!f || !m) continue;
    const rate = Number(f.value);
    if (!Number.isFinite(rate) || rate <= 0) continue;
    out.push({ key, bedrooms: Number(m[1]), orMore: Boolean(m[2]), rate, clause: f.clause, pdfPage: f.pdfPage, lawVersionDate: f.lawVersionDate });
  }
  return out.sort((a, b) => a.bedrooms - b.bedrooms);
}

/** The sentence shown when the stored figures could not be read. It contains no figure. */
export const TOD_STANDARDS_UNAVAILABLE =
  'Section 155 identifies height and floor space ratio standards that differ by what is proposed. ' +
  'The stored figures could not be read just now; they are in the section itself, linked below.';
