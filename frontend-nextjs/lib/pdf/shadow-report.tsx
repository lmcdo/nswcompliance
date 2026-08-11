/**
 * Shadow Detector Report PDF
 * Generated server-side via @react-pdf/renderer renderToBuffer().
 * Data passed directly from the shadow pipeline response — no DB lookup.
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
import { PlotDetectFooter, AboutPage, ReferralLinks, DataCurrencyTable, QRBlock, PreparedBy } from './shared-components';
import { AerialWithOverlay } from './map-overlay';
import {
  SCENARIO_NOT_ASSESSED_LABEL, isScenarioUnavailable, scenarioUnavailableMessage,
} from '../not-assessed';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GeoJSONGeometry {
  type: string;
  coordinates: unknown[];
}

interface GeoJSONCollection {
  type: 'FeatureCollection';
  features: { type: 'Feature'; geometry: GeoJSONGeometry; properties?: Record<string, unknown> }[];
}

export interface ShadowScenario {
  scenario: string;
  label: string;
  date: string;
  time_local: string;
  // Nullable: a scenario whose computation failed is typed-unavailable, and the
  // bearing is absent when the sun is below the horizon or so near the zenith
  // that a direction is meaningless.
  shadow_length_m: number | null;
  shadow_overlap_fraction: number | null;
  shadow_direction_deg: number | null;
  overlaps_subject_lot: boolean | null;
  status?: string | null;
  error_note?: string | null;
  shadow_on_lot?: GeoJSONCollection | null;
  shadow_polygon?: GeoJSONCollection | null;
}

export interface ShadowReportData {
  address: string;
  run_date: string;
  lat: number;
  lng: number;
  zone: string | null;
  lga_name?: string | null;
  // outputs
  height_m: number;
  height_source: string | null;
  lep_name: string | null;
  scenarios: ShadowScenario[];
  adg_compliant: boolean | null;  // null = not assessed (noon scenario missing/errored)
  worst_case_scenario: string;
  confidence: string;
  data_sources: string[];
  warnings?: string[];
  lot_polygon?: GeoJSONGeometry | null;
  north_proxy_polygon?: GeoJSONGeometry | null;
  is_paid?: boolean;
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
const RED         = '#dc2626';
const RED_LIGHT   = '#fef2f2';
const AMBER       = '#d97706';
const AMBER_LIGHT = '#fffbeb';
const GREEN       = '#16a34a';
const GREEN_LIGHT = '#f0fdf4';
const GRAY_900    = '#111827';
const GRAY_700    = '#374151';
const GRAY_500    = '#6b7280';
const GRAY_300    = '#d1d5db';
const GRAY_100    = '#f3f4f6';

const NON_RESIDENTIAL_PREFIXES = ['B', 'E', 'IN', 'SP', 'W'];

const SCENARIO_LABELS: Record<string, string> = {
  jun21_9am:  '21 Jun — 9:00 am (winter)',
  jun21_12pm: '21 Jun — 12:00 pm (winter)',
  jun21_3pm:  '21 Jun — 3:00 pm (winter)',
  sep21_12pm: '21 Sep — 12:00 pm (equinox)',
  dec21_12pm: '21 Dec — 12:00 pm (summer)',
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
  // Scenarios table
  tableHeader: {
    flexDirection: 'row', paddingVertical: 5,
    borderBottom: `1 solid ${GRAY_300}`,
  },
  tableRow: {
    flexDirection: 'row', paddingVertical: 6,
    borderBottom: `1 solid ${GRAY_300}`,
  },
  colDate:     { flex: 3, fontSize: 8.5, color: GRAY_700 },
  colReach:    { flex: 1.2, fontSize: 8.5, color: GRAY_700, textAlign: 'right' },
  colDir:      { flex: 0.8, fontSize: 8.5, color: GRAY_700, textAlign: 'right' },
  colCoverage: { flex: 1.2, fontSize: 8.5, textAlign: 'right' },
  colHeaderText: { fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' },
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

function bearingToCompass(deg: number): string {
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  return dirs[Math.round(deg / 45) % 8];
}

function coveragePillColor(pct: number | null): { bg: string; fg: string } {
  if (pct == null) return { bg: GRAY_100, fg: GRAY_500 };
  if (pct >= 70) return { bg: RED_LIGHT,   fg: RED    };
  if (pct >= 40) return { bg: AMBER_LIGHT, fg: AMBER  };
  if (pct >  0)  return { bg: '#fefce8',   fg: '#ca8a04' };
  return { bg: GRAY_100, fg: GRAY_500 };
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
    <PlotDetectFooter reportName="Shadow Detector" pageNum={pageNum} total={total} />
  );
}

// ---------------------------------------------------------------------------
// Build findings
// ---------------------------------------------------------------------------

// Exported for direct unit testing — the generate-route test mocks the whole
// document, so the findings wording is otherwise unreachable by tests.
export function buildFindings(data: ShadowReportData): Finding[] {
  const findings: Finding[] = [];
  const scenarios = data.scenarios ?? [];
  const overlapCount = scenarios.filter(sc => sc.overlaps_subject_lot).length;
  // A scenario the model could not compute must never be silently absorbed
  // into an all-clear aggregate (Sol pre-push round): overlapCount counts only
  // computed overlaps, so with one scenario unavailable, "no shadow overlap
  // across any test scenario" would claim 5 results from 4. Legacy stored rows
  // predate the status field; its absence means the row was computed.
  const unavailableCount = scenarios.filter(sc => sc.status === 'unavailable').length;
  const computedCount = scenarios.length - unavailableCount;
  const isNonRes = data.zone != null &&
    NON_RESIDENTIAL_PREFIXES.some(p => data.zone!.toUpperCase().startsWith(p));

  // ADG compliance
  if (isNonRes) {
    findings.push({
      label: 'ADG Part 3F solar access test',
      value: 'ADG — indicative only (non-residential zone)',
      detail: 'ADG solar access requirements apply to residential apartment buildings only. This property is in a non-residential zone, so the result is indicative.',
      severity: overlapCount === 0 ? 'green' : 'amber',
    });
  } else if (data.adg_compliant == null) {
    // Not assessed — the model issued no verdict (output-grounding fix 1).
    // Without this branch, null fell through to the "ADG concern" finding.
    findings.push({
      label: 'ADG Part 3F solar access test',
      value: 'Not assessed — the noon scenario could not be computed',
      detail: 'The shadow model could not compute the 21 June noon scenario for this lot, so the ADG solar access test was not run. No shadow verdict is made in this report.',
      severity: 'amber',
    });
  } else if (data.adg_compliant) {
    findings.push({
      label: 'ADG Part 3F solar access test',
      value: overlapCount === 0
        ? `Meets ADG solar access test — no shadow overlap${unavailableCount > 0 ? ` in the ${computedCount} computed scenarios` : ''}`
        : `Meets ADG solar access test — ${overlapCount} of ${unavailableCount > 0 ? `${computedCount} computed` : '5'} scenarios with shadow`,
      detail: overlapCount === 0
        ? `The model shows no significant shadow impact on this property from a maximum-height building modelled immediately north of the lot, across ${unavailableCount > 0 ? `the ${computedCount} scenarios that could be computed. ${unavailableCount} of the 5 scenarios could not be assessed (marked in the scenario table) and no claim is made about ${unavailableCount === 1 ? 'it' : 'them'}` : 'any test scenario'}. The ADG solar access test is met based on this model.`
        : 'Some shadow impact is expected but the ADG 2-hour solar access requirement (9am–3pm on 21 June) is still met. This is typical for urban lots and unlikely to be grounds for objection.',
      severity: overlapCount === 0 ? (unavailableCount > 0 ? 'amber' : 'green') : 'amber',
    });
  } else {
    findings.push({
      label: 'ADG Part 3F solar access test',
      value: `ADG concern — ${overlapCount} of ${unavailableCount > 0 ? `${computedCount} computed` : '5'} scenarios with significant shadow`,
      detail: 'A maximum-height building modelled immediately north of this lot may not meet the ADG 2-hour solar access requirement on 21 June. If a DA is lodged, you can lodge a formal objection during the notification period.',
      severity: 'red',
    });
  }

  // Building height
  if (data.height_source === 'default') {
    findings.push({
      label: 'LEP height of buildings control',
      value: `${data.height_m}m — default (no HOB control found)`,
      detail: 'No building height control was found in the applicable LEP. A 9m default has been used, which is the typical height limit for low-density residential zones.',
      severity: 'amber',
    });
  } else {
    findings.push({
      label: `${data.lep_name ?? 'Local Environmental Plan'} — height of buildings`,
      value: `Maximum building height: ${data.height_m}m`,
      detail: `This is the maximum building height mapped at THIS property's location, used as the modelled height for the hypothetical building to the north. The control applying to the neighbouring lot is not looked up separately and may differ.${data.height_m > 8 ? ' At this height, a Development Application is required (exceeds 8m CDC limit), triggering mandatory neighbour notification.' : ''}`,
      severity: data.height_m > 8 ? 'amber' : 'green',
    });
  }

  // Shadow overlap count
  const worstSc = scenarios.find(sc => sc.scenario === data.worst_case_scenario);
  const worstPct = worstSc?.shadow_overlap_fraction != null
    ? Math.round(worstSc.shadow_overlap_fraction * 100)
    : null;
  if (overlapCount > 0 && worstPct != null) {
    findings.push({
      label: `Worst case: ${SCENARIO_LABELS[data.worst_case_scenario] ?? data.worst_case_scenario}`,
      value: `${worstPct}% of lot in shadow at worst case`,
      detail: worstPct >= 50
        ? 'More than half the lot would be in shadow during the worst-case scenario. This level of overshadowing significantly impacts solar access and outdoor amenity.'
        : worstPct >= 20
        ? 'Substantial shadow impact during the worst-case scenario. This exceeds the ADG Part 3F threshold of 20% coverage of neighbouring open space at 12pm on 21 June.'
        : 'Minor shadow impact during the worst case. This is within typical urban limits and unlikely to trigger an ADG non-compliance.',
      severity: worstPct >= 50 ? 'red' : worstPct >= 20 ? 'amber' : 'green',
    });
  } else if (overlapCount === 0) {
    findings.push({
      label: 'Shadow analysis — 5 ADG test scenarios',
      value: unavailableCount > 0
        ? `No shadow overlap in the ${computedCount} computed scenarios`
        : 'No shadow overlap detected',
      detail: unavailableCount > 0
        ? `A maximum-height building modelled immediately north of this lot would not cast shadow onto the property in any of the ${computedCount} scenarios that could be computed. ${unavailableCount} of the 5 scenarios could not be assessed (marked in the scenario table), so this is not a result across all 5.`
        : 'A maximum-height building modelled immediately north of this lot would not cast shadow onto the property in any of the 5 test scenarios.',
      severity: unavailableCount > 0 ? 'amber' : 'green',
    });
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function ShadowReportDocument({ data }: { data: ShadowReportData }) {
  const scenarios = data.scenarios ?? [];
  const isPaid = data.is_paid === true;
  const isNonRes = data.zone != null &&
    NON_RESIDENTIAL_PREFIXES.some(p => data.zone!.toUpperCase().startsWith(p));
  const hasTile = !!data.tile_b64;
  const hasOverlay = hasTile && data.lot_polygon && isPaid;
  const junScenarios = hasOverlay
    ? scenarios.filter(sc => sc.scenario.startsWith('jun21'))
    : [];

  // Pages: cover+findings, detail+advice, about, aerial/overlay
  const totalPages = 1 + 1 + 1 + (hasTile ? 1 : 0);

  const findings = buildFindings(data);

  let pageCounter = 0;
  const nextPage = () => ++pageCounter;

  return (
    <Document title={`Shadow Report — ${data.address}`} author="PlotDetect">

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + Findings + Scenario table                           */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />
        <Text style={s.h1}>Construction Shadow Detector</Text>
        <Text style={s.subhead}>{data.address}</Text>
        {data.lga_name && (
          <Text style={{ fontSize: 9, color: GRAY_500, marginBottom: 2 }}>{data.lga_name} LGA</Text>
        )}
        <Text style={s.dateText}>Report date: {data.run_date}</Text>
        <PreparedBy firmName={data.firm_name} />

        {/* Key findings */}
        <Text style={s.sectionTitle}>Key findings</Text>
        {findings.map((f) => (
          <FindingRow key={f.label} finding={f} />
        ))}

        {/* Scenario table */}
        <Text style={[s.sectionTitle, { marginTop: 12 }]}>Shadow impact by scenario (ADG test dates)</Text>
        <View style={s.tableHeader}>
          <Text style={[s.colDate, s.colHeaderText]}>Date and time</Text>
          <Text style={[s.colReach, s.colHeaderText]}>Reach</Text>
          <Text style={[s.colDir, s.colHeaderText]}>Direction</Text>
          <Text style={[s.colCoverage, s.colHeaderText]}>Coverage</Text>
        </View>
        {(() => {
          const visibleScenarios = isPaid ? scenarios : scenarios.slice(0, 2);
          const gatedCount = isPaid ? 0 : Math.max(0, scenarios.length - 2);
          return (
            <>
              {visibleScenarios.map((sc) => {
                const pct = sc.shadow_overlap_fraction != null
                  ? Math.round(sc.shadow_overlap_fraction * 100) : null;
                const pillColor = coveragePillColor(pct);
                const isWorstCase = sc.scenario === data.worst_case_scenario;
                // A scenario with no result must not look like a row with a
                // missing number. It spans the measurement columns with one
                // labelled statement instead — a direction printed beside
                // "not assessed" reads as a partial result, and the bearing
                // survives an unavailable scenario because it comes from the
                // sun's position rather than from the lot geometry that failed.
                if (isScenarioUnavailable(sc)) {
                  return (
                    <View key={sc.scenario} style={[s.tableRow, { backgroundColor: AMBER_LIGHT }]}>
                      <Text style={s.colDate}>
                        {SCENARIO_LABELS[sc.scenario] ?? sc.scenario}
                      </Text>
                      <Text style={{ flex: 1, fontSize: 7.5, color: GRAY_700 }}>
                        {`${SCENARIO_NOT_ASSESSED_LABEL} — ${scenarioUnavailableMessage(sc.error_note)}`}
                      </Text>
                    </View>
                  );
                }
                return (
                  <View key={sc.scenario} style={[s.tableRow, isWorstCase ? { backgroundColor: TEAL_LIGHT } : {}]}>
                    <Text style={s.colDate}>
                      {SCENARIO_LABELS[sc.scenario] ?? sc.scenario}
                      {isWorstCase ? ' ★' : ''}
                    </Text>
                    <Text style={s.colReach}>
                      {sc.shadow_length_m != null && sc.shadow_length_m > 0
                        ? `${sc.shadow_length_m.toFixed(0)} m` : '—'}
                    </Text>
                    <Text style={s.colDir}>
                      {sc.shadow_direction_deg != null ? bearingToCompass(sc.shadow_direction_deg) : '—'}
                    </Text>
                    <Text style={[s.colCoverage, { color: pillColor.fg }]}>
                      {pct != null ? `${pct}%` : '—'}
                    </Text>
                  </View>
                );
              })}
              {gatedCount > 0 && (
                <View style={[s.tableRow, { backgroundColor: '#f9fafb', justifyContent: 'center' }]}>
                  <Text style={{ fontSize: 8, color: TEAL, textAlign: 'center', width: '100%' }}>
                    {`+ ${gatedCount} more scenarios in full report — plotdetect.com.au`}
                  </Text>
                </View>
              )}
            </>
          );
        })()}

        <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 6 }}>
          {isPaid
            ? '★ worst-case scenario · Coverage = fraction of subject lot in shadow'
            : 'Coverage = fraction of subject lot in shadow · Full report includes all 5 ADG test scenarios'}
        </Text>

        {/* Warnings */}
        {data.warnings && data.warnings.length > 0 && (
          <View style={{ marginTop: 8 }}>
            {data.warnings.map((w, i) => (
              <View key={i} style={{ backgroundColor: AMBER_LIGHT, borderLeft: `3 solid ${AMBER}`, paddingVertical: 6, paddingHorizontal: 8, marginBottom: 4, borderRadius: 2 }}>
                <Text style={{ fontSize: 7.5, color: GRAY_700 }}>{w}</Text>
              </View>
            ))}
          </View>
        )}

        <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 8, fontStyle: 'italic' }}>
          {'Data valid as of ' + data.run_date + '. Re-run if the applicable LEP has been updated or before lodging a DA objection.'}
        </Text>

        <Footer pageNum={nextPage()} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 2: Paid detail + Advice + Methodology                          */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        {/* Seasonal summary — paid */}
        {isPaid && (() => {
          const winter = scenarios.filter(sc => sc.scenario.startsWith('jun21_'));
          const spring = scenarios.filter(sc => sc.scenario === 'sep21_12pm');
          const summer = scenarios.filter(sc => sc.scenario === 'dec21_12pm');
          function worstPct(group: ShadowScenario[]) {
            const vals = group
              .map(sc => sc.shadow_overlap_fraction != null ? Math.round(sc.shadow_overlap_fraction * 100) : null)
              .filter((v): v is number => v !== null);
            return vals.length ? Math.max(...vals) : null;
          }
          const seasons = [
            { season: 'Winter (21 Jun)', pct: worstPct(winter) },
            { season: 'Spring (21 Sep)', pct: worstPct(spring) },
            { season: 'Summer (21 Dec)', pct: worstPct(summer) },
          ];
          return (
            <>
              <PaidSectionHeader title="Seasonal shadow analysis — paid data" />
              <View style={s.tableHeader}>
                <Text style={[{ flex: 3 }, s.colHeaderText]}>Season</Text>
                <Text style={[{ flex: 1.5 }, s.colHeaderText, { textAlign: 'right' }]}>Worst coverage</Text>
                <Text style={[{ flex: 1.5 }, s.colHeaderText, { textAlign: 'right' }]}>Flag</Text>
              </View>
              {seasons.map(({ season, pct }) => {
                const pill = coveragePillColor(pct);
                const flag = pct != null && pct > 20 ? 'Above 20%' : pct != null ? 'Within limit' : 'No data';
                const flagColor = pct != null && pct > 20 ? RED : GRAY_500;
                return (
                  <View key={season} style={s.tableRow}>
                    <Text style={[{ flex: 3 }, s.colDate]}>{season}</Text>
                    <Text style={[{ flex: 1.5, textAlign: 'right', fontSize: 8.5 }, { color: pill.fg }]}>
                      {pct != null ? `${pct}%` : '—'}
                    </Text>
                    <Text style={[{ flex: 1.5, textAlign: 'right', fontSize: 8, color: flagColor }]}>{flag}</Text>
                  </View>
                );
              })}
              <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 4 }}>
                ADG Part 3F threshold: no more than 20% of neighbouring open space in shadow at 12pm on 21 June.
              </Text>
            </>
          );
        })()}

        {/* Objection-ready paragraph — paid, only when ADG concern is a
            VERDICT (=== false). null is not-assessed, not a concern (fix 1). */}
        {isPaid && data.adg_compliant === false && !isNonRes && (() => {
          const worstSc = scenarios.find(sc => sc.scenario === data.worst_case_scenario);
          const worstPct = worstSc?.shadow_overlap_fraction != null
            ? Math.round(worstSc.shadow_overlap_fraction * 100) : null;
          const worstLabel = data.worst_case_scenario
            ? (SCENARIO_LABELS[data.worst_case_scenario] ?? data.worst_case_scenario) : 'the worst-case scenario';
          return (
            <View style={{ backgroundColor: TEAL_LIGHT, borderWidth: 1, borderColor: '#99f6e4', borderRadius: 4, padding: 10, marginTop: 12, marginBottom: 8 }}>
              <Text style={{ fontSize: 7.5, fontFamily: 'Helvetica-Bold', color: TEAL, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
                Objection-ready paragraph
              </Text>
              <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.6, fontStyle: 'italic' }}>
                {`"Screening modelling I have obtained for ${data.address} indicates that a rectangular building envelope of ${data.height_m}m — the maximum height mapped at my own property under the ${data.lep_name ?? 'applicable LEP'}, positioned immediately north of my boundary — would place ${worstPct != null ? `${worstPct}%` : 'a significant proportion'} of my property in shadow at ${worstLabel}. The Apartment Design Guide (2015) Part 3F requires a minimum of 2 hours of direct sunlight to living areas between 9am and 3pm on 21 June. On that basis I ask that the shadow impact of the proposed development, as designed, be assessed against that requirement under Section 4.15(1)(a)(iii) of the Environmental Planning and Assessment Act 1979."`}
              </Text>
              <Text style={{ fontSize: 7, color: GRAY_500, marginTop: 6 }}>
                Copy this into your council DA objection submission during the notification period. It is deliberately worded as screening modelling of a generic envelope, because that is what it is: the figure comes from a rectangle offset from your own boundary using your own height control, not from the lodged application&apos;s drawings and not from the neighbouring lot&apos;s own control. Presenting it as the proposed building&apos;s shadow figure would misstate it to the council.
              </Text>
            </View>
          );
        })()}

        {/* Free upsell */}
        {!isPaid && (
          <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 12, marginBottom: 12 }}>
            <Text style={{ fontSize: 9, color: GRAY_700, marginBottom: 6 }}>
              The paid report includes:
            </Text>
            {[
              'All 5 ADG test scenarios (free shows 2)',
              'Seasonal shadow summary with ADG thresholds',
              'Shadow diagram overlays on aerial imagery',
              'Objection-ready paragraph (if ADG solar access test not met)',
              'Data currency and methodology details',
            ].map((item) => (
              <View key={item} style={{ flexDirection: 'row', alignItems: 'flex-start', marginBottom: 3 }}>
                <Text style={{ fontSize: 8, color: TEAL, marginRight: 4 }}>•</Text>
                <Text style={{ fontSize: 8, color: GRAY_700 }}>{item}</Text>
              </View>
            ))}
            <Text style={{ fontSize: 8, color: TEAL, fontFamily: 'Helvetica-Bold', marginTop: 6 }}>
              Unlock at plotdetect.com.au — $29
            </Text>
          </View>
        )}

        <View style={s.divider} />

        {/* Referrals */}
        <View style={{ backgroundColor: TEAL_LIGHT, borderRadius: 4, padding: 10, marginBottom: 8, borderWidth: 1, borderColor: '#99f6e4' }}>
          <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
            Next steps
          </Text>
          <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
            A registered town planner can advise on lodging a formal objection or requesting independent shadow modelling as part of a DA response. A solicitor can advise on rights during the neighbour notification period.
          </Text>
        </View>

        <ReferralLinks links={[
          { label: 'Town planner', url: 'https://www.planning.org.au/find-a-planner', urlDisplay: 'planning.org.au/find-a-planner' },
          { label: 'Legal advice (DA objections)', url: 'https://www.lawsociety.com.au/for-the-public/find-a-lawyer', urlDisplay: 'lawsociety.com.au/find-a-lawyer' },
        ]} />

        {isPaid && (
          <DataCurrencyTable rows={[
            { source: 'NSW Planning Portal (lot boundary + height controls)', type: 'Live API query', currency: `Queried ${data.run_date}` },
            { source: 'Shadow geometry (pybdshadow)', type: 'Computed', currency: 'Analytical model' },
          ]} />
        )}

        {/* Methodology — compact */}
        <Text style={s.sectionTitle}>Methodology</Text>
        <Text style={s.bodyText}>
          Shadow geometry computed using the pybdshadow shadow-casting model, which derives sun position from the modelled date and time, for ADG test dates (21 Jun, 21 Sep, 21 Dec). Times shown are local wall-clock times for New South Wales, with daylight saving applied where it is in force — the 21 December scenario is AEDT. The compass direction shown for each scenario is calculated for this address, from the same sun position used to cast the shadow. Building height from the height control mapped at this property&apos;s location. The modelled building north of the lot is a rectangle offset from the subject boundary, not a surveyed neighbouring parcel.
        </Text>

        <Text style={[s.sectionTitle, { marginTop: 4 }]}>Disclaimer</Text>
        <Text style={s.bodyText}>
          This is a worst-case envelope model — not a design-specific shadow study.
          A formal shadow impact assessment by a qualified town planner or architect is
          required for DA submission.
        </Text>
        <Text style={[s.bodyText, { color: GRAY_500 }]}>
          Report generated by PlotDetect · plotdetect.com.au · {data.run_date}
        </Text>

        {data.qr_b64 && data.shareable_url && (
          <QRBlock url={data.shareable_url} qr_b64={data.qr_b64} />
        )}

        <Footer pageNum={nextPage()} total={totalPages} />
      </Page>

      {/* About page */}
      <AboutPage
        logo_b64={data.logo_b64}
        pageNum={nextPage()}
        total={totalPages}
        reportName="Shadow Detector"
      />

      {/* ------------------------------------------------------------------ */}
      {/* Shadow diagrams or plain aerial (optional)                           */}
      {/* ------------------------------------------------------------------ */}
      {hasTile && (
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />
          {hasOverlay ? (
            <>
              <Text style={s.sectionTitle}>Shadow diagrams — 21 June (ADG test date)</Text>
              <Text style={[s.bodyText, { color: GRAY_500, marginBottom: 10 }]}>
                Teal outline = subject lot boundary. Orange fill = shadow cast by a hypothetical {data.height_m}m building. The dashed outline is where that building is modelled — a rectangle offset north of your own boundary by your own lot depth, NOT the neighbouring parcel, whose real boundary and building position are not known to this model.
              </Text>
              <View style={{ flexDirection: 'row', gap: 16, marginBottom: 10 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <View style={{ width: 10, height: 10, backgroundColor: '#0d9488', opacity: 0.4, borderRadius: 1 }} />
                  <Text style={{ fontSize: 7.5, color: GRAY_500 }}>Subject lot</Text>
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <View style={{ width: 10, height: 10, backgroundColor: '#f97316', opacity: 0.7, borderRadius: 1 }} />
                  <Text style={{ fontSize: 7.5, color: GRAY_500 }}>Shadow on lot</Text>
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <View style={{ width: 10, height: 10, borderWidth: 1, borderColor: '#6366f1', borderStyle: 'dashed', borderRadius: 1 }} />
                  <Text style={{ fontSize: 7.5, color: GRAY_500 }}>Modelled building</Text>
                </View>
              </View>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, justifyContent: 'space-between' }}>
                {junScenarios.map((sc) => (
                  <View key={sc.scenario} style={{ width: '31%' }}>
                    <AerialWithOverlay
                      tile_b64={data.tile_b64!}
                      center={[data.lng, data.lat]}
                      zoom="property"
                      label={SCENARIO_LABELS[sc.scenario] ?? sc.scenario}
                      attribution=""
                      layers={[
                        { geojson: sc.shadow_on_lot, fill: '#f97316', fillOpacity: 0.55, stroke: '#ea580c', strokeWidth: 1 },
                        { geojson: data.north_proxy_polygon, dasharray: '6,4', stroke: '#6366f1', strokeWidth: 1.5 },
                        { geojson: data.lot_polygon, fill: '#0d9488', fillOpacity: 0.15, stroke: '#0d9488', strokeWidth: 2 },
                      ]}
                    />
                  </View>
                ))}
              </View>
            </>
          ) : (
            <>
              <Text style={s.sectionTitle}>Property aerial view</Text>
              <Text style={[s.bodyText, { color: GRAY_500, marginBottom: 10 }]}>
                NSW SIX Maps aerial imagery for context.
              </Text>
              <Image
                src={`data:image/png;base64,${data.tile_b64}`}
                style={{ width: '100%', borderRadius: 4 }}
              />
            </>
          )}
          <Text style={[s.bodyText, { fontSize: 7, color: GRAY_500, marginTop: 6 }]}>
            NSW SIX Maps (LPI_Imagery_Best) — CC-BY 4.0 NSW Government
          </Text>
          <Footer pageNum={nextPage()} total={totalPages} />
        </Page>
      )}

    </Document>
  );
}
