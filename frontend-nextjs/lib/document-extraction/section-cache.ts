/**
 * Section Cache
 *
 * In-memory cache for extracted sections
 * Reduces repeated document parsing for same sections
 */

import type { CachedSection, ExtractedSection } from '../lga-configs/types';

// In-memory cache
const sectionCache = new Map<string, CachedSection>();

// Cache TTL: 24 hours
const CACHE_TTL = 24 * 60 * 60 * 1000;

/**
 * Generate cache key
 */
function getCacheKey(documentId: string, sectionRef: string): string {
  return `${documentId}::${sectionRef}`;
}

/**
 * Get cached section if available and not expired
 */
export function getCachedSection(
  documentId: string,
  sectionRef: string
): ExtractedSection | null {
  const key = getCacheKey(documentId, sectionRef);
  const cached = sectionCache.get(key);

  if (!cached) {
    return null;
  }

  // Check if expired
  if (Date.now() > cached.expiresAt) {
    sectionCache.delete(key);
    return null;
  }

  // Return without cache metadata
  const { documentId: _, extractedAt: __, expiresAt: ___, ...section } = cached;
  return section;
}

/**
 * Cache an extracted section
 */
export function cacheSection(
  documentId: string,
  section: ExtractedSection
): void {
  const key = getCacheKey(documentId, section.sectionRef);
  const now = Date.now();

  const cached: CachedSection = {
    ...section,
    documentId,
    extractedAt: now,
    expiresAt: now + CACHE_TTL,
  };

  sectionCache.set(key, cached);
}

/**
 * Clear cache for a specific document
 */
export function clearDocumentCache(documentId: string): void {
  const keysToDelete: string[] = [];

  for (const key of sectionCache.keys()) {
    if (key.startsWith(`${documentId}::`)) {
      keysToDelete.push(key);
    }
  }

  for (const key of keysToDelete) {
    sectionCache.delete(key);
  }
}

/**
 * Clear entire cache
 */
export function clearAllCache(): void {
  sectionCache.clear();
}

/**
 * Get cache statistics
 */
export function getCacheStats() {
  let totalEntries = 0;
  let expiredEntries = 0;
  const now = Date.now();

  for (const cached of sectionCache.values()) {
    totalEntries++;
    if (now > cached.expiresAt) {
      expiredEntries++;
    }
  }

  return {
    totalEntries,
    expiredEntries,
    activeEntries: totalEntries - expiredEntries,
    memoryEstimate: `~${Math.round((totalEntries * 2) / 1024)}KB`, // Rough estimate
  };
}

/**
 * Cleanup expired entries (run periodically)
 */
export function cleanupExpired(): number {
  const now = Date.now();
  const keysToDelete: string[] = [];

  for (const [key, cached] of sectionCache.entries()) {
    if (now > cached.expiresAt) {
      keysToDelete.push(key);
    }
  }

  for (const key of keysToDelete) {
    sectionCache.delete(key);
  }

  return keysToDelete.length;
}

// Auto-cleanup every hour
if (typeof setInterval !== 'undefined') {
  setInterval(() => {
    const cleaned = cleanupExpired();
    if (cleaned > 0) {
      console.log(`[SectionCache] Cleaned ${cleaned} expired entries`);
    }
  }, 60 * 60 * 1000);
}
