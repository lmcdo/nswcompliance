/**
 * Brief "Data sources" footer is per-run, not a static union (issue #753).
 *
 * The footer must list only the sources cited by DataFields that actually
 * populated on the received sections: a source cited solely by null-valued
 * fields (pipeline did not run / nothing at this address) stays off the list,
 * duplicate labels collapse to one row (case-insensitive on the normalised
 * label), and the as-at stamp kept is the latest seen for that source.
 */

import { collectSources, humanizeSource } from '@/app/reports/intelligence-brief/provenance';

// Minimal DataField factory matching the streamed shape (value/source/as_at).
function df(value: unknown, source: string, asAt?: string | null) {
  return { value, confidence: value == null ? 'not_available' : 'authoritative', source, as_at: asAt ?? null };
}

// Section events carry { data: { section, data } }; collectSources reads data.data.
function section(name: string, data: unknown) {
  return { data: { section: name, data } };
}

describe('collectSources — per-run source list', () => {
  it('lists exactly the sources cited by populated fields (planning + cadastre only)', () => {
    const sections = [
      section('planning_controls', {
        zone: df('C4', 'planning_portal', '2026-07-10'),
        fsr: df(null, 'planning_portal'), // null field, same source — still counted via zone
      }),
      section('title', {
        lot: df('12/DP12345', 'cadastre_strata', '2026-07-01'),
      }),
      // DCP pipeline did not run for this council — source cited only by a null field.
      section('dcp_controls', df(null, 'plotdetect_dcp')),
      // No structure detection ran on this brief.
      section('satellite.granny_flat', df(null, 'granny_flat_detect')),
    ];

    const { sources } = collectSources(sections);
    const labels = sources.map((s) => s.label);

    expect(labels).toHaveLength(2);
    expect(labels).toContain('NSW Planning Portal');
    expect(labels).toContain('NSW cadastre (strata/lot)');
    expect(labels).not.toContain('Plotdetect Dcp');
    expect(labels).not.toContain('Satellite imagery + structure detection');
  });

  it('collapses duplicate source labels to one entry, keeping the latest as-at', () => {
    const sections = [
      section('protection', {
        a: df({ layer: 'x' }, 'live_protection_overlay', '2026-06-01'),
        b: df({ layer: 'y' }, 'planning_portal_protection', '2026-07-02'),
      }),
    ];

    const { sources } = collectSources(sections);

    expect(sources).toHaveLength(1);
    expect(sources[0].label).toBe('NSW Planning Portal — Protection layers');
    expect(sources[0].asAt).toBe('2026-07-02');
  });

  it('dedupe is case-insensitive on the normalised label', () => {
    // Two raw slugs whose humanised labels differ only in case must merge.
    const sections = [
      section('s1', { a: df(1, 'nsw lrs') }),   // humanises to "Nsw Lrs"
      section('s2', { b: df(2, 'NSW LRS') }),   // humanises to "NSW LRS"
    ];

    const { sources } = collectSources(sections);
    expect(sources).toHaveLength(1);
  });

  it('excludes a source cited only by null-valued fields', () => {
    const sections = [
      section('planning_controls', { zone: df('R2', 'planning_portal') }),
      section('dcp_controls', {
        setbacks: df(null, 'plotdetect_dcp'),
        landscaping: df(null, 'plotdetect_dcp'),
      }),
    ];

    const { sources } = collectSources(sections);
    expect(sources.map((s) => s.label)).toEqual(['NSW Planning Portal']);
  });

  it('a field with value false or 0 still counts as populated', () => {
    const sections = [
      section('s', {
        flag: df(false, 'anef_zones', '2026-05-05'),
        count: df(0, 'vg_valuation'),
      }),
    ];

    const labels = collectSources(sections).sources.map((s) => s.label);
    expect(labels).toContain('ANEF aircraft-noise contours');
    expect(labels).toContain('NSW Valuer General');
  });

  it('an object carrying source but no value key is not a populated field', () => {
    // e.g. a climate manifest sources_unavailable entry: { source, reason }.
    const sections = [
      section('climate', {
        wrapper: df({ manifest: { sources_unavailable: [{ source: 'nasa_firms', reason: 'no coverage' }] } }, 'narclim_projections'),
      }),
    ];

    const labels = collectSources(sections).sources.map((s) => s.label);
    expect(labels).toEqual(['Narclim Projections']);
    expect(labels).not.toContain('Nasa Firms');
  });

  it('still collects legislation/source URLs as links', () => {
    const sections = [
      section('planning_controls', {
        zone: df('R2', 'planning_portal'),
        legislation_url: 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2013-0568',
      }),
    ];

    const { links } = collectSources(sections);
    expect(links).toHaveLength(1);
    expect(links[0].url).toMatch(/^https:\/\/legislation\.nsw\.gov\.au\//);
  });
});

describe('humanizeSource', () => {
  it('maps known slugs to their real-world label and title-cases unknown slugs', () => {
    expect(humanizeSource('planning_portal')).toBe('NSW Planning Portal');
    expect(humanizeSource('some_new_pipeline')).toBe('Some New Pipeline');
  });
});
