/**
 * Route Obfuscation for Anti-Copycat Security
 *
 * Maps obfuscated route hashes to actual API endpoints.
 * CRITICAL: These hashes are set via environment variables and should NEVER be committed.
 *
 * Usage:
 *   import { SECURE_ROUTES } from '@/lib/security/route-obfuscation';
 *   fetch(SECURE_ROUTES.AI_CHAT, { method: 'POST', ... });
 */

const HASH_1 = process.env.NEXT_PUBLIC_ROUTE_HASH_1 || 'dev-fallback-1';
const HASH_2 = process.env.NEXT_PUBLIC_ROUTE_HASH_2 || 'dev-fallback-2';
const HASH_3 = process.env.NEXT_PUBLIC_ROUTE_HASH_3 || 'dev-fallback-3';

/**
 * Obfuscated route mappings
 * Production uses random hashes from env vars
 * Development uses fallback hashes for easier debugging
 */
export const SECURE_ROUTES = {
  // Main AI chat endpoint (previously /api/ai/chat)
  AI_CHAT: `/api/q/${HASH_1}`,

  // Contextual guidance endpoint
  GUIDANCE: `/api/r/${HASH_2}`,

  // Cross-reference endpoint
  CROSS_REF: `/api/x/${HASH_3}`,
} as const;

/**
 * Verify that a request path matches an expected secure route
 */
export function verifySecureRoute(pathname: string, expectedRoute: keyof typeof SECURE_ROUTES): boolean {
  return pathname === SECURE_ROUTES[expectedRoute];
}

/**
 * Check if route hashes are properly configured
 * Warns in development if using fallback hashes
 */
export function validateRouteConfig(): { valid: boolean; warnings: string[] } {
  const warnings: string[] = [];

  if (!process.env.NEXT_PUBLIC_ROUTE_HASH_1) {
    warnings.push('NEXT_PUBLIC_ROUTE_HASH_1 not set - using development fallback');
  }

  if (!process.env.NEXT_PUBLIC_ROUTE_HASH_2) {
    warnings.push('NEXT_PUBLIC_ROUTE_HASH_2 not set - using development fallback');
  }

  if (!process.env.NEXT_PUBLIC_ROUTE_HASH_3) {
    warnings.push('NEXT_PUBLIC_ROUTE_HASH_3 not set - using development fallback');
  }

  // In production, missing hashes is a critical error
  if (process.env.NODE_ENV === 'production' && warnings.length > 0) {
    return { valid: false, warnings };
  }

  return { valid: true, warnings };
}
