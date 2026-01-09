/**
 * Get the full URL for PDF page images
 * In production (Vercel): prefixes Cloudflare R2 URL
 * In development: returns relative path (served from local public folder)
 *
 * Set NEXT_PUBLIC_R2_URL env var to override the R2 bucket URL
 */

// R2 public URL - can be overridden via env var
const R2_PUBLIC_URL = process.env.NEXT_PUBLIC_R2_URL || 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev';

export function getPdfImageUrl(relativePath: string | undefined | null): string | null {
  if (!relativePath) return null;

  // If already an absolute URL (starts with http:// or https://), return as-is
  if (relativePath.startsWith('http://') || relativePath.startsWith('https://')) {
    return relativePath;
  }

  // In production (Vercel or custom domain), prefix with R2 URL
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    // Production domains
    if (hostname.includes('vercel.app') ||
        hostname.includes('plotdetect.com.au') ||
        hostname !== 'localhost') {
      return `${R2_PUBLIC_URL}${relativePath}`;
    }
  }

  // Also check for VERCEL env var (server-side)
  if (process.env.VERCEL === '1' || process.env.NODE_ENV === 'production') {
    return `${R2_PUBLIC_URL}${relativePath}`;
  }

  // In development (localhost), use relative path (served from public folder)
  return relativePath;
}
