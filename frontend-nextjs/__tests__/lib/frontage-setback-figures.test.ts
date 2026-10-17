import {
  frontageSetbackFigures,
  frontageSetbackNote,
  type FrontageFigureData,
} from '@/lib/frontage-setback-figures';

const data: FrontageFigureData = {
  council: 'ku_ring_gai',
  chapters: [
    {
      chapter_key: 'ch-14e',
      r2_path: 'r2/14e-v1.pdf',
      pdf_url: 'https://x/14e.pdf',
      figures: [
        { precinct_id: '14E_L3', page: 28, figure: '14E.9-6' },
        { precinct_id: '14E_L3', page: 28, figure: '14E.9-6' },
        { precinct_id: '14E_L1', page: 20, figure: '14E.9-1' },
        { precinct_id: null, page: 12, figure: null },
      ],
    },
    {
      chapter_key: 'ch-14c',
      r2_path: 'r2/14c-v1.pdf',
      pdf_url: 'https://x/14c.pdf',
      figures: [{ precinct_id: null, page: 9, figure: '14C.4' }],
    },
  ],
};
const paths = { 'ch-14e': 'r2/14e-v1.pdf', 'ch-14c': 'r2/14c-v1.pdf' };

describe('frontageSetbackFigures', () => {
  it('matches by precinct and dedupes by chapter+page', () => {
    const r = frontageSetbackFigures(data, 'ku_ring_gai', ['14E_L3'], paths, []);
    expect(r).toEqual([
      { chapter_key: 'ch-14e', page: 28, figure: '14E.9-6', pdf_url: 'https://x/14e.pdf#page=28' },
    ]);
  });

  it('applies null-precinct figures through the chapter, sorted by page', () => {
    const r = frontageSetbackFigures(data, 'ku_ring_gai', ['14E_L3'], paths, ['ch-14e']);
    expect(r.map((i) => i.page)).toEqual([12, 28]);
    expect(r[0].figure).toBeNull();
  });

  it('sorts by chapter then page', () => {
    const r = frontageSetbackFigures(data, 'ku_ring_gai', ['14E_L3'], paths, ['ch-14e', 'ch-14c']);
    expect(r.map((i) => `${i.chapter_key}:${i.page}`)).toEqual(['ch-14c:9', 'ch-14e:12', 'ch-14e:28']);
  });

  it('returns nothing when the chapter PDF has changed', () => {
    const r = frontageSetbackFigures(data, 'ku_ring_gai', ['14E_L3'], { 'ch-14e': 'r2/14e-v2.pdf' }, []);
    expect(r).toEqual([]);
    expect(frontageSetbackFigures(data, 'ku_ring_gai', ['14E_L3'], { 'ch-14e': null }, [])).toEqual([]);
  });

  it('returns nothing for another council or none', () => {
    expect(frontageSetbackFigures(data, 'parramatta', ['14E_L3'], paths, ['ch-14e'])).toEqual([]);
    expect(frontageSetbackFigures(data, null, ['14E_L3'], paths, ['ch-14e'])).toEqual([]);
  });

  it('does not apply other precincts', () => {
    expect(frontageSetbackFigures(data, 'ku_ring_gai', ['14E_L9'], paths, [])).toEqual([]);
  });
});

describe('frontageSetbackNote', () => {
  const head = 'Upper-level setbacks apply to some street frontages in this centre: ';
  it('is null for empty', () => {
    expect(frontageSetbackNote([])).toBeNull();
    expect(frontageSetbackNote(undefined)).toBeNull();
  });
  it('names one figure and page', () => {
    expect(
      frontageSetbackNote([{ chapter_key: 'a', page: 28, figure: '14E.9-6', pdf_url: 'u' }]),
    ).toBe(`${head}see Figure 14E.9-6, page 28`);
  });
  it('falls back to the page when the figure is unknown, and joins with "; "', () => {
    expect(
      frontageSetbackNote([
        { chapter_key: 'a', page: 12, figure: null, pdf_url: 'u' },
        { chapter_key: 'a', page: 28, figure: '14E.9-6', pdf_url: 'u' },
      ]),
    ).toBe(`${head}see page 12; Figure 14E.9-6, page 28`);
  });
});
