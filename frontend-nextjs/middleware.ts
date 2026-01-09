import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * API Authentication, Rate Limiting & CORS Middleware
 *
 * Authentication:
 * - If API_KEY env var is set, requires x-api-key header on /api/* routes
 * - If API_KEY is not set, all requests are allowed (dev mode)
 *
 * CORS:
 * - Configurable allowed origins via CORS_ALLOWED_ORIGINS env var
 * - Defaults to localhost in development
 *
 * Public routes (no auth required):
 * - /api/health/*
 * - /api/public/*
 */

const PUBLIC_ROUTES = [
  '/api/health',
  '/api/public',
];

// CORS configuration
const DEFAULT_ALLOWED_ORIGINS = [
  'http://localhost:3000',
  'http://localhost:3001',
  'http://127.0.0.1:3000',
];

function getAllowedOrigins(): string[] {
  const envOrigins = process.env.CORS_ALLOWED_ORIGINS;
  if (envOrigins) {
    return envOrigins.split(',').map(o => o.trim());
  }
  return DEFAULT_ALLOWED_ORIGINS;
}

function isOriginAllowed(origin: string | null): boolean {
  if (!origin) return false;
  const allowed = getAllowedOrigins();
  // Allow all in development
  if (process.env.NODE_ENV === 'development') return true;
  return allowed.includes(origin);
}

// Simple in-memory rate limiting (per IP, resets on server restart)
// For production, use Redis-based solution like @upstash/ratelimit
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute
const RATE_LIMIT_MAX_REQUESTS = 100; // 100 requests per minute

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const record = rateLimitMap.get(ip);

  if (!record || now > record.resetTime) {
    rateLimitMap.set(ip, { count: 1, resetTime: now + RATE_LIMIT_WINDOW_MS });
    return false;
  }

  record.count++;
  if (record.count > RATE_LIMIT_MAX_REQUESTS) {
    return true;
  }

  return false;
}

function getClientIP(request: NextRequest): string {
  const forwarded = request.headers.get('x-forwarded-for');
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  return request.headers.get('x-real-ip') || 'unknown';
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Only apply to API routes
  if (!pathname.startsWith('/api')) {
    return NextResponse.next();
  }

  const origin = request.headers.get('origin');

  // Handle CORS preflight requests
  if (request.method === 'OPTIONS') {
    return new NextResponse(null, {
      status: 200,
      headers: {
        'Access-Control-Allow-Origin': origin || '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, x-api-key, Authorization',
        'Access-Control-Max-Age': '86400',
      },
    });
  }

  // Skip auth for public routes
  const isPublicRoute = PUBLIC_ROUTES.some(route => pathname.startsWith(route));
  if (isPublicRoute) {
    const response = NextResponse.next();
    // Add CORS headers for public routes
    if (origin) {
      response.headers.set('Access-Control-Allow-Origin', origin);
      response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
      response.headers.set('Access-Control-Allow-Headers', 'Content-Type, x-api-key, Authorization');
    }
    return response;
  }

  // Rate limiting
  const clientIP = getClientIP(request);
  if (isRateLimited(clientIP)) {
    return NextResponse.json(
      {
        success: false,
        error: 'Rate limit exceeded. Try again later.',
        code: 'RATE_LIMIT_EXCEEDED'
      },
      { status: 429 }
    );
  }

  // Authentication (only if API_KEY is configured)
  const apiKey = process.env.API_KEY;
  if (apiKey) {
    const providedKey = request.headers.get('x-api-key');
    if (!providedKey || providedKey !== apiKey) {
      return NextResponse.json(
        {
          success: false,
          error: 'Unauthorized. Provide valid x-api-key header.',
          code: 'UNAUTHORIZED'
        },
        { status: 401 }
      );
    }
  }

  // Add security and CORS headers
  const response = NextResponse.next();
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');

  // Add CORS headers
  if (origin) {
    response.headers.set('Access-Control-Allow-Origin', origin);
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    response.headers.set('Access-Control-Allow-Headers', 'Content-Type, x-api-key, Authorization');
  }

  return response;
}

export const config = {
  matcher: '/api/:path*',
};
