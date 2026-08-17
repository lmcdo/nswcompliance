/**
 * Solar Yield Report PDF
 * Generated server-side via @react-pdf/renderer renderToBuffer().
 * Data passed directly from the solar-yield pipeline response.
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
import { WhatThisMeans, PlotDetectFooter, AboutPage, ReferralLinks, DataCurrencyTable, QRBlock, PreparedBy } from './shared-components';
import { solarImageryCurrency } from './imagery-currency';
import { AerialWithOverlay } from './map-overlay';
import { deliveredKwhFrom, deliveryBasisText } from '@/lib/solar/delivered';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SolarYieldReportData {
  address: string;
  run_date: string;
  lat: number;
  lng: number;
  lga_name?: string | null;
  // outputs
  max_panels: number;
  max_panel_area_m2: number;
  annual_kwh_estimate: number;              // DC at the panel, as Google reports it
  annual_kwh_delivered?: number | null;     // after system losses — monetise THIS
  delivery_basis?: string | null;
  sunshine_hours_per_year: number;
  best_pitch_deg: number;
  best_azimuth_deg: number;
  roof_area_m2: number;
  is_heritage: boolean;
  is_commercial_scale: boolean;
  imagery_date: string;
  coverage_available: boolean;
  // financial (pre-computed on route)
  annual_saving_aud: number;
  system_cost_aud: number;
  payback_years: number | null;
  ten_year_return_aud: number;
  system_kw: number;
  solar_grade: string;
  solar_grade_reason: string;
  // paid enhancements
  sensitivity: Array<{ feed_in_rate: number; annual_saving: number; payback_years: number | null }>;
  monthly_kwh: number[] | null;
  neighbour_max_height_m?: number | null;
  is_paid?: boolean;
  // meta
  confidence: string;
  data_sources: string[];
  lot_polygon?: { type: string; coordinates: number[][][] } | null;
  tile_b64: string | null;
  logo_b64?: string | null;
  qr_b64?: string | null;
  firm_name?: string | null;
  shareable_url?: string | null;
}

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

const TEAL        = '#0f766e';
const TEAL_LIGHT  = '#f0fdfa';
const AMBER       = '#d97706';
const AMBER_LIGHT = '#fffbeb';
const GREEN       = '#16a34a';
const GREEN_LIGHT = '#f0fdf4';
const RED         = '#dc2626';
const GRAY_900    = '#111827';
const GRAY_700    = '#374151';
const GRAY_500    = '#6b7280';
const GRAY_300    = '#d1d5db';
const GRAY_100    = '#f3f4f6';

const GRADE_COLORS: Record<string, { bg: string; fg: string }> = {
  A: { bg: '#ecfdf5', fg: GREEN },
  B: { bg: TEAL_LIGHT, fg: TEAL },
  C: { bg: '#fefce8', fg: '#ca8a04' },
  D: { bg: '#fff7ed', fg: AMBER },
  F: { bg: '#fef2f2', fg: RED },
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
  // Grade badge
  gradeBadge: {
    width: 50, height: 50, borderRadius: 6,
    alignItems: 'center', justifyContent: 'center', marginBottom: 8,
  },
  gradeLabel: { fontSize: 7, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase', letterSpacing: 0.5 },
  gradeLetter: { fontSize: 26, fontFamily: 'Helvetica-Bold', lineHeight: 1 },
  // ROI table
  roiRow: {
    flexDirection: 'row', borderBottom: `1 solid ${GRAY_300}`,
    paddingVertical: 6,
  },
  roiLabel: { flex: 2, fontSize: 8.5, color: GRAY_700 },
  roiValue: { flex: 1, fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: GRAY_900, textAlign: 'right' },
});

// ---------------------------------------------------------------------------
// Finding row (matches frontend pattern)
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

function fmt$(n: number) {
  return n.toLocaleString('en-AU', {
    style: 'currency', currency: 'AUD', maximumFractionDigits: 0,
  });
}

const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function azimuthLabel(deg: number): string {
  if (deg >= 337.5 || deg < 22.5) return 'N';
  if (deg < 67.5) return 'NE';
  if (deg < 112.5) return 'E';
  if (deg < 157.5) return 'SE';
  if (deg < 202.5) return 'S';
  if (deg < 247.5) return 'SW';
  if (deg < 292.5) return 'W';
  return 'NW';
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
    <PlotDetectFooter reportName="Solar Potential Assessment" pageNum={pageNum} total={total} />
  );
}

// ---------------------------------------------------------------------------
// Build findings (mirrors ReportCard logic from SolarYieldTool.tsx)
// ---------------------------------------------------------------------------


/** Delivered energy, from the payload if present, derived if not. */
/** Delivered energy, from the payload if usable, derived if not. */
function deliveredKwh(data: SolarYieldReportData): number {
  return deliveredKwhFrom(data.annual_kwh_estimate, data.annual_kwh_delivered) ?? 0;
}

function buildFindings(data: SolarYieldReportData): Finding[] {
  const findings: Finding[] = [];

  // Solar grade
  const gradeDetail: Record<string, string> = {
    A: 'This roof has strong solar potential based on available data. North-facing with ideal pitch and strong sunshine hours — typically considered a premium site by installers.',
    B: 'Good solar potential based on available data. Minor compromises in orientation or pitch, but still a strong candidate for solar installation.',
    C: 'Moderate solar potential. The roof geometry or orientation reduces output compared to ideal. Still viable, but payback period will be longer.',
    D: 'Below-average solar potential. Significant orientation or pitch issues will reduce output. The investment case at current panel prices may be marginal.',
    F: 'Poor solar potential. The roof geometry makes solar panels unlikely to deliver a reasonable return at current prices. A ground-mounted system or different roof face may be worth exploring.',
  };

  findings.push({
    label: 'Solar suitability assessment',
    value: `Grade ${data.solar_grade} — ${data.solar_grade_reason.toLowerCase()}`,
    detail: gradeDetail[data.solar_grade] ?? gradeDetail.C,
    severity: data.solar_grade <= 'B' ? 'green' : data.solar_grade === 'C' ? 'amber' : 'red',
  });

  // Roof orientation
  const northDev = Math.min(data.best_azimuth_deg, 360 - data.best_azimuth_deg);
  if (northDev <= 30) {
    findings.push({
      label: 'Google Solar API — roof geometry',
      value: `${azimuthLabel(data.best_azimuth_deg)}-facing at ${data.best_pitch_deg}° pitch`,
      detail: 'North-facing is ideal for solar in the Southern Hemisphere. Your panels will capture maximum sunlight throughout the day, especially in winter when the sun is lower.',
      severity: 'green',
    });
  } else if (northDev <= 90) {
    findings.push({
      label: 'Google Solar API — roof geometry',
      value: `${azimuthLabel(data.best_azimuth_deg)}-facing at ${data.best_pitch_deg}° pitch`,
      detail: northDev <= 60
        ? 'Partially north-facing. You\'ll lose some output compared to true north, but this is still a viable orientation. East-facing generates more in the morning, west in the afternoon.'
        : 'East or west-facing roof. You\'ll generate around 15–20% less than a north-facing roof. Still viable, but factor the lower yield into your payback calculations.',
      severity: 'amber',
    });
  } else {
    findings.push({
      label: 'Google Solar API — roof geometry',
      value: `${azimuthLabel(data.best_azimuth_deg)}-facing at ${data.best_pitch_deg}° pitch`,
      detail: 'South-facing is the least productive orientation in the Southern Hemisphere. Output could be 30–40% lower than north-facing. Consider panels on a different roof face if available.',
      severity: 'red',
    });
  }

  // Annual output + dollar estimate.
  // The headline is DELIVERED energy, because that is what the meter records
  // and what the dollar figure beside it depends on. Google's DC figure is
  // kept and named, so the reader can see both and check the basis.
  const delivered = deliveredKwh(data);
  const annualDollar = Math.round(delivered * 0.32);
  findings.push({
    label: 'Google Solar building analysis',
    value: `${Math.round(delivered).toLocaleString('en-AU')} kWh/yr delivered from ${data.system_kw.toFixed(1)} kW system`,
    detail: `Your roof can fit ${data.max_panels} panels (${data.max_panel_area_m2} m² of ${data.roof_area_m2} m² total roof area). ${deliveryBasisText(data.annual_kwh_estimate)} At current retail rates the delivered output is worth roughly $${annualDollar.toLocaleString('en-AU')}/yr before feed-in adjustments. An installer's quote will state the figure for the specific hardware.`,
    severity: delivered > 5000 ? 'green' : delivered > 2000 ? 'amber' : 'red',
  });

  // Sunshine hours
  findings.push({
    label: 'Bureau of Meteorology — solar exposure data',
    value: `${data.sunshine_hours_per_year.toLocaleString('en-AU')} sunshine hours per year`,
    detail: data.sunshine_hours_per_year >= 1700
      ? 'Above-average sunshine for NSW. Your panels will perform at or above nameplate capacity for much of the year.'
      : data.sunshine_hours_per_year >= 1500
      ? 'Typical sunshine hours for Sydney metro. Standard solar yield assumptions apply.'
      : 'Below-average sunshine hours. This could be due to local shading, coastal cloud, or valley fog. Factor this into your installer\'s yield estimate.',
    severity: data.sunshine_hours_per_year >= 1700 ? 'green' : data.sunshine_hours_per_year >= 1300 ? 'amber' : 'red',
  });

  // Heritage
  if (data.is_heritage) {
    findings.push({
      label: 'Heritage overlay (LEP cl 5.10)',
      value: 'Heritage item or conservation area',
      detail: 'Solar panels visible from a public place may require council approval. Panels on rear or concealed roof faces are generally approvable — street-facing primary facades are often refused. Check with council before signing an installer contract.',
      severity: 'amber',
    });
  }

  // Commercial scale
  if (data.is_commercial_scale) {
    findings.push({
      label: 'Roof scale classification',
      value: `Large-scale roof — ${data.roof_area_m2.toLocaleString('en-AU')} m²`,
      detail: 'This is a commercial-scale roof. Results reflect panels within this lot boundary only. For multi-tenancy or strata sites, get a commercial energy assessment — residential quotes won\'t cover the full opportunity.',
      severity: 'amber',
    });
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function SolarYieldReportDocument({ data }: { data: SolarYieldReportData }) {
  const gradeColors = GRADE_COLORS[data.solar_grade] ?? GRADE_COLORS.C;
  const isPaid      = data.is_paid === true;
  const hasTile     = !!data.tile_b64;

  // Pages: 1 (cover+findings) + 1 (paid detail OR advice) + 1 (about) + 1? (aerial)
  const totalPages = 1 + 1 + 1 + (hasTile ? 1 : 0);

  if (!data.coverage_available) {
    return (
      <Document title={`Solar Assessment — ${data.address}`} author="PlotDetect">
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />
          <Text style={s.h1}>Solar Potential Assessment</Text>
          <Text style={s.subhead}>{data.address}</Text>
          <Text style={s.dateText}>Report date: {data.run_date}</Text>
          <Text style={s.bodyText}>
            Building-level solar data is not available for this address. Google Solar
            building data currently covers Sydney metro and major NSW cities.
          </Text>
          <Footer pageNum={1} total={1} />
        </Page>
      </Document>
    );
  }

  const findings = buildFindings(data);

  let pageCounter = 0;
  const nextPage = () => ++pageCounter;

  return (
    <Document title={`Solar Assessment — ${data.address}`} author="PlotDetect">

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + Grade + Findings                                    */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />
        <Text style={s.h1}>Solar Potential Assessment</Text>
        <Text style={s.subhead}>{data.address}</Text>
        {data.lga_name && (
          <Text style={{ fontSize: 9, color: GRAY_500, marginBottom: 2 }}>{data.lga_name} LGA</Text>
        )}
        <Text style={s.dateText}>Report date: {data.run_date}</Text>
        <PreparedBy firmName={data.firm_name} />

        {/* Grade badge + system summary */}
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 12 }}>
          <View style={[s.gradeBadge, { backgroundColor: gradeColors.bg }]}>
            <Text style={[s.gradeLabel, { color: gradeColors.fg }]}>Grade</Text>
            <Text style={[s.gradeLetter, { color: gradeColors.fg }]}>{data.solar_grade}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 10, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 3 }}>
              {data.solar_grade_reason}
            </Text>
            <Text style={{ fontSize: 8.5, color: GRAY_700 }}>
              {data.system_kw.toFixed(1)} kW system · {data.max_panels} panels · {Math.round(deliveredKwh(data)).toLocaleString('en-AU')} kWh/yr delivered
            </Text>
          </View>
        </View>

        {/* Key findings */}
        <Text style={s.sectionTitle}>Key findings</Text>
        {findings.map((f) => (
          <FindingRow key={f.label} finding={f} />
        ))}

        {/* Data sources */}
        <View style={{ marginTop: 10 }}>
          <Text style={{ fontSize: 7, color: GRAY_500, marginBottom: 4 }}>
            Data sources: {data.data_sources.join(' · ')}
          </Text>
        </View>

        <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 6, fontStyle: 'italic' }}>
          {'Data valid as of ' + data.run_date + '. Re-run if more than 12 months have passed or if significant works have occurred.'}
        </Text>

        <Footer pageNum={nextPage()} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 2: Financial detail (paid) + Sensitivity + Monthly + Advice     */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        {/* Financial ROI — paid gets full numbers, free gets teaser */}
        {isPaid ? (
          <>
            <PaidSectionHeader title="Financial return — detailed data" />

            {/* ROI table */}
            <View style={s.roiRow}>
              <Text style={s.roiLabel}>Annual savings (at current NSW rates)</Text>
              <Text style={[s.roiValue, { color: GREEN }]}>{fmt$(data.annual_saving_aud)}</Text>
            </View>
            <View style={s.roiRow}>
              <Text style={s.roiLabel}>Estimated system cost (after STCs)</Text>
              <Text style={s.roiValue}>{fmt$(data.system_cost_aud)}</Text>
            </View>
            <View style={s.roiRow}>
              <Text style={s.roiLabel}>Payback period</Text>
              <Text style={s.roiValue}>{data.payback_years ? `${data.payback_years.toFixed(1)} years` : '—'}</Text>
            </View>
            <View style={[s.roiRow, { borderBottom: `2 solid ${GRAY_300}` }]}>
              <Text style={[s.roiLabel, { fontFamily: 'Helvetica-Bold' }]}>10-year net return</Text>
              <Text style={[s.roiValue, { color: data.ten_year_return_aud >= 0 ? GREEN : RED, fontSize: 10 }]}>
                {fmt$(data.ten_year_return_aud)}
              </Text>
            </View>
            <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 4, marginBottom: 12 }}>
              Assumes 32¢/kWh retail (AER DMO 2025–26) · 6¢/kWh feed-in (AER benchmark) ·
              30% self-consumption (ARENA/CSIRO) · $1,000/kW installed after STCs ·
              inverter replacement $2,000 at year 10.
            </Text>

            {/* Payback sensitivity table */}
            {data.sensitivity && data.sensitivity.length > 0 && (
              <View style={{ marginTop: 4 }}>
                <Text style={s.sectionTitle}>Payback sensitivity — feed-in rate scenarios</Text>
                <View style={[s.roiRow, { borderBottom: `1 solid ${GRAY_300}` }]}>
                  <Text style={[s.roiLabel, { fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' }]}>Feed-in rate</Text>
                  <Text style={[s.roiValue, { fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' }]}>Annual saving</Text>
                  <Text style={[s.roiValue, { fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' }]}>Payback</Text>
                </View>
                {data.sensitivity.map((row) => {
                  const isCurrent = row.feed_in_rate === 0.06;
                  return (
                    <View key={row.feed_in_rate} style={[s.roiRow, isCurrent ? { backgroundColor: TEAL_LIGHT } : {}]}>
                      <Text style={[s.roiLabel, isCurrent ? { fontFamily: 'Helvetica-Bold' } : {}]}>
                        {(row.feed_in_rate * 100).toFixed(0)}¢/kWh{isCurrent ? ' (current AER benchmark)' : ''}
                      </Text>
                      <Text style={[s.roiValue, isCurrent ? { color: GREEN } : {}]}>{fmt$(row.annual_saving)}</Text>
                      <Text style={s.roiValue}>{row.payback_years != null ? `${row.payback_years.toFixed(1)} yrs` : '—'}</Text>
                    </View>
                  );
                })}
              </View>
            )}

            {/* Monthly output */}
            {data.monthly_kwh && data.monthly_kwh.length === 12 && (
              <View style={{ marginTop: 12 }}>
                <Text style={s.sectionTitle}>Estimated monthly output (kWh)</Text>
                {[0, 1].map((half) => (
                  <View key={half} style={{ flexDirection: 'row', gap: 4, marginBottom: 4 }}>
                    {MONTH_NAMES.slice(half * 6, half * 6 + 6).map((month, i) => {
                      const idx = half * 6 + i;
                      const val = data.monthly_kwh![idx];
                      return (
                        <View key={month} style={{ flex: 1, backgroundColor: GRAY_100, borderRadius: 3, padding: 5, alignItems: 'center' }}>
                          <Text style={{ fontSize: 7, color: GRAY_500 }}>{month}</Text>
                          <Text style={{ fontSize: 10, fontFamily: 'Helvetica-Bold', color: TEAL, marginTop: 2 }}>{val}</Text>
                        </View>
                      );
                    })}
                  </View>
                ))}
              </View>
            )}

            {/* Battery upgrade callout */}
            {(() => {
              // Delivered, not DC — a battery can only store energy that
              // actually reaches the meter.
              const batteryAnnualSaving = deliveredKwh(data) * (0.80 * 0.32 + 0.20 * 0.06);
              const batteryPayback = batteryAnnualSaving > 0
                ? (data.system_cost_aud + 12000) / batteryAnnualSaving
                : null;
              return (
                <View style={{
                  backgroundColor: TEAL_LIGHT, borderRadius: 4, padding: 10,
                  marginTop: 12, borderWidth: 1, borderColor: '#99f6e4',
                }}>
                  <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
                    Battery storage upgrade
                  </Text>
                  <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
                    {`With a home battery (~$12,000): self-consumption rises from ~30% to ~80%. Estimated payback: approximately ${batteryPayback != null ? batteryPayback.toFixed(1) : 'N/A'} years. Battery storage also provides grid independence during outages.`}
                  </Text>
                </View>
              );
            })()}

            {/* Future shading risk */}
            {data.neighbour_max_height_m != null && data.neighbour_max_height_m > 0 && (
              <View style={{
                backgroundColor: '#fff7ed', borderRadius: 4, padding: 10,
                marginTop: 8, borderWidth: 1, borderColor: '#fed7aa',
              }}>
                <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: '#9a3412', marginBottom: 4 }}>
                  Future shading risk
                </Text>
                <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
                  {`Neighbouring lots permit buildings up to ${data.neighbour_max_height_m}m under the ${data.lga_name ? `${data.lga_name} ` : ''}LEP. A building at this height to the north could reduce your solar yield by 20–40% during winter months.`}
                </Text>
                <Text style={{ fontSize: 8, color: TEAL, fontFamily: 'Helvetica-Bold', marginTop: 4 }}>
                  Run a Shadow Detector check at plotdetect.com.au to assess the impact.
                </Text>
              </View>
            )}
          </>
        ) : (
          <>
            <Text style={s.sectionTitle}>Financial return</Text>
            <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 12, marginBottom: 12 }}>
              <Text style={{ fontSize: 9, color: GRAY_700, marginBottom: 6 }}>
                The paid report includes:
              </Text>
              {[
                'Annual savings at current NSW retail rates',
                'System cost estimate (after STC rebate)',
                'Payback period calculation',
                '10-year net return analysis',
                'Feed-in rate sensitivity table (4 scenarios)',
                'Monthly kWh output breakdown',
                'Battery storage upgrade analysis',
                'Future shading screening',
              ].map((item) => (
                <View key={item} style={{ flexDirection: 'row', alignItems: 'flex-start', marginBottom: 3 }}>
                  <Text style={{ fontSize: 8, color: TEAL, marginRight: 4 }}>•</Text>
                  <Text style={{ fontSize: 8, color: GRAY_700 }}>{item}</Text>
                </View>
              ))}
              <Text style={{ fontSize: 8, color: TEAL, fontFamily: 'Helvetica-Bold', marginTop: 6 }}>
                Unlock at plotdetect.com.au — $19
              </Text>
            </View>
          </>
        )}

        {/* Referral + data currency */}
        <View style={{ backgroundColor: TEAL_LIGHT, borderRadius: 4, padding: 10, marginTop: 8, borderWidth: 1, borderColor: '#99f6e4' }}>
          <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
            Next steps
          </Text>
          <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
            Get 2–3 quotes from CEC-accredited installers. CEC accreditation is required to access the STC rebate, which typically reduces system cost by $2,000–$4,000.
          </Text>
        </View>

        <ReferralLinks links={[
          { label: 'CEC accredited installer', url: 'https://www.cleanenergycouncil.org.au/consumers/find-an-installer', urlDisplay: 'cleanenergycouncil.org.au/find-an-installer' },
          { label: 'Solar quotes comparison', url: 'https://www.solarquotes.com.au', urlDisplay: 'solarquotes.com.au' },
        ]} />

        {isPaid && (
          <DataCurrencyTable rows={[
            // imagery_date was written to the envelope by the backend but
            // never rendered (campaign item 4 census) — the imagery month is
            // the currency that matters for a roof assessment.
            { source: 'Google Solar API (aerial imagery + roof model)', type: 'Satellite/aerial imagery', currency: solarImageryCurrency(data.imagery_date, data.run_date) },
            { source: 'NSW Heritage Register (spatial_overlays)', type: 'PostGIS query', currency: `Queried ${data.run_date}` },
            { source: 'LEP Height of Buildings (spatial_overlays)', type: 'PostGIS query', currency: `Queried ${data.run_date}` },
          ]} />
        )}

        {data.qr_b64 && data.shareable_url && (
          <QRBlock url={data.shareable_url} qr_b64={data.qr_b64} />
        )}

        <Text style={[s.sectionTitle, { marginTop: 8 }]}>Disclaimer</Text>
        <Text style={s.bodyText}>
          This report contains indicative estimates only and does not constitute financial
          or energy advice. Actual savings depend on household consumption patterns, tariff
          structure, system orientation, shading, and future energy prices.
        </Text>
        <Text style={[s.bodyText, { color: GRAY_500 }]}>
          Report generated by PlotDetect · plotdetect.com.au · {data.run_date}
        </Text>

        <Footer pageNum={nextPage()} total={totalPages} />
      </Page>

      {/* About page */}
      <AboutPage
        logo_b64={data.logo_b64}
        pageNum={nextPage()}
        total={totalPages}
        reportName="Solar Potential Assessment"
      />

      {/* Aerial tile (optional) */}
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
