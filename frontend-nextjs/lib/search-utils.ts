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
    provision.v2_marker,
    provision.hca_display_name,  // Human-readable HCA name (e.g. "Summer Hill Central HCA")
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

/**
 * Score provision relevance to search query
 * Higher score = more relevant
 */
export function scoreProvision(
  provision: any,
  query: string,
  context: {
    heritage?: boolean;
    zone?: string;
    precinct?: string;
  } = {}
): number {
  let score = 0;
  const queryLower = query.toLowerCase();
  const text = provision.provision_text?.toLowerCase() || '';

  // 1. Exact phrase in topic/title (highest priority)
  if (provision.v2_topic?.toLowerCase().includes(queryLower)) {
    score += 100;
  }

  if (provision.v2_dcp_part?.toLowerCase().includes(queryLower)) {
    score += 80;
  }

  // 2. Match in first 100 characters
  const first100 = text.substring(0, 100);
  if (first100.includes(queryLower)) {
    score += 50;
  }

  // 3. Match anywhere in text
  if (text.includes(queryLower)) {
    score += 10;
  }

  // 4. Control provisions rank higher than objectives
  if (provision.v2_marker?.startsWith('C')) {
    score += 20;
  } else if (provision.v2_marker?.startsWith('O')) {
    score += 5;
  }

  // 5. Mandatory provisions rank higher
  if (provision.v2_display_priority === 'critical') {
    score += 15;
  }

  // 6. Property context relevance
  if (context.heritage && provision.v2_dcp_layer === 'condition') {
    score += 10;
  }

  if (context.zone && provision.v2_dcp_layer === 'use_specific') {
    score += 10;
  }

  if (context.precinct && provision.v2_dcp_layer === 'precinct') {
    score += 10;
  }

  // 7. Frequency of match (how many times query appears)
  const matches = (text.match(new RegExp(queryLower, 'g')) || []).length;
  score += Math.min(matches * 2, 10); // Cap at +10

  return score;
}
