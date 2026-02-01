/**
 * Enhanced Rate Limiting with Bot Detection
 *
 * Stricter limits for suspected bots and fingerprint-less requests
 */

import { NextRequest } from 'next/server';

/**
 * Detect if User-Agent looks like a bot/scraper
 */
export function isBotUserAgent(userAgent: string | null): boolean {
  if (!userAgent) return true; // No UA = suspicious

  const botPatterns = [
    /bot/i,
    /crawl/i,
    /spider/i,
    /scrape/i,
    /curl/i,
    /wget/i,
    /python/i,
    /http/i,
    /postman/i,
    /insomnia/i,
  ];

  return botPatterns.some(pattern => pattern.test(userAgent));
}

/**
 * Check if request has browser fingerprint headers
 * Real browsers send these; simple scrapers don't
 */
export function hasFingerprint(request: NextRequest): boolean {
  const headers = request.headers;

  // Check for typical browser headers
  const hasAcceptLanguage = headers.has('accept-language');
  const hasAcceptEncoding = headers.has('accept-encoding');
  const hasReferer = headers.has('referer') || headers.has('sec-fetch-site');

  return hasAcceptLanguage && hasAcceptEncoding && hasReferer;
}

/**
 * Determine rate limit based on request characteristics
 *
 * @returns {limit, window} - requests per window (ms)
 */
export function getRateLimit(request: NextRequest): { limit: number; window: number } {
  const userAgent = request.headers.get('user-agent');
  const fingerprint = hasFingerprint(request);
  const isBot = isBotUserAgent(userAgent);

  // Strictest limit: Bot without fingerprint
  if (isBot && !fingerprint) {
    return { limit: 5, window: 3600000 }; // 5 per hour
  }

  // Medium: Bot with fingerprint (might be legitimate headless browser)
  if (isBot) {
    return { limit: 10, window: 3600000 }; // 10 per hour
  }

  // Stricter: No fingerprint (suspicious)
  if (!fingerprint) {
    return { limit: 20, window: 3600000 }; // 20 per hour
  }

  // Normal: Real browser
  return { limit: 60, window: 3600000 }; // 60 per hour (1 per minute)
}

/**
 * In-memory violation tracker
 * In production, use Redis or database
 */
const violations = new Map<string, number>();

/**
 * Track rate limit violations
 */
export function recordViolation(identifier: string): number {
  const current = violations.get(identifier) || 0;
  const updated = current + 1;
  violations.set(identifier, updated);

  // Auto-clear after 24 hours
  setTimeout(() => {
    const count = violations.get(identifier);
    if (count && count <= updated) {
      violations.delete(identifier);
    }
  }, 86400000); // 24 hours

  return updated;
}

/**
 * Check if identifier is blocked due to violations
 */
export function isBlocked(identifier: string): boolean {
  const count = violations.get(identifier) || 0;
  return count >= 3; // Block after 3 violations
}

/**
 * Clear violations (admin function)
 */
export function clearViolations(identifier: string): void {
  violations.delete(identifier);
}
