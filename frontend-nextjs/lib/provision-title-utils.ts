/**
 * Provision Title Utilities
 * Helper functions for displaying provision titles and metadata
 */

/**
 * Check if a provision ID is machine-generated (vs human-readable)
 */
export function isMachineGeneratedId(id: string | number): boolean {
  if (typeof id === 'number') return true;

  // Machine-generated IDs are typically all numeric or UUID-like
  return /^\d+$/.test(id) || /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
}

/**
 * Get display title for a provision
 * Prioritizes human-readable identifiers over machine IDs
 */
export function getProvisionDisplayTitle(provision: {
  ref_number?: string;
  section_header?: string;
  provision_text?: string;
  id?: string | number;
  document_id?: string;
}): string {
  // Priority 1: ref_number (e.g., "4.3", "Part A")
  if (provision.ref_number && provision.ref_number.trim() !== '') {
    return provision.ref_number;
  }

  // Priority 2: section_header
  if (provision.section_header && provision.section_header.trim() !== '') {
    return provision.section_header;
  }

  // Priority 3: First 50 chars of provision text
  if (provision.provision_text) {
    const text = provision.provision_text.trim();
    if (text.length > 0) {
      return text.length > 50 ? `${text.substring(0, 50)}...` : text;
    }
  }

  // Fallback: ID
  return `Provision ${provision.id || 'Unknown'}`;
}

/**
 * Get short title for a provision (for cards/compact views)
 */
export function getProvisionShortTitle(provision: {
  ref_number?: string;
  section_header?: string;
  id?: string | number;
}): string {
  if (provision.ref_number && provision.ref_number.trim() !== '') {
    return provision.ref_number;
  }

  if (provision.section_header) {
    const header = provision.section_header.trim();
    // Truncate long section headers
    return header.length > 30 ? `${header.substring(0, 30)}...` : header;
  }

  return `#${provision.id || '?'}`;
}

/**
 * Get section name from provision metadata
 */
export function getProvisionSectionName(provision: {
  section_header?: string;
  part_name?: string;
  category?: string;
}): string {
  if (provision.section_header && provision.section_header.trim() !== '') {
    return provision.section_header;
  }

  if (provision.part_name && provision.part_name.trim() !== '') {
    return provision.part_name;
  }

  if (provision.category && provision.category.trim() !== '') {
    return provision.category;
  }

  return 'General Provisions';
}

/**
 * Format constraint value for display
 */
export function formatConstraintValue(
  value: string | number | null | undefined,
  unit?: string
): string {
  if (value === null || value === undefined || value === '') {
    return 'Not specified';
  }

  const numericValue = typeof value === 'number' ? value : parseFloat(value as string);

  if (isNaN(numericValue)) {
    return String(value);
  }

  // Format numeric values
  const formatted = numericValue % 1 === 0
    ? numericValue.toString()
    : numericValue.toFixed(2);

  // Add unit if provided
  return unit ? `${formatted} ${unit}` : formatted;
}

/**
 * Extract provision reference from text (e.g., "See clause 4.3" → "4.3")
 */
export function extractProvisionReference(text: string): string | null {
  // Common patterns: "clause 4.3", "section 2.1", "part A", etc.
  const patterns = [
    /(?:clause|section|part)\s+([A-Z0-9.]+)/i,
    /\b([0-9]+\.[0-9]+(?:\.[0-9]+)?)\b/, // Numeric references like 4.3 or 4.3.1
    /\bPart\s+([A-Z])\b/i, // Part A, Part B, etc.
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      return match[1];
    }
  }

  return null;
}

/**
 * Determine provision type from metadata
 */
export function getProvisionType(provision: {
  document_id?: string;
  provision_type?: string;
  section_header?: string;
}): 'LEP' | 'DCP' | 'SEPP' | 'Unknown' {
  // Check explicit provision_type field
  if (provision.provision_type) {
    const type = provision.provision_type.toUpperCase();
    if (type.includes('LEP')) return 'LEP';
    if (type.includes('DCP')) return 'DCP';
    if (type.includes('SEPP')) return 'SEPP';
  }

  // Check document_id
  if (provision.document_id) {
    const docId = provision.document_id.toUpperCase();
    if (docId.includes('LEP')) return 'LEP';
    if (docId.includes('DCP')) return 'DCP';
    if (docId.includes('SEPP')) return 'SEPP';
  }

  // Check section_header
  if (provision.section_header) {
    const header = provision.section_header.toUpperCase();
    if (header.includes('LEP')) return 'LEP';
    if (header.includes('DCP')) return 'DCP';
    if (header.includes('SEPP')) return 'SEPP';
  }

  return 'Unknown';
}
