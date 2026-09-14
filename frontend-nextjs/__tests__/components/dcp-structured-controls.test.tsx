/**
 * Guards the DCP numeric-controls display against operator inversion.
 *
 * Bug (2026-07-15): max_site_coverage / max_height store their CEILING in
 * value_min, but formatValue rendered every value_min with "≥" — so a 65%
 * maximum site coverage displayed as "≥ 65%", the inverse of the control, on a
 * compliance surface, across 28 councils. Fix: controls carry a `direction`
 * ('max' → "≤", else "≥"), classified server-side by MAXIMUM_CONTROL_TYPES.
 */
import fs from 'fs';
import path from 'path';
import { formatValue, noNumberLabel } from '@/components/compliance/DcpStructuredControls';

type Ctl = Parameters<typeof formatValue>[0];

function mk(partial: Partial<Ctl>): Ctl {
  return {
    control_type: 'front_setback',
    control_label: 'Front setback',
    value_min: null,
    value_max: null,
    unit: null,
    condition: null,
    section_ref: null,
    source_text: null,
    dcp_name: null,
    dcp_version: null,
    pdf_page: null,
    pdf_url: null,
    ...partial,
  } as Ctl;
}

describe('formatValue — max controls render ≤, not ≥', () => {
  it('max site coverage (65%) renders ≤, never ≥ (the reported bug)', () => {
    const out = formatValue(mk({ control_type: 'max_site_coverage', direction: 'max', value_min: 65, unit: '%' }));
    expect(out).toBe('≤ 65 %');
    expect(out).not.toContain('≥');
  });

  it('max height (2 storeys) renders ≤', () => {
    expect(formatValue(mk({ control_type: 'max_height', direction: 'max', value_min: 2, unit: 'storeys' })))
      .toBe('≤ 2 storeys');
  });

  it('a minimum (front setback) still renders ≥', () => {
    expect(formatValue(mk({ direction: 'min', value_min: 6.5, unit: 'm' }))).toBe('≥ 6.5 m');
  });

  it('missing direction defaults to a floor (≥) — never silently a ceiling', () => {
    expect(formatValue(mk({ value_min: 1.5, unit: 'm' }))).toBe('≥ 1.5 m');
  });

  it('a range (rear setback) renders as a band, unaffected by direction', () => {
    expect(formatValue(mk({ value_min: 3, value_max: 8, unit: 'm' }))).toBe('3–8 m');
  });

  it('value in value_max only renders ≤', () => {
    expect(formatValue(mk({ value_max: 8, unit: 'm' }))).toBe('≤ 8 m');
  });

  it('no numeric value renders the em-dash placeholder', () => {
    expect(formatValue(mk({}))).toBe('—');
  });
});

describe('noNumberLabel — a rule with no number is described, not called a merit assessment', () => {
  it("shows the plan's rule in plain words when one is stored", () => {
    expect(noNumberLabel({ plain_summary: "Worked out from neighbours' setbacks" }))
      .toBe("Worked out from neighbours' setbacks");
  });

  it('falls back to a neutral "No set number" when none is stored, blank, or the field is absent', () => {
    expect(noNumberLabel({ plain_summary: null })).toBe('No set number');
    expect(noNumberLabel({ plain_summary: '   ' })).toBe('No set number');
    expect(noNumberLabel({})).toBe('No set number');
  });

  it('a non-string value from a malformed response falls back instead of throwing', () => {
    expect(noNumberLabel({ plain_summary: 42 as unknown as string })).toBe('No set number');
  });

  it('the component no longer prints "assessed on merit"', () => {
    const src = fs.readFileSync(
      path.join(__dirname, '../../components/compliance/DcpStructuredControls.tsx'),
      'utf8',
    );
    expect(src).not.toMatch(/assessed on merit/i);
    expect(src).toContain('noNumberLabel(control)');
  });
});

describe('structured-controls API source — classification is complete', () => {
  const src = fs.readFileSync(
    path.join(__dirname, '../../app/api/dcp/structured-controls/route.ts'),
    'utf8',
  );

  it('classifies max_* controls as maximums so the UI renders ≤', () => {
    for (const t of ['max_site_coverage', 'max_height', 'fencing_height_max', 'driveway_gradient']) {
      expect(src).toContain(`'${t}'`);
    }
    expect(src).toMatch(/MAXIMUM_CONTROL_TYPES\.has\(row\.semantic_type\)/);
    // Label backstop: a "Maximum …" label also classifies as a ceiling.
    expect(src).toMatch(/\/\^Maximum\\b\//);
    expect(src).toMatch(/direction\b/);
  });

  it('maps the variant control_types that were leaking raw slugs + "Other"', () => {
    // Each must appear in BOTH the label map and the category map.
    for (const t of ['landscaped_area_min', 'front_setback_landscaping', 'communal_open_space']) {
      const occurrences = src.split(`${t}:`).length - 1;
      expect(occurrences).toBeGreaterThanOrEqual(2);
    }
  });
});
