/**
 * One council key for every lookup in the rules route (lib/council-key.ts).
 *
 * The inputs below are the exact former_council values the assessment page sent for the 30
 * addresses of the served-answer audit (2026-10-11). Each must map to the key its rules and
 * PDFs are stored under. Before this, "City of Sydney" got 0 PDF links and
 * "city_of_parramatta" got 0 rules.
 */
import * as fs from 'fs';
import * as path from 'path';
import { councilKey } from '@/lib/council-key';

describe('councilKey', () => {
  it.each([
    ['Ashfield', 'ashfield'],
    ['Leichhardt', 'leichhardt'],
    ['Marrickville', 'marrickville'],
    ['City of Sydney', 'city_of_sydney'],
    ['city_of_parramatta', 'parramatta'],
    ['canterbury_bankstown', 'canterbury_bankstown'],
    ['ku_ring_gai', 'ku_ring_gai'],
    ['Ku-ring-gai', 'ku_ring_gai'],
    ['northern_beaches', 'northern_beaches'],
    ['campbelltown', 'campbelltown'],
    ['waverley', 'waverley'],
    ['wollongong', 'wollongong'],
    ['woollahra', 'woollahra'],
    ['sydney', 'city_of_sydney'],
    ['INNER WEST', 'inner_west'],
  ])('%s -> %s', (input, key) => {
    expect(councilKey(input)).toBe(key);
  });

  it('returns null for nothing, so no lookup runs on an empty name', () => {
    expect(councilKey(undefined)).toBeNull();
    expect(councilKey('')).toBeNull();
    expect(councilKey('  ')).toBeNull();
  });
});

describe('the rules route finds councils by key, never by a document-name pattern', () => {
  const src = fs.readFileSync(
    path.join(__dirname, '../../app/api/provisions/for-property/route.ts'), 'utf8');

  it('has no document_id pattern match left', () => {
    // A name pattern matched Marrickville's "Parramatta Rd" precinct for Parramatta houses,
    // and every "Inner West Ashfield DCP" document for the inner_west fallback.
    expect(src).not.toMatch(/document_id ILIKE/);
  });

  it('uses councilKey for the rules, the PDF registry and the precinct warning', () => {
    expect(src).toMatch(/source_council = \$\$\{paramIndex\+\+\}`;\s*params\.push\(councilKey\(filters\.former_council\)\)/);
    expect(src).toMatch(/const councilSlug = councilKey\(filters\.former_council\)/);
    expect(src).toMatch(/const fc = councilKey\(filters\.former_council\)/);
  });
});
