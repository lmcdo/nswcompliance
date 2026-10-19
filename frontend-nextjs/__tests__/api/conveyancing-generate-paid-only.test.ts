/**
 * /api/reports/conveyancing/generate makes the PAID conveyancing PDF. Before 2026-10-19 it
 * checked nothing, so anyone who could POST got it for any address. It now needs a Stripe
 * checkout session that is paid, for this product and this report, and takes the address from
 * the session, never from the request.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

const retrieve = jest.fn();
jest.mock('@/lib/stripe-client', () => ({
  getStripe: () => ({ checkout: { sessions: { retrieve } } }),
}));

const fetchMock = jest.fn();
global.fetch = fetchMock as unknown as typeof fetch;

import { POST } from '@/app/api/reports/conveyancing/generate/route';

const req = (body: unknown) =>
  new NextRequest('http://x/api/reports/conveyancing/generate', { method: 'POST', body: JSON.stringify(body) });

const paid = {
  payment_status: 'paid',
  metadata: { product: 'conveyancing-report', report_id: 'r-1', address: '3 Egret Way, Mount Annan', lat: '-34.05', lng: '150.75' },
};

beforeEach(() => {
  process.env.PYTHON_API_URL = 'http://py';
  retrieve.mockReset();
  fetchMock.mockReset();
  fetchMock.mockResolvedValue({ ok: true, json: async () => ({ pdf_url: 'u', report_id: 'r-1', address: 'a' }) });
});

it('refuses a request with no checkout session (the old open path)', async () => {
  const res = await POST(req({ report_id: 'r-1', address: 'any', lat: 1, lng: 2 }));
  expect(res.status).toBe(400);
  expect(fetchMock).not.toHaveBeenCalled();
});

it('refuses an unpaid session', async () => {
  retrieve.mockResolvedValue({ ...paid, payment_status: 'unpaid' });
  expect((await POST(req({ report_id: 'r-1', checkout_session_id: 'cs' }))).status).toBe(403);
  expect(fetchMock).not.toHaveBeenCalled();
});

it('refuses a session paid for a different report or product', async () => {
  retrieve.mockResolvedValue({ ...paid, metadata: { ...paid.metadata, report_id: 'other' } });
  expect((await POST(req({ report_id: 'r-1', checkout_session_id: 'cs' }))).status).toBe(403);
  retrieve.mockResolvedValue({ ...paid, metadata: { ...paid.metadata, product: 'flood-report' } });
  expect((await POST(req({ report_id: 'r-1', checkout_session_id: 'cs' }))).status).toBe(403);
});

it('a paid session generates, using the address from the session', async () => {
  retrieve.mockResolvedValue(paid);
  const res = await POST(req({ report_id: 'r-1', checkout_session_id: 'cs', address: 'ATTACKER ADDRESS' }));
  expect(res.status).toBe(200);
  const sent = JSON.parse(fetchMock.mock.calls[0][1].body);
  expect(sent.address).toBe('3 Egret Way, Mount Annan');
  expect(sent.lat).toBeCloseTo(-34.05);
});

it('an unknown session is refused; Stripe being down is reported as an outage', async () => {
  retrieve.mockRejectedValue({ type: 'StripeInvalidRequestError', code: 'resource_missing' });
  expect((await POST(req({ report_id: 'r-1', checkout_session_id: 'cs' }))).status).toBe(403);
  retrieve.mockRejectedValue(new Error('ECONNRESET'));
  expect((await POST(req({ report_id: 'r-1', checkout_session_id: 'cs' }))).status).toBe(502);
  expect(fetchMock).not.toHaveBeenCalled();
});
