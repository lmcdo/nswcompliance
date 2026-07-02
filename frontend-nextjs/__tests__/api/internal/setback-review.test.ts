/**
 * Setback value review — write-back API tests.
 * Verifies each decision maps to the correct, reversible, single-row DB write,
 * and that a correction cannot enter without a source citation.
 * @jest-environment node
 */
import { POST } from '@/app/api/internal/setback-review/[id]/route';

jest.mock('@/lib/database/pool-manager', () => ({ getPool: jest.fn() }));
jest.mock('@/lib/supabase/server', () => ({ createClient: jest.fn() }));

import { getPool } from '@/lib/database/pool-manager';
import { createClient } from '@/lib/supabase/server';

const mockGetPool = getPool as jest.MockedFunction<typeof getPool>;
const mockCreateClient = createClient as unknown as jest.Mock;

let poolQuery: jest.Mock;
let clientQuery: jest.Mock;
let clientRelease: jest.Mock;

function installPool() {
  poolQuery = jest.fn();
  clientQuery = jest.fn();
  clientRelease = jest.fn();
  const client = { query: clientQuery, release: clientRelease };
  mockGetPool.mockReturnValue({ query: poolQuery, connect: jest.fn().mockResolvedValue(client) } as never);
}

function req(body: object) {
  return new Request('http://localhost/api/internal/setback-review/30', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
const params = (id = '30') => ({ params: Promise.resolve({ id }) });

beforeEach(() => {
  jest.clearAllMocks();
  installPool();
  mockCreateClient.mockResolvedValue({
    auth: { getUser: jest.fn().mockResolvedValue({ data: { user: { email: 'rev@x.com' } } }) },
  });
});

describe('POST /api/internal/setback-review/[id] — validation', () => {
  test('rejects an unknown action', async () => {
    const res = await POST(req({ action: 'nuke' }), params());
    expect(res.status).toBe(400);
    expect(poolQuery).not.toHaveBeenCalled();
  });

  test('rejects a non-numeric id', async () => {
    const res = await POST(req({ action: 'confirm' }), params('abc'));
    expect(res.status).toBe(400);
  });
});

describe('confirm', () => {
  test('clears needs_review on the live row only, keeping the value', async () => {
    poolQuery.mockResolvedValueOnce({ rowCount: 1 });
    const res = await POST(req({ action: 'confirm' }), params());
    expect(res.status).toBe(200);
    const [sql, args] = poolQuery.mock.calls[0];
    expect(sql).toMatch(/needs_review = FALSE/);
    expect(sql).toMatch(/is_current = TRUE AND needs_review = TRUE/);
    expect(args[1]).toBe(30);
    // value columns are never touched by confirm
    expect(sql).not.toMatch(/value_min\s*=/);
  });

  test('404 when the row is already resolved', async () => {
    poolQuery.mockResolvedValueOnce({ rowCount: 0 });
    const res = await POST(req({ action: 'confirm' }), params());
    expect(res.status).toBe(404);
  });
});

describe('remove', () => {
  test('reversibly retires the row via is_current=FALSE (no hard delete)', async () => {
    poolQuery.mockResolvedValueOnce({ rowCount: 1 });
    const res = await POST(req({ action: 'remove' }), params());
    expect(res.status).toBe(200);
    const [sql] = poolQuery.mock.calls[0];
    expect(sql).toMatch(/is_current = FALSE/);
    expect(sql).not.toMatch(/DELETE/i);
  });
});

describe('fix — requires a cited, valued correction', () => {
  test('rejects a correction with no value', async () => {
    const res = await POST(req({ action: 'fix', section_ref: 'Part C 4.2' }), params());
    expect(res.status).toBe(400);
    expect(clientQuery).not.toHaveBeenCalled();
  });

  test('rejects a correction with no source citation', async () => {
    const res = await POST(req({ action: 'fix', value_min: 6 }), params());
    expect(res.status).toBe(400);
    expect(clientQuery).not.toHaveBeenCalled();
  });

  test('supersedes: retires the old row and inserts a corrected, cited row in a transaction', async () => {
    clientQuery
      .mockResolvedValueOnce({}) // BEGIN
      .mockResolvedValueOnce({ rows: [{ provision_id: 5, lga: 'CUMBERLAND', dev_type: 'dwelling_house', control_type: 'rear_setback', unit: 'm', condition: null, applicability: 'universal_residential', source_chapter_key: 'ch1', value_min: 8, value_max: null }] }) // SELECT FOR UPDATE
      .mockResolvedValueOnce({}) // UPDATE old
      .mockResolvedValueOnce({ rows: [{ id: 999 }] }) // INSERT new
      .mockResolvedValueOnce({}); // COMMIT

    const res = await POST(
      req({ action: 'fix', value_min: 6, section_ref: 'Part C 4.2.1', source_text: 'Rear setback minimum 6m' }),
      params(),
    );
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.new_id).toBe(999);

    const calls = clientQuery.mock.calls.map((c) => String(c[0]));
    expect(calls[0]).toBe('BEGIN');
    expect(calls[1]).toMatch(/SELECT[\s\S]*FOR UPDATE/);
    expect(calls[2]).toMatch(/UPDATE dcp_setback_controls[\s\S]*is_current = FALSE/);
    expect(calls[3]).toMatch(/INSERT INTO dcp_setback_controls/);
    expect(calls[4]).toBe('COMMIT');
    // the corrected value + its citation are the inserted params
    const insertArgs = clientQuery.mock.calls[3][1];
    expect(insertArgs).toContain(6);            // corrected value_min
    expect(insertArgs).toContain('Part C 4.2.1'); // required section_ref
    expect(clientRelease).toHaveBeenCalled();
  });

  test('rolls back and 404s when the row is gone', async () => {
    clientQuery
      .mockResolvedValueOnce({}) // BEGIN
      .mockResolvedValueOnce({ rows: [] }) // SELECT FOR UPDATE -> none
      .mockResolvedValueOnce({}); // ROLLBACK
    const res = await POST(req({ action: 'fix', value_min: 6, section_ref: 'X' }), params());
    expect(res.status).toBe(404);
    const calls = clientQuery.mock.calls.map((c) => String(c[0]));
    expect(calls).toContain('ROLLBACK');
    expect(clientRelease).toHaveBeenCalled();
  });
});
