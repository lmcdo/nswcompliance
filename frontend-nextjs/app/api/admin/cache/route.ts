import { NextRequest, NextResponse } from 'next/server';
import { clearAllCaches, getAllCacheStats, cleanupAllCaches } from '@/lib/cache';

/**
 * Admin Cache Management Endpoint
 *
 * GET  /api/admin/cache - Get cache statistics
 * POST /api/admin/cache?action=clear - Clear all caches
 * POST /api/admin/cache?action=cleanup - Remove expired entries only
 */

export async function GET() {
  const stats = getAllCacheStats();

  return NextResponse.json({
    success: true,
    data: stats,
    timestamp: new Date().toISOString()
  });
}

export async function POST(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const action = searchParams.get('action');

  if (action === 'clear') {
    clearAllCaches();
    return NextResponse.json({
      success: true,
      message: 'All caches cleared',
      timestamp: new Date().toISOString()
    });
  }

  if (action === 'cleanup') {
    const removed = cleanupAllCaches();
    return NextResponse.json({
      success: true,
      message: 'Expired entries removed',
      removed,
      timestamp: new Date().toISOString()
    });
  }

  return NextResponse.json({
    success: false,
    error: 'Invalid action. Use ?action=clear or ?action=cleanup'
  }, { status: 400 });
}
