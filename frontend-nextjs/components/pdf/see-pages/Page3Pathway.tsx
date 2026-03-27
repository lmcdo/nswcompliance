import { Page, View, Text } from '@react-pdf/renderer';
import { styles } from '../styles';
import { DataRow } from '../DataRow';
import { SEEComputedData } from '@/lib/see/section-aggregation';

export function Page3Pathway({ computed }: { computed: SEEComputedData }) {
  const {
    property, pathway, reason, pathway_determination,
    sepp_assessable_controls, lep_assessable_standards, footerRef,
  } = computed;

  return (
    <Page size="A4" style={styles.page}>

      {/* ---- 3. Approval Pathway Determination ---- */}
      <View style={{ marginBottom: 18 }}>
        <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 10, paddingBottom: 6, borderBottom: '2pt solid #0f766e' }}>
          3. Approval Pathway Determination
        </Text>
        {pathway_determination ? (
          <View style={styles.dataTable}>
            <DataRow label="Pathway:" value={pathway_determination.pathway} />
            <DataRow label="Reason:" value={pathway_determination.reason} />
            <DataRow label="Legislative basis:" value={pathway_determination.legislative_basis} />
          </View>
        ) : (
          <View style={styles.dataTable}>
            <DataRow label="Pathway:" value={pathway} />
            <DataRow label="Reason:" value={reason} />
          </View>
        )}
        {pathway_determination?.required_reports && pathway_determination.required_reports.length > 0 && (
          <View style={{ marginTop: 8 }}>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#374151', marginBottom: 4 }}>
              Required specialist reports for lodgement:
            </Text>
            {pathway_determination.required_reports.map((report, i) => (
              <View key={i} style={{ flexDirection: 'row', gap: 6, marginBottom: 2 }}>
                <Text style={{ fontSize: 8, color: '#374151' }}>•</Text>
                <Text style={{ fontSize: 8, color: '#374151', flex: 1 }}>{report}</Text>
              </View>
            ))}
          </View>
        )}
        {pathway_determination?.caveats && pathway_determination.caveats.length > 0 && (
          <View style={{ marginTop: 8, padding: 6, border: '1pt solid #fbbf24', backgroundColor: '#fffbeb' }}>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#92400e', marginBottom: 4 }}>
              Planning Caveats:
            </Text>
            {pathway_determination.caveats.map((caveat, i) => (
              <View key={i} style={{ flexDirection: 'row', gap: 4, marginBottom: 2 }}>
                <Text style={{ fontSize: 8, color: '#b45309' }}>!</Text>
                <Text style={{ fontSize: 8, color: '#92400e', flex: 1 }}>{caveat}</Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* ---- 4. SEPP Controls Assessment ---- */}
      {sepp_assessable_controls && sepp_assessable_controls.length > 0 && (
        <View style={{ marginBottom: 18 }}>
          <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 8, paddingBottom: 4, borderBottom: '1pt solid #0f766e' }}>
            4. State Environmental Planning Policy (SEPP) Controls
          </Text>
          <Text style={{ fontSize: 8, color: '#6b7280', marginBottom: 6, fontStyle: 'italic' }}>
            Applicable state-level controls. Status to be confirmed by the consultant.
          </Text>
          <View style={{ border: '1pt solid #e5e7eb' }}>
            <View style={{ flexDirection: 'row', backgroundColor: '#f3f4f6', borderBottom: '1pt solid #e5e7eb' }}>
              <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 2 }}>Instrument</Text>
              <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 2 }}>Control</Text>
              <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 3 }}>Requirement</Text>
              <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 1 }}>Status</Text>
            </View>
            {sepp_assessable_controls.map((ctrl, i) => (
              <View key={i} style={{ flexDirection: 'row', borderBottom: i < sepp_assessable_controls.length - 1 ? '1pt solid #f3f4f6' : undefined }}>
                <Text style={{ fontSize: 7, color: '#374151', padding: 4, flex: 2 }}>{ctrl.instrument}</Text>
                <Text style={{ fontSize: 7, color: '#374151', padding: 4, flex: 2 }}>{ctrl.control}</Text>
                <Text style={{ fontSize: 7, color: '#374151', padding: 4, flex: 3 }}>{ctrl.requirement}</Text>
                <Text style={{ fontSize: 7, color: ctrl.status === 'pending' ? '#9ca3af' : '#374151', padding: 4, flex: 1, fontStyle: 'italic' }}>
                  {ctrl.status === 'pending' ? 'Pending' : ctrl.status}
                </Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* ---- 5. LEP Standards Assessment ---- */}
      {lep_assessable_standards && lep_assessable_standards.length > 0 && (
        <View style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 12, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 8, paddingBottom: 4, borderBottom: '1pt solid #0f766e' }}>
            5. Local Environmental Plan (LEP) Development Standards
          </Text>
          <Text style={{ fontSize: 8, color: '#6b7280', marginBottom: 6, fontStyle: 'italic' }}>
            LEP controls applicable to this assessment. Proposal column to be completed by the consultant.
          </Text>
          <View style={{ border: '1pt solid #e5e7eb' }}>
            <View style={{ flexDirection: 'row', backgroundColor: '#f3f4f6', borderBottom: '1pt solid #e5e7eb' }}>
              <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 1 }}>Clause</Text>
              <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 2 }}>Control</Text>
              <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 2 }}>Requirement</Text>
              <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 2 }}>Proposal</Text>
              <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 1 }}>Status</Text>
              <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 3 }}>Source</Text>
            </View>
            {lep_assessable_standards.map((std, i) => (
              <View key={i} style={{ flexDirection: 'row', borderBottom: i < lep_assessable_standards.length - 1 ? '1pt solid #f3f4f6' : undefined }}>
                <Text style={{ fontSize: 7, color: '#374151', padding: 4, flex: 1 }}>{std.clause}</Text>
                <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 2 }}>{std.control}</Text>
                <Text style={{ fontSize: 7, color: '#374151', padding: 4, flex: 2 }}>{std.requirement}</Text>
                <Text style={{ fontSize: 7, color: std.proposal ? '#374151' : '#9ca3af', padding: 4, flex: 2, fontStyle: std.proposal ? 'normal' : 'italic' }}>{std.proposal ?? '[to be completed]'}</Text>
                <Text style={{ fontSize: 7, padding: 4, flex: 1, fontFamily: std.status !== 'pending' ? 'Helvetica-Bold' : undefined,
                  color: std.status === 'complies' ? '#15803d' : std.status === 'varies' ? '#d97706' : '#9ca3af',
                }}>
                  {std.status === 'pending' ? 'Pending' : std.status === 'complies' ? 'Complies' : std.status === 'varies' ? 'Varies' : std.status}
                </Text>
                <Text style={{ fontSize: 7, color: '#6b7280', padding: 4, flex: 3, fontStyle: 'italic' }}>{std.source ?? ''}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* ---- Footer ---- */}
      <View style={styles.footer}>
        <Text style={styles.footerLeft}>{footerRef}</Text>
        <Text style={styles.footerCenter}>{property.address}</Text>
        <Text style={styles.footerRight}>Page 3</Text>
      </View>
    </Page>
  );
}
