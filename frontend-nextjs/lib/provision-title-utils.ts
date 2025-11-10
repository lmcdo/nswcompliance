/**
 * Provision Title Utilities
 * Generic functions to extract human-readable titles from provision data
 *
 * Handles machine-generated IDs like:
 * - Provision_531
 * - table_in_Marrickville_DCP_2011__4.1_Low_Density_Residential_Development_0
 * - 4.3, 9.29.3 (actual clause numbers)
 */

export interface ProvisionContent {
  id: number;
  ref_number: string;
  section_header: string;
  provision_text: string;
  document_id: string;
}

/**
 * Extract section name from document_id
 *
 * Examples:
 * - "Marrickville_DCP_2011__4.1_Low_Density_Residential_Development"
 *   → "4.1 Low Density Residential Development"
 *
 * - "Leichhardt_DCP_2013__Part_C_Heritage"
 *   → "Part C Heritage"
 */
function extractSectionFromDocumentId(documentId: string): string | null {
  if (!documentId) return null;

  // Pattern: Document_Name_YEAR__Section_Name
  // Everything after "__" is the section name
  const match = documentId.match(/__(.+)$/);
  if (!match) return null;

  const section = match[1]
    .replace(/_/g, ' ')  // Replace underscores with spaces
    .replace(/\s+/g, ' ') // Normalize multiple spaces
    .trim();

  return section || null;
}

/**
 * Extract table subject from HTML table markup
 * Looks for cell with colspan attribute (typically the table title)
 * Falls back to second cell if no colspan found
 *
 * Examples:
 * - "<table><tr><td>Width of lot</td><td colspan='2'>Minimum setback from side boundaries</td>..."
 *   → "Minimum setback from side boundaries"
 *
 * - "<table><tr><td>Front</td><td colspan='2'>The front garden..."
 *   → "The front garden..."
 */
function extractTableSubject(provisionText: string): string | null {
  if (!provisionText.includes('<table')) return null;

  // First, try to find cell with colspan attribute (typically the table title)
  const colspanMatch = provisionText.match(/<t[dh][^>]*colspan[^>]*>(.*?)<\/t[dh]>/i);

  let subject: string;

  if (colspanMatch) {
    // Use colspan cell (this is usually the table title)
    subject = colspanMatch[1];
  } else {
    // Fallback: get all cells in first row and use the longest one
    const allCells = provisionText.match(/<t[dh][^>]*>(.*?)<\/t[dh]>/gi);
    if (!allCells || allCells.length === 0) return null;

    // Extract content from each cell
    const cellContents = allCells.slice(0, 3).map(cell => {
      const content = cell.replace(/<t[dh][^>]*>/i, '').replace(/<\/t[dh]>/i, '');
      return content.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/<[^>]+>/g, '').trim();
    });

    // Use the longest cell (likely the title) or second cell if first is short
    if (cellContents.length > 1 && cellContents[0].length < 20) {
      subject = cellContents[1]; // Second cell is likely the title
    } else {
      subject = cellContents[0];
    }
  }

  // Clean up HTML entities and tags
  subject = subject
    .replace(/&#x27;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&gt;/g, '>')
    .replace(/&lt;/g, '<')
    .replace(/<[^>]+>/g, '')
    .trim();

  // Take first sentence only (before period) if it's long
  if (subject.length > 50 && subject.includes('.')) {
    subject = subject.split('.')[0];
  }

  // Capitalize first letter
  return subject.charAt(0).toUpperCase() + subject.slice(1);
}

/**
 * Get display title for a provision
 *
 * Priority:
 * 1. section_header (if exists and not empty)
 * 2. Parse document_id for section name + ref_number pattern
 * 3. Fallback to cleaned ref_number
 */
export function getProvisionDisplayTitle(provision: ProvisionContent): string {
  // 1. Prefer section_header if available and not empty
  if (provision.section_header?.trim()) {
    return provision.section_header.trim();
  }

  // 2. Extract section from document_id (most reliable context)
  const docSection = extractSectionFromDocumentId(provision.document_id);

  // 3. Determine format based on ref_number pattern

  // Pattern: table_in_XXX
  if (provision.ref_number.match(/^table_in_/i)) {
    // Try to extract specific table subject from HTML content
    const tableSubject = extractTableSubject(provision.provision_text);

    if (tableSubject && docSection) {
      return `${docSection} - ${tableSubject}`;
    } else if (tableSubject) {
      return tableSubject;
    } else if (docSection) {
      return `${docSection} - Table`;
    }

    return 'Table';
  }

  // Pattern: Provision_123 (machine-generated ID)
  if (provision.ref_number.match(/^[Pp]rovision_\d+$/)) {
    return docSection || 'Provision';
  }

  // Pattern: 4.3 or 9.29.3 or 4.3A (actual clause number)
  if (provision.ref_number.match(/^\d+(\.\d+)*[A-Z]?$/)) {
    return `Clause ${provision.ref_number}`;
  }

  // Pattern: Schedule_XXX
  if (provision.ref_number.match(/^[Ss]chedule/)) {
    return provision.ref_number.replace(/_/g, ' ');
  }

  // Fallback: Use document section or clean up ref_number
  return docSection || provision.ref_number.replace(/_/g, ' ');
}

/**
 * Get short title for compact displays (card headers)
 * Returns ONLY the specific table subject, not the section name
 *
 * Examples:
 * - "4.1 Low Density - Minimum setback" → "Minimum setback"
 * - Table with colspan title → Extract just the title
 */
export function getProvisionShortTitle(provision: ProvisionContent): string {
  // Check if provision contains table HTML (regardless of ref_number pattern)
  // Many provisions have table content but generic provision_* IDs
  if (provision.provision_text?.includes('<table')) {
    const tableSubject = extractTableSubject(provision.provision_text);
    console.log('[getProvisionShortTitle] Table HTML detected:', {
      ref_number: provision.ref_number,
      tableSubject,
      text_length: provision.provision_text.length
    });
    if (tableSubject) {
      return tableSubject;
    }
  }

  // For plain text provisions (not tables), extract first meaningful sentence
  // This helps differentiate provisions from the same section
  if (provision.provision_text && !provision.provision_text.includes('<table')) {
    // Remove HTML tags and numbered list markers
    let cleanText = provision.provision_text
      .replace(/<[^>]+>/g, '') // Remove HTML
      .replace(/^\d+\.\s+/gm, '') // Remove "1. ", "2. " at line starts
      .trim();

    // Get first sentence (up to period or newline)
    const firstSentence = cleanText.split(/[.\n]/)[0]?.trim();
    if (firstSentence && firstSentence.length > 10 && firstSentence.length < 100) {
      console.log('[getProvisionShortTitle] Using first sentence:', firstSentence);
      return firstSentence;
    }
  }

  const fullTitle = getProvisionDisplayTitle(provision);

  // If title has " - " separator, take only the part after it (the specific subject)
  if (fullTitle.includes(' - ')) {
    const parts = fullTitle.split(' - ');
    const shortTitle = parts[parts.length - 1];
    console.log('[getProvisionShortTitle] Split title:', { fullTitle, shortTitle });
    return shortTitle; // Return the last part (most specific)
  }

  // Remove "Clause " prefix for compact display
  return fullTitle.replace(/^Clause\s+/, '');
}

/**
 * Get section metadata (the broader context, not the specific title)
 * Returns the section name like "4.1 Low Density Residential Development"
 */
export function getProvisionSectionName(provision: ProvisionContent): string | null {
  // Extract section from document_id
  return extractSectionFromDocumentId(provision.document_id);
}

/**
 * Check if ref_number is a machine-generated ID (not human-readable)
 */
export function isMachineGeneratedId(refNumber: string): boolean {
  return (
    refNumber.match(/^[Pp]rovision_\d+$/) !== null ||
    refNumber.match(/^table_in_/) !== null
  );
}

/**
 * Format constraint value display for cards
 * Handles "See provision" placeholders and clause-style values
 */
export function formatConstraintValue(
  value: string | number,
  provision?: ProvisionContent
): string {
  // If value is "See provision" placeholder, use provision title
  if (typeof value === 'string' && value.toLowerCase().includes('provision')) {
    return provision ? getProvisionShortTitle(provision) : 'See provision';
  }

  // If value looks like a clause number, use provision title instead
  if (typeof value === 'string' && /^\d+(\.\d+)+[A-Z]?$/.test(value)) {
    return provision ? getProvisionShortTitle(provision) : value;
  }

  // Otherwise return as-is
  return String(value);
}
