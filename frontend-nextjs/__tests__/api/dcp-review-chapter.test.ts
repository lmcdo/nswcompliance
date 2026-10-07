/**
 * DCP review — bulk per-chapter approve/reject
 * @jest-environment node
 */
import { POST } from '@/app/api/dcp-review/chapter/route';

const mockQuery = jest.fn();
jest.mock('@/lib/database/pool-manager', () => ({ getPool: () => ({ query: mockQuery }) }));
jest.mock('@/lib/supabase/server', () => ({
  createClient: async () => ({
    auth: { getUser: async () => ({ data: { user: { email: 'rev@example.com' } } }) },
  }),
}));

function req(body: object): Request {
  return new Request('http://localhost/api/dcp-review/chapter', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  process.env.INTERNAL_REVIEWER_EMAILS = 'rev@example.com';
});

describe('POST /api/dcp-review/chapter', () => {
  test('approves every pending row for one chapter, scoped by council + chapter_key', async () => {
    mockQuery.mockResolvedValueOnce({ rowCount: 508 });
    const res = await POST(
      req({ action: 'approve', council: 'leichhardt', chapter_key: 'part-c-s1-general' }),
    );
    const data = await res.json();
    expect(res.status).toBe(200);
    expect(data.count).toBe(508);
    expect(data.status).toBe('approved');
    expect(data.reviewed_by).toBe('rev@example.com');

    const [sql, params] = mockQuery.mock.calls[0];
    // must be scoped to the one chapter AND only touch un-resolved rows
    expect(sql).toMatch(/council = \$4/);
    expect(sql).toMatch(/chapter_key = \$5/);
    expect(sql).toMatch(/status IN \('pending', 'in_progress'\)/);
    expect(params).toEqual([
      'approved', 'rev@example.com', null, 'leichhardt', 'part-c-s1-general',
    ]);
  });

  test('rejects map to the rejected status', async () => {
    mockQuery.mockResolvedValueOnce({ rowCount: 3 });
    const res = await POST(req({ action: 'reject', council: 'c', chapter_key: 'k' }));
    expect((await res.json()).status).toBe('rejected');
  });

  test('400 on an unknown action, without touching the DB', async () => {
    const res = await POST(req({ action: 'delete', council: 'c', chapter_key: 'k' }));
    expect(res.status).toBe(400);
    expect(mockQuery).not.toHaveBeenCalled();
  });

  test('400 when council or chapter_key is missing, without touching the DB', async () => {
    const res = await POST(req({ action: 'approve', council: 'c' }));
    expect(res.status).toBe(400);
    expect(mockQuery).not.toHaveBeenCalled();
  });

  test('404 when the chapter has no pending rows', async () => {
    mockQuery.mockResolvedValueOnce({ rowCount: 0 });
    const res = await POST(req({ action: 'approve', council: 'c', chapter_key: 'k' }));
    expect(res.status).toBe(404);
  });
});
