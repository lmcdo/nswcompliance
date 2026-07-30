import { NextRequest, NextResponse } from 'next/server';
import { promises as dns } from 'dns';
import { z } from 'zod';
import { createClient as createServiceClient } from '@supabase/supabase-js';
import { Resend } from 'resend';
import { checkRateLimit, createRateLimitHeaders, getClientIdentifier } from '@/lib/rate-limit';
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const resend = new Resend(process.env.RESEND_API_KEY);

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
// INPUT SCHEMA
// ============================================================================

const INTEREST_TYPES = ['granny-flat', 'flood', 'flood-truth', 'solar-yield', 'solar', 'shadow', 'threat-radar', 'conveyancing', 'pre-da-history', 'dual-occ-referral', 'lga-request', 'intelligence-brief'] as const;

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
    const firstError = parsed.error.errors[0]?.message ?? 'Invalid input';
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

  // --- 6. Store lead ---
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
      eligible: eligible ?? null,
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

  // --- 7. Send confirmation email ---
  const addressLabel = cleanAddress ?? 'your property';
  const { subject, body: emailBody } = buildEmailContent(interest_type ?? 'granny-flat', addressLabel);
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
    await resend.emails.send({
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
// and gets interpolated into an HTML email body — escape it before use in any
// NEW case here. The 7 pre-existing cases below share this same unescaped
// interpolation; that's a pre-existing pattern, not introduced by this PR, and
// out of scope for a lead-capture-400 bugfix — flagged for a follow-up, not
// silently left or silently expanded into here.
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function buildEmailContent(product: string, address: string): { subject: string; body: string } {
  // address is user-submitted (Zod bounds length only, not character set) and
  // gets interpolated into an HTML email body across every case below —
  // escape once here rather than per-case. Subjects use the raw `address`
  // (plain text, never HTML-rendered; escaping there would show literal
  // "&amp;" etc. for a genuine address containing "&").
  const safeAddress = escapeHtml(address);
  switch (product) {
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
            <a href="https://plotdetect.com.au/tools/upzoning-check" style="color: #0d9488;">plotdetect.com.au/tools/upzoning-check</a>.
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
