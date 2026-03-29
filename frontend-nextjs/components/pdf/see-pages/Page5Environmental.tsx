import { Page, View, Text } from '@react-pdf/renderer';
import { styles } from '../styles';
import { SEEComputedData } from '@/lib/see/section-aggregation';

export function Page5Environmental({ computed }: { computed: SEEComputedData }) {
  const { property, environmental_constraints, planning_portal_layers, heritage_status, footerRef } = computed;

  return (
    <Page size="A4" style={styles.page}>
      <Text style={{ fontSize: 14, fontFamily: 'Helvetica-Bold', color: '#0f766e', marginBottom: 6, paddingBottom: 6, borderBottom: '2pt solid #0f766e' }}>
        7. Environmental Impact Assessment
      </Text>
      <Text style={{ fontSize: 8, color: '#6b7280', marginBottom: 12, fontStyle: 'italic' }}>
        Required under EP&A Act 1979 s4.15(1)(b) — likely impacts of the development on the natural and built environments, and social/economic impacts.
      </Text>

      {/* 7.1 Natural Environment */}
      <View style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#1f2937', marginBottom: 6, paddingBottom: 3, borderBottom: '1pt solid #e5e7eb' }}>
          7.1 Natural Environment
        </Text>
        {(environmental_constraints?.flood_prone ||
          environmental_constraints?.terrestrial_biodiversity ||
          environmental_constraints?.contaminated_land ||
          environmental_constraints?.bushfire_prone ||
          environmental_constraints?.drinking_water_catchment ||
          planning_portal_layers?.tree_canopy_coverage_class) && (
          <View style={{ marginBottom: 6, padding: 8, backgroundColor: '#fefce8', border: '1pt solid #fef08a', borderRadius: 2 }}>
            <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#713f12', marginBottom: 4 }}>Constraint flags — address in assessment below:</Text>
            {environmental_constraints?.flood_prone && (
              <Text style={{ fontSize: 8, color: '#78350f' }}>• Flood prone land — stormwater management and flood impact must be addressed</Text>
            )}
            {environmental_constraints?.bushfire_prone && (
              <Text style={{ fontSize: 8, color: '#78350f' }}>• Bushfire prone land — compliance with Planning for Bushfire Protection 2019 required</Text>
            )}
            {environmental_constraints?.contaminated_land && (
              <Text style={{ fontSize: 8, color: '#78350f' }}>• Contaminated land in vicinity — site contamination assessment may be required</Text>
            )}
            {environmental_constraints?.terrestrial_biodiversity && (
              <Text style={{ fontSize: 8, color: '#78350f' }}>• Terrestrial biodiversity map — biodiversity values assessment may be required</Text>
            )}
            {environmental_constraints?.drinking_water_catchment && (
              <Text style={{ fontSize: 8, color: '#78350f' }}>• Drinking water catchment — development must not adversely impact water quality</Text>
            )}
            {planning_portal_layers?.tree_canopy_coverage_class && (
              <Text style={{ fontSize: 8, color: '#78350f' }}>• Tree canopy: {planning_portal_layers.tree_canopy_coverage_class} — tree impacts must be assessed by a qualified arborist</Text>
            )}
          </View>
        )}
        <View style={{ padding: 10, backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb', borderRadius: 2, minHeight: 60 }}>
          <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>
            [Consultant to address: stormwater runoff and drainage impacts; tree removal/retention and canopy impacts (arborist report if required); biodiversity impacts; soil and water quality; flood risk management; any remediation requirements for contaminated land.]
          </Text>
        </View>
      </View>

      {/* 7.2 Built Environment */}
      <View style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#1f2937', marginBottom: 6, paddingBottom: 3, borderBottom: '1pt solid #e5e7eb' }}>
          7.2 Built Environment
        </Text>
        {(heritage_status.in_hca || heritage_status.heritage_item) && (
          <View style={{ marginBottom: 6, padding: 8, backgroundColor: '#fefce8', border: '1pt solid #fef08a', borderRadius: 2 }}>
            <Text style={{ fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#713f12', marginBottom: 2 }}>Heritage context:</Text>
            {heritage_status.heritage_item && (
              <Text style={{ fontSize: 8, color: '#78350f' }}>• Listed heritage item — built form impacts on heritage significance must be addressed</Text>
            )}
            {heritage_status.in_hca && !heritage_status.heritage_item && (
              <Text style={{ fontSize: 8, color: '#78350f' }}>• Heritage conservation area ({heritage_status.hca_name || 'HCA'}) — consistency with character and streetscape must be demonstrated</Text>
            )}
          </View>
        )}
        <View style={{ padding: 10, backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb', borderRadius: 2, minHeight: 60 }}>
          <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>
            [Consultant to address: bulk, scale and massing relative to adjoining development; solar access and overshadowing impacts on neighbours; visual privacy (overlooking); streetscape character and context; impacts on heritage significance (if applicable); views and view sharing.]
          </Text>
        </View>
      </View>

      {/* 7.3 Social and Economic Impacts */}
      <View style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#1f2937', marginBottom: 6, paddingBottom: 3, borderBottom: '1pt solid #e5e7eb' }}>
          7.3 Social and Economic Impacts
        </Text>
        <View style={{ padding: 10, backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb', borderRadius: 2, minHeight: 40 }}>
          <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>
            [Consultant to address: contribution to housing supply; employment impacts (if applicable); amenity impacts on adjoining properties; traffic and parking impacts; any displacement of existing uses.]
          </Text>
        </View>
      </View>

      {/* 7.4 Site Suitability */}
      <View style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, fontFamily: 'Helvetica-Bold', color: '#1f2937', marginBottom: 6, paddingBottom: 3, borderBottom: '1pt solid #e5e7eb' }}>
          7.4 Site Suitability
        </Text>
        <View style={{ padding: 10, backgroundColor: '#f9fafb', border: '1pt solid #e5e7eb', borderRadius: 2, minHeight: 40 }}>
          <Text style={{ fontSize: 8, color: '#9ca3af', fontStyle: 'italic' }}>
            [Consultant to address: suitability of the site for the proposed development given its zoning ({property.zone}), physical characteristics, and constraints identified above. Confirm the site can accommodate the proposed development without unacceptable impacts.]
          </Text>
        </View>
      </View>

      {/* ---- Footer ---- */}
      <View style={styles.footer}>
        <Text style={styles.footerLeft}>{footerRef}</Text>
        <Text style={styles.footerCenter}>{property.address}</Text>
        <Text style={styles.footerRight}>Environmental Impact Assessment</Text>
      </View>
    </Page>
  );
}
