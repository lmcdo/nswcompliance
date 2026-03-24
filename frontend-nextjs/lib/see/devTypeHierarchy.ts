/**
 * Development type hierarchy for provision matching.
 *
 * Provisions in the DB are tagged at use/building-type level:
 *   dwelling_house, commercial_premises, multi_dwelling_housing, etc.
 *
 * The UI dev type values (extension_single, alterations, etc.) describe the
 * WORKS being proposed on an existing use type. This hierarchy maps works types
 * to the parent use types whose provisions apply to them.
 *
 * Rule for tagging provisions:
 *   Tag at the most specific applicable use type. The hierarchy handles upward
 *   resolution. Never tag at works type (extension_single) — tag at use type
 *   (dwelling_house). A single-storey extension is works ON a dwelling house,
 *   so dwelling_house controls apply.
 */

export const DEV_TYPE_HIERARCHY: Record<string, string[]> = {
  // ── Dwelling house works ─────────────────────────────────────────────────
  // Extensions and alterations are works on a dwelling house — inherit all
  // dwelling_house controls plus their own specific controls if any.
  new_dwelling:           ['new_dwelling', 'dwelling_house_new', 'dwelling_house'],
  extension_single:       ['extension_single', 'dwelling_addition', 'dwelling_house'],
  extension_double:       ['extension_double', 'dwelling_addition', 'dwelling_house'],
  alterations:            ['alterations', 'dwelling_house_alteration', 'dwelling_house'],

  // Legacy DB variants — kept for backward compatibility with existing tagged provisions
  dwelling_house_new:     ['dwelling_house_new', 'dwelling_house'],
  dwelling_house_alteration: ['dwelling_house_alteration', 'dwelling_house'],
  dwelling_addition:      ['dwelling_addition', 'dwelling_house'],
  dwelling_addition_ground: ['dwelling_addition_ground', 'dwelling_addition', 'dwelling_house'],
  dwelling_addition_first:  ['dwelling_addition_first', 'dwelling_addition', 'dwelling_house'],
  dwelling_addition_rear:   ['dwelling_addition_rear', 'dwelling_addition', 'dwelling_house'],
  dwelling_house:         ['dwelling_house'],

  // ── Secondary dwelling ────────────────────────────────────────────────────
  secondary_dwelling:          ['secondary_dwelling'],
  secondary_dwelling_new:      ['secondary_dwelling_new', 'secondary_dwelling'],
  secondary_dwelling_conversion: ['secondary_dwelling_conversion', 'secondary_dwelling'],

  // ── Dual occupancy ────────────────────────────────────────────────────────
  dual_occupancy:          ['dual_occupancy'],
  dual_occupancy_attached: ['dual_occupancy_attached', 'dual_occupancy'],
  dual_occupancy_detached: ['dual_occupancy_detached', 'dual_occupancy'],

  // ── Multi-dwelling ────────────────────────────────────────────────────────
  multi_dwelling_housing:  ['multi_dwelling_housing'],
  residential_flat_building: ['residential_flat_building'],
  shop_top_housing:        ['shop_top_housing', 'commercial_premises'],
  manor_house:             ['manor_house', 'multi_dwelling_housing'],

  // ── Commercial ────────────────────────────────────────────────────────────
  commercial_premises:         ['commercial_premises'],
  retail_premises:             ['retail_premises', 'commercial_premises'],
  office_premises:             ['office_premises', 'commercial_premises'],
  food_and_drink_premises:     ['food_and_drink_premises', 'commercial_premises'],
  neighbourhood_shop:          ['neighbourhood_shop', 'retail_premises', 'commercial_premises'],
  pub:                         ['pub', 'commercial_premises'],
  hotel_or_motel_accommodation: ['hotel_or_motel_accommodation', 'commercial_premises'],
  serviced_apartment:          ['serviced_apartment', 'commercial_premises'],
  change_of_use:               ['change_of_use', 'commercial_premises'],

  // ── Tourist / visitor accommodation ──────────────────────────────────────
  tourist_and_visitor_accommodation: ['tourist_and_visitor_accommodation'],

  // ── Community / education ─────────────────────────────────────────────────
  child_care_centre:       ['child_care_centre'],
  centre_based_childcare:  ['centre_based_childcare', 'child_care_centre'],
  educational_establishment: ['educational_establishment'],

  // ── Industrial ────────────────────────────────────────────────────────────
  industrial_development:  ['industrial_development'],
  light_industry:          ['light_industry', 'industrial_development'],
  warehouse:               ['warehouse', 'industrial_development'],
  heavy_industry:          ['heavy_industry', 'industrial_development'],

  // ── Other residential ─────────────────────────────────────────────────────
  boarding_house:          ['boarding_house'],
  co_living:               ['co_living', 'boarding_house'],

  // ── Subdivision ───────────────────────────────────────────────────────────
  subdivision:             ['subdivision'],

  // ── Ancillary works (compound selections from DA scope input) ─────────────
  pool:          ['pool', 'swimming_pool'],
  fence:         ['fence', 'fencing'],
  carport:       ['carport', 'garage', 'parking'],
  deck:          ['deck', 'terrace'],
  pergola:       ['pergola', 'shade_structure'],
  retaining_wall: ['retaining_wall'],
  signage:       ['signage'],
  demolition:    ['demolition'],
  outbuilding:   ['outbuilding', 'shed'],
  trees:         ['trees', 'tree_removal', 'vegetation'],

  // ── Simplified category groupings (used by Leichhardt / legacy dropdowns) ─
  residential: [
    'dwelling_house', 'dual_occupancy', 'secondary_dwelling',
    'multi_dwelling_housing', 'residential_flat_building', 'boarding_house',
    'dwelling_addition', 'dwelling_house_new', 'dwelling_house_alteration',
  ],
  commercial: [
    'commercial_premises', 'retail_premises', 'office_premises',
    'food_and_drink_premises', 'shop_top_housing', 'child_care_centre',
  ],
  industrial: [
    'industrial_development', 'warehouse', 'light_industry',
  ],
};

/**
 * Expand a single dev type to its full hierarchy for provision matching.
 * Returns an array of dev types that should match provisions.
 * Does NOT include 'ALL' — generic provisions (null / ALL) are always in scope.
 */
export function expandDevTypeHierarchy(devType: string): string[] {
  return DEV_TYPE_HIERARCHY[devType] ?? [devType];
}

/**
 * Expand multiple dev types (compound works) to their full hierarchy union.
 * Accepts comma-separated string. Returns deduplicated union.
 */
export function expandDevTypeHierarchyMulti(devTypes: string): string[] {
  const types = devTypes.split(',').map(t => t.trim()).filter(Boolean);
  const all = new Set<string>();
  for (const t of types) {
    for (const expanded of expandDevTypeHierarchy(t)) {
      all.add(expanded);
    }
  }
  return Array.from(all);
}
