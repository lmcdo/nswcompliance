import { Page, View, Text } from '@react-pdf/renderer';
import { styles } from '../styles';
import { capitalizeFirst } from '@/lib/pdf/see-helpers';
import { SEEComputedData } from '@/lib/see/section-aggregation';

export function Page1Cover({ computed }: { computed: SEEComputedData }) {
  const {
    property, devDesc, see_intro, intake_answers,
    generated_date, docRef, footerRef, client_ref, prepared_by, heritage_status,
  } = computed;

  return (
    <Page size="A4" style={styles.page}>

      {/* ---- Brand header ---- */}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16, paddingBottom: 12, borderBottom: '2pt solid #0f766e' }}>
        <View>
          <Text style={{ fontSize: 20, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 4 }}>
            PLOTDETECT
          </Text>
          <Text style={{ fontSize: 13, color: '#1f2937', marginBottom: 2 }}>
            DRAFT Statement of Environmental Effects
          </Text>
          <Text style={{ fontSize: 9, color: '#6b7280' }}>
            Prepared: {generated_date}
          </Text>
          <Text style={{ fontSize: 8, color: '#9ca3af', marginTop: 2 }}>
            Ref: {docRef}
          </Text>
        </View>
        <View style={{ backgroundColor: '#fef3c7', padding: 8, borderLeft: '3pt solid #f59e0b', maxWidth: 180 }}>
          <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#92400e', marginBottom: 2 }}>
            DRAFT — NOT FOR LODGEMENT
          </Text>
          <Text style={{ fontSize: 7, color: '#78350f', lineHeight: 1.3 }}>
            Must be reviewed and completed by a qualified planning consultant before use.
          </Text>
        </View>
      </View>

      {/* ---- Property address block ---- */}
      <View style={{ backgroundColor: '#f0fdfa', padding: 12, borderLeft: '3pt solid #0f766e', marginBottom: 12 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 4 }}>PROPERTY</Text>
            <Text style={{ fontSize: 11, color: '#1f2937' }}>{property.address}</Text>
          </View>
          {(client_ref || prepared_by) && (
            <View style={{ alignItems: 'flex-end', maxWidth: 150, flexShrink: 0, marginLeft: 12 }}>
              {client_ref && (
                <View style={{ marginBottom: 3 }}>
                  <Text style={{ fontSize: 7, color: '#6b7280' }}>Prepared for</Text>
                  <Text style={{ fontSize: 9, color: '#1f2937' }}>{client_ref}</Text>
                </View>
              )}
              {prepared_by && (
                <View>
                  <Text style={{ fontSize: 7, color: '#6b7280' }}>Prepared by</Text>
                  <Text style={{ fontSize: 9, color: '#1f2937' }}>{prepared_by}</Text>
                </View>
              )}
            </View>
          )}
        </View>
        <View style={{ flexDirection: 'row', gap: 20 }}>
          <View>
            <Text style={{ fontSize: 7, color: '#6b7280' }}>Zone</Text>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#1f2937' }}>{property.zone || 'Not provided'}</Text>
          </View>
          <View>
            <Text style={{ fontSize: 7, color: '#6b7280' }}>Former Council</Text>
            <Text style={{ fontSize: 9, color: '#1f2937' }}>{capitalizeFirst(property.former_council)}</Text>
          </View>
          {heritage_status.in_hca && (
            <View>
              <Text style={{ fontSize: 7, color: '#92400e' }}>Heritage</Text>
              <Text style={{ fontSize: 9, color: '#92400e' }}>{heritage_status.hca_name || 'Heritage Conservation Area'}</Text>
            </View>
          )}
        </View>
      </View>

      {/* ---- Section 1: Introduction ---- */}
      <View style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#0f766e', borderBottom: '1pt solid #0f766e', paddingBottom: 3, marginBottom: 6 }}>
          1. Introduction
        </Text>

        {see_intro ? (
          <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5, marginBottom: 8 }}>
            {see_intro}
          </Text>
        ) : devDesc ? (
          <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5, marginBottom: 8 }}>
            {`This Statement of Environmental Effects has been prepared in support of a Development Application for ${devDesc} at ${property.address}. The proposed development is subject to assessment under the Environmental Planning and Assessment Act 1979 (NSW).`}
          </Text>
        ) : (
          <Text style={{ fontSize: 9, color: '#6b7280', fontStyle: 'italic', marginBottom: 8 }}>
            [Development description not provided — complete before lodgement]
          </Text>
        )}

        <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5 }}>
          {`This document provides a working schedule of the Development Control Plan (DCP) provisions applicable to the subject site and records compliance positions against each applicable provision. It is a working draft prepared as an aid to the planning consultant and must be reviewed, completed, and signed before submission with any Development Application.`}
        </Text>
      </View>

      {/* ---- Proposed development box ---- */}
      <View style={{ backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb', padding: 10, marginBottom: 8 }}>
        <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', marginBottom: 4 }}>PROPOSED DEVELOPMENT</Text>
        {devDesc ? (
          <Text style={{ fontSize: 10, color: '#1f2937' }}>{devDesc}</Text>
        ) : (
          <Text style={{ fontSize: 9, color: '#6b7280', fontStyle: 'italic' }}>
            [To be completed — describe the proposed development]
          </Text>
        )}
      </View>

      {/* ---- Proposal characteristics (intake answers audit trail) ---- */}
      {intake_answers && (
        <View style={{ backgroundColor: '#f0fdf4', border: '1pt solid #bbf7d0', padding: 10, marginBottom: 8 }}>
          <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#166534', marginBottom: 6 }}>PROPOSAL CHARACTERISTICS — CONFIRMED INPUTS</Text>
          <Text style={{ fontSize: 7, color: '#4b7a5a', marginBottom: 4, fontStyle: 'italic' }}>
            Provisions were excluded from this schedule only where their applicability trigger was confirmed as absent below.
          </Text>
          {[
            { key: 'new_impervious_surfaces', label: 'New impervious surfaces (deck, paving, extension)' },
            { key: 'trees_affected', label: 'Trees affected or within works area' },
            { key: 'pool_or_spa', label: 'Swimming pool or spa' },
            { key: 'new_fencing', label: 'New or altered boundary fencing' },
            { key: 'new_parking_or_driveway', label: 'New parking, carport or driveway' },
            { key: 'new_signage', label: 'New or altered signage' },
          ].map(item => (
            <View key={item.key} style={{ flexDirection: 'row', marginBottom: 2 }}>
              <Text style={{ fontSize: 8, color: '#374151', width: 200 }}>{item.label}</Text>
              <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold',
                color: intake_answers[item.key as keyof typeof intake_answers] === 'no' ? '#dc2626'
                     : intake_answers[item.key as keyof typeof intake_answers] === 'yes' ? '#166534'
                     : '#6b7280'
              }}>
                {intake_answers[item.key as keyof typeof intake_answers] === 'yes' ? 'Yes'
                 : intake_answers[item.key as keyof typeof intake_answers] === 'no' ? 'No — provisions excluded'
                 : 'Unknown — provisions included'}
              </Text>
            </View>
          ))}
        </View>
      )}

      {/* ---- Footer ---- */}
      <View style={styles.footer}>
        <Text style={styles.footerLeft}>{footerRef}</Text>
        <Text style={styles.footerCenter}>{property.address}</Text>
        <Text style={styles.footerRight}>Page 1</Text>
      </View>
    </Page>
  );
}
