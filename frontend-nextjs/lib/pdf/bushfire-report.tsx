/**
 * Bushfire Pre-Screen PDF — free one-page report.
 * react-pdf document rendered server-side via renderToBuffer.
 */

import React from 'react'
import { Document, Page, Text, View, Image, StyleSheet } from '@react-pdf/renderer'
import { PlotDetectFooter } from './shared-components'

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

const TEAL       = '#0f766e'
const TEAL_LIGHT = '#f0fdfa'
const GREEN      = '#16a34a'
const AMBER      = '#d97706'
const RED        = '#dc2626'
const GRAY_900   = '#111827'
const GRAY_700   = '#374151'
const GRAY_500   = '#6b7280'
const GRAY_100   = '#f3f4f6'

const SEVERITY_COLORS = { green: GREEN, amber: AMBER, red: RED }

const SIGNAL_LABELS: Record<string, string> = {
  none: 'Not bushfire prone',
  low: 'Low fire signal',
  moderate: 'Moderate fire signal',
  elevated: 'Elevated fire signal',
  unavailable: 'Data unavailable',
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const s = StyleSheet.create({
  page: {
    fontFamily: 'Helvetica', fontSize: 9, color: GRAY_900,
    paddingTop: 48, paddingBottom: 56, paddingHorizontal: 48, lineHeight: 1.4,
  },
  logo:     { fontSize: 11, fontFamily: 'Helvetica-Bold', color: TEAL },
  logoRow:  { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 32 },
  logoImg:  { width: 18, height: 18 },
  h1:       { fontSize: 22, fontFamily: 'Helvetica-Bold', color: GRAY_900, marginBottom: 6 },
  subhead:  { fontSize: 11, color: GRAY_700, marginBottom: 3 },
  dateText: { fontSize: 9, color: GRAY_500, marginBottom: 16 },
  sectionTitle: {
    fontSize: 8, fontFamily: 'Helvetica-Bold', color: GRAY_500,
    textTransform: 'uppercase', letterSpacing: 0.8,
    marginTop: 16, marginBottom: 8,
  },
  bodyText: { fontSize: 8.5, color: GRAY_700, lineHeight: 1.5, marginBottom: 6 },
})

// ---------------------------------------------------------------------------
// Finding row
// ---------------------------------------------------------------------------

interface Finding {
  label: string
  value: string
  detail: string
  severity: 'green' | 'amber' | 'red'
}

function FindingRow({ finding }: { finding: Finding }) {
  const dotColor = SEVERITY_COLORS[finding.severity]
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
  )
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BushfirePdfData {
  address: string
  run_date: string
  lat: number
  lng: number
  fire_signal: string
  is_bushfire_prone: boolean | null
  designation_category: string | null
  designation_guideline: string | null
  estimated_bal_band: string | null
  bal_assessment_likely_required: boolean | null
  rfs_referral_required: boolean | null
  cdc_pathway_available: boolean | null
  clearing_10_50_entitled: boolean | null
  clearing_10_50_exceptions: string | null
  estimated_consultant_costs: string | null
  data_currency: string
  confidence: string
  data_sources: string[]
  logo_b64: string | null
  aerial_b64: string | null
  bfpl_b64: string | null
  lot_svg: string | null
  neighbour_context: string | null
}

// ---------------------------------------------------------------------------
// Build findings
// ---------------------------------------------------------------------------

function buildFindings(data: BushfirePdfData): Finding[] {
  const findings: Finding[] = []
  const signal = data.fire_signal || 'unavailable'

  // BFPL status
  const bfplLabel = SIGNAL_LABELS[signal] || 'Unknown'
  findings.push({
    label: 'NSW Rural Fire Service - Bush Fire Prone Land Map',
    value: bfplLabel,
    detail: data.is_bushfire_prone
      ? `This property is mapped as bushfire prone land (${data.designation_category || 'category unknown'}). ${data.designation_guideline ? `Guideline: ${data.designation_guideline}.` : ''} Development on bushfire prone land requires specific assessments.`
      : data.is_bushfire_prone === false
      ? 'This property is not mapped as bushfire prone land. No bushfire-specific development controls apply under the current BFPL map.'
      : 'Bushfire prone land status could not be determined for this property.',
    severity: signal === 'none' ? 'green' : signal === 'low' ? 'amber' : signal === 'unavailable' ? 'amber' : 'red',
  })

  // BAL band
  if (data.estimated_bal_band) {
    const isHigh = ['BAL-40', 'BAL-FZ'].includes(data.estimated_bal_band)
    findings.push({
      label: 'Estimated from BFPL category + vegetation proximity',
      value: `Estimated BAL: ${data.estimated_bal_band}`,
      detail: isHigh
        ? 'High BAL rating. Significant construction requirements apply including non-combustible materials, ember guards, and potentially bushfire shutters. Formal BAL assessment by a qualified practitioner is required.'
        : data.estimated_bal_band === 'BAL-LOW'
        ? 'Low BAL rating. Minimal additional construction requirements. A formal BAL assessment may still be required for the development application.'
        : `Moderate BAL rating. Additional construction requirements apply under AS 3959. A formal BAL assessment by a qualified practitioner is required for development applications.`,
      severity: isHigh ? 'red' : data.estimated_bal_band === 'BAL-LOW' ? 'green' : 'amber',
    })
  }

  // RFS referral
  if (data.is_bushfire_prone) {
    findings.push({
      label: 'Environmental Planning and Assessment Act 1979 s4.14',
      value: data.rfs_referral_required ? 'RFS referral required' : 'RFS referral may not be required',
      detail: data.rfs_referral_required
        ? 'Development applications on bushfire prone land must be referred to the NSW Rural Fire Service under s4.14. RFS will issue a Bush Fire Safety Authority with conditions.'
        : 'Based on the BFPL category, RFS referral may not be required for all development types. Confirm with your certifier or council.',
      severity: data.rfs_referral_required ? 'red' : 'amber',
    })
  }

  // CDC pathway
  if (data.is_bushfire_prone && data.cdc_pathway_available !== null) {
    findings.push({
      label: 'SEPP (Exempt and Complying) 2008 - bushfire exclusion',
      value: data.cdc_pathway_available ? 'CDC pathway available' : 'DA required (CDC excluded)',
      detail: data.cdc_pathway_available
        ? 'The CDC pathway remains available for this bushfire category. A private certifier can process the application, but bushfire conditions will apply.'
        : 'The CDC pathway is not available for this bushfire category. A full Development Application to council is required, including RFS referral and formal BAL assessment.',
      severity: data.cdc_pathway_available ? 'green' : 'red',
    })
  }

  // 10/50 vegetation clearing
  if (data.clearing_10_50_entitled !== null) {
    findings.push({
      label: 'Rural Fires Act 1997 - 10/50 vegetation clearing',
      value: data.clearing_10_50_entitled ? '10/50 vegetation clearing entitlement applies' : '10/50 clearing does not apply',
      detail: data.clearing_10_50_entitled
        ? 'You may clear trees within 10m and vegetation within 50m of an approved building without council approval, subject to RFS conditions.'
        : `10/50 clearing entitlement does not apply to this property.${data.clearing_10_50_exceptions ? ` ${data.clearing_10_50_exceptions}` : ''}`,
      severity: data.clearing_10_50_entitled ? 'green' : 'amber',
    })
  }

  // Neighbour context
  if (data.neighbour_context) {
    findings.push({
      label: 'PostGIS spatial overlay - 200m buffer analysis',
      value: `Surrounding area: ${data.neighbour_context}`,
      detail: 'Neighbouring BFPL status within approximately 200m of the property boundary. Adjacent bushfire prone land can affect BAL ratings and development requirements even if your lot is not directly mapped.',
      severity: data.neighbour_context.toLowerCase().includes('not') ? 'green' : 'amber',
    })
  }

  return findings
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

function LogoRow({ logo_b64 }: { logo_b64: string | null }) {
  return (
    <View style={s.logoRow}>
      {logo_b64 ? (
        <Image src={`data:image/png;base64,${logo_b64}`} style={s.logoImg} />
      ) : null}
      <Text style={s.logo}>PlotDetect</Text>
    </View>
  )
}

export function BushfireReportDocument({ data }: { data: BushfirePdfData }) {
  const findings = buildFindings(data)

  return (
    <Document title={`Bushfire Pre-Screen - ${data.address}`} author="PlotDetect">
      <Page size="A4" style={s.page}>
        <LogoRow logo_b64={data.logo_b64} />

        <Text style={s.h1}>Bushfire Pre-Screen Report</Text>
        <Text style={s.subhead}>{data.address}</Text>
        <Text style={s.dateText}>Report date: {data.run_date}</Text>

        {/* Composite map: aerial base + BFPL overlay + lot boundary */}
        {(data.aerial_b64 || data.bfpl_b64) && (
          <View style={{ width: '100%', height: 160, marginBottom: 12, position: 'relative' }}>
            {data.aerial_b64 && (
              <Image
                src={`data:image/png;base64,${data.aerial_b64}`}
                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: 160, objectFit: 'cover', borderRadius: 4 }}
              />
            )}
            {data.bfpl_b64 && (
              <Image
                src={`data:image/png;base64,${data.bfpl_b64}`}
                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: 160, objectFit: 'cover', borderRadius: 4, opacity: 0.6 }}
              />
            )}
            {data.lot_svg && (
              <Image
                src={`data:image/svg+xml;base64,${Buffer.from(data.lot_svg).toString('base64')}`}
                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: 160, borderRadius: 4 }}
              />
            )}
            <View style={{ position: 'absolute', bottom: 4, right: 6 }}>
              <Text style={{ fontSize: 6, color: '#ffffff', backgroundColor: 'rgba(0,0,0,0.5)', paddingHorizontal: 3, paddingVertical: 1, borderRadius: 2 }}>
                Aerial + RFS BFPL overlay | Lot boundary (dashed)
              </Text>
            </View>
          </View>
        )}

        {/* Key findings */}
        <Text style={s.sectionTitle}>Key findings</Text>
        {findings.map((f) => (
          <FindingRow key={f.label} finding={f} />
        ))}

        {/* Consultant costs */}
        {data.estimated_consultant_costs && (
          <View style={{
            backgroundColor: TEAL_LIGHT, borderRadius: 4, padding: 10,
            marginTop: 12, borderWidth: 1, borderColor: '#99f6e4',
          }}>
            <Text style={{ fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: TEAL, marginBottom: 4 }}>
              Estimated consultant costs
            </Text>
            <Text style={s.bodyText}>{data.estimated_consultant_costs}</Text>
          </View>
        )}

        {/* Data sources */}
        <View style={{ marginTop: 10 }}>
          <Text style={{ fontSize: 7, color: GRAY_500 }}>
            Data sources: {data.data_sources.join(' · ')} | {data.confidence} confidence | Data currency: {data.data_currency}
          </Text>
        </View>

        {/* Disclaimer */}
        <View style={{ marginTop: 10 }}>
          <Text style={{ fontSize: 7, color: GRAY_500, lineHeight: 1.4 }}>
            This is an indicative pre-screen only and does not constitute a formal BAL assessment. For development
            applications on bushfire prone land, a formal bushfire assessment by a qualified practitioner listed in the
            RFS directory is required. Data sourced from the NSW Rural Fire Service Bush Fire Prone Land Map and PostGIS
            spatial overlays.
          </Text>
        </View>

        <PlotDetectFooter reportName="Bushfire Pre-Screen Report" />
      </Page>
    </Document>
  )
}
