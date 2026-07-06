/**
 * DCP structured-controls — cross-council contamination guards
 *
 * Regression for the bug where a generic chapter_key (e.g. "part-e-s4.6")
 * shared across councils fanned one control into several rows carrying foreign
 * councils' DCP names. Two layers under test:
 *   1. the SQL scopes the registry join to the council (cr.council = sc.lga)
 *   2. the runtime output invariant drops any leaked foreign row and alerts
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import { GET } from '@/app/api/dcp/structured-controls/route';

const mockQuery = jest.fn();
jest.mock('@/lib/db', () => ({ getPool: () => ({ query: mockQuery }) }));

const mockCapture = jest.fn();
jest.mock('@/lib/posthog-server', () => ({
  captureServerException: (...args: unknown[]) => mockCapture(...args),
}));

function req(params: string): NextRequest {
  return new NextRequest(`http://localhost/api/dcp/structured-controls?${params}`);
}

function row(overrides: Record<string, unknown> = {}) {
  return {
    control_type: 'front_setback',
    value_min: '6',
    value_max: null,
    unit: 'm',
    condition: null,
    section_ref: 'B2.1',
    source_text: 'Front setback minimum 6m',
    dcp_version: 'Waverley DCP 2022',
    pdf_page: 12,
    source_chapter_key: 'part-b-s2',
    needs_review: false,
    lga: 'waverley',
    r2_public_pdf_url: 'https://r2.example/waverley.pdf',
    chapter_label: 'Part B2',
    dcp_name: 'Waverley DCP 2022',
    registry_council: 'waverley',
    ...overrides,
  };
}

beforeEach(() => jest.clearAllMocks());

describe('GET /api/dcp/structured-controls', () => {
  test('registry join is scoped to the council in the SQL itself', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [row()] });
    await GET(req('council=waverley'));
    const [sql] = mockQuery.mock.calls[0];
    expect(sql).toMatch(/cr\.council = sc\.lga/);
    expect(sql).toMatch(/cr\.is_active = true/);
  });

  test('seeded collision: a leaked foreign-council row is dropped and alerts', async () => {
    // Same chapter_key under two councils — the exact contamination shape.
    mockQuery.mockResolvedValueOnce({
      rows: [
        row(),
        row({
          registry_council: 'randwick',
          dcp_name: 'Randwick Comprehensive DCP 2013 (Amendment 9)',
          control_type: 'rear_setback',
        }),
      ],
    });
    const res = await GET(req('council=waverley'));
    const data = await res.json();

    const served = data.categories.flatMap(
      (c: { controls: { dcp_name: string }[] }) => c.controls,
    );
    expect(served).toHaveLength(1);
    expect(served[0].dcp_name).toBe('Waverley DCP 2022');
    // top-level dcp_name prefers the LONGEST name — must not pick the foreign one
    expect(data.dcp_name).toBe('Waverley DCP 2022');

    expect(mockCapture).toHaveBeenCalledTimes(1);
    const [err, ctx] = mockCapture.mock.calls[0];
    expect((err as Error).message).toMatch(/cross-council leak/);
    expect(ctx).toMatchObject({
      endpoint: '/api/dcp/structured-controls',
      leaked_rows: 1,
    });
  });

  test('clean rows pass through untouched with no alert', async () => {
    mockQuery.mockResolvedValueOnce({
      rows: [
        row(),
        // LEFT JOIN miss — no registry row attached; must not be treated as a leak
        row({
          registry_council: null,
          dcp_name: null,
          r2_public_pdf_url: null,
          control_type: 'rear_setback',
        }),
      ],
    });
    const res = await GET(req('council=waverley'));
    const data = await res.json();

    const served = data.categories.flatMap(
      (c: { controls: unknown[] }) => c.controls,
    );
    expect(served).toHaveLength(2);
    expect(mockCapture).not.toHaveBeenCalled();
  });
});
