// PDF Table of Contents Component

import { Page, Text, View } from '@react-pdf/renderer';
import { ProvisionGroup } from '@/lib/pdf/types';
import { styles } from './styles';

interface TableOfContentsProps {
  groups: ProvisionGroup[];
}

export function TableOfContents({ groups }: TableOfContentsProps) {
  let sectionNumber = 1;

  return (
    <Page size="A4" style={styles.tocPage}>
      <Text style={styles.tocTitle}>Table of Contents</Text>

      {groups.map((group, idx) => (
        <View key={idx}>
          {/* Main topic */}
          <View style={styles.tocItem}>
            <Text style={styles.tocNumber}>{sectionNumber++}.</Text>
            <Text style={styles.tocLabel}>{group.topicLabel}</Text>
            <Text style={styles.tocCount}>
              {group.count} provision{group.count !== 1 ? 's' : ''}
            </Text>
          </View>

          {/* Subtopics (if heritage) */}
          {group.subtopics && group.subtopics.length > 0 && (
            <View style={{ marginLeft: 20, marginBottom: 8 }}>
              {group.subtopics.map((subtopic, subIdx) => (
                <View key={subIdx} style={[styles.tocItem, { marginBottom: 4 }]}>
                  <Text style={[styles.tocNumber, { fontSize: 8 }]}>•</Text>
                  <Text style={[styles.tocLabel, { fontSize: 8, color: '#6b7280' }]}>
                    {subtopic.subtopic}
                  </Text>
                  <Text style={[styles.tocCount, { fontSize: 8 }]}>
                    ({subtopic.count})
                  </Text>
                </View>
              ))}
            </View>
          )}
        </View>
      ))}

      {/* Footer */}
      <View style={[styles.footer, { position: 'relative', marginTop: 30 }]}>
        <Text style={styles.footerLeft}>PlotDetect DCP Provision Schedule</Text>
        <Text style={styles.footerRight}>Table of Contents</Text>
      </View>
    </Page>
  );
}
