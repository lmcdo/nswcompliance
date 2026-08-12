/**
 * POST /api/lot-search
 * POST /api/lot-search?summary=true
 *
 * Bulk property search against the pre-computed lot_search_index.
 * Direct DB query via lib/db.ts pool — no Python/Railway proxy.
 */

import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

import { query } from '@/lib/db';
import {
  searchRateLimiter,
  checkRateLimit,
  getClientIdentifier,
  createRateLimitHeaders,
} from '@/lib/rate-limit';
import { formatValidationErrors } from '@/lib/schemas';

export const dynamic = 'force-dynamic';
export const maxDuration = 15;

// ---------------------------------------------------------------------------
// Input validation
// ---------------------------------------------------------------------------

const LotSearchSchema = z.object({
  lga_name: z.string().optional(),
  zone_codes: z.array(z.string()).optional(),
  dev_types: z.array(z.string()).optional(),
  min_area_m2: z.number().positive().optional(),
  max_area_m2: z.number().positive().optional(),
  min_gfa_m2: z.number().positive().optional(),
  max_gfa_m2: z.number().positive().optional(),
  min_dwellings: z.number().int().min(1).optional(),
  heritage: z.boolean().optional(),
  flood_prone: z.boolean().optional(),
  bushfire_prone: z.boolean().optional(),
  min_confidence: z.enum(['low', 'medium', 'high']).optional(),
  binding_constraint: z.array(z.string()).optional(),
  bbox: z.array(z.number()).length(4).optional(),
  limit: z.number().int().min(1).max(500).default(50),
  offset: z.number().int().min(0).default(0),
  order_by: z.string().default('ca_realistic_gfa_m2'),
  order_dir: z.enum(['asc', 'desc']).default('desc'),
});

type LotSearchInput = z.infer<typeof LotSearchSchema>;

// Whitelist of columns allowed for ORDER BY — prevents SQL injection
const ALLOWED_ORDER_COLS = new Set([
  'ca_realistic_gfa_m2',
  'ca_realistic_dwellings',
  'lot_area_m2',
  'lep_height_m',
  'lep_fsr',
  'ca_buildable_footprint_m2',
  'ca_lep_envelope_gfa_m2',
  'zone_code',
  'lga_name',
  'ca_dev_type',
]);

// Confidence level ordering for >= filter
const CONFIDENCE_LEVELS: Record<string, number> = { low: 0, medium: 1, high: 2 };

// ---------------------------------------------------------------------------
// WHERE clause builder
// ---------------------------------------------------------------------------

function buildWhere(req: LotSearchInput): { where: string; params: any[] } {
  const conditions: string[] = [];
  const params: any[] = [];
  let paramIdx = 1;

  if (req.lga_name) {
    conditions.push(`lga_name = $${paramIdx++}`);
    params.push(req.lga_name.toUpperCase());
  }
  if (req.zone_codes?.length) {
    conditions.push(`zone_code = ANY($${paramIdx++})`);
    params.push(req.zone_codes);
  }
  if (req.dev_types?.length) {
    conditions.push(`ca_dev_type = ANY($${paramIdx++})`);
    params.push(req.dev_types);
  }
  if (req.min_area_m2 != null) {
    conditions.push(`lot_area_m2 >= $${paramIdx++}`);
    params.push(req.min_area_m2);
  }
  if (req.max_area_m2 != null) {
    conditions.push(`lot_area_m2 <= $${paramIdx++}`);
    params.push(req.max_area_m2);
  }
  if (req.min_gfa_m2 != null) {
    conditions.push(`ca_realistic_gfa_m2 >= $${paramIdx++}`);
    params.push(req.min_gfa_m2);
  }
  if (req.max_gfa_m2 != null) {
    conditions.push(`ca_realistic_gfa_m2 <= $${paramIdx++}`);
    params.push(req.max_gfa_m2);
  }
  if (req.min_dwellings != null) {
    conditions.push(`ca_realistic_dwellings >= $${paramIdx++}`);
    params.push(req.min_dwellings);
  }
  if (req.heritage != null) {
    conditions.push(`heritage = $${paramIdx++}`);
    params.push(req.heritage);
  }
  if (req.flood_prone != null) {
    conditions.push(`flood_prone = $${paramIdx++}`);
    params.push(req.flood_prone);
  }
  if (req.bushfire_prone != null) {
    conditions.push(`bushfire_prone = $${paramIdx++}`);
    params.push(req.bushfire_prone);
  }
  if (req.min_confidence) {
    const minLevel = CONFIDENCE_LEVELS[req.min_confidence] ?? 0;
    const valid = Object.entries(CONFIDENCE_LEVELS)
      .filter(([, v]) => v >= minLevel)
      .map(([k]) => k);
    conditions.push(`ca_confidence = ANY($${paramIdx++})`);
    params.push(valid);
  }
  if (req.binding_constraint?.length) {
    conditions.push(`ca_binding_constraint = ANY($${paramIdx++})`);
    params.push(req.binding_constraint);
  }
  if (req.bbox?.length === 4) {
    const [minLng, minLat, maxLng, maxLat] = req.bbox;
    conditions.push(
      `EXISTS (SELECT 1 FROM nsw_cadastre_lots ncl WHERE ncl.lotidstring = lot_search_index.lotidstring AND ST_Intersects(ncl.geom, ST_MakeEnvelope($${paramIdx++}, $${paramIdx++}, $${paramIdx++}, $${paramIdx++}, 4326)))`
    );
    params.push(minLng, minLat, maxLng, maxLat);
  }

  const where = conditions.length > 0 ? conditions.join(' AND ') : 'TRUE';
  return { where, params };
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

async function handleSearch(req: LotSearchInput) {
  const orderCol = ALLOWED_ORDER_COLS.has(req.order_by) ? req.order_by : 'ca_realistic_gfa_m2';
  const orderDir = req.order_dir === 'asc' ? 'ASC' : 'DESC';
  const { where, params } = buildWhere(req);

  const start = Date.now();

  // Set statement timeout for this query
  await query('SET LOCAL statement_timeout = 10000');

  // Count total matching rows
  const countResult = await query(
    `SELECT COUNT(*) FROM lot_search_index WHERE ${where}`,
    params,
  );
  const totalCount = parseInt(countResult.rows[0].count, 10);

  // Fetch page
  const limitIdx = params.length + 1;
  const offsetIdx = params.length + 2;
  const dataResult = await query(
    `SELECT lotidstring, lga_name, zone_code, lot_area_m2,
            lep_height_m, lep_fsr, heritage, flood_prone,
            bushfire_prone, bushfire_category, ca_dev_type,
            ca_realistic_gfa_m2, ca_realistic_dwellings,
            ca_binding_constraint, ca_confidence,
            ca_effective_height_m, ca_effective_fsr,
            ca_buildable_footprint_m2,
            ca_setback_front_m, ca_setback_rear_m, ca_setback_side_m,
            ca_gaps
     FROM lot_search_index
     WHERE ${where}
     ORDER BY ${orderCol} ${orderDir} NULLS LAST
     LIMIT $${limitIdx} OFFSET $${offsetIdx}`,
    [...params, req.limit, req.offset],
  );

  const queryMs = Date.now() - start;

  return {
    lots: dataResult.rows.map((r: any) => ({
      lotidstring: r.lotidstring,
      lga_name: r.lga_name,
      zone_code: r.zone_code,
      lot_area_m2: r.lot_area_m2,
      lep_height_m: r.lep_height_m,
      lep_fsr: r.lep_fsr,
      // NULL means the overlay was never resolved for this lot. It is not
      // "no heritage / not flood prone / not bushfire prone". Coercing it with
      // `?? false` served three clean hazard flags off a lookup that never
      // happened — the same defect as the flood verdict (#892), on three
      // fields at once. Null passes through; the caller decides how to render
      // an unresolved overlay, and must not render it as a clearance.
      heritage: r.heritage ?? null,
      flood_prone: r.flood_prone ?? null,
      bushfire_prone: r.bushfire_prone ?? null,
      bushfire_category: r.bushfire_category,
      ca_dev_type: r.ca_dev_type,
      ca_realistic_gfa_m2: r.ca_realistic_gfa_m2,
      ca_realistic_dwellings: r.ca_realistic_dwellings,
      ca_binding_constraint: r.ca_binding_constraint,
      ca_confidence: r.ca_confidence,
      ca_effective_height_m: r.ca_effective_height_m,
      ca_effective_fsr: r.ca_effective_fsr,
      ca_buildable_footprint_m2: r.ca_buildable_footprint_m2,
      ca_setback_front_m: r.ca_setback_front_m,
      ca_setback_rear_m: r.ca_setback_rear_m,
      ca_setback_side_m: r.ca_setback_side_m,
      ca_gaps: r.ca_gaps,
    })),
    total_count: totalCount,
    query_ms: queryMs,
  };
}

async function handleSummary(req: LotSearchInput) {
  const { where, params } = buildWhere(req);
  const start = Date.now();

  await query('SET LOCAL statement_timeout = 10000');

  // Scalar aggregates
  const aggResult = await query(
    `SELECT
       COUNT(*) AS total_lots,
       COUNT(ca_realistic_gfa_m2) AS lots_with_ca,
       AVG(lot_area_m2)::double precision AS avg_area_m2,
       AVG(ca_realistic_gfa_m2)::double precision AS avg_gfa_m2,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ca_realistic_gfa_m2) AS median_gfa_m2,
       PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY ca_realistic_gfa_m2) AS p25_gfa_m2,
       PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY ca_realistic_gfa_m2) AS p75_gfa_m2,
       AVG(ca_realistic_dwellings)::double precision AS avg_dwellings,
       COUNT(*) FILTER (WHERE heritage = TRUE) AS heritage_count,
       COUNT(*) FILTER (WHERE flood_prone = TRUE) AS flood_count,
       COUNT(*) FILTER (WHERE bushfire_prone = TRUE) AS bushfire_count,
       COUNT(*) FILTER (WHERE ca_confidence = 'high') AS confidence_high,
       COUNT(*) FILTER (WHERE ca_confidence = 'medium') AS confidence_medium,
       COUNT(*) FILTER (WHERE ca_confidence = 'low') AS confidence_low
     FROM lot_search_index
     WHERE ${where}`,
    params,
  );
  const agg = aggResult.rows[0];

  // Zone distribution
  const zoneResult = await query(
    `SELECT zone_code, COUNT(*)::int AS count
     FROM lot_search_index
     WHERE ${where} AND zone_code IS NOT NULL
     GROUP BY zone_code
     ORDER BY count DESC
     LIMIT 20`,
    params,
  );

  // Binding constraint distribution
  const bindingResult = await query(
    `SELECT ca_binding_constraint, COUNT(*)::int AS count
     FROM lot_search_index
     WHERE ${where} AND ca_binding_constraint IS NOT NULL
     GROUP BY ca_binding_constraint
     ORDER BY count DESC`,
    params,
  );

  // Dev type distribution
  const devTypeResult = await query(
    `SELECT ca_dev_type, COUNT(*)::int AS count
     FROM lot_search_index
     WHERE ${where} AND ca_dev_type IS NOT NULL
     GROUP BY ca_dev_type
     ORDER BY count DESC`,
    params,
  );

  // Data currency: latest successful refresh for the queried LGA (factual "data as of").
  // Best-effort — never let the provenance lookup break the summary response.
  let indexRefreshedAt: string | null = null;
  if (req.lga_name) {
    try {
      const refreshRes = await query(
        `SELECT MAX(finished_at) AS at FROM lot_index_refresh_log
         WHERE lga_name = $1 AND status = 'ok'`,
        [req.lga_name.toUpperCase()],
      );
      indexRefreshedAt = refreshRes?.rows?.[0]?.at ?? null;
    } catch {
      indexRefreshedAt = null;
    }
  }

  const queryMs = Date.now() - start;

  return {
    index_refreshed_at: indexRefreshedAt,
    total_lots: parseInt(agg.total_lots, 10),
    lots_with_ca: parseInt(agg.lots_with_ca, 10),
    avg_area_m2: agg.avg_area_m2 ? Math.round(agg.avg_area_m2 * 10) / 10 : null,
    avg_gfa_m2: agg.avg_gfa_m2 ? Math.round(agg.avg_gfa_m2 * 10) / 10 : null,
    median_gfa_m2: agg.median_gfa_m2 ? Math.round(agg.median_gfa_m2 * 10) / 10 : null,
    p25_gfa_m2: agg.p25_gfa_m2 ? Math.round(agg.p25_gfa_m2 * 10) / 10 : null,
    p75_gfa_m2: agg.p75_gfa_m2 ? Math.round(agg.p75_gfa_m2 * 10) / 10 : null,
    avg_dwellings: agg.avg_dwellings ? Math.round(agg.avg_dwellings * 10) / 10 : null,
    heritage_count: parseInt(agg.heritage_count, 10),
    flood_count: parseInt(agg.flood_count, 10),
    bushfire_count: parseInt(agg.bushfire_count, 10),
    confidence_high: parseInt(agg.confidence_high, 10),
    confidence_medium: parseInt(agg.confidence_medium, 10),
    confidence_low: parseInt(agg.confidence_low, 10),
    zone_distribution: zoneResult.rows,
    binding_distribution: bindingResult.rows,
    dev_type_distribution: devTypeResult.rows,
    query_ms: queryMs,
  };
}

// ---------------------------------------------------------------------------
// Route handler
// ---------------------------------------------------------------------------

export async function POST(request: NextRequest) {
  // Rate limiting
  const identifier = getClientIdentifier(request);
  const rateResult = await checkRateLimit(identifier, searchRateLimiter, 20, 60000);
  if (!rateResult.success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded' },
      { status: 429, headers: createRateLimitHeaders(rateResult) },
    );
  }

  // Parse and validate body
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const parsed = LotSearchSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: 'Validation failed', details: formatValidationErrors(parsed.error) },
      { status: 400 },
    );
  }

  const isSummary = request.nextUrl.searchParams.get('summary') === 'true';

  try {
    const data = isSummary
      ? await handleSummary(parsed.data)
      : await handleSearch(parsed.data);

    return NextResponse.json(data, {
      headers: createRateLimitHeaders(rateResult),
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error('[lot-search] Query error:', message);

    if (message.includes('statement timeout')) {
      return NextResponse.json(
        { error: 'Query timed out — try narrowing your filters' },
        { status: 504 },
      );
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 },
    );
  }
}
