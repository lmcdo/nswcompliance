/**
 * HTML Sanitization Utility
 *
 * Use this to sanitize HTML before rendering with dangerouslySetInnerHTML.
 * Prevents XSS attacks from malicious content in the database.
 */

import DOMPurify from 'isomorphic-dompurify';

// Allowed tags for regulatory/legal content (tables, formatting)
const ALLOWED_TAGS = [
  // Tables
  'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption', 'colgroup', 'col',
  // Text formatting
  'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'sub', 'sup', 'mark',
  // Lists
  'ul', 'ol', 'li', 'dl', 'dt', 'dd',
  // Structure
  'div', 'span', 'section', 'article', 'header', 'footer',
  // Headings
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  // Other
  'blockquote', 'pre', 'code', 'hr',
];

// Allowed attributes (no event handlers, no javascript: URLs)
const ALLOWED_ATTR = [
  'class', 'id', 'style',
  'colspan', 'rowspan', 'scope', 'headers',
  'title', 'lang', 'dir',
];

/**
 * Sanitize HTML content for safe rendering.
 *
 * @param html - Raw HTML string from database
 * @returns Sanitized HTML string safe for dangerouslySetInnerHTML
 *
 * @example
 * ```tsx
 * import { sanitizeHTML } from '@/lib/sanitize';
 *
 * <div dangerouslySetInnerHTML={{ __html: sanitizeHTML(provision.text) }} />
 * ```
 */
export function sanitizeHTML(html: string): string {
  if (!html) return '';

  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false,
    SAFE_FOR_TEMPLATES: true,
  });
}

/**
 * Sanitize HTML with stricter rules (text-only, no tables).
 * Use for short text snippets where complex formatting isn't needed.
 */
export function sanitizeText(html: string): string {
  if (!html) return '';

  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'b', 'em', 'i'],
    ALLOWED_ATTR: [],
    ALLOW_DATA_ATTR: false,
  });
}

/**
 * Strip all HTML and return plain text.
 */
export function stripHTML(html: string): string {
  if (!html) return '';

  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [],
    ALLOWED_ATTR: [],
  });
}
