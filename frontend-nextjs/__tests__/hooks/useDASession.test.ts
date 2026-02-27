import { renderHook, waitFor, act } from '@testing-library/react';
import { useDASession } from '@/hooks/useDASession';

const VALID_UUID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
const ADDRESS = '1 Test St, Marrickville NSW 2204';
const STORAGE_KEY = 'da_session_token_' + ADDRESS;
let fetchMock: jest.Mock;
let storageMock: { getItem: jest.Mock; setItem: jest.Mock; removeItem: jest.Mock; clear: jest.Mock };

beforeEach(() => {
  jest.clearAllMocks();
  storageMock = { getItem: jest.fn().mockReturnValue(null), setItem: jest.fn(), removeItem: jest.fn(), clear: jest.fn() };
  Object.defineProperty(window, 'localStorage', { value: storageMock, writable: true, configurable: true });
  fetchMock = jest.fn();
  global.fetch = fetchMock;
});
afterEach(() => { delete (global as any).fetch; });

function mockOk(body: object) {
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
}

describe('session creation', () => {
  test('creates new session when no localStorage token', async () => {
    storageMock.getItem.mockReturnValue(null);
    fetchMock.mockResolvedValueOnce(
      { ok: true, status: 200, json: () => Promise.resolve({ session_token: VALID_UUID }) }
    );
    const { result } = renderHook(() => useDASession(ADDRESS, 'marrickville', 'R2'));
    await waitFor(() => expect(result.current.sessionToken).toBe(VALID_UUID));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/da-sessions',
      expect.objectContaining({ method: 'POST', body: expect.stringContaining(ADDRESS) })
    );
    expect(storageMock.setItem).toHaveBeenCalledWith(STORAGE_KEY, VALID_UUID);
  });

  test('reuses existing token from localStorage without POSTing', async () => {
    storageMock.getItem.mockReturnValue(VALID_UUID);
    fetchMock.mockResolvedValueOnce(mockOk({ session: { dev_type: 'Rear extension', id: 1 }, responses: {} }));
    const { result } = renderHook(() => useDASession(ADDRESS, 'marrickville', 'R2'));
    await waitFor(() => expect(result.current.sessionToken).toBe(VALID_UUID));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalledWith('/api/da-sessions', expect.objectContaining({ method: 'POST' }));
    expect(storageMock.setItem).not.toHaveBeenCalled();
  });

  test('does not init when address is null', () => {
    const { result } = renderHook(() => useDASession(null));
    expect(result.current.sessionToken).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('development description', () => {
  test('loads dev_type into developmentDescription', async () => {
    storageMock.getItem.mockReturnValue(VALID_UUID);
    fetchMock.mockResolvedValueOnce(
      mockOk({ session: { dev_type: 'Two-storey rear extension', id: 1 }, responses: {} })
    );
    const { result } = renderHook(() => useDASession(ADDRESS));
    await waitFor(() =>
      expect(result.current.developmentDescription).toBe('Two-storey rear extension')
    );
  });

  test('sets developmentDescription to empty string when dev_type is null', async () => {
    storageMock.getItem.mockReturnValue(VALID_UUID);
    fetchMock.mockResolvedValueOnce(mockOk({ session: { dev_type: null, id: 1 }, responses: {} }));
    const { result } = renderHook(() => useDASession(ADDRESS));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.developmentDescription).toBe('');
  });

  test('saveDescription PATCHes dev_type to API', async () => {
    storageMock.getItem.mockReturnValue(VALID_UUID);
    fetchMock
      .mockResolvedValueOnce(mockOk({ session: { dev_type: null, id: 1 }, responses: {} }))
      .mockResolvedValueOnce(mockOk({ success: true }));
    const { result } = renderHook(() => useDASession(ADDRESS));
    await waitFor(() => expect(result.current.sessionToken).toBe(VALID_UUID));
    await act(async () => { await result.current.saveDescription('New description'); });
    const expectedUrl = '/api/da-sessions?token=' + encodeURIComponent(VALID_UUID);
    expect(fetchMock).toHaveBeenLastCalledWith(
      expectedUrl,
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ dev_type: 'New description' }) })
    );
  });

  test('saveDescription sends null for empty string', async () => {
    storageMock.getItem.mockReturnValue(VALID_UUID);
    fetchMock
      .mockResolvedValueOnce(mockOk({ session: { dev_type: 'old', id: 1 }, responses: {} }))
      .mockResolvedValueOnce(mockOk({ success: true }));
    const { result } = renderHook(() => useDASession(ADDRESS));
    await waitFor(() => expect(result.current.sessionToken).toBe(VALID_UUID));
    await act(async () => { await result.current.saveDescription(''); });
    const patchBody = JSON.parse((fetchMock.mock.calls[1][1] as RequestInit).body as string);
    expect(patchBody.dev_type).toBeNull();
  });

  test('saveDescription is a no-op when sessionToken is null', async () => {
    const { result } = renderHook(() => useDASession(null));
    await act(async () => { await result.current.saveDescription('text'); });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('responses map', () => {
  test('loads responses keyed by provision id as number', async () => {
    storageMock.getItem.mockReturnValue(VALID_UUID);
    fetchMock.mockResolvedValueOnce(mockOk({
      session: { dev_type: null, id: 1 },
      responses: {
        '42': { response_text: 'Complies', compliance_status: 'complies' },
        '99': { response_text: null, compliance_status: 'varies' },
      },
    }));
    const { result } = renderHook(() => useDASession(ADDRESS));
    await waitFor(() => expect(result.current.daResponses.size).toBe(2));
    expect(result.current.daResponses.get(42)?.compliance_status).toBe('complies');
    expect(result.current.daResponses.get(99)?.compliance_status).toBe('varies');
  });

  test('refreshResponses re-fetches and updates map', async () => {
    storageMock.getItem.mockReturnValue(VALID_UUID);
    fetchMock
      .mockResolvedValueOnce(mockOk({ session: { dev_type: null, id: 1 }, responses: {} }))
      .mockResolvedValueOnce(mockOk({
        session: { dev_type: null, id: 1 },
        responses: { '5': { response_text: 'Note', compliance_status: 'complies' } },
      }));
    const { result } = renderHook(() => useDASession(ADDRESS));
    await waitFor(() => expect(result.current.sessionToken).toBe(VALID_UUID));
    await act(async () => { await result.current.refreshResponses(); });
    expect(result.current.daResponses.get(5)?.compliance_status).toBe('complies');
  });
});
