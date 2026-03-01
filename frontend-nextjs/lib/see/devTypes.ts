// Development type taxonomy for DA mode structured description
// Stage 2: type selection will drive intake question filtering and DCP topic relevance

export interface DevTypeOption {
  value: string;
  label: string;
}

export const DEV_TYPE_OPTIONS: DevTypeOption[] = [
  { value: 'new_dwelling',        label: 'New dwelling' },
  { value: 'extension_single',    label: 'Single-storey extension' },
  { value: 'extension_double',    label: 'Two-storey extension' },
  { value: 'alterations',         label: 'Alterations and additions' },
  { value: 'secondary_dwelling',  label: 'Secondary dwelling (granny flat)' },
  { value: 'dual_occupancy',      label: 'Dual occupancy' },
  { value: 'driveway',            label: 'Driveway or vehicle crossover' },
  { value: 'carport',             label: 'Carport or garage' },
  { value: 'pergola',             label: 'Pergola / shade structure' },
  { value: 'deck',                label: 'Deck / terrace' },
  { value: 'balcony_verandah',    label: 'Balcony or verandah' },
  { value: 'pool',                label: 'Swimming pool or spa' },
  { value: 'fence',               label: 'Fence or boundary wall' },
  { value: 'retaining_wall',      label: 'Retaining wall' },
  { value: 'outbuilding',         label: 'Outbuilding / shed' },
  { value: 'tree_removal',        label: 'Tree removal or pruning' },
  { value: 'demolition',          label: 'Demolition' },
  { value: 'change_of_use',       label: 'Change of use' },
  { value: 'subdivision',         label: 'Subdivision' },
  { value: 'signage',             label: 'Signage' },
  { value: 'other',               label: 'Other' },
];

/**
 * Assemble a development description string from structured fields.
 * Output feeds directly into the SEE PDF introduction sentence.
 *
 * @example
 * assembleDescription('pergola', 'open-sided timber, 4.2m × 3.6m, within the front setback')
 * // => 'Pergola / shade structure — open-sided timber, 4.2m × 3.6m, within the front setback'
 */
export function assembleDescription(typeValue: string, worksText: string): string {
  const works = worksText.trim();
  if (!typeValue && !works) return '';
  if (!typeValue) return works;
  const typeLabel = DEV_TYPE_OPTIONS.find(o => o.value === typeValue)?.label ?? typeValue;
  return works ? `${typeLabel} — ${works}` : typeLabel;
}
