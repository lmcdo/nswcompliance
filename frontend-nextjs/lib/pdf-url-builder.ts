/**
 * PDF URL Builder - Centralized PDF Image URL Generation
 *
 * Manages URLs for all PDF page images stored in R2 bucket.
 * Supports absolute (R2) and relative (Next.js public) paths.
 *
 * @see https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev
 */

/**
 * R2 Cloudflare Storage Base URL
 * Can be overridden via environment variable for staging/production
 */
const R2_BASE_URL =
  process.env.NEXT_PUBLIC_R2_BASE_URL ||
  'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev';

/**
 * Validate R2 base URL format at module load
 */
if (typeof window === 'undefined') {
  // Server-side validation only
  if (!R2_BASE_URL.startsWith('http')) {
    console.warn('[PDF URL Builder] R2_BASE_URL should be an absolute URL:', R2_BASE_URL);
  }
}

/**
 * SEPP PDF document identifiers and their storage paths
 */
const SEPP_PDF_PATHS = {
  'sustainable_buildings': {
    folder: 'sepp-sustainable-buildings',
    namePattern: (page: number) => `sepp-sustainable-buildings_page_${page}.png`,
    useFullUrl: true,
  },
  'housing': {
    folder: 'sepp-housing',
    namePattern: (page: number) => `sepp-housing_page_${page}.png`,
    useFullUrl: false, // Relative path
  },
  'housing_2021': {
    folder: 'sepp-housing-2021',
    namePattern: (page: number, description?: string) =>
      description ? `page-${page}_${description}.png` : `page-${page}.png`,
    useFullUrl: true,
  },
  'resilience_hazards': {
    folder: 'sepp-resilience-hazards',
    namePattern: (page: number) => `sepp-resilience-hazards_page_${page}.png`,
    useFullUrl: true,
  },
  'exempt_complying': {
    folder: 'sepp-exempt-complying',
    namePattern: (page: number) => `page_${page}.png`,
    useFullUrl: true,
  },
} as const;

export type SeppPdfId = keyof typeof SEPP_PDF_PATHS;

/**
 * Get PDF page image URL for SEPP documents
 *
 * @param seppId - SEPP document identifier (e.g., 'sustainable_buildings', 'housing')
 * @param page - Page number
 * @param description - Optional description suffix for special pages (e.g., 'infill_affordable')
 * @returns Full or relative URL to PDF page image
 *
 * @example
 * getSeppPdfUrl('sustainable_buildings', 11)
 * // => 'https://...r2.dev/pdf-pages/sepp-sustainable-buildings/sepp-sustainable-buildings_page_11.png'
 *
 * @example
 * getSeppPdfUrl('housing', 32)
 * // => '/pdf-pages/sepp-housing/sepp-housing_page_32.png'
 *
 * @example
 * getSeppPdfUrl('housing_2021', 35, 'infill_affordable')
 * // => 'https://...r2.dev/pdf-pages/sepp-housing-2021/page-35_infill_affordable.png'
 */
export function getSeppPdfUrl(
  seppId: SeppPdfId,
  page: number,
  description?: string
): string {
  const config = SEPP_PDF_PATHS[seppId];

  if (!config) {
    console.error(`[PDF URL Builder] Unknown SEPP ID: ${seppId}`);
    return '#';
  }

  const fileName = config.namePattern(page, description);
  const relativePath = `/pdf-pages/${config.folder}/${fileName}`;

  return config.useFullUrl
    ? `${R2_BASE_URL}${relativePath}`
    : relativePath;
}

/**
 * Get PDF page image URL for Apartment Design Guide (ADG)
 *
 * @param page - Page number in ADG Part 3
 * @returns Relative URL to ADG PDF page image
 *
 * @example
 * getAdgPdfUrl(42)
 * // => '/pdf-pages/adg-part3/page-42.png'
 */
export function getAdgPdfUrl(page: number): string {
  return `/pdf-pages/adg-part3/page-${page}.png`;
}

/**
 * Get PDF page image URL for DCP documents (former councils)
 *
 * @param council - Former council name (e.g., 'marrickville', 'leichhardt', 'ashfield')
 * @param page - Page number in DCP
 * @returns Full URL to DCP PDF page image
 *
 * @example
 * getDcpPdfUrl('marrickville', 145)
 * // => 'https://...r2.dev/pdf-pages/marrickville-dcp/page-145.png'
 */
export function getDcpPdfUrl(council: string, page: number): string {
  return `${R2_BASE_URL}/pdf-pages/${council}-dcp/page-${page}.png`;
}

/**
 * Get PDF page image URL for Heritage Conservation Area (HCA) documents
 *
 * @param council - Former council name
 * @param hcaSlug - HCA slug identifier (e.g., 'hca_18')
 * @param page - Page number
 * @returns Full URL to HCA PDF page image
 *
 * @example
 * getHcaPdfUrl('marrickville', 'hca_18', 5)
 * // => 'https://...r2.dev/pdf-pages/marrickville-dcp/hca_18/page-5.png'
 */
export function getHcaPdfUrl(council: string, hcaSlug: string, page: number): string {
  return `${R2_BASE_URL}/pdf-pages/${council}-dcp/${hcaSlug}/page-${page}.png`;
}

/**
 * Get base R2 URL (useful for debugging or custom paths)
 *
 * @returns R2 base URL (with or without trailing slash normalized)
 */
export function getR2BaseUrl(): string {
  return R2_BASE_URL.replace(/\/$/, ''); // Remove trailing slash if present
}

/**
 * Build custom PDF URL for non-standard documents
 *
 * @param relativePath - Path relative to /pdf-pages/ (e.g., 'custom-doc/page-1.png')
 * @param useFullUrl - Whether to prepend R2 base URL (default: true)
 * @returns PDF page image URL
 *
 * @example
 * buildCustomPdfUrl('pattern-book/section-2/page-10.png')
 * // => 'https://...r2.dev/pdf-pages/pattern-book/section-2/page-10.png'
 */
export function buildCustomPdfUrl(relativePath: string, useFullUrl = true): string {
  // Ensure relativePath doesn't start with /pdf-pages/ or leading slash
  const cleanPath = relativePath
    .replace(/^\/pdf-pages\//, '')
    .replace(/^\//, '');

  const fullPath = `/pdf-pages/${cleanPath}`;
  return useFullUrl ? `${R2_BASE_URL}${fullPath}` : fullPath;
}

/**
 * Validate PDF URL is accessible (client-side only)
 * Useful for debugging broken image links
 *
 * @param url - Full or relative PDF URL
 * @returns Promise<boolean> - True if URL returns 200 status
 */
export async function validatePdfUrl(url: string): Promise<boolean> {
  if (typeof window === 'undefined') {
    console.warn('[PDF URL Builder] validatePdfUrl() should only be called client-side');
    return false;
  }

  try {
    const response = await fetch(url, { method: 'HEAD' });
    return response.ok;
  } catch (error) {
    console.error(`[PDF URL Builder] Failed to validate URL: ${url}`, error);
    return false;
  }
}

/**
 * Type-safe PDF URL builder options
 */
export interface PdfUrlOptions {
  /** SEPP document ID */
  seppId?: SeppPdfId;
  /** ADG page flag */
  isAdg?: boolean;
  /** DCP council name */
  dcpCouncil?: string;
  /** HCA slug for heritage documents */
  hcaSlug?: string;
  /** Page number */
  page: number;
  /** Optional description suffix */
  description?: string;
}

/**
 * Generic PDF URL builder with options object
 * Useful when PDF type is determined dynamically
 *
 * @param options - PDF URL options
 * @returns PDF page image URL
 */
export function buildPdfUrl(options: PdfUrlOptions): string {
  if (options.seppId) {
    return getSeppPdfUrl(options.seppId, options.page, options.description);
  }
  if (options.isAdg) {
    return getAdgPdfUrl(options.page);
  }
  if (options.hcaSlug && options.dcpCouncil) {
    return getHcaPdfUrl(options.dcpCouncil, options.hcaSlug, options.page);
  }
  if (options.dcpCouncil) {
    return getDcpPdfUrl(options.dcpCouncil, options.page);
  }

  console.error('[PDF URL Builder] Invalid options provided:', options);
  return '#';
}
