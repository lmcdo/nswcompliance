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
import { toLgaSlug } from '@/lib/lga-slug';
import {
  fetchDcpControls,
  DcpControlRow,
  DcpControlsUnavailableError,
} from '@/lib/dcp-controls-client';

export const dynamic = 'force-dynamic';

// Map formerCouncil slug → dcp_setback_controls.lga value(s).
// Most are 1:1 (formerCouncil === lga slug). Inner West former councils
// (ashfield, leichhardt, marrickville) previously also queried 'inner_west',
// but those rows have been migrated to their correct former council slugs
// (PR #384) — which is why this map is empty rather than deleted: it is the
// hook for any future council that needs a one-to-many expansion.
const COUNCIL_TO_LGA: Record<string, string[]> = {};

// The display-name → slug table moved to lib/lga-slug.ts when /api/tod/parking-rates
// needed the same mapping; a third copy of a lookup table that can drift is how
// DQ-30 happened. Behaviour here is unchanged.
function getLgaSlugs(council: string): string[] {
  const normalized = toLgaSlug(council);
  if (!normalized) return [];
  return COUNCIL_TO_LGA[normalized] || [normalized];
}

// Group control_type values into display categories
/**
 * Our own paginated copies live on Cloudflare R2. Only these can carry a
 * #page anchor, because pdf_page was measured against them.
 */
/**
 * The exact hosts that serve PDFs we paginated ourselves.
 *
 * NOT a *.r2.dev suffix: r2.dev is a SHARED Cloudflare domain, so anyone can
 * publish a bucket under it and a suffix test would trust attacker.r2.dev.
 * One bucket host is in use — verified against dcp_chapter_registry
 * 2026-08-26, which holds exactly one distinct r2 origin.
 */
const OWN_PDF_HOSTS = new Set([
  'pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev',
  'verify.plotdetect.com.au',
]);
const OWN_PDF_PATH_PREFIX = '/pdf-pages/';

/**
 * True only for a PDF we paginated ourselves.
 *
 * Parses the URL and tests the HOSTNAME. A substring match would accept
 * https://example.com/evil/.r2.dev/x.pdf, i.e. a page anchor could be attached
 * to a document we never paginated - the precise-and-wrong case this guard
 * exists to prevent.
 */
function isOwnCopy(url: string): boolean {
  try {
    const u = new URL(url);
    if (!OWN_PDF_HOSTS.has(u.hostname)) return false;
    // /pdf-pages/ only means ours when served from our own host, so the host
    // check gates it rather than standing as an alternative to it.
    return (
      u.hostname !== 'verify.plotdetect.com.au' ||
      u.pathname.startsWith(OWN_PDF_PATH_PREFIX)
    );
  } catch {
    return false;   // unparseable: never anchor
  }
}

const CONTROL_CATEGORIES: Record<string, { label: string; order: number }> = {
  front_setback: { label: 'Setbacks', order: 1 },
  secondary_street_setback: { label: 'Setbacks', order: 1 },
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
  landscaped_area_min: { label: 'Landscaping & Canopy', order: 5 },
  front_setback_landscaping: { label: 'Landscaping & Canopy', order: 5 },
  deep_soil_min: { label: 'Landscaping & Canopy', order: 5 },
  tree_canopy_min: { label: 'Landscaping & Canopy', order: 5 },
  communal_open_space_min: { label: 'Open Space', order: 6 },
  communal_open_space: { label: 'Open Space', order: 6 },
  private_open_space: { label: 'Open Space', order: 6 },
  solar_access_hours: { label: 'Solar & Amenity', order: 7 },
  privacy_separation: { label: 'Privacy', order: 8 },
  fencing_height_max: { label: 'Fencing', order: 9 },
  dwelling_size_min: { label: 'Dwelling Size', order: 10 },
};

// Human-readable control type labels
const CONTROL_TYPE_LABELS: Record<string, string> = {
  front_setback: 'Front setback',
  secondary_street_setback: 'Secondary street setback',
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
  landscaped_area_min: 'Minimum landscaped area',
  front_setback_landscaping: 'Front setback landscaping',
  deep_soil_min: 'Minimum deep soil zone',
  tree_canopy_min: 'Tree canopy coverage',
  communal_open_space_min: 'Communal open space',
  communal_open_space: 'Communal open space',
  private_open_space: 'Private open space',
  solar_access_hours: 'Solar access (hours)',
  privacy_separation: 'Privacy separation',
  fencing_height_max: 'Maximum fence height',
  dwelling_size_min: 'Minimum dwelling size',
};

// Control types whose single value is a CEILING (a maximum, rendered "≤"),
// not a floor. Everything else is a minimum ("≥"). A max control stores its
// ceiling in value_min, so without this the UI would render e.g. a 65% maximum
// site coverage as "≥ 65%" — the inverse of the actual control. Keep in sync
// with any control_type whose label begins "Maximum".
const MAXIMUM_CONTROL_TYPES = new Set<string>([
  'max_site_coverage',
  'max_height',
  'fencing_height_max',
  'driveway_gradient',
]);

/** Whether a control's single value is a maximum (ceiling) or a minimum (floor). */
export type ControlDirection = 'min' | 'max';

/** Data status for a control row — drives distinct UI treatment */
export type ControlDataStatus = 'numeric' | 'not_applicable' | 'under_review';

export interface StructuredControl {
  control_type: string;
  control_label: string;
  direction: ControlDirection;
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
  data_status: ControlDataStatus;
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
    // Item 5 consolidation: rows come from the ONE guarded implementation
    // (conveyancing_db.fetch_dcp_setbacks via /pipeline/dcp-controls) —
    // is_current strict, needs_review excluded, deterministic order, as-at.
    // Two behaviour changes vs the old inline SQL, both deliberate:
    //   1. needs_review rows are EXCLUDED entirely (the old code served a
    //      flagged row as a normal number whenever it had a value — 35 rows
    //      measured 2026-08-03). 'under_review' can no longer occur.
    //   2. is_current is strict (measured: zero NULL rows, no served change).
    // The registry PDF map is per-council by construction, so the old
    // cross-council leak sentinel is structurally unnecessary here.
    const results = await Promise.all(
      lgaSlugs.map((slug) => fetchDcpControls(slug)),
    );

    // Each row keeps its OWN result's PDF map and metadata — flattening the
    // per-council maps by chapter_key alone could attach one former
    // council's PDF (or dcp_name/as-at) to another's control when a future
    // COUNCIL_TO_LGA expansion returns multiple slugs (Sol, 2026-08-04).
    type SourcedRow = DcpControlRow & {
      __pdfBase: string | null;
      __source: (typeof results)[number];
    };
    const allRows: SourcedRow[] = results.flatMap((r) =>
      r.available && r.rows
        ? r.rows.map((row) => ({
            ...row,
            __pdfBase:
              (row.source_chapter_key &&
                r.registry_pdf_urls?.[row.source_chapter_key]) || null,
            __source: r,
          }))
        : [],
    );
    const devRows = allRows.filter((r) => r.dev_type === devType);

    if (devRows.length === 0) {
      const availableDevTypes = [...new Set(allRows.map((r) => r.dev_type))];
      return NextResponse.json({
        council,
        dev_type: devType,
        has_controls: false,
        available_dev_types: availableDevTypes,
        categories: [],
      });
    }

    // Group by category
    const categoryMap = new Map<string, ControlCategory>();

    for (const row of devRows) {
      const catInfo = CONTROL_CATEGORIES[row.semantic_type] || { label: 'Other', order: 99 };
      const catKey = catInfo.label;

      if (!categoryMap.has(catKey)) {
        categoryMap.set(catKey, {
          category: catKey,
          order: catInfo.order,
          controls: [],
        });
      }

      // Build PDF URL with page anchor if available — resolved from the
      // row's OWN council's map at collection time (never cross-council).
      //
      // The page anchor is only appended to OUR OWN R2 copy. pdf_page is a page
      // number in the PDF we paginated; the council's own published PDF may be
      // a different split or edition, so carrying the anchor across would point
      // at a confidently WRONG page. An unanchored link to the right document
      // beats a precise link to the wrong page.
      let pdfUrl: string | null = row.__pdfBase;
      if (pdfUrl && row.pdf_page && isOwnCopy(pdfUrl)) {
        pdfUrl = `${pdfUrl}#page=${row.pdf_page}`;
      }

      const valueMin = row.value_min != null ? Number(row.value_min) : null;
      const valueMax = row.value_max != null ? Number(row.value_max) : null;
      const hasNumeric = valueMin !== null || valueMax !== null;

      // needs_review rows never reach this point (excluded at the guarded
      // source), so status is numeric or not_applicable; 'under_review'
      // remains in the type for consumers but cannot be emitted here.
      const dataStatus: ControlDataStatus = hasNumeric ? 'numeric' : 'not_applicable';

      const controlLabel = CONTROL_TYPE_LABELS[row.semantic_type] || row.semantic_type;
      // Ceiling if the type is a known maximum OR its label reads "Maximum …" —
      // the label backstop catches a future max_* type whose author updated the
      // label map but forgot MAXIMUM_CONTROL_TYPES. No minimum control is labelled
      // "Maximum", so this never mis-flags a floor.
      const direction: ControlDirection =
        MAXIMUM_CONTROL_TYPES.has(row.semantic_type) || /^Maximum\b/.test(controlLabel)
          ? 'max'
          : 'min';

      categoryMap.get(catKey)!.controls.push({
        control_type: row.semantic_type,
        control_label: controlLabel,
        direction,
        value_min: valueMin,
        value_max: valueMax,
        unit: row.unit,
        condition: row.notes || null,
        section_ref: row.clause || null,
        source_text: row.source_text,
        dcp_name: row.dcp_version,
        dcp_version: row.dcp_version,
        pdf_page: row.pdf_page != null ? Number(row.pdf_page) : null,
        pdf_url: pdfUrl,
        data_status: dataStatus,
      });
    }

    const categories = Array.from(categoryMap.values()).sort((a, b) => a.order - b.order);

    // Metadata comes from the result(s) that actually CONTRIBUTED the served
    // rows — never from a slug whose rows were all filtered out (Sol,
    // 2026-08-04: the first-available slug could label another slug's rows).
    const contributing = [...new Set(devRows.map((r) => r.__source))];
    const dcpName =
      contributing.find((r) => r.dcp_name)?.dcp_name ||
      devRows
        .map((r) => r.dcp_version)
        .filter((v): v is string => Boolean(v))
        .sort((a, b) => b.length - a.length)[0] ||
      null;

    const asAt = contributing.find((r) => r.as_at_line);

    return NextResponse.json({
      council,
      dev_type: devType,
      has_controls: true,
      dcp_name: dcpName,
      as_at: asAt?.as_at ?? null,
      as_at_line: asAt?.as_at_line ?? null,
      categories,
    });
  } catch (err) {
    if (err instanceof DcpControlsUnavailableError) {
      console.error('[dcp/structured-controls] source unavailable:', err.message);
      return NextResponse.json(
        { error: 'DCP controls source unavailable — try again shortly' },
        { status: 503 },
      );
    }
    console.error('[dcp/structured-controls] error:', err);
    return NextResponse.json({ error: 'Failed to fetch structured controls' }, { status: 500 });
  }
}
