/**
 * Is a site-specific LEP rule about THIS lot? Decided from the lot's Planning Portal map layers
 * (layerintersect), against the land the clause itself names (DQ-140).
 *
 * prior-art-checked: lib/dcp-land-application.ts is the same pattern for a DCP's Land Application Map
 * (encode on the caller, decode + decide in /api/provisions/for-property). lib/nsw-planning-portal.ts
 * already reads Key Sites / Additional Permitted Uses, but only to list clause numbers in a side card.
 *
 * The condition on each row (regulatory_provisions.v2_land_condition, migration 109) is built from the
 * clause's own words by enrichment/config/inner_west_lep_land.py, e.g. cl 6.21: "land in Zone E3 ... and
 * Zone E4 ... and identified as 'Area 19' on the Key Sites Map" -> {layer: 'Key Sites Map',
 * labels: ['Area 19'], zones: ['E3','E4'], verified: true}.
 *
 * Three answers, and the unsure one is VISIBLE, never silent:
 *   match        the lot carries the label (and zone)  -> served
 *   no_match     a verified layer says it does not     -> withheld
 *   unconfirmed  no portal answer for the lot, a layer never seen returning labels, or land no layer
 *                holds (tidal land, flood planning area) -> served, marked "could not confirm this land"
 */

/** A rule's land condition, as stored. */
export interface LandCondition {
  layer: string | null;
  labels: string[] | null;
  zones: string[] | null;
  verified: boolean;
  source?: string;
  /** The label is shared with other land (cl 6.26 / APU '46'): a hit is only 'unconfirmed'. */
  label_not_unique?: string;
}

/** What the portal says about one lot: its zone, and each layer's label values. */
export interface LandFacts {
  zone: string | null;
  layers: Record<string, string[]>;
}

export type LandStatus = 'match' | 'no_match' | 'unconfirmed';

/** The result fields that carry a map label, across layers: Key Sites 'Label', APU 'Code', Heritage
 *  'Item Number', FSR / Height 'Additional Controls', Acid Sulfate and Biodiversity 'Class'. */
const LABEL_FIELDS = ['Label', 'Code', 'Class', 'Additional Controls', 'Item Number', 'title'];

function norm(s: string): string {
  return s
    .normalize('NFKC')
    .replace(/[‘’“”"']/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

/** Collect the label values of every layer in a layerintersect answer. Null when there is no answer. */
export function landFactsFromLayers(
  layers: Array<{ layerName: string; results?: Array<Record<string, unknown>> }> | null | undefined,
  zone: string | null | undefined
): LandFacts | null {
  if (!layers || layers.length === 0) return null;
  const out: Record<string, string[]> = {};
  for (const layer of layers) {
    if (!layer?.layerName) continue;
    const values = out[layer.layerName] ?? [];
    for (const result of layer.results ?? []) {
      for (const field of LABEL_FIELDS) {
        const v = result?.[field];
        if (typeof v === 'string' && v.trim() && !values.includes(v.trim())) values.push(v.trim());
      }
    }
    out[layer.layerName] = values;
  }
  return { zone: zone ? zone.split(/[\s:]/)[0] : null, layers: out };
}

export function encodeLandFacts(facts: LandFacts | null | undefined): string | null {
  return facts ? JSON.stringify(facts) : null;
}

/** Parse the `land_facts` query value. Anything malformed is null, which reads as UNCONFIRMED. */
export function decodeLandFacts(raw: string | null | undefined): LandFacts | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object') return null;
    const { zone, layers } = parsed as Record<string, unknown>;
    if (!layers || typeof layers !== 'object' || Array.isArray(layers)) return null;
    const clean: Record<string, string[]> = {};
    for (const [name, values] of Object.entries(layers as Record<string, unknown>)) {
      if (!Array.isArray(values)) return null;
      clean[name] = values.filter((v): v is string => typeof v === 'string');
    }
    if (Object.keys(clean).length === 0) return null;
    return { zone: typeof zone === 'string' && zone ? zone : null, layers: clean };
  } catch {
    return null;
  }
}

export function decideLandCondition(cond: LandCondition, facts: LandFacts | null): LandStatus {
  if (!facts || !cond.layer) return 'unconfirmed';
  const present = facts.layers[cond.layer];
  const labelHit =
    present !== undefined &&
    (cond.labels === null || cond.labels.some((l) => present.some((v) => norm(v) === norm(l))));
  if (labelHit) {
    if (cond.label_not_unique) return 'unconfirmed';
    if (!cond.zones) return 'match';
    if (!facts.zone) return 'unconfirmed';
    return cond.zones.includes(facts.zone) ? 'match' : 'no_match';
  }
  return cond.verified ? 'no_match' : 'unconfirmed';
}

export const UNCONFIRMED_NOTE = 'Could not confirm this land';

/**
 * Filter one list of rows. Rows with no condition pass untouched. Kept rows carry `land_status`, and an
 * unconfirmed one also `land_note` naming the land the clause describes, so the reader can check it.
 */
export function applyLandConditions<T extends { v2_land_condition?: LandCondition | null }>(
  rows: T[],
  facts: LandFacts | null
): { kept: Array<T & { land_status?: LandStatus; land_note?: string }>; withheld: number; unconfirmed: number } {
  const kept: Array<T & { land_status?: LandStatus; land_note?: string }> = [];
  let withheld = 0;
  let unconfirmed = 0;
  for (const row of rows) {
    const cond = row.v2_land_condition;
    if (!cond) {
      kept.push(row);
      continue;
    }
    const status = decideLandCondition(cond, facts);
    if (status === 'no_match') {
      withheld += 1;
      continue;
    }
    if (status === 'unconfirmed') {
      unconfirmed += 1;
      kept.push({ ...row, land_status: status, land_note: `${UNCONFIRMED_NOTE}: ${cond.source ?? ''}`.trim() });
    } else {
      kept.push({ ...row, land_status: status });
    }
  }
  return { kept, withheld, unconfirmed };
}
