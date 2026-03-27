import { View, Text } from '@react-pdf/renderer';
import { styles } from './styles';

/** Shared two-column data row used across all SEE PDF pages. */
export function DataRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.contextTableRow}>
      <Text style={styles.tableCellLabel}>{label}</Text>
      <Text style={styles.tableCellValue}>{value}</Text>
    </View>
  );
}
