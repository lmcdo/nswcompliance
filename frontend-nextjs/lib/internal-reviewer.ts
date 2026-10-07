// prior-art-checked: reuse not viable -- the internal routes each carried their own
// `denyIfUnauthenticated` (dcp-review, pipeline-status, structure-labels), and every copy
// returned null unless NEXT_PUBLIC_AUTH_ENABLED was 'true'. No allowlist exists anywhere
// (grep ALLOWED_EMAILS|REVIEWER|ALLOWLIST, 2026-10-07; ADMIN_EMAIL is a notification address).
/**
 * Who may read or decide the internal review queues.
 *
 * Measured 2026-10-07: with NEXT_PUBLIC_AUTH_ENABLED unset in production, the page gate and
 * the route gates were all no-ops, so canibuildit.com.au/api/dcp-review served the queue to
 * anyone, and its POST routes -- including one that saves `edited_text` and marks the row
 * `grounded`, and setback-review's `fix`, which INSERTs a live dcp_setback_controls row --
 * accepted a verdict from anyone. A signed-in user is not enough either: login is a magic
 * link that creates an account for any email address.
 *
 * So the gate is an allowlist, INTERNAL_REVIEWER_EMAILS (comma-separated), and it does not
 * read NEXT_PUBLIC_AUTH_ENABLED. An unset allowlist DENIES -- a review route that cannot say
 * who may use it serves no one, rather than everyone.
 */
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export function reviewerAllowlist(raw: string | undefined = process.env.INTERNAL_REVIEWER_EMAILS): Set<string> {
  return new Set(
    (raw ?? '')
      .split(',')
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean),
  );
}

/**
 * The signed-in user's email (null when there is no session), or 'unavailable' when the
 * auth service could not be asked -- an outage is not the caller's fault, and reporting it
 * as 401 would send a real reviewer to /login to fix something that is not theirs.
 */
async function sessionEmail(): Promise<string | null | 'unavailable'> {
  try {
    const supabase = await createClient();
    const { data } = await supabase.auth.getUser();
    const email = data?.user?.email;
    return typeof email === 'string' && email.trim() ? email.trim().toLowerCase() : null;
  } catch {
    return 'unavailable';
  }
}

/** The reviewer's email when the session belongs to an allowlisted reviewer, else null. */
export async function currentReviewer(): Promise<string | null> {
  const allowed = reviewerAllowlist();
  if (allowed.size === 0) return null;
  const email = await sessionEmail();
  return email && email !== 'unavailable' && allowed.has(email) ? email : null;
}

export type ReviewerCheck = { reviewer: string; denied: null } | { reviewer: null; denied: NextResponse };

/** Route guard: the named reviewer, or the response to return instead. */
export async function requireReviewer(): Promise<ReviewerCheck> {
  const allowed = reviewerAllowlist();
  if (allowed.size === 0) {
    return {
      reviewer: null,
      denied: NextResponse.json(
        { error: 'review routes are disabled: INTERNAL_REVIEWER_EMAILS is not set' },
        { status: 503 },
      ),
    };
  }
  const email = await sessionEmail();
  if (email === 'unavailable') {
    return {
      reviewer: null,
      denied: NextResponse.json({ error: 'sign-in service unavailable' }, { status: 503 }),
    };
  }
  if (!email) {
    return { reviewer: null, denied: NextResponse.json({ error: 'unauthorised' }, { status: 401 }) };
  }
  if (!allowed.has(email)) {
    return { reviewer: null, denied: NextResponse.json({ error: 'forbidden' }, { status: 403 }) };
  }
  return { reviewer: email, denied: null };
}
