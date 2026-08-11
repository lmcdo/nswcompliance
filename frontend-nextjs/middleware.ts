import { NextResponse } from 'next/server';
import type { NextFetchEvent, NextRequest } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import {
  globalRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';
import { identifyAiCrawler } from '@/lib/ai-crawlers';

/**
 * API Authentication, Rate Limiting & CORS Middleware
 *
 * Phase 1 Security Enhancements:
 * - Redis-based rate limiting (persistent across serverless restarts)
 * - Hardened CORS (strict origin checking in production)
 * - Enhanced security headers (CSP, Referrer-Policy, HSTS)
 *
 * Authentication:
 * - If API_KEY env var is set, requires x-api-key header on /api/* routes
 * - If API_KEY is not set, all requests are allowed (dev mode)
 *
 * CORS:
 * - Production: Only allows whitelisted domains
 * - Development: Allows localhost/127.0.0.1
 *
 * Public routes (no auth required):
 * - /api/health/*
 * - /api/public/*
 */

const PUBLIC_ROUTES = [
  '/api/health',
  '/api/public',
  '/api/property',     // used internally by satellite routes (no auth header on server-side fetches)
  '/api/canibuildit',  // consumer-facing tool — no API key required from browsers
];

// ============================================================================
// CORS CONFIGURATION - Phase 1 Security
// ============================================================================

/**
 * Production origins - only these domains can call your API
 * Add your actual production domains here
 */
const PRODUCTION_ORIGINS = [
  'https://plotdetect.com',
  'https://www.plotdetect.com',
  'https://plotdetect.vercel.app',
  'https://plotdetect.com.au',
  'https://www.plotdetect.com.au',
  'https://canibuildit.com.au',
  'https://www.canibuildit.com.au',
  'https://whatcanibuildhere.com.au',
];

/**
 * Development origins - localhost allowed in dev mode only
 */
const DEVELOPMENT_ORIGINS = [
  'http://localhost:3000',
  'http://localhost:3001',
  'http://localhost:3003',
  'http://127.0.0.1:3000',
  'http://127.0.0.1:3001',
  'http://127.0.0.1:3003',
];

/**
 * Checks if an origin is allowed to access the API
 * Production: Strict whitelist only
 * Development: Allows localhost
 */
function isOriginAllowed(origin: string | null): boolean {
  if (!origin) return false;

  if (process.env.NODE_ENV === 'production') {
    // Production: Only allow whitelisted domains
    const envOrigins = process.env.CORS_ALLOWED_ORIGINS?.split(',').map(o => o.trim()) || [];
    const allowedOrigins = [...PRODUCTION_ORIGINS, ...envOrigins];
    return allowedOrigins.includes(origin);
  }

  // Development: Allow localhost/127.0.0.1
  return DEVELOPMENT_ORIGINS.some(allowed =>
    origin.startsWith(allowed) || origin === allowed
  );
}

export async function middleware(request: NextRequest, event: NextFetchEvent) {
  const { pathname } = request.nextUrl;

  // ============================================================================
  // AI CRAWLER TRACKING — server-side, because AI crawlers never execute the
  // PostHog browser SDK. Fire-and-forget via waitUntil; never blocks the
  // response and failures are swallowed.
  // ============================================================================
  if (request.method === 'GET' && !pathname.startsWith('/api')) {
    const crawler = identifyAiCrawler(request.headers.get('user-agent'));
    const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (crawler && posthogKey) {
      event.waitUntil(
        fetch('https://us.i.posthog.com/capture/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            api_key: posthogKey,
            event: 'ai_crawler_hit',
            distinct_id: `crawler:${crawler}`,
            properties: {
              bot: crawler,
              path: pathname,
              host: request.headers.get('x-forwarded-host') ?? request.headers.get('host'),
            },
          }),
        }).catch(() => {}),
      );
    }
  }

  // ============================================================================
  // SUPABASE SESSION REFRESH — /reports/* and /auth/*
  // ============================================================================
  if (pathname.startsWith('/reports') || pathname.startsWith('/auth') || pathname === '/login') {
    let response = NextResponse.next({ request });

    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return request.cookies.getAll();
          },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value }) =>
              request.cookies.set(name, value),
            );
            response = NextResponse.next({ request });
            cookiesToSet.forEach(({ name, value, options }) =>
              response.cookies.set(name, value, options),
            );
          },
        },
      },
    );

    // Refresh session — must call getUser() not getSession() to avoid stale JWTs
    await supabase.auth.getUser();

    return response;
  }

  // ============================================================================
  // HOSTNAME ROUTING — serve correct app per domain
  // Both plotdetect.com.au and verify.plotdetect.com.au point to the same
  // Next.js build. Rewrite root requests to the right section.
  // ============================================================================
  // x-forwarded-host is more reliable than host when behind Cloudflare + Vercel
  const hostname =
    request.headers.get('x-forwarded-host') ??
    request.headers.get('host') ??
    request.nextUrl.hostname;
  // Option B domain map (see memory: domain-architecture):
  //   verify / brief / conveyance = the three pro products as plotdetect subdomains;
  //   canibuildit = the consumer satellite tools; plotdetect.com.au = info site (other project).
  const isVerifyDomain = hostname === 'verify.plotdetect.com.au';
  const isBriefDomain = hostname === 'brief.plotdetect.com.au';
  const isConveyanceDomain = hostname === 'conveyance.plotdetect.com.au';
  const isCanibuilditDomain =
    hostname === 'canibuildit.com.au' || hostname === 'www.canibuildit.com.au';

  if (isVerifyDomain && pathname === '/') {
    return NextResponse.rewrite(new URL('/assessment', request.url));
  }
  if (isBriefDomain && pathname === '/') {
    return NextResponse.rewrite(new URL('/reports/intelligence-brief', request.url));
  }
  if (isConveyanceDomain && pathname === '/') {
    return NextResponse.rewrite(new URL('/reports/conveyancing', request.url));
  }
  if (isCanibuilditDomain && pathname === '/') {
    return NextResponse.rewrite(new URL('/reports', request.url));
  }
  // Option B: canibuildit is consumer instant-checks ONLY. The two pro report
  // pages exist in this build (all domains share it), so send them to their
  // own subdomains instead of serving them under the consumer brand.
  // 307 (temporary) on purpose — cached 308s made an earlier domain move
  // painful to undo (see memory: domain-architecture).
  if (isCanibuilditDomain && pathname === '/reports/intelligence-brief') {
    return NextResponse.redirect(
      new URL(request.nextUrl.search, 'https://brief.plotdetect.com.au'), 307,
    );
  }
  if (isCanibuilditDomain && pathname === '/reports/conveyancing') {
    return NextResponse.redirect(
      new URL(request.nextUrl.search, 'https://conveyance.plotdetect.com.au'), 307,
    );
  }

  // Only apply rate limiting / auth to API routes
  if (!pathname.startsWith('/api')) {
    return NextResponse.next();
  }

  const origin = request.headers.get('origin');

  // ============================================================================
  // CORS PREFLIGHT REQUESTS
  // ============================================================================
  if (request.method === 'OPTIONS') {
    // Check if origin is allowed
    if (origin && isOriginAllowed(origin)) {
      return new NextResponse(null, {
        status: 200,
        headers: {
          'Access-Control-Allow-Origin': origin,
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, x-api-key, x-admin-key, Authorization',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // Origin not allowed - block CORS preflight
    return new NextResponse(null, { status: 403 });
  }

  // ============================================================================
  // PUBLIC ROUTES (skip auth/rate limiting)
  // ============================================================================
  const isPublicRoute = PUBLIC_ROUTES.some(route => pathname.startsWith(route));
  if (isPublicRoute) {
    const response = NextResponse.next();

    // Add CORS headers only for allowed origins
    if (origin && isOriginAllowed(origin)) {
      response.headers.set('Access-Control-Allow-Origin', origin);
      response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
      response.headers.set('Access-Control-Allow-Headers', 'Content-Type, x-api-key, Authorization');
    }

    return response;
  }

  // ============================================================================
  // RATE LIMITING - Phase 1 Redis-based
  // ============================================================================
  const clientIP = getClientIdentifier(request);
  const rateLimitResult = await checkRateLimit(clientIP, globalRateLimiter, 100, 60000);

  if (!rateLimitResult.success) {
    const headers = createRateLimitHeaders(rateLimitResult);

    return NextResponse.json(
      {
        success: false,
        error: 'Rate limit exceeded. Please try again later.',
        code: 'RATE_LIMIT_EXCEEDED',
      },
      {
        status: 429,
        headers,
      }
    );
  }

  // ============================================================================
  // AUTHENTICATION (only if API_KEY is configured)
  // ============================================================================
  const apiKey = process.env.API_KEY;
  if (apiKey) {
    const providedKey = request.headers.get('x-api-key');
    if (!providedKey || providedKey !== apiKey) {
      return NextResponse.json(
        {
          success: false,
          error: 'Unauthorized. Provide valid x-api-key header.',
          code: 'UNAUTHORIZED',
        },
        { status: 401 }
      );
    }
  }

  // ============================================================================
  // SECURITY & CORS HEADERS - Phase 1 Enhanced
  // ============================================================================
  const response = NextResponse.next();

  // Security headers
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');

  // Content Security Policy (CSP)
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-eval' 'unsafe-inline'", // Next.js requires unsafe-eval
    "style-src 'self' 'unsafe-inline'", // Tailwind requires unsafe-inline
    "img-src 'self' data: https:",
    "connect-src 'self' https://*.supabase.co https://*.upstash.io",
    "font-src 'self' data:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join('; ');
  response.headers.set('Content-Security-Policy', csp);

  // HSTS (HTTP Strict Transport Security) - production only
  if (process.env.NODE_ENV === 'production') {
    response.headers.set(
      'Strict-Transport-Security',
      'max-age=31536000; includeSubDomains; preload'
    );
  }

  // CORS headers - only for allowed origins
  if (origin && isOriginAllowed(origin)) {
    response.headers.set('Access-Control-Allow-Origin', origin);
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    response.headers.set('Access-Control-Allow-Headers', 'Content-Type, x-api-key, x-admin-key, Authorization');
  } else if (origin) {
    // Log blocked origin for monitoring
    console.warn(`[CORS] Blocked request from unauthorized origin: ${origin}`);
  }

  // Rate limit headers (for monitoring)
  const rateLimitHeaders = createRateLimitHeaders(rateLimitResult);
  Object.entries(rateLimitHeaders).forEach(([key, value]) => {
    response.headers.set(key, value);
  });

  return response;
}

export const config = {
  // Match everything except Next.js internals and static files.
  // Required for hostname-based routing to fire on the root path.
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};
