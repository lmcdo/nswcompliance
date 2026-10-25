/**
 * Reads of the LEP land use table (GET /api/lep/permissibility, lep_land_use_table gated by
 * lep_zone_coverage). Replaces typed zone lists: a zone answer comes from the council's own table,
 * or it is "not checked" — never a guess from the zone code.
 *
 * prior-art-checked: LandUseZoningCard.tsx and ProvisionsByTocStructure.tsx call the same endpoint
 * inline; this is the first shared reader, for ADGSummaryCard and StateLevelControls.
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
    return data.entries as PermissibilityEntry[];
  } catch {
    return null;
  }
}

/** The table's answer for one development type slug, or null when the table does not list it. */
export function permissibilityOf(table: LepTable, developmentType: string): string | null {
  if (!table) return null;
  return table.find((e) => e.development_type === developmentType)?.permissibility ?? null;
}

/** Slugs that are dwellings for the "does this zone allow housing at all" question. */
const DWELLING_TYPES = ['dwelling_houses', 'residential_flat_buildings'];

/**
 * True only when the table lists dwellings for this zone and every listed one is prohibited.
 * Not checked, or no dwelling row, = false: housing rules are shown rather than hidden on a guess.
 */
export function zoneProhibitsAllDwellings(table: LepTable): boolean {
  const rows = (table ?? []).filter((e) => DWELLING_TYPES.includes(e.development_type));
  return rows.length > 0 && rows.every((e) => e.permissibility === 'prohibited');
}
