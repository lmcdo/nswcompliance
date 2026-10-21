/**
 * Setback-only councils (bayside, liverpool) have no provisions view, so the
 * "Amendment detected" line never showed for them, and their flagged setback
 * rows are excluded before serving. Measured 2026-10-22: bayside s3-5 had 2
 * withheld rows and canterbury_bankstown 9, all silently missing from the page.
 * review_status is how the panel learns that - so it must reach BOTH response
 * shapes, and a failed check must read as unknown (null), never "nothing pending".
 *
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

const mockQuery = jest.fn();
jest.mock('@/lib/db', () => ({ query: (...a: unknown[]) => mockQuery(...a) }));

const mockFetchDcpControls = jest.fn();
jest.mock('@/lib/dcp-controls-client', () => ({
  fetchDcpControls: (...args: unknown[]) => mockFetchDcpControls(...args),
  DcpControlsUnavailableError: class DcpControlsUnavailableError extends Error {},
}));

import { fetchDcpReviewStatus } from '@/lib/dcp-review-status';
import { GET } from '@/app/api/dcp/structured-controls/route';

function req(params: string): NextRequest {
  return new NextRequest(`http://localhost/api/dcp/structured-controls?${params}`);
}

const row = {
  type: 'Front Setback', dev_type: 'dwelling_house', control_type: 'prescribed',
  semantic_type: 'front_setback', requirement: '6 m minimum', value_min: 6, value_max: null,
  unit: 'm', clause: '3.5', notes: '', source_text: 'Front setback minimum 6m',
  source_chapter_key: 's3-5-traffic-parking-access', pdf_page: 12, dcp_version: 'Bayside DCP 2022',
};
const result = (rows: unknown[]) => ({
  available: true, lga: 'bayside', dcp_name: 'Bayside DCP 2022', registry_pdf_urls: {},
  as_at: null, as_at_line: null, rows,
});

beforeEach(() => jest.clearAllMocks());

describe('fetchDcpReviewStatus', () => {
  test('reads both signals for the council slugs', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [{ amendment_pending: true, withheld_source_changed: 2, withheld_other: 1 }] });
    await expect(fetchDcpReviewStatus(['bayside'])).resolves.toEqual({
      amendment_pending: true, withheld_source_changed: 2, withheld_other: 1,
    });
    const [sql, params] = mockQuery.mock.calls[0];
    expect(params).toEqual([['bayside']]);
    // The filters that make it this council's CURRENT, ACTIVE state - drop one and
    // a retired chapter or a superseded row would raise a false warning.
    expect(sql).toMatch(/council = ANY\(\$1\)/);
    expect(sql).toMatch(/is_active = TRUE AND needs_extraction = TRUE/);
    // A queued re-read with no new file must not read as "the plan has changed".
    expect(sql).toMatch(/provisions_extracted_from_hash IS NOT NULL\s+AND content_hash IS DISTINCT FROM provisions_extracted_from_hash/);
    expect(sql).toMatch(/lga = ANY\(\$1\)/);
    expect(sql).toMatch(/is_current = TRUE AND needs_review = TRUE/);
    // Only the monitor's own reason counts as an amendment; everything else
    // (a number that did not match the council's document) is counted apart.
    expect(sql).toMatch(/FILTER \(WHERE review_reason = 'chapter_pdf_changed'\)::int\s+AS withheld_source_changed/);
    expect(sql).toMatch(/FILTER \(WHERE review_reason IS DISTINCT FROM 'chapter_pdf_changed'\)::int\s+AS withheld_other/);
  });

  test('a count arriving as a string (pg bigint) is still a number', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [{ amendment_pending: false, withheld_source_changed: '9', withheld_other: '4' }] });
    await expect(fetchDcpReviewStatus(['canterbury_bankstown'])).resolves.toEqual({
      amendment_pending: false, withheld_source_changed: 9, withheld_other: 4,
    });
  });

  test('a failed query is unknown (null), never "nothing pending"', async () => {
    mockQuery.mockRejectedValueOnce(new Error('connection refused'));
    jest.spyOn(console, 'error').mockImplementation(() => {});
    await expect(fetchDcpReviewStatus(['bayside'])).resolves.toBeNull();
  });

  test('no slug resolves to unknown without querying', async () => {
    await expect(fetchDcpReviewStatus([])).resolves.toBeNull();
    expect(mockQuery).not.toHaveBeenCalled();
  });
});

describe('structured-controls carries review_status', () => {
  test('when controls are served', async () => {
    mockFetchDcpControls.mockResolvedValueOnce(result([row]));
    mockQuery.mockResolvedValueOnce({ rows: [{ amendment_pending: true, withheld_source_changed: 2, withheld_other: 0 }] });
    const body = await (await GET(req('council=bayside&dev_type=dwelling_house'))).json();
    expect(body.has_controls).toBe(true);
    expect(body.review_status).toEqual({ amendment_pending: true, withheld_source_changed: 2, withheld_other: 0 });
  });

  test('when every row was withheld (the case the warning exists for)', async () => {
    mockFetchDcpControls.mockResolvedValueOnce(result([]));
    mockQuery.mockResolvedValueOnce({ rows: [{ amendment_pending: true, withheld_source_changed: 42, withheld_other: 0 }] });
    const body = await (await GET(req('council=bayside&dev_type=dwelling_house'))).json();
    expect(body.has_controls).toBe(false);
    expect(body.review_status).toEqual({ amendment_pending: true, withheld_source_changed: 42, withheld_other: 0 });
  });

  test('a failed check is sent as null, not dropped', async () => {
    mockFetchDcpControls.mockResolvedValueOnce(result([row]));
    mockQuery.mockRejectedValueOnce(new Error('timeout'));
    jest.spyOn(console, 'error').mockImplementation(() => {});
    const body = await (await GET(req('council=bayside&dev_type=dwelling_house'))).json();
    expect(body).toHaveProperty('review_status', null);
  });
});
