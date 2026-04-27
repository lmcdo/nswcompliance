import { NextRequest, NextResponse } from 'next/server';
import { promises as dns } from 'dns';
import { z } from 'zod';
import { createClient } from '@/lib/supabase/server';
import { Resend } from 'resend';
import { checkRateLimit, createRateLimitHeaders, getClientIdentifier } from '@/lib/rate-limit';
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const resend = new Resend(process.env.RESEND_API_KEY);

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

const INTEREST_TYPES = ['granny-flat', 'flood', 'flood-truth', 'solar-yield', 'solar', 'shadow', 'threat-radar'] as const;

const LeadSchema = z.object({
  email: z.string().email('Invalid email address').max(254, 'Email too long'),
  address: z.string().min(5, 'Address too short').max(200, 'Address too long').optional().nullable(),
  eligible: z.boolean().optional().nullable(),
  lga_name: z.string().max(100, 'LGA name too long').optional().nullable(),
  interest_type: z.enum(INTEREST_TYPES).optional().nullable(),
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

  const { email, address, eligible, lga_name, interest_type, website } = parsed.data;

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
    const supabase = await createClient();
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
    const supabase = await createClient();
    await supabase.from('canibuildit_leads').insert({
      email: cleanEmail,
      address: cleanAddress,
      eligible: eligible ?? null,
      ...(lga_name ? { lga_name: lga_name.trim() } : {}),
      ...(interest_type ? { interest_type: interest_type.trim() } : {}),
    });
  } catch {
    // Non-blocking — don't error the user if DB insert fails
  }

  // --- 7. Send confirmation email ---
  const addressLabel = cleanAddress ?? 'your property';
  const { subject, body: emailBody } = buildEmailContent(interest_type ?? 'granny-flat', addressLabel);
  try {
    await resend.emails.send({
      from: 'Can I Build It <info@plotdetect.com.au>',
      replyTo: 'hello@canibuildit.com.au',
      to: [cleanEmail],
      subject,
      html: `
        <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
          ${emailBody}
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
          <p style="color: #999; font-size: 12px;">
            Can I Build It? &middot; <a href="https://canibuildit.com.au" style="color: #0d9488;">canibuildit.com.au</a>
          </p>
        </div>
      `,
    });
  } catch (emailErr) {
    console.error('[canibuildit/lead] Resend error:', emailErr);
  }

  return NextResponse.json({ ok: true });
}

export function buildEmailContent(product: string, address: string): { subject: string; body: string } {
  switch (product) {
    case 'flood':
    case 'flood-truth':
      return {
        subject: `Your flood risk result — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your flood risk result is ready.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your flood risk check for <strong>${address}</strong> is complete.
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
            Your solar yield check for <strong>${address}</strong> is complete.
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
            Your shadow analysis for <strong>${address}</strong> is complete.
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
            Your DA activity check for <strong>${address}</strong> is complete.
            Visit <a href="https://canibuildit.com.au/reports/threat-radar" style="color: #0d9488;">canibuildit.com.au/reports/threat-radar</a>
            to monitor this address or check another.
          </p>`,
      };
    case 'granny-flat':
    default:
      return {
        subject: `Your granny flat check is running — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">We're on it.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your granny flat check for <strong>${address}</strong> is running.
            We're pulling live aerial imagery, running satellite structure detection,
            and cross-referencing NSW Planning Portal rules — this takes 1–3 minutes.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            You can close the tab. We'll send your result here as soon as it's ready.
          </p>`,
      };
  }
}
