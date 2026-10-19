import { publicCondition } from '@/lib/dcp/public-condition';

describe('publicCondition', () => {
  it('cuts the internal extraction note (Concord p.E-15)', () => {
    expect(publicCondition(
      'Rear setbacks - single street frontage (p.E-15); excludes outbuildings and secondary dwellings. ' +
      'NOT yet stored: upper-floor living room 9.0m (C10), secondary dwelling 3.0m (C11).',
    )).toBe('Rear setbacks - single street frontage (p.E-15); excludes outbuildings and secondary dwellings.');
  });
  it('leaves an ordinary condition alone', () => {
    expect(publicCondition('corner lot; secondary street setback')).toBe('corner lot; secondary street setback');
  });
  it('a condition that was only a note is null', () => {
    expect(publicCondition('NOT yet stored: everything')).toBeNull();
    expect(publicCondition(null)).toBeNull();
  });
});
