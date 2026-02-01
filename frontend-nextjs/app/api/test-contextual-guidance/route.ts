/**
 * Test Contextual Guidance Data Quality
 * GET /api/test-contextual-guidance
 *
 * Samples contextual_guidance_real table to assess data quality
 */

import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

export async function GET() {
  const pool = getPool();

  try {
    // Get table structure
    const columns = await pool.query(`
      SELECT column_name, data_type
      FROM information_schema.columns
      WHERE table_name = 'contextual_guidance_real'
      ORDER BY ordinal_position
    `);

    // Get total count
    const count = await pool.query('SELECT COUNT(*) FROM contextual_guidance_real');

    // Sample data - get 20 random rows
    const sample = await pool.query(`
      SELECT *
      FROM contextual_guidance_real
      ORDER BY RANDOM()
      LIMIT 20
    `);

    // Check data quality metrics
    const quality = await pool.query(`
      SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE guidance_text IS NOT NULL AND LENGTH(guidance_text) > 0) as has_text,
        COUNT(*) FILTER (WHERE guidance_text IS NULL OR LENGTH(guidance_text) = 0) as null_text,
        COUNT(*) FILTER (WHERE guidance_title IS NOT NULL) as has_title,
        COUNT(*) FILTER (WHERE document_id IS NOT NULL) as has_document_id,
        AVG(LENGTH(guidance_text)) FILTER (WHERE guidance_text IS NOT NULL) as avg_text_length,
        COUNT(DISTINCT guidance_type) as unique_types,
        COUNT(DISTINCT document_id) as unique_documents
      FROM contextual_guidance_real
    `);

    // Get guidance type distribution
    const types = await pool.query(`
      SELECT guidance_type, COUNT(*) as count
      FROM contextual_guidance_real
      GROUP BY guidance_type
      ORDER BY count DESC
    `);

    // Get sample guidance text lengths
    const lengths = await pool.query(`
      SELECT
        COUNT(*) FILTER (WHERE LENGTH(guidance_text) < 100) as very_short,
        COUNT(*) FILTER (WHERE LENGTH(guidance_text) BETWEEN 100 AND 500) as short,
        COUNT(*) FILTER (WHERE LENGTH(guidance_text) BETWEEN 500 AND 1000) as medium,
        COUNT(*) FILTER (WHERE LENGTH(guidance_text) > 1000) as long
      FROM contextual_guidance_real
      WHERE guidance_text IS NOT NULL
    `);

    return NextResponse.json({
      success: true,
      summary: {
        totalRows: parseInt(count.rows[0].count),
        columns: columns.rows.map(c => c.column_name),
        quality: quality.rows[0],
        textLengthDistribution: lengths.rows[0],
        guidanceTypes: types.rows
      },
      sampleData: sample.rows,
      assessment: assessDataQuality(quality.rows[0]),
      timestamp: new Date().toISOString()
    });

  } catch (error: any) {
    return NextResponse.json({
      success: false,
      error: error.message
    }, { status: 500 });
  }
}

function assessDataQuality(metrics: any): {
  usable: boolean;
  issues: string[];
  recommendations: string[];
} {
  const issues: string[] = [];
  const recommendations: string[] = [];

  const textCoverage = (metrics.has_text / metrics.total) * 100;
  const documentLinkage = (metrics.has_document_id / metrics.total) * 100;

  if (textCoverage < 80) {
    issues.push(`Only ${textCoverage.toFixed(0)}% of rows have guidance text`);
    recommendations.push('Consider filtering to only rows with text');
  }

  if (metrics.avg_text_length < 50) {
    issues.push(`Average text length is very short (${Math.round(metrics.avg_text_length)} chars)`);
    recommendations.push('May not provide meaningful context');
  }

  if (documentLinkage < 90) {
    issues.push(`Only ${documentLinkage.toFixed(0)}% linked to document_id`);
    recommendations.push('May be difficult to associate with specific provisions');
  }

  const usable = issues.length < 2 && textCoverage > 70;

  if (usable) {
    recommendations.push('Data quality sufficient for Phase 3 integration');
    recommendations.push('Build /api/contextual-guidance/{provision_id} endpoint');
  } else {
    recommendations.push('Data quality needs improvement before integration');
    recommendations.push('Consider data cleanup or re-extraction');
  }

  return { usable, issues, recommendations };
}
