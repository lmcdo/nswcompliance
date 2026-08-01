import { Page, View, Text, Link } from '@react-pdf/renderer';
import { styles } from '../styles';
import { DataRow } from '../DataRow';
import { capitalizeFirst, isNumeric } from '@/lib/pdf/see-helpers';
import { containsHtml, parseHtmlLink } from '@/lib/pdf/htmlUtils';
import { SEEComputedData } from '@/lib/see/section-aggregation';

export function Page2SiteContext({ computed }: { computed: SEEComputedData }) {
  const {
    property, heritage_status, lot_dimensions, lep_controls,
    environmental_constraints, additional_local_provisions, planning_portal_layers,
    zoneCode, pathway, reason, housingSeppApplies,
    siteSuitabilityText, footerRef,
  } = computed;

  return (
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
                {additional_local_provisions === undefined
                  ? 'Not assessed - local provision data unavailable'
                  : additional_local_provisions.length > 0
                    ? additional_local_provisions.join('; ')
                    : 'None apply to this property'}
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
            <DataRow
              label="Landslide Risk:"
              value={environmental_constraints.landslide_risk
                ? `Yes${environmental_constraints.landslide_risk_class ? ` — ${environmental_constraints.landslide_risk_class}` : ''}`
                : 'No'}
            />
            <DataRow
              label="Contaminated Land:"
              value={environmental_constraints.contaminated_land
                ? `Yes — notified site within 500m${environmental_constraints.contaminated_site_name ? `: ${environmental_constraints.contaminated_site_name}` : ''}${environmental_constraints.contaminated_management_class ? ` (${environmental_constraints.contaminated_management_class})` : ''}${environmental_constraints.contaminated_type ? ` — ${environmental_constraints.contaminated_type}` : ''}`
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
              <DataRow
                label="Tree Canopy Cover 2022:"
                value={`${planning_portal_layers.tree_canopy_2022}%${planning_portal_layers.tree_canopy_coverage_class ? ` (${planning_portal_layers.tree_canopy_coverage_class})` : ''}`}
              />
            )}
          </View>
        </View>
      )}

      {/* ---- 2.6 Site Suitability Assessment ---- */}
      <View style={{ ...styles.section, marginTop: 8 }}>
        <Text style={styles.sectionTitle}>2.6 Site Suitability Assessment (EP&A Act s 4.15(1)(c))</Text>
        <View style={styles.dataTable}>
          {lot_dimensions?.area && (
            <DataRow label="Lot Area:" value={`${Math.round(lot_dimensions.area).toLocaleString()} m²`} />
          )}
          {lot_dimensions?.frontage && (
            <DataRow label="Lot Frontage:" value={`${lot_dimensions.frontage.toFixed(1)} m`} />
          )}
          {lot_dimensions?.depth && (
            <DataRow label="Lot Depth:" value={`${lot_dimensions.depth.toFixed(1)} m`} />
          )}
          {lot_dimensions?.is_corner !== undefined && (
            <DataRow
              label="Corner Lot:"
              value={lot_dimensions.is_corner
                ? `Yes${lot_dimensions.corner_roads?.length ? ` (${lot_dimensions.corner_roads.join(' / ')})` : ''}`
                : 'No'}
            />
          )}
          {environmental_constraints && (
            <>
              <DataRow label="Flood Prone:" value={environmental_constraints.flood_prone ? 'Yes — refer Section 2.3' : 'No'} />
              <DataRow label="Bushfire Prone:" value={environmental_constraints.bushfire_prone ? 'Yes — refer Section 2.3' : 'No'} />
              {environmental_constraints.coastal_management && (
                <DataRow
                  label="Coastal Management:"
                  value={`Yes${environmental_constraints.coastal_zones?.length ? ` — ${environmental_constraints.coastal_zones.join(', ')}` : ''}`}
                />
              )}
            </>
          )}
        </View>
        <View style={{ marginTop: 5, padding: 6, border: '1pt solid #e5e7eb', backgroundColor: '#f9fafb' }}>
          <Text style={{ fontSize: 9, color: '#374151', lineHeight: 1.5, marginBottom: 4 }}>
            {siteSuitabilityText}
          </Text>
          <Text style={{ fontSize: 9, color: '#6b7280', fontStyle: 'italic' }}>
            [Consultant to confirm the above summary is accurate and add any site-specific observations relevant to the suitability of the site for the proposed development.]
          </Text>
        </View>
      </View>

      {/* ---- Footer ---- */}
      <View style={styles.footer}>
        <Text style={styles.footerLeft}>{footerRef}</Text>
        <Text style={styles.footerCenter}>{property.address}</Text>
        <Text style={styles.footerRight}>Page 2</Text>
      </View>
    </Page>
  );
}
