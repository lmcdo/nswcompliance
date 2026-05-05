/**
 * Production-Grade Rate Limiting with Redis
 *
 * Phase 1 Security: Persistent rate limiting that survives serverless restarts
 *
 * Uses Upstash Redis for:
 * - Persistent storage across all Vercel serverless functions
 * - Sub-20ms response times (edge network)
 * - Built-in analytics dashboard
 * - Free tier: 10,000 requests/day
 *
 * Setup:
 * 1. Create free account at https://upstash.com
 * 2. Create Redis database
 * 3. Add to Vercel env vars:
 *    - UPSTASH_REDIS_REST_URL
 *    - UPSTASH_REDIS_REST_TOKEN
 */

import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

// ============================================================================
// REDIS CLIENT
// ============================================================================

/**
 * Creates Redis client if credentials are available
 * Falls back to null if env vars not configured (development mode)
 */
function createRedisClient(): Redis | null {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;

  if (!url || !token) {
    console.warn('[Rate Limit] Redis not configured - using in-memory fallback');
    return null;
  }

  return new Redis({
    url,
    token,
  });
}

const redis = createRedisClient();

// ============================================================================
// IN-MEMORY FALLBACK (for development without Redis)
// ============================================================================

interface RateLimitRecord {
  count: number;
  resetTime: number;
}

const inMemoryStore = new Map<string, RateLimitRecord>();

/**
 * Simple in-memory rate limiter for development
 * NOTE: Resets on serverless function restart (not production-grade)
 */
function checkInMemoryRateLimit(
  identifier: string,
  maxRequests: number,
  windowMs: number
): { success: boolean; limit: number; remaining: number; reset: number } {
  const now = Date.now();
  const record = inMemoryStore.get(identifier);

  if (!record || now > record.resetTime) {
    // Create new window
    inMemoryStore.set(identifier, {
      count: 1,
      resetTime: now + windowMs,
    });

    return {
      success: true,
      limit: maxRequests,
      remaining: maxRequests - 1,
      reset: now + windowMs,
    };
  }

  // Increment counter
  record.count++;

  const remaining = Math.max(0, maxRequests - record.count);
  const success = record.count <= maxRequests;

  return {
    success,
    limit: maxRequests,
    remaining,
    reset: record.resetTime,
  };
}

// ============================================================================
// RATE LIMITERS
// ============================================================================

/**
 * Global rate limiter: 100 requests per minute per IP
 * Applied to all API routes via middleware
 */
export const globalRateLimiter = redis
  ? new Ratelimit({
      redis,
      limiter: Ratelimit.slidingWindow(100, '1 m'),
      analytics: true,
      prefix: 'rl:global',
    })
  : null;

/**
 * AI endpoint rate limiter: 5 requests per minute per IP
 * Applied to /api/ai/chat and other LLM endpoints
 * Prevents cost blowout from API abuse
 */
export const aiRateLimiter = redis
  ? new Ratelimit({
      redis,
      limiter: Ratelimit.slidingWindow(5, '1 m'),
      analytics: true,
      prefix: 'rl:ai',
    })
  : null;

/**
 * Admin endpoint rate limiter: 10 requests per minute per IP
 * Applied to /api/admin/* endpoints
 * Protects sensitive operations
 */
export const adminRateLimiter = redis
  ? new Ratelimit({
      redis,
      limiter: Ratelimit.slidingWindow(10, '1 m'),
      analytics: true,
      prefix: 'rl:admin',
    })
  : null;

/**
 * Search endpoint rate limiter: 20 requests per minute per IP
 * Applied to search-heavy endpoints
 */
export const searchRateLimiter = redis
  ? new Ratelimit({
      redis,
      limiter: Ratelimit.slidingWindow(20, '1 m'),
      analytics: true,
      prefix: 'rl:search',
    })
  : null;

/**
 * Data endpoint rate limiter: 30 requests per minute per IP
 * Applied to provision/browse/assessment read endpoints
 */
export const dataRateLimiter = redis
  ? new Ratelimit({
      redis,
      limiter: Ratelimit.slidingWindow(30, '1 m'),
      analytics: true,
      prefix: 'rl:data',
    })
  : null;

/**
 * canibuildit check rate limiter: 20 requests per minute per IP
 * Applied to /api/canibuildit/check — hits NSW Planning Portal on every call.
 * 20/min is generous for real users (checking multiple addresses) but stops scrapers.
 */
export const canibuilditCheckLimiter = redis
  ? new Ratelimit({
      redis,
      limiter: Ratelimit.slidingWindow(20, '1 m'),
      analytics: true,
      prefix: 'rl:canibuildit',
    })
  : null;

/**
 * Satellite pipeline rate limiter: 10 requests per minute per IP
 * Applied to expensive endpoints that call Railway/Google Solar/paid APIs.
 * Tighter than the global 100/min to limit per-user cost exposure.
 */
export const satelliteRateLimiter = redis
  ? new Ratelimit({
      redis,
      limiter: Ratelimit.slidingWindow(10, '1 m'),
      analytics: true,
      prefix: 'rl:satellite',
    })
  : null;

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Extracts client identifier (IP address) from request
 * Handles various proxy headers (Vercel, Cloudflare, etc.)
 */
export function getClientIdentifier(request: Request | { headers: Headers }): string {
  const headers = request.headers;

  // Try various headers in order of reliability
  const forwardedFor = headers.get('x-forwarded-for');
  if (forwardedFor) {
    // X-Forwarded-For can be comma-separated list, take first IP
    return forwardedFor.split(',')[0].trim();
  }

  const realIp = headers.get('x-real-ip');
  if (realIp) {
    return realIp;
  }

  const cfConnectingIp = headers.get('cf-connecting-ip'); // Cloudflare
  if (cfConnectingIp) {
    return cfConnectingIp;
  }

  // Fallback for development or when headers missing
  return 'unknown';
}

/**
 * Checks rate limit using Redis or in-memory fallback
 * Returns standardized response with limit headers
 */
export async function checkRateLimit(
  identifier: string,
  limiter: Ratelimit | null,
  fallbackMax: number = 100,
  fallbackWindowMs: number = 60000
): Promise<{
  success: boolean;
  limit: number;
  remaining: number;
  reset: number;
}> {
  // Use Redis if available
  if (limiter) {
    try {
      const result = await limiter.limit(identifier);
      return {
        success: result.success,
        limit: result.limit,
        remaining: result.remaining,
        reset: result.reset,
      };
    } catch (error) {
      console.error('[Rate Limit] Redis error, falling back to in-memory:', error);
      // Fall through to in-memory on Redis errors
    }
  }

  // Fallback to in-memory
  return checkInMemoryRateLimit(identifier, fallbackMax, fallbackWindowMs);
}

/**
 * Creates rate limit headers for HTTP responses
 * Follows standard RateLimit header spec
 */
export function createRateLimitHeaders(result: {
  limit: number;
  remaining: number;
  reset: number;
}): Record<string, string> {
  return {
    'X-RateLimit-Limit': result.limit.toString(),
    'X-RateLimit-Remaining': result.remaining.toString(),
    'X-RateLimit-Reset': result.reset.toString(),
    'Retry-After': result.reset ? Math.ceil((result.reset - Date.now()) / 1000).toString() : '60',
  };
}

// ============================================================================
// CONFIGURATION STATUS
// ============================================================================

/**
 * Returns current rate limiting configuration status
 * Useful for debugging and monitoring
 */
export function getRateLimitStatus() {
  return {
    redisConfigured: redis !== null,
    mode: redis ? 'redis' : 'in-memory',
    limiters: {
      global: globalRateLimiter !== null,
      ai: aiRateLimiter !== null,
      admin: adminRateLimiter !== null,
      search: searchRateLimiter !== null,
    },
    warning:
      redis === null
        ? 'Redis not configured - using in-memory fallback (resets on restart)'
        : null,
  };
}
