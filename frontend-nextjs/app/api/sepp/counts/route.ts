import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

export async function GET(req: NextRequest) {
  const pool = getPool();

  try {
    // Get all SEPP documents
    const { rows: seppDocs } = await pool.query(`
      SELECT
        document_id,
        COUNT(*) as total_provisions,
        COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable,
        COUNT(*) FILTER (WHERE v2_is_actionable = false) as non_actionable,
        COUNT(DISTINCT v2_topic) as unique_topics,
        COUNT(DISTINCT v2_part) as unique_parts
      FROM regulatory_provisions
      WHERE document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental_Planning_Policy%'
      GROUP BY document_id
      ORDER BY total_provisions DESC
    `);

    // Get breakdown by topic for Exempt & Complying
    const { rows: exemptTopics } = await pool.query(`
      SELECT
        v2_topic,
        v2_part,
        COUNT(*) as count,
        COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable
      FROM regulatory_provisions
      WHERE document_id = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation'
        AND v2_topic IS NOT NULL
      GROUP BY v2_topic, v2_part
      ORDER BY v2_part, count DESC
    `);

    // Get total counts
    const { rows: totals } = await pool.query(`
      SELECT
        COUNT(*) as total_sepp,
        COUNT(DISTINCT document_id) as total_sepp_docs
      FROM regulatory_provisions
      WHERE document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental_Planning_Policy%'
    `);

    return NextResponse.json({
      documents: seppDocs,
      exemptComplying: exemptTopics,
      totals: totals[0]
    });
  } catch (error) {
    console.error('[SEPP Counts API]', error);
    return NextResponse.json({ error: 'Failed to fetch SEPP counts' }, { status: 500 });
  }
}
