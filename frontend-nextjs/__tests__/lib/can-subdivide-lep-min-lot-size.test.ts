/**
 * Subdivision rules are hidden only against the LEP minimum lot size the lookup returned,
 * never a typed figure. Before 2026-10-26 `canSubdivide` hid them below a hard-coded 450 m²
 * ("Inner West") for every council (code-quality review, served rules finding 5).
 */
import { canSubdivide } from '@/lib/requirement-prioritization';

describe('canSubdivide uses the LEP minimum lot size', () => {
  it('shows subdivision rules for a 300 m² lot where the LEP minimum is 200 m²', () => {
    expect(canSubdivide(300, 200)).toBe(true);
  });

  it('hides them for a 500 m² lot where the LEP minimum is 600 m²', () => {
    expect(canSubdivide(500, 600)).toBe(false);
  });

  it('shows them when the LEP minimum is unknown, whatever the lot size', () => {
    expect(canSubdivide(100, null)).toBe(true);
    expect(canSubdivide(100, undefined)).toBe(true);
  });

  it('shows them when the lot size is unknown', () => {
    expect(canSubdivide(undefined, 600)).toBe(true);
    expect(canSubdivide('no number here', 600)).toBe(true);
  });

  it('treats a zero or negative area as unknown', () => {
    expect(canSubdivide('0 square metres', 600)).toBe(true);
    expect(canSubdivide(-5, 600)).toBe(true);
  });

  it('parses a text area', () => {
    expect(canSubdivide('228.1 square metres', 300)).toBe(false);
  });
});
