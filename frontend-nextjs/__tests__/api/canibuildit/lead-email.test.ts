/**
 * buildEmailContent — unit tests
 * @jest-environment node
 *
 * Tests: each product type, alias keys, default/unknown fallback.
 */

// Mock heavy Next.js / Supabase / Resend deps so we can import the module cleanly
jest.mock('next/server', () => ({ NextResponse: { json: jest.fn() } }));
jest.mock('@/lib/supabase/server', () => ({ createClient: jest.fn() }));
jest.mock('resend', () => ({ Resend: jest.fn(() => ({ emails: { send: jest.fn() } })) }));

import { buildEmailContent } from '@/app/api/canibuildit/lead/route';

const ADDR = '12 Test St, Marrickville NSW 2204';

describe('buildEmailContent', () => {
  describe('granny-flat', () => {
    it('returns granny-flat subject with address', () => {
      const { subject } = buildEmailContent('granny-flat', ADDR);
      expect(subject).toMatch(/granny flat/i);
      expect(subject).toContain(ADDR);
    });

    it('body explains the wait', () => {
      const { body } = buildEmailContent('granny-flat', ADDR);
      expect(body).toMatch(/1.3 minutes|1–3 minutes/i);
      expect(body).toContain(ADDR);
    });
  });

  describe('flood / flood-truth aliases', () => {
    it('"flood" returns flood subject', () => {
      const { subject } = buildEmailContent('flood', ADDR);
      expect(subject).toMatch(/flood risk/i);
      expect(subject).toContain(ADDR);
    });

    it('"flood-truth" alias resolves to same copy', () => {
      const a = buildEmailContent('flood', ADDR);
      const b = buildEmailContent('flood-truth', ADDR);
      expect(a.subject).toBe(b.subject);
      expect(a.body).toBe(b.body);
    });
  });

  describe('solar-yield / solar aliases', () => {
    it('"solar-yield" returns solar subject', () => {
      const { subject } = buildEmailContent('solar-yield', ADDR);
      expect(subject).toMatch(/solar yield/i);
      expect(subject).toContain(ADDR);
    });

    it('"solar" alias resolves to same copy', () => {
      const a = buildEmailContent('solar-yield', ADDR);
      const b = buildEmailContent('solar', ADDR);
      expect(a.subject).toBe(b.subject);
      expect(a.body).toBe(b.body);
    });
  });

  describe('shadow', () => {
    it('returns shadow subject with address', () => {
      const { subject } = buildEmailContent('shadow', ADDR);
      expect(subject).toMatch(/shadow/i);
      expect(subject).toContain(ADDR);
    });

    it('body contains address', () => {
      const { body } = buildEmailContent('shadow', ADDR);
      expect(body).toContain(ADDR);
    });
  });

  describe('threat-radar', () => {
    it('returns threat-radar subject with address', () => {
      const { subject } = buildEmailContent('threat-radar', ADDR);
      expect(subject).toMatch(/threat radar/i);
      expect(subject).toContain(ADDR);
    });

    it('body mentions DA activity', () => {
      const { body } = buildEmailContent('threat-radar', ADDR);
      expect(body).toMatch(/DA activity/i);
    });
  });

  describe('dual-occ-referral', () => {
    it('returns builder-introduction subject with address', () => {
      const { subject } = buildEmailContent('dual-occ-referral', ADDR);
      expect(subject).toMatch(/builder introduction/i);
      expect(subject).toContain(ADDR);
    });

    it('body discloses the referral fee and consent scope', () => {
      const { body } = buildEmailContent('dual-occ-referral', ADDR);
      expect(body).toMatch(/referral fee/i);
      expect(body).toMatch(/only for this introduction/i);
      expect(body).toContain(ADDR);
    });
  });

  describe('lga-request', () => {
    it('returns a request-noted subject', () => {
      const { subject } = buildEmailContent('lga-request', ADDR);
      expect(subject).toMatch(/request noted/i);
    });

    it('body explains demand-ordered loading without promising a date', () => {
      const { body } = buildEmailContent('lga-request', ADDR);
      expect(body).toMatch(/order of demand/i);
      expect(body).not.toMatch(/\bweeks?\b|\bdays?\b|\bsoon\b/i);
    });
  });

  describe('intelligence-brief', () => {
    it('returns Site Report subject with address', () => {
      const { subject } = buildEmailContent('intelligence-brief', ADDR);
      expect(subject).toMatch(/Site Report/i);
      expect(subject).toContain(ADDR);
    });

    it('body links to the verify.plotdetect.com.au domain (not canibuildit.com.au)', () => {
      const { body } = buildEmailContent('intelligence-brief', ADDR);
      expect(body).toMatch(/verify\.plotdetect\.com\.au/);
      expect(body).not.toMatch(/canibuildit\.com\.au/);
      expect(body).toContain(ADDR);
    });
  });

  describe('default fallback', () => {
    it('unknown product falls back to granny-flat copy', () => {
      const unknown = buildEmailContent('unknown-product', ADDR);
      const fallback = buildEmailContent('granny-flat', ADDR);
      expect(unknown.subject).toBe(fallback.subject);
    });

    it('each product returns distinct subject lines', () => {
      const products = ['granny-flat', 'flood', 'solar-yield', 'shadow', 'threat-radar'];
      const subjects = products.map(p => buildEmailContent(p, ADDR).subject);
      const unique = new Set(subjects);
      expect(unique.size).toBe(products.length);
    });
  });
});
