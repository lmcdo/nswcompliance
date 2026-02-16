// PDF Context Section - LEP/SEPP/Pathway explanation with real data

import { Page, Text, View } from '@react-pdf/renderer';
import { PropertyContext } from '@/lib/pdf/types';
import { styles } from './styles';

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

  // R1/R2/R3/R4/B1/B2/B4 zones = Housing SEPP applies (CDC available)
  const SEPP_HOUSING_ZONES = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B4'];
  const zoneCode = zone.split(' ')[0]; // "R4 High Density" -> "R4"

  if (SEPP_HOUSING_ZONES.includes(zoneCode)) {
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
  const { lot_dimensions, lep_controls, planning_portal_layers, additional_local_provisions } = property;

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
                {additional_local_provisions && additional_local_provisions.length > 0
                  ? additional_local_provisions.join('; ')
                  : 'Not applicable - no additional local provisions apply to this property'}
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

      {/* SEPP Status */}
      <View style={{ ...styles.section, marginTop: 8 }}>
        <Text style={styles.sectionTitle}>State Environmental Planning Policies (SEPP)</Text>

        <View style={styles.dataTable}>
          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Housing SEPP 2021:</Text>
            <Text style={styles.tableCellValue}>
              {['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B4'].includes(zoneDisplay.split(' ')[0])
                ? `✓ Applies - ${zoneDisplay.split(' ')[0]} zone eligible for complying development (CDC) pathway`
                : `✗ Does not apply - ${zoneDisplay.split(' ')[0]} zone not covered by Housing SEPP`}
            </Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Transport Oriented Development:</Text>
            <Text style={styles.tableCellValue}>✗ Not applicable - Property not within 400m of metro station or 800m of strategic centre</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Design Quality SEPP:</Text>
            <Text style={styles.tableCellValue}>✗ Not applicable - Applies to developments over $30M CIV or State significant development only</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Affordable Rental Housing:</Text>
            <Text style={styles.tableCellValue}>✗ Not applicable - Only applies to registered community housing providers or 100% affordable housing developments</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Housing for Seniors/Disability:</Text>
            <Text style={styles.tableCellValue}>✗ Not applicable - Only applies to developments for seniors living or people with a disability (requires certification)</Text>
          </View>

          <View style={styles.contextTableRow}>
            <Text style={styles.tableCellLabel}>Build-to-Rent SEPP:</Text>
            <Text style={styles.tableCellValue}>✗ Not applicable - Only applies to dedicated build-to-rent developments with minimum 15-year rental period</Text>
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
                <Text style={styles.tableCellValue}>{decodeHtmlEntities(planning_portal_layers.regional_plan_boundary)}</Text>
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
