import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

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

  const isEligible = result.eligible;
  const accentColor = isEligible ? '#0d9488' : '#dc2626';
  const bgGradientStart = isEligible ? '#0f766e' : '#991b1b';
  const bgGradientEnd = isEligible ? '#134e4a' : '#7f1d1d';
  const verdictLabel = isEligible ? 'YES — CDC Pathway' : 'NO — DA Required';
  const subtitle = isEligible
    ? 'Complying development eligible under SEPP Housing 2021'
    : (result.constraint ?? 'Does not meet SEPP Housing 2021 criteria');

  // Truncate address for display
  const displayAddress = resolvedAddress.length > 50
    ? resolvedAddress.slice(0, 47) + '...'
    : resolvedAddress;

  // Build stats chips
  const stats: string[] = [];
  if (result.lotArea != null) stats.push(`${Math.round(result.lotArea).toLocaleString()} m²`);
  if (result.zone) stats.push(`Zone ${result.zone}`);
  if (result.lga) stats.push(result.lga);

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          fontFamily: 'system-ui, sans-serif',
          background: `linear-gradient(135deg, ${bgGradientStart} 0%, ${bgGradientEnd} 100%)`,
          color: '#ffffff',
        }}
      >
        {/* Top section — branding + question */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            padding: '48px 56px 0',
          }}
        >
          {/* Brand */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '40px' }}>
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                backgroundColor: 'rgba(255,255,255,0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '22px',
                fontWeight: 700,
              }}
            >
              P
            </div>
            <span style={{ fontSize: '26px', fontWeight: 600, opacity: 0.9 }}>
              PlotDetect
            </span>
          </div>

          {/* Question */}
          <span style={{ fontSize: '22px', fontWeight: 400, opacity: 0.7, marginBottom: '8px' }}>
            Can you build a granny flat at
          </span>
          <span style={{ fontSize: '42px', fontWeight: 800, lineHeight: 1.1, marginBottom: '32px' }}>
            {displayAddress}
          </span>
        </div>

        {/* Verdict — the hero */}
        <div
          style={{
            display: 'flex',
            flex: 1,
            alignItems: 'center',
            padding: '0 56px',
          }}
        >
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              backgroundColor: 'rgba(255,255,255,0.15)',
              borderRadius: '20px',
              padding: '32px 40px',
              width: '100%',
              backdropFilter: 'blur(10px)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
              <div
                style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '50%',
                  backgroundColor: isEligible ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '30px',
                  fontWeight: 700,
                }}
              >
                {isEligible ? '✓' : '✗'}
              </div>
              <span style={{ fontSize: '48px', fontWeight: 800, letterSpacing: '-0.02em' }}>
                {verdictLabel}
              </span>
            </div>
            <span style={{ fontSize: '20px', opacity: 0.7, marginLeft: '72px' }}>
              {subtitle}
            </span>
          </div>
        </div>

        {/* Bottom bar — stats + CTA */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '24px 56px 32px',
          }}
        >
          <div style={{ display: 'flex', gap: '16px' }}>
            {stats.map((stat) => (
              <div
                key={stat}
                style={{
                  backgroundColor: 'rgba(255,255,255,0.15)',
                  borderRadius: '8px',
                  padding: '8px 16px',
                  fontSize: '18px',
                  fontWeight: 600,
                }}
              >
                {stat}
              </div>
            ))}
          </div>
          <span style={{ fontSize: '20px', fontWeight: 700, opacity: 0.9 }}>
            plotdetect.com.au
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
