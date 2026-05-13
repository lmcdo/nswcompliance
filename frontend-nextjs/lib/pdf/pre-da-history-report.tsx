/**
 * Pre-DA Site History Report PDF
 * Generated server-side via @react-pdf/renderer renderToBuffer().
 *
 * Audience: buyer's agents, solicitors, town planners, property investors.
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
import { PlotDetectFooter, AboutPage, ReferralLinks, DataCurrencyTable, QRBlock, PreparedBy } from './shared-components';

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
  is_paid?: boolean;
  qr_b64?: string | null;
  firm_name?: string | null;
  shareable_url?: string | null;
}

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

const TEAL       = '#0f766e';
const TEAL_LIGHT = '#f0fdfa';
const RED        = '#dc2626';
const RED_LIGHT  = '#fef2f2';
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

const SEVERITY_COLORS = { green: GREEN, amber: AMBER, red: RED };

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
  logoRow:   { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 32 },
  logoImg:   { width: 18, height: 18 },
  logo:      { fontSize: 11, fontFamily: 'Helvetica-Bold', color: TEAL },
  h1:        { fontSize: 22, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 6 },
  subhead:   { fontSize: 11, color: GRAY_700, marginBottom: 3 },
  dateText:  { fontSize: 9, color: GRAY_500, marginBottom: 16 },
  sectionTitle: {
    fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_500,
    textTransform: 'uppercase', letterSpacing: 0.8,
    marginTop: 16, marginBottom: 8,
  },
  divider:   { borderBottom: `1 solid ${GRAY_300}`, marginVertical: 12 },
  bodyText:  { fontSize: 8.5, color: GRAY_700, lineHeight: 1.5, marginBottom: 6 },
  bold:      { fontFamily: 'Helvetica-Bold' },
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
});

// ---------------------------------------------------------------------------
// Finding row
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

function normaliseDAs(raw?: (string | DAEvent)[]): DAEvent[] {
  if (!raw) return [];
  return raw.map(item => typeof item === 'string' ? { pan: item } : item);
}

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

function changeTypeExplain(ct?: string): string {
  if (!ct) return '';
  if (ct === 'hardening') return 'Increased hard surfaces detected (concrete, roofing, paving)';
  if (ct === 'greening') return 'Increased vegetation detected (landscaping, tree growth)';
  if (ct === 'demolition') return 'Structures appear to have been removed';
  if (ct === 'construction') return 'New structures or significant building work detected';
  return '';
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
// Build findings
// ---------------------------------------------------------------------------

function buildFindings(data: PreDAHistoryReportData): Finding[] {
  const findings: Finding[] = [];
  const notableYears = data.timeline.filter(r =>
    r.level === 'minor' || r.level === 'moderate' || r.level === 'major'
  );
  const allDAs = collectAllDAs(data.timeline);

  // Satellite change detection
  if (notableYears.some(e => e.level === 'major' || e.level === 'moderate')) {
    findings.push({
      label: 'Sentinel-2 satellite imagery · 2017–2024',
      value: `Significant physical changes detected in ${notableYears.map(e => e.year).join(', ')}`,
      detail: 'Satellite imagery shows major site changes. Commission a site inspection to verify the nature and approval status of these changes before purchasing or lodging a DA.',
      severity: 'red',
    });
  } else if (notableYears.length > 0) {
    findings.push({
      label: 'Sentinel-2 satellite imagery · 2017–2024',
      value: `Minor changes detected in ${notableYears.map(e => e.year).join(', ')}`,
      detail: 'Some physical changes were detected but nothing flagged as major. Review the timeline detail and verify with council as part of standard due diligence.',
      severity: 'amber',
    });
  } else {
    findings.push({
      label: 'Sentinel-2 satellite imagery · 2017–2024',
      value: 'No physical changes detected over 8 years',
      detail: 'Satellite analysis from 2017 to 2024 found no significant physical changes to this property. The site appears stable.',
      severity: 'green',
    });
  }

  // DA records
  if (allDAs.length > 0) {
    findings.push({
      label: 'NSW ePlanning Portal',
      value: `${allDAs.length} development application${allDAs.length > 1 ? 's' : ''} found`,
      detail: `${allDAs.length} DA/CDC application${allDAs.length > 1 ? 's were' : ' was'} matched to this address. Check the ePlanning Portal for determination status, conditions, and any outstanding compliance issues.`,
      severity: 'amber',
    });
  } else {
    findings.push({
      label: 'NSW ePlanning Portal',
      value: 'No development applications found',
      detail: 'No DA or CDC applications were matched to this address on the NSW ePlanning Portal. Note: portal data is comprehensive from July 2021 onward; earlier applications may not appear.',
      severity: 'green',
    });
  }

  // Heritage
  if (data.heritage_flag) {
    findings.push({
      label: 'Heritage overlay (LEP heritage schedule)',
      value: 'Heritage item or conservation area',
      detail: data.heritage_note ?? 'This property is subject to a heritage overlay. Any development works will require a Statement of Heritage Impact and may be subject to additional consent conditions.',
      severity: 'amber',
    });
  } else {
    findings.push({
      label: 'Heritage overlay (LEP heritage schedule)',
      value: 'No heritage listing found',
      detail: 'No heritage item or conservation area was found for this lot. Always verify against the current LEP heritage schedule before lodging.',
      severity: 'green',
    });
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function PreDAHistoryReportDocument({ data }: { data: PreDAHistoryReportData }) {
  const validYears = data.timeline.filter(r => r.level !== 'no_data');
  const notableYears = data.timeline.filter(r =>
    r.level === 'minor' || r.level === 'moderate' || r.level === 'major'
  );
  const stableYears = data.timeline.filter(r => r.level === 'stable');
  const allDAs = collectAllDAs(data.timeline);
  const isPaid = data.is_paid === true;

  const hasRisk = notableYears.some(e => e.level === 'major' || e.level === 'moderate');

  const totalPages = 4;
  const findings = buildFindings(data);

  // Build recommendations
  const recs: string[] = [];
  if (hasRisk) {
    recs.push('Commission a site inspection to verify the nature and approval status of physical changes detected by satellite.');
  }
  if (allDAs.length > 0) {
    const pans = allDAs.slice(0, 3).map(d => d.pan).join(', ');
    recs.push(`Search the NSW Planning Portal for ${pans}${allDAs.length > 3 ? ' and others' : ''} to confirm determination status, conditions, and any outstanding compliance issues.`);
  }
  if (data.heritage_flag) {
    recs.push('Engage a heritage consultant before scoping any development works on this site.');
  }
  if (notableYears.length === 0 && allDAs.length === 0) {
    recs.push('No red flags identified. Standard pre-DA due diligence (s10.7 certificate, site inspection, planner consultation) is sufficient.');
  } else {
    recs.push('Request a Section 10.7(2) planning certificate from council to confirm current planning controls and any outstanding orders.');
  }
  recs.push('Verify all findings with the relevant council and a qualified town planner before lodging a DA.');

  let pageCounter = 0;
  const nextPage = () => ++pageCounter;

  return (
    <Document title={`Pre-DA Site History — ${data.address}`} author="PlotDetect">

      {/* ================================================================ */}
      {/* Page 1 — Cover + Findings + Recommendations                     */}
      {/* ================================================================ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />
        <Text style={s.h1}>Site History Report</Text>
        <Text style={s.subhead}>{data.address}</Text>
        {data.council && (
          <Text style={{ fontSize: 9, color: GRAY_500, marginBottom: 2 }}>{data.council}</Text>
        )}
        <Text style={s.dateText}>Report date: {data.run_date}</Text>
        <PreparedBy firmName={data.firm_name} />

        {/* Key findings */}
        <Text style={s.sectionTitle}>Key findings</Text>
        {findings.map((f) => (
          <FindingRow key={f.label} finding={f} />
        ))}

        {/* Recommended next steps — paid gets full list, free gets teaser */}
        {isPaid ? (
          <>
            <PaidSectionHeader title="Recommended next steps — paid data" />
            {recs.map((rec, i) => (
              <View key={i} style={{ flexDirection: 'row', marginBottom: 6, paddingRight: 16 }}>
                <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', marginRight: 6, color: TEAL }}>
                  {i + 1}.
                </Text>
                <Text style={s.bodyText}>{rec}</Text>
              </View>
            ))}
          </>
        ) : (
          <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 12, marginTop: 12 }}>
            <Text style={{ fontSize: 9, color: GRAY_700, marginBottom: 6 }}>
              The paid report includes:
            </Text>
            {[
              'Site-specific next steps based on detected changes',
              'Year-by-year satellite analysis with change types',
              'Full DA detail (status, type, conditions)',
              'Aerial imagery comparison scores',
              'Data currency and methodology details',
              'Heritage impact guidance',
            ].map((item) => (
              <View key={item} style={{ flexDirection: 'row', alignItems: 'flex-start', marginBottom: 3 }}>
                <Text style={{ fontSize: 8, color: TEAL, marginRight: 4 }}>•</Text>
                <Text style={{ fontSize: 8, color: GRAY_700 }}>{item}</Text>
              </View>
            ))}
            <Text style={{ fontSize: 8, color: TEAL, fontFamily: 'Helvetica-Bold', marginTop: 6 }}>
              Unlock at plotdetect.com.au — $49
            </Text>
          </View>
        )}

        <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 10, fontStyle: 'italic' }}>
          Data valid as of {data.run_date}. Re-run before exchange of contracts or DA lodgement.
        </Text>

        <PlotDetectFooter reportName="Site History Report" pageNum={nextPage()} total={totalPages} />
      </Page>

      {/* ================================================================ */}
      {/* Page 2 — Year-by-year analysis + Timeline table                 */}
      {/* ================================================================ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        <Text style={s.sectionTitle}>Year-by-year satellite analysis</Text>
        <Text style={s.bodyText}>
          Satellite imagery from 2017 to 2024 was analysed for physical changes.
          Each year is compared to the previous. Neighbourhood-wide variations are filtered out.
        </Text>

        {/* Notable years — detailed cards (paid only) */}
        {isPaid && notableYears.length > 0 && (
          <>
            <PaidSectionHeader title="Detected changes — detailed analysis" />
            {notableYears.map((entry) => {
              const ctExplain = changeTypeExplain(entry.change_type);
              return (
                <View key={entry.year} style={{ marginBottom: 10, borderWidth: 1, borderColor: GRAY_300, borderRadius: 4, padding: 10 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <Text style={{ fontFamily: 'Helvetica-Bold', fontSize: 12 }}>{entry.year}</Text>
                    <Text style={levelBadgeStyle(entry.level)}>{levelLabel(entry.level)}</Text>
                  </View>
                  {ctExplain ? <Text style={{ ...s.bodyText, marginBottom: 3 }}>{ctExplain}.</Text> : null}
                  {entry.explanation && <Text style={{ ...s.bodyText, marginBottom: 3 }}>{entry.explanation}</Text>}
                  {entry.da_events && entry.da_events.length > 0 && (
                    <View style={{ backgroundColor: GRAY_100, borderRadius: 3, padding: 6, marginTop: 3 }}>
                      <Text style={{ fontSize: 7.5, fontFamily: 'Helvetica-Bold', color: GRAY_700, marginBottom: 3 }}>
                        Applications matched:
                      </Text>
                      {normaliseDAs(entry.da_events).map(da => (
                        <View key={da.pan} style={{ marginLeft: 8, marginBottom: 2 }}>
                          <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_700 }}>
                            {da.pan}{da.status ? ` — ${da.status}` : ''}
                          </Text>
                          {da.app_type && (
                            <Text style={{ fontSize: 7.5, color: GRAY_500 }}>
                              {da.app_type}{da.dev_type ? `: ${da.dev_type}` : ''}{da.date ? ` (${da.date})` : ''}
                            </Text>
                          )}
                        </View>
                      ))}
                    </View>
                  )}
                  {entry.similarity != null && (
                    <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 3 }}>
                      Similarity score: {entry.similarity.toFixed(3)} (lower = more change)
                    </Text>
                  )}
                </View>
              );
            })}
          </>
        )}

        {!isPaid && notableYears.length > 0 && (
          <View style={{ backgroundColor: TEAL_LIGHT, borderWidth: 1, borderColor: '#99f6e4', borderRadius: 4, padding: 10, marginTop: 4 }}>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 3 }}>
              {notableYears.length} year{notableYears.length > 1 ? 's' : ''} with detected changes
            </Text>
            <Text style={{ fontSize: 8, color: TEAL }}>
              Unlock the full report for detailed analysis — change type, similarity scores, matched DAs.
            </Text>
          </View>
        )}

        {/* Stable years summary */}
        {stableYears.length > 0 && (
          <View style={{ backgroundColor: GREEN_LIGHT, borderWidth: 1, borderColor: '#bbf7d0', borderRadius: 4, padding: 10, marginTop: 8 }}>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: GREEN, marginBottom: 3 }}>
              {stableYears.length === validYears.length ? 'No changes detected in any year' : `Stable in ${stableYears.length} of ${validYears.length} years`}
            </Text>
            <Text style={{ fontSize: 8, color: GRAY_700 }}>
              {stableYears.map(e => e.year).join(', ')} — no site-specific physical changes detected.
            </Text>
          </View>
        )}

        {/* Complete timeline table */}
        <Text style={{ ...s.sectionTitle, marginTop: 16 }}>Complete timeline</Text>
        <View style={s.tableHeader}>
          <Text style={{ ...s.tableHeaderCell, flex: 0.6 }}>Year</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Status</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 3 }}>What we found</Text>
          <Text style={{ ...s.tableHeaderCell, flex: 1.4 }}>DA refs</Text>
        </View>
        {data.timeline.map((entry, i) => (
          <View key={entry.year} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
            <Text style={{ ...s.tableCellBold, flex: 0.6 }}>{entry.year}</Text>
            <Text style={{ ...s.tableCell, flex: 1, color: levelColor(entry.level) }}>
              {levelLabel(entry.level)}
            </Text>
            <Text style={{ ...s.tableCell, flex: 3, fontSize: 7.5 }}>
              {entry.level === 'no_data' ? 'Data not yet available'
                : entry.suppressed ? 'No site-specific change'
                : entry.explanation || entry.label || 'No change detected'}
            </Text>
            <Text style={{ ...s.tableCell, flex: 1.4, fontSize: 7, color: GRAY_500 }}>
              {normaliseDAs(entry.da_events).length > 0
                ? normaliseDAs(entry.da_events).map(d => d.pan).join(', ') : '-'}
            </Text>
          </View>
        ))}

        {/* Wayback SSIM — paid only */}
        {isPaid && data.wayback_ssim && Object.keys(data.wayback_ssim).length > 0 && (
          <>
            <PaidSectionHeader title="Aerial imagery comparison" />
            <Text style={{ ...s.bodyText, marginBottom: 6 }}>
              High-resolution aerial images (30cm/pixel) compared year-on-year. Lower scores = more change.
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

        <PlotDetectFooter reportName="Site History Report" pageNum={nextPage()} total={totalPages} />
      </Page>

      {/* ================================================================ */}
      {/* Page 3 — DA detail + Methodology + Disclaimer                   */}
      {/* ================================================================ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        {/* DA events detail — paid only */}
        {isPaid && allDAs.length > 0 && (
          <>
            <PaidSectionHeader title="Development applications — full detail" />
            {allDAs.some(da => da.app_type || da.status) ? (
              <>
                <View style={s.tableHeader}>
                  <Text style={{ ...s.tableHeaderCell, flex: 1.5 }}>Application</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Type</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Status</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 0.7 }}>Date</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Development</Text>
                </View>
                {allDAs.map((da, i) => (
                  <View key={da.pan} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                    <Text style={{ ...s.tableCellBold, flex: 1.5 }}>{da.pan}</Text>
                    <Text style={{ ...s.tableCell, flex: 1, fontSize: 7.5 }}>{da.app_type || '-'}</Text>
                    <Text style={{ ...s.tableCell, flex: 1, fontSize: 7.5, color: da.status === 'Approved' || da.status === 'Determined' ? GREEN : GRAY_700 }}>
                      {da.status || '-'}
                    </Text>
                    <Text style={{ ...s.tableCell, flex: 0.7, fontSize: 7.5 }}>{da.date || String(da.year)}</Text>
                    <Text style={{ ...s.tableCell, flex: 2, fontSize: 7.5 }}>{da.dev_type || '-'}</Text>
                  </View>
                ))}
              </>
            ) : (
              <>
                <View style={s.tableHeader}>
                  <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Application number</Text>
                  <Text style={{ ...s.tableHeaderCell, flex: 1 }}>Year</Text>
                </View>
                {allDAs.map((da, i) => (
                  <View key={da.pan} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                    <Text style={{ ...s.tableCellBold, flex: 2 }}>{da.pan}</Text>
                    <Text style={{ ...s.tableCell, flex: 1 }}>{da.year}</Text>
                  </View>
                ))}
              </>
            )}
            <Text style={{ fontSize: 7.5, color: GRAY_500, marginTop: 4 }}>
              Check current status at{' '}
              <Link src="https://www.planningportal.nsw.gov.au/" style={{ color: TEAL }}>
                planningportal.nsw.gov.au
              </Link>
            </Text>
          </>
        )}

        {/* Referrals */}
        <View style={{ backgroundColor: TEAL_LIGHT, borderRadius: 4, padding: 10, marginTop: 12, borderWidth: 1, borderColor: '#99f6e4' }}>
          <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
            Next steps
          </Text>
          <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
            A qualified town planner can assess the implications of detected changes and advise on DA strategy. A private certifier can verify compliance of existing structures.
          </Text>
        </View>

        <ReferralLinks links={[
          { label: 'Town planner', url: 'https://www.planning.org.au/find-a-planner', urlDisplay: 'planning.org.au/find-a-planner' },
          { label: 'Private certifier', url: 'https://www.bpb.nsw.gov.au/find-certifier', urlDisplay: 'bpb.nsw.gov.au/find-certifier' },
          { label: 'Heritage consultant', url: 'https://australia.icomos.org/get-involved/find-a-heritage-professional/', urlDisplay: 'australia.icomos.org/find-a-heritage-professional' },
        ]} />

        {isPaid && (
          <DataCurrencyTable rows={[
            { source: 'Sentinel-2 satellite imagery', type: 'Satellite imagery', currency: '2017–2024 composites' },
            { source: 'NSW ePlanning Portal (DA/CC)', type: 'Live API query', currency: `Queried ${data.run_date}` },
            { source: 'NSW Heritage Register', type: 'Live API query', currency: `Queried ${data.run_date}` },
            { source: 'Wayback Machine (Google)', type: 'Cached imagery', currency: 'Historical snapshots' },
          ]} />
        )}

        <Text style={s.sectionTitle}>Methodology</Text>
        <Text style={s.bodyText}>
          Annual satellite imagery (10m resolution, 2017–2024) analysed for physical changes using AI-powered image embeddings. Neighbourhood-wide variations filtered out. DA/CDC applications searched on NSW ePlanning Portal and matched to this address. Heritage checked against spatial overlays.
        </Text>

        <Text style={s.sectionTitle}>Disclaimer</Text>
        <Text style={{ fontSize: 8, color: GRAY_500, lineHeight: 1.6, marginBottom: 8 }}>
          This report is for preliminary due diligence only. It does not constitute planning, legal, or engineering advice. Satellite analysis cannot detect changes smaller than ~30m². Interior renovations are not visible. DA data before July 2021 may be incomplete.
        </Text>

        {data.qr_b64 && data.shareable_url && (
          <QRBlock url={data.shareable_url} qr_b64={data.qr_b64} />
        )}

        <PlotDetectFooter reportName="Site History Report" pageNum={nextPage()} total={totalPages} />
      </Page>

      {/* About page */}
      <AboutPage
        logo_b64={data.logo_b64}
        pageNum={nextPage()}
        total={totalPages}
        reportName="Site History Report"
      />
    </Document>
  );
}
