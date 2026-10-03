/**
 * Does this council's DCP cover this property? Decided from the Planning Portal's
 * Land Application Map (layerintersect layer id 8), not from the council name.
 *
 * prior-art-checked: the layer-8 answer is already PARSED in two places —
 * lib/nsw-planning-portal.ts (`landApplicationInstruments`) and
 * lib/see/propertyContext.ts (`land_application_map`) — and DISPLAYED by
 * components/compliance/LepControls.tsx. Nothing used it to decide what is
 * served. This module is that decision, so it reads the existing field rather
 * than fetching the layer again.
 *
 * WHY (DQ-120). DCP rules are served by council. Sydney DCP 2012 does not cover
 * its whole LGA: Section 1 clause 1.4 (page 4) says it applies to "the land
 * identified in Figure 1.1 Land covered by this DCP", and Figure 1.1 (page 5)
 * excludes eight areas that keep their own plans. Clause 1.5: the DCP "is to be
 * read in conjunction with Sydney LEP 2012", and clause 1.7 calls the excluded
 * land "deferred from" the DCP.
 *
 * WHAT DECIDES IT, measured 2026-10-03 on live layerintersect answers:
 *   CBD (456 Kent St, 1 Martin Pl)  -> "Sydney Local Environmental Plan 2012", Included
 *   Green Square Town Centre        -> "Sydney Local Environmental Plan (Green Square Town Centre) 2013", Included
 *   Harold Park (Tramsheds)         -> "Sydney Local Environmental Plan (Harold Park) 2011", Included
 *   Redfern/Waterloo (Eveleigh)     -> "State Environmental Planning Policy (Precincts—Eastern Harbour City) 2021", Subject Land
 *   Barangaroo, Moore Park Showground -> no layer 8 at all
 * The `Type` field reads "Included" for the excluded LEPs too, so it cannot be
 * the test. The instrument NAME is.
 *
 * KNOWN LIMIT. Figure 1.1 is a 2012 map. Where Sydney LEP 2012 has since absorbed
 * land the figure still excludes, this answers "covered" — over-inclusion only,
 * the same class accepted for Parramatta's deferred strips
 * (data/parramatta_precincts/BOUNDARY_STAGED_WORKLIST_2026-07-29.md:70).
 * Never the reverse: this cannot withhold a DCP from land its LEP names.
 */

import { toLgaSlug } from './lga-slug';

/** One layer-8 result, as lib/nsw-planning-portal.ts stores it. */
export interface LandApplicationInstrument {
  name: string;
  type: string;
}

interface DcpLandBinding {
  dcp: string;
  /** Exact `EPI Name` the Planning Portal returns for land this DCP covers. */
  lep: string;
  source: string;
}

/**
 * Councils whose DCP is known NOT to cover the whole LGA, with the LEP whose
 * land it does cover. A council absent here is not gated (status 'not_gated'),
 * which is exactly the behaviour before this module existed.
 */
const DCP_LAND_BINDING: Record<string, DcpLandBinding> = {
  city_of_sydney: {
    dcp: 'Sydney DCP 2012',
    lep: 'Sydney Local Environmental Plan 2012',
    source:
      'Sydney DCP 2012 Section 1, clauses 1.4 and 1.5 (page 4) and Figure 1.1 (page 5)',
  },
};

export type LandApplicationStatus =
  /** Council not gated — serve as before. */
  | 'not_gated'
  /** Layer 8 names only this DCP's LEP. Serve. */
  | 'covered'
  /** Layer 8 names this DCP's LEP AND another instrument (lot straddles). Serve, with a warning. */
  | 'partial'
  /** Layer 8 names other instruments only. Withhold; name what applies. */
  | 'excluded'
  /** No layer-8 answer (not supplied, portal failed, or none returned). Withhold. */
  | 'unknown';

export interface LandApplicationDecision {
  status: LandApplicationStatus;
  /** True when the DCP's rules must not be served for this property. */
  withhold: boolean;
  dcp: string | null;
  required_lep: string | null;
  /** Layer-8 instruments other than the DCP's own LEP — the plans that apply instead. */
  other_instruments: LandApplicationInstrument[];
  source: string | null;
}

/** Portal names use an em dash in some instruments; compare on a normalised form. */
function norm(s: string): string {
  return s
    .normalize('NFKC')
    .replace(/[‐-―]/g, '-')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

/** Query-string value for `land_application`. Null when there is nothing to send. */
export function encodeLandApplication(
  instruments: LandApplicationInstrument[] | null | undefined
): string | null {
  if (!instruments || instruments.length === 0) return null;
  return JSON.stringify(instruments.map((i) => ({ name: i.name, type: i.type })));
}

/**
 * Parse the `land_application` query value. Anything malformed is null — which
 * the decision reads as UNKNOWN, never as covered.
 */
export function decodeLandApplication(
  raw: string | null | undefined
): LandApplicationInstrument[] | null {
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    const out: LandApplicationInstrument[] = [];
    for (const item of parsed) {
      if (!item || typeof item !== 'object') return null;
      const { name, type } = item as Record<string, unknown>;
      if (typeof name !== 'string' || !name.trim()) return null;
      out.push({ name, type: typeof type === 'string' ? type : '' });
    }
    return out.length > 0 ? out : null;
  } catch {
    return null;
  }
}

export function decideLandApplication(
  council: string | null | undefined,
  instruments: LandApplicationInstrument[] | null | undefined
): LandApplicationDecision {
  const slug = toLgaSlug(council);
  const binding = slug ? DCP_LAND_BINDING[slug] : undefined;
  if (!binding) {
    return {
      status: 'not_gated',
      withhold: false,
      dcp: null,
      required_lep: null,
      other_instruments: [],
      source: null,
    };
  }

  const base = { dcp: binding.dcp, required_lep: binding.lep, source: binding.source };
  if (!instruments || instruments.length === 0) {
    return { ...base, status: 'unknown', withhold: true, other_instruments: [] };
  }

  const lep = norm(binding.lep);
  const own = instruments.filter((i) => norm(i.name) === lep);
  const others = instruments.filter((i) => norm(i.name) !== lep);
  const ownIncluded = own.some((i) => norm(i.type) === 'included');

  if (ownIncluded && others.length === 0) {
    return { ...base, status: 'covered', withhold: false, other_instruments: [] };
  }
  if (ownIncluded) {
    return { ...base, status: 'partial', withhold: false, other_instruments: others };
  }
  if (own.length > 0) {
    // The LEP is named but not as "Included" (e.g. a deferred-matter type). Not
    // proven covered, not proven excluded.
    return { ...base, status: 'unknown', withhold: true, other_instruments: others };
  }
  return { ...base, status: 'excluded', withhold: true, other_instruments: others };
}
