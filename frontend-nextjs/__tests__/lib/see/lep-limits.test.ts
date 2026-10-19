import { lepLimits } from '@/lib/see/lep-limits';

describe('lepLimits', () => {
  it('reads the /api/capacity/calculate shape (capacity.maxHeight / maxFSR)', () => {
    expect(lepLimits({ success: true, capacity: { maxHeight: 9, maxFSR: 0.5 } })).toEqual({ height: 9, fsr: 0.5 });
  });
  it('still reads the flat shape', () => {
    expect(lepLimits({ height_limit: '8.5', fsr: '0.6' })).toEqual({ height: 8.5, fsr: 0.6 });
  });
  it('nothing held -> undefined, never 0', () => {
    expect(lepLimits(null)).toEqual({ height: undefined, fsr: undefined });
    expect(lepLimits({ capacity: { maxHeight: null, maxFSR: 0 } })).toEqual({ height: undefined, fsr: undefined });
  });
});
