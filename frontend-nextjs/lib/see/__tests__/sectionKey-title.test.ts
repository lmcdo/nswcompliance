/**
 * deriveSectionTitleFromProvision — a DCP section must be labelled with the
 * heading the document gives it, or with nothing but its number. Never with a
 * string assembled from somewhere else.
 *
 * Every case below is a real row. Measured 2026-10-08: of 19,219 served DCP
 * provisions carrying a section_header, the previous all-caps-only test matched
 * 59. The other 17,788 returned the bare section number, and
 * ProvisionsByTocStructure then substituted the chapter slug — so Cumberland
 * rendered nineteen different sections as "2.1x Cumberland Dcp Part B
 * Residential" while their real headings sat in the same rows.
 *
 * The planted failure is `rejects the bare section number for a mixed-case
 * header`: it passes only because the mixed-case branch exists. Delete that
 * branch and it fails, which is what makes the rest of this file worth running.
 */

import { deriveSectionTitleFromProvision } from '../sectionKey';

type Row = Parameters<typeof deriveSectionTitleFromProvision>[0];

const row = (toc_section_number: string | null, section_header: string | null): Row =>
  ({ toc_section_number, section_header } as Row);

describe('deriveSectionTitleFromProvision', () => {
  describe('the heading the document actually prints', () => {
    // Real Cumberland rows, regulatory_provisions, chapter
    // cumberland-dcp-part-b-residential.
    it.each([
      ['2.10', '2.10 Visual and acoustic privacy Objectives', '2.10 Visual and acoustic privacy Objectives'],
      ['2.11', '2.11 Solar access Objectives', '2.11 Solar access Objectives'],
      ['2.14', '2.14 Fencing Objectives', '2.14 Fencing Objectives'],
      ['2.19', '2.19 Garages and carports Control', '2.19 Garages and carports Control'],
      ['2.21', '2.21 Secondary dwellings Objectives', '2.21 Secondary dwellings Objectives'],
    ])('%s -> %s', (secNum, header, expected) => {
      expect(deriveSectionTitleFromProvision(row(secNum, header))).toBe(expected);
    });

    it('does not print the section number twice', () => {
      const title = deriveSectionTitleFromProvision(
        row('2.10', '2.10 Visual and acoustic privacy Objectives'),
      );
      expect(title).not.toMatch(/^2\.10\s+2\.10/);
      expect((title!.match(/2\.10/g) ?? []).length).toBe(1);
    });

    it('keeps mixed-case wording verbatim rather than recasing it', () => {
      // "Garages And Carports" would be a rewrite of the source. Only all-caps
      // headings get recased, because there the original case is absent anyway.
      expect(deriveSectionTitleFromProvision(row('2.19', '2.19 Garages and carports Control')))
        .toBe('2.19 Garages and carports Control');
    });

    it('strips a number separated by a dash or colon, not just a space', () => {
      expect(deriveSectionTitleFromProvision(row('C1.2', 'C1.2 — Demolition and site works')))
        .toBe('C1.2 Demolition and site works');
      expect(deriveSectionTitleFromProvision(row('3.1', '3.1: Building envelope')))
        .toBe('3.1 Building envelope');
    });

    it('leaves a leading number that is NOT this section\'s own number alone', () => {
      // Only the provision's own number may be stripped, so a heading that
      // genuinely opens with a different figure keeps it.
      expect(deriveSectionTitleFromProvision(row('2.5', '1.8 m fence height at the street')))
        .toBe('2.5 1.8 m fence height at the street');
    });
  });

  describe('the all-caps heading path, unchanged', () => {
    it('recases a full-caps heading and keeps articles lower', () => {
      expect(deriveSectionTitleFromProvision(row('C1.2', 'DEMOLITION'))).toBe('C1.2 Demolition');
      expect(deriveSectionTitleFromProvision(row('C2', 'URBAN CHARACTER AND THE PUBLIC DOMAIN')))
        .toBe('C2 Urban Character and the Public Domain');
    });
  });

  describe('when there is no usable heading, the number stands alone', () => {
    it('returns the section number for an empty or absent header', () => {
      expect(deriveSectionTitleFromProvision(row('2.10', ''))).toBe('2.10');
      expect(deriveSectionTitleFromProvision(row('2.10', null))).toBe('2.10');
    });

    it('returns the section number when the header is only that number', () => {
      expect(deriveSectionTitleFromProvision(row('2.10', '2.10'))).toBe('2.10');
      expect(deriveSectionTitleFromProvision(row('2.10', '2.10 —'))).toBe('2.10');
    });

    it('returns null without a section number, so nothing is invented', () => {
      expect(deriveSectionTitleFromProvision(row(null, 'Visual and acoustic privacy'))).toBeNull();
      expect(deriveSectionTitleFromProvision(row('', 'Visual and acoustic privacy'))).toBeNull();
    });
  });

  describe('planted failure — this is the regression that shipped', () => {
    it('rejects the bare section number for a mixed-case header', () => {
      // Returning "2.10" here is precisely what let the chapter slug through,
      // producing "2.10 Cumberland Dcp Part B Residential" on screen. Any change
      // that makes this return the bare number reintroduces that defect for
      // 17,788 served provisions.
      const title = deriveSectionTitleFromProvision(
        row('2.10', '2.10 Visual and acoustic privacy Objectives'),
      );
      expect(title).not.toBe('2.10');
      expect(title).toContain('Visual and acoustic privacy');
    });

    it('never labels a section with its chapter name', () => {
      // The chapter slug title is wrong for every section in the chapter, so a
      // real heading must always win over it.
      const chapterName = 'Cumberland Dcp Part B Residential';
      for (const [secNum, header] of [
        ['2.10', '2.10 Visual and acoustic privacy Objectives'],
        ['2.11', '2.11 Solar access Objectives'],
        ['2.12', '2.12 Cross ventilation Objectives'],
      ] as const) {
        expect(deriveSectionTitleFromProvision(row(secNum, header))).not.toContain(chapterName);
      }
    });
  });

  describe('a header that reads like body text is still the text at that page', () => {
    it('shows it rather than falling back to something assembled', () => {
      // 1 row in 19,219 (2026-10-08) carries an extraction artifact. Showing it
      // is honest about what is on that page; the chapter slug never was. Every
      // served row has a pdf_page, so a reader can check it.
      expect(deriveSectionTitleFromProvision(row('2.2', '2.2 Housing Mix B53 This page has been left intentionally blank')))
        .toBe('2.2 Housing Mix B53 This page has been left intentionally blank');
    });
  });
});
