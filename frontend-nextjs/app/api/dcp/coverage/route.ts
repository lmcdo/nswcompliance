/**
 * GET /api/dcp/coverage
 *
 * Returns the list of councils with structured DCP controls,
 * queried from dcp_setback_controls. Single source of truth —
 * no hardcoded council lists needed in UI components.
 *
 * Response: { councils: string[] }
 *   e.g. ["Bayside", "Blacktown", ..., "Woollahra"]
 */

import { NextResponse } from 'next/server';
import { getPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

// LGA slugs that aren't individual councils and should be excluded from the display list.
// Inner West sub-councils (ashfield, leichhardt, marrickville) are shown as "Inner West".
const EXCLUDED_SLUGS = new Set([
  'nsw_statewide',  // SEPP Codes CDC standards, not a council DCP
  'ashfield',       // shown under Inner West
  'leichhardt',     // shown under Inner West
  'marrickville',   // shown under Inner West
]);

// Slug → display name. Only needed when the display name can't be derived from the slug.
const DISPLAY_NAMES: Record<string, string> = {
  inner_west: 'Inner West',
  city_of_sydney: 'City of Sydney',
  ku_ring_gai: 'Ku-ring-gai',
  canada_bay: 'Canada Bay',
  canterbury_bankstown: 'Canterbury-Bankstown',
  georges_river: 'Georges River',
  northern_beaches: 'Northern Beaches',
  sutherland_shire: 'Sutherland Shire',
  the_hills: 'The Hills Shire',
};

function slugToDisplayName(slug: string): string {
  if (DISPLAY_NAMES[slug]) return DISPLAY_NAMES[slug];
  // Default: title-case each word
  return slug.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

export async function GET() {
  try {
    const pool = getPool();
    const result = await pool.query(
      `SELECT DISTINCT lga FROM dcp_setback_controls
       WHERE is_current = true OR is_current IS NULL
       ORDER BY lga`,
    );

    const councils = result.rows
      .map(r => r.lga as string)
      .filter(slug => !EXCLUDED_SLUGS.has(slug))
      .map(slugToDisplayName)
      .sort();

    return NextResponse.json({ councils });
  } catch (err) {
    console.error('[dcp/coverage] DB error:', err);
    return NextResponse.json({ councils: [] }, { status: 500 });
  }
}
