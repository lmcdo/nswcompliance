/**
 * DA Sessions API route — POST / GET / PATCH
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import { POST, GET, PATCH } from '@/app/api/da-sessions/route';

jest.mock('../../lib/db', () => ({ query: jest.fn() }));

import { query } from '../../lib/db';
const mockQuery = query as jest.MockedFunction<typeof query>;

const VALID_UUID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';

function makeRequest(method: string, url: string, body?: object): NextRequest {
  return new NextRequest(url, {
    method,
    body: body ? JSON.stringify(body) : undefined,
    headers: body ? { 'Content-Type': 'application/json' } : {},
  });
}

beforeEach(() => { jest.clearAllMocks(); });

describe('POST /api/da-sessions', () => {
  test('creates session and returns token', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [{ id: 1, session_token: VALID_UUID }] } as any);
    const req = makeRequest('POST', 'http://localhost/api/da-sessions', {
      address: '1 Test St, Marrickville NSW 2204',
      former_council: 'marrickville',
      zone: 'R2 Low Density Residential',
    });
    const res = await POST(req);
    const data = await res.json();
    expect(res.status).toBe(200);
    expect(data.session_token).toBe(VALID_UUID);
    expect(data.session_id).toBe(1);
  });

  test('returns 400 when address is missing', async () => {
    const req = makeRequest('POST', 'http://localhost/api/da-sessions', { former_council: 'marrickville' });
    const res = await POST(req);
    const data = await res.json();
    expect(res.status).toBe(400);
    expect(data.error).toBe('address is required');
    expect(mockQuery).not.toHaveBeenCalled();
  });

  test('passes dev_type to database when provided', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [{ id: 2, session_token: VALID_UUID }] } as any);
    const req = makeRequest('POST', 'http://localhost/api/da-sessions', {
      address: '1 Test St',
      dev_type: 'Two-storey rear extension',
    });
    await POST(req);
    expect(mockQuery).toHaveBeenCalledWith(
      expect.stringContaining('INSERT INTO da_sessions'),
      expect.arrayContaining(['Two-storey rear extension'])
    );
  });

  test('passes null for missing optional fields', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [{ id: 3, session_token: VALID_UUID }] } as any);
    const req = makeRequest('POST', 'http://localhost/api/da-sessions', { address: '1 Test St' });
    await POST(req);
    const callArgs = mockQuery.mock.calls[0][1];
    expect(callArgs).toEqual(['1 Test St', null, null, null]);
  });
});

describe('GET /api/da-sessions', () => {
  test('returns session and responses for valid token', async () => {
    const session = { id: 1, address: '1 Test St', dev_type: 'Extension', former_council: 'marrickville', zone: 'R2', created_at: new Date() };
    mockQuery
      .mockResolvedValueOnce({ rows: [session] } as any)
      .mockResolvedValueOnce({ rows: [
        { provision_id: 42, response_text: 'Complies', compliance_status: 'complies', updated_at: new Date() },
        { provision_id: 99, response_text: null, compliance_status: 'varies', updated_at: new Date() },
      ]} as any)
      .mockResolvedValueOnce({ rows: [] } as any);
    const req = makeRequest('GET', `http://localhost/api/da-sessions?token=${VALID_UUID}`);
    const res = await GET(req);
    const data = await res.json();
    expect(res.status).toBe(200);
    expect(data.session.dev_type).toBe('Extension');
    expect(data.responses[42].compliance_status).toBe('complies');
    expect(data.responses[99].compliance_status).toBe('varies');
  });

  test('returns 400 when token is missing', async () => {
    const req = makeRequest('GET', 'http://localhost/api/da-sessions');
    const res = await GET(req);
    const data = await res.json();
    expect(res.status).toBe(400);
    expect(data.error).toBe('token is required');
  });

  test('returns 400 for malformed UUID', async () => {
    const req = makeRequest('GET', 'http://localhost/api/da-sessions?token=not-a-uuid');
    const res = await GET(req);
    const data = await res.json();
    expect(res.status).toBe(400);
    expect(data.error).toBe('invalid token format');
    expect(mockQuery).not.toHaveBeenCalled();
  });

  test('returns 404 when session not found', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [] } as any);
    const req = makeRequest('GET', `http://localhost/api/da-sessions?token=${VALID_UUID}`);
    const res = await GET(req);
    const data = await res.json();
    expect(res.status).toBe(404);
    expect(data.error).toBe('Session not found');
  });

  test('returns empty responses when session has no annotations', async () => {
    const session = { id: 5, address: '5 Test St', dev_type: null, former_council: 'leichhardt', zone: 'R2', created_at: new Date() };
    mockQuery
      .mockResolvedValueOnce({ rows: [session] } as any)
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);
    const req = makeRequest('GET', `http://localhost/api/da-sessions?token=${VALID_UUID}`);
    const res = await GET(req);
    const data = await res.json();
    expect(res.status).toBe(200);
    expect(data.responses).toEqual({});
    expect(data.session.dev_type).toBeNull();
  });
});

describe('PATCH /api/da-sessions', () => {
  test('updates dev_type and returns success', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [], rowCount: 1 } as any);
    const req = makeRequest('PATCH', `http://localhost/api/da-sessions?token=${VALID_UUID}`, {
      dev_type: 'Two-storey rear extension to existing dwelling house',
    });
    const res = await PATCH(req);
    const data = await res.json();
    expect(res.status).toBe(200);
    expect(data.success).toBe(true);
    expect(mockQuery).toHaveBeenCalledWith(
      expect.stringContaining('UPDATE da_sessions SET dev_type'),
      ['Two-storey rear extension to existing dwelling house', VALID_UUID]
    );
  });

  test('clears dev_type when null is passed', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [], rowCount: 1 } as any);
    const req = makeRequest('PATCH', `http://localhost/api/da-sessions?token=${VALID_UUID}`, { dev_type: null });
    const res = await PATCH(req);
    expect(res.status).toBe(200);
    expect(mockQuery).toHaveBeenCalledWith(expect.any(String), [null, VALID_UUID]);
  });

  test('returns 400 when token is missing', async () => {
    const req = makeRequest('PATCH', 'http://localhost/api/da-sessions', { dev_type: 'test' });
    const res = await PATCH(req);
    const data = await res.json();
    expect(res.status).toBe(400);
    expect(data.error).toBe('token is required');
  });

  test('returns 400 for malformed UUID', async () => {
    const req = makeRequest('PATCH', 'http://localhost/api/da-sessions?token=not-a-uuid', { dev_type: 'test' });
    const res = await PATCH(req);
    const data = await res.json();
    expect(res.status).toBe(400);
    expect(data.error).toBe('invalid token format');
    expect(mockQuery).not.toHaveBeenCalled();
  });
});
