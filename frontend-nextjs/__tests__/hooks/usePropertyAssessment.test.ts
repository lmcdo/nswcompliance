/**
 * Latest selection wins: when two address lookups overlap, the slower, older one must not replace the
 * property, error or loading state of the newer one. Before this guard a stale response silently showed
 * planning data for the wrong property (Sol cross-review, 2026-11-09).
 *
 * prior-art-checked: reuse not viable because no test covers usePropertyAssessment; the render pattern
 * follows __tests__/hooks/useDASession.test.ts.
 */
import { renderHook, act } from '@testing-library/react';
import { usePropertyAssessment } from '@/hooks/usePropertyAssessment';

type Deferred = { resolve: (v: unknown) => void };

function deferredFetch() {
  const pending: Record<string, Deferred> = {};
  global.fetch = jest.fn((url: string) => {
    const key = decodeURIComponent(String(url).split('address=')[1] ?? '');
    return new Promise((resolve) => {
      pending[key] = { resolve };
    });
  }) as unknown as typeof fetch;
  return pending;
}

const ok = (name: string) => ({
  ok: true,
  json: async () => ({ success: true, data: { address: name } }),
});

beforeEach(() => {
  jest.spyOn(console, 'log').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => jest.restoreAllMocks());

describe('usePropertyAssessment.handleAddressSelect', () => {
  test('a slow earlier lookup cannot overwrite the property of a later one', async () => {
    const pending = deferredFetch();
    const { result } = renderHook(() => usePropertyAssessment());

    let first!: Promise<void>;
    let second!: Promise<void>;
    act(() => { first = result.current.handleAddressSelect('1 Alpha St Sydney NSW 2000'); });
    act(() => { second = result.current.handleAddressSelect('2 Beta St Sydney NSW 2000'); });

    const keys = Object.keys(pending);
    expect(keys).toHaveLength(2);
    // The later lookup answers first, then the stale earlier one answers last.
    await act(async () => { pending[keys[1]].resolve(ok('BETA')); await second; });
    await act(async () => { pending[keys[0]].resolve(ok('ALPHA')); await first; });

    expect((result.current.selectedProperty as unknown as { address: string } | null)?.address).toBe('BETA');
    expect(result.current.loading).toBe(false);
  });
});
