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

describe('our own row-type tags are cut (pilot audit 2026-11-10: 18 served rows showed them)', () => {
  it.each([
    ['NO FIGURE: 9 m low side / 12 m high side', '9 m low side / 12 m high side'],
    ['FSR-CONTROLLED: site coverage governed by Floor Space Ratio in the LEP', 'site coverage governed by Floor Space Ratio in the LEP'],
    ['DEFERS-TO-ADG: no council-specific deep soil minimum', 'no council-specific deep soil minimum'],
    ['CHARACTER-BASED: consistent with the streetscape', 'consistent with the streetscape'],
    ['ALTERNATIVE-METRIC: measured as a building envelope', 'measured as a building envelope'],
    ['QUALITATIVE: adequate landscaping', 'adequate landscaping'],
  ])('%s', (raw, shown) => {
    expect(publicCondition(raw)).toBe(shown);
  });

  it("keeps a council's own capitalised heading", () => {
    expect(publicCondition('NOTE: measured from the boundary')).toBe('NOTE: measured from the boundary');
  });

  it('a tag with nothing after it shows nothing', () => {
    expect(publicCondition('NO FIGURE:')).toBeNull();
  });
});
