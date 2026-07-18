/**
 * Shared types + display labels for the upzoning check result, used by the
 * SEO tool page (/tools/upzoning-check) and the ads landing page
 * (/duplex-check). Values render engine output verbatim — no planning logic.
 *
 * prior-art-checked: this file IS the reuse — it extracts the FormResult /
 * UpzoningResult types and FORM_LABELS previously defined inline in
 * app/tools/upzoning-check/page.tsx (edited in the same commit to import
 * from here) so the new /duplex-check landing page can share them instead
 * of duplicating them. No engine logic; services/upzoning_check.py remains
 * the single source of eligibility.
 */

export interface FormResult {
  development_type: string;
  eligible: boolean;
  reason: string;
  unconfirmed: boolean;
  requires_lmr_area: boolean;
  min_lot_size_m2: number | null;
  min_lot_width_m: number | null;
  source_clause: string | null;
  legislation_url: string | null;
  effective_date: string | null;
}

export interface UpzoningResult {
  address: string;
  zone: string | null;
  zone_full: string | null;
  zone_epi: string | null;
  legislation_url: string | null;
  lot_area_m2: number | null;
  lot_width_m: number | null;
  lot_type: 'rectangular' | 'battleaxe' | 'irregular' | null;
  lga_name: string | null;
  /** dcp_setback_controls slug (Inner West → its former council); optional so
   *  responses from a backend without the field stay type-valid. */
  former_council?: string | null;
  heritage: { flag: boolean; items: string[]; hca: string[] };
  gates: { in_lmr_area: boolean; in_tod: boolean; dual_occ_prohibited: boolean };
  status: 'ok' | 'not_residential' | 'unavailable';
  forms: FormResult[];
}

export const FORM_LABELS: Record<string, string> = {
  dwelling_houses: 'Dwelling house',
  dwelling_house: 'Dwelling house',
  dual_occupancy: 'Dual occupancy (duplex)',
  secondary_dwelling: 'Secondary dwelling (granny flat)',
  terraces: 'Terraces (row houses)',
  terrace_house: 'Terraces (row houses)',
  manor_house: 'Manor house (3–4 dwellings)',
  multi_dwelling: 'Multi-dwelling housing (townhouses)',
  multi_dwelling_housing: 'Multi-dwelling housing (townhouses)',
  residential_flat_r1r2: 'Low-rise apartments (R1/R2)',
  residential_flat_r3r4_inner: 'Mid-rise apartments (inner TOD)',
  residential_flat_r3r4_outer: 'Mid-rise apartments (outer TOD)',
};

export function formLabel(devType: string): string {
  return FORM_LABELS[devType] ?? devType.replace(/_/g, ' ');
}

/**
 * Display-layer translation of engine reason strings for consumer surfaces
 * (the ads landing page). The engine string is the audit trail and is never
 * modified — this maps it to a sentence a layperson can act on, and repairs
 * the rounding collision where ":.0f" formatting makes "12 m is below the
 * minimum 12 m" (the underlying value is fractionally under).
 */
export function plainReason(f: FormResult): string {
  const r = f.reason;

  if (f.eligible) {
    return 'Meets the standards — you can apply to build this here.';
  }

  const area = r.match(/^Lot area ([\d.]+) m² is below the minimum ([\d.]+) m²/);
  if (area) {
    const [, got, min] = area;
    return got === min
      ? `The block is just under the ${min} m² minimum for this.`
      : `The block is ${got} m² — this type needs at least ${min} m².`;
  }

  const width = r.match(/^Lot width ([\d.]+) m is below the minimum ([\d.]+) m/);
  if (width) {
    const [, got, min] = width;
    return got === min
      ? `The street frontage is just under the ${min} m minimum for this.`
      : `The frontage is ${got} m — this type needs at least ${min} m.`;
  }

  if (r.startsWith('Not in a Low and Mid-Rise reform area')) {
    return "Outside the special 2025 zones — this pathway doesn't apply here.";
  }
  if (r.startsWith('Excluded on heritage land')) {
    return 'Heritage rules on this block switch off the 2025 pathways.';
  }
  if (r.startsWith('Not in a Transport Oriented Development')) {
    return "Not near a designated station precinct — this pathway doesn't apply here.";
  }
  if (r.startsWith('Dual occupancy is prohibited')) {
    return "The council's plan specifically prohibits dual occupancies on this lot.";
  }
  if (r.startsWith('Lot standard for this form is not in the dataset')) {
    return 'No mapped standard for this type here — so we answer no rather than guess.';
  }

  // Unknown reason: show it, minus the internal hedge suffixes.
  return r
    .replace(/\s*\(or area unconfirmed\)/, '')
    .replace(/\s*\(treated conservatively\)/, '');
}

export function dualOccEligible(result: UpzoningResult): boolean {
  return (
    result.status === 'ok' &&
    result.forms.some(
      (f) => f.development_type.startsWith('dual_occupancy') && f.eligible,
    )
  );
}
