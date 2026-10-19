import { publicCondition } from '@/lib/dcp/public-condition';

describe('publicCondition', () => {
  it('cuts the internal extraction note (Concord p.E-15)', () => {
    expect(publicCondition(
      'Rear setbacks - single street frontage (p.E-15); excludes outbuildings and secondary dwellings. ' +
      'NOT yet stored: upper-floor living room 9.0m (C10), secondary dwelling 3.0m (C11).',
    )).toBe('Rear setbacks - single street frontage (p.E-15); excludes outbuildings and secondary dwellings.');
  });
  it('drops a note written as its own sentence (Mount Annan p.11)', () => {
    expect(publicCondition(
      'Lot <= 900m2 (Table 4-2). A reduced 3.5m applies only where the development fronts open space. ' +
      'Tiers >900-1500m2 = 6.5m and >1500m2 = 10m are NOT yet stored.',
    )).toBe('Lot <= 900m2 (Table 4-2). A reduced 3.5m applies only where the development fronts open space.');
  });
  it('leaves an ordinary condition alone', () => {
    expect(publicCondition('corner lot; secondary street setback')).toBe('corner lot; secondary street setback');
  });
  it('a condition that was only a note is null', () => {
    expect(publicCondition('NOT yet stored: everything')).toBeNull();
    expect(publicCondition(null)).toBeNull();
  });
});
