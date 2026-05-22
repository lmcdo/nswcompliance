/**
 * GET /api/dcp/structured-controls?council=waverley&dev_type=dwelling_house
 *
 * Returns extracted numeric DCP controls from dcp_setback_controls table,
 * grouped by category for display in the assessment DCP tab.
 *
 * These are deterministic, structured values extracted from council DCPs —
 * not AI-generated or RAG-retrieved text.
 *
 * Query params:
 *   council  — formerCouncil slug (e.g. "ashfield", "waverley", "ku_ring_gai")
 *   dev_type — development type slug (default: "dwelling_house")
 */

import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

// Map formerCouncil slug → dcp_setback_controls.lga value(s)
// Most are 1:1 (formerCouncil === lga slug), but Inner West former councils
// may have controls under both the former council slug AND 'inner_west'.
const COUNCIL_TO_LGA: Record<string, string[]> = {
  ashfield: ['ashfield', 'inner_west'],
  leichhardt: ['leichhardt', 'inner_west'],
  marrickville: ['marrickville', 'inner_west'],
};

// LGA display names that differ from their dcp_setback_controls.lga slug
const LGA_NAME_TO_SLUG: Record<string, string> = {
  city_of_parramatta: 'parramatta',
  sydney: 'city_of_sydney',
  the_hills_shire: 'the_hills',
  city_of_canada_bay: 'canada_bay',
  city_of_ryde: 'ryde',
  strathfield_municipal: 'strathfield',
};

function getLgaSlugs(council: string): string[] {
  let normalized = council.toLowerCase().replace(/[-\s]+/g, '_').replace(/[^a-z0-9_]/g, '');
  normalized = LGA_NAME_TO_SLUG[normalized] || normalized;
  return COUNCIL_TO_LGA[normalized] || [normalized];
}

// Group control_type values into display categories
const CONTROL_CATEGORIES: Record<string, { label: string; order: number }> = {
  front_setback: { label: 'Setbacks', order: 1 },
  side_setback: { label: 'Setbacks', order: 1 },
  rear_setback: { label: 'Setbacks', order: 1 },
  separation_from_dwelling: { label: 'Setbacks', order: 1 },
  car_parking: { label: 'Parking', order: 2 },
  bicycle_parking: { label: 'Parking', order: 2 },
  driveway_width: { label: 'Parking', order: 2 },
  driveway_gradient: { label: 'Parking', order: 2 },
  max_site_coverage: { label: 'Site Coverage', order: 3 },
  max_height: { label: 'Height', order: 4 },
  landscaping_min: { label: 'Landscaping & Canopy', order: 5 },
  deep_soil_min: { label: 'Landscaping & Canopy', order: 5 },
  tree_canopy_min: { label: 'Landscaping & Canopy', order: 5 },
  communal_open_space_min: { label: 'Open Space', order: 6 },
  private_open_space: { label: 'Open Space', order: 6 },
  solar_access_hours: { label: 'Solar & Amenity', order: 7 },
  privacy_separation: { label: 'Privacy', order: 8 },
  fencing_height_max: { label: 'Fencing', order: 9 },
  dwelling_size_min: { label: 'Dwelling Size', order: 10 },
};

// Human-readable control type labels
const CONTROL_TYPE_LABELS: Record<string, string> = {
  front_setback: 'Front setback',
  side_setback: 'Side setback',
  rear_setback: 'Rear setback',
  separation_from_dwelling: 'Separation from dwelling',
  car_parking: 'Car parking',
  bicycle_parking: 'Bicycle parking',
  driveway_width: 'Minimum driveway width',
  driveway_gradient: 'Maximum driveway gradient',
  max_site_coverage: 'Maximum site coverage',
  max_height: 'Maximum height',
  landscaping_min: 'Minimum landscaped area',
  deep_soil_min: 'Minimum deep soil zone',
  tree_canopy_min: 'Tree canopy coverage',
  communal_open_space_min: 'Communal open space',
  private_open_space: 'Private open space',
  solar_access_hours: 'Solar access (hours)',
  privacy_separation: 'Privacy separation',
  fencing_height_max: 'Maximum fence height',
  dwelling_size_min: 'Minimum dwelling size',
};

export interface StructuredControl {
  control_type: string;
  control_label: string;
  value_min: number | null;
  value_max: number | null;
  unit: string | null;
  condition: string | null;
  section_ref: string | null;
  source_text: string | null;
  dcp_name: string | null;
  dcp_version: string | null;
  pdf_page: number | null;
  pdf_url: string | null;
}

export interface ControlCategory {
  category: string;
  order: number;
  controls: StructuredControl[];
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const council = searchParams.get('council');
  const devType = searchParams.get('dev_type') || 'dwelling_house';

  if (!council) {
    return NextResponse.json({ error: 'council parameter is required' }, { status: 400 });
  }

  const lgaSlugs = getLgaSlugs(council);

  try {
    const pool = getPool();

    // Build parameterized IN clause
    const placeholders = lgaSlugs.map((_, i) => `$${i + 1}`).join(', ');
    const result = await pool.query(
      `SELECT sc.control_type, sc.value_min, sc.value_max, sc.unit, sc.condition,
              sc.section_ref, sc.source_text, sc.dcp_version, sc.pdf_page,
              sc.source_chapter_key,
              cr.r2_public_pdf_url, cr.chapter_label, cr.dcp_name
       FROM dcp_setback_controls sc
       LEFT JOIN dcp_chapter_registry cr
         ON sc.source_chapter_key = cr.chapter_key
         AND cr.is_active = true
       WHERE sc.lga IN (${placeholders})
         AND sc.dev_type = $${lgaSlugs.length + 1}
         AND (sc.is_current IS NULL OR sc.is_current = true)
       ORDER BY sc.control_type, sc.section_ref`,
      [...lgaSlugs, devType],
    );

    if (result.rows.length === 0) {
      // Check if this council has ANY controls (regardless of dev_type)
      const anyResult = await pool.query(
        `SELECT COUNT(*) as count, array_agg(DISTINCT dev_type) as dev_types
         FROM dcp_setback_controls
         WHERE lga IN (${placeholders})
           AND (is_current IS NULL OR is_current = true)`,
        lgaSlugs,
      );

      const hasAnyControls = parseInt(anyResult.rows[0]?.count || '0') > 0;
      const availableDevTypes = anyResult.rows[0]?.dev_types || [];

      return NextResponse.json({
        council,
        dev_type: devType,
        has_controls: false,
        available_dev_types: hasAnyControls ? availableDevTypes : [],
        categories: [],
      });
    }

    // Group by category
    const categoryMap = new Map<string, ControlCategory>();

    for (const row of result.rows) {
      const catInfo = CONTROL_CATEGORIES[row.control_type] || { label: 'Other', order: 99 };
      const catKey = catInfo.label;

      if (!categoryMap.has(catKey)) {
        categoryMap.set(catKey, {
          category: catKey,
          order: catInfo.order,
          controls: [],
        });
      }

      // Build PDF URL with page anchor if available
      let pdfUrl: string | null = row.r2_public_pdf_url || null;
      if (pdfUrl && row.pdf_page) {
        pdfUrl = `${pdfUrl}#page=${row.pdf_page}`;
      }

      categoryMap.get(catKey)!.controls.push({
        control_type: row.control_type,
        control_label: CONTROL_TYPE_LABELS[row.control_type] || row.control_type,
        value_min: row.value_min ? parseFloat(row.value_min) : null,
        value_max: row.value_max ? parseFloat(row.value_max) : null,
        unit: row.unit,
        condition: row.condition,
        section_ref: row.section_ref,
        source_text: row.source_text,
        dcp_name: row.dcp_name || row.dcp_version,
        dcp_version: row.dcp_version,
        pdf_page: row.pdf_page ? parseInt(row.pdf_page) : null,
        pdf_url: pdfUrl,
      });
    }

    const categories = Array.from(categoryMap.values()).sort((a, b) => a.order - b.order);

    // Extract DCP name — prefer the longest dcp_version (usually the formal name)
    const dcpName = result.rows
      .map(r => r.dcp_name || r.dcp_version)
      .filter(Boolean)
      .sort((a: string, b: string) => b.length - a.length)[0] || null;

    return NextResponse.json({
      council,
      dev_type: devType,
      has_controls: true,
      dcp_name: dcpName,
      categories,
    });
  } catch (err) {
    console.error('[dcp/structured-controls] DB error:', err);
    return NextResponse.json({ error: 'Failed to fetch structured controls' }, { status: 500 });
  }
}
