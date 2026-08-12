/**
 * Feedback routes — invalid-input contract
 * @jest-environment node
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * These four routes had NO test that submits bad data. The zod 3 -> 4 upgrade
 * (#924) broke them in two ways, and only one of the two was catchable by tsc:
 *
 *   1. ZodError.errors -> .issues. Reading the old name threw, so invalid input
 *      returned 500 instead of 400. tsc DID catch this.
 *   2. The fields INSIDE each issue were renamed too (code 'invalid_string' ->
 *      'invalid_format', new 'format'/'origin'). These routes returned those raw
 *      objects to the browser as `details`, so a client reading details[0].code
 *      silently stopped matching. Still 400, still an array — nothing errored.
 *      tsc could NOT catch this. A cross-review did.
 *
 * So both assertions below are load-bearing, and the second one is the whole
 * point: `details` must be a stable string[], never raw zod issue objects.
 */

import { NextRequest } from 'next/server';

// The routes INSERT on the success path only, but the module imports it at load.
jest.mock('@/lib/db', () => ({
  query: jest.fn().mockResolvedValue({ rows: [{ up_votes: 0, down_votes: 0 }] }),
}));

jest.mock('next/server', () => jest.requireActual('next/server'));

import { POST as requirementPOST } from '@/app/api/feedback/requirement/route';
import { POST as submitPOST } from '@/app/api/feedback/submit/route';
import { POST as suggestionPOST } from '@/app/api/feedback/suggestion/route';
import { POST as votePOST } from '@/app/api/feedback/vote/route';

type Handler = (req: NextRequest) => Promise<Response>;

function makeRequest(path: string, body: unknown): NextRequest {
  return new NextRequest(`http://localhost/api/feedback/${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/**
 * Each case carries a body that the route's schema rejects.
 *
 * requirement and submit reject via validateRequest (the early-return path).
 * suggestion and vote reject via schema.parse() throwing, caught by the
 * `error instanceof z.ZodError` branch — that branch is the one #924 changed,
 * so it is the one that most needs covering.
 */
const CASES: Array<{
  name: string;
  path: string;
  handler: Handler;
  invalidBody: unknown;
  rejectsVia: string;
}> = [
  {
    name: 'requirement',
    path: 'requirement',
    handler: requirementPOST as Handler,
    // provisionId must be a uuid; feedback must be >= 10 chars; isCorrect required
    invalidBody: { provisionId: 'not-a-uuid', feedback: 'short', isCorrect: 'yes' },
    rejectsVia: 'validateRequest early return',
  },
  {
    name: 'submit',
    path: 'submit',
    handler: submitPOST as Handler,
    // text must be >= 10 chars; email must be a valid address
    invalidBody: { text: 'tiny', email: 'not-an-email' },
    rejectsVia: 'validateRequest early return',
  },
  {
    name: 'suggestion',
    path: 'suggestion',
    handler: suggestionPOST as Handler,
    // type must be the literal 'user_suggestion'; context object is required
    invalidBody: { type: 'wrong_literal', description: '' },
    rejectsVia: 'ZodError caught in catch block',
  },
  {
    name: 'vote',
    path: 'vote',
    handler: votePOST as Handler,
    // voteType must be 'up' | 'down'; requirementId/propertyAddress required
    invalidBody: { requirementId: 'abc', propertyAddress: '1 Test St', voteType: 'sideways' },
    rejectsVia: 'ZodError caught in catch block',
  },
];

describe.each(CASES)(
  'POST /api/feedback/$name — invalid input ($rejectsVia)',
  ({ path, handler, invalidBody }) => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    it('answers 400, not 500', async () => {
      const res = await handler(makeRequest(path, invalidBody));
      // Guards regression 1: reading a renamed ZodError property throws inside
      // the handler, which surfaces as 500. 400 is the only correct answer to
      // input the schema rejects.
      expect(res.status).toBe(400);
    });

    it('returns details as an array of plain strings, never raw zod issue objects', async () => {
      const res = await handler(makeRequest(path, invalidBody));
      const json = await res.json();

      expect(Array.isArray(json.details)).toBe(true);
      expect(json.details.length).toBeGreaterThan(0);

      // Guards regression 2 — the one tsc cannot see. If a future upgrade goes
      // back to handing zod's own issue objects to the browser, these are
      // objects with .code/.path, not strings, and this fails.
      for (const entry of json.details) {
        expect(typeof entry).toBe('string');
      }
      expect(json.details.some((d: string) => d.length > 0)).toBe(true);
    });

    it('does not leak zod internal field names into the response body', async () => {
      const res = await handler(makeRequest(path, invalidBody));
      const raw = JSON.stringify(await res.json());

      // 'invalid_format' and 'origin' are zod 4 issue-object internals. Their
      // presence means raw issues reached the client again.
      expect(raw).not.toMatch(/"code"\s*:/);
      expect(raw).not.toMatch(/"origin"\s*:/);
    });
  }
);
