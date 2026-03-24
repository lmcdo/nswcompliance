// React-PDF StyleSheet for table format

import { StyleSheet, Font } from '@react-pdf/renderer';

export const styles = StyleSheet.create({
  page: {
    padding: '15mm 15mm',
    fontFamily: 'Helvetica',
    fontSize: 9,
    lineHeight: 1.4,
    backgroundColor: '#ffffff',
  },

  // Cover page
  coverPage: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'flex-start',
    alignItems: 'center',
    paddingTop: 40,
  },
  coverTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#0f766e',
    letterSpacing: 0.5,
  },
  coverSubtitle: {
    fontSize: 16,
    marginBottom: 40,
    color: '#1f2937',
    fontWeight: 'normal',
  },
  propertyDetails: {
    marginBottom: 30,
    padding: 20,
    backgroundColor: '#f0fdfa',
    width: '85%',
    borderLeft: '4pt solid #0f766e',
    borderRadius: 2,
  },
  propertyDetailRow: {
    flexDirection: 'row',
    marginBottom: 6,
  },
  propertyLabel: {
    fontWeight: 'bold',
    width: 120,
    color: '#374151',
  },
  propertyValue: {
    color: '#1f2937',
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 'auto',
  },
  provisionSummary: {
    marginTop: 20,
    padding: 15,
    width: '80%',
  },
  summaryTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#1f2937',
  },
  summaryRow: {
    flexDirection: 'row',
    marginBottom: 4,
    paddingLeft: 10,
  },
  summaryTopic: {
    width: 140,
    color: '#4b5563',
  },
  summaryCount: {
    color: '#1f2937',
  },
  reportMetadata: {
    marginTop: 30,
    fontSize: 8,
    color: '#6b7280',
    textAlign: 'center',
  },

  // Table of contents
  tocPage: {
    padding: '15mm 12mm',
  },
  tocTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 15,
    color: '#1f2937',
        paddingBottom: 8,
  },
  tocItem: {
    flexDirection: 'row',
    marginBottom: 8,
    paddingLeft: 10,
  },
  tocNumber: {
    width: 30,
    color: '#6b7280',
  },
  tocLabel: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 'auto',
    color: '#1f2937',
  },
  tocCount: {
    width: 100,
    textAlign: 'right',
    color: '#6b7280',
  },

  // Table header
  sectionTitle: {
    fontSize: 12,       // Reduced from 13 to 12
    fontWeight: 'bold',
    marginBottom: 6,    // Reduced from 10 to 6
    marginTop: 0,
    color: '#0f766e',
    paddingBottom: 4,   // Reduced from 6 to 4
    borderBottom: '2pt solid #0f766e',
  },
  tableHeader: {
    flexDirection: 'row',
    backgroundColor: '#0f766e',
    padding: 8,
    fontWeight: 'bold',
    fontSize: 8,
    color: '#ffffff',
    marginBottom: 2,
  },
  tableHeaderCell: {
    color: '#ffffff',
  },

  // Table rows
  tableRow: {
    flexDirection: 'row',
    padding: 8,
    minHeight: 28,
    alignItems: 'flex-start',
    borderBottom: '0.5pt solid #e5e7eb',
  },
  subtopicRow: {
    flexDirection: 'row',
    backgroundColor: '#f0fdfa',
    padding: 6,
    fontWeight: 'bold',
    fontSize: 8,
    borderLeft: '3pt solid #0f766e',
    marginTop: 4,
  },

  // Table cells (column widths)
  // Total usable width ~510pt. 3-column layout: # | Provision + Source | Response
  colNumber: {
    width: 22,
    paddingRight: 4,
  },
  colProvision: {
    width: 358,
    paddingRight: 4,
  },
  colSource: {
    // Source now rendered inline below provision text — this column is hidden but kept for compat
    width: 0,
    overflow: 'hidden' as const,
  },
  colResponse: {
    width: 130,
    paddingLeft: 4,
  },
  responseBox: {
    border: '1pt solid #e5e7eb',
    backgroundColor: '#f9fafb',
    minHeight: 40,
    borderRadius: 2,
  },

  // Cell text
  cellNumber: {
    fontSize: 8,
    color: '#6b7280',
    overflow: 'hidden',
  },
  cellProvision: {
    fontSize: 10,
    color: '#1f2937',
    lineHeight: 1.5,
    overflow: 'hidden',
  },
  cellSource: {
    fontSize: 8,
    color: '#0c4a6e',
    overflow: 'hidden',
    textAlign: 'right',
  },

  // Context section
  section: {
    marginBottom: 10,  // Reduced from 20 to 10
    paddingBottom: 8,   // Reduced from 12 to 8
  },
  dataTable: {
  },
  contextTableRow: {
    flexDirection: 'row',
    padding: 4,  // Reduced from 6 to 4
  },
  tableCellLabel: {
    // 160pt fits all DataRow label text (longest: "Legislative basis:" ~18 chars).
    // "Additional Local Provisions (Clause 6.x):" uses a separate custom View, not DataRow.
    width: 160,
    fontSize: 10,
    fontWeight: 'normal',
    color: '#4b5563',
    paddingRight: 8,
  },
  tableCellValue: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 'auto',
    fontSize: 10,
    fontWeight: 'normal',
    color: '#1f2937',
    lineHeight: 1.3,
  },
  contextSubtitle: {
    fontSize: 10,
    color: '#6b7280',
    marginBottom: 20,
    marginTop: -5,
  },
  contextBlock: {
    marginBottom: 8,
  },
  contextHeading: {
    fontSize: 11,
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: 8,
        paddingBottom: 3,
  },
  contextLabel: {
    fontSize: 9,
    fontWeight: 'bold',
    color: '#4b5563',
    marginBottom: 2,
  },
  contextValue: {
    fontSize: 9,
    color: '#1f2937',
    marginBottom: 1,
  },
  contextReason: {
    fontSize: 8,
    color: '#6b7280',
    fontStyle: 'italic',
    marginTop: 2,
  },

  // Footer
  footer: {
    position: 'absolute',
    bottom: 10,
    left: 12,
    right: 12,
    fontSize: 7,
    color: '#9ca3af',
    flexDirection: 'row',
    justifyContent: 'space-between',
        paddingTop: 5,
  },
  footerLeft: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 'auto',
  },
  footerCenter: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 'auto',
    textAlign: 'center',
  },
  footerRight: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 'auto',
    textAlign: 'right',
  },
});
