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

/** Natural-language phrase for each dev type used in the SEE Introduction paragraph. */
const TYPE_TO_PHRASE: Record<string, string> = {
  new_dwelling:        'the construction of a new dwelling-house',
  extension_single:    'a single-storey extension to an existing dwelling-house',
  extension_double:    'a two-storey extension to an existing dwelling-house',
  alterations:         'alterations and additions to an existing dwelling-house',
  secondary_dwelling:  'construction of a secondary dwelling',
  dual_occupancy:      'construction of a dual occupancy',
  driveway:            'a new driveway or vehicle crossover',
  carport:             'construction of a new carport or garage',
  pergola:             'construction of a pergola or shade structure',
  deck:                'construction of a new deck or terrace',
  balcony_verandah:    'construction of a new balcony or verandah',
  pool:                'construction of a swimming pool or spa',
  fence:               'new boundary fencing or boundary wall',
  retaining_wall:      'construction of a retaining wall',
  outbuilding:         'construction of an outbuilding or shed',
  tree_removal:        'tree removal or pruning works',
  demolition:          'demolition works',
  change_of_use:       'a change of use',
  subdivision:         'subdivision of land',
  signage:             'installation of signage',
  other:               'development works',
};

/**
 * Build the SEE Introduction paragraph text.
 * Uses natural-language type phrases and appends works detail as a separate sentence.
 */
export function buildSeeIntro(typeValue: string, worksText: string, address: string): string {
  const phrase = TYPE_TO_PHRASE[typeValue]
    || (typeValue ? typeValue.replace(/_/g, ' ') : 'development works');
  const works = worksText.trim();
  const location = address || 'the subject site';
  const baseSentence = `This Statement of Environmental Effects has been prepared in support of a Development Application for ${phrase} at ${location}.`;
  const worksSentence = works ? ` The proposed works comprise ${works}.` : '';
  const actSentence = ` The proposed development is subject to assessment under the Environmental Planning and Assessment Act 1979 (NSW).`;
  return baseSentence + worksSentence + actSentence;
}
