/**
 * Granny Flat Eligibility Report PDF
 * Generated server-side via @react-pdf/renderer renderToBuffer().
 *
 * Data source: granny_flat_reports table (inputs + outputs columns).
 * SEPP Housing 2021 standards are state-wide uniform — correct for every NSW address.
 */

import React from 'react';
import {
  Document,
  Page,
  View,
  Text,
  StyleSheet,
  Link,
  Image,
} from '@react-pdf/renderer';
import { WhatThisMeans, PlotDetectFooter, AboutPage, ReferralLinks, DataCurrencyTable, QRBlock, PreparedBy } from './shared-components';
import { AerialWithOverlay } from './map-overlay';
import { resolveGrannyReviewState, reviewStateSeverity } from '../granny-flat-review-state';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DCPSetbackEntry {
  type: string;
  requirement: string;
  clause: string;
  notes: string;
}

export interface GrannyFlatReportData {
  address: string;
  run_date: string;
  lat?: number;
  lng?: number;
  // inputs
  lot_area_m2: number | null;
  main_dwelling_area_m2: number | null;
  confirmed_structure_count: number | null;
  // outputs
  granny_flat_buildable: boolean;
  max_floor_area_m2: number;
  estimated_weekly_rent_aud: number | null;
  rental_yield_annual_pct: number | null;
  assumed_build_cost_aud: number | null;
  // Internal grade — retained on the row and in the type because the column
  // is also the job state machine, but NOT rendered on this document.
  confidence: string;
  confidence_reason: string;
  // What actually happened to the structure list. Absent on rows written
  // before 2026-08-06; resolveGrannyReviewState derives those.
  review_state?: string | null;
  review_state_label?: string | null;
  review_state_detail?: string | null;
  samgeo_structure_count?: number | null;
  detected_structures?: unknown[] | null;
  warnings: string[];
  data_sources: string[];
  is_paid?: boolean;
  // aerial tile — base64 PNG from SIX Maps (optional, carried from detect step)
  lot_polygon?: { type: string; coordinates: number[][][] } | null;
  tile_b64: string | null;
  logo_b64?: string | null;
  // LGA + DCP secondary dwelling setbacks
  lga_name?: string | null;
  lga_slug?: string | null;
  dcp_sd_setbacks?: DCPSetbackEntry[] | null;
  dcp_name?: string | null;
  dcp_url?: string | null;
  qr_b64?: string | null;
  firm_name?: string | null;
  shareable_url?: string | null;
}

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

const TEAL        = '#0f766e';
const TEAL_LIGHT  = '#f0fdfa';
const TEAL_BORDER = '#99f6e4';
const RED         = '#dc2626';
const AMBER       = '#d97706';
const GREEN       = '#16a34a';
const GRAY_900    = '#111827';
const GRAY_700    = '#374151';
const GRAY_500    = '#6b7280';
const GRAY_300    = '#d1d5db';
const GRAY_100    = '#f3f4f6';
const WHITE       = '#ffffff';

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
  // Verdict badge
  verdictBadge: {
    paddingVertical: 6, paddingHorizontal: 14, borderRadius: 4,
    alignSelf: 'flex-start', marginBottom: 4,
  },
  verdictText: {
    fontSize: 11, fontFamily: 'Helvetica-Bold', color: WHITE,
  },
  // Table
  tableHeader: {
    flexDirection: 'row', backgroundColor: GRAY_900,
    paddingVertical: 5, paddingHorizontal: 8, borderRadius: 3, marginBottom: 2,
  },
  tableHeaderCell: { color: WHITE, fontSize: 7.5, fontFamily: 'Helvetica-Bold' },
  tableRow: {
    flexDirection: 'row', paddingVertical: 5, paddingHorizontal: 8,
    borderBottomWidth: 1, borderBottomColor: GRAY_100,
  },
  tableRowAlt: { backgroundColor: GRAY_100 },
  tableCell: { fontSize: 8.5, color: GRAY_700 },
  tableCellBold: { fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  // ROI table
  roiRow: {
    flexDirection: 'row', borderBottom: `1 solid ${GRAY_300}`,
    paddingVertical: 6,
  },
  roiLabel: { flex: 2, fontSize: 8.5, color: GRAY_700 },
  roiValue: { flex: 1, fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: GRAY_900, textAlign: 'right' },
});

// ---------------------------------------------------------------------------
// Finding row (matches frontend card pattern)
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
      borderWidth: 1, borderColor: TEAL_BORDER,
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

function fmt(n: number | null | undefined, decimals = 0): string {
  if (n == null) return '-';
  return n.toLocaleString('en-AU', { maximumFractionDigits: decimals });
}

function fmtCurrency(n: number | null | undefined): string {
  if (n == null) return '-';
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(n);
}

function sanitise(str: string): string {
  return str
    .replace(/\u2014/g, ' - ')
    .replace(/\u2013/g, ' - ')
    .replace(/\u2019/g, "'")
    .replace(/\u2018/g, "'")
    .replace(/\u201c/g, '"')
    .replace(/\u201d/g, '"')
    .replace(/[^\x00-\xFF]/g, '');
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

// ---------------------------------------------------------------------------
// Yield sensitivity matrix
// ---------------------------------------------------------------------------

const BUILD_COST_RATES = [2000, 2500, 3000];
const WEEKLY_RENTS = [300, 400, 500];

function yieldMatrix(maxArea: number) {
  return BUILD_COST_RATES.map((rate) =>
    WEEKLY_RENTS.map((rent) => {
      const cost = rate * maxArea;
      const annual = rent * 52;
      return { rate, rent, cost, annual, yield_pct: ((annual / cost) * 100).toFixed(1) };
    })
  );
}

// ---------------------------------------------------------------------------
// Build findings (mirrors frontend card logic)
// ---------------------------------------------------------------------------

function buildFindings(data: GrannyFlatReportData): Finding[] {
  const findings: Finding[] = [];
  const pass = data.granny_flat_buildable;
  const isMultiStructureBlock =
    !pass &&
    (data.confirmed_structure_count ?? 0) >= 3 &&
    data.warnings?.some((w) => w.startsWith('MULTIPLE_SECONDARY_STRUCTURES'));

  // CDC eligibility verdict
  findings.push({
    label: 'SEPP (Housing) 2021 cl 50-58 assessment',
    value: pass
      ? 'Eligible under SEPP Housing 2021 (CDC pathway)'
      : isMultiStructureBlock
      ? 'Eligibility unconfirmed - multiple structures detected'
      : 'Not eligible for CDC pathway',
    detail: pass
      ? 'Based on the data sources checked, this property meets the SEPP Housing 2021 spatial criteria for a secondary dwelling under the Complying Development pathway. A private certifier can verify eligibility and lodge a CDC without council consent.'
      : isMultiStructureBlock
      ? 'Two or more secondary structures were detected. SEPP Housing 2021 (cl 53(1)) only permits one secondary dwelling per lot. A town planner or private certifier must verify before proceeding.'
      : 'This property does not meet one or more requirements for a secondary dwelling under the CDC pathway. A Development Application (DA) to council may still be available.',
    severity: pass ? 'green' : isMultiStructureBlock ? 'amber' : 'red',
  });

  // Lot area
  if (data.lot_area_m2 != null) {
    const lotOk = data.lot_area_m2 >= 450;
    findings.push({
      label: 'NSW Planning Portal - lot boundary data',
      value: `${fmt(data.lot_area_m2)} m\u00B2 lot area`,
      detail: lotOk
        ? 'Lot meets the minimum 450 m\u00B2 requirement for a secondary dwelling under SEPP Housing 2021. No subdivision required.'
        : 'Lot is below the 450 m\u00B2 minimum required under SEPP Housing 2021 for the CDC pathway. A DA may still be possible - consult a town planner.',
      severity: lotOk ? 'green' : 'red',
    });
  }

  // Max floor area (if eligible)
  if (pass && data.max_floor_area_m2 > 0) {
    findings.push({
      label: 'SEPP Housing 2021 cl 4.18 - floor area cap',
      value: `${fmt(data.max_floor_area_m2)} m\u00B2 maximum floor area (CDC)`,
      detail: 'The CDC pathway caps secondary dwellings at 60 m\u00B2. Based on the data sources checked, your lot is within the full allowance. This is the maximum habitable floor area, excluding verandahs, garages, and laundries.',
      severity: 'green',
    });
  }

  // Rental income indicator
  if (pass && data.estimated_weekly_rent_aud != null) {
    const annualRent = data.estimated_weekly_rent_aud * 52;
    const yieldPct = data.rental_yield_annual_pct ?? 0;
    findings.push({
      label: 'NSW Fair Trading Rental Bond Data - comparable 1BR units',
      value: `${fmtCurrency(data.estimated_weekly_rent_aud)}/wk estimated rental income`,
      detail: `Annual gross income of ${fmtCurrency(annualRent)} before vacancy and costs. Gross yield on build cost: ${yieldPct.toFixed(1)}%. Net yield is typically 1-2% lower after management fees and maintenance.`,
      severity: yieldPct >= 6 ? 'green' : yieldPct >= 4 ? 'amber' : 'red',
    });
  }

  // Multi-structure detection
  if ((data.confirmed_structure_count ?? 0) >= 2) {
    findings.push({
      label: 'Satellite structure detection',
      value: `${data.confirmed_structure_count} structures detected on lot`,
      detail: isMultiStructureBlock
        ? 'Multiple secondary structures detected. A town planner or private certifier would need to assess whether an existing structure is already classified as a secondary dwelling before the CDC pathway can proceed.'
        : 'Multiple structures detected but eligibility is not affected. Existing structures may include garages, sheds, or other ancillary buildings that do not count as secondary dwellings.',
      severity: isMultiStructureBlock ? 'amber' : 'green',
    });
  }

  // What happened to the structure list. This finding is ALWAYS pushed —
  // the old version only appeared when the grade was below "high", so a
  // report that had never been checked by anyone and one a person had
  // reviewed were told apart by the PRESENCE of a caveat block. Silence read
  // as the strongest possible statement while asserting nothing that could
  // be held to. The state is stated on every report, including `reviewed`.
  const review = resolveGrannyReviewState(
    data as unknown as Record<string, unknown>,
  );
  findings.push({
    label: 'Structure detection — what was checked',
    value: review.label,
    detail: sanitise(review.detail),
    severity: reviewStateSeverity(review.state),
  });
  // A stored reason on a pre-2026-08-06 row asserts a confirmation that could
  // not have happened ("you confirmed N — counts agree"): the count was seeded
  // from the detector and the control that would change it was never wired.
  // 18 of 20 completed rows carry that phrasing (measured 2026-08-06).
  if (data.confidence_reason && !review.derived) {
    findings.push({
      label: 'Structure count basis',
      value: 'How the count in this report was arrived at',
      detail: sanitise(data.confidence_reason),
      severity: review.state === 'reviewed' ? 'green' : 'amber',
    });
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function GrannyFlatReportDocument({ data }: { data: GrannyFlatReportData }) {
  const pass = data.granny_flat_buildable;
  const isPaid = data.is_paid === true;
  const isMultiStructureBlock =
    !pass &&
    (data.confirmed_structure_count ?? 0) >= 3 &&
    data.warnings?.some((w) => w.startsWith('MULTIPLE_SECONDARY_STRUCTURES'));
  const matrix = pass ? yieldMatrix(data.max_floor_area_m2) : null;
  const hasTile = !!data.tile_b64;
  const hasDCP = isPaid && data.dcp_sd_setbacks && data.dcp_sd_setbacks.length > 0;

  const formattedDate = (() => {
    try {
      return new Date(data.run_date).toLocaleDateString('en-AU', {
        day: 'numeric', month: 'long', year: 'numeric',
      });
    } catch {
      return data.run_date;
    }
  })();

  const findings = buildFindings(data);

  // User-facing warnings (filter out internal sentinel tags)
  const userWarnings = data.warnings
    ?.filter((w) => !w.includes('Run services/') && !w.includes('Run scripts/') && !w.startsWith('MULTIPLE_SECONDARY_STRUCTURES'))
    ?? [];

  let pageCounter = 0;
  const nextPage = () => ++pageCounter;

  return (
    <Document
      title={`Granny Flat Report - ${data.address}`}
      author="PlotDetect"
    >
      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + Verdict + Findings                                  */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        <Text style={s.h1}>Granny Flat Eligibility Report</Text>
        <Text style={s.subhead}>{data.address}</Text>
        {data.lga_name && (
          <Text style={{ fontSize: 9, color: GRAY_500, marginBottom: 2 }}>{data.lga_name} LGA</Text>
        )}
        <Text style={s.dateText}>Report date: {formattedDate}</Text>
        <PreparedBy firmName={data.firm_name} />

        {/* Verdict badge */}
        <View style={[
          s.verdictBadge,
          { backgroundColor: pass ? TEAL : isMultiStructureBlock ? AMBER : RED },
        ]}>
          <Text style={s.verdictText}>
            {pass
              ? 'Eligible under SEPP Housing 2021'
              : isMultiStructureBlock
              ? 'Eligibility unconfirmed'
              : 'Not eligible (CDC pathway)'}
          </Text>
        </View>

        {/* Warnings */}
        {userWarnings.map((w, i) => (
          <Text key={i} style={{ fontSize: 8, color: AMBER, marginBottom: 3 }}>
            {sanitise(w)}
          </Text>
        ))}

        {/* Key findings */}
        <Text style={s.sectionTitle}>Key findings</Text>
        {findings.map((f) => (
          <FindingRow key={f.label} finding={f} />
        ))}

        {/* Data sources */}
        <View style={{ marginTop: 10 }}>
          <Text style={{ fontSize: 7, color: GRAY_500 }}>
            Data sources: {data.data_sources?.join(' · ') || 'NSW Planning Portal · NSW SIX Maps · NSW Fair Trading Rental Bond Data'}
          </Text>
        </View>

        <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 6, fontStyle: 'italic' }}>
          {'Data valid as of ' + data.run_date + '. SEPP Housing 2021 is a state-wide instrument - re-run this report if the SEPP has been amended or before engaging a private certifier.'}
        </Text>

        <PlotDetectFooter reportName="Granny Flat Eligibility Report" pageNum={nextPage()} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 2: Paid detail OR free upsell                                  */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        {isPaid ? (
          <>
            {/* --- Income potential (paid, eligible + rent data) --- */}
            {pass && data.estimated_weekly_rent_aud != null && (
              <>
                <PaidSectionHeader title="Income potential - detailed data" />
                <View style={s.roiRow}>
                  <Text style={s.roiLabel}>Estimated weekly rent</Text>
                  <Text style={[s.roiValue, { color: GREEN }]}>{fmtCurrency(data.estimated_weekly_rent_aud)}/wk</Text>
                </View>
                <View style={s.roiRow}>
                  <Text style={s.roiLabel}>Annual gross income</Text>
                  <Text style={[s.roiValue, { color: GREEN }]}>{fmtCurrency(data.estimated_weekly_rent_aud * 52)}</Text>
                </View>
                <View style={s.roiRow}>
                  <Text style={s.roiLabel}>Gross yield (on build cost)</Text>
                  <Text style={s.roiValue}>
                    {data.rental_yield_annual_pct != null ? `${data.rental_yield_annual_pct.toFixed(1)}%` : '-'}
                  </Text>
                </View>
                <View style={[s.roiRow, { borderBottom: `2 solid ${GRAY_300}` }]}>
                  <Text style={[s.roiLabel, { fontFamily: 'Helvetica-Bold' }]}>Assumed build cost</Text>
                  <Text style={s.roiValue}>{fmtCurrency(data.assumed_build_cost_aud)}</Text>
                </View>
                <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 4, marginBottom: 8 }}>
                  Rent estimate based on NSW Fair Trading rental bond data for comparable 1-bedroom units.
                  Yield is gross before vacancy, management fees, and maintenance. Net yield typically 1-2% lower.
                </Text>
              </>
            )}

            {/* --- 10-Year ROI (paid, eligible + rent data) --- */}
            {pass && data.estimated_weekly_rent_aud != null && data.assumed_build_cost_aud != null && (() => {
              const annualRent = data.estimated_weekly_rent_aud! * 52;
              const buildCost = data.assumed_build_cost_aud!;
              const years = [1, 2, 3, 5, 7, 10];
              const rows = years.map(yr => ({
                yr,
                cumulative: Math.round(annualRent * yr),
                net: Math.round(annualRent * yr - buildCost),
              }));
              const breakEven = years.find(yr => annualRent * yr >= buildCost);
              return (
                <View style={{ marginTop: 4 }}>
                  <Text style={[s.sectionTitle, { marginTop: 8 }]}>10-year return on investment</Text>
                  <View style={s.tableHeader}>
                    <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Year</Text>
                    <Text style={{ ...s.tableHeaderCell, flex: 2, textAlign: 'right' }}>Cumul. income</Text>
                    <Text style={{ ...s.tableHeaderCell, flex: 2, textAlign: 'right' }}>Net position</Text>
                  </View>
                  {rows.map(({ yr, cumulative, net }) => {
                    const isBreakEven = yr === breakEven;
                    const netColor = net >= 0 ? GREEN : GRAY_700;
                    return (
                      <View key={yr} style={[s.tableRow, isBreakEven ? { backgroundColor: TEAL_LIGHT } : {}]}>
                        <Text style={{ ...s.tableCell, flex: 1 }}>
                          Yr {yr}{isBreakEven ? ' (break-even)' : ''}
                        </Text>
                        <Text style={{ ...s.tableCell, flex: 2, textAlign: 'right' }}>
                          {fmtCurrency(cumulative)}
                        </Text>
                        <Text style={{ ...s.tableCellBold, flex: 2, textAlign: 'right', color: netColor }}>
                          {net >= 0 ? '+' : ''}{fmtCurrency(net)}
                        </Text>
                      </View>
                    );
                  })}
                  <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 4 }}>
                    Net position = cumulative rent income minus assumed build cost of {fmtCurrency(buildCost)}.
                    Excludes vacancy, management fees, and maintenance.
                  </Text>
                </View>
              );
            })()}

            {/* --- Yield sensitivity (paid, eligible) --- */}
            {pass && matrix && (
              <View style={{ marginTop: 8 }}>
                <Text style={s.sectionTitle}>Yield sensitivity analysis</Text>
                <Text style={s.bodyText}>
                  Gross annual yield at different build rate ($/m{'\u00B2'}) and weekly rent assumptions.
                  CDC max floor area: <Text style={{ fontFamily: 'Helvetica-Bold' }}>{fmt(data.max_floor_area_m2)} m{'\u00B2'}</Text>.
                </Text>
                {/* Column headers */}
                <View style={{ flexDirection: 'row', marginBottom: 2 }}>
                  <View style={{ flex: 1.2, padding: 6, backgroundColor: GRAY_900, borderRadius: 3 }}>
                    <Text style={{ color: WHITE, fontSize: 7.5, fontFamily: 'Helvetica-Bold' }}>Build rate / Rent</Text>
                  </View>
                  {WEEKLY_RENTS.map((r) => (
                    <View key={r} style={{ flex: 1, padding: 6, backgroundColor: GRAY_900, marginLeft: 2 }}>
                      <Text style={{ color: WHITE, fontSize: 7.5, fontFamily: 'Helvetica-Bold', textAlign: 'center' }}>${r}/wk</Text>
                    </View>
                  ))}
                </View>
                {matrix.map((row, ri) => (
                  <View key={ri} style={{ flexDirection: 'row', marginBottom: 2 }}>
                    <View style={{ flex: 1.2, padding: 6, backgroundColor: GRAY_100, borderRadius: 3 }}>
                      <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_700 }}>
                        ${BUILD_COST_RATES[ri].toLocaleString()}/m{'\u00B2'}
                      </Text>
                      <Text style={{ fontSize: 7, color: GRAY_500 }}>
                        Build: {fmtCurrency(BUILD_COST_RATES[ri] * data.max_floor_area_m2)}
                      </Text>
                    </View>
                    {row.map((cell, ci) => (
                      <View
                        key={ci}
                        style={{
                          flex: 1, padding: 6, marginLeft: 2,
                          backgroundColor: parseFloat(cell.yield_pct) >= 8 ? TEAL_LIGHT : GRAY_100,
                          borderRadius: 3,
                        }}
                      >
                        <Text style={{
                          fontSize: 11, fontFamily: 'Helvetica-Bold', textAlign: 'center',
                          color: parseFloat(cell.yield_pct) >= 8 ? TEAL : GRAY_700,
                        }}>
                          {cell.yield_pct}%
                        </Text>
                        <Text style={{ fontSize: 7, color: GRAY_500, textAlign: 'center' }}>
                          ${(cell.annual / 1000).toFixed(1)}k/yr
                        </Text>
                      </View>
                    ))}
                  </View>
                ))}
                <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 6 }}>
                  Gross yield = annual rent / build cost. Excludes DA/CDC fees (~$2,000-$4,500),
                  finance costs, vacancy (~2-4 weeks/year), and ongoing maintenance (~1.5% of value/year).
                </Text>
              </View>
            )}

            {/* --- What this means (paid) --- */}
            {(() => {
              if (pass && data.estimated_weekly_rent_aud != null) {
                return (
                  <WhatThisMeans>
                    {`Based on the data sources checked, this lot meets the SEPP Housing 2021 spatial criteria for a secondary dwelling via the CDC pathway. A private certifier can confirm eligibility (approximately $500), then a draftsperson can prepare CDC-ready drawings (approximately $2,000-$5,000). Estimated rental income: $${data.estimated_weekly_rent_aud}/week.`}
                  </WhatThisMeans>
                );
              }
              if (pass) {
                return (
                  <WhatThisMeans>
                    Based on the data sources checked, this lot meets the SEPP Housing 2021 spatial criteria for a secondary dwelling via the CDC pathway. A private certifier can confirm eligibility (approximately $500), then a draftsperson can prepare CDC-ready drawings (approximately $2,000-$5,000).
                  </WhatThisMeans>
                );
              }
              if (isMultiStructureBlock) {
                return (
                  <WhatThisMeans>
                    Two or more secondary structures were detected on this lot. A town planner or private certifier would need to assess whether an existing structure is already classified as a secondary dwelling before the CDC pathway can proceed.
                  </WhatThisMeans>
                );
              }
              return (
                <WhatThisMeans>
                  This property does not meet CDC pathway requirements. A Development Application (DA) to council may still be possible - consult a town planner who can assess whether a variation or alternative pathway exists.
                </WhatThisMeans>
              );
            })()}
          </>
        ) : (
          <>
            {/* --- Free version upsell --- */}
            <Text style={s.sectionTitle}>Detailed analysis</Text>
            <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 12, marginBottom: 12 }}>
              <Text style={{ fontSize: 9, color: GRAY_700, marginBottom: 6 }}>
                The paid report includes:
              </Text>
              {[
                'Estimated weekly rental income (NSW Fair Trading data)',
                'Annual gross income and gross yield on build cost',
                '10-year return on investment table with break-even point',
                'Yield sensitivity matrix (3 build rates x 3 rent levels)',
                'CDC vs DA approval pathway comparison',
                'SEPP Housing 2021 development standards checklist',
                'Council DCP secondary dwelling setbacks (where available)',
                'Side-by-side CDC vs DCP standards comparison',
                'Step-by-step next actions with cost estimates',
                'Aerial overlay with lot boundary',
              ].map((item) => (
                <View key={item} style={{ flexDirection: 'row', alignItems: 'flex-start', marginBottom: 3 }}>
                  <Text style={{ fontSize: 8, color: TEAL, marginRight: 4 }}>{'\u2022'}</Text>
                  <Text style={{ fontSize: 8, color: GRAY_700 }}>{item}</Text>
                </View>
              ))}
              <Text style={{ fontSize: 8, color: TEAL, fontFamily: 'Helvetica-Bold', marginTop: 6 }}>
                Unlock at plotdetect.com.au - $29
              </Text>
            </View>
          </>
        )}

        <PlotDetectFooter reportName="Granny Flat Eligibility Report" pageNum={nextPage()} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 3: Pathways + Standards + Next Steps (paid) OR About (free)     */}
      {/* ------------------------------------------------------------------ */}
      {isPaid && (
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />

          {/* --- Approval pathways --- */}
          <PaidSectionHeader title="Approval pathways - detailed comparison" />
          <View style={s.tableHeader}>
            <Text style={{ ...s.tableHeaderCell, flex: 1.5 }}>Factor</Text>
            <Text style={{ ...s.tableHeaderCell, flex: 2 }}>CDC (fast-track)</Text>
            <Text style={{ ...s.tableHeaderCell, flex: 2 }}>DA (council)</Text>
          </View>
          {[
            { factor: 'Approving body', cdc: 'Private certifier', da: 'Council' },
            { factor: 'Timeframe', cdc: '10-20 business days', da: '40-60 days (up to 90+)' },
            { factor: 'Application fee', cdc: '~$1,000-$2,500', da: '~$500-$2,000 + certifier' },
            { factor: 'Design flexibility', cdc: 'Must comply with all SEPP standards', da: 'Council may exercise discretion' },
            { factor: 'Max floor area', cdc: '60 m\u00B2', da: 'Subject to DCP' },
            { factor: 'Heritage / flood lots', cdc: 'Excluded (cl 54-58)', da: 'Possible with specialist report' },
            { factor: 'Neighbour notification', cdc: 'Not required', da: 'Required - neighbours can object' },
          ].map((row, i) => (
            <View key={i} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
              <Text style={{ ...s.tableCellBold, flex: 1.5 }}>{row.factor}</Text>
              <Text style={{ ...s.tableCell, flex: 2, color: pass ? TEAL : GRAY_700 }}>{row.cdc}</Text>
              <Text style={{ ...s.tableCell, flex: 2 }}>{row.da}</Text>
            </View>
          ))}

          {/* --- Development standards --- */}
          <Text style={[s.sectionTitle, { marginTop: 16 }]}>
            Development standards{data.lga_name ? ` - ${data.lga_name}` : ''}
          </Text>

          {hasDCP ? (() => {
            const dcpMap: Record<string, { req: string; clause: string; notes: string }> = {};
            for (const sb of data.dcp_sd_setbacks!) {
              const key = sb.type.toLowerCase();
              dcpMap[key] = { req: sb.requirement, clause: sb.clause, notes: sb.notes };
            }
            const rows = [
              { control: 'Maximum floor area', cdc: '60 m\u00B2', dcpKey: 'max floor area' },
              { control: 'Front setback', cdc: 'Not specified', dcpKey: 'front setback' },
              { control: 'Rear setback', cdc: 'Min 3 m', dcpKey: 'rear setback' },
              { control: 'Side setback', cdc: 'Min 0.9 m (1.5 m above 8 m)', dcpKey: 'side setback' },
              { control: 'Separation from dwelling', cdc: 'Min 3 m', dcpKey: 'separation from dwelling' },
              { control: 'Max wall height', cdc: '5 m', dcpKey: 'max height' },
              { control: 'Max roof height', cdc: '8.5 m', dcpKey: 'max roof height' },
              { control: 'Private open space', cdc: 'Min 24 m\u00B2 (3 m dimension)', dcpKey: 'private open space' },
              { control: 'Car parking', cdc: 'Not required', dcpKey: 'car parking' },
              { control: 'Site coverage', cdc: 'Not specified', dcpKey: 'max site coverage' },
              { control: 'Landscaped area', cdc: 'Not specified', dcpKey: 'min landscaped area' },
            ];
            return (
              <>
                <Text style={s.bodyText}>
                  Side-by-side comparison of CDC standards (SEPP Housing 2021) and DA standards ({data.dcp_name || 'local DCP'}).
                </Text>
                <View style={s.tableHeader}>
                  <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Control</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 2 }}>CDC (SEPP)</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 2 }}>DA (Council DCP)</Text>
                </View>
                {rows.map((row, i) => {
                  const dcp = dcpMap[row.dcpKey];
                  if (!dcp && row.cdc === 'Not specified') return null;
                  return (
                    <View key={i} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                      <Text style={{ ...s.tableCellBold, flex: 2 }}>{row.control}</Text>
                      <Text style={{ ...s.tableCell, flex: 2, color: pass ? TEAL : GRAY_700 }}>{row.cdc}</Text>
                      <Text style={{ ...s.tableCell, flex: 2 }}>{dcp ? dcp.req : '-'}</Text>
                    </View>
                  );
                })}
                {data.dcp_sd_setbacks!.some(r => r.notes) && (
                  <View style={{ marginTop: 4 }}>
                    {data.dcp_sd_setbacks!.filter(r => r.notes).map((r, i) => (
                      <Text key={i} style={{ fontSize: 7, color: GRAY_500, marginBottom: 2 }}>
                        {r.type}: {r.notes}
                      </Text>
                    ))}
                  </View>
                )}
                <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 6 }}>
                  CDC = SEPP Housing 2021 Sch 3 Subdiv 4 (statewide). DA = {data.dcp_name || 'local DCP'} (council-specific).
                  {data.dcp_url && ' '}
                  {data.dcp_url && (
                    <Link src={data.dcp_url} style={{ color: TEAL }}>View full DCP</Link>
                  )}
                </Text>
              </>
            );
          })() : (
            <>
              <Text style={s.bodyText}>
                SEPP Housing 2021 standards apply statewide on the CDC pathway.
              </Text>
              <View style={s.tableHeader}>
                <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Standard</Text>
                <Text style={{ ...s.tableHeaderCell, flex: 2 }}>CDC Requirement</Text>
                <Text style={{ ...s.tableHeaderCell, flex: 1.5 }}>Source</Text>
              </View>
              {[
                { std: 'Maximum floor area', req: '60 m\u00B2', clause: 'cl 4.18' },
                { std: 'Rear setback', req: 'Min 3 m', clause: 'Sch 3 Subdiv 4' },
                { std: 'Side setback', req: 'Min 0.9 m (1.5 m above 8 m)', clause: 'Sch 3 Subdiv 4' },
                { std: 'Separation from dwelling', req: 'Min 3 m', clause: 'Sch 3 Subdiv 4' },
                { std: 'Max wall height', req: '5 m', clause: 'Sch 3 Subdiv 4' },
                { std: 'Max roof height', req: '8.5 m', clause: 'Sch 3 Subdiv 4' },
                { std: 'Private open space', req: 'Min 24 m\u00B2 (3 m dimension)', clause: 'Sch 3 Subdiv 4' },
                { std: 'Car parking', req: 'Not required', clause: 'Sch 3 Subdiv 4' },
              ].map((row, i) => (
                <View key={i} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                  <Text style={{ ...s.tableCell, flex: 2 }}>{row.std}</Text>
                  <Text style={{ ...s.tableCellBold, flex: 2 }}>{row.req}</Text>
                  <Text style={{ ...s.tableCell, flex: 1.5, color: GRAY_500, fontSize: 7.5 }}>SEPP Housing 2021 {row.clause}</Text>
                </View>
              ))}
              <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 6 }}>
                Your council DCP may impose different controls on the DA pathway.
              </Text>
            </>
          )}

          {/* --- Next steps --- */}
          <Text style={[s.sectionTitle, { marginTop: 16 }]}>Next steps</Text>
          {(pass ? [
            {
              n: '1',
              title: 'Engage a private certifier for a CDC pre-lodgement check',
              body: 'A certifier can assess whether the SEPP standards are achievable on your specific lot geometry. Most offer a free or low-cost initial consultation.',
            },
            {
              n: '2',
              title: 'Commission a draftsperson or designer',
              body: 'CDC drawings must meet specific SEPP Housing 2021 design requirements. Expect ~$2,000-$5,000 for CDC-ready plans.',
            },
            {
              n: '3',
              title: 'Lodge the CDC',
              body: 'Lodge with your chosen certifier. Approval typically issued within 10-20 business days. No council submission required.',
            },
            {
              n: '4',
              title: 'Construction and occupation certificate',
              body: 'After construction, the certifier issues an Occupation Certificate. The granny flat can then be legally occupied or rented.',
            },
            {
              n: '5',
              title: 'Register for land tax purposes (if renting)',
              body: 'Rental income from a secondary dwelling is assessable. Consult a tax accountant about land tax implications and depreciation.',
            },
          ] : [
            {
              n: '1',
              title: 'Consider the DA pathway',
              body: 'A DA to council may still be possible, particularly if the lot is close to the 450 m\u00B2 minimum or the exclusion is borderline. A town planner can assess the options.',
            },
            {
              n: '2',
              title: 'Consult a town planner',
              body: 'Experienced planners can advise on whether a variation to the CDC standards is achievable under a DA, and whether a planning proposal or boundary adjustment could resolve the exclusion.',
            },
            {
              n: '3',
              title: 'Check adjacent properties',
              // verdict-ok: next-steps advice about OTHER addresses, hedged with "may";
              // asserts nothing about the subject site.
              body: 'Nearby properties with larger lots or different zone/heritage status may be eligible. Use plotdetect.com.au to run checks on alternative addresses.',
            },
          ]).map((step) => (
            <View key={step.n} style={{ position: 'relative', paddingLeft: 26, marginBottom: 12 }}>
              <View style={{
                position: 'absolute', left: 0, top: 1,
                width: 14, height: 14, borderRadius: 7,
                backgroundColor: pass ? TEAL : GRAY_500,
                alignItems: 'center', justifyContent: 'center',
              }}>
                <Text style={{ color: WHITE, fontSize: 7.5, fontFamily: 'Helvetica-Bold' }}>{step.n}</Text>
              </View>
              <Text style={{ fontFamily: 'Helvetica-Bold', fontSize: 9, marginBottom: 3 }}>{step.title}</Text>
              <Text style={{ fontSize: 8.5, color: GRAY_700, lineHeight: 1.5 }}>{step.body}</Text>
            </View>
          ))}

          <ReferralLinks links={[
            { label: 'Private certifier', url: 'https://www.bpb.nsw.gov.au/find-certifier', urlDisplay: 'bpb.nsw.gov.au/find-certifier' },
            { label: 'Town planner', url: 'https://www.planning.org.au/find-a-planner', urlDisplay: 'planning.org.au/find-a-planner' },
          ]} />

          {isPaid && (
            <DataCurrencyTable rows={[
              { source: 'NSW Planning Portal (zones, overlays)', type: 'Live API query', currency: `Queried ${data.run_date}` },
              { source: 'NSW SIX Maps (lot boundaries)', type: 'Live API query', currency: `Queried ${data.run_date}` },
              { source: 'NSW Fair Trading Rental Bond Data', type: 'Cached dataset', currency: 'Latest quarterly release' },
              { source: 'SEPP (Housing) 2021', type: 'Legislative reference', currency: 'Current as at report date' },
              { source: 'NSW Heritage Register', type: 'Live API query', currency: `Queried ${data.run_date}` },
            ]} />
          )}

          {data.qr_b64 && data.shareable_url && (
            <QRBlock url={data.shareable_url} qr_b64={data.qr_b64} />
          )}

          <PlotDetectFooter reportName="Granny Flat Eligibility Report" pageNum={nextPage()} />
        </Page>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Aerial page (optional, when tile available)                         */}
      {/* ------------------------------------------------------------------ */}
      {hasTile && (
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />
          <Text style={s.sectionTitle}>Property aerial view</Text>
          <Text style={[s.bodyText, { color: GRAY_500, marginBottom: 10 }]}>
            10 cm resolution aerial imagery of the subject lot.
          </Text>
          <AerialWithOverlay
            tile_b64={data.tile_b64!}
            center={[data.lng ?? 0, data.lat ?? 0]}
            zoom="property"
            layers={data.lot_polygon ? [
              { geojson: data.lot_polygon, fill: '#0d9488', fillOpacity: 0.15, stroke: '#0d9488', strokeWidth: 2 },
            ] : []}
          />
          <Text style={[s.bodyText, { fontSize: 7, color: GRAY_500, marginTop: 6 }]}>
            NSW SIX Maps (LPI_Imagery_Best) - CC-BY 4.0 NSW Government - for reference only
          </Text>
          <PlotDetectFooter reportName="Granny Flat Eligibility Report" pageNum={nextPage()} />
        </Page>
      )}

      {/* Disclaimer (free) or About page */}
      {!isPaid && (
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />
          <Text style={s.sectionTitle}>Disclaimer and data sources</Text>
          <Text style={s.bodyText}>
            This report is indicative only and does not constitute legal, planning, or financial advice.
            Eligibility indicators are based on automated screening of publicly available data as at the
            report date and may not reflect recent amendments to planning instruments, heritage listings, or
            flood mapping. Always verify with a qualified town planner or private certifier before lodging a
            development application or complying development certificate.
          </Text>
          <Text style={{ fontSize: 7, color: GRAY_500 }}>
            <Text style={{ fontFamily: 'Helvetica-Bold' }}>Data sources: </Text>
            {data.data_sources?.join(' · ') || 'NSW Planning Portal · NSW SIX Maps · NSW Fair Trading Rental Bond Data'}
          </Text>
          <View style={{ marginTop: 6 }}>
            <Text style={{ fontSize: 7, color: GRAY_500 }}>
              <Text style={{ fontFamily: 'Helvetica-Bold' }}>Legislative references: </Text>
              State Environmental Planning Policy (Housing) 2021 · Environmental Planning and Assessment Act 1979 ·
              Environmental Planning and Assessment Regulation 2021
            </Text>
          </View>
          <View style={{
            backgroundColor: TEAL_LIGHT, borderRadius: 4, padding: 10, marginTop: 12,
            borderWidth: 1, borderColor: TEAL_BORDER,
          }}>
            <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
              Get professional advice
            </Text>
            <Text style={s.bodyText}>
              A private certifier experienced in secondary dwellings can assess SEPP compliance and lodge your CDC.
              Visit <Link src="https://plotdetect.com.au" style={{ color: TEAL }}>plotdetect.com.au</Link> to run checks on any NSW address.
            </Text>
          </View>

          <ReferralLinks links={[
            { label: 'Private certifier', url: 'https://www.bpb.nsw.gov.au/find-certifier', urlDisplay: 'bpb.nsw.gov.au/find-certifier' },
            { label: 'Town planner', url: 'https://www.planning.org.au/find-a-planner', urlDisplay: 'planning.org.au/find-a-planner' },
          ]} />

          <PlotDetectFooter reportName="Granny Flat Eligibility Report" pageNum={nextPage()} />
        </Page>
      )}

      {/* About page */}
      <AboutPage
        logo_b64={data.logo_b64}
        pageNum={nextPage()}
        total={pageCounter}
        reportName="Granny Flat Eligibility Report"
      />
    </Document>
  );
}
