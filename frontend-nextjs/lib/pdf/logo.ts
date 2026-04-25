/**
 * Reads public/plotdetect-logo.png once and caches it as a base64 string.
 * Used by PDF generate routes to embed the logo in reports.
 */

import fs from 'fs';
import path from 'path';

let _cache: string | null | undefined = undefined;

export function getLogoBase64(): string | null {
  if (_cache !== undefined) return _cache;
  try {
    const p = path.join(process.cwd(), 'public', 'plotdetect-logo.png');
    _cache = fs.readFileSync(p).toString('base64');
    return _cache;
  } catch {
    _cache = null;
    return null;
  }
}
