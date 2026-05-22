/**
 * Pre-DA Site History Report PDF
 * Generated server-side via @react-pdf/renderer renderToBuffer().
 *
 * Audience: buyer's agents, solicitors, town planners, property investors.
 * Written in plain English — no jargon, no academic tone.
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

export interface DAEvent {
  pan: string;
  status?: string;
  app_type?: string;
  dev_type?: string;
  date?: string;
}

export interface TimelineEntry {
  year: number;
  level: 'stable' | 'minor' | 'moderate' | 'major' | 'no_data';
  label: string;
  color?: string;
  similarity?: number | null;
  suppressed?: boolean;
  explanation?: string;
  change_type?: string;
  da_events?: (string | DAEvent)[];
  ndvi_delta?: number;
  ndbi_delta?: number;
  spectral_escalation?: boolean;
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
  coverLogoRow:  { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 56 },
  coverLogoImg:  { width: 18, height: 18 },
  coverLogo:     { fontSize: 11, fontFamily: 'Helvetica-Bold', color: TEAL },
  coverTitle:    { fontSize: 22, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 8 },
  coverAddress:  { fontSize: 12, color: GRAY_700, marginBottom: 4 },
  coverDate:     { fontSize: 9, color: GRAY_500, marginBottom: 32 },
  coverSubtitle: { fontSize: 9, color: GRAY_500, marginBottom: 4 },
  sectionTitle: {
    fontSize: 11, fontFamily: 'Helvetica-Bold', color: GRAY_900,
    borderBottomWidth: 1, borderBottomColor: GRAY_300,
    paddingBottom: 4, marginBottom: 10, marginTop: 24,
  },
  statRow:  { flexDirection: 'row', gap: 12, marginBottom: 12 },
  statBox:  { flex: 1, backgroundColor: GRAY_100, borderRadius: 4, padding: 10 },
  statLabel: { fontSize: 7.5, color: GRAY_500, marginBottom: 3, textTransform: 'uppercase' },
  statValue: { fontSize: 14, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  statSub:  { fontSize: 7.5, color: GRAY_500, marginTop: 2 },
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
  footer: {
    position: 'absolute', bottom: 20, left: 48, right: 48,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  footerText: { fontSize: 7.5, color: GRAY_500 },
  body:   { fontSize: 8.5, color: GRAY_700, lineHeight: 1.6 },
  bold:   { fontFamily: 'Helvetica-Bold' },
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function levelColor(level: string) {
  if (level === 'major') return RED;
  if (level === 'moderate') return '#c2410c';
  if (level === 'minor') return AMBER;
  if (level === 'stable') return GREEN;
  return GRAY_500;
}

function levelLabel(level: string): string {
  if (level === 'major') return 'Major change';
  if (level === 'moderate') return 'Moderate change';
  if (level === 'minor') return 'Minor change';
  if (level === 'stable') return 'Stable';
  return 'No data';
}

function levelBadgeStyle(level: string) {
  const base = { fontSize: 7.5, borderRadius: 3, paddingHorizontal: 4, paddingVertical: 1 };
  if (level === 'major') return { ...base, backgroundColor: RED_LIGHT, color: RED };
  if (level === 'moderate') return { ...base, backgroundColor: '#fff7ed', color: '#c2410c' };
  if (level === 'minor') return { ...base, backgroundColor: AMBER_LIGHT, color: AMBER };
  if (level === 'stable') return { ...base, backgroundColor: GREEN_LIGHT, color: GREEN };
  return { ...base, backgroundColor: GRAY_100, color: GRAY_500 };
}

function fmtDate(d: string): string {
  try {
    return new Date(d).toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric' });
  } catch {
    return d;
  }
}

/** Normalise DA events — handles both legacy string[] and new DAEvent[] format */
function normaliseDAs(raw?: (string | DAEvent)[]): DAEvent[] {
  if (!raw) return [];
  return raw.map(item =>
    typeof item === 'string' ? { pan: item } : item
  );
}

/** Get all unique DA events across all timeline entries */
function collectAllDAs(timeline: TimelineEntry[]): (DAEvent & { year: number })[] {
  const seen = new Set<string>();
  const result: (DAEvent & { year: number })[] = [];
  for (const entry of timeline) {
    for (const da of normaliseDAs(entry.da_events)) {
      if (!seen.has(da.pan)) {
        seen.add(da.pan);
        result.push({ ...da, year: entry.year });
      }
    }
  }
  return result;
}

/** Plain-English description of what a change_type means */
function changeTypeExplain(ct?: string): string {
  if (!ct) return '';
  if (ct === 'hardening') return 'Increased hard surfaces detected (concrete, roofing, paving)';
  if (ct === 'greening') return 'Increased vegetation detected (landscaping, tree growth)';
  if (ct === 'demolition') return 'Structures appear to have been removed';
  if (ct === 'construction') return 'New structures or significant building work detected';
  return '';
}

/** Build the executive summary paragraph */
function buildSummary(data: PreDAHistoryReportData, notableYears: TimelineEntry[], allDAs: (DAEvent & { year: number })[]): string {
  const parts: string[] = [];

  if (notableYears.length === 0 && allDAs.length === 0) {
    parts.push(
      `Satellite analysis from 2017 to 2024 found no significant physical changes to this property. ` +
      `No development applications were matched to this address on the NSW ePlanning Portal.`
    );
  } else {
    if (notableYears.length > 0) {
      const years = notableYears.map(e => e.year).join(', ');
      parts.push(
        `Satellite imagery detected physical changes to this property in ${years}.`
      );
    }
    if (allDAs.length > 0) {
      parts.push(
        `${allDAs.length} development application${allDAs.length > 1 ? 's were' : ' was'} found ` +
        `on the NSW ePlanning Portal for this address.`
      );
    }
  }

  if (data.heritage_flag) {
    parts.push('A heritage overlay applies to this property — any works may require a Statement of Heritage Impact.');
  }

  return parts.join(' ');
}

/** What the buyer/planner should do next */
function buildRecommendations(data: PreDAHistoryReportData, notableYears: TimelineEntry[], allDAs: (DAEvent & { year: number })[]): string[] {
  const recs: string[] = [];

  if (notableYears.some(e => e.level === 'major' || e.level === 'moderate')) {
    recs.push('Commission a site inspection to verify the nature and approval status of physical changes detected by satellite.');
  }

  if (allDAs.length > 0) {
    const pans = allDAs.slice(0, 3).map(d => d.pan).join(', ');
    recs.push(
      `Search the NSW Planning Portal for ${pans}${allDAs.length > 3 ? ' and others' : ''} ` +
      `to confirm determination status, conditions, and any outstanding compliance issues.`
    );
  }

  if (data.heritage_flag) {
    recs.push('Engage a heritage consultant before scoping any development works on this site.');
  }

  if (notableYears.length === 0 && allDAs.length === 0) {
    recs.push('No red flags identified in the data sources checked. Standard pre-DA due diligence includes a s10.7 certificate, site inspection, and planner consultation.');
  } else {
    recs.push('Request a Section 10.7(2) planning certificate from council to confirm current planning controls and any outstanding orders.');
  }

  recs.push('Verify all findings with the relevant council and a qualified town planner before lodging a DA.');

  return recs;
}

function LogoRow({ logo_b64 }: { logo_b64?: string | null }) {
  return (
    <View style={s.coverLogoRow}>
      {logo_b64 ? (
        <Image src={`data:image/png;base64,${logo_b64}`} style={s.coverLogoImg} />
      ) : null}
      <Text style={s.coverLogo}>Can I Build It?</Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Main document
// ---------------------------------------------------------------------------

export function PreDAHistoryReportDocument({ data }: { data: PreDAHistoryReportData }) {
  const validYears = data.timeline.filter(r => r.level !== 'no_data');
  const notableYears = data.timeline.filter(r =>
    r.level === 'minor' || r.level === 'moderate' || r.level === 'major'
  );
  const stableYears = data.timeline.filter(r => r.level === 'stable');
  const allDAs = collectAllDAs(data.timeline);
  const formattedDate = fmtDate(data.run_date);
  const summary = buildSummary(data, notableYears, allDAs);
  const recs = buildRecommendations(data, notableYears, allDAs);

  // Risk verdict
  const hasRisk = notableYears.some(e => e.level === 'major' || e.level === 'moderate');
  const hasFlags = notableYears.length > 0 || allDAs.length > 0 || data.heritage_flag;

  return (
    <Document
      title={`Pre-DA Site History — ${data.address}`}
      author="plotdetect.com.au"
      creator="plotdetect.com.au"
    >
      {/* ================================================================ */}
      {/* Page 1 — Cover, verdict, executive summary, recommendations     */}
      {/* ================================================================ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        <Text style={s.coverTitle}>Site History Report</Text>
        <Text style={s.coverAddress}>{data.address}</Text>
        <Text style={s.coverDate}>Prepared {formattedDate}</Text>
        {data.council && <Text style={s.coverSubtitle}>{data.council}</Text>}
        <Text style={{ fontSize: 8, color: GRAY_500, marginBottom: 4 }}>
          Coordinates: {data.lat.toFixed(5)}, {data.lon.toFixed(5)}
        </Text>

        {/* ---- Verdict banner ---- */}
        <View style={hasRisk ? s.calloutRed : hasFlags ? s.calloutAmber : s.calloutGreen}>
          <Text style={{ ...s.calloutTitle, color: hasRisk ? RED : hasFlags ? AMBER : GREEN }}>
            {hasRisk
              ? 'Action required — physical changes detected'
              : hasFlags
                ? 'Further review advisable — activity detected'
                : 'No red flags identified'}
          </Text>
          <Text style={s.calloutText}>{summary}</Text>
        </View>

        {/* ---- At a glance ---- */}
        <Text style={s.sectionTitle}>At a glance</Text>
        <View style={s.statRow}>
          <View style={s.statBox}>
            <Text style={s.statLabel}>Period covered</Text>
            <Text style={s.statValue}>8 years</Text>
            <Text style={s.statSub}>2017 to 2024</Text>
          </View>
          <View style={s.statBox}>
            <Text style={s.statLabel}>Physical changes detected</Text>
            <Text style={{ ...s.statValue, color: notableYears.length > 0 ? AMBER : GREEN }}>
              {notableYears.length > 0 ? `${notableYears.length} year${notableYears.length > 1 ? 's' : ''}` : 'None'}
            </Text>
            <Text style={s.statSub}>
              {notableYears.length > 0 ? notableYears.map(e => e.year).join(', ') : 'Site appears unchanged'}
            </Text>
          </View>
          <View style={s.statBox}>
            <Text style={s.statLabel}>DA applications found</Text>
            <Text style={{ ...s.statValue, color: allDAs.length > 0 ? AMBER : GREEN }}>
              {allDAs.length}
            </Text>
            <Text style={s.statSub}>
              {allDAs.length > 0 ? 'Matched to this address' : 'None on ePlanning Portal'}
            </Text>
          </View>
        </View>

        {/* ---- Heritage ---- */}
        {data.heritage_flag ? (
          <View style={s.calloutAmber}>
            <Text style={{ ...s.calloutTitle, color: AMBER }}>Heritage overlay applies</Text>
            <Text style={s.calloutText}>
              {data.heritage_note ?? 'This property is subject to a heritage overlay. Any development works will require a Statement of Heritage Impact and may be subject to additional consent conditions. Check the LEP heritage schedule for the specific listing.'}
            </Text>
          </View>
        ) : (
          <View style={{ ...s.calloutGreen }}>
            <Text style={{ ...s.calloutTitle, color: GREEN }}>No heritage listing found</Text>
            <Text style={s.calloutText}>
              No heritage item or conservation area was found for this lot. Always verify against the current LEP heritage schedule before lodging.
            </Text>
          </View>
        )}

        {/* ---- Recommended next steps ---- */}
        <Text style={s.sectionTitle}>Suggested next steps</Text>
        <View style={{ marginBottom: 24 }}>
          {recs.map((rec, i) => (
            <View key={i} style={{ flexDirection: 'row', marginBottom: 6, paddingRight: 16 }} wrap={false}>
              <Text style={{ ...s.body, fontFamily: 'Helvetica-Bold', marginRight: 6, color: TEAL }}>
                {i + 1}.
              </Text>
              <Text style={s.body}>{rec}</Text>
            </View>
          ))}
        </View>

        <View style={s.footer} fixed>
          <Text style={s.footerText}>plotdetect.com.au</Text>
          <Text style={s.footerText} render={({ pageNumber, totalPages }) => `${pageNumber} / ${totalPages}`} />
        </View>
      </Page>

      {/* ================================================================ */}
      {/* Page 2 — Year-by-year findings (written in English, not jargon)  */}
      {/* ================================================================ */}
      <Page size="A4" style={s.page}>
        <Text style={s.sectionTitle}>Year-by-year satellite analysis</Text>
        <Text style={{ ...s.body, marginBottom: 12 }}>
          Satellite imagery from 2017 to 2024 was analysed for physical changes to the property.
          Each year is compared to the previous year. Neighbourhood-wide variations (seasonal vegetation,
          weather effects) are filtered out so that only site-specific changes are flagged.
        </Text>

        {/* Notable years — detailed cards */}
        {notableYears.length > 0 && (
          <>
            {notableYears.map((entry) => {
              const ctExplain = changeTypeExplain(entry.change_type);
              return (
                <View key={entry.year} style={{ marginBottom: 12, borderWidth: 1, borderColor: GRAY_300, borderRadius: 4, padding: 10 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <Text style={{ fontFamily: 'Helvetica-Bold', fontSize: 12 }}>{entry.year}</Text>
                    <Text style={levelBadgeStyle(entry.level)}>{levelLabel(entry.level)}</Text>
                  </View>

                  {ctExplain ? (
                    <Text style={{ ...s.body, marginBottom: 4 }}>{ctExplain}.</Text>
                  ) : null}

                  {entry.explanation && (
                    <Text style={{ ...s.body, marginBottom: 4 }}>{entry.explanation}</Text>
                  )}

                  {entry.da_events && entry.da_events.length > 0 && (
                    <View style={{ backgroundColor: GRAY_100, borderRadius: 3, padding: 6, marginTop: 4 }}>
                      <Text style={{ fontSize: 7.5, fontFamily: 'Helvetica-Bold', color: GRAY_700, marginBottom: 3 }}>
                        Applications matched to this address:
                      </Text>
                      {normaliseDAs(entry.da_events).map(da => (
                        <View key={da.pan} style={{ marginLeft: 8, marginBottom: 3 }}>
                          <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_700 }}>
                            {da.pan}{da.status ? ` — ${da.status}` : ''}
                          </Text>
                          {da.app_type && (
                            <Text style={{ fontSize: 7.5, color: GRAY_500, marginLeft: 0 }}>
                              {da.app_type}{da.dev_type ? `: ${da.dev_type}` : ''}{da.date ? ` (${da.date})` : ''}
                            </Text>
                          )}
                        </View>
                      ))}
                    </View>
                  )}

                  {entry.similarity != null && (
                    <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 4 }}>
                      Satellite similarity score: {entry.similarity.toFixed(3)} (lower = more change)
                    </Text>
                  )}
                </View>
              );
            })}
          </>
        )}

        {/* Stable years — single summary, not repeated rows */}
        {stableYears.length > 0 && (
          <View style={{ ...s.calloutGreen, marginTop: 4 }}>
            <Text style={{ ...s.calloutTitle, color: GREEN }}>
              {stableYears.length === validYears.length
                ? 'No physical changes detected in any year'
                : `Stable in ${stableYears.length} of ${validYears.length} years`}
            </Text>
            <Text style={s.calloutText}>
              {stableYears.map(e => e.year).join(', ')} — satellite imagery showed no
              site-specific physical changes. Seasonal and neighbourhood-wide variations were filtered out.
            </Text>
          </View>
        )}

        {/* Full timeline table */}
        <Text style={{ ...s.sectionTitle, marginTop: 20 }}>Complete timeline</Text>
        <View style={s.tableHeader}>
          <Text style={{ ...s.tableHeaderCell, flex: 0.6 }}>Year</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Status</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 3 }}>What we found</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 1.4 }}>DA references</Text>
        </View>

        {data.timeline.map((entry, i) => (
          <View key={entry.year} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
            <Text style={{ ...s.tableCellBold, flex: 0.6 }}>{entry.year}</Text>
            <Text style={{ ...s.tableCell, flex: 1, color: levelColor(entry.level) }}>
              {levelLabel(entry.level)}
            </Text>
            <Text style={{ ...s.tableCell, flex: 3, fontSize: 7.5 }}>
              {entry.level === 'no_data'
                ? 'Satellite data not yet available'
                : entry.suppressed
                  ? 'No site-specific change'
                  : entry.explanation || entry.label || 'No change detected'}
            </Text>
            <Text style={{ ...s.tableCell, flex: 1.4, fontSize: 7, color: GRAY_500 }}>
              {normaliseDAs(entry.da_events).length > 0
                ? normaliseDAs(entry.da_events).map(d => d.pan).join(', ')
                : '-'}
            </Text>
          </View>
        ))}

        {/* Wayback SSIM section */}
        {data.wayback_ssim && Object.keys(data.wayback_ssim).length > 0 && (
          <>
            <Text style={{ ...s.sectionTitle, marginTop: 20 }}>Aerial imagery comparison</Text>
            <Text style={{ ...s.body, marginBottom: 8 }}>
              High-resolution aerial images (30 cm/pixel) were compared year-on-year.
              Lower scores indicate more visible change.
            </Text>
            <View style={s.tableHeader}>
              <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Period</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Score</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Meaning</Text>
            </View>
            {Object.entries(data.wayback_ssim).map(([period, score], i) => (
              <View key={period} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                <Text style={{ ...s.tableCellBold, flex: 2 }}>{period}</Text>
                <Text style={{ ...s.tableCell, flex: 1 }}>{score.toFixed(3)}</Text>
                <Text style={{ ...s.tableCell, flex: 2 }}>
                  {score >= 0.9 ? 'No visible change' :
                   score >= 0.75 ? 'Minor visible change' :
                   score >= 0.6 ? 'Moderate visible change' : 'Significant visible change'}
                </Text>
              </View>
            ))}
          </>
        )}

        <View style={s.footer} fixed>
          <Text style={s.footerText}>plotdetect.com.au</Text>
          <Text style={s.footerText} render={({ pageNumber, totalPages }) => `${pageNumber} / ${totalPages}`} />
        </View>
      </Page>

      {/* ================================================================ */}
      {/* Page 3 — DA detail, data sources, disclaimer                    */}
      {/* ================================================================ */}
      <Page size="A4" style={s.page}>

        {/* DA events detail */}
        {allDAs.length > 0 && (
          <>
            <Text style={s.sectionTitle}>Development applications</Text>
            <Text style={{ ...s.body, marginBottom: 8 }}>
              The following applications were found on the NSW ePlanning Portal for this address.
              The portal has comprehensive data from July 2021 onward; earlier applications may not appear.
            </Text>
            {/* Rich table when pipeline provides full DA data, simple list otherwise */}
            {allDAs.some(da => da.app_type || da.status) ? (
              <>
                <View style={s.tableHeader}>
                  <Text style={{ ...s.tableHeaderCell, flex: 1.5 }}>Application</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Type</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Status</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 0.7 }}>Date</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Development type</Text>
                </View>
                {allDAs.map((da, i) => (
                  <View key={da.pan} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                    <Text style={{ ...s.tableCellBold, flex: 1.5 }}>{da.pan}</Text>
                    <Text style={{ ...s.tableCell, flex: 1, fontSize: 7.5 }}>
                      {da.app_type || '-'}
                    </Text>
                    <Text style={{ ...s.tableCell, flex: 1, fontSize: 7.5, color: da.status === 'Approved' || da.status === 'Determined' ? GREEN : GRAY_700 }}>
                      {da.status || '-'}
                    </Text>
                    <Text style={{ ...s.tableCell, flex: 0.7, fontSize: 7.5 }}>
                      {da.date || String(da.year)}
                    </Text>
                    <Text style={{ ...s.tableCell, flex: 2, fontSize: 7.5 }}>
                      {da.dev_type || '-'}
                    </Text>
                  </View>
                ))}
              </>
            ) : (
              <>
                <View style={s.tableHeader}>
                  <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Application number</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Year detected</Text>
                </View>
                {allDAs.map((da, i) => (
                  <View key={da.pan} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                    <Text style={{ ...s.tableCellBold, flex: 2 }}>{da.pan}</Text>
                    <Text style={{ ...s.tableCell, flex: 1 }}>{da.year}</Text>
                  </View>
                ))}
                <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, marginTop: 4 }}>
                  For full application details (status, type, conditions), search each number on the NSW Planning Portal.
                </Text>
              </>
            )}
            <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, marginTop: 6 }}>
              Check current status at{' '}
              <Link src="https://www.planningportal.nsw.gov.au/" style={{ color: TEAL }}>
                planningportal.nsw.gov.au
              </Link>
            </Text>
          </>
        )}

        {/* How this report was produced */}
        <Text style={s.sectionTitle}>How this report was produced</Text>
        <View style={{ marginBottom: 6 }}>
          <Text style={{ ...s.body, marginBottom: 6 }}>
            <Text style={s.bold}>Satellite change detection: </Text>
            Annual satellite imagery (10 metre resolution, 2017-2024) was analysed for physical changes to the property.
            Each year is compared to the previous year using AI-powered image embeddings.
            Neighbourhood-wide changes (seasonal vegetation, weather) are automatically filtered out
            so that only site-specific changes are flagged.
          </Text>
          <Text style={{ ...s.body, marginBottom: 6 }}>
            <Text style={s.bold}>Development application search: </Text>
            DA and CDC applications were searched on the NSW ePlanning Portal and matched to this address.
            Portal data is comprehensive from July 2021. Earlier applications may not appear.
          </Text>
          <Text style={{ ...s.body, marginBottom: 6 }}>
            <Text style={s.bold}>Heritage check: </Text>
            The property was checked against heritage item and conservation area spatial overlays
            from local and state planning instruments.
          </Text>
        </View>

        <View style={{ marginTop: 4, marginBottom: 12 }}>
          <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5 }}>
            <Text style={s.bold}>Data sources: </Text>
            Sentinel-2 satellite imagery (ESA/Copernicus, via Element84 Earth Search) | GeoTessera Clay v1.5 embeddings |
            NSW ePlanning Portal | NSW Planning Portal spatial overlays |
            Flood and bushfire event annotations based on known event bounding boxes (indicative, not sourced from live SES/RFS feeds)
          </Text>
        </View>

        {/* Limitations */}
        <Text style={s.sectionTitle}>Limitations</Text>
        <Text style={{ ...s.body, color: GRAY_500, fontSize: 8, lineHeight: 1.6, marginBottom: 12 }}>
          This report uses automated satellite analysis and cannot detect changes smaller than
          approximately 30 square metres (e.g. a single-car carport). Interior renovations are not visible
          to satellites. DA data before July 2021 may be incomplete. This report does not cover
          unauthorised works, building compliance, contamination, or structural condition.
        </Text>

        {/* Disclaimer */}
        <Text style={s.sectionTitle}>Disclaimer</Text>
        <Text style={{ ...s.body, color: GRAY_500, fontSize: 7.5, lineHeight: 1.6 }}>
          This report is for preliminary due diligence purposes only. It does not constitute
          planning, legal, or engineering advice. Always commission a formal site inspection,
          engage a qualified town planner or certifier, and verify planning controls with the
          relevant council and NSW Planning Portal before lodging a development application.
        </Text>

        <View style={{ ...s.calloutTeal, marginTop: 16 }}>
          <Text style={{ ...s.calloutTitle, color: TEAL }}>More reports for this property</Text>
          <Text style={s.calloutText}>
            <Link src={`https://plotdetect.com.au`} style={{ color: TEAL }}>plotdetect.com.au</Link>
            {' '} — flood screening, bushfire pre-screen, shadow impact, solar yield, and granny flat eligibility for any NSW address.
          </Text>
        </View>

        <View style={s.footer} fixed>
          <Text style={s.footerText}>plotdetect.com.au</Text>
          <Text style={s.footerText} render={({ pageNumber, totalPages }) => `${pageNumber} / ${totalPages}`} />
        </View>
      </Page>
    </Document>
  );
}
