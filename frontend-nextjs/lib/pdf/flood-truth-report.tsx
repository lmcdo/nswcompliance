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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface EmsActivation {
  activation_id: string;
  event_name: string;
  event_date: string;
  flood_type: string;
}

export interface FloodReportData {
  address: string;
  run_date: string;
  lat: number;
  lng: number;
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
  bom_gauge_name: string | null;
  bom_gauge_distance_km: number | null;
  bom_last_major_flood_date: string | null;
  bom_last_major_flood_peak_m: number | null;
  s1_gap_warning: string | null;
  data_currency: string;
  flood_signal: 'none' | 'low' | 'moderate' | 'elevated' | null;
  confidence: string;
  data_sources: string[];
  warnings?: string[];
  tile_b64: string | null;
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
  logo:     { fontSize: 11, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 64 },
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

function Footer({ pageNum, total }: { pageNum: number; total: number }) {
  return (
    <View style={s.footer} fixed>
      <Text style={s.footerText}>
        Flood Truth Report — plotdetect.com.au
      </Text>
      <Text style={s.footerText}>{pageNum} / {total}</Text>
    </View>
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
  const totalPages = data.tile_b64 ? 3 : 2;

  return (
    <Document title={`Flood Truth Report — ${data.address}`} author="PlotDetect">

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + Signal + Data grid                                  */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <Text style={s.logo}>PlotDetect</Text>
        <Text style={s.h1}>Flood Data Summary</Text>
        <Text style={s.subhead}>{data.address}</Text>
        <Text style={s.dateText}>Report date: {data.run_date}</Text>

        {/* Signal badge */}
        <View style={[s.badge, { backgroundColor: signalMeta.bg }]}>
          <Text style={[s.badgeText, { color: signalMeta.color }]}>
            {signalMeta.label}
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
            {data.jrc_water_occurrence_pct != null ? (
              <>
                <Text style={s.cardValue}>
                  {data.jrc_water_occurrence_pct.toFixed(0)}% of months
                </Text>
                <Text style={s.cardSub}>
                  {data.jrc_water_occurrence_pct === 0
                    ? 'No surface water observed 1984–present'
                    : data.jrc_water_occurrence_pct < 5
                    ? 'Rare — episodic inundation only'
                    : data.jrc_water_occurrence_pct < 15
                    ? 'Occasional — periodic inundation'
                    : data.jrc_water_occurrence_pct < 40
                    ? 'Frequent — seasonal or recurring inundation'
                    : 'Persistent — regular or permanent surface water'}
                </Text>
                <Text style={[s.cardSub, { color: GRAY_500 }]}>
                  JRC Global Surface Water · Landsat 1984–{data.jrc_data_year ?? 2021}
                </Text>
              </>
            ) : (
              <Text style={[s.cardValue, { fontSize: 9, color: GRAY_500 }]}>Not available</Text>
            )}
          </View>
          <View style={s.card}>
            <Text style={s.cardLabel}>Nearest BOM river gauge</Text>
            {data.bom_gauge_name ? (
              <>
                <Text style={[s.cardValue, { fontSize: 10 }]}>{data.bom_gauge_name}</Text>
                <Text style={s.cardSub}>{data.bom_gauge_distance_km} km from property</Text>
                {data.bom_last_major_flood_date ? (
                  <Text style={[s.cardSub, { color: RED, fontFamily: 'Helvetica-Bold' }]}>
                    Last major flood: {data.bom_last_major_flood_date} — {data.bom_last_major_flood_peak_m}m peak
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
      {/* PAGE 2: Disclaimer                                                   */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <Text style={s.logo}>PlotDetect</Text>

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
          resolution. Small water bodies below detection threshold may not be captured.
        </Text>
        <Text style={[s.bodyText, { color: GRAY_500 }]}>
          Report generated by PlotDetect · plotdetect.com.au · {data.run_date}
        </Text>

        <Footer pageNum={2} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 3: Aerial tile (optional)                                       */}
      {/* ------------------------------------------------------------------ */}
      {data.tile_b64 && (
        <Page size="A4" style={s.page}>
          <Text style={s.logo}>PlotDetect</Text>
          <Text style={s.sectionTitle}>Property aerial view</Text>
          <Text style={[s.bodyText, { color: GRAY_500, marginBottom: 10 }]}>
            Google Maps satellite imagery for context.
          </Text>
          <Image
            src={`data:image/png;base64,${data.tile_b64}`}
            style={{ width: '100%', borderRadius: 4 }}
          />
          <Text style={[s.bodyText, { fontSize: 7, color: GRAY_500, marginTop: 6 }]}>
            Imagery © Google Maps · for reference only
          </Text>
          <Footer pageNum={3} total={totalPages} />
        </Page>
      )}

    </Document>
  );
}
