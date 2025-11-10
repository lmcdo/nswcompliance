/**
 * Section Extractor
 *
 * Extracts specific sections (figures, tables, sections) from full document text
 * Uses LGA-specific patterns for accurate extraction
 */

import type { LGAConfig, ExtractedSection } from '../lga-configs/types';

/**
 * Find and extract a section from document text
 */
export function extractSection(
  fullText: string,
  sectionRef: string,
  config: LGAConfig,
  sectionType?: 'figure' | 'table' | 'diagram' | 'section'
): ExtractedSection | null {
  // Build search patterns based on type and config
  const searchPatterns = buildSearchPatterns(sectionRef, sectionType, config);

  let startPos = -1;
  let foundPattern = '';

  // Find the first matching pattern
  for (const pattern of searchPatterns) {
    const pos = fullText.indexOf(pattern);
    if (pos !== -1) {
      startPos = pos;
      foundPattern = pattern;
      break;
    }
  }

  if (startPos === -1) {
    return null; // Section not found
  }

  // Extract content from start position
  const { content, endPos } = extractContent(fullText, startPos, foundPattern, config);

  // Extract images from content
  const images = extractImages(content);

  // Determine actual section type from found pattern
  const detectedType = detectSectionType(foundPattern);

  return {
    sectionRef,
    sectionType: sectionType || detectedType,
    content,
    startPosition: startPos,
    endPosition: endPos,
    hasImages: images.length > 0,
    imageCount: images.length,
    images,
  };
}

/**
 * Build search patterns for finding section
 */
function buildSearchPatterns(
  sectionRef: string,
  sectionType: string | undefined,
  config: LGAConfig
): string[] {
  const patterns: string[] = [];

  // Use custom header patterns from config if available
  if (config.quirks?.customHeaderPatterns) {
    for (const pattern of config.quirks.customHeaderPatterns) {
      // Replace \d+ with actual reference number
      const customPattern = pattern.replace(/\\d\+\\.\\d\+/, sectionRef);
      patterns.push(customPattern);
    }
  }

  // Standard markdown header patterns
  if (!sectionType || sectionType === 'figure') {
    patterns.push(`## Figure ${sectionRef}`);
    patterns.push(`# Figure ${sectionRef}`);
    patterns.push(`### Figure ${sectionRef}`);

    // Try aliases
    if (config.quirks?.figureAliases) {
      for (const alias of config.quirks.figureAliases) {
        patterns.push(`## ${alias} ${sectionRef}`);
        patterns.push(`# ${alias} ${sectionRef}`);
      }
    }
  }

  if (!sectionType || sectionType === 'table') {
    patterns.push(`## Table ${sectionRef}`);
    patterns.push(`# Table ${sectionRef}`);

    if (config.quirks?.tableAliases) {
      for (const alias of config.quirks.tableAliases) {
        patterns.push(`## ${alias} ${sectionRef}`);
      }
    }
  }

  if (!sectionType || sectionType === 'diagram') {
    patterns.push(`## Diagram ${sectionRef}`);
    patterns.push(`# Diagram ${sectionRef}`);
  }

  // Inline mentions (less specific, use as fallback)
  patterns.push(`Figure ${sectionRef}`);
  patterns.push(`Table ${sectionRef}`);

  // Section number directly (for generic sections)
  if (!sectionType || sectionType === 'section') {
    patterns.push(`## ${sectionRef}`);
    patterns.push(`### ${sectionRef}`);
  }

  return patterns;
}

/**
 * Extract content from start position to end of section
 */
function extractContent(
  fullText: string,
  startPos: number,
  foundPattern: string,
  config: LGAConfig
): { content: string; endPos: number } {
  const maxLength = 2500; // Maximum chars to extract
  let endPos = startPos + maxLength;

  // Find next section header
  const remainingText = fullText.substring(startPos + foundPattern.length);
  const nextHeaderMatch = remainingText.match(/\n#{1,3}\s+[A-Z0-9]/);

  if (nextHeaderMatch && nextHeaderMatch.index) {
    const nextHeaderPos = startPos + foundPattern.length + nextHeaderMatch.index;
    endPos = Math.min(nextHeaderPos, endPos);
  }

  const content = fullText.substring(startPos, endPos);
  return { content, endPos };
}

/**
 * Extract image references from markdown content
 */
function extractImages(content: string): string[] {
  const imageRegex = /!\[\]\(images\/([^)]+)\)/g;
  const images: string[] = [];
  let match;

  while ((match = imageRegex.exec(content)) !== null) {
    images.push(match[1]);
  }

  return images;
}

/**
 * Detect section type from pattern
 */
function detectSectionType(pattern: string): ExtractedSection['sectionType'] {
  const lower = pattern.toLowerCase();

  if (lower.includes('figure') || lower.includes('fig')) return 'figure';
  if (lower.includes('table')) return 'table';
  if (lower.includes('diagram')) return 'diagram';
  if (lower.includes('appendix')) return 'appendix';

  return 'section';
}

/**
 * Extract multiple sections at once (batch operation)
 */
export function extractMultipleSections(
  fullText: string,
  sectionRefs: string[],
  config: LGAConfig
): ExtractedSection[] {
  const sections: ExtractedSection[] = [];

  for (const ref of sectionRefs) {
    const section = extractSection(fullText, ref, config);
    if (section) {
      sections.push(section);
    }
  }

  return sections;
}
