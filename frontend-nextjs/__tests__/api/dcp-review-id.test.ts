/**
 * DCP review — one row's verdict. 'skip' may re-label ONE named rejected row; every other
 * action touches open rows only (cross-review 2026-11-10: a chapter-wide re-label would clear
 * genuine rejections that block the commit).
 * @jest-environment node
 */
import { POST } from '@/app/api/dcp-review/[id]/route';

const mockQuery = jest.fn();
jest.mock('@/lib/database/pool-manager', () => ({ getPool: () => ({ query: mockQuery }) }));
jest.mock('@/lib/supabase/server', () => ({
  createClient: async () => ({
    auth: { getUser: async () => ({ data: { user: { email: 'rev@example.com' } } }) },
  }),
}));

function call(action: string) {
  const req = new Request('http://localhost/api/dcp-review/42', {
    method: 'POST',
    body: JSON.stringify({ action }),
    headers: { 'Content-Type': 'application/json' },
  });
  return POST(req, { params: Promise.resolve({ id: '42' }) } as never);
}

beforeEach(() => {
  jest.clearAllMocks();
  process.env.INTERNAL_REVIEWER_EMAILS = 'rev@example.com';
});

test('skip on one named row may change a rejected row to skipped', async () => {
  mockQuery.mockResolvedValueOnce({ rowCount: 1 });
  const res = await call('skip');
  expect(res.status).toBe(200);
  const [sql, params] = mockQuery.mock.calls[0];
  expect(sql).toMatch(/WHERE id = \$4 AND status = ANY\(\$6::text\[\]\)/);
  expect(params[0]).toBe('skipped');
  expect(params[3]).toBe('42');
  expect(params[5]).toEqual(['pending', 'in_progress', 'rejected']);
});

test.each(['approve', 'reject', 'needs-info'])('%s never touches a rejected row', async (action) => {
  mockQuery.mockResolvedValueOnce({ rowCount: 1 });
  await call(action);
  expect(mockQuery.mock.calls[0][1][5]).toEqual(['pending', 'in_progress']);
});
