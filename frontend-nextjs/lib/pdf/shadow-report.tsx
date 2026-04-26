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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ShadowScenario {
  scenario: string;
  label: string;
  date: string;
  time_local: string;
  shadow_length_m: number;
  shadow_overlap_fraction: number;
  shadow_direction_deg: number;
  overlaps_subject_lot: boolean;
}

export interface ShadowReportData {
  address: string;
  run_date: string;
  lat: number;
  lng: number;
  zone: string | null;
  // outputs
  height_m: number;
  height_source: string | null;
  lep_name: string | null;
  scenarios: ShadowScenario[];
  construction_change_score: number | null;
  construction_change_detected: boolean;
  adg_compliant: boolean;
  worst_case_scenario: string;
  confidence: string;
  data_sources: string[];
  warnings?: string[];
  is_paid?: boolean;
  tile_b64: string | null;
  logo_b64?: string | null;
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
  // ADG badge
  adgBadge: {
    paddingVertical: 5, paddingHorizontal: 12,
    borderRadius: 4, alignSelf: 'flex-start', marginBottom: 16,
  },
  adgText: { fontSize: 11, fontFamily: 'Helvetica-Bold' },
  // Stats
  statGrid: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  statCard: {
    flex: 1, backgroundColor: GRAY_100, borderRadius: 4, padding: 10,
  },
  statLabel: { fontSize: 7, color: GRAY_500, marginBottom: 3 },
  statValue: { fontSize: 16, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  statSub:   { fontSize: 7.5, color: GRAY_700, marginTop: 2 },
  // Scenarios table
  tableHeader: {
    flexDirection: 'row', paddingVertical: 5,
    borderBottom: `1 solid ${GRAY_300}`,
  },
  tableRow: {
    flexDirection: 'row', paddingVertical: 7,
    borderBottom: `1 solid ${GRAY_300}`,
  },
  colDate:     { flex: 3, fontSize: 8.5, color: GRAY_700 },
  colReach:    { flex: 1.2, fontSize: 8.5, color: GRAY_700, textAlign: 'right' },
  colDir:      { flex: 0.8, fontSize: 8.5, color: GRAY_700, textAlign: 'right' },
  colCoverage: { flex: 1.2, fontSize: 8.5, textAlign: 'right' },
  colHeaderText: { fontSize: 7, color: GRAY_500, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' },
  footer: {
    position: 'absolute', bottom: 28, left: 48, right: 48,
    flexDirection: 'row', justifyContent: 'space-between',
  },
  footerText: { fontSize: 7, color: GRAY_500 },
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function bearingToCompass(deg: number): string {
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  return dirs[Math.round(deg / 45) % 8];
}

function seasonalSummary(scenarios: ShadowScenario[]) {
  const winter = scenarios.filter(sc => sc.scenario.startsWith('jun21_'));
  const spring = scenarios.filter(sc => sc.scenario === 'sep21_12pm');
  const summer = scenarios.filter(sc => sc.scenario === 'dec21_12pm');

  function worstPct(group: ShadowScenario[]) {
    const vals = group
      .map(sc => sc.shadow_overlap_fraction != null ? Math.round(sc.shadow_overlap_fraction * 100) : null)
      .filter((v): v is number => v !== null);
    return vals.length ? Math.max(...vals) : null;
  }

  return [
    { season: 'Winter (21 Jun)', pct: worstPct(winter) },
    { season: 'Spring (21 Sep)', pct: worstPct(spring) },
    { season: 'Summer (21 Dec)', pct: worstPct(summer) },
  ];
}

function coveragePillColor(pct: number | null): { bg: string; fg: string } {
  if (pct == null) return { bg: GRAY_100, fg: GRAY_500 };
  if (pct >= 70) return { bg: RED_LIGHT,   fg: RED    };
  if (pct >= 40) return { bg: AMBER_LIGHT, fg: AMBER  };
  if (pct >  0)  return { bg: '#fefce8',   fg: '#ca8a04' };
  return { bg: GRAY_100, fg: GRAY_500 };
}

function ValidityNote({ runDate }: { runDate: string }) {
  return (
    <Text style={{ fontSize: 7.5, color: GRAY_500, marginTop: 6, fontStyle: 'italic' }}>
      {'Data valid as of ' + runDate + '. Planning controls are amended regularly - re-run this report before exchange of contracts.'}
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
        A registered town planner can advise on lodging a formal objection or requesting independent shadow modelling as part of a DA response. A solicitor can advise on rights during the neighbour notification period.
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
    <View style={s.footer} fixed>
      <Text style={s.footerText}>Construction Shadow Detector — plotdetect.com.au</Text>
      <Text style={s.footerText}>{pageNum} / {total}</Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function ShadowReportDocument({ data }: { data: ShadowReportData }) {
  const scenarios = data.scenarios ?? [];
  const overlapCount = scenarios.filter(s => s.overlaps_subject_lot).length;
  const isNonResidential =
    data.zone != null &&
    NON_RESIDENTIAL_PREFIXES.some(p => data.zone!.toUpperCase().startsWith(p));

  const adgColor = isNonResidential
    ? { bg: GRAY_100,    fg: GRAY_700 }
    : data.adg_compliant
    ? { bg: GREEN_LIGHT, fg: GREEN }
    : { bg: RED_LIGHT,   fg: RED   };

  const adgLabel = isNonResidential
    ? 'ADG — indicative only'
    : data.adg_compliant
    ? 'ADG compliant'
    : 'ADG concern';

  const summaryText = isNonResidential
    ? overlapCount === 0
      ? `A maximum-height building on an adjacent lot would not significantly shadow this property across any of the 5 test scenarios. ADG solar access requirements apply to residential apartment buildings only — this result is indicative.`
      : `A maximum-height building on an adjacent lot would significantly shadow this property on ${overlapCount} of 5 scenarios. ADG solar access requirements apply to residential apartment buildings only — this result is indicative.`
    : data.adg_compliant
    ? overlapCount === 0
      ? `A maximum-height building on an adjacent lot would not significantly shadow this property across any of the 5 test scenarios. ADG solar access requirements are met.`
      : `A maximum-height building on an adjacent lot would significantly shadow this property on ${overlapCount} of 5 scenarios, but still meets ADG solar access requirements (2 hours between 9 am–3 pm on 21 June).`
    : `A maximum-height building on an adjacent lot would significantly shadow this property on ${overlapCount} of 5 scenarios and may not meet the ADG 2-hour solar access requirement on 21 June.`;

  const totalPages = data.tile_b64 ? 3 : 2;

  return (
    <Document title={`Shadow Report — ${data.address}`} author="PlotDetect">

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + ADG verdict + Scenarios table                       */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />
        <Text style={s.h1}>Construction Shadow Detector</Text>
        <Text style={s.subhead}>{data.address}</Text>
        <Text style={s.dateText}>Report date: {data.run_date}</Text>
        <ValidityNote runDate={data.run_date} />

        {/* ADG verdict badge */}
        <View style={[s.adgBadge, { backgroundColor: adgColor.bg }]}>
          <Text style={[s.adgText, { color: adgColor.fg }]}>{adgLabel}</Text>
        </View>

        <Text style={[s.bodyText, { marginBottom: 8 }]}>{summaryText}</Text>

        {/* ADG non-compliance consequence — only when concern flagged */}
        {!data.adg_compliant && data.zone !== null && (
          <View style={{ backgroundColor: '#fff7ed', borderRadius: 4, padding: 8, marginBottom: 12, borderWidth: 1, borderColor: '#fed7aa' }}>
            <Text style={{ fontSize: 8, color: '#9a3412', lineHeight: 1.5 }}>
              ADG 2015 Part 3D sets a minimum 3-hour solar access requirement for living areas. Overshadowing of this extent may constitute grounds for formal objection during the DA neighbour notification period. Council is not required to approve a DA that fails the ADG solar access test.
            </Text>
          </View>
        )}

        <View style={s.divider} />

        {/* Stats */}
        <Text style={s.sectionTitle}>Key parameters</Text>
        <View style={s.statGrid}>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Max building height modelled</Text>
            <Text style={s.statValue}>{data.height_m} m</Text>
            <Text style={s.statSub}>{data.lep_name ?? 'Local Environmental Plan'}</Text>
            {data.height_source === 'default' && (
              <Text style={[s.statSub, { color: AMBER }]}>
                No HOB control found — 9 m default used
              </Text>
            )}
          </View>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Construction activity</Text>
            <Text style={[s.statValue, { fontSize: 12 }]}>
              {data.construction_change_detected ? 'Detected' : 'None detected'}
            </Text>
            <Text style={s.statSub}>
              {data.construction_change_score != null
                ? `BSI Δ ${data.construction_change_score.toFixed(3)} · threshold 0.120`
                : 'Sentinel-2 · past 90 days vs 12-month baseline'}
            </Text>
          </View>
        </View>

        <View style={s.divider} />

        {/* Scenarios table */}
        <Text style={s.sectionTitle}>Shadow impact by scenario (ADG test dates)</Text>

        {/* Table header */}
        <View style={s.tableHeader}>
          <Text style={[s.colDate, s.colHeaderText]}>Date and time</Text>
          <Text style={[s.colReach, s.colHeaderText]}>Reach</Text>
          <Text style={[s.colDir, s.colHeaderText]}>Direction</Text>
          <Text style={[s.colCoverage, s.colHeaderText]}>Coverage</Text>
        </View>

        {scenarios.map((sc) => {
          const pct = sc.shadow_overlap_fraction != null
            ? Math.round(sc.shadow_overlap_fraction * 100)
            : null;
          const pillColor = coveragePillColor(pct);
          const isWorstCase = sc.scenario === data.worst_case_scenario;

          return (
            <View
              key={sc.scenario}
              style={[s.tableRow, isWorstCase
                ? { backgroundColor: TEAL_LIGHT }
                : {}
              ]}
            >
              <Text style={s.colDate}>
                {SCENARIO_LABELS[sc.scenario] ?? sc.scenario}
                {isWorstCase ? ' ★' : ''}
              </Text>
              <Text style={s.colReach}>
                {sc.shadow_length_m > 0 ? `${sc.shadow_length_m.toFixed(0)} m` : '—'}
              </Text>
              <Text style={s.colDir}>
                {sc.shadow_direction_deg != null
                  ? bearingToCompass(sc.shadow_direction_deg)
                  : '—'}
              </Text>
              <Text style={[s.colCoverage, { color: pillColor.fg }]}>
                {pct != null ? `${pct}%` : '—'}
              </Text>
            </View>
          );
        })}

        <Text style={[s.bodyText, { marginTop: 8, fontSize: 7.5, color: GRAY_500 }]}>
          * worst-case scenario · Coverage = fraction of subject lot in shadow
        </Text>

        {/* Seasonal summary — paid */}
        {data.is_paid !== false && (() => {
          const seasons = seasonalSummary(scenarios);
          return (
            <View style={{ marginTop: 16 }}>
              <Text style={s.sectionTitle}>Seasonal shadow summary</Text>
              {/* Header */}
              <View style={[s.tableHeader]}>
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
              <Text style={[s.bodyText, { marginTop: 4, fontSize: 7.5, color: GRAY_500 }]}>
                ADG Part 3F threshold: no more than 20% of a neighbouring open space in shadow at 12pm on 21 June.
              </Text>
            </View>
          );
        })()}

        {/* Warnings */}
        {data.warnings && data.warnings.length > 0 && (
          <View style={{ marginTop: 12 }}>
            {data.warnings.map((w, i) => (
              <View key={i} style={{
                backgroundColor: AMBER_LIGHT, borderLeft: `3 solid ${AMBER}`,
                paddingVertical: 6, paddingHorizontal: 8, marginBottom: 6, borderRadius: 2,
              }}>
                <Text style={{ fontSize: 8, color: GRAY_700 }}>{w}</Text>
              </View>
            ))}
          </View>
        )}

        <Footer pageNum={1} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 2: Methodology + Disclaimer                                     */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        <Text style={s.sectionTitle}>Methodology</Text>
        <Text style={s.bodyText}>
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>Authority. </Text>
          Test dates follow the NSW Apartment Design Guide (DPHI, 2015), Part 3F — Solar and
          Daylight Access. The critical test is 21 June (winter solstice), when shadows are longest.
        </Text>
        <Text style={s.bodyText}>
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>Solar position. </Text>
          Sun azimuth and altitude are calculated using the NREL Solar Position Algorithm
          (Reda and Andreas, 2004). Verified for Southern Hemisphere latitudes.
        </Text>
        <Text style={s.bodyText}>
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>Building height. </Text>
          The model uses the maximum permissible building height from the applicable LEP.
          The northern neighbour footprint is approximated using the subject lot boundary
          offset one lot-depth northward — a conservative worst-case proxy.
        </Text>
        <Text style={s.bodyText}>
          <Text style={{ fontFamily: 'Helvetica-Bold' }}>Construction activity. </Text>
          Detected using the Bare Soil Index (BSI) applied to Sentinel-2 imagery.
          A BSI change score above 0.120 between recent scenes and the 12-month baseline
          indicates demolition, excavation, or site clearing.
        </Text>

        <View style={s.divider} />

        <ReferralBox />

        <Text style={s.sectionTitle}>Disclaimer</Text>
        <Text style={s.bodyText}>
          This is a worst-case envelope model — not a design-specific shadow study.
          A formal shadow impact assessment by a qualified town planner or architect is
          required for DA submission under the Environmental Planning and Assessment Act 1979.
        </Text>
        <Text style={[s.bodyText, { color: GRAY_500 }]}>
          Data: {(data.data_sources ?? []).join(' · ')} · Report generated {data.run_date} · plotdetect.com.au
        </Text>

        <Footer pageNum={2} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 3: Aerial tile (optional)                                       */}
      {/* ------------------------------------------------------------------ */}
      {data.tile_b64 && (
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />
          <Text style={s.sectionTitle}>Property aerial view</Text>
          <Text style={[s.bodyText, { color: GRAY_500, marginBottom: 10 }]}>
            NSW SIX Maps aerial imagery for context. Shadow polygons cannot be shown in a
            static image — see the interactive tool at plotdetect.com.au for map view.
          </Text>
          <Image
            src={`data:image/png;base64,${data.tile_b64}`}
            style={{ width: '100%', borderRadius: 4 }}
          />
          <Text style={[s.bodyText, { fontSize: 7, color: GRAY_500, marginTop: 6 }]}>
            © NSW SIX Maps (LPI_Imagery_Best) — CC-BY 4.0 NSW Government · for reference only
          </Text>
          <Footer pageNum={3} total={totalPages} />
        </Page>
      )}

    </Document>
  );
}
