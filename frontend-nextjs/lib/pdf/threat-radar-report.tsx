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
import { WhatThisMeans, PlotDetectFooter, AboutPage, ReferralLinks, DataCurrencyTable, QRBlock, PreparedBy } from './shared-components';
import { AerialWithOverlay } from './map-overlay';
import { PDF_DISCLAIMERS } from '../disclaimers';

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
  lot_polygon?: { type: string; coordinates: number[][][] } | null;
  tile_b64: string | null;
  qr_b64?: string | null;
  firm_name?: string | null;
  shareable_url?: string | null;
}

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

const TEAL       = '#0f766e';
const TEAL_LIGHT = '#f0fdfa';
const RED        = '#dc2626';
const AMBER      = '#d97706';
const AMBER_LIGHT = '#fffbeb';
const GREEN      = '#16a34a';
const GRAY_900   = '#111827';
const GRAY_700   = '#374151';
const GRAY_500   = '#6b7280';
const GRAY_300   = '#d1d5db';
const GRAY_100   = '#f3f4f6';

const SEVERITY_COLORS = { green: GREEN, amber: AMBER, red: RED };

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
  logoRow:   { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 32 },
  logoImg:   { width: 18, height: 18 },
  h1:        { fontSize: 22, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 6 },
  subhead:   { fontSize: 11, color: GRAY_700, marginBottom: 3 },
  dateText:  { fontSize: 9, color: GRAY_500, marginBottom: 16 },
  sectionTitle: {
    fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_500,
    textTransform: 'uppercase', letterSpacing: 0.8,
    marginTop: 16, marginBottom: 8,
  },
  divider: { borderBottom: `1 solid ${GRAY_300}`, marginVertical: 12 },
  bodyText: { fontSize: 8.5, color: GRAY_700, lineHeight: 1.5, marginBottom: 6 },
  // Application cards
  appCard: { borderBottom: `1 solid ${GRAY_300}`, paddingVertical: 8 },
  appHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 3 },
  appNum:    { fontSize: 9, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  appType:   { fontSize: 8, color: TEAL, fontFamily: 'Helvetica-Bold' },
  distBadge: {
    fontSize: 7, backgroundColor: AMBER_LIGHT, color: AMBER,
    paddingVertical: 1, paddingHorizontal: 5, borderRadius: 10,
  },
  appDesc:   { fontSize: 8.5, color: GRAY_700, marginBottom: 3 },
  appMeta:   { fontSize: 7.5, color: GRAY_500 },
});

// ---------------------------------------------------------------------------
// Finding row
// ---------------------------------------------------------------------------

interface Finding {
  label: string;
  value: string;
  detail: string;
  severity: 'green' | 'amber' | 'red';
}

function FindingRow({ finding }: { finding: Finding }) {
  const dotColor = SEVERITY_COLORS[finding.severity];
  return (
    <View style={{ paddingVertical: 8, borderBottom: `1 solid ${GRAY_100}` }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 3 }}>
        <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: dotColor }} />
        <Text style={{ fontSize: 10, fontFamily: 'Helvetica-Bold', color: GRAY_900 }}>
          {finding.value}
        </Text>
      </View>
      <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5, marginLeft: 13, marginBottom: 2 }}>
        {finding.detail}
      </Text>
      <Text style={{ fontSize: 6.5, color: GRAY_500, marginLeft: 13 }}>
        {finding.label}
      </Text>
    </View>
  );
}

function PaidSectionHeader({ title }: { title: string }) {
  return (
    <View style={{
      flexDirection: 'row', alignItems: 'center', gap: 6,
      backgroundColor: TEAL_LIGHT, borderRadius: 3,
      paddingVertical: 5, paddingHorizontal: 8,
      marginTop: 16, marginBottom: 8,
      borderWidth: 1, borderColor: '#99f6e4',
    }}>
      <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: TEAL, textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {title}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso?: string) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatCost(val?: number | string) {
  if (val == null || val === '' || val === 0) return null;
  const n = typeof val === 'string' ? parseFloat(val) : val;
  if (!n || isNaN(n)) return null;
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(n);
}

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
  if (score >= 8) return 'Intense';
  if (score >= 5) return 'High';
  if (score >= 3) return 'Moderate';
  return 'Low';
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
    return `If approved mid-${approvalYear}, construction likely ${buildStart}–${buildEnd}. Noise and access impacts possible.`;
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

function Footer({ pageNum, total }: { pageNum: number; total: number }) {
  return (
    <PlotDetectFooter reportName="Threat Radar" pageNum={pageNum} total={total} />
  );
}

// Aerial tile with SVG markers
const TILE_D_LNG = 0.0005;
const TILE_D_LAT = 0.0005;
const TILE_PX = 512;

function AerialWithMarkers({ tile_b64, lat, lng, applications }: {
  tile_b64: string; lat: number; lng: number; applications: ThreatRadarApplication[];
}) {
  const toX = (appLng: number) => ((appLng - (lng - TILE_D_LNG)) / (2 * TILE_D_LNG)) * TILE_PX;
  const toY = (appLat: number) => ((lat + TILE_D_LAT - appLat) / (2 * TILE_D_LAT)) * TILE_PX;
  const visibleApps = applications.filter((a) => {
    const aLat = Number(a.Latitude); const aLng = Number(a.Longitude);
    if (!aLat || !aLng) return false;
    return aLat >= lat - TILE_D_LAT && aLat <= lat + TILE_D_LAT && aLng >= lng - TILE_D_LNG && aLng <= lng + TILE_D_LNG;
  });
  return (
    <View style={{ position: 'relative', width: '100%' }}>
      <Image src={`data:image/png;base64,${tile_b64}`} style={{ width: '100%', borderRadius: 4 }} />
      <Svg viewBox={`0 0 ${TILE_PX} ${TILE_PX}`} style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}>
        {visibleApps.map((app, i) => {
          const x = toX(Number(app.Longitude)); const y = toY(Number(app.Latitude));
          return <Circle key={i} cx={String(x)} cy={String(y)} r="8" fill={app.ApplicationType === 'DA' ? '#f59e0b' : '#a855f7'} opacity="0.85" stroke="white" strokeWidth="2" />;
        })}
        <Circle cx={String(TILE_PX / 2)} cy={String(TILE_PX / 2)} r="10" fill="#0d9488" stroke="white" strokeWidth="3" />
      </Svg>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Build findings
// ---------------------------------------------------------------------------

function buildFindings(data: ThreatRadarReportData): Finding[] {
  const findings: Finding[] = [];
  const apps = data.applications ?? [];
  const radius = data.radius_m ?? 500;

  // Application count
  if (apps.length === 0) {
    findings.push({
      label: `NSW ePlanning Portal · ${radius}m radius · last ${data.window_days} days`,
      value: 'No development applications found',
      detail: 'No DA or CDC applications were lodged near this property in the search window.',
      severity: 'green',
    });
  } else {
    const totalCost = apps.reduce((sum, a) => sum + (Number(a.CostOfDevelopment) || 0), 0);
    const costStr = totalCost > 0 ? ` with ${formatCost(totalCost)} total development value` : '';
    findings.push({
      label: `NSW ePlanning Portal · ${radius}m radius · last ${data.window_days} days`,
      value: `${apps.length} application${apps.length !== 1 ? 's' : ''} found${costStr}`,
      detail: 'Review the application list below to assess potential impact on amenity, privacy, and traffic during construction.',
      severity: apps.length >= 5 ? 'red' : apps.length >= 2 ? 'amber' : 'green',
    });
  }

  // Net dwelling change
  const netDwellings = apps.reduce((sum, a) => sum + (Number(a.NumberOfNewDwellings) || 0), 0);
  if (netDwellings > 0) {
    findings.push({
      label: 'Net dwelling impact',
      value: `+${netDwellings} new dwelling${netDwellings !== 1 ? 's' : ''} proposed nearby`,
      detail: netDwellings >= 10
        ? 'Significant densification is proposed. Areas with this level of new housing typically experience increased traffic, parking pressure, and construction activity over 12–24 months.'
        : 'Moderate new housing proposed. Some construction disruption is expected, though the scale is relatively contained.',
      severity: netDwellings >= 10 ? 'red' : netDwellings >= 4 ? 'amber' : 'green',
    });
  }

  // Proximity alerts
  const closeApps = apps.filter(a => (a._distance_m ?? 999) < 100);
  if (closeApps.length > 0) {
    findings.push({
      label: 'Proximity alert',
      value: `${closeApps.length} application${closeApps.length !== 1 ? 's' : ''} within 100m`,
      detail: 'Development within 100m can directly affect noise, privacy, overshadowing, and traffic access during construction and after completion.',
      severity: 'red',
    });
  }

  // EPI variations
  const epiVars = apps.filter(a => a.EpiVariationProposedFlag === 'Yes' || a.EpiVariationProposedFlag === 'Y');
  if (epiVars.length > 0) {
    findings.push({
      label: 'Planning instrument variations',
      value: `${epiVars.length} application${epiVars.length !== 1 ? 's' : ''} seeking EPI variations`,
      detail: 'These applications seek exceptions to standard planning controls. If approved, they may set precedents for further variation from standard controls in the area.',
      severity: 'amber',
    });
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function ThreatRadarReportDocument({ data }: { data: ThreatRadarReportData }) {
  const apps = data.applications ?? [];
  const radius = data.radius_m ?? 500;
  const isPaid = data.is_paid === true;
  const hasTile = !!data.tile_b64;
  const totalPages = 1 + 1 + (hasTile ? 1 : 0);

  const findings = buildFindings(data);

  let pageCounter = 0;
  const nextPage = () => ++pageCounter;

  return (
    <Document title={`Threat Radar Report — ${data.address}`} author="PlotDetect">

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + Findings + Applications                             */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />
        <Text style={s.h1}>Neighbour Development Threat Radar</Text>
        <Text style={s.subhead}>{data.address}</Text>
        {data.council_name && (
          <Text style={{ fontSize: 9, color: GRAY_500, marginBottom: 2 }}>{data.council_name} LGA</Text>
        )}
        <Text style={s.dateText}>
          Last {data.window_days} days · within {radius}m · Report date: {data.run_date}
        </Text>
        <PreparedBy firmName={data.firm_name} />

        {/* Key findings */}
        <Text style={s.sectionTitle}>Key findings</Text>
        {findings.map((f) => (
          <FindingRow key={f.label} finding={f} />
        ))}

        {/* Paid analytical enhancements */}
        {isPaid && apps.length > 0 && (() => {
          const score = calcPressureScore(apps);
          const label = pressureLabel(score);

          const activeDAs = apps
            .filter(a => {
              const st = (a.Status ?? '').toLowerCase();
              return st.includes('approved') || st.includes('determined') || st.includes('assessment');
            })
            .sort((a, b) => Number(b.NumberOfNewDwellings ?? 0) - Number(a.NumberOfNewDwellings ?? 0))
            .slice(0, 2);

          const nameCounts: Record<string, number> = {};
          for (const app of apps) {
            const name = (app.ApplicantName ?? '').trim();
            if (name) nameCounts[name] = (nameCounts[name] ?? 0) + 1;
          }
          const serialDevs = Object.entries(nameCounts).filter(([, n]) => n >= 2);

          return (
            <>
              <PaidSectionHeader title="Development pressure analysis — paid data" />

              {/* Pressure score */}
              <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 10, marginBottom: 8 }}>
                <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 3 }}>
                  Neighbourhood pressure: {score}/10 ({label})
                </Text>
                <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
                  Based on {apps.length} application{apps.length !== 1 ? 's' : ''} within {radius}m, weighted by proximity and scale.
                </Text>
              </View>

              {/* Construction windows */}
              {activeDAs.length > 0 && activeDAs.map((app, i) => {
                const window = estimateConstructionWindow(app);
                if (!window) return null;
                return (
                  <View key={i} style={{ backgroundColor: AMBER_LIGHT, borderLeft: `3 solid ${AMBER}`, paddingVertical: 6, paddingHorizontal: 8, marginBottom: 4, borderRadius: 2 }}>
                    <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 2 }}>
                      {app.PlanningPortalApplicationNumber ?? '—'}
                    </Text>
                    <Text style={{ fontSize: 8, color: GRAY_700 }}>{window}</Text>
                  </View>
                );
              })}

              {/* Serial developer flag */}
              {serialDevs.length > 0 && (
                <View style={{ backgroundColor: '#fff7ed', borderRadius: 4, padding: 10, marginTop: 4, borderWidth: 1, borderColor: '#fed7aa' }}>
                  <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: '#9a3412', marginBottom: 4 }}>
                    Serial developer activity
                  </Text>
                  {serialDevs.map(([name, count]) => (
                    <Text key={name} style={{ fontSize: 8, color: GRAY_700 }}>
                      {name} has {count} applications within {radius}m — may indicate staged development.
                    </Text>
                  ))}
                </View>
              )}
            </>
          );
        })()}

        {/* Free upsell */}
        {!isPaid && apps.length > 0 && (
          <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 12, marginTop: 12 }}>
            <Text style={{ fontSize: 9, color: GRAY_700, marginBottom: 6 }}>
              The paid monitoring plan includes:
            </Text>
            {[
              'Neighbourhood pressure score (1–10)',
              'Construction impact timeline estimates',
              'Serial developer detection',
              'Monthly email alerts for new applications',
            ].map((item) => (
              <View key={item} style={{ flexDirection: 'row', alignItems: 'flex-start', marginBottom: 3 }}>
                <Text style={{ fontSize: 8, color: TEAL, marginRight: 4 }}>•</Text>
                <Text style={{ fontSize: 8, color: GRAY_700 }}>{item}</Text>
              </View>
            ))}
            <Text style={{ fontSize: 8, color: TEAL, fontFamily: 'Helvetica-Bold', marginTop: 6 }}>
              Subscribe at plotdetect.com.au — $9/month
            </Text>
          </View>
        )}

        {/* Applications list */}
        {apps.length > 0 && (
          <>
            <Text style={s.sectionTitle}>Applications</Text>
            {apps.map((app, i) => {
              const appNum = app.PlanningPortalApplicationNumber ?? '—';
              const lodged = formatDate(app.LodgementDate);
              const determined = formatDate(app.DeterminationDate);
              const cost = formatCost(app.CostOfDevelopment);
              const dwellings = app.NumberOfNewDwellings != null && Number(app.NumberOfNewDwellings) > 0
                ? Number(app.NumberOfNewDwellings) : null;
              const metaParts = [
                app.Status,
                lodged ? `Lodged ${lodged}` : null,
                determined ? `Det. ${determined}` : null,
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
                      <Text style={s.distBadge}>{app._distance_m}m away</Text>
                    )}
                  </View>
                  {app.ApplicationDescription && <Text style={s.appDesc}>{app.ApplicationDescription}</Text>}
                  {app.PropertyAddress && <Text style={[s.appMeta, { marginBottom: 2 }]}>{app.PropertyAddress}</Text>}
                  {metaParts.length > 0 && <Text style={s.appMeta}>{metaParts.join(' · ')}</Text>}
                </View>
              );
            })}
          </>
        )}

        {/* Referrals */}
        <View style={{ backgroundColor: TEAL_LIGHT, borderRadius: 4, padding: 10, marginTop: 12, borderWidth: 1, borderColor: '#99f6e4' }}>
          <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
            Next steps
          </Text>
          <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
            A buyers agent can advise on price adjustments based on nearby development activity. A town planner can assess whether approved DAs would materially affect amenity.
          </Text>
        </View>

        <ReferralLinks links={[
          { label: 'Buyers agent', url: 'https://www.rebaa.com.au/find-a-buyers-agent', urlDisplay: 'rebaa.com.au/find-a-buyers-agent' },
          { label: 'Town planner', url: 'https://www.planning.org.au/find-a-planner', urlDisplay: 'planning.org.au/find-a-planner' },
        ]} />

        {/* Data currency */}
        <DataCurrencyTable rows={[
          { source: 'NSW ePlanning Portal (OnlineDA + OnlineCDC)', type: 'Live API query', currency: `Queried ${data.run_date}` },
        ]} />

        {/* Disclaimer */}
        <Text style={s.sectionTitle}>Disclaimer</Text>
        <Text style={s.bodyText}>
          {PDF_DISCLAIMERS.threat_radar}
        </Text>
        <Text style={[s.bodyText, { color: GRAY_500 }]}>
          Report generated by PlotDetect · plotdetect.com.au · {data.run_date}
        </Text>

        {data.qr_b64 && data.shareable_url && (
          <QRBlock url={data.shareable_url} qr_b64={data.qr_b64} />
        )}

        <Footer pageNum={nextPage()} total={totalPages} />
      </Page>

      {/* About page */}
      <AboutPage
        logo_b64={data.logo_b64}
        pageNum={nextPage()}
        total={totalPages}
        reportName="Threat Radar"
      />

      {/* Aerial tile (optional) */}
      {hasTile && (
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />
          <Text style={s.sectionTitle}>Property aerial view</Text>
          <Text style={[s.bodyText, { color: GRAY_500, marginBottom: 10 }]}>
            Your property (teal) and nearby DA/CDC applications (amber/purple) on NSW SIX Maps aerial imagery.
          </Text>
          <AerialWithMarkers tile_b64={data.tile_b64!} lat={data.lat} lng={data.lng} applications={apps} />
          <Text style={[s.bodyText, { fontSize: 7, color: GRAY_500, marginTop: 6 }]}>
            © NSW SIX Maps (LPI_Imagery_Best) — CC-BY 4.0 NSW Government · for reference only
          </Text>
          <Footer pageNum={nextPage()} total={totalPages} />
        </Page>
      )}

    </Document>
  );
}
