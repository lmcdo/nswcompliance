/**
 * Zone answers come from the LEP land use table, not typed zone lists (code-quality review,
 * served rules findings 3 and 7). Before 2026-10-26 ADGSummaryCard warned from a typed
 * APARTMENT_RESTRICTED_ZONES list and StateLevelControls dropped the Housing SEPP for any zone
 * outside a typed RESIDENTIAL list (MU1, E1, which do allow housing, among them).
 */
import { permissibilityOf } from '@/lib/lep-permissibility';

const t = (rows: Array<[string, string]>) => rows.map(([development_type, permissibility]) => ({ development_type, permissibility }));

describe('permissibilityOf', () => {
  it('reads one type, null when unlisted or unchecked', () => {
    expect(permissibilityOf(t([['residential_flat_buildings', 'prohibited']]), 'residential_flat_buildings')).toBe('prohibited');
    expect(permissibilityOf(t([['shops', 'permitted']]), 'residential_flat_buildings')).toBeNull();
    expect(permissibilityOf(null, 'residential_flat_buildings')).toBeNull();
  });
});
