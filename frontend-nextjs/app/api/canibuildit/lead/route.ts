import { NextRequest, NextResponse } from 'next/server';
import { promises as dns } from 'dns';
import { z } from 'zod';
import { createClient as createServiceClient } from '@supabase/supabase-js';
import { getResend } from '@/lib/resend-client';
import { checkRateLimit, createRateLimitHeaders, getClientIdentifier } from '@/lib/rate-limit';
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';
import { dualOccEligible, type UpzoningResult } from '@/lib/upzoning';

// Service role client — bypasses RLS, server-only, never exposed to browser.
const getSupabase = () =>
  createServiceClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  );

// ============================================================================
// MX DOMAIN CHECK
// Verifies the email domain has real mail servers before storing.
// Catches obviously fake domains (test@aslkjdf.xyz) without blocking real users.
// Times out at 3s — if DNS is slow, we pass through rather than block a real user.
// ============================================================================

async function emailDomainHasMx(email: string): Promise<boolean> {
  const domain = email.split('@')[1];
  if (!domain) return false;
  try {
    const timeout = new Promise<false>((resolve) => setTimeout(() => resolve(false), 3000));
    const lookup = dns.resolveMx(domain).then((records) => records.length > 0).catch(() => false);
    return await Promise.race([lookup, timeout]);
  } catch {
    return true; // fail open — don't block real users on DNS errors
  }
}

// ============================================================================
// RATE LIMITER — 3 submissions per IP per 10 minutes
// Tighter than global (100/min) because this writes to DB and sends email.
// ============================================================================

const redis =
  process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
    ? new Redis({
        url: process.env.UPSTASH_REDIS_REST_URL,
        token: process.env.UPSTASH_REDIS_REST_TOKEN,
      })
    : null;

const leadRateLimiter = redis
  ? new Ratelimit({
      redis,
      limiter: Ratelimit.slidingWindow(3, '10 m'),
      analytics: true,
      prefix: 'rl:lead',
    })
  : null;

// ============================================================================
// VERDICT RECOMPUTATION — Sol HIGH 0.99, PR #1015
//
// `eligible` in the request body is CLIENT-SUPPLIED and unverified — email,
// address and eligible are three unrelated fields in one flat JSON body, and
// nothing binds them together. Two interest_types treat it as a stated fact
// rather than inert data:
//   - 'duplex-result': the confirmation EMAIL asserts a definite verdict
//     sentence ("you can apply to build a duplex here...") built straight
//     from the client's boolean.
//   - 'dual-occ-referral': the value is stored and later rendered as
//     "Eligible"/"Not eligible"/"Needs checking" to staff on the internal
//     leads dashboard (app/internal/leads/page.tsx) — a false claim there
//     misleads a human into connecting a builder to an ineligible property,
//     not just a misleading email.
// A caller can POST any (email, address, eligible) combination directly —
// no UI is required to reach this route — so client trust must be removed
// at the boundary, not patched per-caller.
//
// Fix: for these two interest_types, IGNORE the client's `eligible` and
// recompute it server-side from the submitted `address`, using the exact
// pipeline /api/upzoning proxies to (services/upzoning_check.py ->
// housing_sepp_eligibility) — the same source of truth the on-screen verdict
// already came from moments earlier. This also closes a broader hole than
// originally scoped: previously a caller could pair ANY address with ANY
// eligible value; recomputing means whatever address is submitted is what
// the stored/emailed verdict actually describes.
//
// Fail-closed, three states, never two: recompute failure (network error,
// timeout, non-2xx, malformed JSON) or an indeterminate pipeline result
// (status !== 'ok' — not_residential/unavailable) both resolve to `null`
// (the existing neutral copy — "Your duplex check has been run for this
// address" / stored as unknown), never a default `true` and never let an
// upstream failure quietly collapse into a false "not eligible". Missing
// address for one of these interest_types is treated the same way: null,
// not "assume ineligible".
// ============================================================================

const VERDICT_BEARING_INTEREST_TYPES = new Set(['duplex-result', 'dual-occ-referral']);

// Generous relative to typical pipeline latency, bounded relative to this
// route's own purpose (a "thanks, check your email" confirmation call, not
// the primary interactive check the user already waited through on-screen
// seconds earlier). A timeout here costs one user a neutral email instead of
// the specific one — it can never produce a false claim, so erring toward a
// shorter bound is the safe direction if this needs retuning later.
const RECOMPUTE_TIMEOUT_MS = 20_000;

// Runtime validation of the pipeline's response — a TypeScript `as UpzoningResult`
// assertion alone (the original shape of this fix) trusts the external service's
// JSON without checking it, so a malformed status:'ok' payload (Sol HIGH 0.9,
// e.g. eligible arriving as the STRING "false") could cross the boundary and be
// read as truthy by dualOccEligible's `f.eligible` check, producing exactly the
// false positive this whole fix exists to prevent — just moved from the client
// to a misbehaving upstream service instead. Scoped to only the fields
// dualOccEligible actually reads (status, forms[].development_type/.eligible);
// .passthrough() lets every other field ride along unvalidated since nothing
// here touches them.
const RecomputeResponseSchema = z.object({
  status: z.enum(['ok', 'not_residential', 'unavailable']),
  // Required, not defaulted: the real contract always includes forms (see
  // frontend-nextjs/lib/upzoning.ts's UpzoningResult), so a status:'ok'
  // response missing it entirely is itself malformed and should fail
  // validation -> null, not silently read as "zero forms, so not eligible" --
  // a determinate-looking answer the response never actually grounded.
  forms: z.array(
    z.object({
      development_type: z.string(),
      eligible: z.boolean(),
    }).passthrough(),
  ),
}).passthrough();

export async function recomputeDualOccEligible(address: string): Promise<boolean | null> {
  const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';
  try {
    const resp = await fetch(`${PYTHON_API}/pipeline/upzoning`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address }),
      signal: AbortSignal.timeout(RECOMPUTE_TIMEOUT_MS),
    });
    if (!resp.ok) {
      // Sol MEDIUM 0.99: previously swallowed with zero signal, so a
      // misconfigured PYTHON_API_URL or a systemic pipeline outage would
      // silently degrade every verdict-bearing submission to the neutral
      // copy with nothing in the logs pointing at why. Logging, not
      // retrying or surfacing to the user — the fail-closed behaviour
      // (return null) is unchanged; this only makes it observable.
      console.error(`[canibuildit/lead] upzoning recompute non-2xx: ${resp.status}`);
      return null;
    }
    const raw: unknown = await resp.json();
    const parsed = RecomputeResponseSchema.safeParse(raw);
    if (!parsed.success) {
      console.error('[canibuildit/lead] upzoning recompute response failed validation', parsed.error.flatten());
      return null;
    }
    if (parsed.data.status !== 'ok') return null;
    // parsed.data only statically carries the fields RecomputeResponseSchema
    // checked (status, forms[].development_type/.eligible) plus whatever
    // .passthrough() let through untyped -- dualOccEligible only ever reads
    // the checked fields, so this is safe despite TS seeing an incomplete
    // UpzoningResult; `as unknown as` makes that "trust the rest" step explicit
    // rather than a same-shape cast TS would otherwise (rightly) reject.
    return dualOccEligible(parsed.data as unknown as UpzoningResult);
  } catch (err) {
    console.error('[canibuildit/lead] upzoning recompute threw:', err);
    return null;
  }
}

// ============================================================================
// INPUT SCHEMA
// ============================================================================

// Union of two independent additions to this list, both added since the base
// commit this branch forked from: 'intelligence-brief' (Site Report product)
// and 'duplex-result' (this branch's email-my-result feature). Neither
// supersedes the other.
const INTEREST_TYPES = ['granny-flat', 'flood', 'flood-truth', 'solar-yield', 'solar', 'shadow', 'threat-radar', 'conveyancing', 'pre-da-history', 'dual-occ-referral', 'lga-request', 'intelligence-brief', 'duplex-result'] as const;

const LeadSchema = z.object({
  email: z.string().email('Invalid email address').max(254, 'Email too long'),
  first_name: z.string().max(100, 'Name too long').optional().nullable(),
  phone: z.string().max(40, 'Phone too long').optional().nullable(),
  address: z.string().min(5, 'Address too short').max(200, 'Address too long').optional().nullable(),
  eligible: z.boolean().optional().nullable(),
  lga_name: z.string().max(100, 'LGA name too long').optional().nullable(),
  interest_type: z.enum(INTEREST_TYPES).optional().nullable(),
  // Multi-step qualifier answers — all optional (budget can be skipped).
  qualification: z
    .object({
      timeline: z.string().max(40).optional().nullable(),
      ownership: z.string().max(40).optional().nullable(),
      finance: z.string().max(40).optional().nullable(),
      budget: z.string().max(40).optional().nullable(),
    })
    .optional()
    .nullable(),
  // Consent audit — the exact wording + version the user agreed to, stored so we
  // can prove what a given person consented to (OAIC burden-of-proof).
  consent_version: z.string().max(40).optional().nullable(),
  consent_wording: z.string().max(1000).optional().nullable(),
  // Honeypot — bots fill this, humans don't. Must be present in form but hidden via CSS.
  // Accept any string (don't 400 bots — they'd retry with different payloads).
  // Silently discard after parsing if non-empty.
  website: z.string().optional(),
});

// ============================================================================
// HANDLER
// ============================================================================

export async function POST(req: NextRequest) {
  // --- 1. Per-IP rate limit ---
  const ip = getClientIdentifier(req);
  const rlResult = await checkRateLimit(ip, leadRateLimiter, 3, 10 * 60 * 1000);
  if (!rlResult.success) {
    return NextResponse.json(
      { error: 'Too many submissions. Please wait a few minutes.' },
      { status: 429, headers: createRateLimitHeaders(rlResult) }
    );
  }

  // --- 2. Parse + validate ---
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }

  const parsed = LeadSchema.safeParse(body);
  if (!parsed.success) {
    const firstError = parsed.error.issues[0]?.message ?? 'Invalid input';
    return NextResponse.json({ error: firstError }, { status: 400 });
  }

  const {
    email, first_name, phone, address, eligible, lga_name, interest_type,
    qualification, consent_version, consent_wording, website,
  } = parsed.data;

  // --- 3. Honeypot check — silent success so bots don't know they're blocked ---
  if (website) {
    return NextResponse.json({ ok: true });
  }

  const cleanEmail = email.trim().toLowerCase();
  const cleanAddress = address?.trim() || null;

  // --- 4. MX domain check — reject obviously fake email domains ---
  const domainValid = await emailDomainHasMx(cleanEmail);
  if (!domainValid) {
    return NextResponse.json({ error: 'Please use a valid email address.' }, { status: 400 });
  }

  // --- 5. Duplicate detection — same email+address within 24h ---
  try {
    const supabase = getSupabase();
    const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    const { data: existing } = await supabase
      .from('canibuildit_leads')
      .select('id')
      .eq('email', cleanEmail)
      .eq('address', cleanAddress ?? '')
      .gte('created_at', since)
      .limit(1);

    if (existing && existing.length > 0) {
      // Already stored — still send response but skip DB insert + email
      return NextResponse.json({ ok: true });
    }
  } catch {
    // Non-blocking — if dupe check fails, proceed anyway
  }

  // --- 6. Recompute eligibility server-side for verdict-bearing interest_types.
  // The client's `eligible` is discarded entirely here, not merely double-checked —
  // see the VERDICT RECOMPUTATION block above for why. Runs after the honeypot and
  // duplicate-detection early returns so a bot or a repeat submission never spends
  // a Housing-SEPP pipeline call.
  const verifiedEligible: boolean | null =
    interest_type && VERDICT_BEARING_INTEREST_TYPES.has(interest_type) && cleanAddress
      ? await recomputeDualOccEligible(cleanAddress)
      : null;

  // Visibility, not enforcement: verifiedEligible is already what gets stored
  // and emailed below regardless, so this can't be bypassed by a mismatch —
  // it only logs when a caller's claim disagrees with the recomputed truth.
  // Not proof of malice on its own (a stale on-screen result submitted after a
  // genuine same-day amendment would also land here), but a sustained pattern
  // for one IP/address is worth knowing about, and there was no signal at all
  // for this before.
  if (
    interest_type && VERDICT_BEARING_INTEREST_TYPES.has(interest_type) &&
    typeof eligible === 'boolean' && verifiedEligible !== null &&
    eligible !== verifiedEligible
  ) {
    console.warn('[canibuildit/lead] client eligible claim did not match recomputed verdict', {
      interest_type, address: cleanAddress, ip, client_claimed: eligible, server_recomputed: verifiedEligible,
    });
  }

  // --- 7. Store lead ---
  try {
    const supabase = getSupabase();
    // Build the consent audit only when a consent statement was actually shown,
    // capturing the exact wording/version + server-side IP + timestamp.
    const consentRecord =
      consent_version || consent_wording
        ? {
            version: consent_version ?? null,
            wording: consent_wording ?? null,
            shared_with: 'duplex-referral-partner',
            ip,
            captured_at: new Date().toISOString(),
          }
        : null;
    await supabase.from('canibuildit_leads').insert({
      email: cleanEmail,
      address: cleanAddress,
      eligible: verifiedEligible,
      ...(first_name ? { first_name: first_name.trim() } : {}),
      ...(phone ? { phone: phone.trim() } : {}),
      ...(lga_name ? { lga_name: lga_name.trim() } : {}),
      ...(interest_type ? { interest_type: interest_type.trim() } : {}),
      ...(qualification ? { qualification } : {}),
      ...(consentRecord ? { consent: consentRecord } : {}),
    });
  } catch {
    // Non-blocking — don't error the user if DB insert fails
  }

  // --- 8. Send confirmation email ---
  const addressLabel = cleanAddress ?? 'your property';
  const { subject, body: emailBody } = buildEmailContent(interest_type ?? 'granny-flat', addressLabel, verifiedEligible);
  // Sender brand follows the product, not one hardcoded consumer identity —
  // intelligence-brief is the PlotDetect (verify./brief. subdomain) product,
  // distinct from the canibuildit.com.au consumer tools every other
  // interest_type here belongs to.
  const { fromLine, replyTo, footerLabel, footerUrl } =
    interest_type === 'intelligence-brief'
      ? {
          fromLine: 'PlotDetect <info@plotdetect.com.au>',
          replyTo: undefined,
          footerLabel: 'PlotDetect',
          footerUrl: 'https://verify.plotdetect.com.au',
        }
      : {
          fromLine: 'Can I Build It <info@plotdetect.com.au>',
          replyTo: 'hello@canibuildit.com.au',
          footerLabel: 'Can I Build It?',
          footerUrl: 'https://canibuildit.com.au',
        };
  try {
    await getResend()?.emails.send({
      from: fromLine,
      ...(replyTo ? { replyTo } : {}),
      to: [cleanEmail],
      subject,
      html: `
        <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
          ${emailBody}
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
          <p style="color: #999; font-size: 12px;">
            ${footerLabel} &middot; <a href="${footerUrl}" style="color: #0d9488;">${footerUrl.replace('https://', '')}</a>
          </p>
        </div>
      `,
    });
  } catch (emailErr) {
    console.error('[canibuildit/lead] Resend error:', emailErr);
  }

  return NextResponse.json({ ok: true });
}

// address is user-submitted (Zod only bounds its length, not its character set)
// and gets interpolated into an HTML email body — every case below uses the
// escaped value (see safeAddress in buildEmailContent), never the raw address.
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function buildEmailContent(product: string, address: string, eligible: boolean | null = null): { subject: string; body: string } {
  // address is user-submitted (Zod bounds length only, not character set) and
  // gets interpolated into an HTML email body across every case below —
  // escape once here rather than per-case. Subjects use the raw `address`
  // (plain text, never HTML-rendered; escaping there would show literal
  // "&amp;" etc. for a genuine address containing "&").
  const safeAddress = escapeHtml(address);
  switch (product) {
    case 'duplex-result': {
      const verdictLine =
        eligible === true
          ? 'This block meets the mapped Housing SEPP lot standards for a dual occupancy — you can apply to build a duplex here, with consent, through a development application.'
          : eligible === false
            ? 'This block does not meet the mapped duplex standard.'
            : 'Your duplex check has been run for this address.';
      return {
        subject: `Your duplex check result — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your result, saved.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            <strong>${safeAddress}</strong><br/>${verdictLine}
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Keep this email, forward it to whoever needs it, or run the check
            again any time at
            <a href="https://canibuildit.com.au/duplex-check" style="color: #0d9488;">canibuildit.com.au/duplex-check</a>.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Thinking about what it would cost to build? Reply to this email and
            we&rsquo;ll introduce you to a builder who does dual occupancies in
            your area. PlotDetect may receive a referral fee.
          </p>
          <p style="color: #999; font-size: 12px; line-height: 1.6;">
            This is mapped planning data, not planning advice — development
            consent depends on a development application and site-specific
            assessment by the council.
          </p>`,
      };
    }
    case 'flood':
    case 'flood-truth':
      return {
        subject: `Your flood risk result — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your flood risk result is ready.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your flood risk check for <strong>${safeAddress}</strong> is complete.
            Visit <a href="https://canibuildit.com.au/reports/flood" style="color: #0d9488;">canibuildit.com.au/reports/flood</a>
            to run it again or check another address.
          </p>`,
      };
    case 'solar-yield':
    case 'solar':
      return {
        subject: `Your solar yield estimate — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your solar estimate is ready.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your solar yield check for <strong>${safeAddress}</strong> is complete.
            Visit <a href="https://canibuildit.com.au/reports/solar-yield" style="color: #0d9488;">canibuildit.com.au/reports/solar-yield</a>
            to run it again or check another address.
          </p>`,
      };
    case 'shadow':
      return {
        subject: `Your shadow analysis — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your shadow analysis is ready.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your shadow analysis for <strong>${safeAddress}</strong> is complete.
            Visit <a href="https://canibuildit.com.au/reports/shadow" style="color: #0d9488;">canibuildit.com.au/reports/shadow</a>
            to run it again or check another address.
          </p>`,
      };
    case 'threat-radar':
      return {
        subject: `Your Threat Radar result — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your Threat Radar result is ready.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your DA activity check for <strong>${safeAddress}</strong> is complete.
            Visit <a href="https://canibuildit.com.au/reports/threat-radar" style="color: #0d9488;">canibuildit.com.au/reports/threat-radar</a>
            to monitor this address or check another.
          </p>`,
      };
    case 'dual-occ-referral':
      return {
        subject: `Builder introduction request received — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your request is in.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            You asked for an introduction to a builder who does dual occupancies,
            for <strong>${safeAddress}</strong>. We'll email you to arrange it.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your upzoning result stays available — run it again any time at
            <a href="https://verify.plotdetect.com.au/tools/upzoning-check" style="color: #0d9488;">plotdetect.com.au/tools/upzoning-check</a>.
          </p>
          <p style="color: #999; font-size: 12px; line-height: 1.6;">
            PlotDetect may receive a referral fee from the builder. Your details are
            shared only for this introduction.
          </p>`,
      };
    case 'lga-request':
      return {
        subject: 'Request noted — your council is on the list',
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your council request is noted.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            You asked for your council's development control plan numbers to
            be loaded. Councils are added in order of demand — this request
            counts toward that. We'll email you here when it's ready.
          </p>`,
      };
    case 'intelligence-brief':
      return {
        subject: `Your Site Report — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your Site Report is ready.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your Site Report for <strong>${safeAddress}</strong> is complete — planning controls,
            environmental constraints and development capacity, each figure traced to its source.
            Visit <a href="https://verify.plotdetect.com.au/reports/intelligence-brief" style="color: #0d9488;">verify.plotdetect.com.au/reports/intelligence-brief</a>
            to run this or another address again.
          </p>`,
      };
    case 'granny-flat':
    default:
      return {
        subject: `Your granny flat check is running — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">We're on it.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your granny flat check for <strong>${safeAddress}</strong> is running.
            We're pulling live aerial imagery, running satellite structure detection,
            and cross-referencing NSW Planning Portal rules — this takes 1–3 minutes.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            You can close the tab. We'll send your result here as soon as it's ready.
          </p>`,
      };
  }
}
