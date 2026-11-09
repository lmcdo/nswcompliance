/**
 * /api/feedback: (1) it uses the shared database pool, not a pool of its own built from variables production does not set;
 * (2) the list (GET) refuses anyone who is not signed in, and refuses when the sign-in check itself fails.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

const mockQuery = jest.fn();
jest.mock('@/lib/db', () => ({ getPool: () => ({ query: (...a: unknown[]) => mockQuery(...a) }) }));

const mockGetUser = jest.fn();
jest.mock('@/lib/supabase/server', () => ({
  createClient: async () => ({ auth: { getUser: () => mockGetUser() } }),
}));
jest.mock('resend', () => ({ Resend: jest.fn(() => ({ emails: { send: jest.fn() } })) }));

import { GET, POST } from '@/app/api/feedback/route';

beforeEach(() => { jest.clearAllMocks(); delete process.env.RESEND_API_KEY; });

describe('GET /api/feedback (the list holds email addresses)', () => {
  const get = () => GET(new NextRequest('http://localhost/api/feedback?limit=3'));

  test('no signed-in user: 401, and the database is never read', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null } });
    const res = await get();
    expect(res.status).toBe(401);
    expect(mockQuery).not.toHaveBeenCalled();
  });
  test('the sign-in check itself fails: still 401 (fails closed)', async () => {
    mockGetUser.mockRejectedValueOnce(new Error('no session'));
    const res = await get();
    expect(res.status).toBe(401);
    expect(mockQuery).not.toHaveBeenCalled();
  });
  test('a signed-in user gets the rows', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: { id: 'u1' } } });
    mockQuery.mockResolvedValueOnce({ rows: [{ id: 1 }] });
    const res = await get();
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual([{ id: 1 }]);
  });
});

describe('POST /api/feedback', () => {
  test('writes through the shared pool and returns the new id', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [{ id: 42 }] });
    const res = await POST(new NextRequest('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ feedbackType: 'general', feedbackText: 'a note', context: { propertyAddress: 'x' } }),
    }));
    expect(res.status).toBe(201);
    expect(mockQuery).toHaveBeenCalledTimes(1);
    expect(mockQuery.mock.calls[0][0]).toMatch(/INSERT INTO user_feedback/);
  });
});
