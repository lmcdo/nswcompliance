import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';
import { NSW_STANDARD_ZONES } from '@/lib/regulatory-constants';

// SIX Maps is in Australia — cross-Pacific from Vercel US takes 10-15s
export const maxDuration = 30;

// DQ-30 (.claude/DATA_QUALITY_TRACKER.md): consolidated onto
// NSW_STANDARD_ZONES.RESIDENTIAL — was independently declared in 4 files.
const ELIGIBLE_ZONE_PREFIXES = NSW_STANDARD_ZONES.RESIDENTIAL as readonly string[];

const NSW_ZONE_NAMES: Record<string, string> = {
  R1: 'General Residential', R2: 'Low Density Residential',
  R3: 'Medium Density Residential', R4: 'High Density Residential',
  R5: 'Large Lot Residential', RU5: 'Village',
};

// NSW SIX Maps ArcGIS export — no API key, CC-BY 4.0
const SIX_MAPS_EXPORT =
  'https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/export';

interface PropertyDetails {
  eligible: boolean;
  zone: string | null;
  zoneName: string | null;
  lotArea: number | null;
  frontage: number | null;
  depth: number | null;
  heightLimit: number | null;
  heritage: boolean;
  constraint: string | null;
  lga: string | null;
}

function assess(
  property: Record<string, unknown>,
  lotArea: number | null,
  frontage: number | null,
  depth: number | null,
): PropertyDetails {
  const zone = (property.zone as string) ?? null;
  const heritage = !!(property.heritage_status || (property.heritage_overlays as unknown[] | undefined)?.length);
  const lga = (property.lga_name as string) ?? null;
  const heightLimit = (property.height_limit as number) ?? null;

  const zoneCode = zone?.split(' ')[0] ?? null;
  const zoneName = zoneCode ? (NSW_ZONE_NAMES[zoneCode] ?? zone) : null;
  const zoneOk = zoneCode ? ELIGIBLE_ZONE_PREFIXES.some(p => zoneCode.startsWith(p)) : null;
  const areaOk = lotArea != null ? lotArea >= 450 : null;

  let constraint: string | null = null;
  if (zoneOk === false) constraint = `Zone ${zoneCode} not eligible`;
  else if (heritage) constraint = 'Heritage listed — CDC excluded';
  else if (areaOk === false) constraint = `${Math.round(lotArea!)} m² — below 450 m² minimum`;

  const eligible = zoneOk !== false && !heritage && areaOk !== false && zoneOk !== null;
  return { eligible, zone: zoneCode, zoneName, lotArea, frontage, depth, heightLimit, heritage, constraint, lga };
}

/** Convert Web Mercator (EPSG:3857) to WGS84 (EPSG:4326) */
function webMercatorToWgs84(x: number, y: number): [number, number] {
  const lng = (x / 20037508.34) * 180;
  let lat = (y / 20037508.34) * 180;
  lat = (180 / Math.PI) * (2 * Math.atan(Math.exp((lat * Math.PI) / 180)) - Math.PI / 2);
  return [lng, lat];
}

/** Fetch aerial tile from NSW SIX Maps */
async function fetchAerialTile(
  coordsWgs84: [number, number][],
): Promise<{ dataUrl: string; bbox: { minLng: number; maxLng: number; minLat: number; maxLat: number }; w: number; h: number } | null> {
  const lngs = coordsWgs84.map(c => c[0]);
  const lats = coordsWgs84.map(c => c[1]);
  const rawMinLng = Math.min(...lngs);
  const rawMaxLng = Math.max(...lngs);
  const rawMinLat = Math.min(...lats);
  const rawMaxLat = Math.max(...lats);
  // Tight pad (25%) — keeps lot prominent, reduces building perspective distortion
  const padX = (rawMaxLng - rawMinLng) * 0.25;
  const padY = (rawMaxLat - rawMinLat) * 0.25;
  const minLng = rawMinLng - padX;
  const maxLng = rawMaxLng + padX;
  const minLat = rawMinLat - padY;
  const maxLat = rawMaxLat + padY;

  // Fixed tile size for left panel — jpeg for faster cross-Pacific transfer
  const w = 520;
  const h = 630;

  const params = new URLSearchParams({
    bbox: `${minLng.toFixed(6)},${minLat.toFixed(6)},${maxLng.toFixed(6)},${maxLat.toFixed(6)}`,
    bboxSR: '4326',
    imageSR: '4326',
    size: `${w},${h}`,
    format: 'jpg',
    f: 'image',
  });

  const url = `${SIX_MAPS_EXPORT}?${params}`;
  try {
    const res = await fetch(url, {
      signal: AbortSignal.timeout(20_000),
    });
    if (!res.ok) return { failReason: `http ${res.status}`, url } as never;
    const ct = res.headers.get('content-type') ?? '';
    if (!ct.includes('image')) return { failReason: `content-type: ${ct}`, url } as never;
    const buf = await res.arrayBuffer();
    if (buf.byteLength < 1000) return { failReason: `too small: ${buf.byteLength}`, url } as never;
    const mime = ct.includes('jpeg') || ct.includes('jpg') ? 'image/jpeg' : 'image/png';
    const b64 = Buffer.from(buf).toString('base64');
    return {
      dataUrl: `data:${mime};base64,${b64}`,
      bbox: { minLng, maxLng, minLat, maxLat },
      w,
      h,
    };
  } catch (e) {
    return { failReason: `exception: ${e instanceof Error ? e.message : String(e)}`, url } as never;
  }
}

/** Convert WGS84 coord to pixel position within tile */
function geoToPixel(
  coord: [number, number],
  minLng: number,
  maxLat: number,
  scaleX: number,
  scaleY: number,
): [number, number] {
  return [
    (coord[0] - minLng) * scaleX,
    (maxLat - coord[1]) * scaleY,
  ];
}

const NSW_PLANNING_API = 'https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi';

/** Resolve address → propId → lot geometry via NSW Planning Portal */
async function fetchLotFromNswApi(address: string): Promise<{
  resolvedAddress: string;
  rings: number[][][];
} | null> {
  try {
    const addrResp = await fetch(
      `${NSW_PLANNING_API}/address?a=${encodeURIComponent(address)}`,
      { signal: AbortSignal.timeout(5_000) },
    );
    if (!addrResp.ok) return null;
    const addrData = await addrResp.json();
    const propId = addrData?.[0]?.propId;
    const resolved = addrData?.[0]?.address ?? address;
    if (!propId) return null;

    const lotResp = await fetch(
      `${NSW_PLANNING_API}/lot?propId=${propId}`,
      { signal: AbortSignal.timeout(5_000) },
    );
    if (!lotResp.ok) return null;
    const lotData = await lotResp.json();
    const geometry = lotData?.[0]?.geometry;
    if (!geometry?.rings?.[0]?.length) return null;

    return { resolvedAddress: resolved, rings: geometry.rings };
  } catch {
    return null;
  }
}

/** Compact check-row for the OG card */
function CheckRow({ label, status }: { label: string; status: 'pass' | 'fail' | 'unknown' }) {
  const color = status === 'pass' ? '#10b981' : status === 'fail' ? '#ef4444' : '#64748b';
  const bg = status === 'pass' ? 'rgba(16,185,129,0.2)' : status === 'fail' ? 'rgba(239,68,68,0.2)' : 'rgba(100,116,139,0.2)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{
        width: '16px', height: '16px', borderRadius: '50%',
        backgroundColor: bg, border: `1.5px solid ${color}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }} />
      <span style={{ fontSize: '13px', color: status === 'fail' ? '#fca5a5' : '#cbd5e1' }}>{label}</span>
    </div>
  );
}

export async function GET(request: NextRequest) {
  const address = request.nextUrl.searchParams.get('address');
  if (!address) {
    return new Response('address parameter required', { status: 400 });
  }

  const origin = request.nextUrl.origin;

  // Fetch property data (zone/area) and lot geometry in parallel
  const [propData, nswLot] = await Promise.all([
    (async () => {
      try {
        const resp = await fetch(
          `${origin}/api/property/${encodeURIComponent(address)}`,
          { signal: AbortSignal.timeout(8_000) },
        );
        if (!resp.ok) return null;
        const data = await resp.json();
        if (!data.success || !data.property) return null;
        return {
          property: data.property as Record<string, unknown>,
          lotArea: (data.lotDimensions as { area?: number } | undefined)?.area ?? null,
          frontage: (data.lotDimensions as { frontage?: number } | undefined)?.frontage ?? null,
          depth: (data.lotDimensions as { depth?: number } | undefined)?.depth ?? null,
          lotRings: (data.lotGeometry as { rings?: number[][][] } | undefined)?.rings ?? null,
        };
      } catch { return null; }
    })(),
    fetchLotFromNswApi(address),
  ]);

  const property = propData?.property ?? {};
  const lotArea = propData?.lotArea ?? null;
  const frontage = propData?.frontage ?? null;
  const depth = propData?.depth ?? null;
  const resolvedAddress = (property.address as string) ?? nswLot?.resolvedAddress ?? address;
  const lotRings = (propData?.lotRings?.[0]?.length ? propData.lotRings : null)
    ?? nswLot?.rings ?? null;

  const result = assess(property, lotArea, frontage, depth);

  // Convert lot rings from Web Mercator to WGS84
  let coordsWgs84: [number, number][] | null = null;
  if (lotRings && lotRings[0] && lotRings[0].length >= 3) {
    coordsWgs84 = lotRings[0].map(([x, y]) => webMercatorToWgs84(x, y));
  }

  // Fetch aerial tile + build polygon
  let tile: Awaited<ReturnType<typeof fetchAerialTile>> = null;
  let polygonSvgPoints = '';
  if (coordsWgs84) {
    const rawResult = await fetchAerialTile(coordsWgs84);
    if (rawResult && 'dataUrl' in rawResult) {
      tile = rawResult;
    }
    if (tile) {
      const { bbox, w, h } = tile;
      const scaleX = w / (bbox.maxLng - bbox.minLng);
      const scaleY = h / (bbox.maxLat - bbox.minLat);
      polygonSvgPoints = coordsWgs84
        .map(c => geoToPixel(c, bbox.minLng, bbox.maxLat, scaleX, scaleY))
        .map(([x, y]) => `${x.toFixed(0)},${y.toFixed(0)}`)
        .join(' ');
    }
  }

  const isEligible = result.eligible;
  const verdictColor = isEligible ? '#10b981' : '#ef4444';
  const verdictBg = isEligible ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';
  const verdictLabel = isEligible ? 'CDC Pathway Available' : 'DA Required';
  const displayAddress = resolvedAddress.length > 45
    ? resolvedAddress.slice(0, 42) + '...'
    : resolvedAddress;

  // Zone eligibility check status
  const zoneCode = result.zone;
  const zoneStatus: 'pass' | 'fail' | 'unknown' = zoneCode
    ? (ELIGIBLE_ZONE_PREFIXES.some(p => zoneCode.startsWith(p)) ? 'pass' : 'fail')
    : 'unknown';
  const areaStatus: 'pass' | 'fail' | 'unknown' = result.lotArea != null
    ? (result.lotArea >= 450 ? 'pass' : 'fail')
    : 'unknown';
  const heritageStatus: 'pass' | 'fail' | 'unknown' = result.heritage ? 'fail' : 'pass';

  // ── Card WITH aerial image ──
  if (tile) {
    return new ImageResponse(
      (
        <div
          style={{
            width: '1200px',
            height: '630px',
            display: 'flex',
            flexDirection: 'row',
            backgroundColor: '#0f172a',
            fontFamily: 'system-ui, sans-serif',
          }}
        >
          {/* Left: aerial tile with lot outline */}
          <div style={{ display: 'flex', width: '520px', height: '630px', position: 'relative', flexShrink: 0 }}>
            <img
              src={tile.dataUrl}
              width={520}
              height={630}
              style={{ width: '520px', height: '630px', objectFit: 'cover' }}
            />
            {polygonSvgPoints && (
              <div style={{ position: 'absolute', top: 0, left: 0, width: '520px', height: '630px', display: 'flex' }}>
                <svg
                  viewBox={`0 0 ${tile.w} ${tile.h}`}
                  width="520"
                  height="630"
                  style={{ width: '520px', height: '630px' }}
                >
                  <polygon
                    points={polygonSvgPoints}
                    fill={isEligible ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}
                    stroke={verdictColor}
                    stroke-width="3"
                  />
                </svg>
              </div>
            )}
            <div style={{
              position: 'absolute',
              bottom: '8px',
              left: '8px',
              display: 'flex',
              backgroundColor: 'rgba(0,0,0,0.6)',
              borderRadius: '4px',
              padding: '3px 8px',
            }}>
              <span style={{ fontSize: '10px', color: '#94a3b8' }}>NSW Spatial Services CC-BY 4.0</span>
            </div>
          </div>

          {/* Right: text content */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              flex: 1,
              padding: '32px 40px',
            }}
          >
            {/* Brand */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  backgroundColor: '#0f766e',
                  borderRadius: '7px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '16px',
                  fontWeight: 700,
                  color: 'white',
                }}
              >
                P
              </div>
              <span style={{ color: '#64748b', fontSize: '14px', letterSpacing: '0.08em', fontWeight: 600 }}>
                PLOTDETECT
              </span>
            </div>

            {/* Address */}
            <div style={{ display: 'flex', flexDirection: 'column', marginTop: '20px' }}>
              <span style={{ color: '#64748b', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}>
                Granny Flat Eligibility
              </span>
              <span style={{ color: '#f1f5f9', fontSize: '28px', fontWeight: 700, lineHeight: 1.15 }}>
                {displayAddress}
              </span>
            </div>

            {/* Verdict badge */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                marginTop: '18px',
                backgroundColor: verdictBg,
                border: `2px solid ${verdictColor}`,
                borderRadius: '12px',
                padding: '14px 20px',
              }}
            >
              <div style={{
                width: '28px', height: '28px', borderRadius: '50%',
                backgroundColor: verdictColor, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }} />
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '22px', fontWeight: 700, color: verdictColor }}>
                  {verdictLabel}
                </span>
                {result.constraint && (
                  <span style={{ fontSize: '13px', color: '#94a3b8', marginTop: '2px' }}>
                    {result.constraint}
                  </span>
                )}
              </div>
            </div>

            {/* Property details grid */}
            <div style={{ display: 'flex', gap: '24px', marginTop: '18px' }}>
              {/* Left column: lot stats */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
                {result.lotArea != null && (
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: '#64748b', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                      Lot Area
                    </span>
                    <span style={{ color: '#e2e8f0', fontSize: '18px', fontWeight: 600 }}>
                      {Math.round(result.lotArea).toLocaleString()} m{'\u00B2'}
                    </span>
                  </div>
                )}
                {result.frontage != null && result.depth != null && (
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: '#64748b', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                      Dimensions
                    </span>
                    <span style={{ color: '#e2e8f0', fontSize: '18px', fontWeight: 600 }}>
                      {result.frontage.toFixed(1)}m × {result.depth.toFixed(1)}m
                    </span>
                  </div>
                )}
                {result.zone && (
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: '#64748b', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                      Zone
                    </span>
                    <span style={{ color: '#e2e8f0', fontSize: '16px', fontWeight: 600 }}>
                      {result.zone} {result.zoneName}
                    </span>
                  </div>
                )}
                {result.heightLimit != null && (
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: '#64748b', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                      Height Limit
                    </span>
                    <span style={{ color: '#e2e8f0', fontSize: '16px', fontWeight: 600 }}>
                      {result.heightLimit}m
                    </span>
                  </div>
                )}
              </div>

              {/* Right column: SEPP checks */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '200px' }}>
                <span style={{ color: '#64748b', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '2px' }}>
                  SEPP Housing Checks
                </span>
                <CheckRow label={`Lot area ${result.lotArea != null ? `(${Math.round(result.lotArea).toLocaleString()} m\u00B2)` : ''}`} status={areaStatus} />
                <CheckRow label={`Zoning ${result.zone ? `(${result.zone})` : ''}`} status={zoneStatus} />
                <CheckRow label="Heritage exclusion" status={heritageStatus} />
              </div>
            </div>

            {/* Footer CTA */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginTop: 'auto',
              }}
            >
              <span style={{ color: '#0d9488', fontSize: '15px', fontWeight: 700 }}>
                Check your address free →
              </span>
              <span style={{ color: '#475569', fontSize: '13px' }}>
                plotdetect.com.au
              </span>
            </div>
          </div>
        </div>
      ),
      {
        width: 1200,
        height: 630,
        headers: { 'Cache-Control': 'public, max-age=86400, s-maxage=604800, stale-while-revalidate=86400' },
      },
    );
  }

  // ── Fallback card (no aerial) — gradient design ──
  const bgStart = isEligible ? '#0f766e' : '#991b1b';
  const bgEnd = isEligible ? '#134e4a' : '#7f1d1d';

  return new ImageResponse(
    (
      <div
        style={{
          width: '1200px',
          height: '630px',
          display: 'flex',
          flexDirection: 'column',
          fontFamily: 'system-ui, sans-serif',
          background: `linear-gradient(135deg, ${bgStart} 0%, ${bgEnd} 100%)`,
          color: '#ffffff',
          padding: '48px 56px',
        }}
      >
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: 'rgba(255,255,255,0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px',
              fontWeight: 700,
            }}
          >
            P
          </div>
          <span style={{ fontSize: '22px', fontWeight: 600, opacity: 0.9 }}>PlotDetect</span>
        </div>

        {/* Question + address */}
        <div style={{ display: 'flex', flexDirection: 'column', marginTop: '40px' }}>
          <span style={{ fontSize: '22px', opacity: 0.7 }}>Can you build a granny flat at</span>
          <span style={{ fontSize: '44px', fontWeight: 800, lineHeight: 1.1, marginTop: '8px' }}>
            {displayAddress}
          </span>
        </div>

        {/* Verdict */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            marginTop: '32px',
            backgroundColor: 'rgba(255,255,255,0.15)',
            borderRadius: '16px',
            padding: '24px 32px',
          }}
        >
          <div style={{
            width: '36px', height: '36px', borderRadius: '50%',
            backgroundColor: verdictColor, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }} />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '36px', fontWeight: 800 }}>{verdictLabel}</span>
            {result.constraint && (
              <span style={{ fontSize: '18px', opacity: 0.7, marginTop: '4px' }}>{result.constraint}</span>
            )}
          </div>
        </div>

        {/* Stats + CTA */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'auto' }}>
          <div style={{ display: 'flex', gap: '16px' }}>
            {result.lotArea != null && (
              <div style={{ backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: '8px', padding: '8px 16px', fontSize: '16px', fontWeight: 600 }}>
                {Math.round(result.lotArea).toLocaleString()} m{'\u00B2'}
              </div>
            )}
            {result.zone && (
              <div style={{ backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: '8px', padding: '8px 16px', fontSize: '16px', fontWeight: 600 }}>
                Zone {result.zone}
              </div>
            )}
            {result.frontage != null && result.depth != null && (
              <div style={{ backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: '8px', padding: '8px 16px', fontSize: '16px', fontWeight: 600 }}>
                {result.frontage.toFixed(1)}m × {result.depth.toFixed(1)}m
              </div>
            )}
          </div>
          <span style={{ fontSize: '18px', fontWeight: 700, opacity: 0.9 }}>plotdetect.com.au</span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
      headers: { 'Cache-Control': 'public, max-age=86400, s-maxage=604800, stale-while-revalidate=86400' },
    },
  );
}
