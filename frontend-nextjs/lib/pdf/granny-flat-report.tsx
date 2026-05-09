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
import { WhatThisMeans, PlotDetectFooter, AboutPage, ReferralLinks, DataCurrencyTable } from './shared-components';

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
  confidence: string;
  confidence_reason: string;
  warnings: string[];
  data_sources: string[];
  is_paid?: boolean;
  // aerial tile — base64 PNG from SIX Maps (optional, carried from detect step)
  tile_b64: string | null;
  logo_b64?: string | null;
  // LGA + DCP secondary dwelling setbacks
  lga_name?: string | null;
  lga_slug?: string | null;
  dcp_sd_setbacks?: DCPSetbackEntry[] | null;
  dcp_name?: string | null;
  dcp_url?: string | null;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const TEAL = '#0f766e';
const TEAL_LIGHT = '#f0fdfa';
const TEAL_BORDER = '#99f6e4';
const RED = '#dc2626';
const RED_LIGHT = '#fef2f2';
const AMBER = '#d97706';
const AMBER_LIGHT = '#fffbeb';
const GRAY_900 = '#111827';
const GRAY_700 = '#374151';
const GRAY_500 = '#6b7280';
const GRAY_300 = '#d1d5db';
const GRAY_100 = '#f3f4f6';
const WHITE = '#ffffff';

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
  // Cover
  coverLogo:    { fontSize: 11, fontFamily: 'Helvetica-Bold', color: TEAL },
  coverLogoRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 64 },
  coverLogoImg: { width: 18, height: 18 },
  coverTitle: { fontSize: 22, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 8 },
  coverAddress: { fontSize: 12, color: GRAY_700, marginBottom: 4 },
  coverDate: { fontSize: 9, color: GRAY_500, marginBottom: 48 },
  coverBadgePass: {
    backgroundColor: TEAL, color: WHITE, fontSize: 11, fontFamily: 'Helvetica-Bold',
    paddingVertical: 6, paddingHorizontal: 14, borderRadius: 4, alignSelf: 'flex-start',
  },
  coverBadgeFail: {
    backgroundColor: RED, color: WHITE, fontSize: 11, fontFamily: 'Helvetica-Bold',
    paddingVertical: 6, paddingHorizontal: 14, borderRadius: 4, alignSelf: 'flex-start',
  },
  coverBadgeAmber: {
    backgroundColor: AMBER, color: WHITE, fontSize: 11, fontFamily: 'Helvetica-Bold',
    paddingVertical: 6, paddingHorizontal: 14, borderRadius: 4, alignSelf: 'flex-start',
  },
  coverConfidence: { fontSize: 8, color: GRAY_500, marginTop: 8 },
  // Section
  sectionTitle: {
    fontSize: 10, fontFamily: 'Helvetica-Bold', color: GRAY_900,
    borderBottomWidth: 1, borderBottomColor: GRAY_300, paddingBottom: 4, marginBottom: 10, marginTop: 24,
  },
  // Stat grid
  statRow: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  statBox: {
    flex: 1, backgroundColor: GRAY_100, borderRadius: 4, padding: 10,
  },
  statLabel: { fontSize: 7.5, color: GRAY_500, marginBottom: 3, textTransform: 'uppercase' },
  statValue: { fontSize: 14, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  statSub: { fontSize: 7.5, color: GRAY_500, marginTop: 2 },
  // Callout boxes
  calloutTeal: {
    backgroundColor: TEAL_LIGHT, borderWidth: 1, borderColor: TEAL_BORDER,
    borderRadius: 4, padding: 10, marginBottom: 10,
  },
  calloutRed: {
    backgroundColor: RED_LIGHT, borderWidth: 1, borderColor: '#fecaca',
    borderRadius: 4, padding: 10, marginBottom: 10,
  },
  calloutAmber: {
    backgroundColor: AMBER_LIGHT, borderWidth: 1, borderColor: '#fde68a',
    borderRadius: 4, padding: 10, marginBottom: 10,
  },
  calloutTitle: { fontSize: 9, fontFamily: 'Helvetica-Bold', marginBottom: 4 },
  calloutText: { fontSize: 8.5, color: GRAY_700, lineHeight: 1.5 },
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
  tableCellTeal: { fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL },
  // Checklist
  checkRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 12 },
  checkDot: {
    width: 14, height: 14, borderRadius: 7, backgroundColor: TEAL,
    alignItems: 'center', justifyContent: 'center', marginRight: 8, marginTop: 0.5,
  },
  checkNum: { color: WHITE, fontSize: 7.5, fontFamily: 'Helvetica-Bold' },
  checkText: { flex: 1, fontSize: 8.5, color: GRAY_700, lineHeight: 1.5 },
  checkSub: { fontSize: 7.5, color: GRAY_500, marginTop: 2 },
  // Clause pill
  clause: {
    backgroundColor: GRAY_100, borderRadius: 3, paddingVertical: 1, paddingHorizontal: 4,
    fontSize: 7.5, color: GRAY_700, fontFamily: 'Helvetica-Oblique',
  },
  // Footer
  footer: {
    position: 'absolute', bottom: 20, left: 48, right: 48,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  footerText: { fontSize: 7.5, color: GRAY_500 },
  // Misc
  body: { fontSize: 8.5, color: GRAY_700, lineHeight: 1.6 },
  bold: { fontFamily: 'Helvetica-Bold' },
  spacer: { marginBottom: 8 },
  twoCol: { flexDirection: 'row', gap: 16 },
  col: { flex: 1 },
  row: { flexDirection: 'row', gap: 8 },
  labelGray: { fontSize: 7.5, color: GRAY_500, marginBottom: 1 },
  mb4: { marginBottom: 4 },
  mb8: { marginBottom: 8 },
  mb12: { marginBottom: 12 },
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(n: number | null | undefined, decimals = 0): string {
  if (n == null) return '—';
  return n.toLocaleString('en-AU', { maximumFractionDigits: decimals });
}

function fmtCurrency(n: number | null | undefined): string {
  if (n == null) return '—';
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(n);
}

function confidenceLabel(c: string): string {
  if (c === 'high') return 'High confidence';
  if (c === 'medium') return 'Medium confidence';
  return 'Low confidence';
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
// PDF Document
// ---------------------------------------------------------------------------

function LogoRow({ logo_b64 }: { logo_b64?: string | null }) {
  return (
    <View style={s.coverLogoRow}>
      {logo_b64 ? (
        <Image src={`data:image/png;base64,${logo_b64}`} style={s.coverLogoImg} />
      ) : null}
      <Text style={s.coverLogo}>PlotDetect</Text>
    </View>
  );
}

// Helvetica (react-pdf default) only covers Latin-1. Strip characters outside that range
// so they don't render as garbage glyphs (e.g. em dash -> " - ", smart quotes -> plain).
function ValidityNote({ runDate }: { runDate: string }) {
  return (
    <Text style={{ fontSize: 7.5, color: GRAY_500, marginTop: 6, fontStyle: 'italic' }}>
      {'Data valid as of ' + runDate + '. SEPP Housing 2021 is a state-wide instrument - re-run this report if the SEPP has been amended or before engaging a private certifier.'}
    </Text>
  );
}

function sanitise(str: string): string {
  return str
    .replace(/\u2014/g, ' - ')   // em dash
    .replace(/\u2013/g, ' - ')   // en dash
    .replace(/\u2019/g, "'")     // right single quote
    .replace(/\u2018/g, "'")     // left single quote
    .replace(/\u201c/g, '"')     // left double quote
    .replace(/\u201d/g, '"')     // right double quote
    .replace(/[^\x00-\xFF]/g, ''); // strip any remaining non-Latin-1
}

export function GrannyFlatReportDocument({ data }: { data: GrannyFlatReportData }) {
  const pass = data.granny_flat_buildable;
  // Detect the conservative multi-structure block — distinct from a hard ineligibility
  const isMultiStructureBlock =
    !pass &&
    (data.confirmed_structure_count ?? 0) >= 3 &&
    data.warnings?.some((w) => w.startsWith('MULTIPLE_SECONDARY_STRUCTURES'));
  const matrix = pass ? yieldMatrix(data.max_floor_area_m2) : null;
  const formattedDate = (() => {
    try {
      return new Date(data.run_date).toLocaleDateString('en-AU', {
        day: 'numeric', month: 'long', year: 'numeric',
      });
    } catch {
      return data.run_date;
    }
  })();

  return (
    <Document
      title={`Granny Flat Report — ${data.address}`}
      author="canibuildit.com.au"
      creator="canibuildit.com.au"
    >
      {/* ------------------------------------------------------------------ */}
      {/* Page 1 — Cover + Eligibility + Income                               */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        {/* Logo */}
        <LogoRow logo_b64={data.logo_b64} />

        {/* Title */}
        <Text style={s.coverTitle}>Granny Flat Eligibility Report</Text>
        <Text style={s.coverAddress}>{data.address}</Text>
        <Text style={s.coverDate}>Prepared {formattedDate}</Text>
        <ValidityNote runDate={data.run_date} />

        {/* Verdict badge */}
        <View style={pass ? s.coverBadgePass : isMultiStructureBlock ? s.coverBadgeAmber : s.coverBadgeFail}>
          <Text>
            {pass
              ? 'Eligible under SEPP Housing 2021'
              : isMultiStructureBlock
              ? 'Eligibility unconfirmed - multiple structures detected'
              : 'Not eligible (CDC pathway)'}
          </Text>
        </View>
        <Text style={s.coverConfidence}>{confidenceLabel(data.confidence)}</Text>

        {/* Confidence reason */}
        {data.confidence_reason ? (
          <View style={{ ...s.calloutAmber, marginTop: 12 }}>
            <Text style={s.calloutText}>{sanitise(data.confidence_reason)}</Text>
          </View>
        ) : null}

        {/* Warnings — filter out internal sentinel tags and pipeline messages */}
        {data.warnings
          ?.filter((w) => !w.includes('Run services/') && !w.includes('Run scripts/') && !w.startsWith('MULTIPLE_SECONDARY_STRUCTURES'))
          .map((w, i) => (
            <View key={i} style={{ ...s.calloutAmber, marginTop: 6 }}>
              <Text style={{ ...s.calloutText, color: AMBER }}>{sanitise(w)}</Text>
            </View>
          ))}

        {/* --- Section 1: Eligibility Verdict --- */}
        <Text style={s.sectionTitle}>1. Eligibility Verdict</Text>

        <View style={s.twoCol}>
          <View style={s.col}>
            <Text style={s.labelGray}>CDC pathway</Text>
            <Text style={{ ...s.body, ...s.bold, color: pass ? TEAL : isMultiStructureBlock ? AMBER : RED }}>
              {pass ? 'Eligible' : isMultiStructureBlock ? 'Unconfirmed' : 'Not eligible'}
            </Text>
          </View>
          {data.lot_area_m2 != null && (
            <View style={s.col}>
              <Text style={s.labelGray}>Lot area</Text>
              <Text style={{ ...s.body, ...s.bold }}>{fmt(data.lot_area_m2)} m²</Text>
            </View>
          )}
          {data.max_floor_area_m2 > 0 && pass && (
            <View style={s.col}>
              <Text style={s.labelGray}>Max floor area (CDC)</Text>
              <Text style={{ ...s.body, ...s.bold }}>{fmt(data.max_floor_area_m2)} m²</Text>
            </View>
          )}
        </View>

        <View style={s.mb8} />

        <View style={pass ? s.calloutTeal : isMultiStructureBlock ? s.calloutAmber : s.calloutRed}>
          <Text style={{ ...s.calloutTitle, color: pass ? TEAL : isMultiStructureBlock ? AMBER : RED }}>
            {pass
              ? 'SEPP Housing 2021 criteria met'
              : isMultiStructureBlock
              ? 'Manual verification required'
              : 'CDC pathway blocked'}
          </Text>
          <Text style={s.calloutText}>
            {pass
              ? 'This property meets the minimum requirements for a secondary dwelling under the Complying Development pathway (SEPP Housing 2021 cl 50-58). A CDC can be lodged with a private certifier without council consent.'
              : isMultiStructureBlock
              ? 'Two or more secondary structures were detected on this lot. SEPP Housing 2021 (cl 53(1)) only permits one secondary dwelling per lot. Eligibility cannot be confirmed until a town planner or private certifier determines whether either existing structure is already classified as a secondary dwelling. The CDC pathway may be available once this is resolved.'
              : 'This property does not meet one or more requirements for a secondary dwelling under the CDC pathway. A Development Application (DA) to council may still be available — consult a town planner or certifier.'}
          </Text>
        </View>

        {/* A1: Plain-English interpretation */}
        {data.is_paid === true && (() => {
          if (pass && data.estimated_weekly_rent_aud != null) {
            return (
              <WhatThisMeans>
                {`This lot qualifies for a secondary dwelling under the fast-track CDC pathway. You do not need council approval. Engage a private certifier for a pre-lodgement check (approximately $500), then a draftsperson for CDC-ready drawings (approximately $2,000-$5,000). Estimated rental income: $${data.estimated_weekly_rent_aud}/week.`}
              </WhatThisMeans>
            );
          }
          if (pass) {
            return (
              <WhatThisMeans>
                This lot qualifies for a secondary dwelling under the fast-track CDC pathway. You do not need council approval. Engage a private certifier for a pre-lodgement check (approximately $500), then a draftsperson for CDC-ready drawings (approximately $2,000-$5,000).
              </WhatThisMeans>
            );
          }
          if (isMultiStructureBlock) {
            return (
              <WhatThisMeans>
                Two or more secondary structures were detected on this lot. A town planner or private certifier needs to determine whether an existing structure is already classified as a secondary dwelling before the CDC pathway can be confirmed.
              </WhatThisMeans>
            );
          }
          return (
            <WhatThisMeans>
              This property does not meet CDC pathway requirements. A Development Application (DA) to council may still be possible — consult a town planner who can assess whether a variation or alternative pathway exists.
            </WhatThisMeans>
          );
        })()}

        {/* --- Section 2: Income Potential --- */}
        {pass && (
          <>
            <Text style={s.sectionTitle}>2. Income Potential</Text>
            {data.is_paid === true ? (
              data.estimated_weekly_rent_aud != null ? (
                <>
                  <View style={s.statRow}>
                    <View style={s.statBox}>
                      <Text style={s.statLabel}>Est. weekly rent</Text>
                      <Text style={s.statValue}>{fmtCurrency(data.estimated_weekly_rent_aud)}/wk</Text>
                      <Text style={s.statSub}>NSW Fair Trading median</Text>
                    </View>
                    <View style={s.statBox}>
                      <Text style={s.statLabel}>Annual gross income</Text>
                      <Text style={s.statValue}>
                        {fmtCurrency(data.estimated_weekly_rent_aud * 52)}
                      </Text>
                      <Text style={s.statSub}>Before vacancy and costs</Text>
                    </View>
                    <View style={s.statBox}>
                      <Text style={s.statLabel}>Gross yield (on build cost)</Text>
                      <Text style={s.statValue}>
                        {data.rental_yield_annual_pct != null ? `${data.rental_yield_annual_pct.toFixed(1)}%` : '—'}
                      </Text>
                      <Text style={s.statSub}>
                        {fmtCurrency(data.assumed_build_cost_aud)} assumed build
                      </Text>
                    </View>
                  </View>
                  <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5 }}>
                    Rent estimate based on NSW Fair Trading rental bond data for comparable 1-bedroom units.
                    Yield is gross before vacancy, management fees, and maintenance. Net yield typically 1–2% lower.
                  </Text>
                </>
              ) : (
                <View style={{ ...s.calloutAmber, marginBottom: 4 }}>
                  <Text style={{ ...s.calloutTitle, color: AMBER }}>Rental data not yet available for this postcode</Text>
                  <Text style={s.calloutText}>
                    NSW Fair Trading rental bond data has not yet been loaded for this area.
                    The yield sensitivity table on page 3 uses benchmark rent assumptions — use those as a guide.
                    Typical 1-bedroom granny flat rents in greater Sydney range from $300–$550/week depending on location and finish.
                  </Text>
                </View>
              )
            ) : (
              <View style={s.statRow}>
                <View style={s.statBox}>
                  <Text style={s.statLabel}>Est. weekly rent</Text>
                  <Text style={{ fontSize: 9, color: GRAY_500, marginTop: 2 }}>Calculated</Text>
                  <Text style={{ fontSize: 7.5, color: TEAL, marginTop: 2 }}>Full figures in paid report</Text>
                </View>
                <View style={s.statBox}>
                  <Text style={s.statLabel}>Annual gross income</Text>
                  <Text style={{ fontSize: 9, color: GRAY_500, marginTop: 2 }}>Calculated</Text>
                  <Text style={{ fontSize: 7.5, color: TEAL, marginTop: 2 }}>Full figures in paid report</Text>
                </View>
                <View style={s.statBox}>
                  <Text style={s.statLabel}>Gross yield</Text>
                  <Text style={{ fontSize: 9, color: GRAY_500, marginTop: 2 }}>Calculated</Text>
                  <Text style={{ fontSize: 7.5, color: TEAL, marginTop: 2 }}>Full figures in paid report</Text>
                </View>
              </View>
            )}
          </>
        )}

        {/* Footer */}
        <PlotDetectFooter reportName="Granny Flat Eligibility Report" />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* Page 2 — SEPP Standards + Pathway + Yield Table                     */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>

        {/* --- Section 3: Approval Pathway Comparison --- */}
        <Text style={s.sectionTitle}>3. Approval Pathways</Text>
        <Text style={{ ...s.body, marginBottom: 10 }}>
          {pass
            ? 'This property is eligible for the fast-track CDC pathway. You can also lodge a DA with council if you need more design flexibility.'
            : 'This property is not eligible for CDC. A Development Application (DA) to council may still be possible — consult a town planner.'}
        </Text>
        <View style={s.tableHeader}>
          <Text style={{ ...s.tableHeaderCell, flex: 1.5 }}>Factor</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 2 }}>CDC (fast-track)</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 2 }}>DA (council)</Text>
        </View>
        {[
          { factor: 'Approving body', cdc: 'Private certifier', da: 'Council' },
          { factor: 'Timeframe', cdc: '10–20 business days', da: '40–60 days (up to 90+)' },
          { factor: 'Application fee', cdc: '~$1,000–$2,500', da: '~$500–$2,000 + certifier' },
          { factor: 'Design flexibility', cdc: 'Must comply with all SEPP standards', da: 'Council may exercise discretion' },
          { factor: 'Max floor area', cdc: '60 m²', da: 'Subject to DCP' },
          { factor: 'Heritage / flood lots', cdc: 'Excluded (cl 54–58)', da: 'Possible with specialist report' },
          { factor: 'Neighbour notification', cdc: 'Not required', da: 'Required — neighbours can object' },
        ].map((row, i) => (
          <View key={i} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
            <Text style={{ ...s.tableCellBold, flex: 1.5 }}>{row.factor}</Text>
            <Text style={{ ...s.tableCell, flex: 2, color: pass ? TEAL : GRAY_700 }}>{row.cdc}</Text>
            <Text style={{ ...s.tableCell, flex: 2 }}>{row.da}</Text>
          </View>
        ))}

        {/* --- Section 4: Development Standards by Pathway --- */}
        <Text style={s.sectionTitle}>
          4. Development Standards{data.lga_name ? ` — ${data.lga_name}` : ''}
        </Text>
        <Text style={{ ...s.body, marginBottom: 10 }}>
          {data.is_paid === true && data.dcp_sd_setbacks && data.dcp_sd_setbacks.length > 0
            ? 'Side-by-side comparison of CDC standards (SEPP Housing 2021) and DA standards (your council DCP). CDC standards are statewide. DCP standards are specific to your council.'
            : 'The following SEPP Housing 2021 standards apply to secondary dwellings on the CDC pathway. These are statewide — the same for every NSW address.'}
        </Text>

        {/* Combined comparison table (paid + DCP data) or SEPP-only table */}
        {data.is_paid === true && data.dcp_sd_setbacks && data.dcp_sd_setbacks.length > 0 ? (() => {
          const dcpMap: Record<string, { req: string; clause: string; notes: string }> = {};
          for (const sb of data.dcp_sd_setbacks!) {
            const key = sb.type.toLowerCase();
            dcpMap[key] = { req: sb.requirement, clause: sb.clause, notes: sb.notes };
          }
          const rows = [
            { control: 'Maximum floor area', cdc: '60 m²', dcpKey: 'max floor area' },
            { control: 'Front setback', cdc: 'Not specified', dcpKey: 'front setback' },
            { control: 'Rear setback', cdc: 'Min 3 m', dcpKey: 'rear setback' },
            { control: 'Side setback', cdc: 'Min 0.9 m (1.5 m above 8 m)', dcpKey: 'side setback' },
            { control: 'Separation from dwelling', cdc: 'Min 3 m', dcpKey: 'separation from dwelling' },
            { control: 'Max wall height', cdc: '5 m', dcpKey: 'max height' },
            { control: 'Max roof height', cdc: '8.5 m', dcpKey: 'max roof height' },
            { control: 'Private open space', cdc: 'Min 24 m² (3 m dimension)', dcpKey: 'private open space' },
            { control: 'Car parking', cdc: 'Not required', dcpKey: 'car parking' },
            { control: 'Site coverage', cdc: 'Not specified', dcpKey: 'max site coverage' },
            { control: 'Landscaped area', cdc: 'Not specified', dcpKey: 'min landscaped area' },
          ];
          return (
            <>
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
                    <Text style={{ ...s.tableCell, flex: 2 }}>{dcp ? dcp.req : '—'}</Text>
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
              <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, marginTop: 6 }}>
                CDC = SEPP Housing 2021 Sch 3 Subdiv 4 (statewide).
                DA = {data.dcp_url ? '' : ''}{data.dcp_name || 'local DCP'} (council-specific).
                {data.dcp_url && ' '}
                {data.dcp_url && (
                  <Link src={data.dcp_url} style={{ color: TEAL }}>View full DCP</Link>
                )}
              </Text>
            </>
          );
        })() : (
          <>
            <View style={s.tableHeader}>
              <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Standard</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 2 }}>CDC Requirement</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 1.5 }}>Source</Text>
            </View>
            {[
              { std: 'Maximum floor area', req: '60 m²', clause: 'cl 4.18' },
              { std: 'Rear setback', req: 'Min 3 m', clause: 'Sch 3 Subdiv 4' },
              { std: 'Side setback', req: 'Min 0.9 m (1.5 m above 8 m)', clause: 'Sch 3 Subdiv 4' },
              { std: 'Separation from dwelling', req: 'Min 3 m', clause: 'Sch 3 Subdiv 4' },
              { std: 'Max wall height', req: '5 m', clause: 'Sch 3 Subdiv 4' },
              { std: 'Max roof height', req: '8.5 m', clause: 'Sch 3 Subdiv 4' },
              { std: 'Private open space', req: 'Min 24 m² (3 m dimension)', clause: 'Sch 3 Subdiv 4' },
              { std: 'Car parking', req: 'Not required', clause: 'Sch 3 Subdiv 4' },
            ].map((row, i) => (
              <View key={i} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                <Text style={{ ...s.tableCell, flex: 2 }}>{row.std}</Text>
                <Text style={{ ...s.tableCellBold, flex: 2 }}>{row.req}</Text>
                <Text style={{ ...s.tableCell, flex: 1.5, color: GRAY_500, fontSize: 7.5 }}>SEPP Housing 2021 {row.clause}</Text>
              </View>
            ))}
            <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, marginTop: 6 }}>
              SEPP Housing 2021 standards apply statewide on the CDC pathway.
              Your council DCP may impose different controls on the DA pathway.
            </Text>
          </>
        )}

        {/* Footer */}
        <PlotDetectFooter reportName="Granny Flat Eligibility Report" />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* Aerial Page — only rendered when tile_b64 is available              */}
      {/* ------------------------------------------------------------------ */}
      {data.tile_b64 && (
        <Page size="A4" style={s.page}>
          <Text style={s.sectionTitle}>Property Aerial View</Text>
          <Text style={{ ...s.body, color: GRAY_500, marginBottom: 10 }}>
            10 cm resolution aerial imagery of the subject lot.
          </Text>
          <Image
            src={`data:image/png;base64,${data.tile_b64}`}
            style={{ width: '100%', borderRadius: 4 }}
          />
          <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 6 }}>
            NSW SIX Maps 10 cm imagery — CC-BY 4.0 NSW Government
          </Text>
          <View style={s.footer} fixed>
            <Text style={s.footerText}>canibuildit.com.au — Granny Flat Eligibility Report</Text>
            <Text style={s.footerText} render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`} />
          </View>
        </Page>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Page 3 — Yield Table + Next Steps + Disclaimer                      */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>

        {/* --- Section 5: Yield Sensitivity (pass + paid only) --- */}
        {pass && matrix && data.is_paid === true && (
          <>
            <Text style={s.sectionTitle}>5. Yield Sensitivity Analysis</Text>
            <Text style={{ ...s.body, marginBottom: 10 }}>
              Gross annual yield on build cost at different build rate ($/m²) and weekly rent assumptions.
              CDC max floor area for this property: <Text style={s.bold}>{fmt(data.max_floor_area_m2)} m²</Text>.
            </Text>

            {/* Column headers */}
            <View style={{ flexDirection: 'row', marginBottom: 2 }}>
              <View style={{ flex: 1.2, padding: 6, backgroundColor: GRAY_900, borderRadius: 3 }}>
                <Text style={{ color: WHITE, fontSize: 7.5, fontFamily: 'Helvetica-Bold' }}>Build rate ↓ / Rent →</Text>
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
                    ${BUILD_COST_RATES[ri].toLocaleString()}/m²
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

            <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, marginTop: 6 }}>
              Gross yield = annual rent ÷ build cost. Excludes DA/CDC fees (~$2,000–$4,500),
              finance costs, vacancy (~2–4 weeks/year), and ongoing maintenance (~1.5% of value/year).
              Net yields typically 1–2% lower.
            </Text>
          </>
        )}

        {/* --- Section 5b: 10-Year ROI table (paid, eligible + rent data only) --- */}
        {pass && data.is_paid === true && data.estimated_weekly_rent_aud != null && data.assumed_build_cost_aud != null && (() => {
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
            <View style={{ marginTop: 8 }}>
              <Text style={s.sectionTitle}>5b. 10-Year Return on Investment</Text>
              {/* Header */}
              <View style={[s.tableHeader]}>
                <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Year</Text>
                <Text style={{ ...s.tableHeaderCell, flex: 2, textAlign: 'right' }}>Cumul. income</Text>
                <Text style={{ ...s.tableHeaderCell, flex: 2, textAlign: 'right' }}>Net position</Text>
              </View>
              {rows.map(({ yr, cumulative, net }) => {
                const isBreakEven = yr === breakEven;
                const netColor = net >= 0 ? '#16a34a' : GRAY_700;
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
              <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, marginTop: 4 }}>
                Net position = cumulative rent income minus assumed build cost of {fmtCurrency(buildCost)}.
                Excludes vacancy, management fees, and maintenance costs.
              </Text>
            </View>
          );
        })()}

        {/* --- Section 6: Next Steps --- */}
        <Text style={s.sectionTitle}>{pass ? '6.' : '5.'} Next Steps</Text>

        {pass ? (
          <>
            {[
              {
                n: '1',
                title: 'Engage a private certifier for a CDC pre-lodgement check',
                body: 'A certifier will confirm the SEPP standards are achievable on your specific lot geometry before you commit to design fees. Most offer a free or low-cost initial consultation.',
              },
              {
                n: '2',
                title: 'Commission a draftsperson or designer',
                body: 'CDC drawings must meet specific SEPP Housing 2021 design requirements. A draftsperson experienced in secondary dwellings can prepare CDC-ready plans for ~$2,000–$5,000.',
              },
              {
                n: '3',
                title: 'Lodge the CDC',
                body: 'Lodge with your chosen certifier. Approval typically issued within 10–20 business days. No council submission required for the CDC pathway.',
              },
              {
                n: '4',
                title: 'Construction and occupation certificate',
                body: 'After construction, the certifier issues an Occupation Certificate. The granny flat can then be legally occupied or rented.',
              },
              {
                n: '5',
                title: 'Register for land tax purposes (if renting)',
                body: 'Rental income from a secondary dwelling is assessable income. Consult a tax accountant about land tax implications and depreciation schedules.',
              },
            ].map((step) => (
              <View key={step.n} style={{ position: 'relative', paddingLeft: 26, marginBottom: 16 }}>
                <View style={{ position: 'absolute', left: 0, top: 1, ...s.checkDot }}>
                  <Text style={s.checkNum}>{step.n}</Text>
                </View>
                <Text style={{ fontFamily: 'Helvetica-Bold', fontSize: 9, marginBottom: 4 }}>{step.title}</Text>
                <Text style={{ fontSize: 8.5, color: GRAY_700, lineHeight: 1.5 }}>{step.body}</Text>
              </View>
            ))}
          </>
        ) : (
          <>
            {[
              {
                n: '1',
                title: 'Consider the DA pathway',
                body: 'A Development Application to council may still be possible, particularly if the lot is close to the 450 m² minimum or the exclusion is a borderline heritage or flood zone issue. A town planner can assess feasibility.',
              },
              {
                n: '2',
                title: 'Consult a town planner',
                body: 'Experienced town planners can advise on whether a variation to the CDC standards is achievable under a DA, and whether a planning proposal or boundary adjustment could resolve the exclusion.',
              },
              {
                n: '3',
                title: 'Check adjacent properties',
                body: 'Nearby properties with larger lots or different zone/heritage status may be eligible. Use the canibuildit.com.au tool on alternative addresses.',
              },
            ].map((step) => (
              <View key={step.n} style={{ position: 'relative', paddingLeft: 26, marginBottom: 16 }}>
                <View style={{ position: 'absolute', left: 0, top: 1, ...s.checkDot, backgroundColor: GRAY_500 }}>
                  <Text style={s.checkNum}>{step.n}</Text>
                </View>
                <Text style={{ fontFamily: 'Helvetica-Bold', fontSize: 9, marginBottom: 4 }}>{step.title}</Text>
                <Text style={{ fontSize: 8.5, color: GRAY_700, lineHeight: 1.5 }}>{step.body}</Text>
              </View>
            ))}
          </>
        )}

        {/* --- Disclaimer --- */}
        <Text style={s.sectionTitle}>Disclaimer and Data Sources</Text>
        <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, lineHeight: 1.6 }}>
          This report is indicative only and does not constitute legal, planning, or financial advice.
          Eligibility determinations are based on automated analysis of publicly available data as at the
          report date and may not reflect recent amendments to planning instruments, heritage listings, or
          flood mapping. Always verify with a qualified town planner or private certifier before lodging a
          development application or complying development certificate.
        </Text>
        <View style={s.mb8} />
        <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5 }}>
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>Data sources: </Text>
          {data.data_sources?.join(' · ') || 'NSW Planning Portal · NSW SIX Maps · NSW Fair Trading Rental Bond Data'}
        </Text>
        <View style={s.mb8} />
        <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5 }}>
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>Legislative references: </Text>
          State Environmental Planning Policy (Housing) 2021 · Environmental Planning and Assessment Act 1979 ·
          Environmental Planning and Assessment Regulation 2021
        </Text>
        <View style={s.mb8} />
        <View style={{ backgroundColor: TEAL_LIGHT, borderRadius: 4, padding: 10, marginTop: 8, borderWidth: 1, borderColor: TEAL_BORDER }}>
          <Text style={{ ...s.calloutTitle, color: TEAL, marginBottom: 4 }}>Get professional advice</Text>
          <Text style={{ ...s.calloutText }}>
            A private certifier experienced in secondary dwellings can confirm SEPP compliance and lodge your CDC. A draftsperson can prepare CDC-ready drawings for approximately $2,000-$5,000. Visit{' '}
            <Link src="https://canibuildit.com.au" style={{ color: TEAL }}>canibuildit.com.au</Link>
            {' '}to run checks on any NSW address.
          </Text>
        </View>

        {/* A3: Referral directory links */}
        <ReferralLinks links={[
          { label: 'Private certifier', url: 'https://www.bpb.nsw.gov.au/find-certifier', urlDisplay: 'bpb.nsw.gov.au/find-certifier' },
          { label: 'Town planner', url: 'https://www.planning.org.au/find-a-planner', urlDisplay: 'planning.org.au/find-a-planner' },
        ]} />

        {/* A2: Data currency table — paid only */}
        {data.is_paid === true && (
          <DataCurrencyTable rows={[
            { source: 'NSW Planning Portal (zones, overlays)', type: 'Live API query', currency: `Queried ${data.run_date}` },
            { source: 'NSW SIX Maps (lot boundaries)', type: 'Live API query', currency: `Queried ${data.run_date}` },
            { source: 'NSW Fair Trading Rental Bond Data', type: 'Cached dataset', currency: 'Latest quarterly release' },
            { source: 'SEPP (Housing) 2021', type: 'Legislative reference', currency: 'Current as at report date' },
            { source: 'NSW Heritage Register', type: 'Live API query', currency: `Queried ${data.run_date}` },
          ]} />
        )}

        {/* Footer */}
        <PlotDetectFooter reportName="Granny Flat Eligibility Report" />
      </Page>

      {/* T4: About this report + tools list */}
      <AboutPage
        logo_b64={data.logo_b64}
        pageNum={99}
        total={99}
        reportName="Granny Flat Eligibility Report"
      />
    </Document>
  );
}
