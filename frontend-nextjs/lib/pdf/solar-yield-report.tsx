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
import { WhatThisMeans, PlotDetectFooter, AboutPage, ReferralLinks } from './shared-components';

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
  annual_kwh_estimate: number;
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
  tile_b64: string | null;
  logo_b64?: string | null;
}

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

const TEAL        = '#0f766e';
const TEAL_LIGHT  = '#f0fdfa';
const AMBER       = '#d97706';
const AMBER_LIGHT = '#fffbeb';
const GREEN       = '#16a34a';
const RED         = '#dc2626';
const GRAY_900    = '#111827';
const GRAY_700    = '#374151';
const GRAY_500    = '#6b7280';
const GRAY_300    = '#d1d5db';
const GRAY_100    = '#f3f4f6';

const GRADE_COLORS: Record<string, { bg: string; fg: string }> = {
  A: { bg: '#ecfdf5', fg: GREEN  },
  B: { bg: TEAL_LIGHT, fg: TEAL },
  C: { bg: '#fefce8', fg: '#ca8a04' },
  D: { bg: '#fff7ed', fg: AMBER  },
  F: { bg: '#fef2f2', fg: RED    },
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
  // Grade badge
  gradeBadge: {
    width: 60, height: 60, borderRadius: 8,
    alignItems: 'center', justifyContent: 'center', marginBottom: 16,
  },
  gradeLabel: { fontSize: 8, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase', letterSpacing: 0.5 },
  gradeLetter: { fontSize: 30, fontFamily: 'Helvetica-Bold', lineHeight: 1 },
  // Stats grid
  statGrid: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  statCard: {
    flex: 1, backgroundColor: GRAY_100, borderRadius: 4, padding: 10,
  },
  statLabel: { fontSize: 7, color: GRAY_500, marginBottom: 3 },
  statValue: { fontSize: 16, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  statSub:   { fontSize: 7.5, color: GRAY_700, marginTop: 2 },
  // ROI table
  roiRow: {
    flexDirection: 'row', borderBottom: `1 solid ${GRAY_300}`,
    paddingVertical: 6,
  },
  roiLabel: { flex: 2, fontSize: 8.5, color: GRAY_700 },
  roiValue: { flex: 1, fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: GRAY_900, textAlign: 'right' },
  footer: {
    position: 'absolute', bottom: 28, left: 48, right: 48,
    flexDirection: 'row', justifyContent: 'space-between',
  },
  footerText: { fontSize: 7, color: GRAY_500 },
});

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

function ValidityNote({ runDate }: { runDate: string }) {
  return (
    <Text style={{ fontSize: 7.5, color: GRAY_500, marginTop: 6, fontStyle: 'italic' }}>
      {'Data valid as of ' + runDate + '. Google Solar imagery is updated periodically — re-run this report if more than 12 months have passed or if significant works have occurred on the property.'}
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
        An accredited solar installer (Clean Energy Council) can provide a site-specific design and quote. CEC accreditation is required to access the Small-scale Technology Certificate (STC) rebate, which typically reduces system cost by $2,000-$4,000.
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
    <PlotDetectFooter reportName="Solar Potential Assessment" pageNum={pageNum} total={total} />
  );
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function SolarYieldReportDocument({ data }: { data: SolarYieldReportData }) {
  const gradeColors = GRADE_COLORS[data.solar_grade] ?? GRADE_COLORS.C;
  const totalPages  = (data.tile_b64 ? 3 : 2) + 1; // +1 for About page

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

  return (
    <Document title={`Solar Assessment — ${data.address}`} author="PlotDetect">

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + Grade + Financial ROI                               */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />
        <Text style={s.h1}>Solar Potential Assessment</Text>
        <Text style={s.subhead}>{data.address}</Text>
        {data.lga_name && (
          <Text style={{ fontSize: 9, color: '#6b7280', marginBottom: 2 }}>{data.lga_name} LGA</Text>
        )}
        <Text style={s.dateText}>Report date: {data.run_date}</Text>
        <ValidityNote runDate={data.run_date} />

        {/* Grade badge */}
        <View style={[s.gradeBadge, { backgroundColor: gradeColors.bg }]}>
          <Text style={[s.gradeLabel, { color: gradeColors.fg }]}>Grade</Text>
          <Text style={[s.gradeLetter, { color: gradeColors.fg }]}>{data.solar_grade}</Text>
        </View>
        <Text style={[s.bodyText, { marginBottom: 16 }]}>
          {data.solar_grade_reason} · {data.system_kw.toFixed(1)} kW system
          {data.is_heritage ? ' · Heritage area' : ''}
        </Text>

        {/* A1: Plain-English interpretation */}
        {data.is_paid === true && (
          <WhatThisMeans>
            {data.payback_years != null
              ? `This roof is ${data.solar_grade === 'A' || data.solar_grade === 'B' ? 'well-suited' : 'suitable'} for solar. At current NSW retail rates, a ${data.system_kw.toFixed(1)} kW system would pay for itself in approximately ${data.payback_years.toFixed(1)} years. The next step is to get 2-3 quotes from CEC-accredited installers.`
              : `This roof can support a ${data.system_kw.toFixed(1)} kW solar system producing approximately ${Math.round(data.annual_kwh_estimate).toLocaleString('en-AU')} kWh per year. Get 2-3 quotes from CEC-accredited installers for a site-specific assessment.`}
          </WhatThisMeans>
        )}

        <View style={s.divider} />

        {/* Financial ROI */}
        <Text style={s.sectionTitle}>Financial return</Text>
        <View style={s.statGrid}>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Annual savings</Text>
            <Text style={s.statValue}>{fmt$(data.annual_saving_aud)}</Text>
            <Text style={s.statSub}>at current NSW rates</Text>
          </View>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Payback period</Text>
            <Text style={s.statValue}>
              {data.payback_years ? `${data.payback_years.toFixed(1)} yrs` : '—'}
            </Text>
            <Text style={s.statSub}>system cost {fmt$(data.system_cost_aud)}</Text>
          </View>
          <View style={s.statCard}>
            <Text style={s.statLabel}>10-year return</Text>
            <Text style={[s.statValue, {
              color: data.ten_year_return_aud >= 0 ? GREEN : RED,
            }]}>
              {fmt$(data.ten_year_return_aud)}
            </Text>
            <Text style={s.statSub}>after install + inverter</Text>
          </View>
        </View>

        <Text style={[s.bodyText, { fontSize: 7.5, color: GRAY_500 }]}>
          Assumes 32¢/kWh retail (AER DMO 2025–26) · 6¢/kWh feed-in (AER benchmark) ·
          30% self-consumption (ARENA/CSIRO) · $1,000/kW installed after STCs ·
          inverter replacement $2,000 at year 10.
        </Text>

        <Footer pageNum={1} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 2: Roof specs + Disclaimer                                      */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        {/* Roof and system */}
        <Text style={s.sectionTitle}>Roof and system specifications</Text>
        <View style={s.statGrid}>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Maximum panels</Text>
            <Text style={s.statValue}>{data.max_panels}</Text>
            <Text style={s.statSub}>{data.system_kw.toFixed(1)} kW system</Text>
          </View>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Usable roof area</Text>
            <Text style={s.statValue}>{data.max_panel_area_m2} m²</Text>
            <Text style={s.statSub}>of {data.roof_area_m2} m² total</Text>
          </View>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Annual output</Text>
            <Text style={s.statValue}>{Math.round(data.annual_kwh_estimate).toLocaleString('en-AU')}</Text>
            <Text style={s.statSub}>kWh/year</Text>
          </View>
        </View>
        <View style={s.statGrid}>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Best orientation</Text>
            <Text style={[s.statValue, { fontSize: 12 }]}>
              {azimuthLabel(data.best_azimuth_deg)} · {data.best_pitch_deg}° pitch
            </Text>
            <Text style={s.statSub}>{Math.round(data.sunshine_hours_per_year).toLocaleString('en-AU')} hr/yr sunshine</Text>
          </View>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Imagery date</Text>
            <Text style={[s.statValue, { fontSize: 11 }]}>
              {data.imagery_date !== 'unknown' ? data.imagery_date : 'Unknown'}
            </Text>
            <Text style={s.statSub}>Google Solar API</Text>
          </View>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Confidence</Text>
            <Text style={[s.statValue, { fontSize: 12, textTransform: 'capitalize' }]}>
              {data.confidence}
            </Text>
          </View>
        </View>

        {/* Heritage notice */}
        {data.is_heritage && (
          <View style={{
            backgroundColor: AMBER_LIGHT, borderLeft: `3 solid ${AMBER}`,
            paddingVertical: 8, paddingHorizontal: 10, marginBottom: 12, borderRadius: 2,
          }}>
            <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 3 }}>
              Heritage item or conservation area
            </Text>
            <Text style={{ fontSize: 8, color: GRAY_700 }}>
              Solar panels visible from a public place may require council approval under LEP
              cl 5.10. Panels on rear or concealed roof faces are generally approvable.
            </Text>
          </View>
        )}

        {/* Commercial scale notice */}
        {data.is_commercial_scale && (
          <View style={{
            backgroundColor: '#f0f9ff', borderLeft: `3 solid #0284c7`,
            paddingVertical: 8, paddingHorizontal: 10, marginBottom: 12, borderRadius: 2,
          }}>
            <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 3 }}>
              Large-scale roof detected
            </Text>
            <Text style={{ fontSize: 8, color: GRAY_700 }}>
              {`Roof area: ${data.roof_area_m2.toLocaleString('en-AU')} m\u00B2. Results reflect panels within this lot boundary only. Financial figures assume a single-occupant system. A commercial energy assessment is recommended for multi-tenancy or strata sites.`}
            </Text>
          </View>
        )}

        {/* Payback sensitivity — paid */}
        {data.is_paid === true && data.sensitivity && data.sensitivity.length > 0 && (
          <View style={{ marginTop: 8 }}>
            <Text style={s.sectionTitle}>Payback sensitivity — feed-in rate scenarios</Text>
            {/* Header */}
            <View style={[s.roiRow, { borderBottom: `1 solid ${GRAY_300}` }]}>
              <Text style={[s.roiLabel, { fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' }]}>Feed-in rate (¢/kWh)</Text>
              <Text style={[s.roiValue, { fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' }]}>Annual saving</Text>
              <Text style={[s.roiValue, { fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' }]}>Payback</Text>
            </View>
            {data.sensitivity.map((row) => {
              const isCurrent = row.feed_in_rate === 0.06;
              return (
                <View key={row.feed_in_rate} style={[s.roiRow, isCurrent ? { backgroundColor: TEAL_LIGHT } : {}]}>
                  <Text style={[s.roiLabel, isCurrent ? { fontFamily: 'Helvetica-Bold' } : {}]}>
                    {(row.feed_in_rate * 100).toFixed(0)}c{isCurrent ? ' (current AER benchmark)' : ''}
                  </Text>
                  <Text style={[s.roiValue, isCurrent ? { color: GREEN } : {}]}>{fmt$(row.annual_saving)}</Text>
                  <Text style={s.roiValue}>{row.payback_years != null ? `${row.payback_years.toFixed(1)} yrs` : '—'}</Text>
                </View>
              );
            })}
          </View>
        )}

        {/* Monthly output — paid */}
        {data.is_paid === true && data.monthly_kwh && data.monthly_kwh.length === 12 && (
          <View style={{ marginTop: 16 }}>
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

        {/* Battery upgrade callout — PAID */}
        {data.is_paid === true && (() => {
          // With battery: 80% self-consumed at retail, 20% exported at feed-in
          const batteryAnnualSaving = data.annual_kwh_estimate * (0.80 * 0.32 + 0.20 * 0.06);
          const batteryPayback = batteryAnnualSaving > 0
            ? (data.system_cost_aud + 12000) / batteryAnnualSaving
            : null;
          return (
            <View style={{
              backgroundColor: TEAL_LIGHT, borderRadius: 4, padding: 10,
              marginTop: 8, borderWidth: 1, borderColor: '#99f6e4',
            }}>
              <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
                Battery storage upgrade
              </Text>
              <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
                {`With a home battery (~$12,000): self-consumption rises from ~30% to ~80%. Estimated payback reduces to approximately ${batteryPayback != null ? batteryPayback.toFixed(1) : 'N/A'} years. Battery storage also provides grid independence during outages.`}
              </Text>
            </View>
          );
        })()}

        {/* HOB teaser + shadow cross-sell — paid */}
        {data.is_paid === true && data.neighbour_max_height_m != null && data.neighbour_max_height_m > 0 && (
          <View style={{
            backgroundColor: '#fff7ed', borderRadius: 4, padding: 10,
            marginTop: 8, borderWidth: 1, borderColor: '#fed7aa',
          }}>
            <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: '#9a3412', marginBottom: 4 }}>
              Future shading risk
            </Text>
            <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
              {`Neighbouring lots permit buildings up to ${data.neighbour_max_height_m}m under the ${data.lga_name ? `${data.lga_name} ` : ''}LEP. A building at this height to the north could reduce your solar yield by 20-40% during winter months.`}
            </Text>
            <Text style={{ fontSize: 8, color: TEAL, fontFamily: 'Helvetica-Bold', marginTop: 4 }}>
              Run a Shadow Detector check at plotdetect.com.au to assess the impact.
            </Text>
          </View>
        )}

        <View style={s.divider} />

        <ReferralBox />

        {/* A3: Referral directory links */}
        <ReferralLinks links={[
          { label: 'CEC accredited installer', url: 'https://www.cleanenergycouncil.org.au/consumers/find-an-installer', urlDisplay: 'cleanenergycouncil.org.au/find-an-installer' },
          { label: 'Solar quotes comparison', url: 'https://www.solarquotes.com.au', urlDisplay: 'solarquotes.com.au' },
        ]} />

        <Text style={s.sectionTitle}>Disclaimer</Text>
        <Text style={s.bodyText}>
          This report contains indicative estimates only and does not constitute financial
          or energy advice. Actual savings depend on household consumption patterns, tariff
          structure, system orientation, shading, and future energy prices.
        </Text>
        <Text style={s.bodyText}>
          Solar installation on heritage items or within Heritage Conservation Areas may
          require council approval. Consult a heritage consultant before proceeding.
        </Text>
        <Text style={[s.bodyText, { color: GRAY_500 }]}>
          Data: {data.data_sources.join(' · ')} · Report generated {data.run_date} · plotdetect.com.au
        </Text>

        <Footer pageNum={2} total={totalPages} />
      </Page>

      {/* T4: About this report + tools list */}
      <AboutPage
        logo_b64={data.logo_b64}
        pageNum={3}
        total={totalPages}
        reportName="Solar Potential Assessment"
      />

      {/* Aerial tile (optional) */}
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
          <Footer pageNum={4} total={totalPages} />
        </Page>
      )}

    </Document>
  );
}
