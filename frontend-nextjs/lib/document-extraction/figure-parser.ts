/**
 * Figure Reference Parser
 *
 * Extracts figure, table, and diagram references from provision text
 * Uses LGA-specific patterns for accurate extraction
 */

import type { LGAConfig } from '../lga-configs/types';

export interface FigureReference {
  type: 'figure' | 'table' | 'diagram' | 'appendix';
  reference: string;      // e.g., "4.2", "11.1b"
  fullMatch: string;      // e.g., "Figure 4.2"
  position: number;       // Position in text
}

/**
 * Extract all figure/table/diagram references from text
 */
export function extractReferences(
  text: string,
  config: LGAConfig
): FigureReference[] {
  const references: FigureReference[] = [];

  // Extract figures
  if (config.conventions.figurePattern) {
    const figureRegex = new RegExp(config.conventions.figurePattern, 'gi');
    let match;

    while ((match = figureRegex.exec(text)) !== null) {
      references.push({
        type: 'figure',
        reference: match[1],  // Captured group
        fullMatch: match[0],
        position: match.index,
      });
    }
  }

  // Extract tables
  if (config.conventions.tablePattern) {
    const tableRegex = new RegExp(config.conventions.tablePattern, 'gi');
    let match;

    while ((match = tableRegex.exec(text)) !== null) {
      references.push({
        type: 'table',
        reference: match[1],
        fullMatch: match[0],
        position: match.index,
      });
    }
  }

  // Extract diagrams
  if (config.conventions.diagramPattern) {
    const diagramRegex = new RegExp(config.conventions.diagramPattern, 'gi');
    let match;

    while ((match = diagramRegex.exec(text)) !== null) {
      references.push({
        type: 'diagram',
        reference: match[1],
        fullMatch: match[0],
        position: match.index,
      });
    }
  }

  // Handle edge cases from config
  if (config.quirks?.edgeCases) {
    for (const edgeCase of config.quirks.edgeCases) {
      if (edgeCase.description.includes('parentheses')) {
        // Extract references in parentheses
        const parenRegex = new RegExp(edgeCase.pattern, 'gi');
        let match;

        while ((match = parenRegex.exec(text)) !== null) {
          // Extract the number from parentheses
          const numMatch = match[0].match(/\d+\.\d+[a-z]?/);
          if (numMatch) {
            references.push({
              type: 'figure',
              reference: numMatch[0],
              fullMatch: match[0],
              position: match.index,
            });
          }
        }
      }
    }
  }

  // Remove duplicates (same reference found multiple times)
  const unique = references.filter((ref, index, self) =>
    index === self.findIndex(r => r.reference === ref.reference && r.type === ref.type)
  );

  // Sort by position
  return unique.sort((a, b) => a.position - b.position);
}

/**
 * Check if text contains any figure references
 */
export function hasReferences(text: string, config: LGAConfig): boolean {
  return extractReferences(text, config).length > 0;
}

/**
 * Get unique reference numbers only
 */
export function getUniqueReferences(text: string, config: LGAConfig): string[] {
  const refs = extractReferences(text, config);
  return [...new Set(refs.map(r => r.reference))];
}

/**
 * Parse control code ranges (e.g., "C17-C22" -> ["C17", "C18", ...])
 */
export function expandControlCodeRange(rangeText: string): string[] {
  const rangeMatch = rangeText.match(/([A-Z])(\d+)-([A-Z])(\d+)/);

  if (!rangeMatch) {
    // Not a range, return as-is
    return [rangeText];
  }

  const [, prefix1, start, prefix2, end] = rangeMatch;

  if (prefix1 !== prefix2) {
    // Different prefixes, can't expand
    return [rangeText];
  }

  const startNum = parseInt(start);
  const endNum = parseInt(end);
  const codes: string[] = [];

  for (let i = startNum; i <= endNum; i++) {
    codes.push(`${prefix1}${i}`);
  }

  return codes;
}
