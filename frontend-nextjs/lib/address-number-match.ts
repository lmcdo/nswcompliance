/**
 * House-number matching for the Planning Portal address search (DQ-122).
 *
 * prior-art-checked: no house-number parser existed in frontend-nextjs (grep houseNumber|streetNumber|
 * parseHouse|numberMatch); searchProperty scored candidates on postcode and street words only, so
 * '700 New South Head Rd, Rose Bay' -- an address the NSW address register does not hold -- came
 * back as 893, the Portal's top fuzzy hit.
 *
 * The rule: a candidate is the asked-for property only if its street number is the one asked for,
 * or a range containing it. Anything else is a different property and must not be served.
 */

export interface StreetNumber {
  lo: number;
  hi: number;
  /** Letter suffix of a single number ('869A' -> 'A'); null for ranges and plain numbers. */
  suffix: string | null;
}

// Words that introduce a unit/shop number in front of the street number, in either the Portal's
// form ('SE 1 795 ...', 'SHOP 1 710 ...') or a typed one ('Unit 3/12 ...').
const UNIT_PREFIXES = new Set([
  'SE', 'SHOP', 'UNIT', 'U', 'APT', 'APARTMENT', 'FLAT', 'SUITE', 'LOT', 'LEVEL', 'LVL', 'KIOSK',
  'OFFICE', 'ROOM', 'VILLA', 'TOWNHOUSE', 'CARSPACE', 'STORE',
]);

const NUMBER_TOKEN = /^(\d+)([A-Z]?)(?:-(\d+)[A-Z]?)?$/;
// A level/unit designator glued to its number: 'L1 32 PHILLIP STREET', 'G01 ...', 'B2 ...'.
const DESIGNATOR_TOKEN = /^[A-Z]{1,3}\d+[A-Z]?$/;
const isUnitWord = (tok: string): boolean =>
  UNIT_PREFIXES.has(tok.replace(/\.$/, '')) || DESIGNATOR_TOKEN.test(tok);

function parseToken(tok: string): StreetNumber | null {
  const m = tok.match(NUMBER_TOKEN);
  if (!m) return null;
  const lo = parseInt(m[1], 10);
  const hi = m[3] !== undefined ? parseInt(m[3], 10) : lo;
  if (hi < lo) return null;
  return { lo, hi, suffix: m[3] === undefined && m[2] ? m[2] : null };
}

/**
 * The street number of an address: the last number before the street name begins.
 * '5/12 Smith St' -> 12; 'SE 1 795 NEW SOUTH HEAD ROAD' -> 795; 'SHOP 24A 203-233 ...' -> 203-233.
 * Returns null when no number precedes the street name.
 */
export function parseStreetNumber(address: string | null | undefined): StreetNumber | null {
  if (!address) return null;
  const head = address.split(',')[0].toUpperCase().replace(/\//g, ' ').trim();
  let found: StreetNumber | null = null;
  for (const tok of head.split(/\s+/)) {
    const n = parseToken(tok);
    if (n) {
      found = n;
      continue;
    }
    if (isUnitWord(tok)) continue;
    break; // first word of the street name
  }
  return found;
}

/**
 * True when the candidate's street number is the one asked for.
 * A single asked number matches the same number or a candidate range containing it
 * ('680' -> '674-680'); an asked range matches only an overlapping candidate.
 * A letter suffix on either side must agree ('12' is not '12A').
 */
export function streetNumbersMatch(asked: StreetNumber, candidate: StreetNumber): boolean {
  if (asked.suffix !== candidate.suffix && asked.lo === asked.hi && candidate.lo === candidate.hi) {
    return false;
  }
  return asked.lo <= candidate.hi && candidate.lo <= asked.hi;
}

// Address-format abbreviations (Google writes 'Rd', the Portal writes 'ROAD'). Spelling only.
const STREET_TYPES: Record<string, string> = {
  ST: 'STREET', RD: 'ROAD', LN: 'LANE', AVE: 'AVENUE', AV: 'AVENUE', PDE: 'PARADE', PL: 'PLACE',
  CRES: 'CRESCENT', CR: 'CRESCENT', DR: 'DRIVE', HWY: 'HIGHWAY', CCT: 'CIRCUIT', CL: 'CLOSE',
  CT: 'COURT', TCE: 'TERRACE', BVD: 'BOULEVARD', BLVD: 'BOULEVARD', BVDE: 'BOULEVARDE',
  ESP: 'ESPLANADE', GR: 'GROVE', SQ: 'SQUARE', PKWY: 'PARKWAY', WY: 'WAY', HTS: 'HEIGHTS',
  GDNS: 'GARDENS', MEWS: 'MEWS', ROW: 'ROW', RDGE: 'RIDGE', PSGE: 'PASSAGE', PROM: 'PROMENADE',
  APP: 'APPROACH', ARC: 'ARCADE', CNR: 'CORNER', LOOP: 'LOOP', TRK: 'TRACK', WALK: 'WALK',
};
const TYPE_WORDS = new Set(Object.values(STREET_TYPES));
const normType = (t: string): string => STREET_TYPES[t] ?? t;
const isType = (t: string): boolean => TYPE_WORDS.has(normType(t));

/** Tokens after the street number: the street name onwards. */
function tokensAfterNumber(text: string): string[] {
  const toks = text.toUpperCase().replace(/\//g, ' ').replace(/,/g, ' ').trim().split(/\s+/);
  let i = 0;
  while (i < toks.length && (parseToken(toks[i]) || isUnitWord(toks[i]))) i++;
  return toks.slice(i);
}

/** The street name and type the user asked for, e.g. {name: ['NEW','SOUTH','HEAD'], type: 'ROAD'}. */
export function parseStreet(address: string): { name: string[]; type: string | null } | null {
  const hasComma = address.includes(',');
  const toks = tokensAfterNumber(hasComma ? address.split(',')[0] : address);
  if (toks.length === 0) return null;
  if (hasComma) {
    const last = toks[toks.length - 1];
    if (toks.length > 1 && isType(last)) return { name: toks.slice(0, -1), type: normType(last) };
    return { name: toks, type: null };
  }
  const at = toks.findIndex((t, i) => i > 0 && isType(t));
  return at > 0 ? { name: toks.slice(0, at), type: normType(toks[at]) } : null;
}

const postcodeOf = (a: string): string | null => a.match(/\b(\d{4})\s*$/)?.[1] ?? null;

/**
 * True when the candidate is on the street asked for: same name words, same type when both say one.
 * '14 Hunter St, Lewisham' does not match '14 ST JOHN STREET LEWISHAM'.
 */
export function streetMatches(asked: string, candidate: string): boolean {
  const want = parseStreet(asked);
  if (!want) return true; // nothing to compare
  const got = tokensAfterNumber(candidate);
  for (let i = 0; i < want.name.length; i++) {
    if (normType(got[i] ?? '') !== normType(want.name[i])) return false;
  }
  if (want.type === null) return true;
  return normType(got[want.name.length] ?? '') === want.type;
}

/**
 * Keep only candidates that are the asked-for property: matching street number, street and,
 * when the asked address gives one, postcode. An empty result means NOT FOUND -- a caller must
 * never fall back to a neighbour.
 */
export function filterToAskedProperty<T extends { address: string }>(asked: string, candidates: T[]): T[] {
  const wanted = parseStreetNumber(asked);
  const askedPostcode = postcodeOf(asked);
  return candidates.filter((c) => {
    if (wanted) {
      const got = parseStreetNumber(c.address);
      if (got === null || !streetNumbersMatch(wanted, got)) return false;
    }
    if (askedPostcode) {
      const pc = postcodeOf(c.address);
      if (pc !== null && pc !== askedPostcode) return false;
    }
    return streetMatches(asked, c.address);
  });
}
