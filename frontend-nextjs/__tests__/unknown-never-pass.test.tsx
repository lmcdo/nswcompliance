/**
 * The places that DECIDE (pass / eligible / "no") never decide on an unknown fact.
 * Companion to __tests__/unknown-never-no.test.ts, which scans for the coercions; this runs the code.
 * prior-art-checked: reuse not viable because hazard-lookup-unknown.test.ts covers the hazard maps only.
 */
import { render, screen } from '@testing-library/react';
import { CDCScreener, evaluateCriteria } from '@/components/compliance/CDCScreener';
import { autoPopulateFromConstraints } from '@/lib/see/intake';
import { hasHeritage } from '@/lib/requirement-prioritization';
import { acidSulfateAnswer, heritageAnswer, yesNo } from '@/lib/fact-answer';

describe('lib/fact-answer.ts', () => {
  it('null and undefined are "Not checked"; only a real boolean is Yes or No', () => {
    expect(yesNo(null)).toBe('Not checked');
    expect(yesNo(undefined)).toBe('Not checked');
    expect(yesNo(false)).toBe('No');
    expect(yesNo(true)).toBe('Yes');
    expect(heritageAnswer({ isHeritage: null })).toBeNull();
    expect(heritageAnswer(undefined)).toBeNull();
    expect(heritageAnswer({ isHeritage: false })).toBe(false);
  });
  it('acid sulfate: unknown when the layers or its fallback did not answer, false only when they did', () => {
    expect(acidSulfateAnswer({ notChecked: ['planning_layers'] })).toBeNull();
    expect(acidSulfateAnswer({ notChecked: ['acid_sulfate'] })).toBeNull();
    expect(acidSulfateAnswer({ notChecked: [] })).toBe(false);
    expect(acidSulfateAnswer({})).toBeNull(); // an older payload with no not-checked list
    expect(acidSulfateAnswer({ acidSulfateSoils: 'Class 2', notChecked: ['planning_layers'] })).toBe('Class 2');
  });
});

describe('CDC screener (components/compliance/CDCScreener.tsx)', () => {
  it('unknown heritage is never "Likely CDC Eligible"', () => {
    render(<CDCScreener zoneCode="R2" lotArea={600} heritageItem={false} heritageAffected={null} provisions={[]} />);
    expect(screen.queryByText('Likely CDC Eligible')).toBeNull();
  });
  it('the heritage criterion itself is "unknown" (not pass) when heritage was not checked', () => {
    const proposed = { floorAreaAddition: '', proposedHeight: '' } as any;
    const heritageRow = (affected: boolean | null) =>
      evaluateCriteria('R2', 600, false, affected, proposed, []).find((c) => c.label === 'Heritage item status')!;
    expect(heritageRow(null).result).toBe('unknown');
    expect(heritageRow(false).result).toBe('pass');
  });
});

describe('SEE intake (lib/see/intake.ts)', () => {
  it('leaves acid sulfate unanswered when it was not checked; "no" only when the map answered', () => {
    expect(autoPopulateFromConstraints({ notChecked: ['planning_layers'] }).acid_sulfate_soils).toBeUndefined();
    expect(autoPopulateFromConstraints({ notChecked: [] }).acid_sulfate_soils).toBe('no');
  });
});

describe('requirement prioritisation (lib/requirement-prioritization.ts)', () => {
  it('unknown heritage keeps heritage requirements in view', () => {
    expect(hasHeritage({ isHeritage: null })).toBe(true);
    expect(hasHeritage({ isHeritage: false })).toBe(false);
    expect(hasHeritage(undefined)).toBe(true);
    expect(hasHeritage(false)).toBe(false);
  });
});
