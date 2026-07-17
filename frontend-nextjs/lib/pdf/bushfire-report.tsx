/**
 * Bushfire Pre-Screen Report PDF
 * Generated server-side via @react-pdf/renderer renderToBuffer().
 * Data from property_reports table (product='bushfire').
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
import { WhatThisMeans, PlotDetectFooter, AboutPage, ReferralLinks, InsurerChecklist, DataCurrencyTable, QRBlock, PreparedBy } from './shared-components';
import { AerialWithOverlay } from './map-overlay';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CrossOverlay {
  type: string;
  value: string;
  source: string;
}

interface BushfireCompliance {
  state_legislation: string | null;
  rfs_referral_required: boolean | null;
  rfs_referral_note?: string | null;
  rfs_referral_triggers: string[] | null;
  cdc_pathway_available: boolean | null;
  clearing_10_50_entitled: boolean | null;
  clearing_10_50_exceptions: string | null;
  cross_overlays: CrossOverlay[] | null;
  estimated_consultant_costs: string | null;
  zone: string | null;
  compliance_depth: string;
  legislation_url: string | null;
}

export interface BushfireReportData {
  address: string;
  run_date: string;
  lat: number;
  lng: number;
  // outputs
  is_bushfire_prone: boolean | null;
  designation_source: string | null;
  designation_category: string | null;
  designation_guideline: string | null;
  estimated_bal_band: string | null;
  bal_assessment_likely_required: boolean | null;
  bal_formal_assessment_cost_range: string | null;
  bal_assessor_directory_url: string | null;
  fire_signal: string;
  compliance: BushfireCompliance;
  data_currency: string;
  // meta
  confidence: string;
  data_sources: string[];
  is_paid?: boolean;
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

const TEAL       = '#0f766e';
const TEAL_LIGHT = '#f0fdfa';
const RED        = '#dc2626';
const AMBER      = '#d97706';
const AMBER_LIGHT = '#fffbeb';
const GREEN      = '#16a34a';
const GRAY_900   = '#111827';
const GRAY_700   = '#374151';
const GRAY_500   = '#6b7280';
const GRAY_300   = '#d1d5db';
const GRAY_100   = '#f3f4f6';

const SIGNAL_COLORS: Record<string, { bg: string; fg: string; label: string }> = {
  none:       { bg: '#ecfdf5', fg: GREEN,  label: 'Not bushfire prone' },
  low:        { bg: '#fefce8', fg: '#ca8a04', label: 'Bushfire prone — lower category' },
  moderate:   { bg: '#fff7ed', fg: AMBER,  label: 'Bushfire prone — moderate category' },
  elevated:   { bg: '#fef2f2', fg: RED,    label: 'Bushfire prone — highest category' },
  unavailable:{ bg: GRAY_100,  fg: GRAY_500, label: 'Data unavailable' },
};

const BAL_COLORS: Record<string, { bg: string; fg: string }> = {
  'BAL-LOW':          { bg: '#ecfdf5', fg: GREEN },
  'BAL-12.5':         { bg: '#fefce8', fg: '#ca8a04' },
  'BAL-19':           { bg: '#fefce8', fg: '#ca8a04' },
  'BAL-29':           { bg: '#fff7ed', fg: AMBER },
  'BAL-40 to BAL-FZ': { bg: '#fef2f2', fg: RED },
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
  statGrid: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  statCard: { flex: 1, backgroundColor: GRAY_100, borderRadius: 4, padding: 10 },
  statLabel: { fontSize: 7, color: GRAY_500, marginBottom: 3 },
  statValue: { fontSize: 14, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
  statSub:   { fontSize: 7.5, color: GRAY_700, marginTop: 2 },
  tableHeader: {
    flexDirection: 'row', backgroundColor: GRAY_900,
    paddingVertical: 5, paddingHorizontal: 8, borderRadius: 3, marginBottom: 2,
  },
  tableHeaderCell: { color: '#ffffff', fontSize: 7.5, fontFamily: 'Helvetica-Bold' },
  tableRow: {
    flexDirection: 'row', paddingVertical: 5, paddingHorizontal: 8,
    borderBottomWidth: 1, borderBottomColor: GRAY_100,
  },
  tableRowAlt: { backgroundColor: GRAY_100 },
  tableCell: { fontSize: 8.5, color: GRAY_700 },
  tableCellBold: { fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: GRAY_900 },
});

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
    <PlotDetectFooter reportName="Bushfire Pre-Screen" pageNum={pageNum} total={total} />
  );
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

export function BushfireReportDocument({ data }: { data: BushfireReportData }) {
  const signal = data.fire_signal ?? 'unavailable';
  const signalMeta = SIGNAL_COLORS[signal] ?? SIGNAL_COLORS.unavailable;
  const balColors = BAL_COLORS[data.estimated_bal_band ?? ''] ?? { bg: GRAY_100, fg: GRAY_500 };
  const c = data.compliance;
  const totalPages = (data.tile_b64 ? 3 : 2) + 1; // +1 for About page

  return (
    <Document title={`Bushfire Pre-Screen — ${data.address}`} author="PlotDetect">

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 1: Cover + BFPL + BAL + Signal                                 */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />
        <Text style={s.h1}>Bushfire Pre-Screen Report</Text>
        <Text style={s.subhead}>{data.address}</Text>
        <Text style={s.dateText}>Report date: {data.run_date}</Text>
        <PreparedBy firmName={data.firm_name} />

        <Text style={{ fontSize: 7.5, color: GRAY_500, fontStyle: 'italic', marginBottom: 20 }}>
          Data valid as of {data.run_date}. RFS Bush Fire Prone Land maps are updated periodically. Re-run before development lodgement.
        </Text>

        {/* Signal badge */}
        <View style={{
          backgroundColor: signalMeta.bg, borderRadius: 4, padding: 10,
          marginBottom: 16, borderWidth: 1, borderColor: signalMeta.fg + '33',
        }}>
          <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: signalMeta.fg }}>
            {signalMeta.label}
          </Text>
        </View>

        {/* A1: Plain-English interpretation — paid */}
        {data.is_paid === true && (() => {
          if (!data.is_bushfire_prone) {
            return (
              <WhatThisMeans>
                This property is not mapped as bushfire prone land. No BAL assessment, RFS referral, or AS 3959 construction standards are required. Standard development pathways apply.
              </WhatThisMeans>
            );
          }
          if (signal === 'elevated') {
            return (
              <WhatThisMeans>
                {`This property is in a high-risk bushfire category (${data.designation_category ?? 'Category 1'}). A formal BAL assessment is mandatory before any development. The CDC pathway is not available — a DA to council with RFS referral under s4.14 is required. Estimated BAL: ${data.estimated_bal_band ?? 'BAL-40 to BAL-FZ'}. Engage a qualified BAL assessor as the first step.`}
              </WhatThisMeans>
            );
          }
          return (
            <WhatThisMeans>
              {`This property is mapped as bushfire prone (${data.designation_category ?? 'bushfire prone'}). A BAL assessment by a qualified practitioner is required before development. Estimated BAL: ${data.estimated_bal_band ?? 'unknown'}. ${c.cdc_pathway_available ? 'The CDC pathway is available (BAL 29 or lower).' : 'A DA to council with RFS referral is required.'}`}
            </WhatThisMeans>
          );
        })()}

        {/* BFPL + BAL stats */}
        <Text style={s.sectionTitle}>Bush Fire Prone Land designation</Text>
        <View style={s.statGrid}>
          <View style={s.statCard}>
            <Text style={s.statLabel}>BFPL category</Text>
            <Text style={s.statValue}>
              {data.is_bushfire_prone === null
                ? 'Unavailable'
                : data.is_bushfire_prone
                ? (data.designation_category ?? 'Bushfire prone')
                : 'Not bushfire prone'}
            </Text>
            {data.designation_guideline && (
              <Text style={s.statSub}>{data.designation_guideline}</Text>
            )}
            <Text style={[s.statSub, { color: GRAY_500 }]}>
              NSW RFS - as at {data.data_currency !== 'unknown' && data.data_currency !== 'query_failed' ? data.data_currency : 'date unavailable'}
            </Text>
          </View>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Estimated BAL band</Text>
            {data.estimated_bal_band ? (
              <>
                <View style={{
                  backgroundColor: balColors.bg, borderRadius: 3,
                  paddingVertical: 2, paddingHorizontal: 6, alignSelf: 'flex-start', marginBottom: 4,
                }}>
                  <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold', color: balColors.fg }}>
                    {data.estimated_bal_band}
                  </Text>
                </View>
                <Text style={s.statSub}>
                  {data.bal_assessment_likely_required
                    ? 'Formal BAL assessment required'
                    : 'No bushfire construction standards apply'}
                </Text>
              </>
            ) : (
              <Text style={[s.statValue, { fontSize: 10, color: GRAY_500 }]}>Not applicable</Text>
            )}
          </View>
          <View style={s.statCard}>
            <Text style={s.statLabel}>Confidence</Text>
            <Text style={[s.statValue, { fontSize: 12, textTransform: 'capitalize' }]}>
              {data.confidence}
            </Text>
          </View>
        </View>

        <View style={s.divider} />

        {/* Development implications — free (matches web view) */}
        {data.is_bushfire_prone && (
          <>
            <Text style={s.sectionTitle}>Development implications</Text>
            <View style={s.statGrid}>
              <View style={s.statCard}>
                <Text style={s.statLabel}>RFS referral</Text>
                <Text style={[s.statValue, { fontSize: 10, color: c.rfs_referral_required ? RED : c.rfs_referral_required === false ? GREEN : GRAY_500 }]}>
                  {c.rfs_referral_required == null ? 'Depends on the proposal - see s4.14 triggers' : c.rfs_referral_required ? 'Yes - s4.14 EP&A Act' : 'No'}
                </Text>
              </View>
              <View style={s.statCard}>
                <Text style={s.statLabel}>CDC pathway</Text>
                <Text style={[s.statValue, { fontSize: 10, color: c.cdc_pathway_available === false ? RED : c.cdc_pathway_available ? GREEN : GRAY_500 }]}>
                  {c.cdc_pathway_available === null ? 'Unknown' : c.cdc_pathway_available ? 'Available (BAL 29 or lower)' : 'DA required'}
                </Text>
              </View>
            </View>

            {/* RFS referral conditional note — the three-state answer explained */}
            {c.rfs_referral_required === null && c.rfs_referral_note && (
              <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 10, marginBottom: 12 }}>
                <Text style={{ fontSize: 8.5, color: GRAY_700 }}>{c.rfs_referral_note}</Text>
              </View>
            )}

            {/* 10/50 clearing — free. A null entitlement on prone land means it
                depends on the RFS 10/50 entitlement area map (conditional text). */}
            {(c.clearing_10_50_entitled !== null || c.clearing_10_50_exceptions) && (
              <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 10, marginBottom: 12 }}>
                <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 3 }}>
                  10/50 vegetation clearing
                </Text>
                <Text style={{ fontSize: 8.5, color: GRAY_700 }}>
                  {c.clearing_10_50_entitled === null
                    ? 'Depends on the RFS 10/50 entitlement area map'
                    : c.clearing_10_50_entitled ? 'Entitlement applies' : 'Does not apply'}
                  {c.clearing_10_50_exceptions ? ` - ${c.clearing_10_50_exceptions}` : ''}
                </Text>
              </View>
            )}
          </>
        )}

        {/* Consultant costs — paid */}
        {data.is_paid === true && c.estimated_consultant_costs && (
          <View style={{ backgroundColor: AMBER_LIGHT, borderRadius: 4, padding: 10, marginBottom: 12, borderWidth: 1, borderColor: '#fde68a' }}>
            <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: AMBER, marginBottom: 3 }}>
              Estimated consultant costs
            </Text>
            <Text style={{ fontSize: 8.5, color: GRAY_700 }}>{c.estimated_consultant_costs}</Text>
          </View>
        )}

        {/* BAL assessment cost — paid */}
        {data.is_paid === true && data.bal_formal_assessment_cost_range && (
          <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 10, marginBottom: 12 }}>
            <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 3 }}>
              Formal BAL assessment cost
            </Text>
            <Text style={{ fontSize: 8.5, color: GRAY_700 }}>{data.bal_formal_assessment_cost_range}</Text>
            {data.bal_assessor_directory_url && (
              <Link src={data.bal_assessor_directory_url} style={{ fontSize: 7.5, color: TEAL, marginTop: 4 }}>
                Find a qualified BAL assessor (RFS directory)
              </Link>
            )}
          </View>
        )}

        <Footer pageNum={1} total={totalPages} />
      </Page>

      {/* ------------------------------------------------------------------ */}
      {/* PAGE 2: Referral triggers + Cross-overlays + Compliance + Disclaimer */}
      {/* ------------------------------------------------------------------ */}
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        {/* RFS referral triggers — paid */}
        {data.is_paid === true && c.rfs_referral_triggers && c.rfs_referral_triggers.length > 0 && (
          <>
            <Text style={s.sectionTitle}>s4.14 referral triggers</Text>
            {c.rfs_referral_triggers.map((trigger, i) => (
              <View key={i} style={{ flexDirection: 'row', gap: 6, marginBottom: 4 }}>
                <Text style={{ fontSize: 8.5, color: TEAL }}>-</Text>
                <Text style={{ fontSize: 8.5, color: GRAY_700, flex: 1, lineHeight: 1.5 }}>{trigger}</Text>
              </View>
            ))}
          </>
        )}

        {/* Cross-overlays — paid */}
        {data.is_paid === true && c.cross_overlays && c.cross_overlays.length > 0 && (
          <>
            <Text style={s.sectionTitle}>Additional overlays at this site</Text>
            <View style={s.tableHeader}>
              <Text style={{ ...s.tableHeaderCell, flex: 1.5 }}>Overlay</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 2 }}>Value</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 1.5 }}>Source</Text>
            </View>
            {c.cross_overlays.map((overlay, i) => (
              <View key={i} style={[s.tableRow, i % 2 === 1 ? s.tableRowAlt : {}]}>
                <Text style={{ ...s.tableCellBold, flex: 1.5, textTransform: 'capitalize' }}>{overlay.type}</Text>
                <Text style={{ ...s.tableCell, flex: 2 }}>{overlay.value}</Text>
                <Text style={{ ...s.tableCell, flex: 1.5, fontSize: 7.5, color: GRAY_500 }}>{overlay.source}</Text>
              </View>
            ))}
          </>
        )}

        {/* Free placeholders for gated content */}
        {data.is_paid !== true && data.is_bushfire_prone && (
          <>
            {c.rfs_referral_triggers && c.rfs_referral_triggers.length > 0 && (
              <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 10, marginBottom: 12 }}>
                <Text style={{ fontSize: 8.5, color: GRAY_500 }}>
                  {c.rfs_referral_triggers.length} referral trigger{c.rfs_referral_triggers.length !== 1 ? 's' : ''} identified
                </Text>
                <Text style={{ fontSize: 7.5, color: TEAL, marginTop: 2 }}>
                  Full trigger details in paid report
                </Text>
              </View>
            )}
            {c.cross_overlays && c.cross_overlays.length > 0 && (
              <View style={{ backgroundColor: GRAY_100, borderRadius: 4, padding: 10, marginBottom: 12 }}>
                <Text style={{ fontSize: 8.5, color: GRAY_500 }}>
                  {c.cross_overlays.length} additional overlay{c.cross_overlays.length !== 1 ? 's' : ''} detected
                </Text>
                <Text style={{ fontSize: 7.5, color: TEAL, marginTop: 2 }}>
                  Full overlay details in paid report
                </Text>
              </View>
            )}
          </>
        )}

        {/* AS 3959 construction standards — paid */}
        {data.is_paid === true && data.is_bushfire_prone && data.estimated_bal_band && (
          <>
            <Text style={s.sectionTitle}>AS 3959 construction requirements by BAL</Text>
            <Text style={[s.bodyText, { marginBottom: 8 }]}>
              Australian Standard 3959 prescribes construction requirements based on BAL rating.
              Your estimated BAL is highlighted.
            </Text>
            <View style={s.tableHeader}>
              <Text style={{ ...s.tableHeaderCell, flex: 1 }}>BAL</Text>
              <Text style={{ ...s.tableHeaderCell, flex: 3 }}>Construction requirement</Text>
            </View>
            {[
              { bal: 'BAL-LOW', req: 'Standard construction. No additional bushfire measures.' },
              { bal: 'BAL-12.5', req: 'Ember protection. Non-combustible cladding, screened openings, tempered glass.' },
              { bal: 'BAL-19', req: 'Increased ember and radiant heat protection. Metal/fibre cement cladding, BAL-rated windows.' },
              { bal: 'BAL-29', req: 'High radiant heat. Non-combustible walls, BAL-29 windows, metal roof, enclosed subfloor.' },
              { bal: 'BAL-40', req: 'Very high radiant heat. Non-combustible construction, no timber framing exposed, fire-rated walls.' },
              { bal: 'BAL-FZ', req: 'Flame zone. Specialist design required. Non-combustible throughout, fire-engineered solution.' },
            ].map((row, i) => {
              const isActive = data.estimated_bal_band === row.bal ||
                (data.estimated_bal_band === 'BAL-40 to BAL-FZ' && (row.bal === 'BAL-40' || row.bal === 'BAL-FZ'));
              return (
                <View key={i} style={[s.tableRow, isActive ? { backgroundColor: TEAL_LIGHT } : i % 2 === 1 ? s.tableRowAlt : {}]}>
                  <Text style={{ ...s.tableCellBold, flex: 1, color: isActive ? TEAL : GRAY_900 }}>{row.bal}</Text>
                  <Text style={{ ...s.tableCell, flex: 3 }}>{row.req}</Text>
                </View>
              );
            })}
            <Text style={[s.bodyText, { fontSize: 7.5, color: GRAY_500, marginTop: 6 }]}>
              AS 3959-2018 Construction of buildings in bushfire-prone areas. BAL rating must be confirmed by a formal BAL assessment.
            </Text>
          </>
        )}

        {/* Legislation link */}
        {c.legislation_url && (
          <View style={{ marginTop: 12 }}>
            <Link src={c.legislation_url} style={{ fontSize: 8.5, color: TEAL }}>
              {c.state_legislation ?? 'View applicable legislation'}
            </Link>
          </View>
        )}

        <View style={s.divider} />

        <View style={{ backgroundColor: TEAL_LIGHT, borderRadius: 4, padding: 10, marginTop: 8, borderWidth: 1, borderColor: '#99f6e4' }}>
          <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
            Get professional advice
          </Text>
          <Text style={{ fontSize: 8, color: GRAY_700, lineHeight: 1.5 }}>
            A qualified BAL assessor can confirm the BAL rating for your site and prepare a Bushfire Assessment Report required for development applications on bushfire prone land.
          </Text>
        </View>

        <ReferralLinks links={[
          { label: 'RFS BAL assessor directory', url: 'https://www.rfs.nsw.gov.au/plan-and-prepare/building-in-a-bush-fire-area/find-a-practitioner', urlDisplay: 'rfs.nsw.gov.au/find-a-practitioner' },
          { label: 'FPA Australia', url: 'https://www.fpaa.com.au', urlDisplay: 'fpaa.com.au' },
        ]} />

        {/* A4: Insurer/lender questionnaire — bushfire */}
        {data.is_paid === true && (
          <InsurerChecklist
            title="Questions for your insurer or lender"
            questions={[
              'Does the BAL rating for this property affect my building and/or contents insurance premium?',
              'Is the property in a bushfire exclusion zone for any cover type?',
              'Does the insurer require a formal BAL assessment certificate before providing cover?',
              'Are there vegetation management requirements that affect my cover or premium?',
              'Will the lender require a bushfire assessment before unconditional finance approval?',
            ]}
          />
        )}

        {/* A2: Data currency table — paid only */}
        {data.is_paid === true && (
          <DataCurrencyTable rows={[
            { source: 'NSW RFS Bush Fire Prone Land Map', type: 'Live API query', currency: `Queried ${data.run_date}` },
            { source: 'NSW Planning Portal (EPI overlays)', type: 'Live API query', currency: `Queried ${data.run_date}` },
            { source: 'NSW Heritage Register', type: 'Live API query', currency: `Queried ${data.run_date}` },
          ]} />
        )}

        <Text style={s.sectionTitle}>Disclaimer</Text>
        <Text style={s.bodyText}>
          This report is an indicative pre-screen only and does not constitute a formal BAL assessment,
          planning advice, or bushfire safety recommendation. A formal BAL assessment by a practitioner
          accredited under the RFS scheme is required before any development application or construction
          on bushfire prone land.
        </Text>
        <Text style={[s.bodyText, { color: GRAY_500 }]}>
          Data: {data.data_sources.join(' - ')} - Report generated {data.run_date} - plotdetect.com.au
        </Text>

        {data.qr_b64 && data.shareable_url && (
          <QRBlock url={data.shareable_url} qr_b64={data.qr_b64} />
        )}

        <Footer pageNum={2} total={totalPages} />
      </Page>

      {/* About page */}
      <AboutPage
        logo_b64={data.logo_b64}
        pageNum={3}
        total={totalPages}
        reportName="Bushfire Pre-Screen"
      />

      {/* Aerial tile (optional) */}
      {data.tile_b64 && (
        <Page size="A4" style={s.page}>
          <LogoRow logo_b64={data.logo_b64} />
          <Text style={s.sectionTitle}>Property aerial view</Text>
          <Text style={[s.bodyText, { color: GRAY_500, marginBottom: 10 }]}>
            NSW SIX Maps aerial imagery for context.
          </Text>
          <AerialWithOverlay
            tile_b64={data.tile_b64}
            center={[data.lng, data.lat]}
            zoom="property"
            layers={data.lot_polygon ? [
              { geojson: data.lot_polygon, fill: '#0d9488', fillOpacity: 0.15, stroke: '#0d9488', strokeWidth: 2 },
            ] : []}
          />
          <Footer pageNum={4} total={totalPages} />
        </Page>
      )}
    </Document>
  );
}
