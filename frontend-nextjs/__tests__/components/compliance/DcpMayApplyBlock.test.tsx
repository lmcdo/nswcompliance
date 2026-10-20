import React from 'react';
import { render, screen } from '@testing-library/react';
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

  it('prints no empty page citation when the page is missing', () => {
    render(<DcpMayApplyBlock mayApply={[{ ...area(), applies_to_page: null }]} />);
    const text = screen.getByTestId('dcp-may-apply-block').textContent ?? '';
    expect(text).not.toMatch(/\(page \)/);
  });
});
