// PDF Context Section - LEP/SEPP/Pathway explanation with real data

import { Page, Text, View } from '@react-pdf/renderer';
import { PropertyContext } from '@/lib/pdf/types';
import { styles } from './styles';
import { HOUSING_SEPP_ZONES } from '@/lib/regulatory-constants';

interface ContextSectionProps {
  property: PropertyContext;
  exportedCount: number;
  totalCount: number;
  activeFilters?: string[];
  isEmbedded?: boolean;
}

/**
 * Decode HTML entities in text
 */
function decodeHtmlEntities(text: string | undefined): string | undefined {
  if (!text) return text;
  return text
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/<[^>]*>/g, ''); // Strip any HTML tags
}

/**
 * Determines development pathway based on property constraints
 */
function determineDevelopmentPathway(property: PropertyContext): {
  pathway: 'Exempt' | 'Complying (CDC)' | 'Development Application (DA)';
  reason: string;
} {
  const { heritage_status } = property;
  const { zone } = property;

  // Heritage = always DA (can't use CDC or exempt)
  if (heritage_status.in_hca || heritage_status.heritage_item) {
    return {
      pathway: 'Development Application (DA)',
      reason: heritage_status.heritage_item
        ? 'Heritage item - CDC and exempt development not permitted'
        : 'Heritage conservation area - CDC and exempt development restricted'
    };
  }

  const zoneCode = zone.split(' ')[0]; // "R4 High Density" -> "R4"

  if (HOUSING_SEPP_ZONES.includes(zoneCode)) {
    return {
      pathway: 'Complying (CDC)',
      reason: `${zoneCode} zone - Housing SEPP 2021 CDC pathway available for eligible development`
    };
  }

  // Default to exempt for other zones
  return {
    pathway: 'Exempt',
    reason: `${zoneCode} zone - Check exempt development criteria`
  };
}

export function ContextSection({
  property,
  exportedCount,
  totalCount,
  activeFilters = [],
  isEmbedded = false
}: ContextSectionProps) {
  const { pathway, reason } = determineDevelopmentPathway(property);

  const zoneDisplay = property.zone || 'Unknown';

  /**
   * Housing SEPP status, gated the SAME way as determineDevelopmentPathway().
   *
   * This line used to test the zone alone, while the function above correctly
   * checked heritage first. On a heritage-listed property the one PDF therefore
   * said both "Development Pathway: Development Application (DA) — CDC and exempt
   * development not permitted" AND "Housing SEPP 2021: ✓ Applies — eligible for
   * complying development (CDC) pathway". Two contradictory answers to the same
   * question, in the same table, one of them definitive and wrong.
   *
   * Zone membership is necessary but not sufficient, so a zone match is now
   * reported as what it is — the zone test passing — not as an eligibility
   * verdict on a proposal this report has never seen.
   */
  const zoneCode = zoneDisplay.split(' ')[0];
  const isHeritage = Boolean(
    property.heritage_status?.in_hca || property.heritage_status?.heritage_item
  );
  // An absent zone must not become a verdict. `zoneDisplay` falls back to
  // 'Unknown', which is not in HOUSING_SEPP_ZONES, so without this the PDF would
  // print "Does not apply - Unknown zone not covered by Housing SEPP" — a
  // definitive negative derived from missing data, the same defect as the
  // hardcoded TOD line below.
  const hasZone = Boolean(property.zone && property.zone.trim());
  const housingSeppStatus = !hasZone
    ? 'Not assessed - zoning data unavailable for this property'
    : !HOUSING_SEPP_ZONES.includes(zoneCode)
    ? `✗ Does not apply - ${zoneCode} zone not covered by Housing SEPP`
    : isHeritage
      ? `Zone test met (${zoneCode}), but the CDC pathway is not available on `
        + `heritage-listed land - see Development Pathway below`
      : `Zone test met (${zoneCode}) - CDC pathway may be available depending on `
        + `the proposal, lot and site constraints`;
  const { lot_dimensions, lep_controls, planning_portal_layers, additional_local_provisions, environmental_constraints } = property;

  return (
    <View>
      {/* Property Details */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Property Details</Text>

        <View style={styles.dataTable}>
          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Address:</Text>
            <Text style={styles.tableCellValue}>{property.address}</Text>
          </View>
          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Former Council:</Text>
            <Text style={styles.tableCellValue}>{property.former_council}</Text>
          </View>
          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Zone:</Text>
            <Text style={styles.tableCellValue}>{zoneDisplay}</Text>
          </View>

          {/* Lot Dimensions */}
          {lot_dimensions && (
            <>
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Lot Area:</Text>
                <Text style={styles.tableCellValue}>{lot_dimensions.area}m²</Text>
              </View>
              {lot_dimensions.frontage && (
                <View style={styles.contextTableRow}>
                  <Text style={styles.tableCellLabel}>Frontage:</Text>
                  <Text style={styles.tableCellValue}>{lot_dimensions.frontage}m</Text>
                </View>
              )}
              {lot_dimensions.depth && (
                <View style={styles.contextTableRow}>
                  <Text style={styles.tableCellLabel}>Depth:</Text>
                  <Text style={styles.tableCellValue}>{lot_dimensions.depth}m</Text>
                </View>
              )}
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Corner Lot:</Text>
                <Text style={styles.tableCellValue}>
                  {lot_dimensions.is_corner
                    ? `Yes (${lot_dimensions.corner_roads?.join(' & ') || '2 roads'})`
                    : 'No'}
                </Text>
              </View>
            </>
          )}
        </View>
      </View>

      {/* LEP Controls */}
      <View style={{ ...styles.section, marginTop: 8 }}>
        <Text style={styles.sectionTitle}>Local Environmental Plan (LEP)</Text>

        <View style={styles.dataTable}>
          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Heritage:</Text>
            <Text style={styles.tableCellValue}>
              {property.heritage_status.heritage_item
                ? `Item ${property.heritage_status.item_number}: ${property.heritage_status.item_name}`
                : property.heritage_status.in_hca
                ? `${property.heritage_status.hca_name} (${property.heritage_status.hca_code})`
                : 'Not heritage listed'}
            </Text>
          </View>

          {lep_controls?.height && (
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Height Limit:</Text>
              <Text style={styles.tableCellValue}>{lep_controls.height}</Text>
            </View>
          )}

          {lep_controls?.fsr && (
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Floor Space Ratio:</Text>
              <Text style={styles.tableCellValue}>{lep_controls.fsr}</Text>
            </View>
          )}

          {lep_controls?.acid_sulfate_soils && (
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Acid Sulfate Soils:</Text>
              <Text style={styles.tableCellValue}>{lep_controls.acid_sulfate_soils}</Text>
            </View>
          )}

          {/* Permitted Uses */}
          {lep_controls?.permitted_uses && lep_controls.permitted_uses.length > 0 && (
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Permitted Uses:</Text>
              <Text style={styles.tableCellValue}>{lep_controls.permitted_uses.join('; ')}</Text>
            </View>
          )}

          {/* Prohibited Uses */}
          {lep_controls?.prohibited_uses && lep_controls.prohibited_uses.length > 0 && (
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Prohibited Uses:</Text>
              <Text style={styles.tableCellValue}>{lep_controls.prohibited_uses.join('; ')}</Text>
            </View>
          )}
        </View>

        {/* Additional Local Provisions */}
        <View style={{ marginTop: 6 }}>
          <Text style={{ fontSize: 10, fontWeight: 'bold', color: '#374151', marginBottom: 3 }}>
            Additional Local Provisions (Clause 6.x):
          </Text>
          <View style={styles.dataTable}>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellValue}>
                {additional_local_provisions === undefined
                  ? 'Not assessed - local provision data unavailable for this property'
                  : additional_local_provisions.length > 0
                    ? additional_local_provisions.join('; ')
                    : 'None apply to this property'}
              </Text>
            </View>
          </View>
        </View>

        {/* HCA Details */}
        {property.hca_details && (
          <View style={{ marginTop: 8 }}>
            <Text style={{ fontSize: 9, fontWeight: 'bold', color: '#374151', marginBottom: 4 }}>
              Heritage Conservation Area Details:
            </Text>
            <View style={styles.dataTable}>
              {property.hca_details.significance && (
                <View style={styles.contextTableRow}>
                  <Text style={styles.tableCellLabel}>Significance:</Text>
                  <Text style={styles.tableCellValue}>{property.hca_details.significance}</Text>
                </View>
              )}
              {property.hca_details.key_attributes && property.hca_details.key_attributes.length > 0 && (
                <View style={styles.contextTableRow}>
                  <Text style={styles.tableCellLabel}>Key Attributes:</Text>
                  <Text style={styles.tableCellValue}>{property.hca_details.key_attributes.join('; ')}</Text>
                </View>
              )}
              {property.hca_details.controls && property.hca_details.controls.length > 0 && (
                <View style={styles.contextTableRow}>
                  <Text style={styles.tableCellLabel}>HCA Controls:</Text>
                  <Text style={styles.tableCellValue}>{property.hca_details.controls.join('; ')}</Text>
                </View>
              )}
            </View>
          </View>
        )}
      </View>

      {/* Environmental Constraints */}
      {environmental_constraints && (
        <View style={{ ...styles.section, marginTop: 8 }}>
          <Text style={styles.sectionTitle}>Environmental Constraints</Text>

          <View style={styles.dataTable}>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Flood Prone Land:</Text>
              <Text style={styles.tableCellValue}>{environmental_constraints.flood_prone ? 'Yes' : 'No'}</Text>
            </View>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Bushfire Prone Land:</Text>
              <Text style={styles.tableCellValue}>{environmental_constraints.bushfire_prone ? 'Yes' : 'No'}</Text>
            </View>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Acid Sulfate Soils:</Text>
              <Text style={styles.tableCellValue}>
                {environmental_constraints.acid_sulfate_soils
                  ? `${environmental_constraints.acid_sulfate_soils} — LEP Clause 6.1: acid sulfate soils management plan may be required`
                  : 'No'}
              </Text>
            </View>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Aircraft Noise (ANEF):</Text>
              <Text style={styles.tableCellValue}>
                {environmental_constraints.anef_zone
                  ? `Yes — ANEF ${environmental_constraints.anef_level ?? ''}${environmental_constraints.anef_code ? ` (${environmental_constraints.anef_code})` : ''}`
                  : 'No'}
              </Text>
            </View>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Mine Subsidence:</Text>
              <Text style={styles.tableCellValue}>
                {environmental_constraints.mine_subsidence
                  ? `Yes${environmental_constraints.mine_subsidence_district ? ` — ${environmental_constraints.mine_subsidence_district}` : ''}`
                  : 'No'}
              </Text>
            </View>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Landslide Risk:</Text>
              <Text style={styles.tableCellValue}>{environmental_constraints.landslide_risk ? 'Yes' : 'No'}</Text>
            </View>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Contaminated Land:</Text>
              <Text style={styles.tableCellValue}>
                {environmental_constraints.contaminated_land
                  ? `Yes — Notified site within 500m${environmental_constraints.contaminated_site_name ? `: ${environmental_constraints.contaminated_site_name}` : ''}`
                  : 'No known sites within 500m'}
              </Text>
            </View>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Drinking Water Catchment:</Text>
              <Text style={styles.tableCellValue}>{environmental_constraints.drinking_water_catchment ? 'Yes' : 'No'}</Text>
            </View>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Terrestrial Biodiversity:</Text>
              <Text style={styles.tableCellValue}>{environmental_constraints.terrestrial_biodiversity ? 'Yes' : 'No'}</Text>
            </View>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Coastal Management:</Text>
              <Text style={styles.tableCellValue}>
                {environmental_constraints.coastal_management
                  ? `Yes${environmental_constraints.coastal_zones?.length ? ` — ${environmental_constraints.coastal_zones.join(', ')}` : ''}`
                  : 'No'}
              </Text>
            </View>
          </View>
        </View>
      )}

      {/* SEPP Status */}
      <View style={{ ...styles.section, marginTop: 8 }}>
        <Text style={styles.sectionTitle}>State Environmental Planning Policies (SEPP)</Text>

        <View style={styles.dataTable}>
          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Housing SEPP 2021:</Text>
            <Text style={styles.tableCellValue}>{housingSeppStatus}</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Transport Oriented Development:</Text>
            {/* Was hardcoded to "✗ Not applicable - Property not within 400m of a
                metro station or 800m of a strategic centre". That is a claim about
                THIS SITE, and this component is passed no TOD/LMR catchment data at
                all — so for any property that IS in a catchment the PDF stated a
                falsehood, with no code path that could ever say otherwise. Not
                assessed is the truth; asserting a negative was not. */}
            <Text style={styles.tableCellValue}>Not assessed in this report - TOD and low/mid-rise catchments are proximity-based; confirm against the NSW Planning Portal TOD maps</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Design Quality SEPP:</Text>
            <Text style={styles.tableCellValue}>Depends on the proposal - Applies to development over $30M CIV or State significant development</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Affordable Rental Housing:</Text>
            <Text style={styles.tableCellValue}>Depends on the proposal - Applies to registered community housing providers or 100% affordable housing development</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Housing for Seniors/Disability:</Text>
            <Text style={styles.tableCellValue}>Depends on the proposal - Applies to development for seniors living or people with a disability (requires certification)</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Build-to-Rent SEPP:</Text>
            <Text style={styles.tableCellValue}>Depends on the proposal - Applies to dedicated build-to-rent development with a minimum 15-year rental period</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Development Pathway:</Text>
            <Text style={styles.tableCellValue}>{pathway}</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}></Text>
            <Text style={{ ...styles.tableCellValue, fontSize: 7, color: '#6b7280', fontStyle: 'italic' }}>
              {reason}
            </Text>
          </View>
        </View>
      </View>

      {/* Pattern Book CDC Pathway Analysis */}
      {property.pattern_book_cdc && (
        <View style={{ ...styles.section, marginTop: 8 }}>
          <Text style={styles.sectionTitle}>Pattern Book CDC (10-Day Approval Pathway)</Text>

          <View style={styles.dataTable}>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Eligibility Status:</Text>
              <Text style={{
                ...styles.tableCellValue,
                fontFamily: 'Helvetica-Bold',
                color: property.pattern_book_cdc.status === 'ELIGIBLE' ? '#15803d' :
                       property.pattern_book_cdc.status === 'CONDITIONAL' ? '#d97706' : '#dc2626'
              }}>
                {property.pattern_book_cdc.status}
              </Text>
            </View>

            {property.pattern_book_cdc.pathway_timeframe && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Approval Timeframe:</Text>
                <Text style={styles.tableCellValue}>{property.pattern_book_cdc.pathway_timeframe}</Text>
              </View>
            )}

            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Checks Performed:</Text>
              <Text style={styles.tableCellValue}>
                {property.pattern_book_cdc.exclusion_count} exclusion triggers • {property.pattern_book_cdc.numeric_standards_count} numeric standards • {property.pattern_book_cdc.override_rules_count} override rules
              </Text>
            </View>

            {property.pattern_book_cdc.blockers && property.pattern_book_cdc.blockers.length > 0 && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Exclusion Blockers:</Text>
                <Text style={{ ...styles.tableCellValue, color: '#dc2626' }}>
                  {property.pattern_book_cdc.blockers.join(' • ')}
                </Text>
              </View>
            )}
          </View>
        </View>
      )}

      {/* Pathway Comparison */}
      {property.pathway_summary && (
        <View style={{ ...styles.section, marginTop: 8 }}>
          <Text style={styles.sectionTitle}>Development Pathway Comparison</Text>

          <View style={styles.dataTable}>
            <View style={styles.contextTableRow}>
              <Text style={styles.tableCellLabel}>Recommended Pathway:</Text>
              <Text style={{ ...styles.tableCellValue, fontFamily: 'Helvetica-Bold', color: '#0f766e' }}>
                {property.pathway_summary.recommended_pathway}
              </Text>
            </View>

            {property.pathway_summary.pathways.map((pathway, idx) => (
              <View key={idx} style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>{pathway.name}:</Text>
                <Text style={styles.tableCellValue}>
                  {pathway.status === 'Available' ? '✓' : pathway.status === 'Conditional' ? '⚠' : '✗'} {pathway.status} ({pathway.timeframe})
                  {pathway.notes && ` — ${pathway.notes}`}
                </Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* NSW Planning Portal Layers */}
      {planning_portal_layers && (
        <View style={{ ...styles.section, marginTop: 8 }}>
          <Text style={styles.sectionTitle}>NSW Planning Portal Layers</Text>

          <View style={styles.dataTable}>
            {planning_portal_layers.heritage_map !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Heritage Map:</Text>
                <Text style={styles.tableCellValue}>{planning_portal_layers.heritage_map}</Text>
              </View>
            )}

            {planning_portal_layers.fsr_map !== undefined && planning_portal_layers.fsr_map !== null && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Floor Space Ratio (FSR):</Text>
                <Text style={styles.tableCellValue}>{planning_portal_layers.fsr_map}:1</Text>
              </View>
            )}

            {planning_portal_layers.height_map !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Height of Buildings:</Text>
                <Text style={styles.tableCellValue}>{planning_portal_layers.height_map}m</Text>
              </View>
            )}

            {planning_portal_layers.acid_sulfate_soils_map !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Acid Sulfate Soils Map:</Text>
                <Text style={styles.tableCellValue}>{planning_portal_layers.acid_sulfate_soils_map}</Text>
              </View>
            )}

            {planning_portal_layers.local_aboriginal_land_council !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Local Aboriginal Land Council:</Text>
                <Text style={styles.tableCellValue}>{planning_portal_layers.local_aboriginal_land_council}</Text>
              </View>
            )}

            {planning_portal_layers.sepp_requirements !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>SEPP Requirements:</Text>
                <Text style={styles.tableCellValue}>{planning_portal_layers.sepp_requirements}</Text>
              </View>
            )}

            {planning_portal_layers.land_application_map !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Land Application Map:</Text>
                <Text style={styles.tableCellValue}>{planning_portal_layers.land_application_map}</Text>
              </View>
            )}

            {planning_portal_layers.regional_plan_boundary !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Regional Plan Boundary:</Text>
                <Text style={styles.tableCellValue}>{decodeHtmlEntities(String(planning_portal_layers.regional_plan_boundary))}</Text>
              </View>
            )}

            {planning_portal_layers.land_zoning_map !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Land Zoning Map:</Text>
                <Text style={styles.tableCellValue}>{planning_portal_layers.land_zoning_map}</Text>
              </View>
            )}

            {planning_portal_layers.tree_canopy_2019 !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Greater Sydney Tree Canopy Cover 2019:</Text>
                <Text style={styles.tableCellValue}>{planning_portal_layers.tree_canopy_2019}%</Text>
              </View>
            )}

            {planning_portal_layers.tree_canopy_2022 !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Greater Sydney Tree Canopy Cover 2022:</Text>
                <Text style={styles.tableCellValue}>{planning_portal_layers.tree_canopy_2022}%</Text>
              </View>
            )}

            {planning_portal_layers.terrestrial_biodiversity_map !== undefined && (
              <View style={styles.contextTableRow}>
                <Text style={styles.tableCellLabel}>Terrestrial Biodiversity Map:</Text>
                <Text style={styles.tableCellValue}>
                  {planning_portal_layers.terrestrial_biodiversity_map === 'N/A' || planning_portal_layers.terrestrial_biodiversity_map === null
                    ? 'N/A'
                    : planning_portal_layers.terrestrial_biodiversity_map}
                </Text>
              </View>
            )}
          </View>
        </View>
      )}

      {/* DCP Export Summary */}
      <View style={{ ...styles.section, marginTop: 8 }}>
        <Text style={styles.sectionTitle}>DCP Provisions Export</Text>

        <View style={styles.dataTable}>
          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Total provisions:</Text>
            <Text style={styles.tableCellValue}>{totalCount} provisions for this property</Text>
          </View>
          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>This export:</Text>
            <Text style={styles.tableCellValue}>
              {exportedCount} provisions{activeFilters.length > 0 ? ` (${activeFilters.join(', ')})` : ''}
            </Text>
          </View>
        </View>
      </View>
    </View>
  );
}
