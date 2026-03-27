import { Page, View, Text } from '@react-pdf/renderer';
import { styles } from '../styles';
import { DataRow } from '../DataRow';
import { SEEComputedData } from '@/lib/see/section-aggregation';

export function Page6Conclusion({ computed }: { computed: SEEComputedData }) {
  const {
    property, generated_date, docRef, footerRef, intake_answers,
    chapter_assertions, topic_assertions,
    devDesc,
    // Section-level model
    useSectionModel,
    secScopeTotal, secAssessedTotal, secUnassessedTotal,
    secVaries, secComplies, secNA, secFlagged,
    // Provision-level model
    totalCount, annotatedCount, unannotatedCount,
    compliesProvisions, variesProvisions, naManualProvisions, naIntakeProvisions,
    compliesPct, variesPct, naPct,
    client_ref, prepared_by,
  } = computed;

  return (
    <Page size="A4" style={styles.page}>
      <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 12, paddingBottom: 6, borderBottom: '2pt solid #0f766e' }}>
        8. Conclusion
      </Text>

      {/* Auto-generated conclusion from assessment data */}
      <View style={{ marginBottom: 10 }}>
        <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5, marginBottom: 6 }}>
          {`This Statement of Environmental Effects has assessed the proposed development at ${property.address} against the applicable planning controls under the Environmental Planning and Assessment Act 1979 (NSW).`}
        </Text>
        {useSectionModel ? (
          <>
            {secScopeTotal > 0 && secAssessedTotal > 0 && (
              <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5, marginBottom: 6 }}>
                {`Of the ${secScopeTotal} DCP sections in scope, ${secComplies.length} have been assessed as complying with the applicable controls${secVaries.length > 0 ? `, ${secVaries.length} require${secVaries.length === 1 ? 's' : ''} further consideration as the development varies from the applicable standard` : ''}${secNA.length > 0 ? `, and ${secNA.length} are not applicable to the proposed works` : ''}${secFlagged.length > 0 ? `. ${secFlagged.length} section${secFlagged.length !== 1 ? 's have' : ' has'} been flagged for further review` : ''}.`}
              </Text>
            )}
            {secVaries.length > 0 && (
              <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5, marginBottom: 6 }}>
                {`The ${secVaries.length} section${secVaries.length !== 1 ? 's' : ''} identified as varying from the DCP standard should be assessed on planning merit having regard to the objectives of the applicable controls.`}
              </Text>
            )}
            {secUnassessedTotal > 0 && (
              <Text style={{ fontSize: 9, color: '#92400e', lineHeight: 1.5, marginBottom: 6 }}>
                {`Note: ${secUnassessedTotal} DCP section${secUnassessedTotal !== 1 ? 's have' : ' has'} not yet been assessed. This document is incomplete and must not be lodged until all sections in Section 6.5 have been addressed.`}
              </Text>
            )}
          </>
        ) : (
          <>
            {totalCount > 0 && annotatedCount > 0 && (
              <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5, marginBottom: 6 }}>
                {`Of the ${totalCount} applicable DCP provisions, ${compliesProvisions.length} (${compliesPct}%) have been assessed as complying with the relevant controls${variesProvisions.length > 0 ? `, ${variesProvisions.length} (${variesPct}%) require further consideration as the development varies from the applicable standard` : ''}${naManualProvisions.length + naIntakeProvisions.length > 0 ? `, and ${naManualProvisions.length + naIntakeProvisions.length} (${naPct}%) are not applicable to the proposed works` : ''}.`}
              </Text>
            )}
            {variesProvisions.length > 0 && (
              <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5, marginBottom: 6 }}>
                {`The ${variesProvisions.length} provision${variesProvisions.length !== 1 ? 's' : ''} identified as varying from the DCP standard${variesProvisions.length !== 1 ? ' are' : ' is'} detailed in Section 6.1 of this report. Each variation should be assessed on its planning merit having regard to the objectives of the applicable control.`}
              </Text>
            )}
            {unannotatedCount > 0 && (
              <Text style={{ fontSize: 9, color: '#92400e', lineHeight: 1.5, marginBottom: 6 }}>
                {`Note: ${unannotatedCount} provision${unannotatedCount !== 1 ? 's have' : ' has'} not yet been assessed. This document is incomplete and must not be lodged until all provisions in Section 6.5 have been addressed.`}
              </Text>
            )}
          </>
        )}
      </View>
      <View style={{ backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb', padding: 12, marginBottom: 16 }}>
        <Text style={{ fontSize: 9, color: '#6b7280', fontStyle: 'italic' }}>
          [Consultant to review the above summary and add: (1) planning merit justification for any variations, (2) consistency with zone objectives, and (3) recommendation for consent.]
        </Text>
      </View>

      {/* Report metadata */}
      <View style={{ ...styles.section, marginTop: 8 }}>
        <Text style={styles.sectionTitle}>Report Information</Text>
        <View style={styles.dataTable}>
          <DataRow label="Generated:" value={generated_date} />
          <DataRow label="Property:" value={property.address} />
          {useSectionModel ? (
            <>
              <DataRow label="Assessment model:" value="Section-level (DCP sections as unit of assessment)" />
              <DataRow label="DCP sections in scope:" value={`${secScopeTotal}`} />
              <DataRow label="Sections assessed:" value={`${secAssessedTotal}`} />
              <DataRow label="  — Requires attention (Varies):" value={`${secVaries.length}`} />
              <DataRow label="  — Complies:" value={`${secComplies.length}`} />
              <DataRow label="  — Not applicable:" value={`${secNA.length}`} />
              {secFlagged.length > 0 && <DataRow label="  — Flagged for review:" value={`${secFlagged.length}`} />}
              <DataRow label="Sections not yet assessed:" value={secUnassessedTotal > 0 ? `${secUnassessedTotal} — INCOMPLETE` : '0 — fully assessed'} />
            </>
          ) : (
            <>
              <DataRow label="Total applicable provisions:" value={`${totalCount}`} />
              <DataRow label="Annotated (Varies + Complies + N/A):" value={`${annotatedCount}`} />
              <DataRow label="  — Requires attention (Varies):" value={`${variesProvisions.length}`} />
              <DataRow label="  — Complies:" value={`${compliesProvisions.length}`} />
              <DataRow label="  — Not applicable (planner):" value={`${naManualProvisions.length}`} />
              <DataRow label="  — Not applicable (intake triage):" value={`${naIntakeProvisions.length}`} />
              <DataRow label="Not yet assessed:" value={unannotatedCount > 0 ? `${unannotatedCount} — INCOMPLETE` : '0 — fully assessed'} />
            </>
          )}
          <DataRow label="Structured intake:" value={intake_answers ? 'Completed' : 'Not completed — no automatic exclusions applied'} />
          {(chapter_assertions?.length ?? 0) > 0 && (
            <DataRow label="Schedule B — dismissed chapters:" value={`${chapter_assertions!.length} DCP chapter${chapter_assertions!.length !== 1 ? 's' : ''} asserted not applicable`} />
          )}
          {(chapter_assertions?.length ?? 0) === 0 && (topic_assertions?.length ?? 0) > 0 && (
            <DataRow label="Schedule B — dismissed topics:" value={`${topic_assertions!.length} topic${topic_assertions!.length !== 1 ? 's' : ''} asserted not applicable`} />
          )}
          <DataRow label="Development description:" value={devDesc || '[Not provided]'} />
        </View>
      </View>

      {/* Legal disclaimer */}
      <View style={{ marginTop: 16, padding: 10, backgroundColor: '#fef2f2', border: '1pt solid #fecaca', borderRadius: 2 }}>
        <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#991b1b', marginBottom: 4 }}>
          IMPORTANT DISCLAIMER
        </Text>
        <Text style={{ fontSize: 7, color: '#7f1d1d', lineHeight: 1.4 }}>
          This document is a draft scaffold generated by PlotDetect for planning reference only. It does not constitute professional planning advice and must not be lodged with a Development Application without review, completion, and verification by a qualified planning consultant. The information is provided in good faith based on available data but may not be complete, current, or correct. Users rely on this document entirely at their own risk. PlotDetect accepts no liability for decisions made based on this document.
        </Text>
      </View>

      {/* ---- Footer ---- */}
      <View style={styles.footer}>
        <Text style={styles.footerLeft}>{footerRef}</Text>
        <Text style={styles.footerCenter}>{property.address}</Text>
        <Text style={styles.footerRight}>Generated {generated_date}</Text>
      </View>
    </Page>
  );
}
