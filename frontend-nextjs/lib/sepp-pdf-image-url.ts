/**
 * Construct PDF page image URLs for SEPP provisions
 *
 * Usage:
 *   const url = getSeppPdfImageUrl('Housing', 'State Environmental Planning Policy (Housing) 2021.pdf', 42)
 *   // Returns: /pdf-pages/sepp-housing-2021/sepp-housing-2021_page_42.png
 */

import { getPdfImageUrl } from './pdf-image-url';

/**
 * Slugify SEPP document name to match extraction script output
 */
function slugifySeppDocument(pdfName: string): string {
  // Remove .pdf extension and NSW Legislation suffix
  let name = pdfName
    .replace('.pdf', '')
    .replace(' - NSW Legislation', '');

  // Extract year (e.g., "2021")
  const yearMatch = name.match(/\b(20\d{2})\b/);
  const year = yearMatch ? yearMatch[1] : '';

  // Extract SEPP type from parentheses
  const typeMatch = name.match(/\((.*?)\)/);
  let seppType = typeMatch
    ? typeMatch[1]
    : name.replace('State Environmental Planning Policy', '').trim();

  // Clean and slugify
  let slug = seppType.toLowerCase();
  slug = slug.replace(/ and /g, '-');
  slug = slug.replace(/ /g, '-');
  slug = slug.replace(/[^a-z0-9-]/g, '');

  // Add year if present
  if (year) {
    return `sepp-${slug}-${year}`;
  }
  return `sepp-${slug}`;
}

/**
 * Get PDF page image URL for a SEPP provision
 *
 * @param documentName - Name of the SEPP document (from documents.pdf_name)
 * @param pageNumber - Page number in the PDF (from regulatory_provisions.pdf_page)
 * @returns Full URL to PDF page image, or null if inputs invalid
 *
 * @example
 * // Housing SEPP page 42
 * getSeppPdfImageUrl('State Environmental Planning Policy (Housing) 2021.pdf', 42)
 * // => 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-housing-2021/sepp-housing-2021_page_42.png'
 *
 * @example
 * // Exempt & Complying SEPP page 152
 * getSeppPdfImageUrl('State Environmental Planning Policy (Exempt and Complying Development Codes) 2008.pdf', 152)
 * // => 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-exempt-complying-2008/sepp-exempt-complying-2008_page_152.png'
 */
export function getSeppPdfImageUrl(
  documentName: string | null | undefined,
  pageNumber: number | null | undefined
): string | null {
  if (!documentName || !pageNumber) {
    return null;
  }

  const slug = slugifySeppDocument(documentName);
  const relativePath = `/pdf-pages/${slug}/${slug}_page_${pageNumber}.png`;

  return getPdfImageUrl(relativePath);
}

/**
 * Get label for PDF page modal
 *
 * @example
 * getSeppPdfLabel('Housing', 42)
 * // => 'Housing SEPP - Page 42'
 */
export function getSeppPdfLabel(
  seppType: string,
  pageNumber: number
): string {
  return `${seppType} SEPP - Page ${pageNumber}`;
}

/**
 * Extract SEPP type from document name for display
 *
 * @example
 * getSeppType('State Environmental Planning Policy (Housing) 2021.pdf')
 * // => 'Housing'
 */
export function getSeppType(documentName: string): string {
  const match = documentName.match(/\((.*?)\)/);
  if (match) {
    // Shorten common long names
    const type = match[1];
    if (type.includes('Exempt and Complying')) return 'Exempt & Complying';
    if (type.includes('Transport and Infrastructure')) return 'Transport & Infrastructure';
    if (type.includes('Biodiversity and Conservation')) return 'Biodiversity & Conservation';
    if (type.includes('Industry and Employment')) return 'Industry & Employment';
    return type;
  }
  return 'SEPP';
}
