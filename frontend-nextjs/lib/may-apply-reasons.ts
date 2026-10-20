/**
 * Plain-language reasons an area's rules "may apply" to a property, and suburb helpers.
 *
 * prior-art-checked: extends the council-wide not-covered notice (lib/not-covered.ts) with a
 * per-suburb block; no existing module maps a reason code to text or normalises a suburb.
 */
import { parseStreet } from '@/lib/address-number-match';

export const MAY_APPLY_REASONS: Record<string, string> = {
  MAP_NOT_PUBLISHED: "The council's plan refers to a map of this area, but the map is not in the published plan.",
  DRAWING_NOT_MATCHED: 'The plan shows this area only on a drawing we could not match to real streets.',
  WORDS_ONLY: 'The plan describes this area in words only, with no map.',
  SOUND_AREA_MAP: 'The plan shows this area only on its noise (sound category) maps, which we have not mapped.',
  LOT_LIST_UNPROVEN: 'The plan lists the lots in this area, but we could not match that list to the official lot records.',
};

/** The text for a reason code, or null when the code is unknown (callers show nothing, not a guess). */
export function reasonText(code: string | null | undefined): string | null {
  return code && Object.prototype.hasOwnProperty.call(MAY_APPLY_REASONS, code) ? MAY_APPLY_REASONS[code] : null;
}

/** Uppercase, trim, collapse spaces, drop "NSW" and a 4-digit postcode. */
export function normaliseSuburb(s: string | null | undefined): string {
  if (!s) return '';
  return s
    .toUpperCase()
    .replace(/,/g, ' ')
    .split(/\s+/)
    .filter((t) => t && t !== 'NSW' && t !== 'AUSTRALIA' && !/^\d{4}$/.test(t))
    .join(' ');
}

const UNIT_WORDS = new Set(['UNIT', 'APT', 'APARTMENT', 'SHOP', 'LEVEL', 'SUITE', 'LOT']);

/** The suburb of an address ("12 Smith St, Winston Hills NSW 2153" -> "WINSTON HILLS"), or '' when none can be read. */
export function suburbFromAddress(address: string | null | undefined): string {
  if (!address) return '';
  const parts = address.split(',').map((p) => normaliseSuburb(p)).filter(Boolean);
  // With commas the suburb is the LAST part that is not just state/postcode ("Unit 3, 12 Smith St, Winston Hills NSW
  // 2153" -> "WINSTON HILLS"); normaliseSuburb already drops "NSW" and the postcode (Sol, 2026-10-20).
  // A last part that still starts with a number or unit word holds the street too ("Unit 3, 12 Smith Street Winston
  // Hills NSW 2153"): read the suburb from after the street in that part (Sol, 2026-10-21).
  let rest = address;
  if (address.includes(',')) {
    if (parts.length <= 1) return '';
    const last = parts[parts.length - 1];
    const first = last.split(' ')[0];
    if (!/\d/.test(first) && !UNIT_WORDS.has(first)) return last;
    rest = last;
  }
  const street = parseStreet(rest);
  if (!street) return '';
  const toks = rest.toUpperCase().replace(/\//g, ' ').trim().split(/\s+/);
  let i = 0;
  // Any token with a digit is a unit or house number ("12", "12A", "G03"), never part of a street name.
  while (i < toks.length && (/\d/.test(toks[i]) || UNIT_WORDS.has(toks[i]))) i++;
  const nameTokens = street.name.length;  // parseStreet returns the name as tokens (Sol: tokens, not characters)
  return normaliseSuburb(toks.slice(i + nameTokens + (street.type ? 1 : 0)).join(' '));
}
