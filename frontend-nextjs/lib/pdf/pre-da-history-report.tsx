/**
 * Pre-DA Site History Report PDF
 * Generated server-side via @react-pdf/renderer renderToBuffer().
 *
 * Data source: pre_da_history_reports.report_json (JSONB).
 * Covers: Tessera cosine similarity 2017–2025, DA events, heritage flag, flood/fire.
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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TimelineEntry {
  year: number;
  level: 'stable' | 'minor' | 'moderate' | 'major' | 'no_data';
  label: string;
  color?: string;
  similarity?: number | null;
  suppressed?: boolean;
  explanation?: string;
  change_type?: string;
  da_events?: string[];
}

export interface PreDAHistoryReportData {
  address: string;
  run_date: string;
  lat: number;
  lon: number;
  council: string | null;
  heritage_flag: boolean;
  heritage_note: string | null;
  timeline: TimelineEntry[];
  wayback_ssim?: Record<string, number>;
  data_quality_note: string;
  logo_b64?: string | null;
}

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

const TEAL      = '#0f766e';
const TEAL_LIGHT = '#f0fdfa';
const TEAL_BORDER = '#99f6e4';
const RED       = '#dc2626';
const RED_LIGHT  = '#fef2f2';
const AMBER     = '#d97706';
const AMBER_LIGHT = '#fffbeb';
const GREEN     = '#16a34a';
const GREEN_LIGHT = '#f0fdf4';
const GRAY_900  = '#111827';
const GRAY_700  = '#374151';
const GRAY_500  = '#6b7280';
const GRAY_300  = '#d1d5db';
const GRAY_100  = '#f3f4f6';
const WHITE     = '#ffffff';

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
  // Logo / cover
  coverLogoRow:  { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 56 },
  coverLogoImg:  { width: 18, height: 18 },
  coverLogo:     { fontSize: 11, fontFamily: 'Helvetica-Bold', color: TEAL },
  coverTitle:    { fontSize: 22, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 8 },
  coverAddress:  { fontSize: 12, color: GRAY_700, marginBottom: 4 },
  coverDate:     { fontSize: 9, color: GRAY_500, marginBottom: 32 },
  coverSubtitle: { fontSize: 9, color: GRAY_500, marginBottom: 4 },
  // Section
  sectionTitle: {
    fontSize: 10, fontFamily: 'Helvetica-Bold', color: GRAY_900,
    borderBottomWidth: 1, borderBottomColor: GRAY_300,
    paddingBottom: 4, marginBottom: 10, marginTop: 24,
  },
  // Stat grid
  statRow:  { flexDirection: 'row', gap: 12, marginBottom: 12 },
  statBox:  { flex: 1, backgroundColor: GRAY_100, borderRadius: 4, padding: 10 },
  statLabel: { fontSize: 7.5, color: GRAY_500, marginBottom: 3, textTransform: 'uppercase' },
  statValue: { fontSize: 14, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  statSub:  { fontSize: 7.5, color: GRAY_500, marginTop: 2 },
  // Callouts
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
  calloutGreen: {
    backgroundColor: GREEN_LIGHT, borderWidth: 1, borderColor: '#bbf7d0',
    borderRadius: 4, padding: 10, marginBottom: 10,
  },
  calloutTitle: { fontSize: 9, fontFamily: 'Helvetica-Bold', marginBottom: 4 },
  calloutText:  { fontSize: 8.5, color: GRAY_700, lineHeight: 1.5 },
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
  tableCell:     { fontSize: 8, color: GRAY_700 },
  tableCellBold: { fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  // Level badge
  badgeGreen:  { backgroundColor: GREEN_LIGHT, color: GREEN, fontSize: 7.5, borderRadius: 3, paddingHorizontal: 4, paddingVertical: 1 },
  badgeAmber:  { backgroundColor: AMBER_LIGHT, color: AMBER, fontSize: 7.5, borderRadius: 3, paddingHorizontal: 4, paddingVertical: 1 },
  badgeOrange: { backgroundColor: '#fff7ed', color: '#c2410c', fontSize: 7.5, borderRadius: 3, paddingHorizontal: 4, paddingVertical: 1 },
  badgeRed:    { backgroundColor: RED_LIGHT, color: RED, fontSize: 7.5, borderRadius: 3, paddingHorizontal: 4, paddingVertical: 1 },
  badgeGray:   { backgroundColor: GRAY_100, color: GRAY_500, fontSize: 7.5, borderRadius: 3, paddingHorizontal: 4, paddingVertical: 1 },
  // Footer
  footer: {
    position: 'absolute', bottom: 20, left: 48, right: 48,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  footerText: { fontSize: 7.5, color: GRAY_500 },
  // Misc
  body:   { fontSize: 8.5, color: GRAY_700, lineHeight: 1.6 },
  bold:   { fontFamily: 'Helvetica-Bold' },
  mb4:    { marginBottom: 4 },
  mb8:    { marginBottom: 8 },
  mb12:   { marginBottom: 12 },
  mb16:   { marginBottom: 16 },
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function levelBadgeStyle(level: string) {
  if (level === 'major') return s.badgeRed;
  if (level === 'moderate') return s.badgeOrange;
  if (level === 'minor') return s.badgeAmber;
  if (level === 'stable') return s.badgeGreen;
  return s.badgeGray;
}

function levelLabel(level: string): string {
  if (level === 'major') return 'Major change';
  if (level === 'moderate') return 'Moderate change';
  if (level === 'minor') return 'Minor change';
  if (level === 'stable') return 'Stable';
  return 'No data';
}

function fmtDate(d: string): string {
  try {
    return new Date(d).toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric' });
  } catch {
    return d;
  }
}

// ---------------------------------------------------------------------------
// Sub-components
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

// ---------------------------------------------------------------------------
// Main document
// ---------------------------------------------------------------------------

export function PreDAHistoryReportDocument({ data }: { data: PreDAHistoryReportData }) {
  const validYears  = data.timeline.filter((r) => r.level !== 'no_data');
  const notableYears = data.timeline.filter((r) =>
    r.level === 'minor' || r.level === 'moderate' || r.level === 'major'
  );
  const allDaPans = Array.from(
    new Set(data.timeline.flatMap((r) => r.da_events ?? []))
  );

  const formattedDate = fmtDate(data.run_date);

  return (
    <Document
      title={`Pre-DA Site History Report — ${data.address}`}
      author="canibuildit.com.au"
      creator="canibuildit.com.au"
    >
      {/* ================================================================ */}
      {/* Page 1 — Cover + Summary stats + Heritage flag                   */}
      {/* ================================================================ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        <Text style={s.coverTitle}>Pre-DA Site History Report</Text>
        <Text style={s.coverAddress}>{data.address}</Text>
        <Text style={s.coverDate}>Prepared {formattedDate}</Text>
        {data.council ? (
          <Text style={s.coverSubtitle}>Council: {data.council}</Text>
        ) : null}

        {/* ---- Summary stats ---- */}
        <Text style={s.sectionTitle}>1. Summary</Text>
        <View style={s.statRow}>
          <View style={s.statBox}>
            <Text style={s.statLabel}>Years analysed</Text>
            <Text style={s.statValue}>{validYears.length}/8</Text>
            <Text style={s.statSub}>2017–2024</Text>
          </View>
          <View style={s.statBox}>
            <Text style={s.statLabel}>Notable years</Text>
            <Text style={{ ...s.statValue, color: notableYears.length > 0 ? AMBER : GREEN }}>
              {notableYears.length}
            </Text>
            <Text style={s.statSub}>
              {notableYears.length === 0 ? 'No physical changes detected' : 'Year(s) with detected change'}
            </Text>
          </View>
          <View style={s.statBox}>
            <Text style={s.statLabel}>DA/CC events found</Text>
            <Text style={s.statValue}>{allDaPans.length}</Text>
            <Text style={s.statSub}>
              {allDaPans.length > 0 ? allDaPans.slice(0, 2).join(', ') + (allDaPans.length > 2 ? '…' : '') : 'None matched'}
            </Text>
          </View>
        </View>

        {/* ---- Heritage flag ---- */}
        {data.heritage_flag ? (
          <View style={{ ...s.calloutAmber, marginTop: 4 }}>
            <Text style={{ ...s.calloutTitle, color: AMBER }}>Heritage overlay detected</Text>
            <Text style={s.calloutText}>
              {data.heritage_note ?? 'This property may be subject to a heritage overlay. Any development works require a Statement of Heritage Impact and may be subject to additional conditions.'}
            </Text>
          </View>
        ) : (
          <View style={{ ...s.calloutGreen, marginTop: 4 }}>
            <Text style={{ ...s.calloutTitle, color: GREEN }}>No heritage overlay detected</Text>
            <Text style={s.calloutText}>
              No heritage listing was found for this lot in the PostGIS spatial overlay dataset.
              Always verify against the current LEP heritage schedule before lodging.
            </Text>
          </View>
        )}

        {/* ---- Notable year summary ---- */}
        {notableYears.length > 0 ? (
          <>
            <Text style={s.sectionTitle}>2. Notable Years</Text>
            <Text style={{ ...s.body, marginBottom: 8 }}>
              The following years showed physical site changes above the baseline threshold.
            </Text>
            {notableYears.map((entry, i) => (
              <View key={i} style={{ marginBottom: 10 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                  <Text style={{ fontFamily: 'Helvetica-Bold', fontSize: 10 }}>{entry.year}</Text>
                  <Text style={levelBadgeStyle(entry.level)}>{levelLabel(entry.level)}</Text>
                  {entry.similarity != null ? (
                    <Text style={{ fontSize: 7.5, color: GRAY_500 }}>
                      similarity: {entry.similarity.toFixed(3)}
                    </Text>
                  ) : null}
                </View>
                <Text style={s.calloutText}>
                  {entry.explanation || entry.label}
                  {entry.da_events && entry.da_events.length > 0
                    ? `  •  DA refs: ${entry.da_events.join(', ')}`
                    : ''}
                </Text>
              </View>
            ))}
          </>
        ) : (
          <View style={{ marginTop: 12 }}>
            <Text style={s.sectionTitle}>2. Change Detection Result</Text>
            <View style={s.calloutGreen}>
              <Text style={{ ...s.calloutTitle, color: GREEN }}>No significant physical changes detected (2017–2024)</Text>
              <Text style={s.calloutText}>
                Cosine similarity between consecutive annual Tessera embeddings remained above the
                stable threshold (0.95) across all analysed years. This property shows no evidence of
                demolition, major construction, or significant physical alteration during this period.
              </Text>
            </View>
          </View>
        )}

        <View style={s.footer} fixed>
          <Text style={s.footerText}>canibuildit.com.au — Pre-DA Site History Report</Text>
          <Text style={s.footerText} render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`} />
        </View>
      </Page>

      {/* ================================================================ */}
      {/* Page 2 — Full year-by-year timeline                              */}
      {/* ================================================================ */}
      <Page size="A4" style={s.page}>
        <Text style={s.sectionTitle}>3. Year-by-Year Satellite Timeline</Text>
        <Text style={{ ...s.body, marginBottom: 10 }}>
          Annual cosine similarity scores between consecutive years using Tessera/Clay v1.5
          10 m embeddings. Scores are neighbourhood-adjusted to suppress area-wide events.
          Change thresholds: stable ≥ 0.95 · minor ≥ 0.85 · moderate ≥ 0.70 · major &lt; 0.70.
        </Text>

        {/* Table header */}
        <View style={s.tableHeader}>
          <Text style={{ ...s.tableHeaderCell, flex: 0.7 }}>Year</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 1.2 }}>Level</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 0.8 }}>Similarity</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 3 }}>Notes</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 1.5 }}>DA refs</Text>
        </View>

        {data.timeline.map((entry, i) => (
          <View key={entry.year} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
            <Text style={{ ...s.tableCellBold, flex: 0.7 }}>{entry.year}</Text>
            <Text style={{ ...s.tableCell, flex: 1.2, color:
              entry.level === 'major' ? RED :
              entry.level === 'moderate' ? '#c2410c' :
              entry.level === 'minor' ? AMBER :
              entry.level === 'no_data' ? GRAY_500 : GREEN
            }}>
              {levelLabel(entry.level)}
            </Text>
            <Text style={{ ...s.tableCell, flex: 0.8 }}>
              {entry.similarity != null ? entry.similarity.toFixed(3) : '—'}
            </Text>
            <Text style={{ ...s.tableCell, flex: 3, fontSize: 7.5 }}>
              {entry.suppressed
                ? 'Systemic event suppressed (neighbourhood-wide change)'
                : entry.explanation || entry.label || '—'}
            </Text>
            <Text style={{ ...s.tableCell, flex: 1.5, fontSize: 7, color: GRAY_500 }}>
              {entry.da_events && entry.da_events.length > 0
                ? entry.da_events.join(', ')
                : '—'}
            </Text>
          </View>
        ))}

        <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, marginTop: 8 }}>
          Note: 2025 satellite data is sparse — many tiles incomplete. 2025 column shows N/A for most addresses.
          DA refs show the NSW ePlanning Portal Application Number for DAs/CCs active in that year.
        </Text>

        {/* Wayback SSIM section (if present) */}
        {data.wayback_ssim && Object.keys(data.wayback_ssim).length > 0 ? (
          <>
            <Text style={s.sectionTitle}>4. Visual Imagery Comparison (Wayback SSIM)</Text>
            <Text style={{ ...s.body, marginBottom: 8 }}>
              Structural Similarity Index between consecutive years of Esri World Imagery Wayback tiles
              (zoom 19 ≈ 30 cm/px). Score range 0–1; lower = more visual change.
            </Text>
            <View style={s.tableHeader}>
              <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Period</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 1 }}>SSIM Score</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Interpretation</Text>
            </View>
            {Object.entries(data.wayback_ssim).map(([period, score], i) => (
              <View key={period} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                <Text style={{ ...s.tableCellBold, flex: 2 }}>{period}</Text>
                <Text style={{ ...s.tableCell, flex: 1 }}>{score.toFixed(3)}</Text>
                <Text style={{ ...s.tableCell, flex: 2 }}>
                  {score >= 0.9 ? 'No visible change' :
                   score >= 0.75 ? 'Minor visual change' :
                   score >= 0.6 ? 'Moderate visual change' : 'Significant visual change'}
                </Text>
              </View>
            ))}
          </>
        ) : null}

        <View style={s.footer} fixed>
          <Text style={s.footerText}>canibuildit.com.au — Pre-DA Site History Report</Text>
          <Text style={s.footerText} render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`} />
        </View>
      </Page>

      {/* ================================================================ */}
      {/* Page 3 — DA events detail + data quality + disclaimer            */}
      {/* ================================================================ */}
      <Page size="A4" style={s.page}>

        {/* DA events list */}
        {allDaPans.length > 0 ? (
          <>
            <Text style={s.sectionTitle}>
              {data.wayback_ssim && Object.keys(data.wayback_ssim).length > 0 ? '5.' : '4.'}
              {' '}Development Application Events
            </Text>
            <Text style={{ ...s.body, marginBottom: 8 }}>
              The following DA/CC/OC events were found on the NSW ePlanning Portal for this address.
              DA events are sourced from the ePlanning API — complete from July 2021; earlier events
              may not be captured.
            </Text>
            <View style={s.tableHeader}>
              <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Application number</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Year</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Type</Text>
            </View>
            {data.timeline
              .flatMap((entry) =>
                (entry.da_events ?? []).map((pan) => ({
                  pan,
                  year: entry.year,
                  level: entry.level,
                  label: entry.explanation || entry.label,
                }))
              )
              .filter(
                (item, idx, arr) => arr.findIndex((x) => x.pan === item.pan) === idx
              )
              .map((item, i) => (
                <View key={item.pan} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                  <Text style={{ ...s.tableCellBold, flex: 2 }}>{item.pan}</Text>
                  <Text style={{ ...s.tableCell, flex: 1 }}>{item.year}</Text>
                  <Text style={{ ...s.tableCell, flex: 2, fontSize: 7.5 }}>
                    {item.label || '—'}
                  </Text>
                </View>
              ))}
            <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, marginTop: 6 }}>
              Verify current status at{' '}
              <Link src="https://www.planningportal.nsw.gov.au/" style={{ color: TEAL }}>
                planningportal.nsw.gov.au
              </Link>
            </Text>
          </>
        ) : null}

        {/* Methodology */}
        <Text style={s.sectionTitle}>Methodology</Text>
        <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, lineHeight: 1.6 }}>
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>Satellite change detection: </Text>
          Tessera/Clay v1.5 annual 10 m embeddings (128 channels, 2017–2025). Year-on-year cosine
          similarity is computed across 5 lot-interior sample points (centroid + 4 interior corners)
          and normalised against a 16-point neighbourhood ring to suppress area-wide events
          (vegetation seasons, atmospheric effects).{'\n\n'}
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>DA event matching: </Text>
          NSW ePlanning Portal API — OnlineDA and OnlinePCC endpoints. Filtered by council, then
          fuzzy-matched to the subject address. Complete from July 2021; pre-July 2021 events
          may not be captured.{'\n\n'}
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>Heritage flag: </Text>
          PostGIS spatial overlay query against the PlotDetect spatial database. Covers heritage
          items and conservation areas from local and state planning instruments.{'\n\n'}
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>Flood/fire annotations: </Text>
          Hardcoded bounding-box annotations for known major NSW flood and bushfire events
          (2019–2022). Not a substitute for formal flood/bushfire risk assessment.
        </Text>

        <View style={s.mb8} />

        <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5 }}>
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>Data sources: </Text>
          Tessera/Clay v1.5 (Spatial Days) · NSW ePlanning Portal · PlotDetect spatial database ·
          NSW SES flood event records · NSW RFS bushfire event records
        </Text>

        <View style={s.mb12} />

        {/* Disclaimer */}
        <Text style={s.sectionTitle}>Disclaimer</Text>
        <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, lineHeight: 1.6 }}>
          This report is produced for preliminary due diligence purposes only and does not
          constitute planning, legal, or engineering advice. Change detection results are based
          on automated analysis of publicly available satellite data and may not capture all
          physical changes, particularly for additions smaller than approximately 30 m².
          DA event data is sourced from the NSW ePlanning Portal and may not reflect all
          historical approvals or recent amendments.{'\n\n'}
          Always commission a formal site inspection, engage a qualified town planner or
          certifier, and verify planning controls with the relevant council and NSW Planning
          Portal before lodging a development application.
        </Text>

        <View style={{ ...s.calloutTeal, marginTop: 16 }}>
          <Text style={{ ...s.calloutTitle, color: TEAL }}>Check this property's development potential</Text>
          <Text style={s.calloutText}>
            <Link src="https://canibuildit.com.au" style={{ color: TEAL }}>canibuildit.com.au</Link>
            {' '}— granny flat eligibility, flood risk, solar yield, and shadow impact reports for any NSW address.
          </Text>
        </View>

        <View style={s.footer} fixed>
          <Text style={s.footerText}>canibuildit.com.au — Pre-DA Site History Report</Text>
          <Text style={s.footerText} render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`} />
        </View>
      </Page>
    </Document>
  );
}
