/**
 * Provisions Changes API
 *
 * Returns what changed in provisions since a specific date or amendment.
 *
 * Query Parameters:
 * - document_id: Document identifier (e.g., "Marrickville_DCP_2011__Part_2")
 * - since: ISO date string (e.g., "2024-01-01") - show changes since this date
 * - provision_id: Optional provision ID - show changes for specific provision
 * - change_type: Optional filter (e.g., "modified", "created", "deleted")
 * - limit: Maximum number of changes to return (default: 100)
 *
 * Response includes:
 * - summary: Count of changes by type
 * - changes: Array of change records with before/after text
 * - metadata: Query parameters and timing information
 */

import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';


export const dynamic = 'force-dynamic';
interface ChangesFilters {
  document_id?: string;
  since?: string;
  provision_id?: number;
  change_type?: string;
  limit: number;
}

interface ChangeRecord {
  id: number;
  provision_id: number;
  ref_number: string;
  v2_topic: string;
  change_type: string;
  changed_at: string;
  amendment_reference: string | null;
  text_before: string | null;
  text_after: string;
  version_from: number | null;
  version_to: number;
  fields_changed: string[];
}

interface ChangeSummary {
  modified: number;
  created: number;
  deleted: number;
  total: number;
}

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    const searchParams = request.nextUrl.searchParams;

    // Parse filters
    const filters: ChangesFilters = {
      document_id: searchParams.get('document_id') || undefined,
      since: searchParams.get('since') || undefined,
      provision_id: searchParams.get('provision_id')
        ? parseInt(searchParams.get('provision_id')!, 10)
        : undefined,
      change_type: searchParams.get('change_type') || undefined,
      limit: parseInt(searchParams.get('limit') || '100', 10),
    };

    // Validate required parameters
    if (!filters.document_id && !filters.provision_id) {
      return NextResponse.json(
        {
          success: false,
          error: 'Either document_id or provision_id is required',
        },
        { status: 400 }
      );
    }

    if (filters.since) {
      // Validate date format
      const datePattern = /^\d{4}-\d{2}-\d{2}$/;
      if (!datePattern.test(filters.since)) {
        return NextResponse.json(
          {
            success: false,
            error: 'Invalid date format. Use YYYY-MM-DD (e.g., "2024-01-01")',
          },
          { status: 400 }
        );
      }
    }

    console.log(`[Changes API] Filters: ${JSON.stringify(filters)}`);

    const pool = getPool();
    const client = await pool.connect();

    try {
      // Build query
      const params: any[] = [];
      let paramIndex = 1;

      let sql = `
        SELECT
          pcl.id,
          pcl.provision_id,
          rp.ref_number,
          rp.v2_topic,
          pcl.change_type,
          pcl.changed_at,
          pcl.amendment_reference,
          pv_from.provision_text as text_before,
          pv_to.provision_text as text_after,
          pv_from.version_number as version_from,
          pv_to.version_number as version_to,
          pcl.fields_changed
        FROM provision_change_log pcl
        INNER JOIN regulatory_provisions rp ON pcl.provision_id = rp.id
        LEFT JOIN provision_versions pv_from ON pcl.version_from = pv_from.id
        INNER JOIN provision_versions pv_to ON pcl.version_to = pv_to.id
        WHERE 1=1
      `;

      // Filter by document_id
      if (filters.document_id) {
        sql += ` AND pcl.triggered_by_document = $${paramIndex++}`;
        params.push(filters.document_id);
      }

      // Filter by provision_id
      if (filters.provision_id) {
        sql += ` AND pcl.provision_id = $${paramIndex++}`;
        params.push(filters.provision_id);
      }

      // Filter by date
      if (filters.since) {
        sql += ` AND pcl.changed_at >= $${paramIndex++}::timestamp`;
        params.push(filters.since);
      }

      // Filter by change type
      if (filters.change_type) {
        sql += ` AND pcl.change_type = $${paramIndex++}`;
        params.push(filters.change_type);
      }

      // Order and limit
      sql += `
        ORDER BY pcl.changed_at DESC
        LIMIT $${paramIndex++}
      `;
      params.push(filters.limit);

      console.log(`[Changes API] Executing query with ${params.length} parameters`);

      const result = await client.query(sql, params);
      const changes: ChangeRecord[] = result.rows.map((row) => ({
        id: row.id,
        provision_id: row.provision_id,
        ref_number: row.ref_number,
        v2_topic: row.v2_topic,
        change_type: row.change_type,
        changed_at: row.changed_at,
        amendment_reference: row.amendment_reference,
        text_before: row.text_before,
        text_after: row.text_after,
        version_from: row.version_from,
        version_to: row.version_to,
        fields_changed: row.fields_changed || [],
      }));

      // Calculate summary
      const summary: ChangeSummary = {
        modified: changes.filter((c) => c.change_type.includes('modified')).length,
        created: changes.filter((c) => c.change_type === 'created').length,
        deleted: changes.filter((c) => c.change_type === 'deleted').length,
        total: changes.length,
      };

      // Categorize changes
      const categorized = {
        modified: changes.filter((c) => c.change_type.includes('modified')),
        created: changes.filter((c) => c.change_type === 'created'),
        deleted: changes.filter((c) => c.change_type === 'deleted'),
        other: changes.filter(
          (c) => !c.change_type.includes('modified') && c.change_type !== 'created' && c.change_type !== 'deleted'
        ),
      };

      const duration = Date.now() - startTime;

      console.log(`[Changes API] Found ${changes.length} changes in ${duration}ms`);

      return NextResponse.json(
        {
          success: true,
          data: {
            document_id: filters.document_id,
            provision_id: filters.provision_id,
            since_date: filters.since,
            summary,
            changes: categorized,
            all_changes: changes, // Include flat list for convenience
          },
          metadata: {
            query_time_ms: duration,
            filters,
            result_count: changes.length,
          },
        },
        {
          status: 200,
          headers: {
            'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=7200',
          },
        }
      );
    } finally {
      client.release();
    }
  } catch (error: any) {
    console.error('[Changes API] Error:', error);

    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to fetch provision changes',
      },
      { status: 500 }
    );
  }
}
