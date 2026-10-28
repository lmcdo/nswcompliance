/**
 * Operator alert for a new lead: plain text, reply goes to the lead, and the
 * alert says when the person's own email did not go (so it gets a hand reply).
 * @jest-environment node
 */
jest.mock('next/server', () => ({ NextResponse: { json: jest.fn() } }));
jest.mock('@/lib/supabase/server', () => ({ createClient: jest.fn() }));
jest.mock('resend', () => ({ Resend: jest.fn(() => ({ emails: { send: jest.fn() } })) }));

import { buildLeadAlert, type LeadAlertFields } from '@/app/api/canibuildit/lead/route';

const BASE: LeadAlertFields = {
  id: 7, email: 'owner@example.com', firstName: 'Sam', phone: null,
  address: '12 Test St, Goulburn NSW 2580', interestType: 'granny-flat-referral',
  lgaName: 'Goulburn Mulwaree', eligible: true,
  qualification: { timeline: '1-3m', ownership: 'owner', finance: null, budget: null },
  emailSent: true, consentWording: 'Share my name with a granny flat builder.',
};

it('carries what is needed to act on the lead', () => {
  const { subject, text } = buildLeadAlert(BASE);
  expect(subject).toBe('Lead: granny-flat-referral - 12 Test St, Goulburn NSW 2580');
  expect(text).toContain('Sam <owner@example.com>');
  expect(text).toContain('Council:   Goulburn Mulwaree');
  expect(text).toContain('Answers:   timeline=1-3m, ownership=owner');
  expect(text).toContain('Wording on the form: "Share my name with a granny flat builder."');
  expect(text).toContain('Lead id 7.');
});

it('does not guess a product when none was stated', () => {
  const { subject, text } = buildLeadAlert({ ...BASE, interestType: null });
  expect(subject).toMatch(/^Lead: \(not stated\)/);
  expect(text).toContain('Type:      (not stated)');
});

it('flags a confirmation email that did not go', () => {
  expect(buildLeadAlert({ ...BASE, emailSent: false }).text).toContain('Their email sent: NO - reply by hand');
});

it('says when no consent wording was recorded, and omits empty lines', () => {
  const { text } = buildLeadAlert({ ...BASE, consentWording: null, lgaName: null, eligible: null, qualification: null });
  expect(text).toContain('No consent wording recorded.');
  expect(text).not.toMatch(/Council:|Eligible:|Answers:/);
});
