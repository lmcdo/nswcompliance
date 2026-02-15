// PDF Cover Page Component

import { Page, Text, View } from '@react-pdf/renderer';
import { PropertyContext, ProvisionGroup, ReportMetadata } from '@/lib/pdf/types';
import { styles } from './styles';

interface CoverPageProps {
  property: PropertyContext;
  groups: ProvisionGroup[];
  metadata: ReportMetadata;
}

export function CoverPage({ property, groups, metadata }: CoverPageProps) {
  return (
    <View style={{ marginBottom: 24, paddingBottom: 16, borderBottom: '2pt solid #0f766e' }}>
      {/* Compact Header */}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <View>
          <Text style={{ fontSize: 20, fontWeight: 'bold', color: '#0f766e', marginBottom: 4 }}>
            PLOTDETECT
          </Text>
          <Text style={{ fontSize: 11, color: '#6b7280' }}>
            Planning Compliance Report • {metadata.reportDate}
          </Text>
        </View>
        <View style={{ textAlign: 'right' }}>
          <Text style={{ fontSize: 8, color: '#6b7280' }}>Report ID</Text>
          <Text style={{ fontSize: 9, color: '#1f2937', fontWeight: 'bold' }}>{metadata.reportId}</Text>
        </View>
      </View>

      {/* Property Summary - Compact 2-column layout */}
      <View style={{ flexDirection: 'row', gap: 12 }}>
        <View style={{
          flexGrow: 1,
          flexShrink: 1,
          flexBasis: 'auto',
          backgroundColor: '#f0fdfa',
          padding: 12,
          borderLeft: '3pt solid #0f766e'
        }}>
          <Text style={{ fontSize: 8, color: '#0f766e', fontWeight: 'bold', marginBottom: 6 }}>
            PROPERTY ADDRESS
          </Text>
          <Text style={{ fontSize: 10, color: '#1f2937', marginBottom: 8 }}>
            {property.address}
          </Text>

          <View style={{ flexDirection: 'row', gap: 16 }}>
            <View>
              <Text style={{ fontSize: 7, color: '#6b7280' }}>Zone</Text>
              <Text style={{ fontSize: 9, color: '#1f2937', fontWeight: 'bold' }}>{property.zone}</Text>
            </View>
            <View>
              <Text style={{ fontSize: 7, color: '#6b7280' }}>Council</Text>
              <Text style={{ fontSize: 9, color: '#1f2937' }}>
                {capitalizeFirst(property.former_council)}
              </Text>
            </View>
          </View>
        </View>

        {property.heritage_status.in_hca && (
          <View style={{
            width: 200,
            backgroundColor: '#fef3c7',
            padding: 12,
            borderLeft: '3pt solid #f59e0b'
          }}>
            <Text style={{ fontSize: 8, color: '#92400e', fontWeight: 'bold', marginBottom: 4 }}>
              ⚠ HERITAGE AREA
            </Text>
            <Text style={{ fontSize: 9, color: '#78350f', lineHeight: 1.3 }}>
              {property.heritage_status.hca_name}
            </Text>
            {property.heritage_status.hca_code && (
              <Text style={{ fontSize: 8, color: '#92400e', marginTop: 4 }}>
                Code: {property.heritage_status.hca_code}
              </Text>
            )}
          </View>
        )}
      </View>
    </View>
  );
}

function capitalizeFirst(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}
