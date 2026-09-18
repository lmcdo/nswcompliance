/**
 * DQ-78 at the display boundary: 111 served provisions carry street labels lifted off a
 * map figure and interleaved into the prose. Until the extractor can separate them, the
 * reader is told which characters came off the figure instead of being shown nonsense
 * that reads like a control.
 *
 * The hard rule these tests defend is the ledger's: DO NOT hide these rows. Rows near the
 * detection cut carry binding controls alongside the scramble, so a change that drops or
 * blanks them would hide controls — the harmful direction.
 *
 * prior-art-checked (2026-09-18): no existing test covers scrambled/map text at display.
 * `__tests__/lib/provision-grouping.test.ts` groups provisions, `dcp-citation-links.test.ts`
 * covers citation links, `lib/see/provisionUtils.test.ts` covers SEE intake; grep for
 * "scramble", "map label" and "single letter" across __tests__ returns nothing else.
 */
import {
  hasInterleavedMapText,
  isMapScrambledLine,
  mapScrambleRatio,
  MAP_SCRAMBLE_MIN_RATIO,
  MAP_SCRAMBLE_MIN_TOKENS,
} from '@/lib/provision-text-formatter';

/** Real shape of a City of Sydney Section 2 locality page: street names one glyph at a time. */
const SCRAMBLED =
  'Zen B H i i t a n h S n d S in fi t g e r e S ld y e tr s t ee S t t d ree E t n l A e li y s o h t P t m A a v r o enu k e r e R S oa t M r F o d i x e t B c A u e h v r e r t e o ll w n R s u o R e a o d ad ' +
  'W a l k e r S t r e e t B o u n d a r y S t r e e t C r o w n S t r e e t R i l e y S t r e e t B o u r k e S t r e e t';

/** A normal control from the same council, of comparable length. */
const PROSE =
  'This locality is bounded by Ashmore Street to the north, the rail corridor to the east, ' +
  'Coulson Street to the south and Mitchell Road to the west. Development is to provide active ' +
  'frontages at ground level along Ashmore Street and to maintain the existing pattern of ' +
  'subdivision. Buildings are to be no more than 9.5 metres in height above existing ground level ' +
  'and are to be set back at least 3 metres from the primary street boundary in accordance with ' +
  'the setback diagram for this locality shown in Figure 2.14 of this section of the plan.';

describe('mapScrambleRatio', () => {
  it('is near zero for ordinary prose', () => {
    expect(mapScrambleRatio(PROSE)).toBeLessThan(0.05);
  });

  it('is high for interleaved map labels', () => {
    expect(mapScrambleRatio(SCRAMBLED)).toBeGreaterThan(MAP_SCRAMBLE_MIN_RATIO);
  });

  it('does not divide by zero on empty text', () => {
    expect(mapScrambleRatio('')).toBe(0);
    expect(mapScrambleRatio('   ')).toBe(0);
  });
});

describe('hasInterleavedMapText', () => {
  it('flags the scrambled locality text', () => {
    expect(hasInterleavedMapText(SCRAMBLED)).toBe(true);
  });

  it('leaves ordinary provisions alone', () => {
    expect(hasInterleavedMapText(PROSE)).toBe(false);
  });

  it('ignores short text however odd it looks', () => {
    // DQ-77's territory, not DQ-78's: "900 m m" is a split unit, not a map.
    expect(hasInterleavedMapText('Minimum 900 m m side setback')).toBe(false);
  });

  it('needs the token floor, not just the ratio', () => {
    const shortButLettery = 'a b c d e f g h i j k l m n o p q r s t u v w x y z '.repeat(1);
    expect(shortButLettery.trim().split(/\s+/).length).toBeLessThan(MAP_SCRAMBLE_MIN_TOKENS);
    expect(hasInterleavedMapText(shortButLettery)).toBe(false);
  });

  it('is false for null-ish input rather than throwing', () => {
    expect(hasInterleavedMapText('')).toBe(false);
    expect(hasInterleavedMapText(undefined as unknown as string)).toBe(false);
  });
});

describe('isMapScrambledLine', () => {
  it('marks a figure line', () => {
    expect(isMapScrambledLine('B o u n d a r y S t r e e t C r o w n S t r e e t')).toBe(true);
  });

  it('leaves a real control line unmarked — the line that must never be dimmed', () => {
    // Verbatim from the DQ-78 note: rows near the cut carry controls like these.
    expect(
      isMapScrambledLine('This locality is bounded by Ashmore Street to the north')
    ).toBe(false);
    expect(
      isMapScrambledLine('Building heights are to comply with Figure 6.1')
    ).toBe(false);
    expect(
      isMapScrambledLine(
        'Ensure that the safety and amenity of pedestrians and cyclists is not compromised by off-street parking access points'
      )
    ).toBe(false);
  });

  it('does not mark a short line that happens to contain single letters', () => {
    expect(isMapScrambledLine('Zone R2 a b')).toBe(false);
  });
});
