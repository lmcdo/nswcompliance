import { NextResponse } from 'next/server';
import { getAllCacheStats, cleanupAllCaches } from '@/lib/cache';

/**
 * GET /api/health/cache
 *
 * Returns cache statistics and health information
 * Useful for monitoring cache performance and hit rates
 */
export async function GET() {
  const stats = getAllCacheStats();

  // Calculate overall cache effectiveness
  const totalSize = stats.sepp.size + stats.lep.size + stats.dcp.size + stats.heritage.size;
  const totalValid = stats.sepp.validEntries + stats.lep.validEntries + stats.dcp.validEntries + stats.heritage.validEntries;
  const totalHits = stats.sepp.totalHits + stats.lep.totalHits + stats.dcp.totalHits + stats.heritage.totalHits;

  return NextResponse.json({
    success: true,
    data: {
      stats,
      summary: {
        totalCachedEntries: totalSize,
        validEntries: totalValid,
        expiredEntries: totalSize - totalValid,
        totalCacheHits: totalHits,
        cacheEffectiveness: totalSize > 0 ? ((totalHits / totalSize) * 100).toFixed(2) + '%' : 'N/A'
      },
      timestamp: new Date().toISOString()
    }
  });
}

/**
 * DELETE /api/health/cache
 *
 * Cleans up expired entries from all caches
 * Returns number of entries removed
 */
export async function DELETE() {
  const removed = cleanupAllCaches();

  const totalRemoved = removed.sepp + removed.lep + removed.dcp + removed.heritage;

  return NextResponse.json({
    success: true,
    data: {
      removed,
      totalRemoved,
      message: `Cleaned up ${totalRemoved} expired cache entries`
    }
  });
}
