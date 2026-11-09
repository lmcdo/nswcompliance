/**
 * A clause that says "comply with Table X" must show Table X. Real stored text (production, 2026-11-09): Hornsby DCP Part 3,
 * clause 3.1.2 a (id 262143, page 9) names Table 3.1.2-a; the table's rows were extracted onto the end of clause 3.1.2 h
 * (id 262150, same page), after a paragraph about dual occupancies. Before this, the clause was judged complete (the digits
 * in "3.1.2-a" read as a figure) and, when it did get a follow-on, the next three clauses by id were shown, not the table.
 */
import { needsFollowOn, showsNextClauses, tablePart, tableFor, tableRows } from '@/lib/plan-brief';

const HORNSBY_3_1_2_A = '# 3.1.2 a Prescriptive Measures\n\na. The minimum setback of all buildings and structures to the boundaries of the site should comply with Table 3.1.2-a.';
const HORNSBY_3_1_2_H = [
  '# 3.1.2 h Prescriptive Measures',
  '',
  'h. An attached dual occupancy on a corner lot should have both dwellings address the primary road frontage (see Figure 3.1-f) whereas for a detached dual occupancy the secondary road frontage becomes the primary road frontage for the second dwelling (see Figure 3.1-g). For detached:',
  'i. The dwelling fronting the main Primary Road should have a minimum setback with the secondary road of 3m (see Figure 3.1-g).',
  'i. Detached dual occupancies (either side by side or one behind the other) should be separated by a minimum distance of 3m.',
  'Boundary setback | Minimum building setback',
  'Front boundary (Primary frontage) Dwellings and detached dual occupancies | 6m to local roads and 9m to designated roads, except for the following ▪ On local roads, where an existing setback of 7.6m or greater exists, it may be necessary to conform to this setback to maintain the streetscape character, ▪ 3m Brooklyn Road, Brooklyn and ▪ 9m to roads in Cherrybrook',
  'Attached dual occupancy | 7.6m (9m if designated road or in Cherrybrook)',
  'Secondary boundary (on corner lots) | 3m',
  'Side boundary | Up to 1 storey = 0.9m 2 storey element = 1.5m',
  'Rear boundary | Up to 1 storey = 3m 2 storey element = 8m',
  'Table 3.1.2-a: Minimum boundary setbacks for dwellings and dual occupancies',
].join('\n');

describe('needsFollowOn: a table name is not a figure', () => {
  test('Hornsby 3.1.2 a names a table and states no figure of its own', () => {
    expect(needsFollowOn(HORNSBY_3_1_2_A)).toBe(true);
  });
  test('a clause that states its own figure and names a table is still complete', () => {
    expect(needsFollowOn('# 3.2 x\n\nThe minimum front setback is 6 metres (Table 3.1 gives the exceptions to this rule).')).toBe(false);
  });
  test('a long clause with no table and no figure is unchanged (complete)', () => {
    expect(needsFollowOn('# 4 x\n\nBuildings are to be sited so that they are compatible with the character of the street and neighbours nearby.')).toBe(false);
  });
});

describe('showsNextClauses: the old rule, kept for the no-table fallback', () => {
  test('a clause new to needsFollowOn (names a table, no figure) does not show unrelated next clauses', () => {
    expect(needsFollowOn(HORNSBY_3_1_2_A)).toBe(true);
    expect(showsNextClauses(HORNSBY_3_1_2_A)).toBe(false);
  });
  test('an opener still shows the clauses that follow', () => {
    expect(showsNextClauses('# 5 x\n\nThe requirements are as follows:')).toBe(true);
    expect(showsNextClauses('# 5 x\n\nA minimum of:')).toBe(true);
  });
  test('a short fragment with no figure still shows the clauses that follow', () => {
    expect(showsNextClauses('# 5 x\n\nFront setback')).toBe(true);
  });
});

describe('tablePart', () => {
  test('returns the rows and the caption of the table at the end of a prose clause, as printed', () => {
    const part = tablePart(HORNSBY_3_1_2_H);
    expect(part).not.toBeNull();
    expect(part!.startsWith('Boundary setback | Minimum building setback')).toBe(true);
    expect(part!.endsWith('Table 3.1.2-a: Minimum boundary setbacks for dwellings and dual occupancies')).toBe(true);
    expect(part).toContain('Side boundary | Up to 1 storey = 0.9m 2 storey element = 1.5m');
    expect(part).not.toContain('dual occupancy on a corner lot');   // the prose before the table is not part of it
    expect(HORNSBY_3_1_2_H).toContain(part!);                       // a verbatim slice, never a rewrite
  });
  test('the slice reads as a table in the page', () => {
    expect(tableRows(tablePart(HORNSBY_3_1_2_H)!)).not.toBeNull();
  });
  test('a caption printed above the rows is kept', () => {
    const t = 'Intro text that is long enough to be prose.\nTable 6.2.1 – Minimum car parking rates\nUse | Spaces\nDwelling house | 2\nSecondary dwelling | 1';
    expect(tablePart(t)).toBe('Table 6.2.1 – Minimum car parking rates\nUse | Spaces\nDwelling house | 2\nSecondary dwelling | 1');
  });
  test('a wrapped continuation of the last row is kept, up to the caption', () => {
    const t = '# 1 x\n\nProse.\nBoundary | Setback\nRear boundary | 3m except:\n8m for two-storey elements\nTable 1.1-a: Rear setbacks';
    expect(tablePart(t)).toBe('Boundary | Setback\nRear boundary | 3m except:\n8m for two-storey elements\nTable 1.1-a: Rear setbacks');
  });
  test('text after the rows with no caption closing them is NOT served as a table (could be a wrapped cell)', () => {
    expect(tablePart('# 1 x\n\nBoundary | Setback\nFront | 6m\nRear | 3m\nThe rear setback may be reduced where the lot backs onto a reserve.')).toBeNull();
  });
  test('trailing blank lines after the rows are fine', () => {
    expect(tablePart('# 1 x\n\nBoundary | Setback\nFront | 6m\n\n')).toBe('Boundary | Setback\nFront | 6m');
  });
  test('no table -> null', () => {
    expect(tablePart('# 1 x\n\nPlain prose with no rows at all.')).toBeNull();
  });
  test('a single "a | b" line is not a table', () => {
    expect(tablePart('# 1 x\n\nSome prose.\nSetback | 6m')).toBeNull();
  });
  test('empty text -> null', () => {
    expect(tablePart('')).toBeNull();
  });
});

describe('tableFor: pick the table the clause names', () => {
  const t312a = 'Boundary setback | Minimum building setback\nSide boundary | 0.9m\nTable 3.1.2-a: Minimum boundary setbacks';
  const t313a = 'Lot size | Landscaped area\nUnder 450 | 45%\nTable 3.1.3-a: Minimum landscaped area';
  test('a named table is matched by its caption', () => {
    expect(tableFor(HORNSBY_3_1_2_A, [t313a, t312a])).toBe(t312a);
  });
  test('a named table with no matching caption is NOT replaced by some other table', () => {
    expect(tableFor('# x\n\nShould comply with Table 9.9-z.', [t312a, t313a])).toBeNull();
  });
  test('"the following table" takes the first table that follows', () => {
    expect(tableFor('# x\n\nThe setbacks are as set out in the following table:', [t313a, t312a])).toBe(t313a);
  });
  test('a clause that mentions "table" only in passing does not take whatever table follows', () => {
    expect(tableFor('# x\n\nNotes: deep soil zones are areas of soil. A table is not provided for this item.', [t313a])).toBeNull();
  });
  test('"the table above" is not followed: only later tables are on offer, so it gets nothing', () => {
    expect(tableFor('# x\n\nSetbacks are shown in the table above.', [t313a])).toBeNull();
  });
  test('table 3.1-a is not table 13.1-a (exact identifier, not a substring)', () => {
    const t131 = 'Lot | Area\nA | 1\nTable 13.1-a: Something else';
    const t31 = 'Lot | Area\nB | 2\nTable 3.1-a: The one named';
    expect(tableFor('# x\n\nShould comply with Table 3.1-a.', [t131, t31])).toBe(t31);
    expect(tableFor('# x\n\nShould comply with Table 3.1-a.', [t131])).toBeNull();
  });
  test('a letter-led identifier (Table A2.1.1) matches its caption', () => {
    const a = 'Use | Bin\nHouse | 1\nTable A2.1.1 - Bin storage';
    expect(tableFor('# x\n\nSee Table A2.1.1.', [t313a, a])).toBe(a);
  });
  test('"table below" is a pointer, not an identifier', () => {
    expect(tableFor('# x\n\nLandscaped area complies with the table below:', [t313a])).toBe(t313a);
  });
  test('no tables -> null', () => {
    expect(tableFor(HORNSBY_3_1_2_A, [])).toBeNull();
  });
  test('a trailing full stop in the clause is not part of the table name', () => {
    expect(tableFor('# x\n\nSee Table 3.1.3-a.', [t312a, t313a])).toBe(t313a);
  });
});
