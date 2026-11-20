import { evidenceUrl, isEvidence } from '@/lib/evidence-statement';

const good = {
  law_version_date: '2026-10-23', headline: 'h', lga: 'PENRITH', notes: [], exclusions: [],
  walk: { clause: null, page: null, anchor: null, limit_m: null, walk_low_m: null, walk_high_m: null, detail: null, heuristic: null },
  council_controls: { status: 'ok', controls: [] }, council_files: { status: 'none', files: [] },
};

describe('evidence page helpers', () => {
  it('builds the proxy address only from two numbers', () => {
    expect(evidenceUrl('-33.75', '150.70')).toBe('/api/housing-sepp/evidence?lat=-33.75&lng=150.70');
    for (const [a, b] of [[null, '1'], ['1', null], ['', '1'], ['a', '1'], ['1', ' ']] as const) expect(evidenceUrl(a, b)).toBeNull();
  });
  it('accepts a full payload', () => { expect(isEvidence(good)).toBe(true); });
  it('rejects a partial payload, so the page shows an error not an empty statement', () => {
    expect(isEvidence(null)).toBe(false);
    expect(isEvidence({ ...good, exclusions: undefined })).toBe(false);
    expect(isEvidence({ ...good, walk: undefined })).toBe(false);
    expect(isEvidence({ ...good, council_controls: { status: 'weird', controls: [] } })).toBe(false);
    expect(isEvidence({ ...good, council_files: { status: 'ok' } })).toBe(false);
  });
});
