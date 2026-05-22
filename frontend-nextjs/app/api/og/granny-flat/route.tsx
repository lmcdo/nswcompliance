import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

// SIX Maps is in Australia — cross-Pacific from Vercel US takes 10-15s
export const maxDuration = 30;

const ELIGIBLE_ZONE_PREFIXES = ['R1', 'R2', 'R3', 'R4', 'R5', 'RU5'];

const NSW_ZONE_NAMES: Record<string, string> = {
  R1: 'General Residential', R2: 'Low Density Residential',
  R3: 'Medium Density Residential', R4: 'High Density Residential',
  R5: 'Large Lot Residential', RU5: 'Village',
};

// NSW SIX Maps ArcGIS export — no API key, CC-BY 4.0
const SIX_MAPS_EXPORT =
  'https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/export';

interface QuickEligibility {
  eligible: boolean;
  zone: string | null;
  zoneName: string | null;
  lotArea: number | null;
  constraint: string | null;
  lga: string | null;
}

function assess(property: Record<string, unknown>, lotArea: number | null): QuickEligibility {
  const zone = (property.zone as string) ?? null;
  const heritage = !!(property.heritage_status || (property.heritage_overlays as unknown[] | undefined)?.length);
  const lga = (property.lga_name as string) ?? null;

  const zoneCode = zone?.split(' ')[0] ?? null;
  const zoneName = zoneCode ? (NSW_ZONE_NAMES[zoneCode] ?? zone) : null;
  const zoneOk = zoneCode ? ELIGIBLE_ZONE_PREFIXES.some(p => zoneCode.startsWith(p)) : null;
  const areaOk = lotArea != null ? lotArea >= 450 : null;

  let constraint: string | null = null;
  if (zoneOk === false) constraint = `Zone ${zoneCode} not eligible`;
  else if (heritage) constraint = 'Heritage listed — CDC excluded';
  else if (areaOk === false) constraint = `${Math.round(lotArea!)} m² — below 450 m² minimum`;

  const eligible = zoneOk !== false && !heritage && areaOk !== false && zoneOk !== null;
  return { eligible, zone: zoneCode, zoneName, lotArea, constraint, lga };
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
  // Pad 60% around the lot so it's not edge-to-edge
  const padX = (rawMaxLng - rawMinLng) * 0.6;
  const padY = (rawMaxLat - rawMinLat) * 0.6;
  const minLng = rawMinLng - padX;
  const maxLng = rawMaxLng + padX;
  const minLat = rawMinLat - padY;
  const maxLat = rawMaxLat + padY;

  // Fixed tile size for left panel
  const w = 520;
  const h = 630;

  const params = new URLSearchParams({
    bbox: `${minLng.toFixed(6)},${minLat.toFixed(6)},${maxLng.toFixed(6)},${maxLat.toFixed(6)}`,
    bboxSR: '4326',
    imageSR: '4326',
    size: `${w},${h}`,
    format: 'png',
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
    if (buf.byteLength < 3000) return { failReason: `too small: ${buf.byteLength}`, url } as never;
    const b64 = Buffer.from(buf).toString('base64');
    return {
      dataUrl: `data:image/png;base64,${b64}`,
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
    // Step 1: address search
    const addrResp = await fetch(
      `${NSW_PLANNING_API}/address?a=${encodeURIComponent(address)}`,
      { signal: AbortSignal.timeout(5_000) },
    );
    if (!addrResp.ok) return null;
    const addrData = await addrResp.json();
    const propId = addrData?.[0]?.propId;
    const resolved = addrData?.[0]?.address ?? address;
    if (!propId) return null;

    // Step 2: lot geometry
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

export async function GET(request: NextRequest) {
  const address = request.nextUrl.searchParams.get('address');
  if (!address) {
    return new Response('address parameter required', { status: 400 });
  }

  const origin = request.nextUrl.origin;
  let property: Record<string, unknown> = {};
  let lotArea: number | null = null;
  let resolvedAddress = address;
  let lotRings: number[][][] | null = null;

  try {
    const propResp = await fetch(
      `${origin}/api/property/${encodeURIComponent(address)}`,
      { signal: AbortSignal.timeout(8_000) },
    );
    if (propResp.ok) {
      const data = await propResp.json();
      if (data.success && data.property) {
        property = data.property;
        resolvedAddress = (property.address as string) ?? address;
        lotArea = (data.lotDimensions as { area?: number } | undefined)?.area ?? null;
        lotRings = (data.lotGeometry as { rings?: number[][][] } | undefined)?.rings ?? null;
      }
    }
  } catch {
    // Continue — will try NSW API directly for geometry
  }

  // If internal API didn't return lot geometry, fetch directly from NSW Planning API
  if (!lotRings || !lotRings[0]?.length) {
    const nswResult = await fetchLotFromNswApi(address);
    if (nswResult) {
      lotRings = nswResult.rings;
      if (resolvedAddress === address) resolvedAddress = nswResult.resolvedAddress;
    }
  }

  const result = assess(property, lotArea);

  // Convert lot rings from Web Mercator to WGS84
  let coordsWgs84: [number, number][] | null = null;
  if (lotRings && lotRings[0] && lotRings[0].length >= 3) {
    coordsWgs84 = lotRings[0].map(([x, y]) => webMercatorToWgs84(x, y));
  }

  // Debug mode: return JSON diagnostics instead of image
  const debug = request.nextUrl.searchParams.get('debug') === '1';

  // Fetch aerial tile + build polygon
  let tile: Awaited<ReturnType<typeof fetchAerialTile>> = null;
  let polygonSvgPoints = '';

  let tileError: string | null = null;
  let tileDebug: unknown = null;
  if (coordsWgs84) {
    const rawResult = await fetchAerialTile(coordsWgs84);
    if (rawResult && 'dataUrl' in rawResult) {
      tile = rawResult;
    } else {
      tileDebug = rawResult;
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

  if (debug) {
    return Response.json({
      resolvedAddress,
      hasProperty: !!property.zone,
      lotRingsCount: lotRings?.[0]?.length ?? 0,
      coordsWgs84Count: coordsWgs84?.length ?? 0,
      coordsSample: coordsWgs84?.slice(0, 2),
      tileLoaded: !!tile,
      tileError,
      tileDebug,
      result,
    });
  }

  const isEligible = result.eligible;
  const verdictColor = isEligible ? '#10b981' : '#ef4444';
  const verdictBg = isEligible ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';
  const verdictLabel = isEligible ? 'CDC Pathway Available' : 'DA Required';
  const verdictIcon = isEligible ? '\u2713' : '\u2717';

  const displayAddress = resolvedAddress.length > 45
    ? resolvedAddress.slice(0, 42) + '...'
    : resolvedAddress;

  // Stats
  const stats: { label: string; value: string }[] = [];
  if (result.lotArea != null) stats.push({ label: 'Lot Area', value: `${Math.round(result.lotArea).toLocaleString()} m\u00B2` });
  if (result.zone && result.zoneName) stats.push({ label: 'Zone', value: `${result.zone} ${result.zoneName}` });
  else if (result.zone) stats.push({ label: 'Zone', value: result.zone });
  if (result.lga) stats.push({ label: 'Council', value: result.lga });

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
            {/* Lot polygon overlay */}
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
                    fill={isEligible ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.25)'}
                    stroke={verdictColor}
                    stroke-width="3"
                  />
                </svg>
              </div>
            )}
            {/* Attribution */}
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
              padding: '40px 44px',
            }}
          >
            {/* Brand */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  backgroundColor: '#0f766e',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '18px',
                  fontWeight: 700,
                  color: 'white',
                }}
              >
                P
              </div>
              <span style={{ color: '#64748b', fontSize: '15px', letterSpacing: '0.08em', fontWeight: 600 }}>
                PLOTDETECT
              </span>
            </div>

            {/* Address */}
            <div style={{ display: 'flex', flexDirection: 'column', marginTop: '32px' }}>
              <span style={{ color: '#64748b', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '6px' }}>
                Granny Flat Eligibility
              </span>
              <span style={{ color: '#f1f5f9', fontSize: '32px', fontWeight: 700, lineHeight: 1.15 }}>
                {displayAddress}
              </span>
            </div>

            {/* Verdict badge */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                marginTop: '24px',
                backgroundColor: verdictBg,
                border: `2px solid ${verdictColor}`,
                borderRadius: '14px',
                padding: '16px 22px',
              }}
            >
              <span style={{ fontSize: '28px', color: verdictColor, fontWeight: 700 }}>
                {verdictIcon}
              </span>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '24px', fontWeight: 700, color: verdictColor }}>
                  {verdictLabel}
                </span>
                {result.constraint && (
                  <span style={{ fontSize: '14px', color: '#94a3b8', marginTop: '2px' }}>
                    {result.constraint}
                  </span>
                )}
              </div>
            </div>

            {/* Stats */}
            <div style={{ display: 'flex', flexDirection: 'column', marginTop: '24px', gap: '12px' }}>
              {stats.map((stat) => (
                <div key={stat.label} style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ color: '#64748b', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    {stat.label}
                  </span>
                  <span style={{ color: '#e2e8f0', fontSize: '20px', fontWeight: 600 }}>
                    {stat.value}
                  </span>
                </div>
              ))}
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
              <span style={{ color: '#0d9488', fontSize: '16px', fontWeight: 700 }}>
                Check your address free
              </span>
              <span style={{ color: '#475569', fontSize: '14px' }}>
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
          <span style={{ fontSize: '36px', fontWeight: 700 }}>{verdictIcon}</span>
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
            {stats.map((stat) => (
              <div
                key={stat.label}
                style={{
                  backgroundColor: 'rgba(255,255,255,0.15)',
                  borderRadius: '8px',
                  padding: '8px 16px',
                  fontSize: '16px',
                  fontWeight: 600,
                }}
              >
                {stat.value}
              </div>
            ))}
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
