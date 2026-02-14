import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

const DOC_ID = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation';

// Zone → applicable housing code Part
// Part 3  = Housing Code           (R1, R2, R3, R4, RU5 — standard Sydney metro)
// Part 3A = Rural Housing Code     (R5, RU1, RU2, RU3, RU4, RU6)
// Parts 3B/3C/3D are geographic (Low Rise Diversity, Greenfield, Inland) — handled separately
function zoneToPartMap(zoneCode: string): string {
  const ruralZones = ['R5', 'RU1', 'RU2', 'RU3', 'RU4', 'RU6'];
  if (ruralZones.includes(zoneCode)) return '3A';
  return '3'; // default: Housing Code covers R1-R4, RU5
}

const VALID_WORK_TYPES = ['Deck', 'Fence', 'Carport', 'Pool'];

/**
 * GET /api/sepp/exempt-complying?zone=R2&workType=Deck
 *
 * Returns actionable provisions for a given zone + work type.
 * Filters by: document, v2_part (from zone), v2_topic (work type), v2_is_actionable=true
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const zone = searchParams.get('zone')?.toUpperCase() || '';
  const workType = searchParams.get('workType') || '';

  // Validate workType
  if (workType && !VALID_WORK_TYPES.includes(workType)) {
    return NextResponse.json({ error: 'Invalid workType' }, { status: 400 });
  }

  const part = zoneToPartMap(zone);

  try {
    let query: string;
    let params: any[];

    if (workType) {
      // Filtered: specific work type
      query = `
        SELECT id, pdf_page, pdf_printed_page, provision_text, v2_part, v2_topic
        FROM regulatory_provisions
        WHERE document_id = $1
          AND v2_part = $2
          AND v2_topic = $3
          AND v2_is_actionable = true
        ORDER BY id
      `;
      params = [DOC_ID, part, workType];
    } else {
      // All work types for this zone — return counts per type
      query = `
        SELECT v2_topic, COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id = $1
          AND v2_part = $2
          AND v2_topic IN ('Deck', 'Fence', 'Carport', 'Pool')
          AND v2_is_actionable = true
        GROUP BY v2_topic
        ORDER BY v2_topic
      `;
      params = [DOC_ID, part];
    }

    const { rows } = await getPool().query(query, params);

    return NextResponse.json({
      part,
      zone,
      workType: workType || null,
      provisions: workType ? rows : [],
      counts: workType ? null : Object.fromEntries(rows.map((r: any) => [r.v2_topic, parseInt(r.count)])),
    });
  } catch (error) {
    console.error('[exempt-complying API]', error);
    return NextResponse.json({ error: 'Database error' }, { status: 500 });
  }
}
