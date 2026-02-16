/**
 * Numeric compliance checking utilities
 *
 * Extracts numeric limits from provision text and checks user values against them.
 */

export interface NumericCheckValues {
  height: string;
  frontSetback: string;
  sideSetback: string;
  gfa: string;
  siteCoverage: string;
  carSpaces: string;
}

export interface ComplianceResult {
  provisionId: number;
  provisionTitle: string;
  topic: string;
  limitType: 'max' | 'min';
  limitValue: number;
  limitUnit: string;
  userValue: number;
  checkType: 'height' | 'gfa' | 'siteCoverage' | 'carSpaces';
  status: 'complies' | 'borderline' | 'fails';
  limitSnippet: string; // Text snippet showing the limit
}

/**
 * Extract numeric limit from provision text
 */
export function extractNumericLimit(text: string): { value: number; isMin: boolean; isMax: boolean; snippet: string } | null {
  // Exclude provisions about freeboard, dimensions under 1m (mm/cm), or non-building contexts
  const excludePatterns = [
    /freeboard/i,
    /clearance/i,
    /\bmm\b/i,  // millimeters
    /\bcm\b/i,  // centimeters
    /diameter/i,
    /thickness/i,
    /width.*tree/i, // tree dimensions
    /fence.*height/i, // fence height (different from building height)
  ];

  for (const pattern of excludePatterns) {
    if (pattern.test(text)) return null;
  }

  // Look for values adjacent to direction keywords
  // Use negative lookahead to exclude mm/cm ((?!mm|cm))
  const maxPattern = /(?:maximum|must not exceed|not exceed|no more than)\s+(\d+(?:\.\d+)?)\s*(?:m(?!m|c)|metres?|m²|m2|%|spaces?)\b/gi;
  const minPattern = /(?:minimum|not less than|at least)\s+(\d+(?:\.\d+)?)\s*(?:m(?!m|c)|metres?|m²|m2|%|spaces?)\b/gi;

  let match;
  maxPattern.lastIndex = 0;
  minPattern.lastIndex = 0;

  const maxMatch = maxPattern.exec(text);
  if (maxMatch) {
    const snippet = text.substring(Math.max(0, maxMatch.index - 20), Math.min(text.length, maxMatch.index + maxMatch[0].length + 30));
    return { value: parseFloat(maxMatch[1]), isMin: false, isMax: true, snippet };
  }

  const minMatch = minPattern.exec(text);
  if (minMatch) {
    const snippet = text.substring(Math.max(0, minMatch.index - 20), Math.min(text.length, minMatch.index + minMatch[0].length + 30));
    return { value: parseFloat(minMatch[1]), isMin: true, isMax: false, snippet };
  }

  // Fallback: look for bare numbers with direction keywords elsewhere in text
  if (text.toLowerCase().includes('maximum') || text.toLowerCase().includes('not exceed')) {
    const bareNumPattern = /\b(\d+(?:\.\d+)?)\s*(?:m(?!m|c)|metres?|m²|m2|%|spaces?)\b/gi;
    bareNumPattern.lastIndex = 0;
    const bareMatch = bareNumPattern.exec(text);
    if (bareMatch) {
      const snippet = text.substring(Math.max(0, bareMatch.index - 20), Math.min(text.length, bareMatch.index + bareMatch[0].length + 30));
      return { value: parseFloat(bareMatch[1]), isMin: false, isMax: true, snippet };
    }
  }

  if (text.toLowerCase().includes('minimum') || text.toLowerCase().includes('not less than')) {
    const bareNumPattern = /\b(\d+(?:\.\d+)?)\s*(?:m(?!m|c)|metres?|m²|m2|%|spaces?)\b/gi;
    bareNumPattern.lastIndex = 0;
    const bareMatch = bareNumPattern.exec(text);
    if (bareMatch) {
      const snippet = text.substring(Math.max(0, bareMatch.index - 20), Math.min(text.length, bareMatch.index + bareMatch[0].length + 30));
      return { value: parseFloat(bareMatch[1]), isMin: true, isMax: false, snippet };
    }
  }

  return null;
}

/**
 * Determine which check type applies to a provision
 */
function getCheckType(topic: string, marker: string | null): 'height' | 'gfa' | 'siteCoverage' | 'carSpaces' | null {
  const t = topic.toLowerCase();
  const m = marker?.toLowerCase() || '';

  if (t.includes('height') || m === 'height') return 'height';
  if (t.includes('built form') || t.includes('floor space') || t.includes('gfa') || m.includes('floor')) return 'gfa';
  if (t.includes('site coverage') || t.includes('coverage')) return 'siteCoverage';
  if (t.includes('parking') || t.includes('car space') || m.includes('parking')) return 'carSpaces';

  return null;
}

/**
 * Check a single provision against user values
 */
function checkProvision(
  provision: any,
  checkValues: NumericCheckValues
): ComplianceResult | null {
  const checkType = getCheckType(provision.v2_topic || '', provision.v2_marker);
  if (!checkType) return null;

  const userValueStr = checkValues[checkType];
  if (!userValueStr || userValueStr === '') return null;

  const userValue = parseFloat(userValueStr);
  if (isNaN(userValue)) return null;

  const limit = extractNumericLimit(provision.provision_text);
  if (!limit) return null;

  // Determine compliance status
  let status: 'complies' | 'borderline' | 'fails';
  if (limit.isMax) {
    if (userValue <= limit.value) {
      status = 'complies';
    } else if (userValue <= limit.value * 1.1) { // Within 10%
      status = 'borderline';
    } else {
      status = 'fails';
    }
  } else {
    // isMin
    if (userValue >= limit.value) {
      status = 'complies';
    } else if (userValue >= limit.value * 0.9) { // Within 10%
      status = 'borderline';
    } else {
      status = 'fails';
    }
  }

  // Determine unit from limit snippet
  let limitUnit = 'm';
  if (limit.snippet.includes('m²') || limit.snippet.includes('m2')) limitUnit = 'm²';
  else if (limit.snippet.includes('%')) limitUnit = '%';
  else if (limit.snippet.toLowerCase().includes('space')) limitUnit = 'spaces';

  return {
    provisionId: provision.id,
    provisionTitle: provision.v2_subtopic || provision.v2_topic || 'Provision',
    topic: provision.v2_topic || '',
    limitType: limit.isMax ? 'max' : 'min',
    limitValue: limit.value,
    limitUnit,
    userValue,
    checkType,
    status,
    limitSnippet: limit.snippet.trim(),
  };
}

/**
 * Check all provisions against user values
 */
export function checkProvisionsAgainstValues(
  provisions: any[],
  checkValues: NumericCheckValues | undefined
): ComplianceResult[] {
  if (!checkValues) return [];

  const results: ComplianceResult[] = [];

  for (const provision of provisions) {
    const result = checkProvision(provision, checkValues);
    if (result) {
      results.push(result);
    }
  }

  return results;
}
