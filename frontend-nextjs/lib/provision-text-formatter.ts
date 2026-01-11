/**
 * Provision Text Formatter
 * Parses raw DCP provision text and returns structured elements
 * for proper UI rendering with headings, paragraphs, lists, and controls
 */

export interface FormattedElement {
  type: 'heading' | 'subheading' | 'control-marker' | 'control-text' | 'paragraph' | 'list-item' | 'figure-ref';
  content: string;
  level?: number; // For headings (1, 2, 3)
  marker?: string; // For control markers (C1, C2, O1)
}

/**
 * Fix common OCR spacing errors, LaTeX artifacts, and encoding issues (mojibake)
 * e.g., "before1920.Therearemanydifferences" → "before 1920. There are many differences"
 * e.g., "$20 \% 1$" → "20%"
 * e.g., "â€™" → "'" (UTF-8 mojibake)
 */
function fixOcrSpacing(text: string): string {
  let fixed = text;

  // ===== FIX ENCODING ISSUES (MOJIBAKE) =====
  // These occur when UTF-8 text is interpreted as Windows-1252

  // Fix curly apostrophes/quotes
  fixed = fixed.replace(/â€™/g, "'");  // RIGHT SINGLE QUOTATION MARK
  fixed = fixed.replace(/â€˜/g, "'");  // LEFT SINGLE QUOTATION MARK
  fixed = fixed.replace(/â€œ/g, '"');  // LEFT DOUBLE QUOTATION MARK
  fixed = fixed.replace(/â€/g, '"');   // RIGHT DOUBLE QUOTATION MARK (partial)
  fixed = fixed.replace(/â€"/g, '—');  // EM DASH
  fixed = fixed.replace(/â€"/g, '–');  // EN DASH

  // Fix bullet points - various corruption patterns
  fixed = fixed.replace(/â€¢/g, '•');  // BULLET
  fixed = fixed.replace(/"¢/g, '• ');  // Corrupted bullet (quote + cent)
  fixed = fixed.replace(/[""]\s*¢/g, '• ');  // Quote + cent with optional space
  fixed = fixed.replace(/¢\s+To\b/g, '• To');  // Cent followed by "To" is a bullet
  fixed = fixed.replace(/^\s*¢\s*/gm, '• ');  // Lone cent at start of line

  // Fix other common mojibake
  fixed = fixed.replace(/Â /g, ' ');   // Non-breaking space artifact
  fixed = fixed.replace(/Â·/g, '·');   // Middle dot
  fixed = fixed.replace(/â€¦/g, '…');  // ELLIPSIS
  fixed = fixed.replace(/â˜…/g, '★');  // Star
  fixed = fixed.replace(/Â²/g, '²');   // Superscript 2
  fixed = fixed.replace(/Â°/g, '°');   // Degree symbol
  fixed = fixed.replace(/Ã©/g, 'é');   // e-acute
  fixed = fixed.replace(/Ã¨/g, 'è');   // e-grave

  // Fix smart quotes to regular quotes
  fixed = fixed.replace(/[\u2018\u2019]/g, "'");
  fixed = fixed.replace(/[\u201C\u201D]/g, '"');

  // ===== FIX SPACING ARTIFACTS =====

  // Fix number spacing artifacts: "1 8 0 m m $" → "180mm"
  fixed = fixed.replace(/(\d)\s+(\d)\s+(\d)\s+(m|c|k)\s+m\s+\$/g, '$1$2$3$4m');

  // Remove trailing "$" artifacts
  fixed = fixed.replace(/\s+\$/g, '');

  // Fix ", #" artifacts
  fixed = fixed.replace(/,\s*#\s*/g, ', ');

  // Multiple spaces to single space
  fixed = fixed.replace(/\s{2,}/g, ' ');

  // ===== FIX LATEX ARTIFACTS =====

  // Fix LaTeX math mode notation: "$20 \% 1$" → "20%"
  fixed = fixed.replace(/\$(\d+)\s*\\%\s*\d*\$/g, '$1%');

  // Fix other LaTeX percentage patterns: "\%" → "%"
  fixed = fixed.replace(/\\%/g, '%');

  // Fix stray LaTeX delimiters
  fixed = fixed.replace(/\$(\d+)\$/g, '$1');

  // ===== FIX ORPHANED SECTION NUMBERS =====

  // Fix section numbers on their own line followed by content
  // Handles: "5.1\nObjectives" or "5.1 \n Objectives" → "5.1 Objectives"
  fixed = fixed.replace(/(\d+(?:\.\d+)+)\s*[\r\n]+\s*/g, '$1 ');

  // ===== FIX OCR SPACING ERRORS =====

  // Fix missing space after period before capital letter
  // "word.Capital" → "word. Capital"
  fixed = fixed.replace(/([a-z])\.([A-Z])/g, '$1. $2');

  // Fix missing space before year numbers after lowercase
  // "before1920" → "before 1920"
  fixed = fixed.replace(/([a-z])(1[89]\d{2}|20[0-2]\d)/g, '$1 $2');

  // Fix missing space after year numbers before capital
  // "1920The" → "1920 The"
  fixed = fixed.replace(/(1[89]\d{2}|20[0-2]\d)([A-Z])/g, '$1 $2');

  // Fix "century(1840" → "century (1840"
  fixed = fixed.replace(/([a-z])\((\d)/g, '$1 ($2');

  // Fix "1890)and" → "1890) and"
  fixed = fixed.replace(/(\d)\)([a-z])/g, '$1) $2');

  return fixed;
}

/**
 * Detect section number pattern (e.g., "2.11.3", "8.1.7", "Part 8")
 */
function extractSectionNumber(text: string): { number: string; title: string } | null {
  // Pattern: X.X.X or X.X at start of text followed by title
  const sectionMatch = text.match(/^(\d+(?:\.\d+)+)\s+(.+?)(?:\s*(?:Controls|Objectives|C\d|O\d)|$)/i);
  if (sectionMatch) {
    return { number: sectionMatch[1], title: sectionMatch[2].trim() };
  }

  // Pattern: Part X: Title
  const partMatch = text.match(/^(Part\s+\d+)[:\s]+(.+?)(?:\s*(?:Controls|Objectives)|$)/i);
  if (partMatch) {
    return { number: partMatch[1], title: partMatch[2].trim() };
  }

  return null;
}

/**
 * Detect control markers (C1, C2, C3, O1, O2, etc.)
 */
function extractControlMarkers(text: string): string[] {
  const markers = text.match(/\b([CO]\d+)\b/g);
  return markers ? [...new Set(markers)] : [];
}

/**
 * Parse provision text into structured elements
 */
export function parseProvisionText(rawText: string): FormattedElement[] {
  if (!rawText) return [];

  const elements: FormattedElement[] = [];

  // Fix OCR spacing errors first
  const text = fixOcrSpacing(rawText.trim());

  // Split by common delimiters while preserving structure
  const lines = text.split(/\n+/);

  let currentControlMarker: string | null = null;
  let inControlSection = false;

  for (let line of lines) {
    line = line.trim();
    if (!line) continue;

    // Check for section heading at start
    const section = extractSectionNumber(line);
    if (section && elements.length === 0) {
      elements.push({
        type: 'heading',
        content: `${section.number} ${section.title}`,
        level: section.number.split('.').length
      });
      // Remove the heading from the line for further processing
      // Use the extracted section info, not a separate regex
      const headingText = `${section.number} ${section.title}`;
      line = line.slice(headingText.length).trim();
      if (!line) continue;
    }

    // Check for "Controls" or "Objectives" section marker
    if (/^Controls?\s*$/i.test(line) || /^Objectives?\s*$/i.test(line)) {
      elements.push({
        type: 'subheading',
        content: line,
        level: 3
      });
      inControlSection = true;
      continue;
    }

    // Check for control marker at start of line (C1, C2, O1, etc.)
    const controlMatch = line.match(/^([CO]\d+)\s+(.+)/);
    if (controlMatch) {
      currentControlMarker = controlMatch[1];
      elements.push({
        type: 'control-marker',
        content: currentControlMarker,
        marker: currentControlMarker
      });
      elements.push({
        type: 'control-text',
        content: controlMatch[2],
        marker: currentControlMarker
      });
      continue;
    }

    // Check for inline control marker
    const inlineControlMatch = line.match(/\b([CO]\d+)\b/);
    if (inlineControlMatch && !line.startsWith(inlineControlMatch[1])) {
      // Line contains control marker but doesn't start with it
      // Split around the control marker
      const parts = line.split(new RegExp(`\\b(${inlineControlMatch[1]})\\b`));
      for (let i = 0; i < parts.length; i++) {
        const part = parts[i].trim();
        if (!part) continue;

        if (/^[CO]\d+$/.test(part)) {
          currentControlMarker = part;
          elements.push({
            type: 'control-marker',
            content: part,
            marker: part
          });
        } else {
          elements.push({
            type: currentControlMarker ? 'control-text' : 'paragraph',
            content: part,
            marker: currentControlMarker || undefined
          });
        }
      }
      continue;
    }

    // Check for list item patterns
    // Bullet: • or - or * at start
    // Letter: a. b. c. or (a) (b) (c)
    // Number: 1. 2. 3. or (1) (2) (3)
    // Also catch corrupted bullets that weren't fully cleaned
    const listMatch = line.match(/^([•\-–*]\s*|["""]?¢\s*|[a-z][.)]\s*|\([a-z]\)\s*|\d+[.)]\s*|\(\d+\)\s*)(.+)/i);
    if (listMatch) {
      elements.push({
        type: 'list-item',
        content: listMatch[2],
        marker: listMatch[1].trim()
      });
      continue;
    }

    // Check for figure reference
    if (/\b(Figure|Fig\.?)\s+\d+/i.test(line)) {
      elements.push({
        type: 'figure-ref',
        content: line
      });
      continue;
    }

    // Default: regular paragraph
    elements.push({
      type: currentControlMarker ? 'control-text' : 'paragraph',
      content: line,
      marker: currentControlMarker || undefined
    });
  }

  // If no structure was detected, try to parse as continuous text
  if (elements.length <= 1 && text.length > 200) {
    return parseUnstructuredText(text);
  }

  return elements;
}

/**
 * Parse unstructured continuous text (common with OCR'd documents)
 * Splits into logical paragraphs based on content patterns
 */
function parseUnstructuredText(text: string): FormattedElement[] {
  const elements: FormattedElement[] = [];

  // Try to extract section heading from start
  const section = extractSectionNumber(text);
  if (section) {
    elements.push({
      type: 'heading',
      content: `${section.number} ${section.title}`,
      level: section.number.split('.').length
    });
  }

  // Extract control markers
  const markers = extractControlMarkers(text);
  if (markers.length > 0) {
    elements.push({
      type: 'subheading',
      content: 'Controls',
      level: 3
    });
  }

  // Split text into sentences/logical chunks
  // Split on period followed by space and capital, but not on abbreviations
  const chunks = text
    .replace(/([.!?])\s+([A-Z])/g, '$1\n$2')
    .split('\n')
    .map(c => c.trim())
    .filter(c => c.length > 0);

  // Group chunks by control marker if present
  let currentMarker: string | null = null;
  let currentBuffer: string[] = [];

  for (const chunk of chunks) {
    const markerMatch = chunk.match(/^([CO]\d+)\s*/);
    if (markerMatch) {
      // Flush buffer
      if (currentBuffer.length > 0) {
        elements.push({
          type: currentMarker ? 'control-text' : 'paragraph',
          content: currentBuffer.join(' '),
          marker: currentMarker || undefined
        });
        currentBuffer = [];
      }

      currentMarker = markerMatch[1];
      elements.push({
        type: 'control-marker',
        content: currentMarker,
        marker: currentMarker
      });

      const remainder = chunk.replace(/^[CO]\d+\s*/, '');
      if (remainder) {
        currentBuffer.push(remainder);
      }
    } else {
      currentBuffer.push(chunk);

      // Flush on paragraph boundaries (empty sentences, topic change)
      if (currentBuffer.length >= 3 || chunk.length > 150) {
        elements.push({
          type: currentMarker ? 'control-text' : 'paragraph',
          content: currentBuffer.join(' '),
          marker: currentMarker || undefined
        });
        currentBuffer = [];
      }
    }
  }

  // Flush remaining buffer
  if (currentBuffer.length > 0) {
    elements.push({
      type: currentMarker ? 'control-text' : 'paragraph',
      content: currentBuffer.join(' '),
      marker: currentMarker || undefined
    });
  }

  return elements;
}

/**
 * Get CSS classes for element type
 */
export function getElementClasses(element: FormattedElement): string {
  switch (element.type) {
    case 'heading':
      return element.level === 1
        ? 'text-lg font-bold text-gray-900 mb-3'
        : element.level === 2
        ? 'text-base font-semibold text-gray-800 mb-2'
        : 'text-sm font-semibold text-gray-700 mb-2';

    case 'subheading':
      return 'text-xs font-bold text-purple-700 uppercase tracking-wide mb-2 mt-3';

    case 'control-marker':
      return 'inline-flex items-center justify-center w-8 h-8 rounded-full bg-purple-100 text-purple-700 font-bold text-xs mr-2 flex-shrink-0';

    case 'control-text':
      return 'text-sm text-gray-800 leading-relaxed';

    case 'paragraph':
      return 'text-sm text-gray-700 leading-relaxed mb-2';

    case 'list-item':
      return 'text-sm text-gray-700 leading-relaxed pl-4 relative before:content-["•"] before:absolute before:left-0 before:text-purple-500';

    case 'figure-ref':
      return 'text-xs text-blue-600 italic mt-2';

    default:
      return 'text-sm text-gray-700';
  }
}
