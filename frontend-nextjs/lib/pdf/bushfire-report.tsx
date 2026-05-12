/**
 * Bushfire Pre-Screen PDF — free one-page report.
 * react-pdf document rendered server-side via renderToBuffer.
 */

import React from 'react'
import { Document, Page, Text, View, Image, StyleSheet } from '@react-pdf/renderer'

const styles = StyleSheet.create({
  page: { padding: 40, fontSize: 9, fontFamily: 'Helvetica', color: '#1a1a1a' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  logo: { width: 28, height: 28 },
  brand: { fontSize: 11, fontWeight: 'bold', color: '#0d9488' },
  title: { fontSize: 16, fontWeight: 'bold', marginBottom: 4 },
  subtitle: { fontSize: 10, color: '#6b7280', marginBottom: 16 },
  section: { marginBottom: 14 },
  sectionTitle: { fontSize: 10, fontWeight: 'bold', color: '#374151', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 },
  row: { flexDirection: 'row', marginBottom: 4 },
  label: { width: 180, color: '#6b7280', fontSize: 9 },
  value: { flex: 1, fontSize: 9, fontWeight: 'bold' },
  signalBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4, alignSelf: 'flex-start', marginBottom: 8 },
  divider: { borderBottomWidth: 1, borderBottomColor: '#e5e7eb', marginVertical: 12 },
  footer: { position: 'absolute', bottom: 30, left: 40, right: 40 },
  footerText: { fontSize: 7, color: '#9ca3af', lineHeight: 1.4 },
  aerialImage: { width: '100%', height: 160, objectFit: 'cover', borderRadius: 4, marginBottom: 12 },
})

const SIGNAL_COLORS: Record<string, { bg: string; text: string }> = {
  none: { bg: '#dcfce7', text: '#166534' },
  low: { bg: '#fef9c3', text: '#854d0e' },
  moderate: { bg: '#ffedd5', text: '#9a3412' },
  elevated: { bg: '#fee2e2', text: '#991b1b' },
  unavailable: { bg: '#f3f4f6', text: '#4b5563' },
}

const SIGNAL_LABELS: Record<string, string> = {
  none: 'Not bushfire prone',
  low: 'Low fire signal',
  moderate: 'Moderate fire signal',
  elevated: 'Elevated fire signal',
  unavailable: 'Data unavailable',
}

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

export function BushfireReportDocument({ data }: { data: BushfirePdfData }) {
  const signal = data.fire_signal || 'unavailable'
  const colors = SIGNAL_COLORS[signal] || SIGNAL_COLORS.unavailable
  const signalLabel = SIGNAL_LABELS[signal] || 'Unknown'

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        {/* Header */}
        <View style={styles.header}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            {data.logo_b64 && (
              <Image src={`data:image/png;base64,${data.logo_b64}`} style={styles.logo} />
            )}
            <Text style={styles.brand}>canibuildit.com.au</Text>
          </View>
          <Text style={{ fontSize: 8, color: '#9ca3af' }}>Bushfire Pre-Screen Report</Text>
        </View>

        {/* Title */}
        <Text style={styles.title}>{data.address}</Text>
        <Text style={styles.subtitle}>
          Generated {data.run_date} | {data.confidence} confidence | {data.data_sources.join(' + ')}
        </Text>

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

        {/* Fire signal badge */}
        <View style={[styles.signalBadge, { backgroundColor: colors.bg }]}>
          <Text style={{ color: colors.text, fontSize: 10, fontWeight: 'bold' }}>{signalLabel}</Text>
        </View>

        {/* BFPL + BAL */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Bush Fire Prone Land Status</Text>
          <View style={styles.row}>
            <Text style={styles.label}>BFPL category</Text>
            <Text style={styles.value}>
              {data.is_bushfire_prone === null ? 'Unavailable' : data.is_bushfire_prone ? (data.designation_category || 'Bushfire prone') : 'Not bushfire prone'}
            </Text>
          </View>
          {data.designation_guideline && (
            <View style={styles.row}>
              <Text style={styles.label}>Guideline</Text>
              <Text style={styles.value}>{data.designation_guideline}</Text>
            </View>
          )}
          <View style={styles.row}>
            <Text style={styles.label}>Estimated BAL band</Text>
            <Text style={styles.value}>{data.estimated_bal_band || 'N/A'}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>BAL assessment required</Text>
            <Text style={styles.value}>{data.bal_assessment_likely_required ? 'Yes' : 'No'}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Data currency</Text>
            <Text style={styles.value}>{data.data_currency}</Text>
          </View>
        </View>

        {/* Surrounding context */}
        {data.neighbour_context && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Surrounding Area Context</Text>
            <View style={styles.row}>
              <Text style={styles.label}>Neighbouring BFPL status (~200m)</Text>
              <Text style={styles.value}>{data.neighbour_context}</Text>
            </View>
          </View>
        )}

        <View style={styles.divider} />

        {/* Development implications */}
        {data.is_bushfire_prone && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Development Implications</Text>
            <View style={styles.row}>
              <Text style={styles.label}>RFS referral required (s4.14)</Text>
              <Text style={styles.value}>{data.rfs_referral_required ? 'Yes' : data.rfs_referral_required === false ? 'No' : 'Unknown'}</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.label}>CDC pathway</Text>
              <Text style={styles.value}>{data.cdc_pathway_available === false ? 'DA required' : data.cdc_pathway_available ? 'Available' : 'Unknown'}</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.label}>10/50 vegetation clearing</Text>
              <Text style={styles.value}>{data.clearing_10_50_entitled ? 'Entitlement applies' : data.clearing_10_50_entitled === false ? 'Does not apply' : 'Unknown'}</Text>
            </View>
            {data.estimated_consultant_costs && (
              <View style={styles.row}>
                <Text style={styles.label}>Estimated consultant costs</Text>
                <Text style={styles.value}>{data.estimated_consultant_costs}</Text>
              </View>
            )}
          </View>
        )}

        {/* Footer */}
        <View style={styles.footer}>
          <View style={styles.divider} />
          <Text style={styles.footerText}>
            This is an indicative pre-screen only and does not constitute a formal BAL assessment. For development
            applications on bushfire prone land, a formal bushfire assessment by a qualified practitioner listed in the
            RFS directory is required. Data sourced from the NSW Rural Fire Service Bush Fire Prone Land Map and PostGIS
            spatial overlays.
          </Text>
          <Text style={[styles.footerText, { marginTop: 4 }]}>
            canibuildit.com.au | Free NSW property intelligence | {data.run_date}
          </Text>
        </View>
      </Page>
    </Document>
  )
}
