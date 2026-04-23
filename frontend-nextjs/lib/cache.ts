/**
 * In-Memory Cache Utility for Next.js API Routes
 * Implements LRU cache with TTL for high-performance request caching
 *
 * Use Cases:
 * - Static SEPP/LEP provisions (rarely change)
 * - Heritage conservation areas (rarely change)
 * - DCP provisions by zone/devtype (rarely change)
 *
 * NOT for:
 * - Property lookups (varies per request)
 * - User-specific data
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  hits: number;
}

class LRUCache<T> {
  private cache: Map<string, CacheEntry<T>>;
  private maxSize: number;
  private ttl: number; // Time to live in milliseconds

  constructor(maxSize: number = 100, ttlSeconds: number = 3600) {
    this.cache = new Map();
    this.maxSize = maxSize;
    this.ttl = ttlSeconds * 1000;
  }

  /**
   * Get value from cache
   * Returns null if not found or expired
   */
  get(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    // Check if expired
    const now = Date.now();
    if (now - entry.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    // Update access (for LRU)
    entry.hits++;
    this.cache.delete(key);
    this.cache.set(key, entry);

    return entry.data;
  }

  /**
   * Set value in cache
   * Implements LRU eviction when full
   */
  set(key: string, data: T): void {
    // If cache is full, remove oldest (first) entry
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const firstKey = this.cache.keys().next().value as string;
      this.cache.delete(firstKey);
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      hits: 0
    });
  }

  /**
   * Clear entire cache
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Get cache statistics
   */
  getStats() {
    const entries = Array.from(this.cache.entries());
    const now = Date.now();
    const valid = entries.filter(([_, entry]) => now - entry.timestamp <= this.ttl);

    return {
      size: this.cache.size,
      validEntries: valid.length,
      expiredEntries: this.cache.size - valid.length,
      totalHits: entries.reduce((sum, [_, entry]) => sum + entry.hits, 0),
      maxSize: this.maxSize,
      ttlSeconds: this.ttl / 1000
    };
  }

  /**
   * Remove expired entries
   */
  cleanup(): number {
    const now = Date.now();
    let removed = 0;

    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > this.ttl) {
        this.cache.delete(key);
        removed++;
      }
    }

    return removed;
  }
}

// Global cache instances (singleton pattern for Next.js)
const globalForCache = globalThis as unknown as {
  seppCache?: LRUCache<any>;
  lepCache?: LRUCache<any>;
  dcpCache?: LRUCache<any>;
  heritageCache?: LRUCache<any>;
};

/**
 * Cache for SEPP provisions (rarely change)
 * TTL: 1 hour, Max: 100 entries
 */
export function getSEPPCache() {
  if (!globalForCache.seppCache) {
    globalForCache.seppCache = new LRUCache(100, 3600);
  }
  return globalForCache.seppCache;
}

/**
 * Cache for LEP provisions (rarely change)
 * TTL: 1 hour, Max: 100 entries
 */
export function getLEPCache() {
  if (!globalForCache.lepCache) {
    globalForCache.lepCache = new LRUCache(100, 3600);
  }
  return globalForCache.lepCache;
}

/**
 * Cache for DCP provisions (rarely change)
 * TTL: 30 minutes, Max: 200 entries (more varied by zone/devtype)
 */
export function getDCPCache() {
  if (!globalForCache.dcpCache) {
    globalForCache.dcpCache = new LRUCache(200, 1800);
  }
  return globalForCache.dcpCache;
}

/**
 * Cache for Heritage Conservation Areas (rarely change)
 * TTL: 2 hours, Max: 50 entries
 */
export function getHeritageCache() {
  if (!globalForCache.heritageCache) {
    globalForCache.heritageCache = new LRUCache(50, 7200);
  }
  return globalForCache.heritageCache;
}

/**
 * Get all cache statistics
 */
export function getAllCacheStats() {
  return {
    sepp: getSEPPCache().getStats(),
    lep: getLEPCache().getStats(),
    dcp: getDCPCache().getStats(),
    heritage: getHeritageCache().getStats()
  };
}

/**
 * Clear all caches (useful for testing or admin operations)
 */
export function clearAllCaches() {
  getSEPPCache().clear();
  getLEPCache().clear();
  getDCPCache().clear();
  getHeritageCache().clear();
}

/**
 * Run cleanup on all caches (remove expired entries)
 */
export function cleanupAllCaches() {
  return {
    sepp: getSEPPCache().cleanup(),
    lep: getLEPCache().cleanup(),
    dcp: getDCPCache().cleanup(),
    heritage: getHeritageCache().cleanup()
  };
}

/**
 * Helper function to create cache key from object
 */
export function createCacheKey(prefix: string, params: Record<string, any>): string {
  const sortedParams = Object.keys(params)
    .sort()
    .map(key => `${key}=${params[key]}`)
    .join('&');
  return `${prefix}:${sortedParams}`;
}

// ============================================================================
// REDIS ADDRESS CHECK CACHE
// Persistent 24-hour cache for /api/canibuildit/check results.
// Prevents the same address from re-hitting the NSW Planning Portal API,
// protects against scraping, and reduces Railway + Planning Portal costs.
// Falls back to no-op if UPSTASH_REDIS_REST_URL/TOKEN are not set.
// ============================================================================

import { Redis } from '@upstash/redis';

function createAddressRedisClient(): Redis | null {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return null;
  return new Redis({ url, token });
}

const addressRedis = createAddressRedisClient();
const ADDRESS_CACHE_TTL = 86400; // 24 hours in seconds

function normaliseAddressKey(address: string): string {
  return `cache:canibuildit:check:${address.trim().toLowerCase().replace(/\s+/g, ' ')}`;
}

/**
 * Retrieve a cached canibuildit check result.
 * Returns null on miss, Redis error, or if Redis is not configured.
 */
export async function getCachedAddressCheck(address: string): Promise<Record<string, unknown> | null> {
  if (!addressRedis) return null;
  try {
    const raw = await addressRedis.get<unknown>(normaliseAddressKey(address));
    if (!raw) return null;
    if (typeof raw === 'object') return raw as Record<string, unknown>;
    return JSON.parse(raw as string) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * Store a canibuildit check result in Redis with a 24-hour TTL.
 * Silent no-op on error — cache failure must never break the response.
 */
export async function setCachedAddressCheck(address: string, result: Record<string, unknown>): Promise<void> {
  if (!addressRedis) return;
  try {
    await addressRedis.set(normaliseAddressKey(address), JSON.stringify(result), { ex: ADDRESS_CACHE_TTL });
  } catch {
    // Non-fatal
  }
}
