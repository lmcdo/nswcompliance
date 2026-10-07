/**
 * The internal review routes accept nothing from anyone outside INTERNAL_REVIEWER_EMAILS.
 *
 * Found 2026-10-07: canibuildit.com.au/api/dcp-review served the queue to anyone and the
 * write routes took a verdict -- and an edited_text marked `grounded` -- from anyone,
 * because every gate was a no-op unless NEXT_PUBLIC_AUTH_ENABLED was 'true'.
 * Each case below forces one way the gate can fail and asserts the DB is never touched.
 * @jest-environment node
 */
import { GET as listDcp } from '@/app/api/dcp-review/route';
import { POST as decideDcp } from '@/app/api/dcp-review/[id]/route';
import { POST as decideChapter } from '@/app/api/dcp-review/chapter/route';
import { GET as listSetbacks } from '@/app/api/internal/setback-review/route';
import { POST as decideSetback } from '@/app/api/internal/setback-review/[id]/route';
import { reviewerAllowlist } from '@/lib/internal-reviewer';

const mockQuery = jest.fn();
const mockConnect = jest.fn();
jest.mock('@/lib/database/pool-manager', () => ({
  getPool: () => ({ query: mockQuery, connect: mockConnect }),
}));

let sessionUser: { email?: string } | null = null;
let sessionThrows = false;
jest.mock('@/lib/supabase/server', () => ({
  createClient: async () => ({
    auth: {
      getUser: async () => {
        if (sessionThrows) throw new Error('no session cookie store');
        return { data: { user: sessionUser } };
      },
    },
  }),
}));

const post = (body: object) =>
  new Request('http://localhost/x', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
const idParams = { params: Promise.resolve({ id: '7' }) };

const CALLS: Array<[string, () => Promise<Response>]> = [
  ['GET /api/dcp-review', () => listDcp()],
  ['POST /api/dcp-review/[id]', () =>
    decideDcp(post({ action: 'approve', edited_text: 'Maximum height 99 m' }), idParams)],
  ['POST /api/dcp-review/chapter', () =>
    decideChapter(post({ action: 'approve', council: 'c', chapter_key: 'k' }))],
  ['GET /api/internal/setback-review', () => listSetbacks()],
  ['POST /api/internal/setback-review/[id]', () =>
    decideSetback(post({ action: 'fix', value_min: 0.1, section_ref: 'x' }), idParams)],
];

beforeEach(() => {
  jest.clearAllMocks();
  sessionUser = null;
  sessionThrows = false;
  process.env.INTERNAL_REVIEWER_EMAILS = 'Reviewer@Example.com, second@example.com';
  delete process.env.NEXT_PUBLIC_AUTH_ENABLED;
});

describe.each(CALLS)('%s', (_name, call) => {
  test('503 and no DB access when the allowlist is unset', async () => {
    delete process.env.INTERNAL_REVIEWER_EMAILS;
    sessionUser = { email: 'reviewer@example.com' };
    const res = await call();
    expect(res.status).toBe(503);
    expect(mockQuery).not.toHaveBeenCalled();
    expect(mockConnect).not.toHaveBeenCalled();
  });

  test('401 and no DB access with no session, even with NEXT_PUBLIC_AUTH_ENABLED unset', async () => {
    const res = await call();
    expect(res.status).toBe(401);
    expect(mockQuery).not.toHaveBeenCalled();
    expect(mockConnect).not.toHaveBeenCalled();
  });

  test('401 when the session cannot be read at all', async () => {
    sessionThrows = true;
    const res = await call();
    expect(res.status).toBe(401);
    expect(mockQuery).not.toHaveBeenCalled();
  });

  test('403 and no DB access for a signed-in user who is not on the allowlist', async () => {
    sessionUser = { email: 'anyone@gmail.com' };
    const res = await call();
    expect(res.status).toBe(403);
    expect(mockQuery).not.toHaveBeenCalled();
    expect(mockConnect).not.toHaveBeenCalled();
  });
});

test('an allowlisted reviewer reaches the DB, matched case-insensitively and recorded by name', async () => {
  sessionUser = { email: 'REVIEWER@example.com' };
  mockQuery.mockResolvedValueOnce({ rowCount: 1 });
  const res = await decideDcp(post({ action: 'approve' }), idParams);
  expect(res.status).toBe(200);
  expect((await res.json()).reviewed_by).toBe('reviewer@example.com');
  expect(mockQuery.mock.calls[0][1][1]).toBe('reviewer@example.com');
});

test('reviewerAllowlist trims, lowercases and drops empty entries', () => {
  expect([...reviewerAllowlist(' A@x.com, ,b@Y.com,')]).toEqual(['a@x.com', 'b@y.com']);
  expect(reviewerAllowlist('').size).toBe(0);
  delete process.env.INTERNAL_REVIEWER_EMAILS;
  expect(reviewerAllowlist().size).toBe(0);
});
