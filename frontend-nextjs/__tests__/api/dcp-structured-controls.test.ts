/**
 * DCP structured-controls — consolidated onto the guarded proxy (item 5).
 *
 * REWRITTEN 2026-08-03: the previous suite mocked pool.query and pinned the
 * route's own SQL (registry-join scoping + the runtime cross-council leak
 * sentinel). Both are gone by construction: rows and the per-council PDF-URL
 * map now come from /pipeline/dcp-controls (conveyancing_db.
 * fetch_dcp_setbacks — the ONE guarded implementation), so a foreign
 * council's registry row can never attach. What this suite pins instead:
 *   1. no inline SQL — rows come from the client, filtered by dev_type
 *   2. needs_review rows cannot be served (excluded at source; the old route
 *      served a flagged row as a normal number whenever it had a value —
 *      35 rows measured 2026-08-03)
 *   3. the empty case reports available_dev_types from the guarded rows
 *   4. source-unavailable is a visible 503, never an empty success
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

const mockFetchDcpControls = jest.fn();
jest.mock('@/lib/dcp-controls-client', () => ({
  fetchDcpControls: (...args: unknown[]) => mockFetchDcpControls(...args),
  DcpControlsUnavailableError: class DcpControlsUnavailableError extends Error {},
}));

import { GET } from '@/app/api/dcp/structured-controls/route';
import { DcpControlsUnavailableError } from '@/lib/dcp-controls-client';

function req(params: string): NextRequest {
  return new NextRequest(`http://localhost/api/dcp/structured-controls?${params}`);
}

function proxyRow(overrides: Record<string, unknown> = {}) {
  return {
    type: 'Front Setback',
    dev_type: 'dwelling_house',
    control_type: 'prescribed',
    semantic_type: 'front_setback',
    requirement: '6 m minimum',
    value_min: 6,
    value_max: null,
    unit: 'm',
    clause: 'B2.1',
    notes: '',
    source_text: 'Front setback minimum 6m',
    source_chapter_key: 'part-b-s2',
    pdf_page: 12,
    dcp_version: 'Waverley DCP 2022',
    ...overrides,
  };
}

function proxyResult(rows: unknown[], overrides: Record<string, unknown> = {}) {
  return {
    available: true,
    lga: 'waverley',
    dcp_name: 'Waverley DCP 2022',
    // Real R2 URLs are https://pub-<hash>.r2.dev/... — verified against
    // production 2026-08-26. 'r2.example' was never a shape this system
    // produces, and the page anchor is now restricted to our own copies
    // because pdf_page is measured against the PDF we paginated.
    registry_pdf_urls: {
      'part-b-s2': 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/waverley.pdf',
    },
    as_at: { date: '2022-01-01', precision: 'year', kind: 'effective', basis: 'stated_in_document' },
    as_at_line: 'In force from 2022 (date stated in the plan document)',
    rows,
    ...overrides,
  };
}

beforeEach(() => jest.clearAllMocks());

describe('GET /api/dcp/structured-controls', () => {
  test('serves guarded proxy rows for the requested dev_type with anchored PDF links', async () => {
    mockFetchDcpControls.mockResolvedValueOnce(proxyResult([
      proxyRow(),
      proxyRow({ dev_type: 'secondary_dwelling', semantic_type: 'rear_setback' }),
    ]));
    const res = await GET(req('council=waverley&dev_type=dwelling_house'));
    const data = await res.json();

    expect(mockFetchDcpControls).toHaveBeenCalledWith('waverley');
    const served = data.categories.flatMap(
      (c: { controls: { pdf_url: string | null }[] }) => c.controls,
    );
    expect(served).toHaveLength(1); // dev_type filter applied
    expect(served[0].pdf_url).toBe(
      'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/waverley.pdf#page=12',
    );
    expect(data.dcp_name).toBe('Waverley DCP 2022');
    expect(data.as_at_line).toMatch(/In force from 2022/);
  });

  test('does NOT anchor a page onto a council-hosted PDF', async () => {
    // pdf_page is a page number in OUR paginated copy. The council's published
    // PDF may be a different split or edition, so carrying the anchor across
    // would point confidently at the wrong page - worse than no anchor, because
    // the reader has no reason to doubt it.
    mockFetchDcpControls.mockResolvedValueOnce(
      proxyResult([proxyRow()], {
        registry_pdf_urls: { 'part-b-s2': 'https://www.waverley.nsw.gov.au/dcp.pdf' },
      }),
    );
    const res = await GET(req('council=waverley&dev_type=dwelling_house'));
    const body = await res.json();
    const served = body.categories.flatMap(
      (c: { controls: { pdf_url: string | null }[] }) => c.controls,
    );
    expect(served[0].pdf_url).toBe('https://www.waverley.nsw.gov.au/dcp.pdf');
    expect(served[0].pdf_url).not.toContain('#page=');
  });

  test('under_review can never be emitted — flagged rows are excluded at the source', async () => {
    // The proxy (fetch_dcp_setbacks) excludes needs_review rows in SQL and
    // per-row; whatever arrives here is clean, so status is numeric or
    // not_applicable only.
    mockFetchDcpControls.mockResolvedValueOnce(proxyResult([
      proxyRow(),
      proxyRow({ semantic_type: 'rear_setback', value_min: null, value_max: null }),
    ]));
    const res = await GET(req('council=waverley'));
    const data = await res.json();
    const statuses = data.categories.flatMap(
      (c: { controls: { data_status: string }[] }) => c.controls.map((x) => x.data_status),
    );
    expect(statuses.sort()).toEqual(['not_applicable', 'numeric']);
    expect(statuses).not.toContain('under_review');
  });

  test('passes the plain wording of a no-number rule through, and null when the backend has none', async () => {
    mockFetchDcpControls.mockResolvedValueOnce(proxyResult([
      proxyRow({ value_min: null, plain_summary: "Worked out from neighbours' setbacks" }),
      proxyRow({ semantic_type: 'rear_setback' }),
    ]));
    const res = await GET(req('council=waverley'));
    const data = await res.json();
    const served = data.categories.flatMap(
      (c: { controls: { control_type: string; data_status: string; plain_summary: string | null }[] }) => c.controls,
    );
    const front = served.find((x: { control_type: string }) => x.control_type === 'front_setback');
    const rear = served.find((x: { control_type: string }) => x.control_type === 'rear_setback');
    expect(front.data_status).toBe('not_applicable');
    expect(front.plain_summary).toBe("Worked out from neighbours' setbacks");
    expect(rear.plain_summary).toBeNull();
  });

  test('empty dev_type reports the dev types the guarded rows actually carry', async () => {
    mockFetchDcpControls.mockResolvedValueOnce(proxyResult([
      proxyRow({ dev_type: 'secondary_dwelling' }),
    ]));
    const res = await GET(req('council=waverley&dev_type=dwelling_house'));
    const data = await res.json();
    expect(data.has_controls).toBe(false);
    expect(data.available_dev_types).toEqual(['secondary_dwelling']);
  });

  test('source-unavailable is a visible 503, never an empty success', async () => {
    mockFetchDcpControls.mockRejectedValueOnce(
      new DcpControlsUnavailableError('down'));
    const res = await GET(req('council=waverley'));
    expect(res.status).toBe(503);
    const data = await res.json();
    expect(data.error).toMatch(/unavailable/);
  });
});
