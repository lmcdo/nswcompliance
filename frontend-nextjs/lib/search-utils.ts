/**
 * Search utilities for DCP provisions
 * Multi-field search, synonym expansion, and relevance scoring
 */

/**
 * Multi-field search matching
 */
export function matchesSearch(provision: any, query: string): boolean {
  const searchLower = query.toLowerCase();

  // Searchable fields
  const searchableText = [
    provision.provision_text,
    provision.v2_dcp_part,
    provision.v2_topic,
    provision.section_title,
    provision.v2_marker
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  return searchableText.includes(searchLower);
}

/**
 * Planning-specific synonyms
 */
export const PLANNING_SYNONYMS: Record<string, string[]> = {
  'verandah': ['veranda', 'awning', 'canopy'],
  'fsr': ['floor space ratio', 'plot ratio'],
  'setback': ['building line', 'boundary setback', 'front boundary'],
  'front': ['street facing', 'primary street'],
  'height': ['building height', 'maximum height', 'height limit'],
  'parking': ['car parking', 'vehicle parking'],
  'signage': ['signs', 'advertising', 'business identification'],
  'heritage': ['conservation', 'historic', 'character'],
  'balcony': ['terrace', 'deck'],
  'fence': ['fencing', 'boundary fence', 'front fence'],
  'landscaping': ['planting', 'gardens', 'vegetation'],
  'solar': ['solar panels', 'photovoltaic', 'renewable energy'],
};

/**
 * Expand query with synonyms
 */
export function expandQueryWithSynonyms(query: string): string[] {
  const lower = query.toLowerCase();
  const synonyms = PLANNING_SYNONYMS[lower] || [];
  return [query, ...synonyms];
}

/**
 * Search with synonym expansion
 */
export function matchesSearchWithSynonyms(provision: any, query: string): boolean {
  const expandedQueries = expandQueryWithSynonyms(query);
  return expandedQueries.some(q => matchesSearch(provision, q));
}

/**
 * Common search terms for autocomplete
 * Ordered by frequency/importance
 */
export const COMMON_SEARCHES = [
  // Dimensional
  'front setback',
  'rear setback',
  'side setback',
  'building height',
  'floor space ratio',
  'FSR',
  'site coverage',

  // Features
  'signage',
  'parking',
  'landscaping',
  'fencing',
  'solar panels',
  'swimming pool',
  'balcony',
  'verandah',
  'awning',

  // Heritage
  'heritage',
  'heritage item',
  'conservation area',
  'alterations',
  'additions',
  'demolition',

  // Materials
  'materials',
  'brick',
  'timber',
  'roof',

  // Other
  'stormwater',
  'privacy',
  'waste',
  'access',
];

/**
 * Get autocomplete suggestions
 */
export function getSearchSuggestions(query: string, maxResults = 5): string[] {
  if (!query || query.length < 2) return [];

  const queryLower = query.toLowerCase();

  return COMMON_SEARCHES
    .filter(term => term.toLowerCase().includes(queryLower))
    .slice(0, maxResults);
}
