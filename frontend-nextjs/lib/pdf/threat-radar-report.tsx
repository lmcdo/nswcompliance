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
  _distance_m?: number | null;
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
      {'Data valid as of ' + runDate + '. Planning controls are amended regularly - re-run this report before exchange of contracts.'}
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
        {data.is_paid !== false && apps.length > 0 && (() => {
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
            NSW SIX Maps aerial imagery for context.
          </Text>
          <Image
            src={`data:image/png;base64,${data.tile_b64}`}
            style={{ width: '100%', borderRadius: 4 }}
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
