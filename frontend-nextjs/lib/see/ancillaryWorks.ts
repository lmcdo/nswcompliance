// Ancillary works taxonomy — compound works selection for DA scope input.
// Maps ancillary selections to intake answers for auto-triage.

import type { IntakeAnswers } from './intake';
import { expandDevTypeHierarchy } from './devTypeHierarchy';

export interface AncillaryWork {
  value: string;
  label: string;
  /** Maps to existing intake field — null if no direct intake mapping */
  intakeField: keyof IntakeAnswers | null;
  /** Additional dev type tag for hierarchy expansion in API */
  devTypeTag?: string;
}

export const ANCILLARY_WORKS: AncillaryWork[] = [
  { value: 'pool',       label: 'Swimming pool or spa',         intakeField: 'pool_or_spa',              devTypeTag: 'pool' },
  { value: 'fencing',    label: 'Fence or boundary wall',       intakeField: 'new_fencing',              devTypeTag: 'fence' },
  { value: 'parking',    label: 'Carport, garage, or driveway', intakeField: 'new_parking_or_driveway',  devTypeTag: 'carport' },
  { value: 'deck',       label: 'Deck or terrace',              intakeField: null,                       devTypeTag: 'deck' },
  { value: 'pergola',    label: 'Pergola or shade structure',   intakeField: null,                       devTypeTag: 'pergola' },
  { value: 'retaining',  label: 'Retaining wall',               intakeField: null,                       devTypeTag: 'retaining_wall' },
  { value: 'trees',      label: 'Tree removal or pruning',      intakeField: 'trees_affected' },
  { value: 'signage',    label: 'Signage',                      intakeField: 'new_signage',              devTypeTag: 'signage' },
  { value: 'demolition', label: 'Demolition',                   intakeField: 'demolition',               devTypeTag: 'demolition' },
];

/** Dev types whose selection implies new impervious surfaces */
const IMPERVIOUS_PRIMARY_TYPES = new Set([
  'new_dwelling', 'extension_single', 'extension_double', 'alterations',
  'secondary_dwelling', 'dual_occupancy',
]);
const IMPERVIOUS_ANCILLARY = new Set(['pool', 'deck', 'pergola', 'parking']);

/**
 * Infer whether the proposal creates new impervious surfaces.
 * Returns 'yes' if any impervious-triggering primary type or ancillary is selected.
 */
export function inferImperviousSurfaces(primaryType: string, ancillary: string[]): 'yes' | 'no' {
  if (IMPERVIOUS_PRIMARY_TYPES.has(primaryType)) return 'yes';
  if (ancillary.some(a => IMPERVIOUS_ANCILLARY.has(a))) return 'yes';
  return 'no';
}

/**
 * Derive intake answers from scope selection (primary type + ancillary works).
 * Each ancillary's intakeField maps to 'yes' when selected; unselected ancillary
 * fields with intake mappings map to 'no'.
 *
 * Returns a partial — caller merges over auto-answers and defaults.
 */
export function deriveIntakeFromScope(
  primaryType: string,
  ancillary: string[],
): Partial<IntakeAnswers> {
  const result: Partial<IntakeAnswers> = {};
  const ancillarySet = new Set(ancillary);

  for (const work of ANCILLARY_WORKS) {
    if (!work.intakeField) continue;
    result[work.intakeField] = ancillarySet.has(work.value) ? 'yes' : 'no';
  }

  // Retaining walls often disturb tree roots — leave trees_affected unset (unknown) rather
  // than auto-excluding tree provisions when the user hasn't explicitly confirmed no trees.
  if (ancillarySet.has('retaining') && !ancillarySet.has('trees')) {
    delete result.trees_affected;
  }

  // Impervious surfaces auto-inferred — never asked manually
  result.new_impervious_surfaces = inferImperviousSurfaces(primaryType, ancillary);

  return result;
}

/**
 * Get all dev type tags for API expansion from scope selection.
 * Returns the full hierarchy-expanded union of primary type + selected ancillary works,
 * so client-side isPrimary checks match server-side provision matching.
 */
export function getScopeDevTypeTags(primaryType: string, ancillary: string[]): string[] {
  const all = new Set<string>();
  if (primaryType) {
    for (const t of expandDevTypeHierarchy(primaryType)) all.add(t);
  }
  const ancillarySet = new Set(ancillary);
  for (const work of ANCILLARY_WORKS) {
    if (work.devTypeTag && ancillarySet.has(work.value)) {
      for (const t of expandDevTypeHierarchy(work.devTypeTag)) all.add(t);
    }
  }
  return Array.from(all);
}
