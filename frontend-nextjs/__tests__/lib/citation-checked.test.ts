/** isCitationChecked mirrors DQ-145 (scripts/dq_probe_live.py). The parity test reads the SQL text. */
import { readFileSync } from 'fs';
import { join } from 'path';
import {
  isCitationChecked, withServedCitation, CITATION_PROVEN_STATUSES, CITATION_PROVEN_PAGE_CHECKS,
} from '@/lib/citation-display';

describe('isCitationChecked', () => {
  it.each([
    [{ citation_status: 'proven' }, true],
    [{ citation_status: 'imprecise' }, true],
    [{ page_check: 'on_page' }, true],
    [{ page_check: 'moved' }, true],
    [{ citation_status: 'read_by_person' }, false],
    [{ citation_status: 'not_proven', page_check: 'not_found' }, false],
    [{ citation_status: null, page_check: null }, false],
    [{}, false],
    [null, false],
    [undefined, false],
  ])('%j -> %s', (row, want) => {
    expect(isCitationChecked(row as any)).toBe(want);
  });

  it('withServedCitation carries the flag', () => {
    expect(withServedCitation({ citation_status: 'proven', source_council: 'x' }, null).citation_checked).toBe(true);
    expect(withServedCitation({ source_council: 'x' }, null).citation_checked).toBe(false);
  });
});

describe('parity with DQ-145', () => {
  const py = readFileSync(join(__dirname, '../../../scripts/dq_probe_live.py'), 'utf8');
  const start = py.indexOf('"DQ-145": (');
  const block = py.slice(start, py.indexOf('\n    ),', start));
  const set = (col: string) => {
    const m = block.match(new RegExp(`COALESCE\\(${col}, ''\\) IN \\(([^)]*)\\)`));
    expect(m).not.toBeNull();
    return [...m![1].matchAll(/'([^']+)'/g)].map((x) => x[1]).sort();
  };
  it('uses the same citation_status values', () => {
    expect(set('citation_status')).toEqual([...CITATION_PROVEN_STATUSES].sort());
  });
  it('uses the same page_check values', () => {
    expect(set('page_check')).toEqual([...CITATION_PROVEN_PAGE_CHECKS].sort());
  });
});
