// Development type taxonomy for DA mode structured description
// Primary types only — ancillary works (pool, fence, deck, etc.) moved to ancillaryWorks.ts

import { ANCILLARY_WORKS } from './ancillaryWorks';

export interface DevTypeOption {
  value: string;
  label: string;
  /** Primary LEP land use slug — used to check zone permissibility */
  lepSlug?: string;
}

export const DEV_TYPE_OPTIONS: DevTypeOption[] = [
  { value: 'new_dwelling',        label: 'New dwelling',                     lepSlug: 'dwelling_houses' },
  { value: 'extension_single',    label: 'Single-storey extension',          lepSlug: 'dwelling_houses' },
  { value: 'extension_double',    label: 'Two-storey extension',             lepSlug: 'dwelling_houses' },
  { value: 'alterations',         label: 'Alterations and additions',        lepSlug: 'dwelling_houses' },
  { value: 'secondary_dwelling',  label: 'Secondary dwelling (granny flat)', lepSlug: 'secondary_dwellings' },
  { value: 'dual_occupancy',      label: 'Dual occupancy',                   lepSlug: 'dual_occupancies' },
  { value: 'change_of_use',       label: 'Change of use' },
  { value: 'subdivision',         label: 'Subdivision',                      lepSlug: 'subdivision_of_land' },
  { value: 'other',               label: 'Other' },
];

/** Natural-language phrase for each ancillary work, used in SEE intro sentence */
const ANCILLARY_TYPE_TO_PHRASE: Record<string, string> = {
  pool:       'construction of a swimming pool',
  fencing:    'new boundary fencing',
  parking:    'construction of a carport, garage, or driveway',
  deck:       'construction of a deck or terrace',
  pergola:    'construction of a pergola or shade structure',
  retaining:  'construction of a retaining wall',
  trees:      'tree removal or pruning works',
  signage:    'installation of signage',
  demolition: 'demolition works',
};

/**
 * Assemble a development description string from structured fields.
 * Output feeds directly into the SEE PDF introduction sentence.
 *
 * Supports compound works: primary type + ancillary labels + free-text detail.
 *
 * @example
 * assembleDescription('alterations', ['pool', 'demolition'], 'rear ground floor extension 4.2m × 6.1m')
 * // => 'Alterations and additions, Swimming pool or spa, Demolition — rear ground floor extension 4.2m × 6.1m'
 */
export function assembleDescription(typeValue: string, worksText: string): string;
export function assembleDescription(typeValue: string, ancillaryValues: string[], worksText: string): string;
export function assembleDescription(typeValue: string, arg2: string | string[], arg3?: string): string {
  // Backward-compatible: 2-arg form (old signature)
  let ancillaryValues: string[];
  let worksText: string;
  if (typeof arg2 === 'string') {
    ancillaryValues = [];
    worksText = arg2;
  } else {
    ancillaryValues = arg2;
    worksText = arg3 ?? '';
  }

  const works = worksText.trim();
  const parts: string[] = [];

  if (typeValue) {
    const typeLabel = DEV_TYPE_OPTIONS.find(o => o.value === typeValue)?.label ?? typeValue;
    parts.push(typeLabel);
  }

  for (const av of ancillaryValues) {
    const ancWork = ANCILLARY_WORKS.find(a => a.value === av);
    if (ancWork) parts.push(ancWork.label);
  }

  if (parts.length === 0 && !works) return '';
  if (parts.length === 0) return works;

  const typePart = parts.join(', ');
  return works ? `${typePart} — ${works}` : typePart;
}

/** Natural-language phrase for each dev type used in the SEE Introduction paragraph. */
const TYPE_TO_PHRASE: Record<string, string> = {
  new_dwelling:        'the construction of a new dwelling-house',
  extension_single:    'a single-storey extension to an existing dwelling-house',
  extension_double:    'a two-storey extension to an existing dwelling-house',
  alterations:         'alterations and additions to an existing dwelling-house',
  secondary_dwelling:  'construction of a secondary dwelling',
  dual_occupancy:      'construction of a dual occupancy',
  change_of_use:       'a change of use',
  subdivision:         'subdivision of land',
  other:               'development works',
};

/**
 * Build the SEE Introduction paragraph text.
 * Uses natural-language type phrases, appends ancillary works, and adds works detail.
 */
export function buildSeeIntro(typeValue: string, worksText: string, address: string): string;
export function buildSeeIntro(typeValue: string, ancillaryValues: string[], worksText: string, address: string): string;
export function buildSeeIntro(typeValue: string, arg2: string | string[], arg3: string, arg4?: string): string {
  let ancillaryValues: string[];
  let worksText: string;
  let address: string;
  if (typeof arg2 === 'string') {
    // Old 3-arg signature: (typeValue, worksText, address)
    ancillaryValues = [];
    worksText = arg2;
    address = arg3;
  } else {
    // New 4-arg signature: (typeValue, ancillaryValues, worksText, address)
    ancillaryValues = arg2;
    worksText = arg3;
    address = arg4 ?? '';
  }

  const phrase = TYPE_TO_PHRASE[typeValue]
    || (typeValue ? typeValue.replace(/_/g, ' ') : 'development works');
  const works = worksText.trim();
  const location = address || 'the subject site';

  // Build ancillary phrase: "including construction of a swimming pool and demolition works"
  let ancillaryPhrase = '';
  if (ancillaryValues.length > 0) {
    const phrases = ancillaryValues
      .map(v => ANCILLARY_TYPE_TO_PHRASE[v])
      .filter(Boolean);
    if (phrases.length === 1) {
      ancillaryPhrase = `, including ${phrases[0]},`;
    } else if (phrases.length === 2) {
      ancillaryPhrase = `, including ${phrases[0]} and ${phrases[1]},`;
    } else if (phrases.length > 2) {
      const last = phrases.pop();
      ancillaryPhrase = `, including ${phrases.join(', ')}, and ${last},`;
    }
  }

  const baseSentence = `This Statement of Environmental Effects has been prepared in support of a Development Application for ${phrase}${ancillaryPhrase} at ${location}.`;
  const worksSentence = works ? ` The proposed works comprise ${works}.` : '';
  const actSentence = ` The proposed development is subject to assessment under the Environmental Planning and Assessment Act 1979 (NSW).`;
  return baseSentence + worksSentence + actSentence;
}
