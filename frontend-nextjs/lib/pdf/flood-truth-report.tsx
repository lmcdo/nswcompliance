/**
 * Flood Truth Report PDF
 * Generated server-side via @react-pdf/renderer renderToBuffer().
 * Data passed directly from the flood pipeline response — no DB lookup.
 */

import React from 'react';
import { floodZoneUnavailableMessage } from '@/lib/not-assessed';
import {
  Document,
  Page,
  View,
  Text,
  StyleSheet,
  Image,
} from '@react-pdf/renderer';
import { WhatThisMeans, PlotDetectFooter, AboutPage, ReferralLinks, InsurerChecklist, DataCurrencyTable, QRBlock, PreparedBy } from './shared-components';
import { sarImageryCurrency } from './imagery-currency';
import { AerialWithOverlay } from './map-overlay';

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
  // null / undefined = NOT ASSESSED. Typed explicitly so a reader of this
  // interface cannot assume two states, and so `=== false` stays meaningful.
  in_100yr_flood_zone?: boolean | null;
  in_100yr_flood_zone_unconsulted?: string[] | null;
  flood_studies?: FloodStudyResult[];
  s1_gap_warning: string | null;
  data_currency: string;
  flood_signal: 'none' | 'low' | 'moderate' | 'elevated' | 'unavailable' | null;
  refused?: boolean;
  refused_reason?: string;
  data_gaps?: Array<{ source: string; reason: string }>;
  confidence: string;
  data_sources: string[];
  warnings?: string[];
  is_paid?: boolean;
  lot_polygon?: { type: string; coordinates: number[][][] } | null;
  tile_b64: string | null;
  qr_b64?: string | null;
  shareable_url?: string | null;
  firm_name?: string | null;
}

// ---------------------------------------------------------------------------
// Palette
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

const SIGNAL_META: Record<string, { label: string; sublabel: string; bg: string; color: string }> = {
  none:     { label: 'No flood indicators detected', sublabel: 'No signals across statutory overlay, council flood study, or observed satellite and gauge records', bg: GREEN_LIGHT, color: GREEN },
  low:      { label: 'Low flood signal', sublabel: 'Property is within a statutory flood zone — no observed inundation events on record', bg: AMBER_LIGHT, color: AMBER },
  moderate: { label: 'Moderate flood signal', sublabel: 'One or more sources indicate flood exposure — review the full data before purchasing or developing', bg: ORANGE_LIGHT, color: ORANGE },
  elevated:    { label: 'Elevated flood signal', sublabel: 'Multiple independent sources indicate flood exposure — professional flood study advisable', bg: RED_LIGHT, color: RED },
  unavailable: { label: 'Flood data unavailable', sublabel: 'Statutory flood data could not be retrieved for this address — this does not indicate absence of flood risk', bg: GRAY_100, color: GRAY_500 },
};

const EPI_CLASS_META: Record<string, { label: string }> = {
  high_flood_risk:     { label: 'High flood risk zone' },
  medium_flood_risk:   { label: 'Medium flood risk zone' },
  low_flood_risk:      { label: 'Low flood risk zone' },
  flood_planning_area: { label: 'Flood planning area' },
  none:                { label: 'Not in statutory flood overlay' },
};

const SEVERITY_COLORS = {
  green: GREEN,
  amber: AMBER,
  red: RED,
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
    paddingBottom: 56,
    paddingHorizontal: 48,
    lineHeight: 1.4,
  },
  logo:     { fontSize: 11, fontFamily: 'Helvetica-Bold', color: TEAL },
  logoRow:  { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 32 },
  logoImg:  { width: 18, height: 18 },
  h1:       { fontSize: 22, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 6 },
  subhead:  { fontSize: 11, color: GRAY_700, marginBottom: 3 },
  dateText: { fontSize: 9, color: GRAY_500, marginBottom: 16 },
  badge: {
    paddingVertical: 5, paddingHorizontal: 12,
    borderRadius: 4, alignSelf: 'flex-start', marginBottom: 6,
  },
  badgeText: { fontSize: 11, fontFamily: 'Helvetica-Bold' },
  badgeSub:  { fontSize: 8, marginTop: 2 },
  sectionTitle: {
    fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_500,
    textTransform: 'uppercase', letterSpacing: 0.8,
    marginTop: 16, marginBottom: 8,
  },
  divider: { borderBottom: `1 solid ${GRAY_300}`, marginVertical: 12 },
  bodyText: { fontSize: 8.5, color: GRAY_700, lineHeight: 1.5, marginBottom: 6 },
  footer: {
    position: 'absolute', bottom: 28, left: 48, right: 48,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  footerText: { fontSize: 7, color: GRAY_500 },
});

// ---------------------------------------------------------------------------
// Findings row (matches frontend pattern)
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

// ---------------------------------------------------------------------------
// Paid section header
// ---------------------------------------------------------------------------

function PaidSectionHeader({ title }: { title: string }) {
  return (
    <View style={{
      flexDirection: 'row', alignItems: 'center', gap: 6,
      backgroundColor: '#f0fdfa', borderRadius: 3,
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
// Build findings from data (mirrors FloodCard logic)
// ---------------------------------------------------------------------------

function buildFindings(data: FloodReportData): Finding[] {
  const findings: Finding[] = [];
  const epiKey = data.epi_flood_class ?? 'none';
  const epiLabel = EPI_CLASS_META[epiKey]?.label ?? epiKey;
  const signal = data.flood_signal ?? 'none';

  // 1. Government flood overlay
  if (epiKey === 'none' && (signal === 'moderate' || signal === 'elevated')) {
    // EPI says clear but other sources indicate flood exposure — contextual wording
    findings.push({
      label: 'NSW EPI Flood WFS',
      value: 'Not in statutory flood overlay',
      detail: 'This property is not in a gazetted flood zone, but other data sources in this report indicate flood exposure. The EPI overlay does not cover all flood-affected areas — absence from the overlay is not clearance.',
      severity: 'amber',
    });
  } else if (epiKey === 'none') {
    findings.push({
      label: 'NSW EPI Flood WFS',
      value: 'Not mapped as flood-prone',
      detail: 'This property is not in a gazetted flood zone under NSW planning instruments. Lenders and insurers typically don\'t flag properties outside this overlay.',
      severity: 'green',
    });
  } else {
    findings.push({
      label: 'NSW EPI Flood WFS',
      value: epiLabel,
      detail: 'This property is inside a gazetted flood zone. Your lender\'s valuer will note this, and insurers will price flood loading into your premium.',
      severity: 'red',
    });
  }

  // 2. 100yr flood zone
  if (data.in_100yr_flood_zone === true) {
    const depth1pct = (data.flood_studies ?? [])
      .flatMap(s => s.design?.['1pct']?.depth_m != null ? [s.design['1pct'].depth_m] : []);
    const maxDepth = depth1pct.length > 0 ? Math.max(...depth1pct) : null;
    findings.push({
      label: 'Council flood study raster',
      value: maxDepth != null
        ? `Within 1-in-100yr flood zone — ${(maxDepth * 100).toFixed(0)}cm depth`
        : 'Within 1-in-100 year flood zone',
      detail: maxDepth != null && maxDepth > 0.5
        ? 'Modelled flood depth exceeds typical floor level for single-storey dwellings. Request a Section 10.7(2) certificate from council ($53) and a flood loading quote from your insurer before exchange.'
        : 'Council flood modelling confirms this site is within the 1-in-100 year flood extent. Obtain a Section 10.7(2) certificate before exchange.',
      severity: 'red',
    });
  } else if (data.in_100yr_flood_zone === false) {
    findings.push({
      label: 'Council flood study raster',
      value: 'Not in 1-in-100 year flood zone',
      detail: 'Flood modelling does not place this property within the 1% AEP flood extent. Ground elevation provides additional clearance from modelled levels.',
      severity: 'green',
    });
  } else {
    // THE THIRD STATE. Before 2026-08-08 this branch did not exist: a null
    // fell through both === comparisons and the finding vanished from the PDF
    // altogether, while the report page rendered the same null as a green
    // 'No'. Neither said that the question had not been answered.
    //
    // It must appear, and it must be amber. A missing row reads as "nothing to
    // report here", which for the flood question is the same lie in quieter
    // clothing.
    findings.push({
      // Source-NEUTRAL label. 'Council flood study raster' would name the
      // wrong source whenever the unreachable one was EPI or the SES overlay
      // — telling the reader a specific falsehood about what failed. The
      // detail sentence names the actual sources.
      label: '1% AEP flood extent',
      value: 'Not assessed — no answer either way',
      detail: floodZoneUnavailableMessage(data.in_100yr_flood_zone_unconsulted),
      severity: 'amber',
    });
  }

  // 3. Ground elevation
  if (data.ground_elevation_m_ahd != null) {
    findings.push({
      label: 'NSW 5m DEM',
      value: `Ground elevation: ${data.ground_elevation_m_ahd.toFixed(1)}m AHD`,
      detail: 'Australian Height Datum elevation at this site. Compare with flood levels in the AEP table — the difference is the depth of water you\'d see during that event.',
      severity: 'green',
    });
  }

  // 4. Satellite water history (DEA WOfS / JRC)
  const waterPct = data.dea_wofs_frequency_pct ?? data.jrc_water_occurrence_pct;
  const waterSource = data.dea_wofs_frequency_pct != null
    ? 'DEA WOfS · Landsat 1987–present'
    : `JRC Global Surface Water · Landsat 1984–${data.jrc_data_year ?? 2021}`;
  if (waterPct != null) {
    if (waterPct === 0) {
      findings.push({
        label: waterSource,
        value: 'No surface water detected since 1987',
        detail: 'Across 37 years of Landsat satellite passes, no surface water has been observed at this location. Strong independent signal of low flood exposure.',
        severity: 'green',
      });
    } else if (waterPct < 5) {
      findings.push({
        label: waterSource,
        value: `Water detected in ${waterPct.toFixed(1)}% of satellite passes`,
        detail: 'Satellites have detected surface water here on rare occasions. Could indicate localised ponding or proximity to a waterway that occasionally overtops.',
        severity: 'amber',
      });
    } else {
      findings.push({
        label: waterSource,
        value: `Water detected in ${waterPct.toFixed(1)}% of satellite passes`,
        detail: 'Satellites regularly detect surface water at this location. This is a strong independent signal of recurring flood exposure.',
        severity: 'red',
      });
    }
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Build paid-only findings
// ---------------------------------------------------------------------------

function buildPaidFindings(data: FloodReportData): Finding[] {
  const findings: Finding[] = [];

  // EMS activations
  if (data.ems_flood_detected === true && data.ems_activations?.length) {
    const events = data.ems_activations;
    findings.push({
      label: 'Copernicus EMS activations',
      value: `${events.length} observed flood event${events.length > 1 ? 's' : ''} on record`,
      detail: events.map(a => `${a.event_name} (${a.event_date})`).join('; '),
      severity: 'red',
    });
  } else if (data.ems_flood_detected === false) {
    findings.push({
      label: 'Copernicus EMS activations',
      value: 'No observed flood events at this location',
      detail: 'Copernicus Emergency Management Service has not recorded a flood activation at this property since records began.',
      severity: 'green',
    });
  }

  // SAR radar
  if (data.sar_flood_detected !== null) {
    findings.push({
      label: `Sentinel-1 SAR${data.sar_analysis_date ? ` · ${data.sar_analysis_date}` : ''}`,
      value: data.sar_flood_detected
        ? `Flood signal detected${data.sar_confidence ? ` — ${data.sar_confidence} confidence` : ''}`
        : 'No flood signal detected',
      detail: data.sar_flood_detected
        ? 'Synthetic Aperture Radar detected standing water at this location during the most recent satellite pass. SAR can see through cloud cover.'
        : 'No standing water detected by SAR imagery. SAR can detect flood inundation even during cloud cover and at night.',
      severity: data.sar_flood_detected ? 'red' : 'green',
    });
  }

  // BOM gauge
  if (data.bom_gauge_name) {
    const distStr = data.bom_gauge_distance_km != null ? data.bom_gauge_distance_km.toFixed(1) : '?';
    if (data.bom_last_major_flood_date) {
      findings.push({
        label: `BOM WaterConnect · ${data.bom_gauge_name} (${distStr}km)`,
        value: `Last major flood: ${data.bom_last_major_flood_date} — ${data.bom_last_major_flood_peak_m?.toFixed(2) ?? '?'}m peak`,
        detail: 'The nearest river gauge recorded a major flood event. If the gauge is within 5km and the property is in the same floodplain, expect similar inundation risk.',
        severity: 'red',
      });
    } else {
      findings.push({
        label: `BOM WaterConnect · ${data.bom_gauge_name} (${distStr}km)`,
        value: 'No major flood recorded since 2021',
        detail: 'The nearest BOM river gauge has not recorded a major flood event in the monitoring period. This doesn\'t rule out older events.',
        severity: 'green',
      });
    }
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function FloodTruthReportDocument({ data }: { data: FloodReportData }) {
  // --- Refused: too few data sources for reliable screening ---
  if (data.refused) {
    return (
      <Document title={`Flood Screening — ${data.address}`} author="PlotDetect">
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />
          <Text style={s.h1}>Flood Data Summary</Text>
          <Text style={s.subhead}>{data.address}</Text>
          <Text style={s.dateText}>Report date: {data.run_date}</Text>

          <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 12, marginTop: 12, marginBottom: 12 }}>
            <Text style={{ fontSize: 12, fontWeight: 700, color: GRAY_900, marginBottom: 4 }}>
              Flood screening could not be generated
            </Text>
            <Text style={{ fontSize: 9, color: GRAY_700, lineHeight: 1.5 }}>
              {data.refused_reason || 'Too few data sources responded to produce a flood screening. Absence of data does not indicate absence of flood risk.'}
            </Text>
          </View>

          {(data.data_gaps ?? []).length > 0 && (
            <View style={{ marginBottom: 12 }}>
              <Text style={{ fontSize: 10, fontWeight: 700, color: GRAY_900, marginBottom: 6 }}>
                Data sources that could not be reached
              </Text>
              {(data.data_gaps ?? []).map((gap, i) => (
                <View key={i} style={{ flexDirection: 'row', marginBottom: 4 }}>
                  <Text style={{ fontSize: 8, color: GRAY_500, width: 8 }}>{'\u2022'}</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: 8, fontWeight: 600, color: GRAY_700 }}>{gap.source}</Text>
                    <Text style={{ fontSize: 7.5, color: GRAY_500, lineHeight: 1.4 }}>{gap.reason}</Text>
                  </View>
                </View>
              ))}
            </View>
          )}

          <View style={{ backgroundColor: AMBER_LIGHT, borderRadius: 4, padding: 8, marginBottom: 12, borderWidth: 1, borderColor: '#fcd34d' }}>
            <Text style={{ fontSize: 8, color: '#92400e', lineHeight: 1.5 }}>
              Contact the local council for a Section 10.7 planning certificate (~$53) or request a flood enquiry letter to confirm the flood status of this property.
            </Text>
          </View>

          <PlotDetectFooter reportName="Flood Truth Report" pageNum={1} total={1} />
        </Page>
      </Document>
    );
  }

  const signal     = data.flood_signal ?? 'none';
  const signalMeta = SIGNAL_META[signal] ?? SIGNAL_META.none;
  const isPaid     = data.is_paid === true;
  const hasStudies = isPaid && (data.flood_studies ?? []).length > 0;
  const hasTile    = !!data.tile_b64;

  // Page count: 1 (cover) + 1? (AEP tables) + 1 (advice) + 1 (about) + 1? (aerial)
  const totalPages = 1 + (hasStudies ? 1 : 0) + 1 + 1 + (hasTile ? 1 : 0);

  const freeFindings = buildFindings(data);
  const paidFindings = isPaid ? buildPaidFindings(data) : [];

  let pageCounter = 0;
  const nextPage = () => ++pageCounter;

  return (
    <Document title={`Flood Truth Report — ${data.address}`} author="PlotDetect">

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + Signal + Findings                                   */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        {/* Title block */}
        <Text style={s.h1}>Flood Data Summary</Text>
        <Text style={s.subhead}>{data.address}</Text>
        {data.lga_name && (
          <Text style={{ fontSize: 9, color: GRAY_500, marginBottom: 2 }}>{data.lga_name} LGA</Text>
        )}
        <Text style={s.dateText}>Report date: {data.run_date}</Text>

        {/* Signal badge + sublabel */}
        <View style={[s.badge, { backgroundColor: signalMeta.bg }]}>
          <Text style={[s.badgeText, { color: signalMeta.color }]}>
            {signalMeta.label}
          </Text>
        </View>
        <Text style={{ fontSize: 8, color: GRAY_700, marginBottom: 12, lineHeight: 1.5 }}>
          {signalMeta.sublabel}
        </Text>

        {/* Data gaps — shown when signal is unavailable */}
        {signal === 'unavailable' && (data.data_gaps ?? []).length > 0 && (
          <View style={{ marginBottom: 8 }}>
            <Text style={{ fontSize: 9, fontWeight: 700, color: GRAY_900, marginBottom: 4 }}>
              Why this data is unavailable
            </Text>
            {(data.data_gaps ?? []).map((gap, i) => (
              <View key={i} style={{ flexDirection: 'row', marginBottom: 3 }}>
                <Text style={{ fontSize: 7.5, color: GRAY_500, width: 8 }}>{'\u2022'}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={{ fontSize: 7.5, fontWeight: 600, color: GRAY_700 }}>{gap.source}</Text>
                  <Text style={{ fontSize: 7, color: GRAY_500, lineHeight: 1.4 }}>{gap.reason}</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Insurance implication — always shown */}
        {signal !== 'none' && signal !== 'unavailable' && (
          <View style={{ backgroundColor: AMBER_LIGHT, borderRadius: 4, padding: 8, marginBottom: 12, borderWidth: 1, borderColor: '#fcd34d' }}>
            <Text style={{ fontSize: 8, color: '#92400e', lineHeight: 1.5 }}>
              Properties with flood indicators typically attract higher building and contents insurance premiums. Request a flood loading quote from your insurer before proceeding with purchase or finance.
            </Text>
          </View>
        )}

        {/* Free findings */}
        <Text style={s.sectionTitle}>Key findings</Text>
        {freeFindings.map((f) => (
          <FindingRow key={f.label} finding={f} />
        ))}

        {/* Paid findings — visually differentiated */}
        {isPaid && paidFindings.length > 0 && (
          <>
            <PaidSectionHeader title="Detailed data — paid report" />
            {paidFindings.map((f) => (
              <FindingRow key={f.label} finding={f} />
            ))}
          </>
        )}

        {/* Warnings */}
        {(data.s1_gap_warning || (data.warnings && data.warnings.length > 0)) && (
          <View style={{ marginTop: 8 }}>
            {!!data.s1_gap_warning && (
              <View style={{ backgroundColor: AMBER_LIGHT, borderLeft: `3 solid ${AMBER}`, paddingVertical: 6, paddingHorizontal: 8, marginBottom: 4, borderRadius: 2 }}>
                <Text style={{ fontSize: 7.5, color: GRAY_700 }}>{data.s1_gap_warning}</Text>
              </View>
            )}
            {data.warnings?.map((w, i) => (
              <View key={i} style={{ backgroundColor: AMBER_LIGHT, borderLeft: `3 solid ${AMBER}`, paddingVertical: 6, paddingHorizontal: 8, marginBottom: 4, borderRadius: 2 }}>
                <Text style={{ fontSize: 7.5, color: GRAY_700 }}>{w}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Data sources pills */}
        <View style={{ marginTop: 10 }}>
          <Text style={{ fontSize: 7, color: GRAY_500, marginBottom: 4 }}>
            Cross-referenced across {data.data_sources.length} independent data sources
          </Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
            {data.data_sources.map((src) => (
              <Text key={src} style={{ backgroundColor: GRAY_100, borderRadius: 3, paddingVertical: 2, paddingHorizontal: 5, fontSize: 6.5, color: GRAY_700 }}>
                {src}
              </Text>
            ))}
          </View>
        </View>

        <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 8, fontStyle: 'italic' }}>
          {'Data valid as of ' + data.run_date + '. Re-run this report if more than 12 months have passed or before exchange of contracts.'}
        </Text>

        <Footer pageNum={nextPage()} total={totalPages} />
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
          '0_1pct': '1-in-1000 yr (0.1% AEP)',
          '0_05pct': '1-in-2000 yr (0.05% AEP)',
          '0_02pct': '1-in-5000 yr (0.02% AEP)',
          'pmf':   'PMF (Probable Maximum Flood)',
        };
        const AEP_ORDER = ['50pct','20pct','10pct','5pct','2pct','1pct','0_5pct','0_2pct','0_1pct','0_05pct','0_02pct','pmf'];
        return (
          <Page size="A4" style={s.page}>
            <LogoRow logo_b64={data.logo_b64} />
            <PaidSectionHeader title="Flood depth and level by AEP event" />
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
                  <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 4 }}>
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

            {/* BOM flood event history table */}
            {data.bom_flood_history && data.bom_flood_history.length > 0 && (
              <View style={{ marginTop: 8 }}>
                <Text style={s.sectionTitle}>BOM gauge flood event history</Text>
                <View style={{ flexDirection: 'row', borderBottom: `1 solid ${GRAY_300}`, paddingVertical: 4 }}>
                  <Text style={{ flex: 2, fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' }}>Date</Text>
                  <Text style={{ flex: 1.5, fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase', textAlign: 'right' }}>Peak height</Text>
                  <Text style={{ flex: 2, fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase', textAlign: 'right' }}>ARI category</Text>
                </View>
                {data.bom_flood_history.slice(0, 5).map((event, i) => (
                  <View key={i} style={{ flexDirection: 'row', borderBottom: `1 solid ${GRAY_300}`, paddingVertical: 5 }}>
                    <Text style={{ flex: 2, fontSize: 8.5, color: GRAY_700 }}>{event.date}</Text>
                    <Text style={{ flex: 1.5, fontSize: 8.5, color: RED, fontFamily: 'Helvetica-Bold', textAlign: 'right' }}>{event.peak_m} m</Text>
                    <Text style={{ flex: 2, fontSize: 8.5, color: GRAY_700, textAlign: 'right' }}>{event.ari_category}</Text>
                  </View>
                ))}
              </View>
            )}

            <Footer pageNum={nextPage()} total={totalPages} />
          </Page>
        );
      })()}

      {/* ------------------------------------------------------------------ */}
      {/* Advice + Referrals + Data Currency page                              */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        {/* Professional referrals */}
        <View style={{ backgroundColor: '#f0fdfa', borderRadius: 4, padding: 10, marginBottom: 12, borderWidth: 1, borderColor: '#99f6e4' }}>
          <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
            Next steps
          </Text>
          <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
            A licensed flood consultant can assess whether this flood classification triggers mandatory disclosure under the Conveyancing (Sale of Land) Regulation 2022. A conveyancer can advise on the impact on contract terms and negotiate appropriate special conditions.
          </Text>
        </View>

        <ReferralLinks links={[
          { label: 'Section 10.7 certificate', url: 'https://www.planningportal.nsw.gov.au/spatialviewer', urlDisplay: 'Council website (via Planning Portal)' },
          { label: 'Flood consultant', url: 'https://www.fma.com.au/find-a-member', urlDisplay: 'fma.com.au/find-a-member' },
          { label: 'Conveyancer', url: 'https://www.aicnsw.com.au/find-a-conveyancer', urlDisplay: 'aicnsw.com.au/find-a-conveyancer' },
        ]} />

        {/* Insurer checklist — paid only */}
        {isPaid && (
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

        {/* Data currency table — paid only */}
        {isPaid && (
          <DataCurrencyTable rows={[
            { source: 'NSW EPI Flood Planning WFS', type: 'Live API query', currency: `Queried ${data.run_date}` },
            { source: 'Council flood study (ARI grids)', type: 'Ingested raster', currency: data.flood_study_date ?? 'See study metadata' },
            { source: 'Copernicus EMS activations', type: 'Live API query', currency: `Queried ${data.run_date}` },
            // 'Most recent pass' implied a SAR analysis that has never run
            // (sar_analysis_date is always null until Phase 3B) — say what is
            // actually true (campaign item 4 / DQ-44).
            { source: 'ESA Sentinel-1 SAR', type: 'Satellite imagery', currency: sarImageryCurrency(data.sar_analysis_date) },
            { source: 'JRC Global Surface Water', type: 'Cached raster', currency: 'Landsat 1984–2024' },
            { source: 'DEA Water Observations (WOfS)', type: 'Cached raster', currency: 'Landsat 1987–2024' },
            { source: 'BoM river gauge network', type: 'Live API query', currency: `Queried ${data.run_date}` },
            { source: 'NSW DEM (ground elevation)', type: 'Cached raster', currency: 'LiDAR 2020–2023' },
          ]} />
        )}

        {/* Disclaimer */}
        <Text style={[s.sectionTitle, { marginTop: 12 }]}>Important limitations</Text>
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
        <Text style={[s.bodyText, { color: GRAY_500 }]}>
          Report generated by PlotDetect · plotdetect.com.au · {data.run_date}
        </Text>

        <Footer pageNum={nextPage()} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* About page                                                           */}
      {/* ------------------------------------------------------------------ */}
      <AboutPage
        logo_b64={data.logo_b64}
        pageNum={nextPage()}
        total={totalPages}
        reportName="Flood Truth Report"
      />

      {/* ------------------------------------------------------------------ */}
      {/* Aerial tile page (only if tile is valid)                             */}
      {/* ------------------------------------------------------------------ */}
      {hasTile && (
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />
          <Text style={s.sectionTitle}>Property aerial view</Text>
          <Text style={[s.bodyText, { color: GRAY_500, marginBottom: 10 }]}>
            NSW SIX Maps aerial imagery for context.
          </Text>
          <AerialWithOverlay
            tile_b64={data.tile_b64!}
            center={[data.lng, data.lat]}
            zoom="property"
            layers={data.lot_polygon ? [
              { geojson: data.lot_polygon, fill: '#0d9488', fillOpacity: 0.15, stroke: '#0d9488', strokeWidth: 2 },
            ] : []}
          />
          <Text style={[s.bodyText, { fontSize: 7, color: GRAY_500, marginTop: 6 }]}>
            © NSW SIX Maps (LPI_Imagery_Best) — CC-BY 4.0 NSW Government · for reference only
          </Text>
          <Footer pageNum={nextPage()} total={totalPages} />
        </Page>
      )}

    </Document>
  );
}
