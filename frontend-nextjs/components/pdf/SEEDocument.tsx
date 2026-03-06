// SEE PDF Document — deterministic scaffold, 100% data-driven
// No AI, no hardcoded LGA names, no hardcoded zone lists beyond domain logic

import { Document, Page, Text, View, Link } from '@react-pdf/renderer';
import { SEEDocumentData } from '@/lib/see/types';
import { INTAKE_QUESTIONS, type IntakeAnswers } from '@/lib/see/intake';
import { ProvisionForPDF } from '@/lib/pdf/types';
import { ProvisionTable } from './ProvisionTable';
import { styles } from './styles';
import { groupProvisionsByTopic } from '@/lib/pdf/formatProvisions';
import { parseHtmlLink, containsHtml } from '@/lib/pdf/htmlUtils';
import { buildSeeIntro } from '@/lib/see/devTypes';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function capitalizeFirst(str: string): string {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/** Returns true if value looks like a bare number (not already including a unit label) */
function isNumeric(value: string | number | undefined): boolean {
  if (value === undefined || value === null) return false;
  return /^\d+(\.\d+)?$/.test(String(value).trim());
}


/**
 * Determines development pathway from property data.
 * Zone codes come from property.zone — never hardcoded comparisons beyond the SEPP schedule.
 */
function determineDevelopmentPathway(
  zone: string,
  heritage_in_hca: boolean,
  heritage_item: boolean
): { pathway: string; reason: string } {
  if (heritage_item) {
    return {
      pathway: 'Development Application (DA)',
      reason: 'Heritage item — CDC and exempt development not permitted',
    };
  }
  if (heritage_in_hca) {
    return {
      pathway: 'Development Application (DA)',
      reason: 'Heritage conservation area — CDC and exempt development restricted',
    };
  }
  // Housing SEPP 2021 eligible zones (derived from the SEPP schedule — these are the statutory zone codes)
  const HOUSING_SEPP_ZONES = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B4'];
  const zoneCode = zone.split(' ')[0];
  if (HOUSING_SEPP_ZONES.includes(zoneCode)) {
    return {
      pathway: 'Complying Development (CDC)',
      reason: `${zoneCode} zone — Housing SEPP 2021 CDC pathway available for eligible development`,
    };
  }
  return {
    pathway: 'Development Application (DA)',
    reason: `${zoneCode} zone — check exempt development criteria`,
  };
}

// ---------------------------------------------------------------------------
// Row helper for data tables
// ---------------------------------------------------------------------------

function DataRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.contextTableRow}>
      <Text style={styles.tableCellLabel}>{label}</Text>
      <Text style={styles.tableCellValue}>{value}</Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// SEE Document
// ---------------------------------------------------------------------------

export function SEEDocument({ data }: { data: SEEDocumentData }) {
  const { property, development_description, see_intro, annotated_provisions, all_provisions,
          generated_date, intake_answers, client_ref, prepared_by,
          pathway_determination, sepp_assessable_controls, lep_assessable_standards } = data;
  const { heritage_status, lot_dimensions, lep_controls, environmental_constraints,
          additional_local_provisions, planning_portal_layers } = property;

  // Provisions not yet annotated — listed in a final outstanding section
  const annotatedIds = new Set(annotated_provisions.map(p => p.id));
  const unannotatedProvisions = all_provisions.filter(p => !annotatedIds.has(p.id));

  const zoneCode = property.zone?.split(' ')[0] || '';
  const { pathway, reason } = determineDevelopmentPathway(
    property.zone || '',
    heritage_status.in_hca,
    heritage_status.heritage_item || false
  );

  // Housing SEPP eligibility derived purely from zone code in data
  const HOUSING_SEPP_ZONES = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B4'];
  const housingSeppApplies = HOUSING_SEPP_ZONES.includes(zoneCode);

  // DCP Assessment buckets
  const variesProvisions = annotated_provisions.filter(p => p.da_status === 'varies');
  const compliesProvisions = annotated_provisions.filter(p => p.da_status === 'complies');
  const naAllProvisions = annotated_provisions.filter(p => p.da_status === 'not_applicable');

  // Split N/A into intake-auto-excluded vs planner-assessed
  const naIntakeProvisions = naAllProvisions.filter(p => p.da_response?.startsWith('Excluded by intake:'));
  const naManualProvisions = naAllProvisions.filter(p => !p.da_response?.startsWith('Excluded by intake:'));

  const variesGroups = groupProvisionsByTopic(variesProvisions);
  const compliesGroups = groupProvisionsByTopic(compliesProvisions);
  const naManualGroups = groupProvisionsByTopic(naManualProvisions);
  const naIntakeGroups = groupProvisionsByTopic(naIntakeProvisions);

  const annotatedCount = annotated_provisions.length;
  const totalCount = all_provisions.length;
  const unannotatedCount = totalCount - annotatedCount;

  return (
    <Document>
      {/* ================================================================
          PAGE 1 — Cover + Introduction
          ================================================================ */}
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
          ) : development_description ? (
            <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5, marginBottom: 8 }}>
              {`This Statement of Environmental Effects has been prepared in support of a Development Application for ${development_description} at ${property.address}. The proposed development is subject to assessment under the Environmental Planning and Assessment Act 1979 (NSW).`}
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
          {development_description ? (
            <Text style={{ fontSize: 10, color: '#1f2937' }}>{development_description}</Text>
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
          <Text style={styles.footerLeft}>Draft Statement of Environmental Effects</Text>
          <Text style={styles.footerCenter}>{property.address}</Text>
          <Text style={styles.footerRight}>Page 1</Text>
        </View>
      </Page>

      {/* ================================================================
          PAGE 2 — Site and Statutory Context
          ================================================================ */}
      <Page size="A4" style={styles.page}>

        <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 12, paddingBottom: 6, borderBottom: '2pt solid #0f766e' }}>
          2. Site and Statutory Context
        </Text>

        {/* ---- 2.1 Property Details ---- */}
        <View style={{ ...styles.section }}>
          <Text style={styles.sectionTitle}>2.1 Property Details</Text>
          <View style={styles.dataTable}>
            <DataRow label="Address:" value={property.address} />
            <DataRow label="Former Council Area:" value={capitalizeFirst(property.former_council)} />
            <DataRow label="Zone:" value={property.zone || 'Not provided'} />

            {lot_dimensions && (
              <>
                {lot_dimensions.area !== undefined && (
                  <DataRow label="Lot Area:" value={`${lot_dimensions.area}m²`} />
                )}
                {lot_dimensions.frontage !== undefined && (
                  <DataRow label="Frontage:" value={`${lot_dimensions.frontage}m`} />
                )}
                {lot_dimensions.depth !== undefined && (
                  <DataRow label="Depth:" value={`${lot_dimensions.depth}m`} />
                )}
                <DataRow
                  label="Corner Lot:"
                  value={lot_dimensions.is_corner
                    ? `Yes${lot_dimensions.corner_roads?.length ? ` (${lot_dimensions.corner_roads.join(' & ')})` : ''}`
                    : 'No'}
                />
              </>
            )}

            <DataRow
              label="Heritage Status:"
              value={
                heritage_status.heritage_item
                  ? `Heritage Item${heritage_status.item_number ? ` ${heritage_status.item_number}` : ''}${heritage_status.item_name ? `: ${heritage_status.item_name}` : ''}`
                  : heritage_status.in_hca
                  ? `Heritage Conservation Area${heritage_status.hca_name ? `: ${heritage_status.hca_name}` : ''}${heritage_status.hca_code ? ` (${heritage_status.hca_code})` : ''}`
                  : 'Not heritage listed'
              }
            />
          </View>
        </View>

        {/* ---- 2.2 LEP Controls ---- */}
        <View style={{ ...styles.section, marginTop: 8 }}>
          <Text style={styles.sectionTitle}>2.2 Local Environmental Plan (LEP) Controls</Text>
          <View style={styles.dataTable}>
            {lep_controls?.height && (
              <DataRow label="Height of Buildings:" value={lep_controls.height} />
            )}
            {lep_controls?.fsr && (
              <DataRow label="Floor Space Ratio:" value={lep_controls.fsr} />
            )}
            {lep_controls?.acid_sulfate_soils && (
              <DataRow label="Acid Sulfate Soils Class:" value={lep_controls.acid_sulfate_soils} />
            )}
            {lep_controls?.permitted_uses && lep_controls.permitted_uses.length > 0 && (
              <DataRow label="Permitted Uses:" value={lep_controls.permitted_uses.join('; ')} />
            )}
          </View>

          <View style={{ marginTop: 6 }}>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#374151', marginBottom: 3 }}>
              Additional Local Provisions (Clause 6.x):
            </Text>
            <View style={styles.dataTable}>
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellValue}>
                  {additional_local_provisions && additional_local_provisions.length > 0
                    ? additional_local_provisions.join('; ')
                    : 'None applicable'}
                </Text>
              </View>
            </View>
          </View>
        </View>

        {/* ---- 2.3 Environmental Constraints ---- */}
        {environmental_constraints && (
          <View style={{ ...styles.section, marginTop: 8 }}>
            <Text style={styles.sectionTitle}>2.3 Environmental Constraints</Text>
            <View style={styles.dataTable}>
              <DataRow label="Flood Prone Land:" value={environmental_constraints.flood_prone ? 'Yes' : 'No'} />
              <DataRow label="Bushfire Prone Land:" value={environmental_constraints.bushfire_prone ? 'Yes' : 'No'} />
              <DataRow
                label="Acid Sulfate Soils:"
                value={environmental_constraints.acid_sulfate_soils
                  ? `${environmental_constraints.acid_sulfate_soils} — LEP Clause 6.1 applies`
                  : 'No'}
              />
              <DataRow
                label="Aircraft Noise (ANEF):"
                value={environmental_constraints.anef_zone
                  ? `Yes — ANEF ${environmental_constraints.anef_level ?? ''}${environmental_constraints.anef_code ? ` (${environmental_constraints.anef_code})` : ''}`
                  : 'No'}
              />
              <DataRow
                label="Mine Subsidence:"
                value={environmental_constraints.mine_subsidence
                  ? `Yes${environmental_constraints.mine_subsidence_district ? ` — ${environmental_constraints.mine_subsidence_district}` : ''}`
                  : 'No'}
              />
              <DataRow label="Landslide Risk:" value={environmental_constraints.landslide_risk ? 'Yes' : 'No'} />
              <DataRow
                label="Contaminated Land:"
                value={environmental_constraints.contaminated_land
                  ? `Yes — notified site within 500m${environmental_constraints.contaminated_site_name ? `: ${environmental_constraints.contaminated_site_name}` : ''}`
                  : 'No known sites within 500m'}
              />
              <DataRow label="Drinking Water Catchment:" value={environmental_constraints.drinking_water_catchment ? 'Yes' : 'No'} />
              <DataRow label="Terrestrial Biodiversity:" value={environmental_constraints.terrestrial_biodiversity ? 'Yes' : 'No'} />
              <DataRow
                label="Coastal Management:"
                value={environmental_constraints.coastal_management
                  ? `Yes${environmental_constraints.coastal_zones?.length ? ` — ${environmental_constraints.coastal_zones.join(', ')}` : ''}`
                  : 'No'}
              />
            </View>
          </View>
        )}

        {/* ---- 2.4 SEPP Status ---- */}
        <View style={{ ...styles.section, marginTop: 8 }}>
          <Text style={styles.sectionTitle}>2.4 State Environmental Planning Policy (SEPP) Status</Text>
          <View style={styles.dataTable}>
            <DataRow
              label="Housing SEPP 2021:"
              value={housingSeppApplies
                ? `Applies — ${zoneCode} zone eligible for complying development (CDC) pathway`
                : `Does not apply — ${zoneCode} zone not covered by Housing SEPP`}
            />
            <DataRow label="Development Pathway:" value={pathway} />
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}></Text>
              <Text style={{ ...styles.tableCellValue, fontSize: 8, color: '#6b7280', fontStyle: 'italic' }}>{reason}</Text>
            </View>
          </View>
        </View>

        {/* ---- 2.5 Planning Portal Layers ---- */}
        {planning_portal_layers && (
          <View style={{ ...styles.section, marginTop: 8 }}>
            <Text style={styles.sectionTitle}>2.5 NSW Planning Portal Layers</Text>
            <View style={styles.dataTable}>
              {planning_portal_layers.land_zoning_map !== undefined && (
                <DataRow label="Land Zoning Map:" value={String(planning_portal_layers.land_zoning_map)} />
              )}
              {planning_portal_layers.height_map !== undefined && (
                <DataRow
                  label="Height of Buildings:"
                  value={isNumeric(planning_portal_layers.height_map)
                    ? `${planning_portal_layers.height_map}m`
                    : String(planning_portal_layers.height_map)}
                />
              )}
              {planning_portal_layers.fsr_map !== undefined && planning_portal_layers.fsr_map !== null && (
                <DataRow
                  label="Floor Space Ratio:"
                  value={isNumeric(planning_portal_layers.fsr_map)
                    ? `${planning_portal_layers.fsr_map}:1`
                    : String(planning_portal_layers.fsr_map)}
                />
              )}
              {planning_portal_layers.heritage_map !== undefined && (
                <DataRow label="Heritage Map:" value={String(planning_portal_layers.heritage_map)} />
              )}
              {planning_portal_layers.acid_sulfate_soils_map !== undefined && (
                <DataRow label="Acid Sulfate Soils Map:" value={String(planning_portal_layers.acid_sulfate_soils_map)} />
              )}
              {planning_portal_layers.regional_plan_boundary !== undefined && (() => {
                const raw = String(planning_portal_layers.regional_plan_boundary);
                const hasHtml = containsHtml(raw);
                const { text, url } = hasHtml ? parseHtmlLink(raw) : { text: raw, url: undefined };
                return (
                  <View style={styles.contextTableRow}>
                    <Text style={styles.tableCellLabel}>Regional Plan Boundary:</Text>
                    {url ? (
                      <Link src={url} style={{ ...styles.tableCellValue, color: '#0c4a6e', textDecoration: 'underline' }}>
                        {text}
                      </Link>
                    ) : (
                      <Text style={styles.tableCellValue}>{text}</Text>
                    )}
                  </View>
                );
              })()}
              {planning_portal_layers.terrestrial_biodiversity_map !== undefined && (
                <DataRow label="Terrestrial Biodiversity Map:" value={String(planning_portal_layers.terrestrial_biodiversity_map)} />
              )}
              {planning_portal_layers.tree_canopy_2022 !== undefined && (
                <DataRow label="Tree Canopy Cover 2022:" value={`${planning_portal_layers.tree_canopy_2022}%`} />
              )}
            </View>
          </View>
        )}

        {/* ---- Footer ---- */}
        <View style={styles.footer}>
          <Text style={styles.footerLeft}>Draft Statement of Environmental Effects</Text>
          <Text style={styles.footerCenter}>{property.address}</Text>
          <Text style={styles.footerRight}>Page 2</Text>
        </View>
      </Page>

      {/* ================================================================
          PAGE 3 — Approval Pathway + SEPP Controls + LEP Standards
          ================================================================ */}
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
              {/* Header row */}
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
              {/* Header row */}
              <View style={{ flexDirection: 'row', backgroundColor: '#f3f4f6', borderBottom: '1pt solid #e5e7eb' }}>
                <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 1 }}>Clause</Text>
                <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 2 }}>Control</Text>
                <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 2 }}>Requirement</Text>
                <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 2 }}>Proposal</Text>
                <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 1 }}>Status</Text>
              </View>
              {lep_assessable_standards.map((std, i) => (
                <View key={i} style={{ flexDirection: 'row', borderBottom: i < lep_assessable_standards.length - 1 ? '1pt solid #f3f4f6' : undefined }}>
                  <Text style={{ fontSize: 7, color: '#374151', padding: 4, flex: 1 }}>{std.clause}</Text>
                  <Text style={{ fontSize: 7, fontFamily: 'Helvetica-Bold', color: '#374151', padding: 4, flex: 2 }}>{std.control}</Text>
                  <Text style={{ fontSize: 7, color: '#374151', padding: 4, flex: 2 }}>{std.requirement}</Text>
                  <Text style={{ fontSize: 7, color: '#9ca3af', padding: 4, flex: 2, fontStyle: 'italic' }}>{std.proposal ?? '[to be completed]'}</Text>
                  <Text style={{ fontSize: 7, color: std.status === 'pending' ? '#9ca3af' : '#374151', padding: 4, flex: 1, fontStyle: 'italic' }}>
                    {std.status === 'pending' ? 'Pending' : std.status}
                  </Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* ---- Footer ---- */}
        <View style={styles.footer}>
          <Text style={styles.footerLeft}>Draft Statement of Environmental Effects</Text>
          <Text style={styles.footerCenter}>{property.address}</Text>
          <Text style={styles.footerRight}>Page 3</Text>
        </View>
      </Page>

      {/* ================================================================
          PAGE 4+ — DCP Assessment
          ================================================================ */}
      <Page size="A4" style={styles.page}>
        <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 12, paddingBottom: 6, borderBottom: '2pt solid #0f766e' }}>
          6. Development Control Plan Assessment
        </Text>

        {/* ---- Assessment status summary ---- */}
        <View style={{ border: '1pt solid #e5e7eb', marginBottom: 14 }}>
          {/* Header row */}
          <View style={{ backgroundColor: '#f3f4f6', flexDirection: 'row', borderBottom: '1pt solid #e5e7eb', padding: '4 8' }}>
            <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 2 }}>Status</Text>
            <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 1, textAlign: 'right' }}>Provisions</Text>
            <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 3, marginLeft: 8 }}>Notes</Text>
          </View>
          {/* Varies row */}
          <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8', backgroundColor: variesProvisions.length > 0 ? '#fffbeb' : '#ffffff' }}>
            <Text style={{ fontSize: 8, color: '#d97706', fontFamily: 'Helvetica-Bold', flex: 2 }}>Requires attention (Varies)</Text>
            <Text style={{ fontSize: 8, color: '#d97706', flex: 1, textAlign: 'right' }}>{variesProvisions.length}</Text>
            <Text style={{ fontSize: 7, color: '#6b7280', flex: 3, marginLeft: 8 }}>
              {variesProvisions.length > 0
                ? 'Development may not fully comply — justification required. See section 6.1.'
                : 'No provisions marked as Varies — either all assessed as compliant or not yet reviewed.'}
            </Text>
          </View>
          {/* Complies row */}
          <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8' }}>
            <Text style={{ fontSize: 8, color: '#15803d', fontFamily: 'Helvetica-Bold', flex: 2 }}>Complies</Text>
            <Text style={{ fontSize: 8, color: '#15803d', flex: 1, textAlign: 'right' }}>{compliesProvisions.length}</Text>
            <Text style={{ fontSize: 7, color: '#6b7280', flex: 3, marginLeft: 8 }}>
              {compliesProvisions.length > 0
                ? 'Assessed as compliant by the applicant. See section 6.2.'
                : 'No provisions confirmed compliant — assessment may be incomplete.'}
            </Text>
          </View>
          {/* N/A manual row */}
          <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8' }}>
            <Text style={{ fontSize: 8, color: '#6b7280', fontFamily: 'Helvetica-Bold', flex: 2 }}>Not applicable (planner)</Text>
            <Text style={{ fontSize: 8, color: '#6b7280', flex: 1, textAlign: 'right' }}>{naManualProvisions.length}</Text>
            <Text style={{ fontSize: 7, color: '#6b7280', flex: 3, marginLeft: 8 }}>
              {naManualProvisions.length > 0
                ? 'Manually assessed as not applicable to this proposal. See section 6.3.'
                : 'No provisions manually assessed as not applicable.'}
            </Text>
          </View>
          {/* N/A intake row */}
          <View style={{ flexDirection: 'row', borderBottom: '1pt solid #f3f4f6', padding: '3 8', backgroundColor: '#f9fafb' }}>
            <Text style={{ fontSize: 8, color: '#9ca3af', fontFamily: 'Helvetica-Bold', flex: 2 }}>Not applicable (intake triage)</Text>
            <Text style={{ fontSize: 8, color: '#9ca3af', flex: 1, textAlign: 'right' }}>{naIntakeProvisions.length}</Text>
            <Text style={{ fontSize: 7, color: '#9ca3af', flex: 3, marginLeft: 8 }}>
              {naIntakeProvisions.length > 0
                ? 'Auto-excluded: applicability trigger confirmed absent in intake. See section 6.4 and cover page.'
                : intake_answers
                  ? 'Structured intake was completed but no provisions were excluded by the answers provided.'
                  : 'Structured intake was not completed — no automatic exclusions were applied.'}
            </Text>
          </View>
          {/* Unannotated row */}
          <View style={{ flexDirection: 'row', padding: '3 8', backgroundColor: unannotatedCount > 0 ? '#fef3c7' : '#f0fdf4' }}>
            <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', flex: 2, color: unannotatedCount > 0 ? '#92400e' : '#166534' }}>
              {unannotatedCount > 0 ? '⚠ Not yet assessed' : '✓ Fully assessed'}
            </Text>
            <Text style={{ fontSize: 8, flex: 1, textAlign: 'right', color: unannotatedCount > 0 ? '#92400e' : '#166534' }}>{unannotatedCount}</Text>
            <Text style={{ fontSize: 7, flex: 3, marginLeft: 8, color: unannotatedCount > 0 ? '#92400e' : '#166534' }}>
              {unannotatedCount > 0
                ? `${unannotatedCount} of ${totalCount} applicable provisions have not been annotated. This document is incomplete and must not be lodged until all provisions are addressed.`
                : 'All applicable provisions have been assessed.'}
            </Text>
          </View>
        </View>

        {/* ---- 6.1 Provisions Requiring Attention (varies) ---- */}
        {variesGroups.length > 0 ? (
          <View style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#d97706', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #d97706' }}>
              {`6.1 Provisions Requiring Attention — Varies (${variesProvisions.length})`}
            </Text>
            <Text style={{ fontSize: 8, color: '#92400e', marginBottom: 8 }}>
              These provisions have been identified as varying from the DCP standard. Each requires a planning response addressing how the variation is justified or will be resolved.
            </Text>
            {variesGroups.map((group, idx) => (
              <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} />
            ))}
          </View>
        ) : (
          <View style={{ marginBottom: 12, padding: '6 8', backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb' }}>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#6b7280', marginBottom: 2 }}>6.1 Provisions Requiring Attention — Varies (0)</Text>
            <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>No provisions have been marked as Varies.</Text>
          </View>
        )}

        {/* ---- 6.2 Complying Provisions ---- */}
        {compliesGroups.length > 0 ? (
          <View style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#15803d', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #15803d' }}>
              {`6.2 Complying Provisions (${compliesProvisions.length})`}
            </Text>
            {compliesGroups.map((group, idx) => (
              <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} />
            ))}
          </View>
        ) : (
          <View style={{ marginBottom: 12, padding: '6 8', backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb' }}>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#6b7280', marginBottom: 2 }}>6.2 Complying Provisions (0)</Text>
            <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>No provisions have been confirmed as complying.</Text>
          </View>
        )}

        {/* ---- 6.3 Not Applicable — Planner Assessment ---- */}
        {naManualGroups.length > 0 ? (
          <View style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#6b7280', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #9ca3af' }}>
              {`6.3 Not Applicable — Planner Assessment (${naManualProvisions.length})`}
            </Text>
            <Text style={{ fontSize: 8, color: '#6b7280', marginBottom: 6 }}>
              These provisions have been assessed by the applicant as not applicable to the proposed development.
            </Text>
            {naManualGroups.map((group, idx) => (
              <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} />
            ))}
          </View>
        ) : (
          <View style={{ marginBottom: 12, padding: '6 8', backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb' }}>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#6b7280', marginBottom: 2 }}>6.3 Not Applicable — Planner Assessment (0)</Text>
            <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>No provisions were manually assessed as not applicable.</Text>
          </View>
        )}

        {/* ---- 6.4 Not Applicable — Excluded by Intake Triage ---- */}
        {naIntakeGroups.length > 0 ? (
          <View style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#9ca3af', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #d1d5db' }}>
              {`6.4 Not Applicable — Excluded by Intake Triage (${naIntakeProvisions.length})`}
            </Text>
            <Text style={{ fontSize: 7, color: '#9ca3af', marginBottom: 6, fontStyle: 'italic' }}>
              These provisions were automatically excluded because their applicability trigger was confirmed as absent in the structured intake completed by the applicant. The confirmed inputs are recorded in the "PROPOSAL CHARACTERISTICS — CONFIRMED INPUTS" table on the cover page (page 1) of this document. A provision was only excluded when its trigger was factually impossible given the confirmed answers — answering "Unknown" retains the provision for manual assessment.
            </Text>
            {naIntakeGroups.map((group, idx) => (
              <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} />
            ))}
          </View>
        ) : (
          <View style={{ marginBottom: 12, padding: '6 8', backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb' }}>
            <Text style={{ fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#9ca3af', marginBottom: 2 }}>6.4 Not Applicable — Excluded by Intake Triage (0)</Text>
            <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>
              {intake_answers
                ? 'Structured intake was completed. No provisions were automatically excluded by the answers provided — all provisions were retained for manual assessment.'
                : 'Structured intake was not completed for this assessment. No automatic exclusions were applied.'}
            </Text>
          </View>
        )}

        {/* ---- 6.5 Provisions Requiring Further Assessment ---- */}
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
                <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 2 }}>Topic</Text>
                <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 3 }}>Provision (first line)</Text>
                <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', flex: 1, textAlign: 'right' }}>Source</Text>
              </View>
              {unannotatedProvisions.map((p, idx) => {
                const firstLine = (p.provision_text || '').split('\n')[0].substring(0, 120);
                const topic = p.v2_topic ? capitalizeFirst(p.v2_topic.toLowerCase().replace(/_/g, ' ')) : '—';
                const source = p.pdf_printed_page ? `p.${p.pdf_printed_page}` : '';
                return (
                  <View key={p.id} style={{ flexDirection: 'row', borderBottom: idx < unannotatedProvisions.length - 1 ? '1pt solid #f3f4f6' : undefined, padding: '2 8', backgroundColor: idx % 2 === 0 ? '#ffffff' : '#fafafa' }}>
                    <Text style={{ fontSize: 7, color: '#374151', flex: 2 }}>{topic}</Text>
                    <Text style={{ fontSize: 7, color: '#6b7280', flex: 3 }}>{firstLine}{firstLine.length >= 120 ? '…' : ''}</Text>
                    <Text style={{ fontSize: 7, color: '#9ca3af', flex: 1, textAlign: 'right' }}>{source}</Text>
                  </View>
                );
              })}
            </View>
          </View>
        )}

        {/* ---- Footer ---- */}
        <View style={styles.footer}>
          <Text style={styles.footerLeft}>Draft Statement of Environmental Effects</Text>
          <Text style={styles.footerCenter}>{property.address}</Text>
          <Text style={styles.footerRight}>Page 3</Text>
        </View>
      </Page>

      {/* ================================================================
          FINAL PAGE — Report Information + Conclusion placeholder
          ================================================================ */}
      <Page size="A4" style={styles.page}>
        <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 12, paddingBottom: 6, borderBottom: '2pt solid #0f766e' }}>
          7. Conclusion
        </Text>

        <View style={{ backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb', padding: 12, marginBottom: 16 }}>
          <Text style={{ fontSize: 9, color: '#6b7280', fontStyle: 'italic' }}>
            [Conclusion — to be completed by planning consultant]
          </Text>
          <Text style={{ fontSize: 9, color: '#6b7280', fontStyle: 'italic', marginTop: 6 }}>
            [Summarise compliance outcome, any variations sought, planning merit justification, and recommendation for consent.]
          </Text>
        </View>

        {/* Report metadata */}
        <View style={{ ...styles.section, marginTop: 8 }}>
          <Text style={styles.sectionTitle}>Report Information</Text>
          <View style={styles.dataTable}>
            <DataRow label="Generated:" value={generated_date} />
            <DataRow label="Property:" value={property.address} />
            <DataRow label="Total applicable provisions:" value={`${totalCount}`} />
            <DataRow label="Annotated (Varies + Complies + N/A):" value={`${annotatedCount}`} />
            <DataRow label="  — Requires attention (Varies):" value={`${variesProvisions.length}`} />
            <DataRow label="  — Complies:" value={`${compliesProvisions.length}`} />
            <DataRow label="  — Not applicable (planner):" value={`${naManualProvisions.length}`} />
            <DataRow label="  — Not applicable (intake triage):" value={`${naIntakeProvisions.length}`} />
            <DataRow label="Not yet assessed:" value={unannotatedCount > 0 ? `${unannotatedCount} — INCOMPLETE` : '0 — fully assessed'} />
            <DataRow label="Structured intake:" value={intake_answers ? 'Completed' : 'Not completed — no automatic exclusions applied'} />
            <DataRow label="Development description:" value={development_description || '[Not provided]'} />
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
          <Text style={styles.footerLeft}>Draft Statement of Environmental Effects</Text>
          <Text style={styles.footerCenter}>{property.address}</Text>
          <Text style={styles.footerRight}>Generated {generated_date}</Text>
        </View>
      </Page>
    </Document>
  );
}
