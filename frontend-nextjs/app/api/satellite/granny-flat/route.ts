import { NextRequest, NextResponse } from 'next/server';
import { getResend } from '@/lib/resend-client';
import { createClient } from '@supabase/supabase-js';
import { NSW_STANDARD_ZONES } from '@/lib/regulatory-constants';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

export const dynamic = 'force-dynamic';
// Confirm action calls Python with 30s AbortSignal; detect (dev) has 180s. maxDuration must exceed both.
export const maxDuration = 60;

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

// NSW Standard Instrument zone names (source: Standard Instrument (Local Environmental Plans) Order 2006)
// These are official zone identifiers, not regulatory controls — safe to keep as a display lookup.
const NSW_ZONE_NAMES: Record<string, string> = {
  R1: 'General Residential', R2: 'Low Density Residential',
  R3: 'Medium Density Residential', R4: 'High Density Residential',
  R5: 'Large Lot Residential',
  RU1: 'Primary Production', RU2: 'Rural Landscape', RU3: 'Forestry',
  RU4: 'Primary Production Small Lots', RU5: 'Village', RU6: 'Transition',
  MU1: 'Mixed Use',
  E1: 'Local Centre', E2: 'Commercial Centre', E3: 'Productivity Support',
  E4: 'General Industrial', E5: 'Heavy Industrial',
  IN1: 'General Industrial', IN2: 'Light Industrial',
  IN3: 'Heavy Industrial', IN4: 'Working Waterfront',
  SP1: 'Special Activities', SP2: 'Infrastructure', SP3: 'Tourist',
  RE1: 'Public Recreation', RE2: 'Private Recreation',
  C1: 'Environmental Protection', C2: 'Environmental Conservation',
  C3: 'Environmental Management', C4: 'Environmental Living',
  W1: 'Natural Waterways', W2: 'Recreational Waterways',
  W3: 'Working Waterways', W4: 'Working Waterways',
  // Legacy B zones (pre-2023 reform — still present on some LEPs)
  B1: 'Neighbourhood Centre', B2: 'Local Centre', B3: 'Commercial Core',
  B4: 'Mixed Use', B5: 'Business Development', B6: 'Enterprise Corridor',
  B7: 'Business Park', B8: 'Metropolitan Centre',
};
const TRIGGER_API = 'https://api.trigger.dev/api/v1/tasks/satellite-job-runner/trigger';
const TRIGGER_SECRET = process.env.TRIGGER_SECRET_KEY!;

// ePlanning API — DA and CDC history lookup by lot/DP
const EPLANNING_BASE = 'https://api.apps1.nsw.gov.au/eplanning/data/v0';
const SECONDARY_DWELLING_TYPES = ['secondary dwelling', 'granny flat', 'secondary dwelling (granny flat)'];

interface EplanningApplication {
  type: 'DA' | 'CDC';
  development_type: string;
  status: string;
  lodgement_date: string | null;
  reference: string;
}

interface EplanningHistory {
  found: boolean;
  applications: EplanningApplication[];
  source_note: string;
  error: 'timeout' | 'unavailable' | null;
}

function parseLotDp(lot_description: string | null): { lot: string; dp: string } | null {
  if (!lot_description) return null;
  const m = lot_description.match(/\bLot\s+(\w+)\s+DP\s+(\d+)/i);
  if (!m) return null;
  return { lot: m[1], dp: m[2] };
}

async function queryEPlanning(lot_description: string | null): Promise<EplanningHistory> {
  const parsed = parseLotDp(lot_description);
  if (!parsed) {
    return { found: false, applications: [], source_note: 'Lot/DP reference not available for this property.', error: null };
  }

  const { lot, dp } = parsed;
  const params = new URLSearchParams({
    'filters[LotNumber]': lot,
    'filters[SectionNumber]': '',
    'filters[PlanNumber]': dp,
    'filters[PageSize]': '20',
    'filters[PageNumber]': '1',
  });
  const headers = { Accept: 'application/json' };

  const [daResult, cdcResult] = await Promise.allSettled([
    fetch(`${EPLANNING_BASE}/OnlineDA?${params}`, { headers, signal: AbortSignal.timeout(8_000) })
      .then(r => r.ok ? r.json() : null)
      .catch(() => null),
    fetch(`${EPLANNING_BASE}/OnlineCDC?${params}`, { headers, signal: AbortSignal.timeout(8_000) })
      .then(r => r.ok ? r.json() : null)
      .catch(() => null),
  ]);

  const timedOut = daResult.status === 'rejected' || cdcResult.status === 'rejected';
  const daData = daResult.status === 'fulfilled' ? daResult.value : null;
  const cdcData = cdcResult.status === 'fulfilled' ? cdcResult.value : null;

  const daApps: EplanningApplication[] = [];
  const cdcApps: EplanningApplication[] = [];

  if (daData?.Application) {
    for (const app of daData.Application) {
      const devType: string = (app.DevelopmentType ?? app.ApplicationType ?? '').toLowerCase();
      if (SECONDARY_DWELLING_TYPES.some(t => devType.includes(t))) {
        daApps.push({
          type: 'DA',
          development_type: app.DevelopmentType ?? 'Secondary dwelling',
          status: app.ApplicationStatus ?? 'Unknown',
          lodgement_date: app.LodgementDate ?? null,
          reference: app.LodgementNumber ?? app.ApplicationNumber ?? '',
        });
      }
    }
  }

  if (cdcData?.Application) {
    for (const app of cdcData.Application) {
      const devType: string = (app.DevelopmentType ?? app.ApplicationType ?? '').toLowerCase();
      if (SECONDARY_DWELLING_TYPES.some(t => devType.includes(t))) {
        cdcApps.push({
          type: 'CDC',
          development_type: app.DevelopmentType ?? 'Secondary dwelling',
          status: app.ApplicationStatus ?? 'Issued',
          lodgement_date: app.LodgementDate ?? null,
          reference: app.CertificateNumber ?? app.LodgementNumber ?? '',
        });
      }
    }
  }

  const applications = [...daApps, ...cdcApps];

  if (timedOut && applications.length === 0) {
    return { found: false, applications: [], source_note: 'NSW ePlanning Portal lookup timed out.', error: 'timeout' };
  }
  if (!daData && !cdcData && !timedOut) {
    return { found: false, applications: [], source_note: 'NSW ePlanning Portal unavailable.', error: 'unavailable' };
  }

  return {
    found: applications.length > 0,
    applications,
    source_note: 'Records available from approximately 2012. "Determined" status covers both approved and refused applications — approval cannot be confirmed from this data.',
    error: null,
  };
}

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

/**
 * POST /api/satellite/granny-flat
 * Body: { address: string, action: 'detect' | 'confirm', ...confirmPayload? }
 *
 * action=detect (async — LangSAM inference can exceed Vercel 60s limit):
 *   Geocodes address, pre-allocates a granny_flat_reports row, triggers
 *   satellite-job-runner Trigger.dev task → returns { jobId }.
 *   Frontend polls GET /api/satellite/granny-flat?jobId=X every 2s.
 *   When status='detected', the detect result is in the response.
 *
 * action=confirm (direct — <30s):
 *   User confirmed structure count. Calls /pipeline/granny-flat/confirm directly.
 */
export async function POST(request: NextRequest) {
  // Per-product rate limit — LangSAM inference is expensive
  const clientIP = getClientIdentifier(request);
  const rl = await checkRateLimit(clientIP, satelliteRateLimiter, 10, 60000);
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again later.' },
      { status: 429, headers: createRateLimitHeaders(rl) },
    );
  }

  let body: {
    address?: string;
    action?: 'detect' | 'confirm';
    notification_email?: string;
    detect_id?: string;
    confirmed_structure_count?: number;
    samgeo_structure_count?: number;
    postcode?: string;
    report_id?: string;
    existing_secondary_dwelling?: boolean | null;
    main_dwelling_area_m2?: number | null;
    // How confirmed_structure_count came to hold its value. Three states —
    // an absent value is 'unrecorded' downstream, never treated as a human
    // check. See services/granny_flat.CountSource.
    confirmed_count_source?: 'secondary_detections_classified' | 'machine_default' | 'unrecorded';
    // Per-structure human answers, bound to detected_structures[].index.
    // Previously computed in the browser and discarded.
    structure_types?: { index: number; answer: string }[];
  };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { address, action = 'detect', notification_email } = body;
  // #745 D3: the brief's VG-reconciled lot area — forwarded so the detect
  // pipeline uses the SAME figure as every other card (single source of truth).
  const lotAreaM2: number | null =
    typeof (body as { lot_area_m2?: unknown }).lot_area_m2 === 'number'
      ? ((body as { lot_area_m2: number }).lot_area_m2)
      : null;
  if (!address?.trim()) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  // Resolve address for both actions
  const propUrl = `${new URL(request.url).origin}/api/property/${encodeURIComponent(address)}`;
  const internalHeaders: Record<string, string> = {};
  if (process.env.API_KEY) internalHeaders['x-api-key'] = process.env.API_KEY;
  const propResp = await fetch(propUrl, { headers: internalHeaders, signal: AbortSignal.timeout(10_000) }).catch(() => null);
  if (!propResp?.ok) {
    return NextResponse.json({ error: `Could not resolve address: ${address}` }, { status: 422 });
  }

  const propData = await propResp.json();
  if (!propData.success || !propData.property) {
    return NextResponse.json(
      { error: propData.error ?? 'Could not resolve address' },
      { status: 422 },
    );
  }

  const prop_id = String(propData.property.prop_id);
  const lotGeometry = propData.lotGeometry ?? null;

  let lat: number | null = propData.property.coordinates?.lat ?? null;
  let lng: number | null = propData.property.coordinates?.lng ?? null;

  if ((!lat || !lng) && lotGeometry?.rings?.[0]?.length) {
    // Rings are EPSG:3857 (Mercator metres) — convert centroid to WGS84
    const ring: [number, number][] = lotGeometry.rings[0];
    const xMerc = ring.reduce((s: number, p: [number, number]) => s + p[0], 0) / ring.length;
    const yMerc = ring.reduce((s: number, p: [number, number]) => s + p[1], 0) / ring.length;
    const R = 20037508.342789244;
    lng = xMerc * 180.0 / R;
    lat = (Math.atan(Math.exp(yMerc * Math.PI / R)) * 2 - Math.PI / 2) * (180 / Math.PI);
  }

  if (!lat || !lng) {
    return NextResponse.json(
      { error: 'Could not determine coordinates for this address' },
      { status: 422 },
    );
  }

  // Convert EPSG:3857 lot geometry ring to WGS84 GeoJSON polygon + centroid
  let lotPolygonWgs84: { type: 'Polygon'; coordinates: number[][][] } | null = null;
  let centroidLat = lat as number;
  let centroidLng = lng as number;
  if (lotGeometry?.rings?.[0]?.length) {
    const R = 20037508.342789244;
    const ring: [number, number][] = lotGeometry.rings[0];
    const wgs84Ring = ring.map(([x, y]: [number, number]): [number, number] => [
      x * 180.0 / R,
      (Math.atan(Math.exp(y * Math.PI / R)) * 2 - Math.PI / 2) * (180 / Math.PI),
    ]);
    lotPolygonWgs84 = { type: 'Polygon', coordinates: [wgs84Ring] };
    centroidLng = wgs84Ring.reduce((s, p) => s + p[0], 0) / wgs84Ring.length;
    centroidLat = wgs84Ring.reduce((s, p) => s + p[1], 0) / wgs84Ring.length;
  }

  // -------------------------------------------------------------------------
  // Eligibility gates — run before pre-allocating Supabase row or firing SAM
  // All return { ineligible: true, error, evidence? } so the frontend can
  // render a result card with specific authoritative evidence.
  // -------------------------------------------------------------------------

  // Gate 1: Unit / apartment / shop address
  // Check the canonical NSW Planning Portal address (structured, not user input).
  // Match only when a known indicator is at the start followed by a number,
  // e.g. "UNIT 5 43 SHORELINE DR" — avoids false positives like "Flat Rock Rd".
  const canonicalAddress: string = (propData.property as { address?: string })?.address ?? '';
  if (/^(UNIT|APT|APARTMENT|FLAT|SUITE|LEVEL|SHOP|OFFICE|U)\s+\d/i.test(canonicalAddress)) {
    return NextResponse.json(
      {
        ineligible: true,
        error:
          'This address contains a unit or apartment number. SEPP Housing 2021 (cl 53) secondary dwelling provisions apply to individual lots containing a dwelling house — not strata units, apartments, or commercial tenancies.',
        evidence: canonicalAddress,
        evidence_label: 'NSW Planning Portal — canonical address',
      },
      { status: 422 },
    );
  }

  // Gate 2: Strata Plan lot (SP number in lot description)
  // Lot descriptions are "Lot 1 SP 87654" (strata) or "Lot 12 DP 123456" (Torrens).
  // Strata lots are typically individual units within a multi-dwelling building.
  const lot_description: string | null = (propData as { lot_description?: string | null }).lot_description ?? null;
  if (lot_description) {
    const spMatch = lot_description.match(/\bSP\s*(\d+)\b/i);
    if (spMatch) {
      return NextResponse.json(
        {
          ineligible: true,
          error:
            `This lot is registered on Strata Plan ${spMatch[1]}. Secondary dwelling provisions under SEPP Housing 2021 apply to lots containing a single dwelling house — lots within a strata scheme are typically units or apartments within a larger building and do not qualify.`,
          evidence: lot_description,
          evidence_label: 'NSW Planning Portal — lot registration',
        },
        { status: 422 },
      );
    }
  }

  // Gate 3: Zone not in eligible residential set
  // DQ-30 (.claude/DATA_QUALITY_TRACKER.md): consolidated onto
  // NSW_STANDARD_ZONES.RESIDENTIAL — was independently declared in 4 files.
  const ELIGIBLE_ZONE_PREFIXES = NSW_STANDARD_ZONES.RESIDENTIAL as readonly string[];
  const zone: string | null = (propData.property as { zone?: string | null })?.zone ?? null;
  if (zone) {
    const eligible = ELIGIBLE_ZONE_PREFIXES.some((p) => zone.startsWith(p));
    if (!eligible) {
      return NextResponse.json(
        {
          ineligible: true,
          error:
            'SEPP (Housing) 2021 ch 3 pt 1 applies to secondary dwellings on land in a residential zone (R1–R5 or an equivalent zone) where a dwelling house is permissible. This lot’s zone is outside those zones, so the SEPP pathway does not apply here. A council LEP can separately permit secondary dwellings — check the zone’s land-use table in the LEP.',
          evidence: NSW_ZONE_NAMES[zone] ? `${zone} — ${NSW_ZONE_NAMES[zone]}` : zone,
          evidence_label: 'NSW Planning Portal — land zoning',
        },
        { status: 422 },
      );
    }
  }

  // -------------------------------------------------------------------------
  // DETECT — async via Trigger.dev (production) / direct Python call (dev)
  // -------------------------------------------------------------------------
  if (action === 'detect') {
    // Pre-allocate report row so frontend can poll immediately
    const { data: reportRow, error: insertError } = await getSupabase()
      .from('granny_flat_reports')
      .insert({
        product: 'granny-flat',
        address,
        lat,
        lng,
        prop_id,
        run_date: new Date().toISOString().slice(0, 10),
        confidence: null,
        outputs: null,
      })
      .select('id')
      .single();

    if (insertError || !reportRow) {
      console.error('[granny-flat] Failed to pre-allocate report row:', insertError);
      return NextResponse.json({ error: 'Failed to initialise report' }, { status: 500 });
    }

    const jobId = reportRow.id as string;

    // In local dev, call Python directly (Trigger.dev can't reach localhost).
    if (process.env.NODE_ENV === 'development') {
      let detectResp: Response;
      try {
        detectResp = await fetch(`${PYTHON_API}/pipeline/granny-flat/detect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ address, lat, lng, prop_id, report_id: jobId, lot_geometry: lotGeometry, ...(lotAreaM2 != null ? { lot_area_m2: lotAreaM2 } : {}) }),
          signal: AbortSignal.timeout(180_000),
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        return NextResponse.json({ error: `Detect failed: ${msg}` }, { status: 502 });
      }
      if (!detectResp.ok) {
        const text = await detectResp.text().catch(() => '');
        return NextResponse.json({ error: `Detect error (${detectResp.status}): ${text}` }, { status: 502 });
      }
      return NextResponse.json({ jobId, lotPolygonWgs84, centroidLat, centroidLng }, { status: 202 });
    }

    const triggerResp = await fetch(TRIGGER_API, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${TRIGGER_SECRET}`,
      },
      body: JSON.stringify({
        payload: {
          product: 'granny-flat',
          endpoint_suffix: '/detect',
          address,
          lat,
          lng,
          prop_id,
          report_id: jobId,
          extra_body: { lot_geometry: lotGeometry, ...(lotAreaM2 != null ? { lot_area_m2: lotAreaM2 } : {}) },
          ...(notification_email ? { notification_email } : {}),
        },
      }),
    });

    if (!triggerResp.ok) {
      const text = await triggerResp.text();
      console.error('[granny-flat] Trigger.dev error:', text);
      return NextResponse.json(
        { jobId, warning: 'Pipeline enqueue failed — retry or check Trigger.dev dashboard' },
        { status: 202 },
      );
    }

    return NextResponse.json({ jobId, lotPolygonWgs84, centroidLat, centroidLng }, { status: 202 });
  }

  // -------------------------------------------------------------------------
  // CONFIRM — direct call (<30s)
  // -------------------------------------------------------------------------
  if (action === 'confirm') {
    const { detect_id, confirmed_structure_count, samgeo_structure_count, postcode, report_id, existing_secondary_dwelling, main_dwelling_area_m2, notification_email, confirmed_count_source, structure_types } = body;

    if (!detect_id) {
      return NextResponse.json({ error: 'detect_id is required for confirm action' }, { status: 400 });
    }
    if (confirmed_structure_count == null) {
      return NextResponse.json(
        { error: 'confirmed_structure_count is required for confirm action' },
        { status: 400 },
      );
    }
    if (
      !Number.isInteger(confirmed_structure_count) ||
      confirmed_structure_count < 0 ||
      confirmed_structure_count > 20
    ) {
      return NextResponse.json(
        { error: 'confirmed_structure_count must be an integer between 0 and 20' },
        { status: 400 },
      );
    }

    if (existing_secondary_dwelling !== undefined && existing_secondary_dwelling !== null &&
        typeof existing_secondary_dwelling !== 'boolean') {
      return NextResponse.json(
        { error: 'existing_secondary_dwelling must be boolean or null' },
        { status: 400 },
      );
    }

    // Reject a bad provenance value rather than coercing it. Silently
    // defaulting an unknown string to 'secondary_detections_classified' would manufacture the
    // exact claim this field exists to make falsifiable.
    const COUNT_SOURCES = ['secondary_detections_classified', 'machine_default', 'unrecorded'] as const;
    if (confirmed_count_source !== undefined &&
        !COUNT_SOURCES.includes(confirmed_count_source)) {
      return NextResponse.json(
        { error: `confirmed_count_source must be one of ${COUNT_SOURCES.join(', ')}` },
        { status: 400 },
      );
    }

    const STRUCTURE_ANSWERS = ['part_of_main', 'garage', 'existing_gf', 'unsure', 'rejected', 'kept'];
    if (structure_types !== undefined) {
      if (!Array.isArray(structure_types) || structure_types.length > 40) {
        return NextResponse.json(
          { error: 'structure_types must be an array of at most 40 entries' },
          { status: 400 },
        );
      }
      const bad = structure_types.find(
        (s) => !s || !Number.isInteger(s.index) || s.index < 0 || s.index > 100 ||
               !STRUCTURE_ANSWERS.includes(s.answer),
      );
      if (bad) {
        return NextResponse.json(
          { error: `structure_types entries must be {index: int, answer: one of ${STRUCTURE_ANSWERS.join('|')}}` },
          { status: 400 },
        );
      }
      const indexes = structure_types.map((s) => s.index);
      if (new Set(indexes).size !== indexes.length) {
        return NextResponse.json(
          { error: 'structure_types contains duplicate index values' },
          { status: 400 },
        );
      }
    }

    // A claim of human review with no recorded answers behind it is the same
    // unfalsifiable assertion this field exists to remove — refuse it here as
    // well as in the Python model, so neither entry point can create a row
    // whose own fields contradict each other.
    if (confirmed_count_source === 'secondary_detections_classified' &&
        (!structure_types || structure_types.length === 0)) {
      return NextResponse.json(
        { error: "confirmed_count_source='secondary_detections_classified' requires a non-empty structure_types" },
        { status: 400 },
      );
    }

    // #745 D3 / #752: a caller-supplied reconciled lot_area_m2 (the brief's
    // single lot-area figure, already used by detect) takes precedence so the
    // confirm calculation runs on the SAME figure as every other brief card.
    // Fallback: shoelace on EPSG:3857 rings with Mercator cos²(lat) correction.
    let lot_area_m2: number | null = lotAreaM2;
    if (lot_area_m2 == null && lotGeometry?.rings?.[0]) {
      const ring: [number, number][] = lotGeometry.rings[0];
      let area = 0;
      for (let i = 0; i < ring.length; i++) {
        const [x1, y1] = ring[i];
        const [x2, y2] = ring[(i + 1) % ring.length];
        area += x1 * y2 - x2 * y1;
      }
      const scale = Math.cos((lat as number) * Math.PI / 180);
      lot_area_m2 = (Math.abs(area) / 2) * scale * scale;
    }

    const is_heritage = !!(propData.property?.heritage_status || propData.property?.heritage_overlays?.length);

    // Fire Python confirm + ePlanning history lookup in parallel
    const [pythonSettled, ePlanningSettled] = await Promise.allSettled([
      fetch(`${PYTHON_API}/pipeline/granny-flat/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          detect_id,
          address,
          prop_id,
          lat,
          lng,
          lot_area_m2,
          confirmed_structure_count,
          confirmed_count_source: confirmed_count_source ?? 'unrecorded',
          structure_types: structure_types ?? null,
          samgeo_structure_count: samgeo_structure_count ?? null,
          postcode: postcode ?? null,
          report_id: report_id ?? crypto.randomUUID(),
          is_heritage,
          existing_secondary_dwelling: existing_secondary_dwelling ?? null,
          main_dwelling_area_m2: main_dwelling_area_m2 ?? null,
        }),
        signal: AbortSignal.timeout(30_000),
      }),
      queryEPlanning(lot_description),
    ]);

    if (pythonSettled.status === 'rejected') {
      const msg = pythonSettled.reason instanceof Error ? pythonSettled.reason.message : String(pythonSettled.reason);
      return NextResponse.json({ error: `Confirm failed: ${msg}` }, { status: 502 });
    }

    const pythonResp = pythonSettled.value;
    const ePlanningHistory = ePlanningSettled.status === 'fulfilled'
      ? ePlanningSettled.value
      : { found: false, applications: [], source_note: 'NSW ePlanning Portal unavailable.', error: 'unavailable' as const };

    if (!pythonResp.ok) {
      const text = await pythonResp.text().catch(() => '');
      return NextResponse.json(
        { error: `Confirm error (${pythonResp.status}): ${text}` },
        { status: 502 },
      );
    }

    const result = await pythonResp.json();
    // Attach ePlanning history — never blocks the confirm result
    result.eplanning_history = ePlanningHistory;

    // Send results email. AWAITED: this was fire-and-forget, and on serverless
    // the instance can be frozen at the response 27 lines below, cancelling the
    // in-flight send. This one goes to the CUSTOMER with their report link, so a
    // cancelled send means someone who asked for a result never got told it was
    // ready. Failure is still swallowed - the report is already computed and
    // stored, and is reachable at the URL regardless.
    if (notification_email && process.env.RESEND_API_KEY) {
      const eligible: boolean = result.granny_flat_buildable ?? false;
      const maxArea: number | null = result.max_floor_area_m2 ?? null;
      const rent: number | null = result.estimated_weekly_rent_aud ?? null;
      const reportAddress: string = result.address ?? address ?? '';
      const addressParam = encodeURIComponent(reportAddress);
      const reportUrl = `https://verify.plotdetect.com.au/reports/granny-flat?jobId=${detect_id}&address=${addressParam}`;

      const verdictColor = eligible ? '#0f766e' : '#dc2626';
      const verdictLabel = eligible ? 'Eligible' : 'Not eligible';
      const verdictNote = eligible
        ? `Max floor area: <strong>${maxArea ?? '—'} m²</strong> (CDC pathway)`
        : result.confidence_reason ?? 'Does not meet SEPP Housing 2021 criteria.';

      await getResend()?.emails.send({
        from: 'Can I Build It <info@plotdetect.com.au>',
        to: [notification_email],
        subject: `Your granny flat result — ${reportAddress}`,
        html: `
          <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
            <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your result is in.</p>
            <div style="background: #f9fafb; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px;">
              <p style="margin: 0 0 4px; font-size: 13px; color: #6b7280;">${reportAddress}</p>
              <p style="margin: 0; font-size: 22px; font-weight: 700; color: ${verdictColor};">${verdictLabel}</p>
              <p style="margin: 6px 0 0; font-size: 13px; color: #374151;">${verdictNote}</p>
              ${eligible && rent ? `<p style="margin: 6px 0 0; font-size: 13px; color: #374151;">Est. weekly rent: <strong>$${rent}/wk</strong></p>` : ''}
            </div>
            <a href="${reportUrl}" style="display: inline-block; background: #0f766e; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; margin-bottom: 20px;">
              View full report
            </a>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
            <p style="color: #999; font-size: 12px; margin: 0;">
              Can I Build It? &middot; <a href="https://plotdetect.com.au" style="color: #0d9488;">plotdetect.com.au</a>
            </p>
          </div>
        `,
      }).catch((err: unknown) => {
        console.error('[granny-flat/confirm] Resend error:', err);
      });
    }

    return NextResponse.json(result);
  }

  return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
}

/**
 * GET /api/satellite/granny-flat?jobId=<uuid>
 * Poll granny_flat_reports for detect result or completed report.
 * Returns { status: 'pending' | 'detected' | 'completed' | 'error' }
 */
export async function GET(request: NextRequest) {
  const jobId = request.nextUrl.searchParams.get('jobId');
  if (!jobId) {
    return NextResponse.json({ error: 'jobId is required' }, { status: 400 });
  }

  const { data, error } = await getSupabase()
    .from('granny_flat_reports')
    .select('confidence, outputs, address, lat, lng')
    .eq('id', jobId)
    .single();

  if (error || !data) {
    return NextResponse.json({ status: 'pending' });
  }

  if (data.confidence === 'error') {
    const msg = (data.outputs as { error?: string } | null)?.error ?? 'Detection failed — please try again.';
    return NextResponse.json({ status: 'error', error: msg });
  }

  if (data.confidence === 'pending_confirm' && data.outputs) {
    return NextResponse.json({ status: 'detected', data: data.outputs });
  }

  // Completed report (confidence = high/medium/low) — return final result
  if (data.confidence && data.confidence !== 'pending_confirm' && data.outputs) {
    return NextResponse.json({
      status: 'completed',
      data: {
        report_id: jobId,
        address: data.address,
        lat: data.lat,
        lng: data.lng,
        ...(data.outputs as Record<string, unknown>),
      },
    });
  }

  return NextResponse.json({ status: 'pending' });
}
