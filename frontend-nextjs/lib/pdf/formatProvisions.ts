// Group and format provisions for PDF export

import { ProvisionForPDF, ProvisionGroup, ProvisionSubgroup } from './types';

const TOPIC_ORDER = [
  'built_form',
  'parking',
  'heritage',
  'landscaping',
  'waste',
  'privacy',
  'stormwater',
] as const;

const TOPIC_LABELS: Record<string, string> = {
  built_form: 'Built Form',
  parking: 'Parking & Access',
  heritage: 'Heritage',
  landscaping: 'Landscaping',
  waste: 'Waste Management',
  privacy: 'Privacy & Amenity',
  stormwater: 'Stormwater',
  setbacks: 'Setbacks',
  height: 'Height',
  trees: 'Trees',
  // Additional topics from v2_topic
  subdivision: 'Subdivision',
  fencing: 'Fencing',
  signage: 'Signage',
  advertising: 'Advertising',
  outdoor_dining: 'Outdoor Dining',
  basement: 'Basement',
  attics: 'Attics',
  solar: 'Solar Panels',
  pools: 'Swimming Pools',
  accessibility: 'Accessibility',
  noise: 'Noise',
  contamination: 'Contamination',
  flooding: 'Flooding',
  biodiversity: 'Biodiversity',
  other: 'Other Provisions',
};

export function groupProvisionsByTopic(
  provisions: ProvisionForPDF[],
  options: { includeNonActionable?: boolean } = {}
): ProvisionGroup[] {
  const { includeNonActionable = true } = options;
  if (!includeNonActionable) {
    provisions = provisions.filter(p => p.v2_is_actionable !== false);
  }
  // Group by v2_marker (main topic), fallback to v2_topic if marker empty
  const byMarker = provisions.reduce((acc, p) => {
    // Use v2_marker if available, otherwise use v2_topic, otherwise 'other'
    const marker = (p.v2_marker && p.v2_marker.trim())
      ? p.v2_marker.toLowerCase().trim()
      : (p.v2_topic && p.v2_topic.trim())
        ? p.v2_topic.toLowerCase().trim().replace(/\s+/g, '_')
        : 'other';

    if (!acc[marker]) acc[marker] = [];
    acc[marker].push(p);
    return acc;
  }, {} as Record<string, ProvisionForPDF[]>);

  // Convert to ProvisionGroup array
  const groups: ProvisionGroup[] = Object.entries(byMarker).map(
    ([marker, provs]) => {
      const topicLabel = TOPIC_LABELS[marker] || capitalizeFirst(marker);

      // For heritage, create subtopic groups
      if (marker === 'heritage') {
        const subtopics = createSubtopicGroups(provs);
        return {
          topic: marker,
          topicLabel,
          count: provs.length,
          provisions: provs,
          subtopics,
        };
      }

      return {
        topic: marker,
        topicLabel,
        count: provs.length,
        provisions: provs,
      };
    }
  );

  // Sort by defined order
  return groups.sort((a, b) => {
    const aIdx = TOPIC_ORDER.indexOf(a.topic as any);
    const bIdx = TOPIC_ORDER.indexOf(b.topic as any);
    if (aIdx === -1) return 1;
    if (bIdx === -1) return -1;
    return aIdx - bIdx;
  });
}

function createSubtopicGroups(
  provisions: ProvisionForPDF[]
): ProvisionSubgroup[] {
  const bySubtopic = provisions.reduce((acc, p) => {
    const subtopic = p.v2_topic || 'General';
    if (!acc[subtopic]) acc[subtopic] = [];
    acc[subtopic].push(p);
    return acc;
  }, {} as Record<string, ProvisionForPDF[]>);

  return Object.entries(bySubtopic)
    .map(([subtopic, provs]) => ({
      subtopic,
      count: provs.length,
      provisions: provs,
    }))
    .sort((a, b) => a.subtopic.localeCompare(b.subtopic));
}

function capitalizeFirst(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}

export function generateFilename(address: string, date: Date): string {
  const sanitizedAddress = address
    .replace(/\s+/g, '-')
    .replace(/[^a-zA-Z0-9-]/g, '')
    .replace(/-+/g, '-');

  const dateStr = date.toISOString().split('T')[0];

  return `${sanitizedAddress}-DCP-Provision-Schedule-${dateStr}.pdf`;
}

export function generateReportId(
  council: string,
  zone: string,
  heritage: boolean,
  count: number,
  date: Date
): string {
  const dateStr = date.toISOString().split('T')[0].replace(/-/g, '');
  const councilCode = council.substring(0, 3).toUpperCase();
  const heritageFlag = heritage ? 'H' : '';

  return `PD-${dateStr}-${councilCode}-${zone}-${heritageFlag}${count}`;
}

export function formatCitation(provision: ProvisionForPDF): string {
  const part = provision.v2_dcp_part || '';
  const page = provision.pdf_printed_page || provision.pdf_page || '?';

  return `${part}, PDF p.${page}`;
}

/**
 * Sanitize text to remove scientific notation, LaTeX artifacts, and invalid formatting
 */
export function sanitizeForPdf(text: string): string {
  let cleaned = text;

  // Remove scientific notation (e.g., -1.5690502821161975e+22)
  cleaned = cleaned.replace(/-?\d+\.?\d*e[+-]?\d+/gi, '[invalid number]');

  // Fix LaTeX superscript notation: \mathsf{m}^{2}$ → m²
  cleaned = cleaned.replace(/\\mathsf\s*\{\s*m\s*\}\s*\^\s*\{\s*2\s*\}\s*\$/g, 'm²');
  cleaned = cleaned.replace(/\\mathrm\s*\{\s*m\s*\}\s*\^\s*\{\s*2\s*\}\s*\$/g, 'm²');

  // Fix other LaTeX artifacts: \mathsf{...} → ... and \mathrm{...} → ...
  cleaned = cleaned.replace(/\\mathsf\s*\{\s*([^}]+)\s*\}/g, '$1');
  cleaned = cleaned.replace(/\\mathrm\s*\{\s*([^}]+)\s*\}/g, '$1');

  // Remove stray $ symbols (LaTeX delimiters)
  cleaned = cleaned.replace(/\$/g, '');

  // Remove backslash escapes
  cleaned = cleaned.replace(/\\\\/g, '');

  return cleaned;
}

export function truncateText(text: string, maxWords: number = 100): string {
  // Sanitize first to remove invalid numbers
  const sanitized = sanitizeForPdf(text);

  // Split into words (whitespace separated)
  const words = sanitized.trim().split(/\s+/);

  // If within limit, return as-is
  if (words.length <= maxWords) return sanitized;

  // Take first maxWords words
  const truncated = words.slice(0, maxWords).join(' ');

  // Find the last sentence end (period followed by space or end of string)
  // Search backwards for ". " or period at end
  const lastPeriod = truncated.lastIndexOf('. ');
  const endsWithPeriod = truncated.endsWith('.');

  if (lastPeriod !== -1) {
    // Found a sentence break - truncate there (include the period)
    return truncated.substring(0, lastPeriod + 1);
  } else if (endsWithPeriod) {
    // The truncated text happens to end with a period
    return truncated;
  } else {
    // No sentence break found - add ellipsis
    return truncated + '...';
  }
}

/**
 * Extract key numeric values from provision text for highlighting
 * Returns array of [number, unit] pairs
 */
export function extractKeyNumbers(text: string): string[] {
  const pattern = /\b(\d+(?:\.\d+)?)\s*(m²|m|mm|cm|km|%|metres?|meters?|centimetres?|centimeters?|sqm|square metres?|ha|hectares?)\b/gi;
  const matches = text.matchAll(pattern);
  const numbers: string[] = [];

  for (const match of matches) {
    numbers.push(`${match[1]}${match[2]}`);
  }

  return numbers.slice(0, 3); // Return max 3 key numbers
}

/**
 * Parse text with numeric highlights AND control reference markers (C34, O5, etc.)
 * Returns segments with type flags for styling
 */
export function parseTextWithAllHighlights(text: string): Array<{
  text: string;
  isNumeric: boolean;
  isControl: boolean;
}> {
  const segments: Array<{ text: string; isNumeric: boolean; isControl: boolean }> = [];
  let remaining = text;

  // Pattern for numerics with units - includes m2 (digit) and m² (superscript)
  const numericPattern = /\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(m²|m2|m|mm|cm|km|%|metres?|meters?|centimetres?|centimeters?|sqm|square metres?|ha|hectares?)\b/gi;

  // Pattern for control markers (C34, O5, etc.)
  const controlPattern = /\b([CO]\d+)\b/g;

  // Combine patterns - find all matches
  const allMatches: Array<{ index: number; length: number; text: string; type: 'numeric' | 'control' }> = [];

  // Find numeric matches
  for (const match of remaining.matchAll(numericPattern)) {
    allMatches.push({
      index: match.index!,
      length: match[0].length,
      text: match[0],
      type: 'numeric'
    });
  }

  // Find control matches
  for (const match of remaining.matchAll(controlPattern)) {
    allMatches.push({
      index: match.index!,
      length: match[0].length,
      text: match[0],
      type: 'control'
    });
  }

  // Sort by index
  allMatches.sort((a, b) => a.index - b.index);

  let lastIndex = 0;

  for (const match of allMatches) {
    // Add text before match
    if (match.index > lastIndex) {
      segments.push({
        text: remaining.substring(lastIndex, match.index),
        isNumeric: false,
        isControl: false
      });
    }

    // Add the match
    segments.push({
      text: match.text,
      isNumeric: match.type === 'numeric',
      isControl: match.type === 'control'
    });

    lastIndex = match.index + match.length;
  }

  // Add remaining text
  if (lastIndex < remaining.length) {
    segments.push({
      text: remaining.substring(lastIndex),
      isNumeric: false,
      isControl: false
    });
  }

  // If no matches found, return whole text
  if (segments.length === 0) {
    segments.push({ text: remaining, isNumeric: false, isControl: false });
  }

  return segments;
}

/**
 * Split provision text into segments with numeric values highlighted
 * Returns array of {text, isNumeric} segments for inline rendering
 */
export function parseTextWithNumericHighlights(text: string): Array<{ text: string; isNumeric: boolean }> {
  // Match numbers with units - includes m2 (digit) and m² (superscript)
  const pattern = /\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(m²|m2|m|mm|cm|km|%|metres?|meters?|centimetres?|centimeters?|sqm|square metres?|ha|hectares?)\b/gi;
  const segments: Array<{ text: string; isNumeric: boolean }> = [];
  let lastIndex = 0;

  // Find all numeric matches
  const matches = Array.from(text.matchAll(pattern));

  for (const match of matches) {
    const matchStart = match.index!;
    const matchEnd = matchStart + match[0].length;

    // Add text before the match
    if (matchStart > lastIndex) {
      segments.push({
        text: text.substring(lastIndex, matchStart),
        isNumeric: false
      });
    }

    // Add the numeric match
    segments.push({
      text: match[0],
      isNumeric: true
    });

    lastIndex = matchEnd;
  }

  // Add remaining text after last match
  if (lastIndex < text.length) {
    segments.push({
      text: text.substring(lastIndex),
      isNumeric: false
    });
  }

  // If no matches found, return the whole text as one segment
  if (segments.length === 0) {
    segments.push({ text, isNumeric: false });
  }

  return segments;
}

/**
 * Split text into paragraphs and highlight numerics within each paragraph
 * Preserves paragraph structure and detects lists, nested lists, headers, and control markers
 */
export function parseParagraphsWithHighlights(text: string): Array<{
  paragraph: string;
  segments: Array<{ text: string; isNumeric: boolean; isControl: boolean }>;
  isList: boolean;
  isNestedList: boolean;
  isHeader: boolean;
  isControlMarker: boolean;
}> {
  // PRE-PROCESSING: Add newlines for better paragraph detection

  // 1. Split inline control/objective markers (C1, O1, etc)
  // Matches: "C1 Text" or "O2 Text" -> "C1\nText"
  text = text.replace(/(\s)([CO]\d+)(\s+)([A-Z])/g, '$1$2\n$4');

  // 2. Add breaks before section headers in multiple contexts:

  // 2a. Section headers at start of text or after newline (e.g., "2.16.4 Subdivision...")
  text = text.replace(/(^|\n)(\d+\.\d+\.\d+(?:\.\d+)?)\s+([A-Z])/gm, '$1$2 $3\n');

  // 2b. Section headers in numbered lists (e.g., "1. 2.16.4 Subdivision...")
  // Preserve the list number, add break before section number
  text = text.replace(/(\d+\.)\s+(\d+\.\d+\.\d+(?:\.\d+)?)\s+([A-Z])/g, '$1\n$2 $3\n');

  // 2c. Section headers after periods (e.g., "text. 8.4.1 Header...")
  text = text.replace(/(\.)(\s+)(\d+\.\d+\.\d+(?:\.\d+)?)\s+([A-Z])/g, '$1\n$3 $4');

  // 3. Add breaks before lettered list items that follow periods
  // "controls. a. Text" -> "controls.\na. Text"
  text = text.replace(/(\.)(\s+)([a-h]\.)\s+([A-Z])/g, '$1\n$3 $4');

  // 4. Add breaks before "The HCA/area/estate..." (new topic paragraphs)
  text = text.replace(/(\.)\s+(The\s+(?:HCA|area|estate|property|development))/g, '$1\n$2');

  // 5. Add breaks before "It is also/of significance..." (new significance points)
  text = text.replace(/(\.)\s+(It\s+is\s+(?:also|of|significant))/g, '$1\n$2');

  console.log('[PDF Parse] Pre-processed text sample:', text.substring(0, 200));

  // If text has newlines, split on them; otherwise use intelligent splitting
  const hasNewlines = text.includes('\n');
  let lines: string[];

  if (hasNewlines) {
    lines = text.split(/\n/).filter(l => l.trim().length > 0);
  } else {
    // No newlines - find all split points (headers and list items)
    const splitPoints: Array<{ index: number; type: string }> = [];

    // Find section headers (e.g., "2.12.3 Signage controls")
    const headerPattern = /\d+\.\d+(?:\.\d+)*\s+[A-Z][a-z]+/g;
    for (const match of text.matchAll(headerPattern)) {
      splitPoints.push({ index: match.index!, type: 'header' });
    }

    // Find list items: numbered (1. 2.), lettered (a. b.), roman (i. ii. iii.)
    // Match list markers after ". " OR ";" OR at start/after whitespace
    const listPatterns = [
      // After sentence ending (period)
      /\.\s+(\d+)\.\s+/g,           // Numbered: ". 1. ", ". 2. "
      /\.\s+([a-h])\.\s+/g,         // Lettered: ". a. ", ". b. "
      /\.\s+(i{1,3}|iv|v|vi{1,3}|ix|x)\.\s+/g,  // Roman: ". i. ", ". ii. "

      // After semicolon (common in provision lists) - space is optional
      /;\s*(\d+)\.\s+/g,            // Numbered: ";1. ", "; 1. "
      /;\s*([a-h])\.\s+/g,          // Lettered: ";a. ", "; a. "
      /;\s*(i{1,3}|iv|v|vi{1,3}|ix|x)\.\s+/g,   // Roman: ";ii. ", "; ii. "

      // After 2+ spaces or at start (captures list items not after period)
      /(?:^|\s{2,})(\d+)\.\s+/g,    // Numbered at start or after spacing
      /(?:^|\s{2,})([a-h])\.\s+/g,  // Lettered at start or after spacing
      /(?:^|\s{2,})(i{1,3}|iv|v|vi{1,3}|ix|x)\.\s+/g,  // Roman at start or after spacing
    ];

    for (const pattern of listPatterns) {
      for (const match of text.matchAll(pattern)) {
        const matchText = match[0];
        const capturedMarker = match[1];
        // Find where the captured marker (number/letter/roman) starts in the match
        const markerOffset = matchText.indexOf(capturedMarker);
        const listItemStart = match.index! + markerOffset;
        splitPoints.push({ index: listItemStart, type: 'list' });
      }
    }

    // Find control/objective markers (C7, O7, C2, C3, etc.)
    // Split BEFORE and AFTER them to isolate on separate line
    const controlMarkerPattern = /\s+([CO]\d+)(?=\s|$)/g;
    for (const match of text.matchAll(controlMarkerPattern)) {
      const markerStart = match.index! + match[0].indexOf(match[1]);
      const markerEnd = markerStart + match[1].length;

      // Split BEFORE the marker
      splitPoints.push({ index: markerStart, type: 'control-start' });

      // Split AFTER the marker (skip any trailing space)
      const nextChar = text[markerEnd];
      if (nextChar === ' ') {
        splitPoints.push({ index: markerEnd + 1, type: 'control-end' });
      } else {
        splitPoints.push({ index: markerEnd, type: 'control-end' });
      }
    }

    // Sort by position
    splitPoints.sort((a, b) => a.index - b.index);

    // If no split points found, return whole text
    if (splitPoints.length === 0) {
      lines = [text.trim()];
    } else {
      lines = [];

      // Add text before first split point
      if (splitPoints[0].index > 0) {
        const before = text.substring(0, splitPoints[0].index).trim();
        if (before) lines.push(before);
      }

      // Create chunks between split points
      for (let i = 0; i < splitPoints.length; i++) {
        const start = splitPoints[i].index;
        const end = splitPoints[i + 1]?.index ?? text.length;
        const chunk = text.substring(start, end).trim();
        if (chunk) lines.push(chunk);
      }
    }
  }

  const paragraphs: Array<{ paragraph: string; isList: boolean }> = [];

  // If we split on headers (no newlines), each line is already a complete paragraph
  // If we split on newlines, we need to combine lines into paragraphs
  if (!hasNewlines) {
    // Each line from header/list splitting is a complete paragraph
    console.log(`[PDF Parse] Processing ${lines.length} lines (no newlines detected)`);
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      if (trimmed) {
        const isListItem = /^([•\-*]|\d+[\.):]|[a-z][\.):]|[ivx]+[\.):])\s+/i.test(trimmed);
        console.log(`[PDF Parse] Line ${i + 1}: isList=${isListItem}, text="${trimmed.substring(0, 40)}..."`);
        paragraphs.push({ paragraph: trimmed, isList: isListItem });
      }
    }
  } else {
    // Original logic for newline-split text
    let currentPara = '';
    let isInList = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      const isListItem = /^([•\-*]|\d+[\.):]|[a-z][\.):]|[ivx]+[\.):])\s+/i.test(line);

      if (isListItem) {
        if (currentPara && !isInList) {
          paragraphs.push({ paragraph: currentPara, isList: false });
          currentPara = '';
        }
        paragraphs.push({ paragraph: line, isList: true });
        isInList = true;
      } else {
        if (isInList && line.length > 0) {
          isInList = false;
        }

        if (currentPara.length > 0) {
          currentPara += ' ' + line;
        } else {
          currentPara = line;
        }

        const nextLine = lines[i + 1];
        const nextIsBlank = !nextLine || nextLine.trim().length === 0;
        const nextIsList = nextLine && /^([•\-*]|\d+[\.):]|[a-z][\.):]|[ivx]+[\.):])\s+/i.test(nextLine.trim());

        if (nextIsBlank || nextIsList || i === lines.length - 1) {
          if (currentPara.length > 0) {
            paragraphs.push({ paragraph: currentPara, isList: false });
            currentPara = '';
            isInList = false;
          }
        }
      }
    }
  }

  const result = paragraphs.map(({ paragraph, isList }, idx) => {
    // Check if this paragraph is a section header (e.g., "2.25.3.14 Freeboard C34")
    const isHeader = /^\d+\.\d+(?:\.\d+)*\s+[A-Z]/.test(paragraph);

    // Check if this is a control/objective marker (C7, O7, C2, etc.)
    // ONLY match if paragraph is JUST the marker (nothing else)
    const isControlMarker = /^[CO]\d+\s*$/.test(paragraph.trim());

    // Check if this is a nested list (e.g., "2. ii. Sites" or "a. i. Something")
    const isNestedList = isList && /^([•\-*]|\d+[\.):]|[a-z][\.):]|[ivx]+[\.):])\s+([ivx]+|[a-z])[\.)]\s+/i.test(paragraph);

    // Parse segments with all highlights (numerics + control markers)
    const segments = parseTextWithAllHighlights(paragraph);

    // DEBUG LOGGING
    console.log(`[PDF Parse] Para ${idx + 1}:`, {
      text: paragraph.substring(0, 60) + (paragraph.length > 60 ? '...' : ''),
      isHeader,
      isControlMarker,
      isList,
      isNestedList,
      segmentCount: segments.length
    });

    return {
      paragraph,
      segments,
      isList,
      isNestedList,
      isHeader,
      isControlMarker
    };
  });

  console.log(`[PDF Parse] Total paragraphs: ${result.length}`);
  return result;
}

/**
 * Detect if text is a Table of Contents entry rather than actual provision
 */
export function isTableOfContents(text: string): boolean {
  if (!text || text.length < 20) return false;

  // Check for multiple sequential section numbers (e.g., "8.1.7.1 Title\n8.1.7.2 Title")
  const sectionNumberPattern = /^\d+\.\d+\.\d+(?:\.\d+)?/gm;
  const matches = text.match(sectionNumberPattern);

  // If 3+ section numbers appear, it's likely a TOC
  if (matches && matches.length >= 3) return true;

  // Check for TOC-style formatting: short lines with section numbers
  const lines = text.trim().split('\n');
  const tocStyleLines = lines.filter(line => {
    const trimmed = line.trim();
    return trimmed.length < 80 && /^\d+\.\d+/.test(trimmed);
  });

  // If most lines are TOC-style, it's a TOC
  if (tocStyleLines.length >= Math.min(lines.length * 0.6, 4)) return true;

  return false;
}
