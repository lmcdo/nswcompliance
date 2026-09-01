/**
 * Feedback operator alert — unit tests
 * @jest-environment node
 *
 * Until 2026-08-26 nothing told the operator that feedback had arrived. It was
 * written to user_feedback and sat there; the `email` field on the route is the
 * SUBMITTER's contact address, not an alert. Every outreach email asks people
 * to report wrong controls, so an unwatched table turned the campaign into
 * silence nobody saw.
 *
 * The property that matters most here is NOT the wording — it is that a mail
 * problem can never destroy a submission. The insert has already committed by
 * the time we notify, so every failure path must be swallowed.
 */
jest.mock('next/server', () => ({
  NextRequest: jest.fn(),
  NextResponse: { json: jest.fn() },
}));
jest.mock('pg', () => ({ Pool: jest.fn(() => ({ query: jest.fn() })) }));

const mockSend = jest.fn();
jest.mock('resend', () => ({
  Resend: jest.fn(() => ({ emails: { send: mockSend } })),
}));

import { Resend } from 'resend';
import { buildFeedbackAlert, notifyOperator } from '@/app/api/feedback/route';

const BASE = {
  id: 42,
  feedbackType: 'data_accuracy',
  severity: 'high',
  userType: 'town_planner',
  address: '12 Test St, Marrickville NSW 2204',
  section: 'Setbacks',
  text: 'The front setback says 6m, the DCP says 4.5m.',
  contactEmail: 'planner@example.com',
  cohort: null as string | null,
};

describe('buildFeedbackAlert', () => {
  it('puts the type and the address in the subject', () => {
    const { subject } = buildFeedbackAlert(BASE);
    expect(subject).toContain('data_accuracy');
    expect(subject).toContain('12 Test St, Marrickville NSW 2204');
  });

  it('carries the actual complaint, not just metadata', () => {
    // An alert that says "feedback arrived" without saying what it was still
    // costs a database round trip to action, which is the problem being fixed.
    const { text } = buildFeedbackAlert(BASE);
    expect(text).toContain('The front setback says 6m, the DCP says 4.5m.');
    expect(text).toContain('planner@example.com');
    expect(text).toContain('Feedback id 42.');
  });

  it('tags the cohort in the subject so a class groups in the inbox', () => {
    const { subject, text } = buildFeedbackAlert({ ...BASE, cohort: 'UTS-16658' });
    expect(subject).toContain('[UTS-16658]');
    expect(text).toContain('Cohort:   UTS-16658');
  });

  it('omits the cohort tag entirely when there is none', () => {
    const { subject, text } = buildFeedbackAlert(BASE);
    expect(subject).not.toContain('[');
    expect(text).not.toContain('Cohort:');
  });

  it('says so when the sender left no contact address', () => {
    // Silently rendering "undefined" here would read as a broken address.
    const { text } = buildFeedbackAlert({ ...BASE, contactEmail: null });
    expect(text).toContain('(no contact address)');
    expect(text).not.toContain('undefined');
  });

  it('joins on real newlines, not a literal backslash-n', () => {
    // The first implementation had its escape mangled in transit and emitted a
    // raw newline inside the string literal, which did not compile.
    const { text } = buildFeedbackAlert(BASE);
    expect(text.split('\n').length).toBeGreaterThan(5);
    const literalBackslashN = String.fromCharCode(92) + 'n';
    expect(text).not.toContain(literalBackslashN);
  });
});

describe('notifyOperator never costs the submitter their feedback', () => {
  const KEY = process.env.RESEND_API_KEY;
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.RESEND_API_KEY = 'test-key';
  });
  afterAll(() => {
    if (KEY === undefined) delete process.env.RESEND_API_KEY;
    else process.env.RESEND_API_KEY = KEY;
  });

  it('sends when a key is configured, and reports acceptance', async () => {
    mockSend.mockResolvedValue({});
    await expect(notifyOperator(BASE)).resolves.toBe(true);
    expect(mockSend).toHaveBeenCalledTimes(1);
    const arg = mockSend.mock.calls[0][0];
    expect(arg.to).not.toMatch(/@plotdetect\.com\.au$/);  // self-send quarantine
  });

  it('AWAITS the send, so a frozen instance cannot cancel it', async () => {
    // The original implementation did not await. On serverless the instance can
    // be frozen the moment the response returns, cancelling the in-flight
    // request: the insert commits and the alert never goes, which looks exactly
    // like the bug this feature exists to fix. Asserting the promise has settled
    // by the time notifyOperator resolves is what pins the await in place.
    let settled = false;
    mockSend.mockImplementation(
      () => new Promise((r) => setTimeout(() => { settled = true; r({}); }, 10)),
    );
    await notifyOperator(BASE);
    expect(settled).toBe(true);
  });

  it('does not reject when the Resend constructor throws', async () => {
    (Resend as unknown as jest.Mock).mockImplementationOnce(() => {
      throw new Error('malformed API key');
    });
    await expect(notifyOperator(BASE)).resolves.toBe(false);
  });

  it('does not reject when the send rejects, and reports the failure', async () => {
    mockSend.mockRejectedValue(new Error('resend 503'));
    await expect(notifyOperator(BASE)).resolves.toBe(false);
  });

  it('is a no-op without a key, and says so rather than erroring', async () => {
    delete process.env.RESEND_API_KEY;
    await expect(notifyOperator(BASE)).resolves.toBe(false);
    expect(mockSend).not.toHaveBeenCalled();
  });
});
