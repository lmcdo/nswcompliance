/**
 * HONEYPOT - Fake AI Chat Endpoint
 *
 * This is NOT the real AI chat endpoint. The real endpoint is obfuscated.
 * This honeypot logs anyone trying to access the "obvious" route.
 *
 * Purpose: Detect reverse-engineering attempts and competitor scraping
 */

import { NextRequest, NextResponse } from 'next/server';
import { getClientIdentifier } from '@/lib/rate-limit';

interface HoneypotLog {
  timestamp: string;
  ip: string;
  userAgent: string | null;
  method: string;
  headers: Record<string, string>;
  body?: any;
}

/**
 * Log honeypot access attempt
 */
function logHoneypotAccess(request: NextRequest, body?: any): void {
  const log: HoneypotLog = {
    timestamp: new Date().toISOString(),
    ip: getClientIdentifier(request),
    userAgent: request.headers.get('user-agent'),
    method: request.method,
    headers: {
      referer: request.headers.get('referer') || 'none',
      origin: request.headers.get('origin') || 'none',
      'sec-fetch-site': request.headers.get('sec-fetch-site') || 'none',
    },
    body,
  };

  // Log to console (in production, send to monitoring)
  console.warn('🍯 [HONEYPOT] Unauthorized API access attempt:', log);

  // In production, alert via monitoring service
  // if (process.env.NODE_ENV === 'production') {
  //   // Sentry.captureMessage('Honeypot triggered', { level: 'warning', extra: log });
  //   // Or send to Slack/email alert
  // }
}

/**
 * POST handler - Most likely scraping attempt
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    logHoneypotAccess(request, body);
  } catch (error) {
    logHoneypotAccess(request);
  }

  // Return plausible error (not 404, which reveals it's a honeypot)
  return NextResponse.json(
    {
      success: false,
      error: 'Service temporarily unavailable. Please try again later.',
    },
    { status: 503 }
  );
}

/**
 * GET handler - Probably just exploration
 */
export async function GET(request: NextRequest) {
  logHoneypotAccess(request);

  return NextResponse.json(
    {
      service: 'AI Assistant',
      status: 'unavailable',
      message: 'This service is currently under maintenance.',
    },
    { status: 503 }
  );
}
