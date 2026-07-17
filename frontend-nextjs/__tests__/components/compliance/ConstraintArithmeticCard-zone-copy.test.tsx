/**
 * ConstraintArithmeticCard — the non-residential "Dwelling yield" note must
 * branch by zone family: shop-top copy only on centres/business zones, the
 * land-use-table sentence everywhere else (C/RU/other).
 */

import React from 'react';
import { render } from '@testing-library/react';
import {
  ConstraintArithmeticCard,
  type ConstraintArithmeticResult,
} from '@/components/compliance/ConstraintArithmeticCard';

// Minimal engine result: LEP envelope present, nothing modelled beyond it.
const RESULT: ConstraintArithmeticResult = {
  lot_area_m2: 8467,
  dev_type: 'dwelling_house',
  lep_height_m: null,
  lep_fsr: null,
  lep_max_gfa_from_fsr_m2: null,
  lep_max_storeys: null,
  lep_max_gfa_from_height_m2: null,
  lep_envelope_gfa_m2: null,
  buildable_footprint_m2: null,
  setback_front_m: null,
  setback_rear_m: null,
  setback_side_m: null,
  site_coverage_cap_m2: null,
  landscaping_reduction_m2: null,
  effective_height_m: null,
  effective_fsr: null,
  shadow_storey_reduction: 0,
  parking_spaces_required: null,
  parking_gfa_consumed_m2: null,
  realistic_gfa_m2: null,
  dcp_adjusted_gfa_m2: null,
  realistic_dwellings: null,
  binding_constraint: null,
  binding_constraint_label: '',
  steps: [],
  gaps: [],
  confidence: 'medium',
  disclaimer: 'Screening calculation only.',
};

describe('ConstraintArithmeticCard — dwelling-yield note by zone family', () => {
  it('C4 (conservation): land-use-table sentence, no shop-top claim', () => {
    const { container } = render(
      <ConstraintArithmeticCard briefData={RESULT} zone="C4" />,
    );
    expect(container.textContent).toMatch(/Dwelling yield is not modelled for C4/);
    expect(container.textContent).toMatch(/land-use table/);
    expect(container.textContent).not.toMatch(/shop-top/i);
  });

  it('RU1 (rural): land-use-table sentence, no shop-top claim', () => {
    const { container } = render(
      <ConstraintArithmeticCard briefData={RESULT} zone="RU1" />,
    );
    expect(container.textContent).toMatch(/Dwelling yield is not modelled for RU1/);
    expect(container.textContent).not.toMatch(/shop-top/i);
  });

  it('E1 (centres): keeps the shop-top sentence', () => {
    const { container } = render(
      <ConstraintArithmeticCard briefData={RESULT} zone="E1" />,
    );
    expect(container.textContent).toMatch(/shop-top housing above retail/);
  });

  it('R2 (residential): no non-modelled note at all', () => {
    const { container } = render(
      <ConstraintArithmeticCard briefData={RESULT} zone="R2" />,
    );
    expect(container.textContent).not.toMatch(/not modelled for/i);
  });
});
