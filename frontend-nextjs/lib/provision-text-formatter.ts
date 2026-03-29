/**
 * Provision Text Formatter
 * Parses raw DCP provision text and returns structured elements
 * for proper UI rendering with headings, paragraphs, lists, and controls
 */

export interface FormattedElement {
  type: 'heading' | 'subheading' | 'control-marker' | 'control-text' | 'paragraph' | 'list-item' | 'figure-ref' | 'note';
  content: string;
  level?: number; // For headings (1, 2, 3)
  marker?: string; // For control markers (C1, C2, O1)
}

/**
 * Escape special regex characters in a string
 */
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Strip section header from start of provision text
 *
 * Section headers are structured data in the database (toc_section_title, section_header fields).
 * This function removes duplicate headers from provision_text before formatting.
 *
 * @param text - Raw provision text that may contain section header at start
 * @param sectionHeader - Section header from database (e.g., "Built Form And Character")
 * @returns Text with section header removed if present
 *
 * @example
 * stripSectionHeader("4.1.6 Built Form And Character. Text...", "Built Form And Character")
 * // Returns: "Text..."
 *
 * stripSectionHeader("To provide more details...", "Objectives")
 * // Returns: "To provide more details..." (no match, unchanged)
 */
/**
 * Strip section header from start of provision text (CONSERVATIVE)
 * Only strips when we have an exact match to avoid accidentally removing content
 * Better to show duplicate than strip valid provision content
 *
 * Handles two patterns from database:
 * 1. "4.1.1 Objectives\n<body text>" - header followed by newline
 * 2. "4.1.1 Objectives to provide..." - header followed by continuation text
 */
export function stripSectionHeader(text: string, sectionHeader?: string | null): string {
  if (!sectionHeader || !text) return text;

  // Pattern 1: Section number + exact header + newline/end/punctuation
  // Example: "4.1.6 Built Form And Character\nObjectives..."
  const patternWithNewline = new RegExp(
    `^\\d+\\.\\d+(?:\\.\\d+)*\\s+${escapeRegex(sectionHeader)}(?:\\n|$|[.,:;]\\s*(?:\\n|$))`,
    'i'
  );

  let cleaned = text.replace(patternWithNewline, '').trim();
  if (cleaned.length < text.length - 10) {
    return cleaned;
  }

  // Pattern 2: Section number + exact header + space + lowercase word
  // Example: "4.1.1 Objectives to provide..." where "to" indicates continuation
  // Only strip if next word after header starts with lowercase (indicates continuation, not new sentence)
  const patternWithContinuation = new RegExp(
    `^\\d+\\.\\d+(?:\\.\\d+)*\\s+${escapeRegex(sectionHeader)}\\s+(?=[a-z])`,
    'i'
  );

  cleaned = text.replace(patternWithContinuation, '').trim();
  if (cleaned.length < text.length - 10) {
    return cleaned;
  }

  // Pattern 3: Section number + exact header + Page info
  // Example: "4.1.2 Planning context Page 3 · 1 provision"
  const patternWithPage = new RegExp(
    `^\\d+\\.\\d+(?:\\.\\d+)*\\s+${escapeRegex(sectionHeader)}\\s+Page\\s+\\d+[^\\n]*(?:\\n|$)`,
    'i'
  );

  cleaned = text.replace(patternWithPage, '').trim();
  if (cleaned.length < text.length - 10) {
    return cleaned;
  }

  // Otherwise return original - DON'T GUESS!
  return text;
}

/**
 * Fix common OCR spacing errors, LaTeX artifacts, and encoding issues (mojibake)
 * e.g., "before1920.Therearemanydifferences" → "before 1920. There are many differences"
 * e.g., "$20 \% 1$" → "20%"
 * e.g., "â€™" → "'" (UTF-8 mojibake)
 */
function fixOcrSpacing(text: string): string {
  let fixed = text;

  // ===== FIX TRAILING LIST NUMBERS =====
  // OCR extraction sometimes puts the NEXT item's number at the end of the previous provision
  // e.g., "...nearby streets). 2." should just be "...nearby streets)."
  // Strip trailing ". N." or ". N" where N is 1-99
  fixed = fixed.replace(/\.\s+(\d{1,2})\.?\s*$/, '.');

  // Also strip standalone trailing numbers like "...content 3." at end
  fixed = fixed.replace(/\s+(\d{1,2})\.?\s*$/, '');

  // Strip trailing roman numerals too (i., ii., iii., iv., etc.)
  const trailingRoman = /\.\s+(xxx|xxix|xxviii|xxvii|xxvi|xxv|xxiv|xxiii|xxii|xxi|xx|xix|xviii|xvii|xvi|xv|xiv|xiii|xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i)\.?\s*$/i;
  fixed = fixed.replace(trailingRoman, '.');

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

  // ===== FIX LATEX MATH MODE BLOCKS =====
  // Must run before trailing "$" stripper below, which eats opening "$" preceded by space.
  // "$3 0 0 \mathsf { m m }$" → "300mm"
  // "$1 8 0 0 ^ { \prime } { \sf s }$" → "1800's"
  // "$5 . 1 - 8 \mathsf { m }$" → "5.1-8m"
  fixed = fixed.replace(/\$([^$]*(?:\\mathsf|\\prime|\\sf)[^$]*)\$/g, (_match, inner) => {
    let result = inner;
    result = result.replace(/\\mathsf\s*\{\s*([^}]*?)\s*\}/g, (_m: string, c: string) => c.replace(/\s+/g, ''));
    result = result.replace(/\^\s*\{\s*\\prime\s*\}/g, "'");
    result = result.replace(/\{\s*\\sf\s+([^}]*?)\s*\}/g, (_m: string, c: string) => c.replace(/\s+/g, ''));
    result = result.replace(/\\[a-zA-Z]+/g, '');
    result = result.replace(/[{}^]/g, '');
    result = result.replace(/\s+/g, '');
    return result;
  });

  // ===== FIX SPACING ARTIFACTS =====

  // Fix number spacing artifacts: "1 8 0 m m $" → "180mm"
  fixed = fixed.replace(/(\d)\s+(\d)\s+(\d)\s+(m|c|k)\s+m\s+\$/g, '$1$2$3$4m');

  // Remove trailing "$" artifacts
  fixed = fixed.replace(/\s+\$/g, '');

  // Fix ", #" artifacts
  fixed = fixed.replace(/,\s*#\s*/g, ', ');

  // Multiple spaces to single space (preserve newlines!)
  // CRITICAL: Only match space character ( ), NOT all whitespace (\s includes \n \r \t)
  // This preserves paragraph breaks and list structure
  fixed = fixed.replace(/ {2,}/g, ' ');

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
 * Note: Section headers are already in database (section_header field)
 * This is only used in unstructured text parsing fallback
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
  return markers ? Array.from(new Set(markers)) : [];
}

export interface ParseOptions {
  /** Skip heading detection - useful when provisions are already under TOC structure */
  skipHeadings?: boolean;
  /** Section header from database to strip from start of text if present */
  sectionHeader?: string;
}

/**
 * Parse provision text into structured elements
 */
export function parseProvisionText(rawText: string, options?: ParseOptions): FormattedElement[] {
  if (!rawText) return [];

  const { skipHeadings = false } = options || {};
  const elements: FormattedElement[] = [];

  // Fix OCR spacing errors first
  let text = fixOcrSpacing(rawText.trim());

  // Pre-process: Insert line breaks before NB/Note patterns (e.g., "text NB:" → "text\nNB:")
  // Patterns: "NB:", "NB.", "NB ", "Note:", "NOTE:"
  if (!skipHeadings) {
    text = text.replace(/([^\n])\s+(NB[:\.\s]|Note[:\s]|NOTE[:\s])/gi, '$1\n$2');
  }

  // Pre-process: join list markers that are on their own line with next line
  // e.g., "text\nii.\nMore text" -> "text\nii. More text"
  // Also join lone bullet characters with the following line
  // e.g., "•\nStreet type..." -> "• Street type..."
  const preprocessed = text
    .replace(/\n(i{1,3}|iv|v|vi{1,3}|ix|x)\.\s*\n/gi, '\n$1. ')
    .replace(/\n([a-z])\.\s*\n/gi, '\n$1. ')
    .replace(/\n(\d+)\.\s*\n/g, '\n$1. ')
    .replace(/\n([•\-–])\s*\n/g, '\n$1 ')
    // Join word-wrapped section title continuations (Marrickville DCP artifact).
    // fixOcrSpacing joins "2.1\nUrban" → "2.1 Urban"; this step merges a lone
    // capitalised trailing word e.g., "2.1 Urban\nDesign\n" → "2.1 Urban Design\n"
    .replace(/(\d+\.\d+(?:\.\d+)?\s+[A-Za-z][a-z]*)\n([A-Z][a-z]+)\n/g, '$1 $2\n');

  // Split by common delimiters while preserving structure
  const lines = preprocessed.split(/\n+/);

  let currentControlMarker: string | null = null;
  let inControlSection = false;

  for (let line of lines) {
    line = line.trim();
    if (!line) continue;

    // Council-specific artifact filtering is handled by preProcessProvisionText()
    // in lib/dcp-format-configs.ts before text reaches this parser.

    // Handle markdown headings (e.g., "# A1.1 Section title", "## Subheading")
    // These appear in Leichhardt and other councils where the extractor uses markdown
    // heading syntax to mark section boundaries within provision text.
    if (!skipHeadings) {
      const mdHeading = line.match(/^(#{1,2})\s+(.+)/);
      if (mdHeading) {
        elements.push({
          type: mdHeading[1].length === 1 ? 'heading' : 'subheading',
          content: mdHeading[2],
          level: mdHeading[1].length === 1 ? 1 : 2
        });
        continue;
      }
    } else {
      // skipHeadings: strip markdown heading markers but keep the text as a paragraph
      const mdHeadingStrip = line.match(/^#{1,2}\s+(.+)/);
      if (mdHeadingStrip) {
        line = mdHeadingStrip[1];
      }
    }

    // Check for section headers (e.g., "4.1.9 Additional controls")
    // Section headers MAY be in database (section_header field), but not always
    // Parse them from text if they exist and skipHeadings is false
    //
    // IMPORTANT: Only detect SHORT headings (< 80 chars, < 10 words) to avoid
    // capturing body text as headings. Long titles are likely descriptions, not headers.
    if (!skipHeadings) {
      // Pattern 1: Section header at start of line (e.g., "2.16.4 Subdivision...")
      const sectionMatch = line.match(/^(\d+\.\d+(?:\.\d+)?)\s+(.+?)(?:\s*$)/);
      if (sectionMatch) {
        const titleText = sectionMatch[2];
        const wordCount = titleText.split(/\s+/).length;

        // Only treat as heading if it's reasonably short
        // Typical headers: "Objectives", "Built Form And Character", "Additional controls"
        // NOT headers: "Additional controls for contemporary dwellings within the Heritage Conservation Area blah blah"
        if (titleText.length <= 80 && wordCount <= 10) {
          elements.push({
            type: 'heading',
            content: `${sectionMatch[1]} ${titleText}`,
            level: 3
          });
          continue;
        }
        // If too long, treat as regular paragraph (fall through to default handling)
      }

      // Pattern 2: Section header within numbered list (e.g., "1. 2.16.4 Subdivision...")
      // Strip list number, check if section header follows
      const listSectionMatch = line.match(/^\d+\.\s+(\d+\.\d+(?:\.\d+)?)\s+(.+?)(?:\s*$)/);
      if (listSectionMatch) {
        const titleText = listSectionMatch[2];
        const wordCount = titleText.split(/\s+/).length;

        // Same constraints: short headings only
        if (titleText.length <= 80 && wordCount <= 10) {
          elements.push({
            type: 'heading',
            content: `${listSectionMatch[1]} ${titleText}`,
            level: 3
          });
          continue;
        }
      }

      // Pattern 3: Letter-prefixed section codes (e.g., "A1.1 HEADING", "B3.2 Title")
      // Common in Leichhardt DCP where sections are labeled A1.1, A1.2, B1.1, etc.
      const letterSectionMatch = line.match(/^([A-Z]\d+\.\d+(?:\.\d+)?)\s+(.+?)(?:\s*$)/);
      if (letterSectionMatch) {
        const titleText = letterSectionMatch[2];
        const wordCount = titleText.split(/\s+/).length;
        if (titleText.length <= 80 && wordCount <= 12) {
          elements.push({
            type: 'heading',
            content: `${letterSectionMatch[1]} ${titleText}`,
            level: 3
          });
          continue;
        }
      }
    }

    // Check for NB/Note patterns (e.g., "NB:", "Note:", etc.)
    // Match patterns like "NB: text", "Note: text", "NB. text", "NB text"
    // Limit to first sentence or two to avoid capturing entire paragraphs
    const nbPattern = /^(NB|Note|NOTE)[:\.\s]\s*([^.\n]+(?:\.[^.\n]+){0,1}\.?)/i;
    const nbMatch = line.match(nbPattern);
    if (nbMatch) {
      const noteContent = nbMatch[2].trim();
      elements.push({
        type: 'note',
        content: noteContent
      });

      // CRITICAL: Process remaining text after NB note (may contain lists!)
      const remainingText = line.slice(nbMatch[0].length).trim();
      if (remainingText) {
        const textType = currentControlMarker ? 'control-text' : 'paragraph';
        const textElements = processTextWithPossibleLists(remainingText, textType, currentControlMarker || undefined);
        elements.push(...textElements);
      }
      continue;
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
    // Handle both "C11 text..." and standalone "C11" on its own line
    const controlMatch = line.match(/^([CO]\d+)(?:\s+(.+))?$/);
    if (controlMatch) {
      currentControlMarker = controlMatch[1];
      elements.push({
        type: 'control-marker',
        content: currentControlMarker,
        marker: currentControlMarker
      });
      // If there's text on the same line, process it
      if (controlMatch[2]) {
        const textElements = processTextWithPossibleLists(controlMatch[2], 'control-text', currentControlMarker);
        elements.push(...textElements);
      }
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
          // Process part for possible inline lists
          const textType = currentControlMarker ? 'control-text' : 'paragraph';
          const textElements = processTextWithPossibleLists(part, textType, currentControlMarker || undefined);
          elements.push(...textElements);
        }
      }
      continue;
    }

    // Check for list item patterns
    // Bullet: • or - or * at start
    // Roman: i. ii. iii. iv. v. vi. etc. (period OPTIONAL - database has "i Item" without periods)
    // Letter: a. b. c. or (a) (b) (c)
    // Number: 1. 2. 3. or (1) (2) (3)
    // Also catch corrupted bullets that weren't fully cleaned
    // \([a-z]\) matches single-letter parens: (a), (b)... but also (i), (v), (x) which are
    // roman numeral single-letters. Exclude i, v, x from this pattern so they fall through
    // to paragraph rendering with their labels preserved (consistent with (ii), (iii) etc.).
    const listMatch = line.match(/^((?:i{1,3}|iv|v|vi{1,3}|ix|x)\.?\s+|[•\-–*]\s*|["""]?¢\s*|[a-z][.)]\s*|\([a-hj-uw-z]\)\s*|\d+[.)]\s*|\(\d+\)\s*)(.+)/i);
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

    // Default: regular paragraph - but check for inline lists first
    const textType = currentControlMarker ? 'control-text' : 'paragraph';
    const textElements = processTextWithPossibleLists(line, textType, currentControlMarker || undefined);
    elements.push(...textElements);
  }

  // If no structure was detected, try to parse as continuous text
  if (elements.length <= 1 && text.length > 200) {
    return parseUnstructuredText(text, { skipHeadings });
  }

  return elements;
}

/**
 * Split inline list items - handles multiple formats:
 * - "i. First; ii. Second; iii. Third" (semicolon-separated)
 * - "i. First ii. Second iii. Third" (space-separated roman numerals)
 * - "a. First b. Second c. Third" (space-separated letters)
 * - "1. First 2. Second 3. Third" (numbered lists)
 * - "text: 1. First; 2. Second" (numbered with intro text)
 * Returns array of items if list detected, otherwise null
 */
function splitInlineList(text: string): string[] | null {
  // Helper to collect all regex matches with positions
  function getAllMatches(regex: RegExp, str: string): Array<{ match: RegExpExecArray; index: number }> {
    const results: Array<{ match: RegExpExecArray; index: number }> = [];
    let m: RegExpExecArray | null;
    const re = new RegExp(regex.source, regex.flags);
    while ((m = re.exec(str)) !== null) {
      results.push({ match: m, index: m.index });
    }
    return results;
  }

  // Pattern for numbered lists: "1. text 2. text" or "text: 1. text; 2. text"
  // Match numbered markers like " 1. " or "; 1. " or ": 1. "
  // Only match 1-99 to avoid matching years like "1920."
  // Avoid matching after closing parens like "See (K). 2." unless there's clear list context
  const numberPattern = /(?:^|[;:\s])([1-9]\d?)\.\s/g;
  const numberMatches = getAllMatches(numberPattern, text);

  // Additional validation: check if numbers are sequential (1, 2, 3 or close to it)
  // This helps avoid false positives from random numbers in text
  const numbers = numberMatches.map(m => parseInt(m.match[1], 10));
  const hasSequentialNumbers = numbers.length >= 2 && numbers.some((n, i) => i > 0 && (n === numbers[i-1] + 1 || n === 1));

  if (numberMatches.length >= 2 && hasSequentialNumbers) {
    // Find positions of all numbered markers
    const positions: number[] = [];
    for (const { match, index } of numberMatches) {
      // Position of the digit (not the preceding char)
      const digitPos = index + match[0].indexOf(match[1]);
      positions.push(digitPos);
    }

    // Split at each position
    const parts: string[] = [];
    let lastPos = 0;
    for (let i = 0; i < positions.length; i++) {
      const pos = positions[i];
      if (pos > lastPos) {
        const before = text.slice(lastPos, pos).trim();
        if (before && !before.match(/^\d+\.?\s*$/)) {
          // Intro text before first number - skip it for list items
          if (i === 0 && !before.match(/^\d+\./)) {
            // This is intro text, don't include as list item
          } else if (before.match(/^\d+\./)) {
            parts.push(before);
          }
        }
      }
      lastPos = pos;
    }
    // Add the last part
    const lastPart = text.slice(lastPos).trim();
    if (lastPart) parts.push(lastPart);

    if (parts.length >= 2) {
      return parts;
    }
  }

  // Pattern for roman numerals (i., ii., iii., iv., v., vi., ... up to xxx)
  // Match patterns like " i. " or "; i. " or ": i. " or "and i. "
  // Explicit list to avoid matching empty strings
  const romanNumerals = 'xxx|xxix|xxviii|xxvii|xxvi|xxv|xxiv|xxiii|xxii|xxi|xx|xix|xviii|xvii|xvi|xv|xiv|xiii|xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i';
  const romanPattern = new RegExp(`(?:^|[;:\\s]|and\\s)(${romanNumerals})\\.\\s`, 'gi');
  const romanMatches = getAllMatches(romanPattern, text);

  if (romanMatches.length >= 2) {
    // Find positions of all roman numeral markers
    const positions: number[] = [];
    for (const { match, index } of romanMatches) {
      const romanNumeral = match[1];
      const digitPos = index + match[0].indexOf(romanNumeral);
      positions.push(digitPos);
    }

    // Split at each position
    const parts: string[] = [];
    let lastPos = 0;
    for (let i = 0; i < positions.length; i++) {
      const pos = positions[i];
      if (pos > lastPos && i > 0) {
        const part = text.slice(lastPos, pos).trim();
        // Remove trailing "and" or ";" from previous part
        const cleanPart = part.replace(/[;,]\s*$/, '').replace(/\s+and\s*$/, '').trim();
        if (cleanPart) parts.push(cleanPart);
      }
      lastPos = pos;
    }
    // Add the last part
    const lastPart = text.slice(lastPos).trim();
    if (lastPart) parts.push(lastPart);

    if (parts.length >= 2) {
      return parts;
    }
  }

  // Pattern for letter lists: "a. text b. text c. text" or "(a) text (b) text"
  const letterPattern = /(?:^|[;:\s])(?:\([a-z]\)|[a-z]\.)\s/gi;
  const letterMatches = getAllMatches(letterPattern, text);

  if (letterMatches.length >= 2) {
    // Similar position-based splitting
    const positions: number[] = [];
    for (const { match, index } of letterMatches) {
      // Find position of the letter marker
      const letterMatch = match[0].match(/\([a-z]\)|[a-z]\./i);
      if (letterMatch) {
        const digitPos = index + match[0].indexOf(letterMatch[0]);
        positions.push(digitPos);
      }
    }

    const parts: string[] = [];
    let lastPos = 0;
    for (let i = 0; i < positions.length; i++) {
      const pos = positions[i];
      if (pos > lastPos && i > 0) {
        const part = text.slice(lastPos, pos).trim();
        const cleanPart = part.replace(/[;,]\s*$/, '').trim();
        if (cleanPart) parts.push(cleanPart);
      }
      lastPos = pos;
    }
    const lastPart = text.slice(lastPos).trim();
    if (lastPart) parts.push(lastPart);

    if (parts.length >= 2) {
      return parts;
    }
  }

  return null;
}

/**
 * Process text that may contain inline lists, returning formatted elements.
 * Used for control-text and paragraphs that might have embedded lists.
 */
function processTextWithPossibleLists(
  text: string,
  type: 'control-text' | 'paragraph',
  marker?: string
): FormattedElement[] {
  const elements: FormattedElement[] = [];

  // Try to split into inline list items
  const listItems = splitInlineList(text);

  if (listItems && listItems.length >= 2) {
    // Roman numerals pattern for marker extraction (i through xxx)
    const romanMarkerPattern = /^(xxx|xxix|xxviii|xxvii|xxvi|xxv|xxiv|xxiii|xxii|xxi|xx|xix|xviii|xvii|xvi|xv|xiv|xiii|xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i)\.?\s*/i;

    for (const item of listItems) {
      // Extract the marker (1., 2., i., ii., xvi., a., b., etc.)
      let markerMatch = item.match(/^(\d+)\.?\s*/); // Try numbered first
      if (!markerMatch) {
        markerMatch = item.match(romanMarkerPattern); // Then roman
      }
      if (!markerMatch) {
        markerMatch = item.match(/^(\([a-z]\)|[a-z])\.?\s*/i); // Then letter
      }
      const itemMarker = markerMatch ? markerMatch[1] : '•';
      const content = markerMatch ? item.slice(markerMatch[0].length) : item;

      elements.push({
        type: 'list-item',
        content: content.trim(),
        marker: itemMarker
      });
    }
  } else {
    // No inline list detected, add as single element
    elements.push({
      type,
      content: text,
      marker
    });
  }

  return elements;
}

/**
 * Parse unstructured continuous text (common with OCR'd documents)
 * Splits into logical paragraphs based on content patterns
 */
function parseUnstructuredText(text: string, options?: ParseOptions): FormattedElement[] {
  const { skipHeadings = false } = options || {};
  const elements: FormattedElement[] = [];

  // Try to extract section heading from start (only if not skipping headings)
  if (!skipHeadings) {
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
 * Theme color variants for provision text elements
 */
export type ProvisionTheme = 'purple' | 'green' | 'amber';

/**
 * Get CSS classes for element type with theme support
 * NOTE: Using explicit class strings (not template literals) so Tailwind can detect them
 */
export function getElementClasses(element: FormattedElement, theme: ProvisionTheme = 'purple'): string {
  switch (element.type) {
    case 'heading':
      return element.level === 1
        ? 'text-lg font-bold text-gray-900 mb-3 mt-4'
        : element.level === 2
        ? 'text-base font-semibold text-gray-800 mb-2 mt-3'
        : element.level === 3
        ? 'text-sm font-semibold text-gray-800 mb-2 mt-3'
        : 'text-sm font-semibold text-gray-700 mb-2 mt-2';

    case 'subheading':
      if (theme === 'green') {
        return 'text-xs font-bold text-green-700 uppercase tracking-wide mb-2 mt-3';
      } else if (theme === 'amber') {
        return 'text-xs font-bold text-amber-700 uppercase tracking-wide mb-2 mt-3';
      } else {
        return 'text-xs font-bold text-purple-700 uppercase tracking-wide mb-2 mt-3';
      }

    case 'control-marker':
      if (theme === 'green') {
        return 'inline-flex items-center justify-center w-8 h-8 rounded-full bg-green-100 text-green-700 font-bold text-xs mr-2 flex-shrink-0';
      } else if (theme === 'amber') {
        return 'inline-flex items-center justify-center w-8 h-8 rounded-full bg-amber-100 text-amber-700 font-bold text-xs mr-2 flex-shrink-0';
      } else {
        return 'inline-flex items-center justify-center w-8 h-8 rounded-full bg-purple-100 text-purple-700 font-bold text-xs mr-2 flex-shrink-0';
      }

    case 'control-text':
      return 'text-sm text-gray-800 leading-relaxed';

    case 'paragraph':
      return 'text-sm text-gray-700 leading-relaxed mb-2';

    case 'list-item':
      if (theme === 'green') {
        return 'text-sm text-gray-700 leading-relaxed pl-4 relative before:content-["•"] before:absolute before:left-0 before:text-green-500';
      } else if (theme === 'amber') {
        return 'text-sm text-gray-700 leading-relaxed pl-4 relative before:content-["•"] before:absolute before:left-0 before:text-amber-500';
      } else {
        return 'text-sm text-gray-700 leading-relaxed pl-4 relative before:content-["•"] before:absolute before:left-0 before:text-purple-500';
      }

    case 'figure-ref':
      return 'text-xs text-blue-600 italic mt-2';

    case 'note':
      return 'text-sm text-gray-700 mt-3 mb-1';

    default:
      return 'text-sm text-gray-700';
  }
}
