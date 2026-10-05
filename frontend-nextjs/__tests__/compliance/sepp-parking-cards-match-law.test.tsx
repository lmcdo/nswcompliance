/**
 * The SEPP (Housing) 2021 parking cards against the instrument in force.
 *
 * Every string asserted here was read on 2026-10-05 from the whole-instrument PDF,
 * "Current version for 11 September 2026 to date" (epi-2021-0714, 186 pages). Three
 * cards disagreed with it:
 *
 *   build-to-rent      showed per-bedroom tiers (0.2 / 0.5 / 1 per dwelling). s74(2)(d)
 *                      page 61 sets a flat per-dwelling rate, binding only in a
 *                      designated Sydney local government area, and (e) hands the rate
 *                      to the council's own plan everywhere else.
 *   in-fill affordable showed 0.2 / 0.5 per dwelling, which is the build-to-rent rate.
 *                      s22A page 25 sets per-bedroom tiers that differ for affordable
 *                      and non-affordable dwellings, as one of two alternatives.
 *   TOD affordable     had the right numbers under the wrong heading: s157 page 114
 *                      attaches no accessible-area condition to them.
 *
 * This is a TEXT test, not a data test. s22A is in no `regulatory_provisions` row (0
 * rows, measured 2026-10-05) because our stored copy of this instrument stops at page
 * 120 of 186, so these words cannot come from the database yet. That is the whole
 * reason the strings are pinned here: nothing else in the repo can notice if someone
 * edits them. When a text refresh lands s22A, these cards move to
 * /api/sepp/parking-provisions and this file is replaced by the resolver's own tests.
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const SOURCE = readFileSync(
  join(__dirname, '..', '..', 'components', 'compliance', 'StateLevelControls.tsx'),
  'utf8',
);

/**
 * Strip comments, then slice the file into one block per card.
 *
 * The first version of this file matched against the whole raw source. Two things were
 * wrong with that, both raised by cross-review. A rate moved from one card to another
 * would still be found, so the suite proved the string existed somewhere and not that
 * the named card renders it — and a positive assertion could be satisfied by a comment,
 * including the comments this change added to explain the rates. Both are the shape of
 * defect the suite exists to catch, so it had to stop reading the file as one blob.
 *
 * Blocks are cut on each card's own heading, which is the string a reader sees. A card
 * whose heading is renamed or removed therefore fails loudly rather than silently
 * widening someone else's block.
 */
const RENDERED_ONLY = SOURCE
  .replace(/\{\s*\/\*[\s\S]*?\*\/\s*\}/g, ' ')
  .replace(/\/\*[\s\S]*?\*\//g, ' ')
  .replace(/^\s*\/\/.*$/gm, ' ');

const CARD_HEADINGS = [
  'Boarding Houses',
  'Co-Living Housing',
  'Build-to-Rent Housing',
  'In-Fill Affordable Housing',
  'Seniors Independent Living',
  'Affordable Housing in TOD Areas',
  'Residential Flat Buildings & Apartments',
] as const;

/** The rendered source belonging to one card, from its heading to the next card's. */
function cardBlock(heading: string): string {
  const start = RENDERED_ONLY.indexOf(`>${heading}<`);
  if (start === -1) {
    throw new Error(
      `Card heading "${heading}" is not in the rendered markup of StateLevelControls.tsx. `
      + 'Either the card was removed or its heading changed; both need a deliberate look, '
      + 'because every assertion in this file is scoped by heading.',
    );
  }
  const laterStarts = CARD_HEADINGS
    .map((h) => RENDERED_ONLY.indexOf(`>${h}<`, start + 1))
    .filter((i) => i > start);
  const end = laterStarts.length ? Math.min(...laterStarts) : RENDERED_ONLY.length;
  return RENDERED_ONLY.slice(start, end).replace(/\s+/g, ' ');
}

/** True when THIS card renders the text — not merely that the file contains it. */
const cardHas = (heading: string, s: string) =>
  cardBlock(heading).includes(s.replace(/\s+/g, ' '));

/**
 * The whole rendered markup, whitespace collapsed, for the few assertions that are
 * about the file rather than one card.
 *
 * Comments are excluded for the same reason they are excluded from `cardBlock`: the
 * currency assertion below is about what a READER sees, and an earlier draft of it
 * scanned raw source and failed on this change's own provenance comments, which cite
 * the PDF's "Current version for 11 September 2026" as the source of every string
 * here. That would have forced the edition and page numbers out of the code to satisfy
 * a test about the UI.
 */
const RENDERED = RENDERED_ONLY.replace(/\s+/g, ' ');

describe('build-to-rent — s74(2)(d)-(e), page 61', () => {
  it('states the flat per-dwelling rate the section actually sets', () => {
    expect(cardHas('Build-to-Rent Housing', 'within an accessible area: at least 0.2 parking spaces for each dwelling')).toBe(true);
    expect(cardHas('Build-to-Rent Housing', 'otherwise: at least 0.5 parking spaces for each dwelling')).toBe(true);
  });

  it('carries the designated-Sydney-LGA condition the rate depends on', () => {
    // Without this the card states a standard that binds nationwide. It does not.
    expect(cardHas('Build-to-Rent Housing', 'In a designated Sydney local government area:')).toBe(true);
  });

  it('carries paragraph (e) — the council rate that applies elsewhere', () => {
    expect(cardHas('Build-to-Rent Housing', 'at least the number of parking spaces required under the relevant development control plan or local environmental plan for a residential flat building')).toBe(true);
  });

  it('carries the lower-number override in paragraph (d)(iii)', () => {
    expect(cardHas('Build-to-Rent Housing', 'where a relevant planning instrument specifies a lower number, that lower number')).toBe(true);
  });

  it('no longer shows the per-bedroom tiers that are not in s74', () => {
    // The exact strings the card carried until 2026-10-05.
    expect(cardHas('Build-to-Rent Housing', '1 bedroom: 0.2 parking spaces per dwelling')).toBe(false);
    expect(cardHas('Build-to-Rent Housing', '2 bedrooms: 0.5 parking spaces per dwelling')).toBe(false);
    expect(cardHas('Build-to-Rent Housing', '3+ bedrooms: 1 parking space per dwelling')).toBe(false);
  });

  it('cites section 74 and deep-links to it', () => {
    expect(cardHas('Build-to-Rent Housing', 'section 74(2)(d)–(e)')).toBe(true);
    expect(cardHas('Build-to-Rent Housing', "seppHousingProvisionUrl('sec.74')")).toBe(true);
  });
});

describe('in-fill affordable housing — s22A, page 25', () => {
  it('states the affordable-dwelling tiers verbatim', () => {
    expect(cardHas('In-Fill Affordable Housing', '1 bedroom: at least 0.4 parking spaces')).toBe(true);
    expect(cardHas('In-Fill Affordable Housing', '2 bedrooms: at least 0.5 parking spaces')).toBe(true);
    expect(cardHas('In-Fill Affordable Housing', '3 or more bedrooms: at least 1 parking space')).toBe(true);
  });

  it('states the separate tiers for the non-affordable dwellings', () => {
    // s22A(a)(ii). A card showing only (a)(i) would understate the parking required
    // for the market dwellings in the same development.
    expect(cardHas('In-Fill Affordable Housing', 'Dwellings not used for affordable housing:')).toBe(true);
    expect(cardHas('In-Fill Affordable Housing', '1 bedroom: at least 0.5 parking spaces')).toBe(true);
    expect(cardHas('In-Fill Affordable Housing', '2 bedrooms: at least 1 parking space')).toBe(true);
    expect(cardHas('In-Fill Affordable Housing', '3 or more bedrooms: at least 1.5 parking spaces')).toBe(true);
  });

  it('says the numbers are one of two alternatives, which is what the section says', () => {
    // s22A is "(a) ... or (b) the consent authority has considered the Guide to
    // Transport Impact Assessment". Numbers alone would state a requirement the
    // section does not impose on its own.
    expect(cardHas('In-Fill Affordable Housing', 'consent must not be granted unless either these parking rates are provided or the consent authority has considered')).toBe(true);
    expect(cardHas('In-Fill Affordable Housing', 'Guide to Transport Impact Assessment published by Transport for NSW on 4 November 2024')).toBe(true);
  });

  it('no longer shows the build-to-rent rate it had borrowed', () => {
    expect(cardHas('In-Fill Affordable Housing', 'In accessible area: 0.2 parking spaces per dwelling')).toBe(false);
    expect(cardHas('In-Fill Affordable Housing', 'Otherwise: 0.5 parking spaces per dwelling')).toBe(false);
  });

  it('cites section 22A instead of saying the section is unidentified', () => {
    expect(cardHas('In-Fill Affordable Housing', 'section 22A — requirement to provide car parking')).toBe(true);
    expect(cardHas('In-Fill Affordable Housing', "seppHousingProvisionUrl('sec.22A')")).toBe(true);
    expect(RENDERED_ONLY).not.toMatch(/section number not yet identified/);
  });
});

describe('affordable housing in TOD areas — s157, page 114', () => {
  it('keeps the rates, which were already right', () => {
    expect(cardHas('Affordable Housing in TOD Areas', '1 bedroom: 0.4 parking space')).toBe(true);
    expect(cardHas('Affordable Housing in TOD Areas', '2 bedrooms: 0.5 parking space')).toBe(true);
    expect(cardHas('Affordable Housing in TOD Areas', '3 or more bedrooms: 1 parking space')).toBe(true);
  });

  it('drops the accessible-area condition s157 does not impose', () => {
    expect(cardHas('Affordable Housing in TOD Areas', 'For each affordable housing dwelling required under section 156:')).toBe(true);
  });

  it('cites section 157 and deep-links to it', () => {
    expect(cardHas('Affordable Housing in TOD Areas', 'section 157 — affordable housing parking spaces')).toBe(true);
    expect(cardHas('Affordable Housing in TOD Areas', "seppHousingProvisionUrl('sec.157')")).toBe(true);
  });
});

describe('the three cards that were already correct are untouched', () => {
  it('boarding houses still quotes s24', () => {
    expect(cardHas('Boarding Houses', '0.2 parking spaces per boarding room')).toBe(true);
    expect(cardHas('Boarding Houses', "seppHousingProvisionUrl('sec.24')")).toBe(true);
  });

  it('co-living still quotes s68', () => {
    expect(cardHas('Co-Living Housing', '0.2 parking spaces per private room')).toBe(true);
    expect(cardHas('Co-Living Housing', "seppHousingProvisionUrl('sec.68')")).toBe(true);
  });

  it('seniors independent living still quotes s108', () => {
    expect(cardHas('Seniors Independent Living', '1 parking space per 5 dwellings')).toBe(true);
    expect(cardHas('Seniors Independent Living', "seppHousingProvisionUrl('sec.108')")).toBe(true);
  });
});

describe('no card claims a currency it cannot show', () => {
  it('does not state a version date in the rendered markup', () => {
    // The instrument's currency belongs to InstrumentCurrency.tsx, which reads
    // instrument_registry. A date typed into a card would be a second, unmonitored
    // source of truth, and would read as current forever. Comments are excluded:
    // recording WHICH version these words came from is the point of the comments.
    expect(RENDERED).not.toMatch(/11 September 2026/);
    expect(RENDERED).not.toMatch(/\bCurrent version for\b/);
  });

  it('keeps the provenance in the comments, where a reviewer will find it', () => {
    // The inverse of the assertion above, so "remove the date everywhere" cannot
    // satisfy that one. The source must still say which edition was read.
    expect(SOURCE).toMatch(/11 September 2026/);
    expect(SOURCE).toMatch(/page 25/);
    expect(SOURCE).toMatch(/page 61/);
    expect(SOURCE).toMatch(/page 114/);
  });
});
