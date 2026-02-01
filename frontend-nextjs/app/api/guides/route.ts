/**
 * Getting Started Guides API
 *
 * Query step-by-step guides for common development scenarios.
 * Supports:
 * - List all published guides
 * - Get guide by slug
 * - Get guide by ID
 * - Search guides by keyword
 *
 * GET /api/guides - List all guides
 * GET /api/guides?slug=build-granny-flat - Get specific guide
 * GET /api/guides?id=G1 - Get guide by ID
 * GET /api/guides?search=duplex - Search guides
 */

import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/database/pool-manager';


export const dynamic = 'force-dynamic';
interface GuideStep {
  step_number: number;
  title: string;
  description: string;
  duration: string;
  tasks: string[];
  tips: string[];
}

interface GuideResult {
  id: number;
  guide_id: string;
  title: string;
  slug: string;
  target_user: string;
  typical_timeline: string | null;
  typical_cost_range: string | null;
  eligibility: Record<string, string> | null;
  steps: GuideStep[];
  common_pitfalls: string[] | null;
  related_qa_ids: string[] | null;
  related_checklist_ids: string[] | null;
  source_document: string | null;
  source_url: string | null;
  last_verified: string | null;
  display_order: number;
}

interface GuidesResponse {
  success: boolean;
  count: number;
  guides: GuideResult[];
  meta: {
    filters_applied: Record<string, string>;
    response_time_ms: number;
  };
}

export async function GET(request: NextRequest): Promise<NextResponse<GuidesResponse | { error: string; details?: string }>> {
  const startTime = Date.now();

  try {
    const searchParams = request.nextUrl.searchParams;

    // Parse query parameters
    const slug = searchParams.get('slug');
    const guideId = searchParams.get('id');
    const searchTerm = searchParams.get('search');
    const limit = Math.min(parseInt(searchParams.get('limit') || '20'), 100);

    const filtersApplied: Record<string, string> = {};
    if (slug) filtersApplied.slug = slug;
    if (guideId) filtersApplied.id = guideId;
    if (searchTerm) filtersApplied.search = searchTerm;

    // Build query
    const conditions: string[] = ['is_published = true'];
    const params: (string | number)[] = [];
    let paramIndex = 1;

    // Filter by slug
    if (slug) {
      conditions.push(`slug = $${paramIndex++}`);
      params.push(slug);
    }

    // Filter by guide_id
    if (guideId) {
      conditions.push(`guide_id = $${paramIndex++}`);
      params.push(guideId.toUpperCase());
    }

    // Full-text search
    if (searchTerm) {
      conditions.push(`(
        title ILIKE $${paramIndex++}
        OR target_user ILIKE $${paramIndex++}
        OR to_tsvector('english', title || ' ' || target_user) @@ plainto_tsquery('english', $${paramIndex++})
      )`);
      params.push(`%${searchTerm}%`);
      params.push(`%${searchTerm}%`);
      params.push(searchTerm);
    }

    const whereClause = conditions.length > 0
      ? `WHERE ${conditions.join(' AND ')}`
      : '';

    const sql = `
      SELECT
        id,
        guide_id,
        title,
        slug,
        target_user,
        typical_timeline,
        typical_cost_range,
        eligibility,
        steps,
        common_pitfalls,
        related_qa_ids,
        related_checklist_ids,
        source_document,
        source_url,
        last_verified::text,
        display_order
      FROM getting_started_guides
      ${whereClause}
      ORDER BY display_order, guide_id
      LIMIT $${paramIndex}
    `;

    params.push(limit);

    const result = await query(sql, params);
    const guides = result.rows as GuideResult[];

    const responseTime = Date.now() - startTime;

    console.log(`[Guides API] Found ${guides.length} guides in ${responseTime}ms`);

    return NextResponse.json({
      success: true,
      count: guides.length,
      guides,
      meta: {
        filters_applied: filtersApplied,
        response_time_ms: responseTime
      }
    });

  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.error('[Guides API] Error:', error);

    return NextResponse.json(
      {
        error: 'Failed to query guides',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
