import { NextRequest, NextResponse } from 'next/server';
import { clearAllCaches, getAllCacheStats, cleanupAllCaches } from '@/lib/cache';

/**
 * Admin Cache Management Endpoint
 *
 * GET  /api/admin/cache - Get cache statistics
 * POST /api/admin/cache?action=clear - Clear all caches
 * POST /api/admin/cache?action=cleanup - Remove expired entries only
 *
 * Requires X-Admin-Key header matching ADMIN_API_KEY environment variable
 */

function checkAdminAuth(request: NextRequest): boolean {
  const adminKey = process.env.ADMIN_API_KEY;
  const providedKey = request.headers.get('x-admin-key');

  // If no admin key is configured, deny access (fail secure)
  if (!adminKey) {
    console.warn('[Admin Auth] ADMIN_API_KEY not configured - denying access');
    return false;
  }

  return providedKey === adminKey;
}

export async function GET(request: NextRequest) {
  if (!checkAdminAuth(request)) {
    return NextResponse.json(
      {
        success: false,
        error: 'Forbidden - Admin authentication required'
      },
      { status: 403 }
    );
  }
  const stats = getAllCacheStats();

  return NextResponse.json({
    success: true,
    data: stats,
    timestamp: new Date().toISOString()
  });
}

export async function POST(request: NextRequest) {
  if (!checkAdminAuth(request)) {
    return NextResponse.json(
      {
        success: false,
        error: 'Forbidden - Admin authentication required'
      },
      { status: 403 }
    );
  }

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
