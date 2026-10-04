/**
 * DQ-125: the extractor's HTML tables are shown as tables, never as literal tags, and no value is lost.
 * Both fixtures are served rules, copied from regulatory_provisions on 2026-10-04.
 */
import { hasProvisionTable, splitProvisionTables, provisionTablesToPlainText } from '@/lib/provision-tables';

// Waverley DCP 2022, page 189: a side-setback table with empty padding columns.
const WAVERLEY = `Side setbacks are to comply with Table 1.

<table>
<thead>
<tr>
  <th></th>
  <th>Location of proposed works</th>
  <th></th>
  <th></th>
  <th>Side setback (min.)</th>
  <th></th>
</tr>
</thead>
<tbody>
<tr>
  <td>Ground Floor</td>
  <td></td>
  <td></td>
  <td>0.9m</td>
  <td></td>
  <td></td>
</tr>
<tr>
  <td>Second Floor</td>
  <td></td>
  <td></td>
  <td>1.5m</td>
  <td></td>
  <td></td>
</tr>
</tbody>
</table>

**Table 2** (Page 189)`;

// A statewide instrument's height table: no thead, one line, entity in a cell.
const DULWICH = 'Heights:<table><tr><td> Part of Dulwich Grove land</td><td> Maximum building height</td></tr>' +
  '<tr><td>Lot 14, Section 4, DP 932 &amp; Lot 4, DP 540366</td><td>9.5m</td></tr><tr><td></td><td>20m</td></tr></table>';

describe('splitProvisionTables', () => {
  it('keeps the prose before and after, in order', () => {
    const segs = splitProvisionTables(WAVERLEY);
    expect(segs.map((s) => s.kind)).toEqual(['text', 'table', 'text']);
    expect((segs[0] as any).text).toContain('Side setbacks are to comply');
    expect((segs[2] as any).text).toContain('Table 2');
  });

  it('keeps every value and drops only columns empty in every row', () => {
    const t = (splitProvisionTables(WAVERLEY)[1] as any).table;
    expect(t.head).toEqual([['', 'Location of proposed works', '', 'Side setback (min.)']]);
    expect(t.body).toEqual([['Ground Floor', '', '0.9m', ''], ['Second Floor', '', '1.5m', '']]);
  });

  it('reads a table with no thead, and decodes entities', () => {
    const t = (splitProvisionTables(DULWICH)[1] as any).table;
    expect(t.head).toEqual([]);
    expect(t.body[1]).toEqual(['Lot 14, Section 4, DP 932 & Lot 4, DP 540366', '9.5m']);
    expect(t.body[2]).toEqual(['', '20m']);
  });

  it('text with no table is one unchanged segment', () => {
    expect(splitProvisionTables('C1 Height 9.5m')).toEqual([{ kind: 'text', text: 'C1 Height 9.5m' }]);
    expect(hasProvisionTable('C1 Height 9.5m')).toBe(false);
  });

  it('an unclosed <table> is not parsed (the DQ-125 check counts these)', () => {
    expect(hasProvisionTable('x <table><tr><td>a</td></tr>')).toBe(false);
  });
});

describe('provisionTablesToPlainText', () => {
  it('writes each row as cells joined by |, with no tag left', () => {
    const out = provisionTablesToPlainText(WAVERLEY);
    expect(out).not.toMatch(/<\/?(table|thead|tbody|tr|th|td)\b/i);
    expect(out).toContain('Location of proposed works | Side setback (min.)');
    expect(out).toContain('Ground Floor | 0.9m');
    expect(out).toContain('Second Floor | 1.5m');
  });

  it('returns text without tables unchanged, and tolerates null', () => {
    expect(provisionTablesToPlainText('C1 Height 9.5m')).toBe('C1 Height 9.5m');
    expect(provisionTablesToPlainText(null)).toBe('');
  });
});
