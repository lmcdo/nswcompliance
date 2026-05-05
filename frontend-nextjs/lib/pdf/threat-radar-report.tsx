/**
 * Threat Radar Report PDF
 * Generated server-side via @react-pdf/renderer renderToBuffer().
 * Data passed directly from the threat-radar search response — no DB lookup.
 */

import React from 'react';
import {
  Document,
  Page,
  View,
  Text,
  StyleSheet,
  Image,
  Svg,
  Circle,
} from '@react-pdf/renderer';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ThreatRadarApplication {
  PlanningPortalApplicationNumber?: string;
  ApplicationType?: string;
  DevelopmentType?: string;
  ApplicationDescription?: string;
  LodgementDate?: string;
  DeterminationDate?: string;
  Status?: string;
  PropertyAddress?: string;
  CostOfDevelopment?: number | string;
  NumberOfNewDwellings?: number | string;
  CouncilName?: string;
  ApplicantName?: string;
  _distance_m?: number | null;
  Latitude?: string | number;
  Longitude?: string | number;
  NumberOfStoreys?: number | string | null;
  DemolitionDwellings?: number | string | null;
  SubdivisionProposedFlag?: string | null;
  EpiVariationProposedFlag?: string | null;
  AccompaniedByVpaFlag?: string | null;
  DevelopmentSubjectToSicFlag?: string | null;
  DevelopmentCategory?: string | null;
}

export interface ThreatRadarReportData {
  address: string;
  run_date: string;
  lat: number;
  lng: number;
  logo_b64?: string | null;
  council_name: string | null;
  applications: ThreatRadarApplication[];
  window_days: number;
  radius_m?: number;
  is_paid?: boolean;
  tile_b64: string | null;
}

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

const TEAL       = '#0f766e';
const AMBER      = '#d97706';
const AMBER_LIGHT = '#fffbeb';
const GRAY_900   = '#111827';
const GRAY_700   = '#374151';
const GRAY_500   = '#6b7280';
const GRAY_300   = '#d1d5db';
const GRAY_100   = '#f3f4f6';
const WHITE      = '#ffffff';

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const s = StyleSheet.create({
  page: {
    fontFamily: 'Helvetica',
    fontSize: 9,
    color: GRAY_900,
    paddingTop: 48,
    paddingBottom: 56,
    paddingHorizontal: 48,
    lineHeight: 1.4,
  },
  logo:      { fontSize: 11, fontFamily: 'Helvetica-Bold', color: TEAL },
  logoRow:   { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 64 },
  logoImg:   { width: 18, height: 18 },
  h1:        { fontSize: 22, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 8 },
  subhead:   { fontSize: 12, color: GRAY_700, marginBottom: 4 },
  dateText:  { fontSize: 9, color: GRAY_500, marginBottom: 32 },
  sectionTitle: {
    fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_500,
    textTransform: 'uppercase', letterSpacing: 0.8,
    marginTop: 20, marginBottom: 8,
  },
  divider: { borderBottom: `1 solid ${GRAY_300}`, marginVertical: 14 },
  bodyText: { fontSize: 8.5, color: GRAY_700, lineHeight: 1.5, marginBottom: 6 },
  // Summary stat
  statBlock: {
    backgroundColor: GRAY_100, borderRadius: 4,
    paddingVertical: 12, paddingHorizontal: 16,
    marginBottom: 20,
  },
  statNumber: { fontSize: 28, fontFamily: 'Helvetica-Bold', color: TEAL },
  statLabel:  { fontSize: 9, color: GRAY_700, marginTop: 2 },
  // Application cards
  appCard: {
    borderBottom: `1 solid ${GRAY_300}`,
    paddingVertical: 10,
  },
  appHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 3 },
  appNum:    { fontSize: 9, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  appType:   { fontSize: 8, color: TEAL, fontFamily: 'Helvetica-Bold' },
  distBadge: {
    fontSize: 7, backgroundColor: AMBER_LIGHT, color: AMBER,
    paddingVertical: 1, paddingHorizontal: 5, borderRadius: 10,
  },
  appDesc:   { fontSize: 8.5, color: GRAY_700, marginBottom: 3 },
  appMeta:   { fontSize: 7.5, color: GRAY_500 },
  footer: {
    position: 'absolute', bottom: 28, left: 48, right: 48,
    flexDirection: 'row', justifyContent: 'space-between',
  },
  footerText: { fontSize: 7, color: GRAY_500 },
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso?: string) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString('en-AU', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

function formatCost(val?: number | string) {
  if (val == null || val === '' || val === 0) return null;
  const n = typeof val === 'string' ? parseFloat(val) : val;
  if (!n || isNaN(n)) return null;
  return new Intl.NumberFormat('en-AU', {
    style: 'currency', currency: 'AUD', maximumFractionDigits: 0,
  }).format(n);
}

// ---------------------------------------------------------------------------
// Paid analytical helpers
// ---------------------------------------------------------------------------

function calcPressureScore(apps: ThreatRadarApplication[]): number {
  if (apps.length === 0) return 0;
  let total = 0;
  for (const app of apps) {
    const base = (app._distance_m ?? 999) < 100 ? 3 : (app._distance_m ?? 999) < 250 ? 2 : 1;
    const dw = Number(app.NumberOfNewDwellings ?? 0);
    const scale = dw >= 10 ? 2 : dw >= 4 ? 1.5 : 1;
    total += base * scale;
  }
  return Math.min(10, Math.max(1, Math.round(total)));
}

function pressureLabel(score: number): string {
  if (score >= 8) return 'high';
  if (score >= 5) return 'elevated';
  if (score >= 3) return 'moderate';
  return 'low';
}

function estimateConstructionWindow(app: ThreatRadarApplication): string | null {
  const status = (app.Status ?? '').toLowerCase();
  const now = new Date();

  if (status.includes('approved') || status.includes('determined')) {
    const det = app.DeterminationDate ? new Date(app.DeterminationDate) : now;
    const startYear = det.getFullYear() + Math.floor((det.getMonth() + 6) / 12);
    const endYear = det.getFullYear() + Math.floor((det.getMonth() + 12) / 12);
    return `Construction likely ${startYear}–${endYear} (6–12 months post-approval typical).`;
  }
  if (status.includes('under assessment') || status.includes('assessment')) {
    const approvalYear = now.getFullYear() + (now.getMonth() >= 8 ? 1 : 0);
    const buildStart = approvalYear + 1;
    const buildEnd = buildStart + 1;
    return `If approved mid-${approvalYear}, construction likely ${buildStart}–${buildEnd} (12–18 month typical build). Noise and access impacts possible.`;
  }
  return null;
}

function LogoRow({ logo_b64 }: { logo_b64?: string | null }) {
  return (
    <View style={s.logoRow}>
      {logo_b64 ? (
        <Image src={`data:image/png;base64,${logo_b64}`} style={s.logoImg} />
      ) : null}
      <Text style={s.logo}>PlotDetect</Text>
    </View>
  );
}

function ValidityNote({ runDate }: { runDate: string }) {
  return (
    <Text style={{ fontSize: 7.5, color: GRAY_500, marginTop: 6, fontStyle: 'italic' }}>
      {'DA data sourced from NSW ePlanning Portal and reflects applications as at ' + runDate + '. Re-run before making an offer to capture recent lodgements.'}
    </Text>
  );
}

function ReferralBox() {
  return (
    <View style={{ backgroundColor: '#f0fdfa', borderRadius: 4, padding: 10, marginTop: 16, borderWidth: 1, borderColor: '#99f6e4' }}>
      <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
        Get professional advice
      </Text>
      <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
        A buyers agent can advise on negotiating price adjustments based on nearby development risk. A town planner can assess whether the DAs, if approved, would generate third-party appeal rights or materially affect amenity.
      </Text>
    </View>
  );
}

function Footer({ pageNum, total }: { pageNum: number; total: number }) {
  return (
    <View style={s.footer} fixed>
      <Text style={s.footerText}>Neighbour Development Threat Radar — plotdetect.com.au</Text>
      <Text style={s.footerText}>{pageNum} / {total}</Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// AerialWithMarkers — aerial tile with SVG overlay for property + DA markers
// ---------------------------------------------------------------------------

// Tile uses 'property' zoom preset: d_lng=0.0005, d_lat=0.0005, 512x512px
const TILE_D_LNG = 0.0005;
const TILE_D_LAT = 0.0005;
const TILE_PX = 512;

function AerialWithMarkers({
  tile_b64,
  lat,
  lng,
  applications,
}: {
  tile_b64: string;
  lat: number;
  lng: number;
  applications: ThreatRadarApplication[];
}) {
  const toX = (appLng: number) => ((appLng - (lng - TILE_D_LNG)) / (2 * TILE_D_LNG)) * TILE_PX;
  const toY = (appLat: number) => ((lat + TILE_D_LAT - appLat) / (2 * TILE_D_LAT)) * TILE_PX;

  // Filter apps with valid coords that fall within tile bbox
  const visibleApps = applications.filter((a) => {
    const aLat = Number(a.Latitude);
    const aLng = Number(a.Longitude);
    if (!aLat || !aLng) return false;
    return (
      aLat >= lat - TILE_D_LAT && aLat <= lat + TILE_D_LAT &&
      aLng >= lng - TILE_D_LNG && aLng <= lng + TILE_D_LNG
    );
  });

  return (
    <View style={{ position: 'relative', width: '100%' }}>
      <Image
        src={`data:image/png;base64,${tile_b64}`}
        style={{ width: '100%', borderRadius: 4 }}
      />
      <Svg viewBox={`0 0 ${TILE_PX} ${TILE_PX}`} style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}>
        {/* DA/CDC markers */}
        {visibleApps.map((app, i) => {
          const x = toX(Number(app.Longitude));
          const y = toY(Number(app.Latitude));
          const isDA = app.ApplicationType === 'DA';
          return (
            <Circle
              key={i}
              cx={String(x)}
              cy={String(y)}
              r="8"
              fill={isDA ? '#f59e0b' : '#a855f7'}
              opacity="0.85"
              stroke="white"
              strokeWidth="2"
            />
          );
        })}
        {/* Property center marker — teal dot with white border */}
        <Circle cx={String(TILE_PX / 2)} cy={String(TILE_PX / 2)} r="10" fill="#0d9488" stroke="white" strokeWidth="3" />
      </Svg>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function ThreatRadarReportDocument({ data }: { data: ThreatRadarReportData }) {
  const apps = data.applications ?? [];
  const radius = data.radius_m ?? 500;
  const totalPages = data.tile_b64 ? 2 : 1;
  // Split: first ~12 cards per page (approx — react-pdf handles wrapping)

  return (
    <Document title={`Threat Radar Report — ${data.address}`} author="PlotDetect">

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + Applications                                         */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />
        <Text style={s.h1}>Neighbour Development Threat Radar</Text>
        <Text style={s.subhead}>{data.address}</Text>
        <Text style={s.dateText}>
          {data.council_name ?? 'NSW'} · last {data.window_days} days · within {radius} m
        </Text>
        <ValidityNote runDate={data.run_date} />

        {/* Summary stat — row layout avoids react-pdf large-font line-height bug */}
        <View style={[s.statBlock, { flexDirection: 'row', alignItems: 'center', gap: 16 }]}>
          <Text style={s.statNumber}>{apps.length}</Text>
          <Text style={s.statLabel}>
            DA/CDC application{apps.length !== 1 ? 's' : ''} found within {radius} m
            in the last {data.window_days} days
          </Text>
        </View>

        <View style={s.divider} />

        {/* Key risk callout — paid, only when applications exist */}
        {data.is_paid === true && apps.length > 0 && (() => {
          const keyApp = [...apps].sort((a, b) => {
            const dwA = Number(a.NumberOfNewDwellings ?? 0);
            const dwB = Number(b.NumberOfNewDwellings ?? 0);
            if (dwB !== dwA) return dwB - dwA;
            const costA = Number(a.CostOfDevelopment ?? 0);
            const costB = Number(b.CostOfDevelopment ?? 0);
            if (costB !== costA) return costB - costA;
            return (a._distance_m ?? 9999) - (b._distance_m ?? 9999);
          })[0];
          const appNum = keyApp.PlanningPortalApplicationNumber ?? '—';
          const cost = formatCost(keyApp.CostOfDevelopment);
          const dwellings = Number(keyApp.NumberOfNewDwellings ?? 0);
          const metaParts = [
            keyApp.Status,
            keyApp._distance_m != null ? `${keyApp._distance_m} m away` : null,
            cost ? `Cost ${cost}` : null,
            dwellings > 0 ? `${dwellings} new dwelling${dwellings !== 1 ? 's' : ''}` : null,
          ].filter(Boolean);
          return (
            <View style={{ backgroundColor: AMBER_LIGHT, borderLeft: `3 solid ${AMBER}`, borderRadius: 2, paddingVertical: 10, paddingHorizontal: 12, marginBottom: 16 }}>
              <Text style={{ fontSize: 7.5, fontFamily: 'Helvetica-Bold', color: AMBER, marginBottom: 4 }}>
                Highest-impact application nearby
              </Text>
              <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 3 }}>
                {appNum}{keyApp.DevelopmentType ? `  -  ${keyApp.DevelopmentType}` : ''}
              </Text>
              {keyApp.ApplicationDescription ? (
                <Text style={{ fontSize: 8.5, color: GRAY_700, marginBottom: 3 }}>
                  {keyApp.ApplicationDescription}
                </Text>
              ) : null}
              {keyApp.PropertyAddress ? (
                <Text style={{ fontSize: 7.5, color: GRAY_500, marginBottom: 3 }}>
                  {keyApp.PropertyAddress}
                </Text>
              ) : null}
              {metaParts.length > 0 && (
                <Text style={{ fontSize: 7.5, color: GRAY_700 }}>{metaParts.join('  -  ')}</Text>
              )}
            </View>
          );
        })()}

        {/* ---- PAID analytical enhancements ---- */}
        {data.is_paid === true && apps.length > 0 && (() => {
          // 3a. Neighbourhood pressure score
          const score = calcPressureScore(apps);
          const label = pressureLabel(score);

          // 3b. Construction impact window — top 2 active DAs by scale
          const activeDAs = apps
            .filter(a => {
              const st = (a.Status ?? '').toLowerCase();
              return st.includes('approved') || st.includes('determined') ||
                     st.includes('under assessment') || st.includes('assessment');
            })
            .sort((a, b) => Number(b.NumberOfNewDwellings ?? 0) - Number(a.NumberOfNewDwellings ?? 0))
            .slice(0, 2);

          // 3c. Serial developer flag
          const nameCounts: Record<string, number> = {};
          for (const app of apps) {
            const name = (app.ApplicantName ?? '').trim();
            if (name) nameCounts[name] = (nameCounts[name] ?? 0) + 1;
          }
          const serialDevs = Object.entries(nameCounts).filter(([, n]) => n >= 2);

          return (
            <>
              {/* Pressure score */}
              <View style={{
                backgroundColor: GRAY_100, borderRadius: 4, padding: 10,
                marginBottom: 12,
              }}>
                <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 3 }}>
                  {`Neighbourhood pressure: ${score} / 10 (${label})`}
                </Text>
                <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
                  {`Based on ${apps.length} development application${apps.length !== 1 ? 's' : ''} within ${data.radius_m ?? 500} m, weighted by proximity and scale.`}
                </Text>
              </View>

              {/* Construction windows */}
              {activeDAs.length > 0 && (
                <View style={{ marginBottom: 12 }}>
                  <Text style={[s.sectionTitle, { marginTop: 0 }]}>Construction impact window</Text>
                  {activeDAs.map((app, i) => {
                    const window = estimateConstructionWindow(app);
                    if (!window) return null;
                    const appNum = app.PlanningPortalApplicationNumber ?? '—';
                    return (
                      <View key={i} style={{
                        backgroundColor: AMBER_LIGHT, borderLeft: `3 solid ${AMBER}`,
                        paddingVertical: 6, paddingHorizontal: 8, marginBottom: 6, borderRadius: 2,
                      }}>
                        <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 2 }}>
                          {appNum}{app.PropertyAddress ? `  —  ${app.PropertyAddress}` : ''}
                        </Text>
                        <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.4 }}>{window}</Text>
                      </View>
                    );
                  })}
                </View>
              )}

              {/* Serial developer flag */}
              {serialDevs.length > 0 && (
                <View style={{
                  backgroundColor: '#fff7ed', borderRadius: 4, padding: 10,
                  marginBottom: 12, borderWidth: 1, borderColor: '#fed7aa',
                }}>
                  <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: '#9a3412', marginBottom: 4 }}>
                    Serial developer activity
                  </Text>
                  {serialDevs.map(([name, count]) => (
                    <Text key={name} style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
                      {`${name} has ${count} applications within ${data.radius_m ?? 500} m. This pattern may indicate staged development.`}
                    </Text>
                  ))}
                </View>
              )}
            </>
          );
        })()}

        {/* Applications list */}
        {apps.length === 0 ? (
          <Text style={s.bodyText}>
            No development applications or complying development certificates were lodged
            within {radius} m in the last {data.window_days} days.
          </Text>
        ) : (
          <>
            <Text style={s.sectionTitle}>Applications</Text>
            {apps.map((app, i) => {
              const appNum = app.PlanningPortalApplicationNumber ?? '—';
              const lodged = formatDate(app.LodgementDate);
              const determined = formatDate(app.DeterminationDate);
              const cost = formatCost(app.CostOfDevelopment);
              const dwellings = app.NumberOfNewDwellings != null && Number(app.NumberOfNewDwellings) > 0
                ? Number(app.NumberOfNewDwellings)
                : null;
              const metaParts = [
                app.Status,
                lodged ? `Lodged ${lodged}` : null,
                determined ? `Determined ${determined}` : null,
                cost ? `Cost ${cost}` : null,
                dwellings ? `${dwellings} new dwelling${dwellings !== 1 ? 's' : ''}` : null,
              ].filter(Boolean);

              return (
                <View key={i} style={s.appCard} wrap={false}>
                  <View style={s.appHeader}>
                    <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
                      <Text style={s.appNum}>{appNum}</Text>
                      <Text style={s.appType}>{app.ApplicationType ?? 'DA'}</Text>
                    </View>
                    {app._distance_m != null && (
                      <Text style={s.distBadge}>{app._distance_m} m away</Text>
                    )}
                  </View>
                  {app.ApplicationDescription && (
                    <Text style={s.appDesc}>{app.ApplicationDescription}</Text>
                  )}
                  {app.PropertyAddress && (
                    <Text style={[s.appMeta, { marginBottom: 2 }]}>{app.PropertyAddress}</Text>
                  )}
                  {metaParts.length > 0 && (
                    <Text style={s.appMeta}>{metaParts.join(' · ')}</Text>
                  )}
                </View>
              );
            })}
          </>
        )}

        <ReferralBox />

        <View style={[s.divider, { marginTop: 16 }]} />
        <Text style={[s.bodyText, { color: GRAY_500, fontSize: 7.5 }]}>
          Data: NSW ePlanning Portal (DA and CDC applications). Results are indicative only and
          may not include all applications. Consult council for a complete search.
          Report generated {data.run_date} · plotdetect.com.au
        </Text>

        <Footer pageNum={1} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 2: Aerial tile (optional)                                       */}
      {/* ------------------------------------------------------------------ */}
      {data.tile_b64 && (
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />
          <Text style={s.sectionTitle}>Property aerial view</Text>
          <Text style={[s.bodyText, { color: GRAY_500, marginBottom: 10 }]}>
            Your property (teal) and nearby DA/CDC applications (amber/purple) on NSW SIX Maps aerial imagery.
          </Text>
          <AerialWithMarkers
            tile_b64={data.tile_b64}
            lat={data.lat}
            lng={data.lng}
            applications={apps}
          />
          <Text style={[s.bodyText, { fontSize: 7, color: GRAY_500, marginTop: 6 }]}>
            © NSW SIX Maps (LPI_Imagery_Best) — CC-BY 4.0 NSW Government · for reference only
          </Text>
          <Footer pageNum={2} total={totalPages} />
        </Page>
      )}

    </Document>
  );
}
