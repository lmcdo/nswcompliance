/**
 * fetchDcpControls must never reuse a stored backend response.
 *
 * Measured 2026-09-13: after a backend fix restored citation links
 * (/pipeline/dcp-controls returned them on 6 of 6 direct calls), the site kept
 * serving 0 links for councils whose response had been fetched before the fix
 * (penrith, hornsby, waverley) while councils first requested afterwards were
 * correct (blacktown 10 of 10, camden 9 of 9). No proxy sits in front of the
 * backend; Next 14 keeps server fetch() results in its Data Cache across
 * deployments. The same cache would keep a control that has since been held
 * for review on screen.
 *
 * prior-art-checked: the only existing suite touching this client
 * (__tests__/api/dcp-structured-controls.test.ts) mocks fetchDcpControls
 * wholesale, so nothing asserted how it calls fetch.
 * @jest-environment node
 */
import { fetchDcpControls, DcpControlsUnavailableError } from '@/lib/dcp-controls-client';

const realFetch = global.fetch;

afterEach(() => {
  global.fetch = realFetch;
});

function stubFetch(body: unknown, ok = true, status = 200): jest.Mock {
  const fn = jest.fn().mockResolvedValue({ ok, status, json: async () => body });
  global.fetch = fn as unknown as typeof fetch;
  return fn;
}

test('asks the backend for a fresh response every time', async () => {
  const fn = stubFetch({ available: true, lga: 'penrith', rows: [], registry_pdf_urls: {} });

  await fetchDcpControls('penrith');

  expect(fn).toHaveBeenCalledTimes(1);
  const [url, init] = fn.mock.calls[0];
  expect(String(url)).toContain('/pipeline/dcp-controls?lga=penrith');
  expect(init).toEqual(expect.objectContaining({ cache: 'no-store' }));
});

test('a zone-filtered request is not cached either', async () => {
  const fn = stubFetch({ available: true, lga: 'penrith', rows: [] });

  await fetchDcpControls('penrith', 'R2');

  const [url, init] = fn.mock.calls[0];
  expect(String(url)).toContain('zone=R2');
  expect(init.cache).toBe('no-store');
});

test('returns the backend body unchanged, including the citation link map', async () => {
  const body = {
    available: true,
    lga: 'penrith',
    rows: [],
    registry_pdf_urls: { 'penrith-dcp-2014-part-d2': 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/x.pdf' },
  };
  stubFetch(body);

  await expect(fetchDcpControls('penrith')).resolves.toEqual(body);
});

test('an unreachable backend is a thrown DcpControlsUnavailableError, never an empty success', async () => {
  global.fetch = jest.fn().mockRejectedValue(new Error('ECONNRESET')) as unknown as typeof fetch;

  await expect(fetchDcpControls('penrith')).rejects.toBeInstanceOf(DcpControlsUnavailableError);
});

test('a non-ok status is a thrown DcpControlsUnavailableError', async () => {
  stubFetch({}, false, 503);

  await expect(fetchDcpControls('penrith')).rejects.toBeInstanceOf(DcpControlsUnavailableError);
});
