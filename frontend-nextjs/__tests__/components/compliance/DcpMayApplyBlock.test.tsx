import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { DcpMayApplyBlock, type MayApplyArea } from '@/components/compliance/DcpMayApplyBlock';
import type { Provision } from '@/components/compliance/PageGroupedProvisions';

const rule = (id: number, text: string, page?: number): Provision =>
  ({ id, provision_text: text, v2_dcp_layer: 'dcp', pdf_page: page }) as Provision;

const area = (over: Partial<MayApplyArea> = {}): MayApplyArea => ({
  area_id: 'a1',
  title: 'Winston Hills Precinct',
  reason_code: 'WORDS_ONLY',
  reason_text: 'The plan describes this area in words only, with no map.',
  applies_to_quote: 'land bounded by the railway',
  applies_to_page: 12,
  suburb: 'WINSTON HILLS',
  provisions: [rule(1, 'Setback 6m.', 5), rule(2, 'Height 9m.')],
  ...over,
});

describe('DcpMayApplyBlock', () => {
  it('renders nothing for null, undefined or empty', () => {
    expect(render(<DcpMayApplyBlock mayApply={null} />).container).toBeEmptyDOMElement();
    expect(render(<DcpMayApplyBlock mayApply={undefined} />).container).toBeEmptyDOMElement();
    expect(render(<DcpMayApplyBlock mayApply={[]} />).container).toBeEmptyDOMElement();
  });

  it('renders one collapsed details per area with the summary and body', () => {
    render(<DcpMayApplyBlock mayApply={[area(), area({ area_id: 'a2', title: 'Other Area', provisions: [rule(3, 'X')] })]} />);
    const areas = screen.getAllByTestId('dcp-may-apply-area') as HTMLDetailsElement[];
    expect(areas).toHaveLength(2);
    expect(areas[0].open).toBe(false);
    const text = areas[0].textContent ?? '';
    expect(text).toContain('Rules for Winston Hills Precinct may apply to this property (2 rules)');
    expect(text).toContain('This property is in WINSTON HILLS. We can’t tell whether it is inside this area.');
    expect(text).toContain('The plan says: “land bounded by the railway” (page 12).');
    expect(text).toContain('we have not been able to check that they cover this address.');
    expect(areas[1].textContent).toContain('(1 rule)');
    expect(screen.getAllByTestId('dcp-may-apply-rule')).toHaveLength(3);
  });

  it('shows each rule text and a page reference when it has one', () => {
    render(<DcpMayApplyBlock mayApply={[area()]} />);
    const rules = screen.getAllByTestId('dcp-may-apply-rule');
    expect(rules[0].textContent).toContain('Setback 6m.');
    expect(rules[0].textContent).toMatch(/page/i);
    expect(rules[1].textContent).toBe('Height 9m.');
  });

  it('uses no assurance words', () => {
    render(<DcpMayApplyBlock mayApply={[area()]} />);
    const text = screen.getByTestId('dcp-may-apply-block').textContent ?? '';
    expect(text).not.toMatch(/\b(safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|approved|guaranteed|certified|verified|ensure|accurate|definitive|comprehensive|reliable)\b/i);
  });

  it('says the rules could not be loaded when the list is missing, instead of "0 rules"', () => {
    render(<DcpMayApplyBlock mayApply={[{ ...area(), provisions: null }]} />);
    const text = screen.getByTestId('dcp-may-apply-block').textContent ?? '';
    expect(text).toMatch(/couldn.t load the rules/);
    expect(text).not.toMatch(/\(0 rules\)/);
  });

  describe('plan map link', () => {
    const withUrl = (url: string | undefined, over: Partial<MayApplyArea> = {}) =>
      render(<DcpMayApplyBlock address="1 A St" mayApply={[area({ chapter_key: 'c1', ...over })]} chapterPdfUrls={url ? { c1: url } : {}} />);

    it('opens the pdf at the area page', () => {
      withUrl('https://x.test/plan.pdf');
      expect(screen.getByTestId('dcp-may-apply-map-link').getAttribute('href')).toBe('https://x.test/plan.pdf#page=12');
      expect(screen.getByTestId('dcp-may-apply-map-link').textContent).toContain('(page 12)');
    });
    it('shows a lazy thumbnail linking to the pdf page only when the area has a map image', () => {
      withUrl('https://x.test/plan.pdf', { map_image_url: 'https://img.test/a1.png' });
      const img = screen.getByTestId('dcp-may-apply-map-thumb') as HTMLImageElement;
      expect(img.getAttribute('src')).toBe('https://img.test/a1.png');
      expect(img.getAttribute('loading')).toBe('lazy');
      expect(img.getAttribute('alt')).toBe('The plan’s map of Winston Hills Precinct, page 12');
      expect(img.closest('a')?.getAttribute('href')).toBe('https://x.test/plan.pdf#page=12');
      cleanup();
      withUrl('https://x.test/plan.pdf');
      expect(screen.queryByTestId('dcp-may-apply-map-thumb')).toBeNull();
      expect(screen.getByTestId('dcp-may-apply-map-link')).toBeTruthy();
    });
    it('has no link without a url', () => {
      withUrl(undefined);
      expect(screen.queryByTestId('dcp-may-apply-map-link')).toBeNull();
    });
    it('adds no anchor to a url that has a # or is not a pdf, or when the page is missing', () => {
      withUrl('https://x.test/plan.pdf#zoom=50');
      expect(screen.getByTestId('dcp-may-apply-map-link').getAttribute('href')).toBe('https://x.test/plan.pdf#zoom=50');
      cleanup();
      withUrl('https://x.test/plan.html');
      expect(screen.getByTestId('dcp-may-apply-map-link').getAttribute('href')).toBe('https://x.test/plan.html');
      cleanup();
      withUrl('https://x.test/plan.pdf', { applies_to_page: null });
      expect(screen.getByTestId('dcp-may-apply-map-link').getAttribute('href')).toBe('https://x.test/plan.pdf');
    });
  });

  describe('the reader’s answer', () => {
    beforeEach(() => window.localStorage.clear());
    const open = () => render(<DcpMayApplyBlock address="1 A St" mayApply={[area()]} />);

    it('in: expands and says so, as the reader’s own words', () => {
      open();
      fireEvent.click(screen.getByRole('button', { name: 'My property is in this area' }));
      const a = screen.getByTestId('dcp-may-apply-area') as HTMLDetailsElement;
      expect(a.open).toBe(true);
      expect(a.textContent).toContain('You said your property is in this area — these rules apply to it');
      expect(window.localStorage.getItem('dcp-may-apply:v1:1 A St:a1')).toBe('in');
    });
    it('out: collapses to one line with Change, which restores the area', () => {
      open();
      fireEvent.click(screen.getByRole('button', { name: 'My property is not in this area' }));
      expect(screen.queryByTestId('dcp-may-apply-rule')).toBeNull();
      expect(screen.getByTestId('dcp-may-apply-area-out').textContent).toContain('You said your property is not in this area.');
      fireEvent.click(screen.getByRole('button', { name: 'Change' }));
      expect(screen.getAllByTestId('dcp-may-apply-rule')).toHaveLength(2);
    });
    it('remembers the answer for the same address only', () => {
      window.localStorage.setItem('dcp-may-apply:v1:1 A St:a1', 'out');
      open();
      expect(screen.getByTestId('dcp-may-apply-area-out')).toBeTruthy();
      cleanup();
      render(<DcpMayApplyBlock address="2 B St" mayApply={[area()]} />);
      expect(screen.getByTestId('dcp-may-apply-area')).toBeTruthy();
    });
    it('not sure is the default and reads as today', () => {
      open();
      expect((screen.getByTestId('dcp-may-apply-area') as HTMLDetailsElement).open).toBe(false);
      expect(screen.getByTestId('dcp-may-apply-area').textContent).toContain('may apply to this property (2 rules)');
    });
    it('still renders and answers when localStorage throws', () => {
      const boom = jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
      const set = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
      open();
      fireEvent.click(screen.getByRole('button', { name: 'My property is not in this area' }));
      expect(screen.getByTestId('dcp-may-apply-area-out')).toBeTruthy();
      boom.mockRestore();
      set.mockRestore();
    });
  });

  it('collapses the whole box with a count when there are more than three areas', () => {
    const many = [1, 2, 3, 4].map((i) => area({ area_id: `m${i}` }));
    render(<DcpMayApplyBlock address="1 A St" mayApply={many} />);
    const box = screen.getByTestId('dcp-may-apply-block') as HTMLDetailsElement;
    expect(box.tagName).toBe('DETAILS');
    expect(box.open).toBe(false);
    expect(box.textContent).toContain('(4)');
  });

  it('prints no empty page citation when the page is missing', () => {
    render(<DcpMayApplyBlock mayApply={[{ ...area(), applies_to_page: null }]} />);
    const text = screen.getByTestId('dcp-may-apply-block').textContent ?? '';
    expect(text).not.toMatch(/\(page \)/);
  });
});
