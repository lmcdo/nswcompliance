/**
 * POST /api/stripe/checkout/shadow -- the shadow tool was turned off 2026-10-22.
 * @jest-environment node
 */

import { NextRequest } from 'next/server';
import { POST } from '@/app/api/stripe/checkout/shadow/route';

describe('POST /api/stripe/checkout/shadow (tool off)', () => {
  it('refuses with 410 and never starts a checkout', async () => {
    const req = new NextRequest('http://localhost/api/stripe/checkout/shadow', {
      method: 'POST',
      body: JSON.stringify({ report_id: 'r1', address: '5 Elm St Haberfield NSW 2045' }),
      headers: { 'Content-Type': 'application/json' },
    });
    const res = await (POST as unknown as (r: NextRequest) => Promise<Response>)(req);
    expect(res.status).toBe(410);
    expect(await res.json()).toEqual({ error: 'The shadow tool has been turned off.' });
  });
});
