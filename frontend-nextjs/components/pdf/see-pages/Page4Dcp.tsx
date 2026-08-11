import { Page, View, Text } from '@react-pdf/renderer';
import { styles } from '../styles';
import { ProvisionTable } from '../ProvisionTable';
import { sectionStatusMeta, truncateForPdf } from '@/lib/pdf/see-helpers';
import { parseSectionKey } from '@/lib/see/sectionKey';
import { SEEComputedData } from '@/lib/see/section-aggregation';

export function Page4Dcp({ computed }: { computed: SEEComputedData }) {
  const {
    property, chapter_assertions, topic_assertions, council_pdf_url,
    intake_answers, ancillaryWorksWithNoProvisions,
    // Section-level model
    useSectionModel,
    secVaries, secComplies, secNA, secFlagged,
    secScopeTotal, secAssessedTotal, secUnassessedTotal, secAssessedPct,
    secSortedParts, secUnassessedList,
    // Provision-level model
    totalCount, annotatedCount, unannotatedCount,
    variesProvisions, compliesProvisions, naManualProvisions, naIntakeProvisions,
    variesGroups, compliesGroups, naManualGroups, naIntakeGroups,
    compliesPct, variesPct, naPct, assessedPct,
    unannotatedProvisions,
    footerRef,
  } = computed;

  return (
    <Page size="A4" style={styles.page}>
      <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 12, paddingBottom: 6, borderBottom: '2pt solid #0f766e' }}>
        6. Development Control Plan Assessment
      </Text>

      {/* ---- Cover statement (Schedule B reference) ---- */}
      {/* verdict-ok: the count and the claim both come from chapter_assertions /
          topic_assertions, which this component receives; Schedule B IS the list of
          provisions asserted non-applicable, so the sentence restates received data. */}
      {((chapter_assertions?.length ?? 0) > 0 || (topic_assertions?.length ?? 0) > 0) && (
        <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5, marginBottom: 10 }}>
          {(chapter_assertions?.length ?? 0) > 0
            ? `All provisions of the applicable Development Control Plan have been considered. The ${chapter_assertions!.length} DCP chapter${chapter_assertions!.length !== 1 ? 's' : ''} listed in Schedule B relate to works and uses not proposed and are not applicable to this development. Provisions assessed for compliance are set out in Schedule A below.`
            : `All provisions of the applicable Development Control Plan have been considered. The ${topic_assertions!.length} topic categor${topic_assertions!.length !== 1 ? 'ies' : 'y'} listed in Schedule B relate to works and uses not proposed and are not applicable to this development. Provisions assessed for compliance are set out in Schedule A below.`
          }
        </Text>
      )}

      {useSectionModel ? (
        /* ================================================================
           SECTION-LEVEL DCP ASSESSMENT (new model)
           ================================================================ */
        <>
          {/* Summary table */}
          <View style={{ border: '1pt solid #e5e7eb', marginBottom: 14 }}>
            <View style={{ backgroundColor: secAssessedPct === 100 ? '#f0fdf4' : '#fffbeb', padding: '6 8', borderBottom: '1pt solid #e5e7eb', flexDirection: 'row', justifyContent: 'space-between' }}>
              <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: secAssessedPct === 100 ? '#166534' : '#92400e' }}>
                {secScopeTotal} DCP sections in scope | {secAssessedPct}% assessed
              </Text>
              {secAssessedTotal > 0 && (
                <Text style={{ fontSize: 8, color: '#374151' }}>
                  Complies {secComplies.length} | Varies {secVaries.length} | N/A {secNA.length}{secFlagged.length > 0 ? ` | Flagged ${secFlagged.length}` : ''}
                </Text>
              )}
            </View>
            <View style={{ backgroundColor: '#f3f4f6', flexDirection: 'row', borderBottom: '1pt solid #e5e7eb', padding: '4 8' }}>
              <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 2 }}>Status</Text>
              <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 1, textAlign: 'right' }}>Sections</Text>
              <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 3, marginLeft: 8 }}>Notes</Text>
            </View>
            {/* Varies */}
            <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8', backgroundColor: secVaries.length > 0 ? '#fffbeb' : '#ffffff' }}>
              <Text style={{ fontSize: 8, color: '#d97706', fontFamily: 'Helvetica-Bold', flex: 2 }}>Requires attention (Varies)</Text>
              <Text style={{ fontSize: 8, color: '#d97706', flex: 1, textAlign: 'right' }}>{secVaries.length}</Text>
              <Text style={{ fontSize: 7, color: '#6b7280', flex: 3, marginLeft: 8 }}>
                {secVaries.length > 0 ? 'Sections where the development does not fully comply — justification required.' : 'No sections marked as Varies.'}
              </Text>
            </View>
            {/* Complies */}
            <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8' }}>
              <Text style={{ fontSize: 8, color: '#15803d', fontFamily: 'Helvetica-Bold', flex: 2 }}>Complies</Text>
              <Text style={{ fontSize: 8, color: '#15803d', flex: 1, textAlign: 'right' }}>{secComplies.length}</Text>
              <Text style={{ fontSize: 7, color: '#6b7280', flex: 3, marginLeft: 8 }}>
                {secComplies.length > 0 ? 'Sections assessed as complying with the applicable controls.' : 'No sections confirmed as complying.'}
              </Text>
            </View>
            {/* N/A */}
            <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8' }}>
              <Text style={{ fontSize: 8, color: '#6b7280', fontFamily: 'Helvetica-Bold', flex: 2 }}>Not applicable</Text>
              <Text style={{ fontSize: 8, color: '#6b7280', flex: 1, textAlign: 'right' }}>{secNA.length}</Text>
              <Text style={{ fontSize: 7, color: '#6b7280', flex: 3, marginLeft: 8 }}>
                {secNA.length > 0 ? 'Sections assessed as not applicable to this proposal.' : 'No sections assessed as not applicable.'}
              </Text>
            </View>
            {/* Flagged */}
            {secFlagged.length > 0 && (
              <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8', backgroundColor: '#fef2f2' }}>
                <Text style={{ fontSize: 8, color: '#dc2626', fontFamily: 'Helvetica-Bold', flex: 2 }}>Flagged for review</Text>
                <Text style={{ fontSize: 8, color: '#dc2626', flex: 1, textAlign: 'right' }}>{secFlagged.length}</Text>
                <Text style={{ fontSize: 7, color: '#6b7280', flex: 3, marginLeft: 8 }}>Requires further review or referral before lodgement.</Text>
              </View>
            )}
            {/* Unassessed */}
            <View style={{ flexDirection: 'row', padding: '3 8', backgroundColor: secUnassessedTotal > 0 ? '#fef3c7' : '#f0fdf4' }}>
              <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', flex: 2, color: secUnassessedTotal > 0 ? '#92400e' : '#166534' }}>
                {secUnassessedTotal > 0 ? 'Not yet assessed' : '✓ Fully assessed'}
              </Text>
              <Text style={{ fontSize: 8, flex: 1, textAlign: 'right', color: secUnassessedTotal > 0 ? '#92400e' : '#166534' }}>{secUnassessedTotal}</Text>
              <Text style={{ fontSize: 7, flex: 3, marginLeft: 8, color: secUnassessedTotal > 0 ? '#92400e' : '#166534' }}>
                {secUnassessedTotal > 0
                  ? `${secUnassessedTotal} of ${secScopeTotal} sections not yet assessed. Document is incomplete.`
                  : 'All sections in scope have been assessed.'}
              </Text>
            </View>
          </View>

          {/* Per-part section tables */}
          {secSortedParts.map(([part, sections]) => {
            const sortedSections = [...sections].sort((a, b) => {
              const na = parseSectionKey(a.section_key).sectionNumber;
              const nb = parseSectionKey(b.section_key).sectionNumber;
              return na.localeCompare(nb, undefined, { numeric: true });
            });
            return (
              <View key={part} style={{ marginBottom: 14 }}>
                <Text style={{ fontSize: 10, fontFamily: 'Helvetica-Bold', color: '#1f2937', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #d1d5db' }}>
                  {part}
                </Text>
                <View style={{ border: '1pt solid #e5e7eb' }}>
                  <View style={{ flexDirection: 'row', backgroundColor: '#f3f4f6', borderBottom: '1pt solid #e5e7eb', padding: '3 6' }}>
                    <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 1 }}>Section</Text>
                    <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 2 }}>Title</Text>
                    <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 1 }}>Status</Text>
                    <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 4 }}>Compliance Narrative</Text>
                  </View>
                  {sortedSections.map((sec, idx) => {
                    const { sectionNumber } = parseSectionKey(sec.section_key);
                    const displaySectionNumber = sectionNumber === 'general' ? '—' : sectionNumber;
                    const { label, color } = sectionStatusMeta(sec.status);
                    return (
                      <View key={sec.section_key} style={{ borderBottom: idx < sortedSections.length - 1 ? '1pt solid #f3f4f6' : undefined, backgroundColor: idx % 2 === 0 ? '#ffffff' : '#fafafa' }}>
                        <View style={{ flexDirection: 'row', padding: '3 6' }}>
                          <Text style={{ fontSize: 7, color: '#374151', flex: 1 }}>{displaySectionNumber}</Text>
                          <Text style={{ fontSize: 7, color: '#374151', flex: 2 }}>{truncateForPdf(sec.section_title || '—', 80)}</Text>
                          <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color, flex: 1 }}>{label}</Text>
                          <Text style={{ fontSize: 7, color: sec.narrative ? '#374151' : '#9ca3af', flex: 4, fontStyle: sec.narrative ? 'normal' : 'italic' }}>
                            {sec.narrative ? truncateForPdf(sec.narrative) : '[No narrative recorded]'}
                          </Text>
                        </View>
                        {sec.key_provisions && sec.key_provisions.length > 0 && (
                          <View style={{ paddingLeft: 10, paddingRight: 6, paddingBottom: 3, backgroundColor: '#f9fafb' }}>
                            <Text style={{ fontSize: 6, color: '#6b7280', fontStyle: 'italic' }}>
                              {'DCP: ' + sec.key_provisions.join(' / ')}
                            </Text>
                          </View>
                        )}
                      </View>
                    );
                  })}
                </View>
              </View>
            );
          })}

          {/* Ancillary scope note */}
          {ancillaryWorksWithNoProvisions.length > 0 && (
            <View style={{ marginBottom: 12, padding: '6 8', backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb' }}>
              <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#9ca3af', marginBottom: 3 }}>
                Ancillary Works — No DCP Provisions for Development Type
              </Text>
              <Text style={{ fontSize: 8, color: '#9ca3af', marginBottom: 6, fontStyle: 'italic' }}>
                The following ancillary works are included in the proposal scope. The applicable DCP does not contain provisions specifically addressing these work types for the nominated development type.
              </Text>
              {ancillaryWorksWithNoProvisions.map(w => (
                <View key={w.value} style={{ flexDirection: 'row', paddingVertical: 2, borderBottom: '0.5pt solid #f3f4f6' }}>
                  <Text style={{ fontSize: 7, color: '#6b7280', flex: 2 }}>{w.label}</Text>
                  <Text style={{ fontSize: 7, color: '#9ca3af', flex: 3 }}>No DCP provisions for this work type under the nominated development type</Text>
                </View>
              ))}
            </View>
          )}

          {/* 6.5 Unassessed sections */}
          {secUnassessedList.length > 0 && (
            <View style={{ marginBottom: 16 }}>
              <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#92400e', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #fed7aa' }}>
                {`6.5 Sections Requiring Further Assessment (${secUnassessedList.length})`}
              </Text>
              <Text style={{ fontSize: 8, color: '#92400e', marginBottom: 6 }}>
                The following DCP sections have not yet been assessed. This document is incomplete until all sections below have been addressed.
              </Text>
              <View style={{ border: '1pt solid #e5e7eb' }}>
                <View style={{ flexDirection: 'row', backgroundColor: '#f3f4f6', borderBottom: '1pt solid #e5e7eb', padding: '3 8' }}>
                  <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 1 }}>Part</Text>
                  <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 1 }}>Section</Text>
                  <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 3 }}>Title</Text>
                </View>
                {secUnassessedList.map((s, idx) => {
                  const { part, sectionNumber } = parseSectionKey(s.section_key);
                  const displaySectionNumber = sectionNumber === 'general' ? '—' : sectionNumber;
                  return (
                    <View key={s.section_key} style={{ flexDirection: 'row', borderBottom: idx < secUnassessedList.length - 1 ? '1pt solid #f3f4f6' : undefined, padding: '2 8', backgroundColor: idx % 2 === 0 ? '#ffffff' : '#fafafa' }}>
                      <Text style={{ fontSize: 7, color: '#374151', flex: 1 }}>{part}</Text>
                      <Text style={{ fontSize: 7, color: '#374151', flex: 1 }}>{displaySectionNumber}</Text>
                      <Text style={{ fontSize: 7, color: '#6b7280', flex: 3 }}>{s.section_title || '—'}</Text>
                    </View>
                  );
                })}
              </View>
            </View>
          )}
        </>
      ) : (
        /* ================================================================
           PROVISION-LEVEL DCP ASSESSMENT (legacy model)
           ================================================================ */
        <>
          {/* Assessment status summary */}
          <View style={{ border: '1pt solid #e5e7eb', marginBottom: 14 }}>
            {totalCount > 0 && (
              <View style={{ backgroundColor: assessedPct === 100 ? '#f0fdf4' : '#fffbeb', padding: '6 8', borderBottom: '1pt solid #e5e7eb', flexDirection: 'row', justifyContent: 'space-between' }}>
                <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: assessedPct === 100 ? '#166534' : '#92400e' }}>
                  {totalCount} applicable provisions | {assessedPct}% assessed
                </Text>
                {annotatedCount > 0 && (
                  <Text style={{ fontSize: 8, color: '#374151' }}>
                    Complies {compliesPct}% | Varies {variesPct}% | N/A {naPct}%
                  </Text>
                )}
              </View>
            )}
            <View style={{ backgroundColor: '#f3f4f6', flexDirection: 'row', borderBottom: '1pt solid #e5e7eb', padding: '4 8' }}>
              <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 2 }}>Status</Text>
              <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 1, textAlign: 'right' }}>Provisions</Text>
              <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 3, marginLeft: 8 }}>Notes</Text>
            </View>
            <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8', backgroundColor: variesProvisions.length > 0 ? '#fffbeb' : '#ffffff' }}>
              <Text style={{ fontSize: 8, color: '#d97706', fontFamily: 'Helvetica-Bold', flex: 2 }}>Requires attention (Varies)</Text>
              <Text style={{ fontSize: 8, color: '#d97706', flex: 1, textAlign: 'right' }}>{variesProvisions.length}</Text>
              <Text style={{ fontSize: 7, color: '#6b7280', flex: 3, marginLeft: 8 }}>
                {variesProvisions.length > 0 ? 'Development may not fully comply — justification required. See section 6.1.' : 'No provisions marked as Varies.'}
              </Text>
            </View>
            <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8' }}>
              <Text style={{ fontSize: 8, color: '#15803d', fontFamily: 'Helvetica-Bold', flex: 2 }}>Complies</Text>
              <Text style={{ fontSize: 8, color: '#15803d', flex: 1, textAlign: 'right' }}>{compliesProvisions.length}</Text>
              <Text style={{ fontSize: 7, color: '#6b7280', flex: 3, marginLeft: 8 }}>
                {compliesProvisions.length > 0 ? 'Assessed as compliant by the applicant. See section 6.2.' : 'No provisions confirmed compliant.'}
              </Text>
            </View>
            <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8' }}>
              <Text style={{ fontSize: 8, color: '#6b7280', fontFamily: 'Helvetica-Bold', flex: 2 }}>Not applicable (planner)</Text>
              <Text style={{ fontSize: 8, color: '#6b7280', flex: 1, textAlign: 'right' }}>{naManualProvisions.length}</Text>
              <Text style={{ fontSize: 7, color: '#6b7280', flex: 3, marginLeft: 8 }}>
                {naManualProvisions.length > 0 ? 'Manually assessed as not applicable. See section 6.3.' : 'No provisions manually assessed as not applicable.'}
              </Text>
            </View>
            <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8', backgroundColor: '#f9fafb' }}>
              <Text style={{ fontSize: 8, color: '#9ca3af', fontFamily: 'Helvetica-Bold', flex: 2 }}>Not applicable (intake triage)</Text>
              <Text style={{ fontSize: 8, color: '#9ca3af', flex: 1, textAlign: 'right' }}>{naIntakeProvisions.length}</Text>
              <Text style={{ fontSize: 7, color: '#9ca3af', flex: 3, marginLeft: 8 }}>
                {naIntakeProvisions.length > 0
                  ? 'Auto-excluded: applicability trigger absent in intake. See section 6.4 and cover page.'
                  : intake_answers ? 'Intake completed — no provisions auto-excluded.' : 'Intake not completed.'}
              </Text>
            </View>
            <View style={{ flexDirection: 'row', padding: '3 8', backgroundColor: unannotatedCount > 0 ? '#fef3c7' : '#f0fdf4' }}>
              <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', flex: 2, color: unannotatedCount > 0 ? '#92400e' : '#166534' }}>
                {unannotatedCount > 0 ? '⚠ Not yet assessed' : '✓ Fully assessed'}
              </Text>
              <Text style={{ fontSize: 8, flex: 1, textAlign: 'right', color: unannotatedCount > 0 ? '#92400e' : '#166534' }}>{unannotatedCount}</Text>
              <Text style={{ fontSize: 7, flex: 3, marginLeft: 8, color: unannotatedCount > 0 ? '#92400e' : '#166534' }}>
                {unannotatedCount > 0
                  ? `${unannotatedCount} of ${totalCount} provisions not annotated. Document is incomplete.`
                  : 'All applicable provisions have been assessed.'}
              </Text>
            </View>
          </View>

          {variesGroups.length > 0 ? (
            <View style={{ marginBottom: 16 }}>
              <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#d97706', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #d97706' }}>
                {`6.1 Provisions Requiring Attention — Varies (${variesProvisions.length})`}
              </Text>
              <Text style={{ fontSize: 8, color: '#92400e', marginBottom: 8 }}>
                These provisions have been identified as varying from the DCP standard. Each requires a planning response addressing how the variation is justified or will be resolved.
              </Text>
              {variesGroups.map((group, idx) => (
                <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} councilPdfUrl={council_pdf_url} />
              ))}
            </View>
          ) : (
            <View style={{ marginBottom: 12, padding: '6 8', backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb' }}>
              <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#6b7280', marginBottom: 2 }}>6.1 Provisions Requiring Attention — Varies (0)</Text>
              <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>No provisions have been marked as Varies.</Text>
            </View>
          )}

          {compliesGroups.length > 0 ? (
            <View style={{ marginBottom: 16 }}>
              <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#15803d', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #15803d' }}>
                {`6.2 Complying Provisions (${compliesProvisions.length})`}
              </Text>
              {compliesGroups.map((group, idx) => (
                <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} councilPdfUrl={council_pdf_url} />
              ))}
            </View>
          ) : (
            <View style={{ marginBottom: 12, padding: '6 8', backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb' }}>
              <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#6b7280', marginBottom: 2 }}>6.2 Complying Provisions (0)</Text>
              <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>No provisions have been confirmed as complying.</Text>
            </View>
          )}

          {naManualGroups.length > 0 ? (
            <View style={{ marginBottom: 16 }}>
              <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#6b7280', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #9ca3af' }}>
                {`6.3 Not Applicable — Planner Assessment (${naManualProvisions.length})`}
              </Text>
              <Text style={{ fontSize: 8, color: '#6b7280', marginBottom: 6 }}>
                These provisions have been assessed by the applicant as not applicable to the proposed development.
              </Text>
              {naManualGroups.map((group, idx) => (
                <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} councilPdfUrl={council_pdf_url} />
              ))}
            </View>
          ) : (
            <View style={{ marginBottom: 12, padding: '6 8', backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb' }}>
              <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#6b7280', marginBottom: 2 }}>6.3 Not Applicable — Planner Assessment (0)</Text>
              <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>No provisions were manually assessed as not applicable.</Text>
            </View>
          )}

          {naIntakeGroups.length > 0 ? (
            <View style={{ marginBottom: 16 }}>
              <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#9ca3af', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #d1d5db' }}>
                {`6.4 Not Applicable — Excluded by Intake Triage (${naIntakeProvisions.length})`}
              </Text>
              <Text style={{ fontSize: 7, color: '#9ca3af', marginBottom: 6, fontStyle: 'italic' }}>
                These provisions were automatically excluded because their applicability trigger was confirmed as absent in the structured intake completed by the applicant. The confirmed inputs are recorded in the cover page table.
              </Text>
              {naIntakeGroups.map((group, idx) => (
                <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} councilPdfUrl={council_pdf_url} />
              ))}
            </View>
          ) : (
            <View style={{ marginBottom: 12, padding: '6 8', backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb' }}>
              <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#9ca3af', marginBottom: 2 }}>6.4 Not Applicable — Excluded by Intake Triage (0)</Text>
              <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>
                {intake_answers ? 'Intake completed — no provisions auto-excluded.' : 'Intake not completed — no automatic exclusions applied.'}
              </Text>
            </View>
          )}

          {ancillaryWorksWithNoProvisions.length > 0 && (
            <View style={{ marginBottom: 12, padding: '6 8', backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb' }}>
              <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#9ca3af', marginBottom: 3 }}>
                Ancillary Works — No DCP Provisions for Development Type
              </Text>
              <Text style={{ fontSize: 8, color: '#9ca3af', marginBottom: 6, fontStyle: 'italic' }}>
                The following ancillary works are included in the proposal scope. The applicable DCP does not contain provisions specifically addressing these work types for the nominated development type.
              </Text>
              <View style={{ flexDirection: 'row', borderBottom: '0.5pt solid #d1d5db', paddingBottom: 3, marginBottom: 3 }}>
                <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#6b7280', flex: 2 }}>Ancillary Work</Text>
                <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#6b7280', flex: 3 }}>Basis</Text>
              </View>
              {ancillaryWorksWithNoProvisions.map(w => (
                <View key={w.value} style={{ flexDirection: 'row', paddingVertical: 2, borderBottom: '0.5pt solid #f3f4f6' }}>
                  <Text style={{ fontSize: 7, color: '#6b7280', flex: 2 }}>{w.label}</Text>
                  <Text style={{ fontSize: 7, color: '#9ca3af', flex: 3 }}>DCP contains no provisions for this work type under the nominated development type</Text>
                </View>
              ))}
            </View>
          )}

          {unannotatedProvisions.length > 0 && (
            <View style={{ marginBottom: 16 }}>
              <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#92400e', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #fed7aa' }}>
                {`6.5 Provisions Requiring Further Assessment (${unannotatedProvisions.length})`}
              </Text>
              <Text style={{ fontSize: 8, color: '#92400e', marginBottom: 6 }}>
                The following provisions have not yet been assessed. This document is incomplete until all provisions below have been addressed.
              </Text>
              <View style={{ border: '1pt solid #e5e7eb' }}>
                <View style={{ flexDirection: 'row', backgroundColor: '#f3f4f6', borderBottom: '1pt solid #e5e7eb', padding: '3 8' }}>
                  <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 2 }}>Section</Text>
                  <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 3 }}>Provision (first line)</Text>
                  <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 1, textAlign: 'right' }}>Source</Text>
                </View>
                {unannotatedProvisions.map((p, idx) => {
                  const firstLine = (p.provision_text || '').split('\n')[0].substring(0, 120);
                  const section = p.v2_dcp_part || '—';
                  const source = p.pdf_printed_page ? `PDF p.${p.pdf_printed_page}` : '';
                  return (
                    <View key={p.id} style={{ flexDirection: 'row', borderBottom: idx < unannotatedProvisions.length - 1 ? '1pt solid #f3f4f6' : undefined, padding: '2 8', backgroundColor: idx % 2 === 0 ? '#ffffff' : '#fafafa' }}>
                      <Text style={{ fontSize: 7, color: '#374151', flex: 2 }}>{section}</Text>
                      <Text style={{ fontSize: 7, color: '#6b7280', flex: 3 }}>{firstLine}{firstLine.length >= 120 ? '…' : ''}</Text>
                      <Text style={{ fontSize: 7, color: '#9ca3af', flex: 1, textAlign: 'right' }}>{source}</Text>
                    </View>
                  );
                })}
              </View>
            </View>
          )}
        </>
      )}

      {/* ---- Schedule B — Non-Applicable DCP Chapters/Topics ---- */}
      {((chapter_assertions?.length ?? 0) > 0 || (topic_assertions?.length ?? 0) > 0) && (
        <View style={{ marginTop: 16 }}>
          {(chapter_assertions?.length ?? 0) > 0 ? (
            <>
              <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#374151', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #d1d5db' }}>
                {`Schedule B — Non-Applicable DCP Chapters (${chapter_assertions!.length})`}
              </Text>
              <Text style={{ fontSize: 8, color: '#6b7280', marginBottom: 6, fontStyle: 'italic' }}>
                The following DCP chapters were assessed as not applicable to the proposed development. Provisions within these chapters are excluded from Schedule A.
              </Text>
              <View style={{ flexDirection: 'row', borderBottom: '1pt solid #d1d5db', paddingBottom: 4, marginBottom: 4 }}>
                <Text style={{ flex: 1, fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151' }}>DCP Chapter</Text>
                <Text style={{ flex: 2, fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151' }}>Chapter Name</Text>
                <Text style={{ flex: 3, fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151' }}>Basis for Non-Applicability</Text>
              </View>
              {chapter_assertions!.map((ca, i) => (
                <View key={i} style={{ flexDirection: 'row', paddingVertical: 3, borderBottom: '0.5pt solid #f3f4f6' }}>
                  <Text style={{ flex: 1, fontSize: 8, color: '#374151', fontFamily: 'Helvetica-Bold' }}>{ca.chapter_label}</Text>
                  <Text style={{ flex: 2, fontSize: 8, color: '#374151' }}>{ca.chapter_desc || '—'}</Text>
                  <Text style={{ flex: 3, fontSize: 8, color: '#6b7280' }}>{ca.reason}</Text>
                </View>
              ))}
            </>
          ) : (
            <>
              <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#374151', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #d1d5db' }}>
                {`Schedule B — Non-Applicable DCP Topics (${topic_assertions!.length})`}
              </Text>
              <Text style={{ fontSize: 8, color: '#6b7280', marginBottom: 6, fontStyle: 'italic' }}>
                The following topic categories were assessed as not applicable to the proposed development. Provisions within these categories are excluded from Schedule A.
              </Text>
              <View style={{ flexDirection: 'row', borderBottom: '1pt solid #d1d5db', paddingBottom: 4, marginBottom: 4 }}>
                <Text style={{ flex: 1, fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151' }}>Topic</Text>
                <Text style={{ flex: 3, fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151' }}>Basis for Non-Applicability</Text>
              </View>
              {topic_assertions!.map((ta, i) => (
                <View key={i} style={{ flexDirection: 'row', paddingVertical: 3, borderBottom: '0.5pt solid #f3f4f6' }}>
                  <Text style={{ flex: 1, fontSize: 8, color: '#374151', textTransform: 'capitalize' }}>
                    {ta.topic.replace(/_/g, ' ')}
                  </Text>
                  <Text style={{ flex: 3, fontSize: 8, color: '#6b7280' }}>{ta.reason}</Text>
                </View>
              ))}
            </>
          )}
        </View>
      )}

      {/* ---- Footer ---- */}
      <View style={styles.footer}>
        <Text style={styles.footerLeft}>{footerRef}</Text>
        <Text style={styles.footerCenter}>{property.address}</Text>
        <Text style={styles.footerRight}>DCP Assessment</Text>
      </View>
    </Page>
  );
}
