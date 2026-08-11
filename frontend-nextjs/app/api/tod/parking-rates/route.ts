import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';
import { TODSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';
import { toLgaSlug } from '@/lib/lga-slug';
import { selectParkingRate, type ParkingControlRow } from '@/lib/parking-rate-selection';
import { fetchDcpControls } from '@/lib/dcp-controls-client';


export const dynamic = 'force-dynamic';
/**
 * TOD Parking Rates API
 *
 * Returns parking rates with source provenance:
 * 1. First checks SEPP Housing standards (overrides local DCP)
 * 2. Then checks council DCP provisions
 * 3. Returns "not found" if no authoritative source - no hardcoded fallbacks
 */

// Map development types to SEPP Housing dwelling types
const SEPP_DWELLING_TYPE_MAP: Record<string, string[]> = {
  'residential_flat': ['residential_flat_building', 'rfb'],
  'residential_flat_building': ['residential_flat_building', 'rfb'],
  'multi_dwelling': ['multi_dwelling_housing', 'mdh'],
  'multi_dwelling_housing': ['multi_dwelling_housing', 'mdh'],
  'shop_top_housing': ['shop_top_housing'],
  'boarding_house': ['boarding_house'],
  'dual_occupancy': ['dual_occupancy'],
  'dwelling_house': ['dwelling_house'],
  'manor_house': ['manor_house'],
  'townhouse': ['multi_dwelling_housing'],
  'terrace': ['multi_dwelling_housing'],
};


/**
 * Run one source tier, converting a thrown query into a recorded degradation.
 *
 * Each tier used to own a bare try/catch that logged and fell through. Three
 * problems with that: the caller could not tell "this tier found nothing" from
 * "this tier never ran"; the failure never reached the user; and a catch that
 * neither returns nor rethrows is exactly the shape the QA scanner flags as a
 * silent failure — correctly, as it turned out. Returning an explicit
 * discriminated result fixes all three, and makes each tier independently
 * testable.
 */
type TierResult<T> = { ok: true; rows: T[] } | { ok: false };

async function runTier<T>(
  label: string,
  degraded: string[],
  userMessage: string,
  query: () => Promise<{ rows: T[] }>,
): Promise<TierResult<T>> {
  try {
    const result = await query();
    return { ok: true, rows: result.rows };
  } catch (err) {
    console.error(`[Parking Rates API] ${label} failed:`, err);
    degraded.push(userMessage);
    return { ok: false };
  }
}

/**
 * GET /api/tod/parking-rates
 *
 * Fetches parking rates from authoritative sources with provenance:
 * 1. SEPP Housing standards (state-level, overrides DCP)
 * 2. Council DCP provisions
 *
 * Query params: zone, development_type, lga
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;

    // Validate query params using TODSchema
    const validation = validateRequest(TODSchema, {
      address: searchParams.get('lga') || 'N/A',
    });

    if (!validation.success) {
      return NextResponse.json({
        found: false,
        error: 'Invalid query parameters',
        details: formatValidationErrors(validation.details),
      }, { status: 400 });
    }

    const zone = searchParams.get('zone');
    const developmentType = searchParams.get('development_type');
    const lga = searchParams.get('lga');

    if (!developmentType) {
      return NextResponse.json({
        found: false,
        message: 'development_type parameter required'
      }, { status: 400 });
    }

    const pool = getPool();

    // Tiers that ERRORED, as opposed to legitimately finding nothing. The two are
    // not the same and must not read the same: an empty tier is an answer, a
    // crashed tier is an unknown. Every response carries this so a partial result
    // can never present itself as a complete one.
    const degraded: string[] = [];

    const lgaSlug = toLgaSlug(lga);

    // 1. First check SEPP Housing standards (authoritative, overrides local DCP)
    const seppDwellingTypes = SEPP_DWELLING_TYPE_MAP[developmentType] || [developmentType];

    const seppTier = await runTier('SEPP standards', degraded,
      'State SEPP (Housing) parking standards could not be read; a SEPP rate may '
      + 'exist and would override the council rate below.',
      () => pool.query(`
        SELECT standard_type, numeric_value, unit, source_clause, dwelling_type,
               effective_date, notes
        FROM housing_sepp_standards
        WHERE dwelling_type = ANY($1)
          AND standard_type IN ('parking_per_dwelling', 'parking_rate', 'car_parking')
          AND (is_current = true OR is_current IS NULL)
        ORDER BY CASE WHEN dwelling_type = $2 THEN 0 ELSE 1 END,
                 effective_date DESC NULLS LAST
        LIMIT 1
      `, [seppDwellingTypes, developmentType]));

    if (seppTier.ok && seppTier.rows.length > 0) {
      const row = seppTier.rows[0] as Record<string, any>;
      return NextResponse.json({
        found: true,
        rate: parseFloat(row.numeric_value),
        unit: row.unit || 'spaces',
        source: `SEPP (Housing) 2021 ${row.source_clause}`,
        source_clause: row.source_clause,
        source_url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714',
        dwelling_type: row.dwelling_type,
        effective_date: row.effective_date,
        notes: row.notes,
        authority: 'SEPP',
        sepp_override: true,
        degraded,
      });
    }

    // 2. Check council DCP numeric parking controls.
    //
    // Repointed off `regulatory_provisions JOIN dcps` — `dcps` has never existed
    // in the catalog and neither did 7 of the columns this selected, so this tier
    // threw on every call and degraded into the text search below. It is the same
    // repoint already made for /api/capacity/calculate: `dcp_setback_controls` is
    // the maintained numeric source (412 car_parking rows, 29 LGAs), keyed by the
    // council slug, needs_review-guarded fail-closed.
    //
    // `condition` is a row SELECTOR, not a footnote: a group can hold a resident
    // rate, a visitor rate and a zone-specific rate side by side. Measured across
    // the live table: of 123 (lga, dev_type) groups, 27 have exactly one
    // unconditioned row and 96 have none at all. Returning `LIMIT 1` from a
    // conditioned set would hand back "0.2 spaces/dwelling (visitor parking)" as
    // if it were the dwelling rate — the DQ-32 defect in a new place. So a single
    // `rate` is only stated when exactly one unconditioned row exists; otherwise
    // every row is returned with its condition for the reader to apply.
    if (lgaSlug) {
      // Item 5 consolidation: rows come from the ONE guarded implementation
      // via /pipeline/dcp-controls (is_current strict, needs_review excluded
      // at source). The exact-dev-type-first / unconditioned-first / value
      // ordering the selector expects is reproduced deterministically here —
      // it is presentation ordering over already-guarded rows, not a guard.
      const dcpTier = await runTier<ParkingControlRow>('DCP numeric query', degraded,
        'Council DCP numeric parking rates could not be read; showing provision text only.',
        async () => {
          const dcp = await fetchDcpControls(lgaSlug);
          const rows = (dcp.available && dcp.rows ? dcp.rows : [])
            .filter((r) =>
              r.semantic_type === 'car_parking' &&
              (r.dev_type === developmentType || r.dev_type === 'universal_residential'))
            .map((r) => ({
              value_min: r.value_min,
              value_max: r.value_max,
              unit: r.unit,
              condition: r.notes || null,
              source_text: r.source_text,
              section_ref: r.clause || null,
              dcp_version: r.dcp_version,
              pdf_page: r.pdf_page,
              dev_type: r.dev_type,
            }))
            .sort((a, b) => {
              const exactA = a.dev_type === developmentType ? 0 : 1;
              const exactB = b.dev_type === developmentType ? 0 : 1;
              if (exactA !== exactB) return exactA - exactB;
              const condA = (a.condition ?? '').trim() ? 1 : 0;
              const condB = (b.condition ?? '').trim() ? 1 : 0;
              if (condA !== condB) return condA - condB;
              const vA = a.value_min ?? Number.POSITIVE_INFINITY;
              const vB = b.value_min ?? Number.POSITIVE_INFINITY;
              return vA - vB;
            });
          return { rows } as { rows: ParkingControlRow[] };
        });

      if (dcpTier.ok) {
        const selection = selectParkingRate(dcpTier.rows);

        if (selection.kind === 'single') {
          const { base, additional, dcpVersion } = selection;
          return NextResponse.json({
            found: true,
            has_numeric_rate: true,
            rate: base.rate,
            rate_max: base.rate_max,
            unit: base.unit,
            source: `${dcpVersion ?? 'Council DCP'} ${base.section_ref ?? ''}`.trim(),
            section_ref: base.section_ref,
            requirement_text: base.source_text,
            pdf_page: base.pdf_page,
            // Conditioned siblings (visitor spaces, zone-specific rates) are
            // ADDITIONAL to the base rate, never a replacement for it.
            additional_rates: additional,
            authority: 'DCP',
            sepp_override: false,
            degraded,
          });
        }

        if (selection.kind === 'conditional') {
          // No single unconditioned row: there is no such thing as "the rate"
          // here. Return every row with its condition and say so, rather than
          // breaking the tie by ordering and presenting a guess as a number.
          return NextResponse.json({
            found: true,
            has_numeric_rate: false,
            rates: selection.rates,
            source: selection.dcpVersion ?? 'Council DCP',
            authority: 'DCP',
            sepp_override: false,
            note: 'This council sets parking rates by condition (for example resident '
              + 'versus visitor, or by zone). Every applicable rate is listed with the '
              + 'condition it applies under; no single rate covers this development type.',
            degraded,
          });
        }
      }
    }

    // 3. Return DCP provision text even without numeric extraction
    // Professionals read the actual provision - we provide the text + PDF source
    if (lga) {
      const textTier = await runTier<Record<string, any>>('provision text query', degraded,
        'Council DCP provision text could not be read.',
        () => pool.query(`
          SELECT id, section_header, provision_text, document_id, provision_type,
                 pdf_page, pdf_page_image_url
          FROM regulatory_provisions
          WHERE document_id ILIKE $1
            AND v2_is_actionable = true
            AND (
              provision_text ~* 'parking|car space|vehicle space'
              OR section_header ~* 'parking'
            )
          ORDER BY CASE
                     WHEN section_header ~* 'parking' THEN 0
                     WHEN provision_text ~* 'parking rate|spaces per' THEN 1
                     ELSE 2
                   END,
                   pdf_page
          LIMIT 5
        `, [`%${lga}%`]));

      if (textTier.ok && textTier.rows.length > 0) {
        return NextResponse.json({
          found: true,
          has_numeric_rate: false,
          provisions: textTier.rows.map((row) => ({
            id: row.id,
            title: row.section_header,
            text: row.provision_text,
            pdf_page: row.pdf_page,
            pdf_page_image_url: row.pdf_page_image_url,
            document_id: row.document_id,
          })),
          source: (textTier.rows[0]?.document_id ?? '').replace(/_/g, ' '),
          council: lga,
          authority: 'DCP',
          note: 'Parking requirements vary by development type and context. Review the '
            + 'provision text to determine applicable rate.',
          degraded,
        });
      }
    }

    // Nothing found. Whether that means "we looked everywhere and this council
    // publishes no rate" or "every lookup crashed" is the difference between an
    // answer and an outage, and the caller cannot tell them apart from the
    // outside — so they get different shapes.
    if (degraded.length > 0) {
      return NextResponse.json({
        found: false,
        unavailable: true,
        error: 'Parking rates could not be determined: one or more sources failed to load.',
        degraded,
        message: 'This is not a finding that no rate exists. Do not read it as "no '
          + 'parking requirement" — the sources were not successfully consulted.',
      }, { status: 503 });
    }

    return NextResponse.json({
      found: false,
      unavailable: false,
      degraded,
      message: `No parking provisions found${lga ? ` for ${lga}` : ''}. The DCP may not be loaded or parking may be in a different section.`
    });

  } catch (error) {
    console.error('[Parking Rates API] Error:', error);
    return NextResponse.json({
      found: false,
      error: error instanceof Error ? error.message : 'Internal server error'
    }, { status: 500 });
  }
}
