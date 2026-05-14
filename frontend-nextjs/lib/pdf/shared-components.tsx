/**
 * Shared PDF components used across all satellite report PDFs.
 * - AboutPage: "About this report" + full tools list (T4)
 * - PlotDetectFooter: standardised footer with free-check URL (R4)
 * - WhatThisMeans: plain-English interpretation callout box (A1)
 * - DataCurrencyTable: structured data provenance table (A2)
 * - QRBlock: QR code linking to shareable report URL (T5)
 * - PreparedBy: white-label firm name on cover (T3)
 * - InsurerChecklist: actionable questions for insurer/lender (A4)
 * - ReferralLinks: professional referral directory links (A3)
 */

import React from 'react';
import {
  Page,
  View,
  Text,
  Image,
  Link,
  StyleSheet,
} from '@react-pdf/renderer';
import { ABOUT_PAGE_DISCLAIMER } from '../disclaimers';

// ---------------------------------------------------------------------------
// Palette (matches existing reports)
// ---------------------------------------------------------------------------

const TEAL       = '#0f766e';
const TEAL_LIGHT = '#f0fdfa';
const TEAL_BORDER = '#99f6e4';
const GRAY_900   = '#111827';
const GRAY_700   = '#374151';
const GRAY_500   = '#6b7280';
const GRAY_300   = '#d1d5db';
const GRAY_100   = '#f3f4f6';

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const ss = StyleSheet.create({
  page: {
    fontFamily: 'Helvetica',
    fontSize: 9,
    color: GRAY_900,
    paddingTop: 48,
    paddingBottom: 56,
    paddingHorizontal: 48,
    lineHeight: 1.4,
  },
  logoRow:  { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 32 },
  logoText: { fontSize: 11, fontFamily: 'Helvetica-Bold', color: TEAL },
  logoImg:  { width: 18, height: 18 },
  h2: {
    fontSize: 14, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_500,
    textTransform: 'uppercase', letterSpacing: 0.8,
    marginTop: 20, marginBottom: 8,
  },
  body: { fontSize: 8.5, color: GRAY_700, lineHeight: 1.6, marginBottom: 6 },
  divider: { borderBottom: `1 solid ${GRAY_300}`, marginVertical: 14 },
  footer: {
    position: 'absolute', bottom: 28, left: 48, right: 48,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  footerText: { fontSize: 7, color: GRAY_500 },
  // WhatThisMeans callout
  wtmBox: {
    backgroundColor: TEAL_LIGHT,
    borderWidth: 1,
    borderColor: TEAL_BORDER,
    borderRadius: 4,
    padding: 10,
    marginTop: 8,
    marginBottom: 10,
  },
  wtmLabel: {
    fontSize: 7.5, fontFamily: 'Helvetica-Bold', color: TEAL,
    textTransform: 'uppercase', letterSpacing: 0.5,
    marginBottom: 4,
  },
  wtmText: { fontSize: 8.5, color: GRAY_700, lineHeight: 1.6 },
  // Tool card
  toolCard: {
    backgroundColor: GRAY_100, borderRadius: 4, padding: 10, marginBottom: 6,
  },
  toolName: { fontSize: 9, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 2 },
  toolDesc: { fontSize: 8, color: GRAY_700, lineHeight: 1.5 },
  toolPrice: { fontSize: 7.5, color: TEAL, fontFamily: 'Helvetica-Bold', marginTop: 3 },
  // Referral link row
  refRow: {
    flexDirection: 'row', paddingVertical: 5,
    borderBottom: `1 solid ${GRAY_100}`,
  },
  refLabel: { flex: 2, fontSize: 8, color: GRAY_700 },
  refUrl: { flex: 3, fontSize: 7.5, color: TEAL },
  // Checklist
  checkItem: {
    flexDirection: 'row', alignItems: 'flex-start', marginBottom: 6,
  },
  checkBullet: {
    width: 12, fontSize: 8, color: TEAL, fontFamily: 'Helvetica-Bold',
    marginRight: 6, marginTop: 1,
  },
  checkText: { flex: 1, fontSize: 8, color: GRAY_700, lineHeight: 1.5 },
  // Data currency table
  dcTable: { marginTop: 12, marginBottom: 8 },
  dcHeaderRow: {
    flexDirection: 'row', backgroundColor: GRAY_100, paddingVertical: 5, paddingHorizontal: 8,
    borderTopLeftRadius: 3, borderTopRightRadius: 3,
  },
  dcRow: {
    flexDirection: 'row', paddingVertical: 4, paddingHorizontal: 8,
    borderBottom: `1 solid ${GRAY_100}`,
  },
  dcCellSource: { flex: 3, fontSize: 7.5, color: GRAY_700 },
  dcCellType: { flex: 2, fontSize: 7.5, color: GRAY_700 },
  dcCellCurrency: { flex: 2, fontSize: 7.5, color: GRAY_700 },
  dcHeaderText: { fontSize: 7, fontFamily: 'Helvetica-Bold', color: GRAY_500, textTransform: 'uppercase', letterSpacing: 0.5 },
  // QR placeholder
  qrBox: { alignItems: 'center', marginTop: 16, marginBottom: 8 },
  qrLabel: { fontSize: 7, color: GRAY_500, marginTop: 4 },
});

// ---------------------------------------------------------------------------
// R4: PlotDetectFooter — standardised footer with free-check URL
// ---------------------------------------------------------------------------

export function PlotDetectFooter({
  reportName,
  pageNum,
  total,
}: {
  reportName: string;
  pageNum?: number;
  total?: number;
}) {
  return (
    <View style={ss.footer} fixed>
      <Text style={ss.footerText}>
        {reportName} — Run a free check on any NSW address: plotdetect.com.au
      </Text>
      {pageNum != null && total != null && (
        <Text style={ss.footerText}>{pageNum} / {total}</Text>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// A1: WhatThisMeans — plain-English interpretation callout
// ---------------------------------------------------------------------------

export function WhatThisMeans({ children }: { children: string }) {
  return (
    <View style={ss.wtmBox}>
      <Text style={ss.wtmLabel}>What this means</Text>
      <Text style={ss.wtmText}>{children}</Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// A3: ReferralLinks — professional referral directory
// ---------------------------------------------------------------------------

interface ReferralLink {
  label: string;
  url: string;
  urlDisplay: string;
}

export function ReferralLinks({ links }: { links: ReferralLink[] }) {
  return (
    <View style={{ marginTop: 12, marginBottom: 8 }}>
      <Text style={ss.sectionTitle}>Professional referrals</Text>
      {links.map((link) => (
        <View key={link.label} style={ss.refRow}>
          <Text style={ss.refLabel}>{link.label}</Text>
          <Link src={link.url}>
            <Text style={ss.refUrl}>{link.urlDisplay}</Text>
          </Link>
        </View>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------
// A4: InsurerChecklist — actionable questions for insurer/lender
// ---------------------------------------------------------------------------

export function InsurerChecklist({
  title,
  questions,
}: {
  title: string;
  questions: string[];
}) {
  return (
    <View style={{ marginTop: 12, marginBottom: 8 }}>
      <Text style={ss.sectionTitle}>{title}</Text>
      <Text style={{ fontSize: 8, color: GRAY_500, marginBottom: 8 }}>
        Take this report to your insurer or lender and ask:
      </Text>
      {questions.map((q, i) => (
        <View key={i} style={ss.checkItem}>
          <Text style={ss.checkBullet}>{i + 1}.</Text>
          <Text style={ss.checkText}>{q}</Text>
        </View>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------
// A2: DataCurrencyTable — structured data provenance table
// ---------------------------------------------------------------------------

interface DataCurrencyRow {
  source: string;
  type: string;
  currency: string;
}

export function DataCurrencyTable({ rows }: { rows: DataCurrencyRow[] }) {
  return (
    <View style={ss.dcTable}>
      <Text style={ss.sectionTitle}>Data sources and currency</Text>
      <View style={ss.dcHeaderRow}>
        <Text style={{ ...ss.dcHeaderText, flex: 3 }}>Source</Text>
        <Text style={{ ...ss.dcHeaderText, flex: 2 }}>Type</Text>
        <Text style={{ ...ss.dcHeaderText, flex: 2 }}>Currency</Text>
      </View>
      {rows.map((row, i) => (
        <View key={i} style={ss.dcRow}>
          <Text style={ss.dcCellSource}>{row.source}</Text>
          <Text style={ss.dcCellType}>{row.type}</Text>
          <Text style={ss.dcCellCurrency}>{row.currency}</Text>
        </View>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------
// T5: QRBlock — QR code linking to shareable report URL
// ---------------------------------------------------------------------------

export function QRBlock({ url, qr_b64 }: { url: string; qr_b64?: string | null }) {
  if (!qr_b64) return null;
  return (
    <View style={ss.qrBox}>
      <Image src={`data:image/png;base64,${qr_b64}`} style={{ width: 72, height: 72 }} />
      <Text style={ss.qrLabel}>Scan to view this report online</Text>
      <Link src={url}>
        <Text style={{ fontSize: 7, color: TEAL, marginTop: 2 }}>{url}</Text>
      </Link>
    </View>
  );
}

// ---------------------------------------------------------------------------
// T3: PreparedBy — white-label firm name on cover
// ---------------------------------------------------------------------------

export function PreparedBy({ firmName }: { firmName?: string | null }) {
  if (!firmName) return null;
  return (
    <View style={{ marginTop: 8, marginBottom: 4 }}>
      <Text style={{ fontSize: 8, color: GRAY_500 }}>
        Prepared by: <Text style={{ fontFamily: 'Helvetica-Bold', color: GRAY_700 }}>{firmName}</Text> via PlotDetect
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// T4: AboutPage — "About this report" + full product suite list
// ---------------------------------------------------------------------------

const TOOLS = [
  {
    name: 'Flood Truth',
    desc: 'Cross-references 6+ independent flood data sources to assess flood risk at any NSW address. Includes EPI overlays, satellite observations, BoM gauge history, and council flood study depths.',
    price: 'Free check / $49 full report',
  },
  {
    name: 'Granny Flat Eligibility',
    desc: 'Checks whether a property qualifies for a secondary dwelling under the fast-track CDC pathway (SEPP Housing 2021). Includes setbacks, max floor area, rental yield estimate, and approval pathway comparison.',
    price: 'Free check / $49 full report',
  },
  {
    name: 'Shadow Detector',
    desc: 'Models worst-case shadow impact from a maximum-height building on an adjacent lot. Tests 5 ADG scenarios across winter, equinox, and summer to assess solar access compliance.',
    price: 'Free check / $29 full report',
  },
  {
    name: 'Solar Yield',
    desc: 'Estimates rooftop solar potential using Google Solar API data. Includes system sizing, annual output, payback period, and feed-in rate sensitivity analysis.',
    price: 'Free check / $19 full report',
  },
  {
    name: 'Threat Radar',
    desc: 'Scans nearby DA and CDC applications from the NSW ePlanning Portal. Identifies development activity, construction timelines, and neighbourhood pressure within a customisable radius.',
    price: 'Free check / $9/month monitoring',
  },
  {
    name: 'Bushfire Pre-Screen',
    desc: 'Checks RFS Bush Fire Prone Land mapping and identifies the applicable BAL category. Flags construction cost implications and AS3959 requirements.',
    price: 'Free check / $29 full report',
  },
];

export function AboutPage({
  logo_b64,
  pageNum,
  total,
  reportName,
}: {
  logo_b64?: string | null;
  pageNum: number;
  total: number;
  reportName: string;
}) {
  return (
    <Page size="A4" style={ss.page}>
      {/* Logo */}
      <View style={ss.logoRow}>
        {logo_b64 ? (
          <Image src={`data:image/png;base64,${logo_b64}`} style={ss.logoImg} />
        ) : null}
        <Text style={ss.logoText}>PlotDetect</Text>
      </View>

      <Text style={ss.h2}>About this report</Text>
      <Text style={ss.body}>
        This report was generated by PlotDetect, an automated property intelligence platform for NSW.
        PlotDetect cross-references live government data sources to provide objective, data-driven
        property assessments. No human interpretation is applied — all results are deterministic
        and reproducible.
      </Text>
      <Text style={ss.body}>
        {ABOUT_PAGE_DISCLAIMER}
      </Text>

      <View style={ss.divider} />

      <Text style={ss.sectionTitle}>Other property checks available</Text>
      {TOOLS.map((tool) => (
        <View key={tool.name} style={ss.toolCard}>
          <Text style={ss.toolName}>{tool.name}</Text>
          <Text style={ss.toolDesc}>{tool.desc}</Text>
          <Text style={ss.toolPrice}>{tool.price}</Text>
        </View>
      ))}

      <View style={{ marginTop: 12 }}>
        <Text style={{ fontSize: 8.5, color: TEAL, fontFamily: 'Helvetica-Bold' }}>
          Run a free check on any NSW address: plotdetect.com.au
        </Text>
      </View>

      <PlotDetectFooter reportName={reportName} pageNum={pageNum} total={total} />
    </Page>
  );
}
