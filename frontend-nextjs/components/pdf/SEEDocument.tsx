// SEE PDF Document — deterministic scaffold, 100% data-driven
// No AI, no hardcoded LGA names, no hardcoded zone lists beyond domain logic

import { Document, Page, Text, View, Link } from '@react-pdf/renderer';
import { SEEDocumentData } from '@/lib/see/types';
import { ProvisionForPDF } from '@/lib/pdf/types';
import { ProvisionTable } from './ProvisionTable';
import { styles } from './styles';
import { groupProvisionsByTopic } from '@/lib/pdf/formatProvisions';

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

/** Extract URL and display text from an HTML anchor string, e.g. <a href="...">Label</a> */
function parseHtmlLink(value: string): { text: string; url?: string } {
  const urlMatch = value.match(/href="([^"]+)"/);
  const textMatch = value.match(/>([^<]+)</);
  const text = textMatch?.[1]?.trim() || value.replace(/<[^>]*>/g, '').trim() || value;
  return { text, url: urlMatch?.[1] };
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
  const { property, development_description, annotated_provisions, all_provisions, generated_date } = data;
  const { heritage_status, lot_dimensions, lep_controls, environmental_constraints,
          additional_local_provisions, planning_portal_layers } = property;

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
  const naProvisions = annotated_provisions.filter(p => p.da_status === 'not_applicable');

  const variesGroups = groupProvisionsByTopic(variesProvisions);
  const compliesGroups = groupProvisionsByTopic(compliesProvisions);
  const naGroups = groupProvisionsByTopic(naProvisions);

  const annotatedCount = annotated_provisions.length;
  const totalCount = all_provisions.length;

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
          <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 4 }}>PROPERTY</Text>
          <Text style={{ fontSize: 11, color: '#1f2937', marginBottom: 6 }}>{property.address}</Text>
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

          {development_description ? (
            <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5, marginBottom: 8 }}>
              {`This Statement of Environmental Effects has been prepared in support of a Development Application for ${development_description} at ${property.address}. The proposed development is subject to assessment under the Environmental Planning and Assessment Act 1979 (NSW).`}
            </Text>
          ) : (
            <Text style={{ fontSize: 9, color: '#6b7280', fontStyle: 'italic', marginBottom: 8 }}>
              [Development description not provided — complete before lodgement]
            </Text>
          )}

          <Text style={{ fontSize: 9, color: '#1f2937', lineHeight: 1.5 }}>
            {`This document provides a schedule of the Development Control Plan (DCP) provisions applicable to the subject site and records the applicant's assessment of compliance with each provision. This document must be reviewed, completed, and verified by a qualified planning consultant before submission with any Development Application.`}
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

        {/* ---- Footer ---- */}
        <View style={styles.footer}>
          <Text style={styles.footerLeft}>PlotDetect — Draft SEE Scaffold</Text>
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
                const hasHtml = raw.includes('<');
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
          <Text style={styles.footerLeft}>PlotDetect — Draft SEE Scaffold</Text>
          <Text style={styles.footerCenter}>{property.address}</Text>
          <Text style={styles.footerRight}>Page 2</Text>
        </View>
      </Page>

      {/* ================================================================
          PAGE 3+ — DCP Assessment
          ================================================================ */}
      <Page size="A4" style={styles.page}>
        <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 12, paddingBottom: 6, borderBottom: '2pt solid #0f766e' }}>
          3. Development Control Plan Assessment
        </Text>

        <Text style={{ fontSize: 9, color: '#4b5563', marginBottom: 12, lineHeight: 1.4 }}>
          {`The following sections record the applicant's assessment of compliance with the applicable DCP provisions. ${annotatedCount} of ${totalCount} provisions have been annotated. Only annotated provisions are included in this assessment schedule.`}
        </Text>

        {/* ---- 3.1 Provisions Requiring Attention (varies) ---- */}
        {variesGroups.length > 0 && (
          <View style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#d97706', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #d97706' }}>
              {`3.1 Provisions Requiring Attention (${variesProvisions.length})`}
            </Text>
            <Text style={{ fontSize: 8, color: '#6b7280', marginBottom: 8, fontStyle: 'italic' }}>
              These provisions have been marked as "varies" — the proposed development may not fully comply or requires further justification.
            </Text>
            {variesGroups.map((group, idx) => (
              <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} />
            ))}
          </View>
        )}

        {/* ---- 3.2 Complying Provisions ---- */}
        {compliesGroups.length > 0 && (
          <View style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#15803d', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #15803d' }}>
              {`3.2 Complying Provisions (${compliesProvisions.length})`}
            </Text>
            {compliesGroups.map((group, idx) => (
              <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} />
            ))}
          </View>
        )}

        {/* ---- 3.3 Not Applicable Provisions ---- */}
        {naGroups.length > 0 && (
          <View style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#6b7280', marginBottom: 4, paddingBottom: 3, borderBottom: '1pt solid #9ca3af' }}>
              {`3.3 Not Applicable Provisions (${naProvisions.length})`}
            </Text>
            {naGroups.map((group, idx) => (
              <ProvisionTable key={group.topic} group={group} sectionNumber={idx + 1} isFirst={idx === 0} />
            ))}
          </View>
        )}

        {annotatedCount === 0 && (
          <View style={{ backgroundColor: '#fef3c7', padding: 12, borderLeft: '3pt solid #f59e0b' }}>
            <Text style={{ fontSize: 9, color: '#92400e' }}>
              No provisions have been annotated. Use DA Mode in PlotDetect to annotate provisions before exporting the SEE.
            </Text>
          </View>
        )}

        {/* ---- Footer ---- */}
        <View style={styles.footer}>
          <Text style={styles.footerLeft}>PlotDetect — Draft SEE Scaffold</Text>
          <Text style={styles.footerCenter}>{property.address}</Text>
          <Text style={styles.footerRight}>Page 3</Text>
        </View>
      </Page>

      {/* ================================================================
          FINAL PAGE — Report Information + Conclusion placeholder
          ================================================================ */}
      <Page size="A4" style={styles.page}>
        <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 12, paddingBottom: 6, borderBottom: '2pt solid #0f766e' }}>
          4. Conclusion
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
            <DataRow label="Provisions annotated:" value={`${annotatedCount} of ${totalCount} total`} />
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
          <Text style={styles.footerLeft}>PlotDetect — Draft SEE Scaffold</Text>
          <Text style={styles.footerCenter}>{property.address}</Text>
          <Text style={styles.footerRight}>Generated {generated_date}</Text>
        </View>
      </Page>
    </Document>
  );
}
