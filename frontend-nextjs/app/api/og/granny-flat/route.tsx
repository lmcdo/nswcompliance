import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

const ELIGIBLE_ZONE_PREFIXES = ['R1', 'R2', 'R3', 'R4', 'R5', 'RU5'];

const NSW_ZONE_NAMES: Record<string, string> = {
  R1: 'General Residential', R2: 'Low Density Residential',
  R3: 'Medium Density Residential', R4: 'High Density Residential',
  R5: 'Large Lot Residential', RU5: 'Village',
};

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

  // Determine constraint
  let constraint: string | null = null;
  if (zoneOk === false) constraint = `Zone ${zoneCode} is not eligible`;
  else if (heritage) constraint = 'Heritage listed — CDC excluded';
  else if (areaOk === false) constraint = `Lot ${Math.round(lotArea!)} m² — below 450 m² minimum`;

  const eligible = zoneOk !== false && !heritage && areaOk !== false && zoneOk !== null;

  return { eligible, zone: zoneCode, zoneName, lotArea, constraint, lga };
}

export async function GET(request: NextRequest) {
  const address = request.nextUrl.searchParams.get('address');
  if (!address) {
    return new Response('address parameter required', { status: 400 });
  }

  // Fetch property data from internal API
  const origin = request.nextUrl.origin;
  let property: Record<string, unknown> = {};
  let lotArea: number | null = null;
  let resolvedAddress = address;

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
      }
    }
  } catch {
    // Render fallback card if API fails
  }

  const result = assess(property, lotArea);

  const verdictColor = result.eligible ? '#0f766e' : '#dc2626';
  const verdictBg = result.eligible ? '#f0fdfa' : '#fef2f2';
  const verdictLabel = result.eligible ? 'CDC Pathway Available' : 'DA Required';
  const verdictIcon = result.eligible ? '✓' : '✗';

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#ffffff',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        {/* Top bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '28px 48px 20px',
            borderBottom: '1px solid #e5e7eb',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: '#0f766e',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
                fontSize: '18px',
                fontWeight: 700,
              }}
            >
              P
            </div>
            <span style={{ fontSize: '22px', fontWeight: 600, color: '#111827' }}>
              PlotDetect
            </span>
          </div>
          <span style={{ fontSize: '16px', color: '#9ca3af', fontWeight: 500 }}>
            Granny Flat Eligibility
          </span>
        </div>

        {/* Main content */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            padding: '36px 48px',
            gap: '24px',
          }}
        >
          {/* Address */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '14px', color: '#6b7280', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Property
            </span>
            <span style={{ fontSize: '30px', fontWeight: 700, color: '#111827', lineHeight: 1.2 }}>
              {resolvedAddress.length > 60 ? resolvedAddress.slice(0, 57) + '...' : resolvedAddress}
            </span>
          </div>

          {/* Verdict badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              backgroundColor: verdictBg,
              border: `2px solid ${verdictColor}`,
              borderRadius: '12px',
              padding: '16px 24px',
            }}
          >
            <span style={{ fontSize: '32px', color: verdictColor, fontWeight: 700 }}>
              {verdictIcon}
            </span>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '26px', fontWeight: 700, color: verdictColor }}>
                {verdictLabel}
              </span>
              {result.constraint && (
                <span style={{ fontSize: '16px', color: '#6b7280', marginTop: '2px' }}>
                  {result.constraint}
                </span>
              )}
            </div>
          </div>

          {/* Stats row */}
          <div style={{ display: 'flex', gap: '24px' }}>
            {result.lotArea != null && (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  backgroundColor: '#f9fafb',
                  borderRadius: '8px',
                  padding: '14px 20px',
                  minWidth: '160px',
                }}
              >
                <span style={{ fontSize: '13px', color: '#9ca3af', fontWeight: 500 }}>Lot Area</span>
                <span style={{ fontSize: '22px', fontWeight: 700, color: '#111827' }}>
                  {Math.round(result.lotArea).toLocaleString()} m²
                </span>
              </div>
            )}
            {result.zoneName && (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  backgroundColor: '#f9fafb',
                  borderRadius: '8px',
                  padding: '14px 20px',
                  minWidth: '160px',
                }}
              >
                <span style={{ fontSize: '13px', color: '#9ca3af', fontWeight: 500 }}>Zone</span>
                <span style={{ fontSize: '22px', fontWeight: 700, color: '#111827' }}>
                  {result.zone}
                </span>
                <span style={{ fontSize: '14px', color: '#6b7280' }}>{result.zoneName}</span>
              </div>
            )}
            {result.lga && (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  backgroundColor: '#f9fafb',
                  borderRadius: '8px',
                  padding: '14px 20px',
                  minWidth: '160px',
                }}
              >
                <span style={{ fontSize: '13px', color: '#9ca3af', fontWeight: 500 }}>Council</span>
                <span style={{ fontSize: '22px', fontWeight: 700, color: '#111827' }}>
                  {(result.lga.length > 20 ? result.lga.slice(0, 18) + '...' : result.lga)}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Bottom CTA bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '20px 48px',
            backgroundColor: '#f9fafb',
            borderTop: '1px solid #e5e7eb',
          }}
        >
          <span style={{ fontSize: '18px', fontWeight: 600, color: '#0f766e' }}>
            Check your address free →  plotdetect.com.au/granny-flat
          </span>
          <span style={{ fontSize: '14px', color: '#9ca3af' }}>
            SEPP Housing 2021
          </span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    },
  );
}
