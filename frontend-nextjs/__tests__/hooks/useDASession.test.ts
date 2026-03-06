import { renderHook, waitFor } from '@testing-library/react';
import { useDASession } from '@/hooks/useDASession';

const TEST_ADDRESS = '40 Lackey St Summer Hill NSW 2130';

beforeEach(() => {
  localStorage.clear();
  jest.resetAllMocks();
});

// W1-8: error signal
describe('useDASession error signal', () => {
  test('error is null on init before any fetch', () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ session_token: 'tok', session: {}, responses: {} }) });
    const { result } = renderHook(() => useDASession(TEST_ADDRESS));
    expect(result.current.error).toBeNull();
  });

  test('error is populated when session creation fails', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));
    const { result } = renderHook(() => useDASession(TEST_ADDRESS));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error!.message).toContain('Network error');
  });

  test('error is populated when loadResponses fetch fails', async () => {
    localStorage.setItem(`da_session_token_${TEST_ADDRESS}`, 'existing-token');
    global.fetch = jest.fn().mockRejectedValue(new Error('Server unavailable'));
    const { result } = renderHook(() => useDASession(TEST_ADDRESS));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBeInstanceOf(Error);
  });

  test('isLoading starts false and goes false after completion', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_token: 'tok', session: {}, responses: {} }),
    });
    const { result } = renderHook(() => useDASession(TEST_ADDRESS));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBeNull();
  });

  test('address null skips init and keeps error null', () => {
    global.fetch = jest.fn();
    const { result } = renderHook(() => useDASession(null));
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });
});

// W1-8: return shape
describe('useDASession return shape', () => {
  test('exposes error property', () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ session_token: 'tok', session: {}, responses: {} }) });
    const { result } = renderHook(() => useDASession(null));
    expect('error' in result.current).toBe(true);
  });

  test('exposes isLoading property', () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ session_token: 'tok', session: {}, responses: {} }) });
    const { result } = renderHook(() => useDASession(null));
    expect('isLoading' in result.current).toBe(true);
  });
});
