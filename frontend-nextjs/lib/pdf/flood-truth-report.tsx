/**
 * Flood Truth Report PDF
 * Generated server-side via @react-pdf/renderer renderToBuffer().
 * Data passed directly from the flood pipeline response — no DB lookup.
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
import { WhatThisMeans, PlotDetectFooter, AboutPage, ReferralLinks, InsurerChecklist } from './shared-components';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface EmsActivation {
  activation_id: string;
  event_name: string;
  event_date: string;
  flood_type: string;
}

export interface BomFloodEvent {
  date: string;
  peak_m: number;
  ari_category: string;
}

export interface FloodStudyEntry {
  depth_m: number | null;
  level_m_ahd: number | null;
}

export interface FloodStudyResult {
  study_key: string;
  study_name: string;
  source: string;
  design: Record<string, FloodStudyEntry>;
  historical: Record<string, FloodStudyEntry>;
}

export interface FloodReportData {
  address: string;
  run_date: string;
  lat: number;
  lng: number;
  lga_name?: string | null;
  logo_b64?: string | null;
  // outputs
  epi_flood_class: string | null;
  epi_flood_label: string | null;
  sar_flood_detected: boolean | null;
  sar_confidence: string | null;
  sar_analysis_date: string | null;
  ems_flood_detected: boolean | null;
  ems_activations: EmsActivation[] | null;
  jrc_water_occurrence_pct: number | null;
  jrc_data_year: number | null;
  dea_wofs_frequency_pct: number | null;
  bom_gauge_name: string | null;
  bom_gauge_distance_km: number | null;
  bom_last_major_flood_date: string | null;
  bom_last_major_flood_peak_m: number | null;
  // flood enhancements
  bom_flood_history?: BomFloodEvent[] | null;
  flood_study_name?: string | null;
  flood_study_date?: string | null;
  // Hawkesbury FRMSP 2025 — AEP flood levels (metres AHD)
  hawkesbury_flood_level_2aep?: number | null;
  hawkesbury_flood_level_5aep?: number | null;
  hawkesbury_flood_level_10aep?: number | null;
  hawkesbury_flood_level_20aep?: number | null;
  hawkesbury_flood_level_50aep?: number | null;
  hawkesbury_flood_level_100aep?: number | null;
  hawkesbury_flood_level_200aep?: number | null;
  hawkesbury_flood_level_500aep?: number | null;
  hawkesbury_flood_level_pmf?: number | null;
  hawkesbury_flood_study?: string | null;
  // Generalised flood study rasters + DEM elevation
  ground_elevation_m_ahd?: number | null;
  in_100yr_flood_zone?: boolean;
  flood_studies?: FloodStudyResult[];
  s1_gap_warning: string | null;
  data_currency: string;
  flood_signal: 'none' | 'low' | 'moderate' | 'elevated' | null;
  confidence: string;
  data_sources: string[];
  warnings?: string[];
  is_paid?: boolean;
  tile_b64: string | null;
  qr_b64?: string | null;
  shareable_url?: string | null;
  firm_name?: string | null;
}

// ---------------------------------------------------------------------------
// Palette (shared with granny-flat-report)
// ---------------------------------------------------------------------------

const TEAL       = '#0f766e';
const RED        = '#dc2626';
const RED_LIGHT  = '#fef2f2';
const ORANGE     = '#ea580c';
const ORANGE_LIGHT = '#fff7ed';
const AMBER      = '#d97706';
const AMBER_LIGHT = '#fffbeb';
const GREEN      = '#16a34a';
const GREEN_LIGHT = '#f0fdf4';
const GRAY_900   = '#111827';
const GRAY_700   = '#374151';
const GRAY_500   = '#6b7280';
const GRAY_300   = '#d1d5db';
const GRAY_100   = '#f3f4f6';
const WHITE      = '#ffffff';

const SIGNAL_META: Record<string, { label: string; bg: string; color: string }> = {
  none:     { label: 'No flood indicators detected', bg: GREEN_LIGHT,  color: GREEN  },
  low:      { label: 'Low flood signal',             bg: AMBER_LIGHT,  color: AMBER  },
  moderate: { label: 'Moderate flood signal',        bg: ORANGE_LIGHT, color: ORANGE },
  elevated: { label: 'Elevated flood signal',        bg: RED_LIGHT,    color: RED    },
};

const EPI_CLASS_META: Record<string, { label: string }> = {
  high_flood_risk:     { label: 'High flood risk zone' },
  medium_flood_risk:   { label: 'Medium flood risk zone' },
  low_flood_risk:      { label: 'Low flood risk zone' },
  flood_planning_area: { label: 'Flood planning area' },
  none:                { label: 'Not in statutory flood overlay' },
};

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const s = StyleSheet.create({
  page: {
    fontFamily: 'Helvetica',
    fontSize: 9,
    color: GRAY_900,
    paddingTop: 48,
    paddingBottom: 48,
    paddingHorizontal: 48,
    lineHeight: 1.4,
  },
  logo:     { fontSize: 11, fontFamily: 'Helvetica-Bold', color: TEAL },
  logoRow:  { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 64 },
  logoImg:  { width: 18, height: 18 },
  h1:       { fontSize: 22, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 8 },
  subhead:  { fontSize: 12, color: GRAY_700, marginBottom: 4 },
  dateText: { fontSize: 9, color: GRAY_500, marginBottom: 48 },
  badge: {
    paddingVertical: 5, paddingHorizontal: 12,
    borderRadius: 4, alignSelf: 'flex-start', marginBottom: 24,
  },
  badgeText: { fontSize: 11, fontFamily: 'Helvetica-Bold' },
  sectionTitle: {
    fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_500,
    textTransform: 'uppercase', letterSpacing: 0.8,
    marginTop: 20, marginBottom: 8,
  },
  row2: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  card: {
    flex: 1, backgroundColor: GRAY_100, borderRadius: 4,
    padding: 10,
  },
  cardLabel: { fontSize: 7, color: GRAY_500, marginBottom: 3 },
  cardValue: { fontSize: 12, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  cardSub:   { fontSize: 7.5, color: GRAY_700, marginTop: 2 },
  divider: { borderBottom: `1 solid ${GRAY_300}`, marginVertical: 14 },
  bodyText: { fontSize: 8.5, color: GRAY_700, lineHeight: 1.5, marginBottom: 6 },
  warningBox: {
    backgroundColor: AMBER_LIGHT, borderLeft: `3 solid ${AMBER}`,
    paddingVertical: 8, paddingHorizontal: 10, marginBottom: 8, borderRadius: 2,
  },
  warningText: { fontSize: 8, color: GRAY_700 },
  footer: {
    position: 'absolute', bottom: 28, left: 48, right: 48,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  footerText: { fontSize: 7, color: GRAY_500 },
  sourceRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: 6 },
  sourcePill: {
    backgroundColor: GRAY_100, borderRadius: 3,
    paddingVertical: 2, paddingHorizontal: 5,
    fontSize: 7, color: GRAY_700,
  },
});

// ---------------------------------------------------------------------------
// Helper: page number
// ---------------------------------------------------------------------------

function ValidityNote({ runDate }: { runDate: string }) {
  return (
    <Text style={{ fontSize: 7.5, color: GRAY_500, marginTop: 6, fontStyle: 'italic' }}>
      {'Data valid as of ' + runDate + '. Flood data is updated periodically — re-run this report if more than 12 months have passed or before exchange of contracts.'}
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
        A licensed flood consultant can assess whether this flood classification triggers mandatory disclosure under the Conveyancing (Sale of Land) Regulation 2022. A conveyancer can advise on the impact on contract terms and negotiate appropriate special conditions.
      </Text>
    </View>
  );
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
    <PlotDetectFooter reportName="Flood Truth Report" pageNum={pageNum} total={total} />
  );
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function FloodTruthReportDocument({ data }: { data: FloodReportData }) {
  const signal     = data.flood_signal ?? 'none';
  const signalMeta = SIGNAL_META[signal] ?? SIGNAL_META.none;
  const epiKey     = data.epi_flood_class ?? 'none';
  const epiLabel   = EPI_CLASS_META[epiKey]?.label ?? epiKey;
  const hasStudies = data.is_paid && (data.flood_studies ?? []).length > 0;
  // +1 for About page (T4)
  const totalPages = (data.tile_b64 ? 1 : 0) + (hasStudies ? 3 : 2) + 1;

  return (
    <Document title={`Flood Truth Report — ${data.address}`} author="PlotDetect">

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + Signal + Data grid                                  */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />
        <Text style={s.h1}>Flood Data Summary</Text>
        <Text style={s.subhead}>{data.address}</Text>
        <Text style={s.dateText}>Report date: {data.run_date}</Text>
        <ValidityNote runDate={data.run_date} />

        {/* Signal badge */}
        <View style={[s.badge, { backgroundColor: signalMeta.bg }]}>
          <Text style={[s.badgeText, { color: signalMeta.color }]}>
            {signalMeta.label}
          </Text>
        </View>

        {/* 100yr flood zone headline */}
        {data.in_100yr_flood_zone === true && (
          <View style={{ backgroundColor: RED_LIGHT, borderLeft: `3 solid ${RED}`, paddingVertical: 8, paddingHorizontal: 10, marginBottom: 10, borderRadius: 2 }}>
            <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: RED }}>
              Within 1-in-100 year flood zone
            </Text>
            {data.ground_elevation_m_ahd != null && (
              <Text style={{ fontSize: 8, color: GRAY_700, marginTop: 3 }}>
                Ground elevation: {data.ground_elevation_m_ahd.toFixed(1)}m AHD
              </Text>
            )}
          </View>
        )}
        {data.in_100yr_flood_zone === false && (
          <View style={{ backgroundColor: GREEN_LIGHT, borderLeft: `3 solid ${GREEN}`, paddingVertical: 8, paddingHorizontal: 10, marginBottom: 10, borderRadius: 2 }}>
            <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: GREEN }}>
              Not in 1-in-100 year flood zone
            </Text>
            {data.ground_elevation_m_ahd != null && (
              <Text style={{ fontSize: 8, color: GRAY_700, marginTop: 3 }}>
                Ground elevation: {data.ground_elevation_m_ahd.toFixed(1)}m AHD
              </Text>
            )}
          </View>
        )}

        {/* A1: Plain-English interpretation */}
        {data.is_paid === true && (() => {
          const depth1pct = (data.flood_studies ?? [])
            .flatMap(s => s.design?.['1pct']?.depth_m != null ? [s.design['1pct'].depth_m] : []);
          const maxDepth = depth1pct.length > 0 ? Math.max(...depth1pct) : null;
          if (data.in_100yr_flood_zone === true && maxDepth != null) {
            return (
              <WhatThisMeans>
                {`In a 1-in-100 year flood, modelled water depth at this site is approximately ${(maxDepth * 100).toFixed(0)}cm. ${maxDepth > 0.5 ? 'This is above floor level for most single-storey dwellings. ' : ''}Your conveyancer should request the Section 10.7(2) certificate from council ($53, approximately 5 business days) and a flood loading quote from your insurer before exchange.`}
              </WhatThisMeans>
            );
          }
          if (data.in_100yr_flood_zone === true) {
            return (
              <WhatThisMeans>
                This property is within a mapped 1-in-100 year flood zone. Your conveyancer should request the Section 10.7(2) certificate from council ($53, approximately 5 business days) and a flood loading quote from your insurer before exchange.
              </WhatThisMeans>
            );
          }
          if (signal !== 'none') {
            return (
              <WhatThisMeans>
                Flood indicators have been detected at this address from one or more data sources. While not in a mapped 1-in-100 year zone, you should request a Section 10.7 certificate from council to confirm the formal flood classification before exchange.
              </WhatThisMeans>
            );
          }
          return (
            <WhatThisMeans>
              No flood indicators were detected across the data sources checked. This is a positive signal, but a Section 10.7 certificate from council remains the authoritative confirmation for conveyancing purposes.
            </WhatThisMeans>
          );
        })()}

        {/* Insurance implication note */}
        <View style={{ backgroundColor: AMBER_LIGHT, borderRadius: 4, padding: 8, marginTop: 6, marginBottom: 4, borderWidth: 1, borderColor: '#fcd34d' }}>
          <Text style={{ fontSize: 8, color: '#92400e', lineHeight: 1.5 }}>
            Properties in a Flood Planning Area typically attract higher building and contents insurance premiums. Request a flood loading quote from your insurer before proceeding with purchase or finance.
          </Text>
        </View>

        <Text style={s.bodyText}>
          Cross-referenced across {data.data_sources.length} independent data sources.
          A formal Section 10.7 certificate from council is required for legal flood status.
        </Text>

        <View style={s.divider} />

        {/* Row 1: EPI overlay + EMS events */}
        <Text style={s.sectionTitle}>Statutory and observed flood data</Text>
        <View style={s.row2}>
          <View style={s.card}>
            <Text style={s.cardLabel}>Council flood overlay</Text>
            <Text style={s.cardValue}>{epiLabel}</Text>
            <Text style={s.cardSub}>
              NSW EPI Flood WFS · {data.data_currency !== 'unknown' ? data.data_currency : 'date unavailable'}
            </Text>
            {/* Flood study provenance — FREE */}
            {data.flood_study_name && (
              <Text style={[s.cardSub, { color: GRAY_500, marginTop: 4 }]}>
                {`Source: ${data.flood_study_name}${data.flood_study_date ? ` (effective ${data.flood_study_date})` : ''}. Flood planning controls derive from this study.`}
              </Text>
            )}
          </View>
          <View style={s.card}>
            <Text style={s.cardLabel}>Copernicus EMS observed events</Text>
            {data.ems_flood_detected === null ? (
              <Text style={[s.cardValue, { fontSize: 9, color: GRAY_500 }]}>Data not available</Text>
            ) : data.ems_flood_detected && data.ems_activations?.length ? (
              <>
                {data.ems_activations.map((a) => (
                  <View key={a.activation_id} style={{ marginBottom: 4 }}>
                    <Text style={[s.cardSub, { fontFamily: 'Helvetica-Bold', color: RED }]}>
                      {a.event_name}
                    </Text>
                    <Text style={s.cardSub}>{a.activation_id} · {a.event_date}</Text>
                  </View>
                ))}
              </>
            ) : (
              <Text style={[s.cardValue, { fontSize: 9, color: GRAY_700 }]}>
                No recorded events at this location
              </Text>
            )}
          </View>
        </View>

        {/* Row 2: JRC + BOM */}
        <View style={s.row2}>
          <View style={s.card}>
            <Text style={s.cardLabel}>40-year surface water history</Text>
            {(() => {
              const pct = data.dea_wofs_frequency_pct ?? data.jrc_water_occurrence_pct;
              const srcLabel = data.dea_wofs_frequency_pct != null
                ? 'DEA WOfS · Landsat 1987–present'
                : `JRC Global Surface Water · Landsat 1984–${data.jrc_data_year ?? 2021}`;
              return pct != null ? (
                <>
                  <Text style={s.cardValue}>
                    {pct.toFixed(1)}% of observations
                  </Text>
                  <Text style={s.cardSub}>
                    {pct === 0
                      ? 'No surface water observed'
                      : pct < 5
                      ? 'Rare — episodic inundation only'
                      : pct < 15
                      ? 'Occasional — periodic inundation'
                      : pct < 40
                      ? 'Frequent — seasonal or recurring inundation'
                      : 'Persistent — regular or permanent surface water'}
                  </Text>
                  <Text style={[s.cardSub, { color: GRAY_500 }]}>{srcLabel}</Text>
                </>
              ) : (
                <Text style={[s.cardValue, { fontSize: 9, color: GRAY_500 }]}>Not available</Text>
              );
            })()}
          </View>
          <View style={s.card}>
            <Text style={s.cardLabel}>Nearest BOM river gauge</Text>
            {data.bom_gauge_name ? (
              <>
                <Text style={[s.cardValue, { fontSize: 10 }]}>{data.bom_gauge_name}</Text>
                <Text style={s.cardSub}>{data.bom_gauge_distance_km != null ? data.bom_gauge_distance_km.toFixed(1) : '?'} km from property</Text>
                {data.bom_last_major_flood_date ? (
                  <Text style={[s.cardSub, { color: RED, fontFamily: 'Helvetica-Bold' }]}>
                    Last major flood: {data.bom_last_major_flood_date} — {data.bom_last_major_flood_peak_m != null ? data.bom_last_major_flood_peak_m.toFixed(2) : '?'}m peak
                  </Text>
                ) : (
                  <Text style={s.cardSub}>No major flood recorded at this gauge since 2021</Text>
                )}
                <Text style={[s.cardSub, { color: GRAY_500 }]}>BOM WaterConnect · SOS2 API</Text>
              </>
            ) : (
              <Text style={[s.cardValue, { fontSize: 9, color: GRAY_500 }]}>
                No BOM gauge within 75 km
              </Text>
            )}
          </View>
        </View>

        {/* BoM flood event history table — PAID (up to 3 events) */}
        {data.is_paid === true && data.bom_flood_history && data.bom_flood_history.length > 0 && (
          <View style={{ marginBottom: 12 }}>
            <Text style={s.sectionTitle}>BOM flood event history</Text>
            {/* Header */}
            <View style={{
              flexDirection: 'row', borderBottom: `1 solid ${GRAY_300}`,
              paddingVertical: 4,
            }}>
              <Text style={{ flex: 2, fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' }}>Date</Text>
              <Text style={{ flex: 1.5, fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase', textAlign: 'right' }}>Peak height</Text>
              <Text style={{ flex: 2, fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase', textAlign: 'right' }}>ARI category</Text>
            </View>
            {data.bom_flood_history.slice(0, 3).map((event, i) => (
              <View key={i} style={{
                flexDirection: 'row', borderBottom: `1 solid ${GRAY_300}`, paddingVertical: 5,
              }}>
                <Text style={{ flex: 2, fontSize: 8.5, color: GRAY_700 }}>{event.date}</Text>
                <Text style={{ flex: 1.5, fontSize: 8.5, color: RED, fontFamily: 'Helvetica-Bold', textAlign: 'right' }}>{event.peak_m} m</Text>
                <Text style={{ flex: 2, fontSize: 8.5, color: GRAY_700, textAlign: 'right' }}>{event.ari_category}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Flood study raster results — free: 1pct teaser per study */}
        {(data.flood_studies ?? []).map((study) => {
          const pct1 = study.design?.['1pct'];
          const hasDesign = pct1?.depth_m != null || pct1?.level_m_ahd != null;
          const historicalYears = Object.keys(study.historical ?? {}).sort();
          if (!hasDesign && historicalYears.length === 0) return null;
          return (
            <View key={study.study_key} style={[s.card, { marginBottom: 8 }]}>
              <Text style={s.cardLabel}>{study.study_name} — {study.source}</Text>
              {pct1?.depth_m != null && (
                <Text style={s.cardValue}>
                  {'1-in-100 yr flood depth: ' + pct1.depth_m.toFixed(2) + 'm'}
                  {pct1.level_m_ahd != null ? ` (${pct1.level_m_ahd.toFixed(2)}m AHD)` : ''}
                </Text>
              )}
              {pct1?.depth_m == null && pct1?.level_m_ahd != null && (
                <Text style={s.cardValue}>
                  {'1-in-100 yr flood level: ' + pct1.level_m_ahd.toFixed(2) + 'm AHD'}
                </Text>
              )}
              {historicalYears.length > 0 && (
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                  {historicalYears.map((yr) => {
                    const ev = study.historical[yr];
                    const evLabel = ev?.depth_m != null ? `${ev.depth_m}m deep` : ev?.level_m_ahd != null ? `${ev.level_m_ahd}m AHD` : 'flooded';
                    return (
                      <Text key={yr} style={{ fontSize: 7, backgroundColor: AMBER_LIGHT, color: '#92400e', paddingVertical: 2, paddingHorizontal: 5, borderRadius: 3 }}>
                        {yr}: {evLabel}
                      </Text>
                    );
                  })}
                </View>
              )}
              {data.is_paid !== true && (
                <Text style={[s.cardSub, { color: GRAY_500, marginTop: 3 }]}>
                  Full AEP depth table included in the paid report
                </Text>
              )}
            </View>
          );
        })}

        {/* SAR row */}
        {data.sar_flood_detected !== null && (
          <View style={[s.card, { marginBottom: 12 }]}>
            <Text style={s.cardLabel}>Satellite SAR flood detection</Text>
            <Text style={s.cardValue}>
              {data.sar_flood_detected ? 'Flood signal detected' : 'No flood signal detected'}
              {data.sar_confidence ? ` — ${data.sar_confidence} confidence` : ''}
            </Text>
            <Text style={s.cardSub}>
              Sentinel-1 RTC · Microsoft Planetary Computer
              {data.sar_analysis_date ? ` · ${data.sar_analysis_date}` : ''}
            </Text>
          </View>
        )}

        {/* Warnings */}
        {(data.s1_gap_warning || (data.warnings && data.warnings.length > 0)) && (
          <>
            {data.s1_gap_warning && (
              <View style={s.warningBox}>
                <Text style={s.warningText}>{data.s1_gap_warning}</Text>
              </View>
            )}
            {data.warnings?.map((w, i) => (
              <View key={i} style={s.warningBox}>
                <Text style={s.warningText}>{w}</Text>
              </View>
            ))}
          </>
        )}

        <View style={s.divider} />

        <Text style={s.sectionTitle}>Data sources</Text>
        <View style={s.sourceRow}>
          {data.data_sources.map((src) => (
            <Text key={src} style={s.sourcePill}>{src}</Text>
          ))}
        </View>

        <Footer pageNum={1} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 2: Full AEP depth tables per flood study (PAID only)           */}
      {/* ------------------------------------------------------------------ */}
      {hasStudies && (() => {
        const AEP_DISPLAY: Record<string, string> = {
          '50pct': '1-in-2 yr (50% AEP)',
          '20pct': '1-in-5 yr (20% AEP)',
          '10pct': '1-in-10 yr (10% AEP)',
          '5pct':  '1-in-20 yr (5% AEP)',
          '2pct':  '1-in-50 yr (2% AEP)',
          '1pct':  '1-in-100 yr (1% AEP)',
          '0_5pct': '1-in-200 yr (0.5% AEP)',
          '0_2pct': '1-in-500 yr (0.2% AEP)',
          'pmf':   'PMF (Probable Maximum Flood)',
        };
        const AEP_ORDER = ['50pct','20pct','10pct','5pct','2pct','1pct','0_5pct','0_2pct','pmf'];
        return (
          <Page size="A4" style={s.page}>
            <LogoRow logo_b64={data.logo_b64} />
            <Text style={s.sectionTitle}>Flood depth and level by AEP event</Text>
            {data.ground_elevation_m_ahd != null && (
              <Text style={[s.bodyText, { marginBottom: 10 }]}>
                Ground elevation at this site: {data.ground_elevation_m_ahd.toFixed(1)}m AHD (NSW 5m DEM).
                Depth = flood level minus ground elevation.
              </Text>
            )}

            {(data.flood_studies ?? []).map((study) => {
              const designKeys = AEP_ORDER.filter((k) => study.design?.[k]);
              const histKeys = Object.keys(study.historical ?? {}).sort();
              if (designKeys.length === 0 && histKeys.length === 0) return null;
              const hasDepth = designKeys.some((k) => study.design[k]?.depth_m != null);
              return (
                <View key={study.study_key} style={{ marginBottom: 16 }}>
                  <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 6 }}>
                    {study.study_name}
                  </Text>
                  <Text style={{ fontSize: 7, color: GRAY_500, marginBottom: 6 }}>
                    Source: {study.source}
                  </Text>

                  {/* Table header */}
                  <View style={{ flexDirection: 'row', borderBottom: `1 solid ${GRAY_300}`, paddingVertical: 4 }}>
                    <Text style={{ flex: 3, fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' }}>
                      AEP event
                    </Text>
                    {hasDepth && (
                      <Text style={{ flex: 2, fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase', textAlign: 'right' }}>
                        Depth (m)
                      </Text>
                    )}
                    <Text style={{ flex: 2, fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase', textAlign: 'right' }}>
                      Level (m AHD)
                    </Text>
                  </View>

                  {/* Design event rows */}
                  {designKeys.map((aepKey) => {
                    const entry = study.design[aepKey];
                    const isHundred = aepKey === '1pct';
                    return (
                      <View key={aepKey} style={{
                        flexDirection: 'row', borderBottom: `1 solid ${GRAY_300}`, paddingVertical: 5,
                        backgroundColor: isHundred ? RED_LIGHT : undefined,
                      }}>
                        <Text style={{ flex: 3, fontSize: 8.5, color: isHundred ? RED : GRAY_700, fontFamily: isHundred ? 'Helvetica-Bold' : 'Helvetica' }}>
                          {AEP_DISPLAY[aepKey] ?? aepKey}
                        </Text>
                        {hasDepth && (
                          <Text style={{ flex: 2, fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: entry?.depth_m != null ? (isHundred ? RED : GRAY_900) : GRAY_500, textAlign: 'right' }}>
                            {entry?.depth_m != null ? entry.depth_m.toFixed(2) : '—'}
                          </Text>
                        )}
                        <Text style={{ flex: 2, fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: entry?.level_m_ahd != null ? (isHundred ? RED : GRAY_900) : GRAY_500, textAlign: 'right' }}>
                          {entry?.level_m_ahd != null ? entry.level_m_ahd.toFixed(2) : '—'}
                        </Text>
                      </View>
                    );
                  })}

                  {/* Historical event rows */}
                  {histKeys.length > 0 && (
                    <>
                      <View style={{ flexDirection: 'row', paddingVertical: 4, marginTop: 4 }}>
                        <Text style={{ fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' }}>
                          Historical events
                        </Text>
                      </View>
                      {histKeys.map((yr) => {
                        const entry = study.historical[yr];
                        return (
                          <View key={yr} style={{ flexDirection: 'row', borderBottom: `1 solid ${GRAY_300}`, paddingVertical: 5 }}>
                            <Text style={{ flex: 3, fontSize: 8.5, color: AMBER }}>{yr} flood event</Text>
                            {hasDepth && (
                              <Text style={{ flex: 2, fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: entry?.depth_m != null ? AMBER : GRAY_500, textAlign: 'right' }}>
                                {entry?.depth_m != null ? entry.depth_m.toFixed(2) : '—'}
                              </Text>
                            )}
                            <Text style={{ flex: 2, fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: entry?.level_m_ahd != null ? AMBER : GRAY_500, textAlign: 'right' }}>
                              {entry?.level_m_ahd != null ? entry.level_m_ahd.toFixed(2) : '—'}
                            </Text>
                          </View>
                        );
                      })}
                    </>
                  )}
                </View>
              );
            })}

            <Footer pageNum={2} total={totalPages} />
          </Page>
        );
      })()}

      {/* ------------------------------------------------------------------ */}
      {/* Disclaimer page                                                      */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        <ReferralBox />

        {/* A3: Referral directory links */}
        <ReferralLinks links={[
          { label: 'Section 10.7 certificate', url: 'https://www.planningportal.nsw.gov.au/spatialviewer', urlDisplay: 'Council website (via Planning Portal)' },
          { label: 'Flood consultant', url: 'https://www.fma.com.au/find-a-member', urlDisplay: 'fma.com.au/find-a-member' },
          { label: 'Conveyancer', url: 'https://www.aicnsw.com.au/find-a-conveyancer', urlDisplay: 'aicnsw.com.au/find-a-conveyancer' },
        ]} />

        {/* A4: Insurer/lender questionnaire — flood */}
        {data.is_paid === true && (
          <InsurerChecklist
            title="Questions for your insurer or lender"
            questions={[
              'Does this property attract a flood loading on building and/or contents insurance?',
              'What is the flood loading amount and how is it calculated?',
              'Is the property in a flood exclusion zone for any cover type?',
              'Has the property been subject to a flood insurance claim in the last 10 years?',
              'Will the lender require a flood certificate before unconditional approval?',
            ]}
          />
        )}

        <Text style={s.sectionTitle}>Important limitations</Text>
        <Text style={s.bodyText}>
          This report is an indicative cross-reference of publicly available flood data sources only.
          It does not constitute a formal Section 10.7 Planning Certificate, a flood engineering
          assessment, or legal advice.
        </Text>
        <Text style={s.bodyText}>
          Flood hazard determination for development applications, conveyancing, or insurance
          purposes requires a formal flood study or certificate issued by council under the
          Environmental Planning and Assessment Act 1979.
        </Text>
        <Text style={s.bodyText}>
          The Sentinel-1B satellite was non-operational December 2021 – March 2025 due to a
          gyroscope failure. SAR observations during this period have gaps. Sentinel-1C launched
          in March 2025 restores coverage.
        </Text>
        <Text style={s.bodyText}>
          JRC Global Surface Water data uses Landsat imagery from 1984 to present at 30m
          resolution. DEA Water Observations (WOfS) uses Landsat imagery from 1987 to present
          at 25m resolution (Australian Government, CC BY 4.0). Both datasets classify surface
          water from satellite observations; small or ephemeral water bodies below detection
          threshold may not be captured.
        </Text>
        <Text style={[s.bodyText, { color: GRAY_500 }]}>
          Report generated by PlotDetect · plotdetect.com.au · {data.run_date}
        </Text>

        <Footer pageNum={hasStudies ? 3 : 2} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* T4: About this report + tools list                                    */}
      {/* ------------------------------------------------------------------ */}
      <AboutPage
        logo_b64={data.logo_b64}
        pageNum={hasStudies ? 4 : 3}
        total={totalPages}
        reportName="Flood Truth Report"
      />

      {/* ------------------------------------------------------------------ */}
      {/* Aerial tile page (optional)                                          */}
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
          <Footer pageNum={totalPages} total={totalPages} />
        </Page>
      )}

    </Document>
  );
}
