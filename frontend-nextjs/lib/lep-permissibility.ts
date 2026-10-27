/**
 * Reads of the LEP land use table (GET /api/lep/permissibility, lep_land_use_table gated by
 * lep_zone_coverage). Replaces typed zone lists: a zone answer comes from the council's own table,
 * or it is "not checked" — never a guess from the zone code.
 *
 * prior-art-checked: LandUseZoningCard.tsx and ProvisionsByTocStructure.tsx call the same endpoint
 * inline; this is the first shared reader, for ADGSummaryCard.
 */

export interface PermissibilityEntry {
  development_type: string;
  permissibility: 'permitted' | 'prohibited' | 'exempt' | string;
}

/** null = not checked (no zone/LGA, not covered, request failed). */
export type LepTable = PermissibilityEntry[] | null;

export async function fetchLepTable(zone: string | null | undefined, lga: string | null | undefined): Promise<LepTable> {
  if (!zone || !lga) return null;
  try {
    const r = await fetch(`/api/lep/permissibility?zone=${encodeURIComponent(zone)}&lga=${encodeURIComponent(lga)}`);
    if (!r.ok) return null;
    const data = await r.json();
    if (data?.covered !== true || !Array.isArray(data.entries) || data.entries.length === 0) return null;
    const rows = (data.entries as unknown[]).filter(
      (e): e is PermissibilityEntry => typeof (e as PermissibilityEntry)?.development_type === 'string'
        && typeof (e as PermissibilityEntry)?.permissibility === 'string');
    return rows.length > 0 ? rows : null;
  } catch {
    return null;
  }
}

/** The table's answer for one development type slug, or null when the table does not list it. */
export function permissibilityOf(table: LepTable, developmentType: string): string | null {
  if (!table) return null;
  return table.find((e) => e.development_type === developmentType)?.permissibility ?? null;
}
