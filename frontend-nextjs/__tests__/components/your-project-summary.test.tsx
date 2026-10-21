/**
 * "Your project" summary: fixtures only (no database, no network).
 * Pass-through, mapping, comparison, missing value, no liability words.
 */
import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { DEV_TYPE_OPTIONS } from '@/lib/see/devTypes';
import { PROJECT_TYPE_TO_CONTROLS_DEV_TYPE, projectTypeToControlsDevType, resolveControlsDevType } from '@/lib/project-type';
import {
  NOT_FOUND_TEXT,
  NO_CONTROLS_FOR_TYPE_TEXT,
  buildDcpRows,
  buildLepRows,
  buildSiteFlags,
  compareFigure,
  type ControlsPayload,
} from '@/lib/project-summary';
import { YourProjectSummaryView } from '@/components/compliance/YourProjectSummary';
import type { StructuredControl } from '@/components/compliance/DcpStructuredControls';

function control(over: Partial<StructuredControl>): StructuredControl {
  return {
    control_type: 'front_setback', control_label: 'Front setback', direction: 'min',
    value_min: null, value_max: null, unit: 'm', condition: null, section_ref: null,
    source_text: null, dcp_name: 'Fixture Council DCP 2000', dcp_version: 'Fixture Council DCP 2000',
    pdf_page: null, pdf_url: null, data_status: 'numeric', plain_summary: null, ...over,
  };
}

// Invented fixture figures: they exist only inside this test file.
const FIXTURE: ControlsPayload = {
  has_controls: true,
  dcp_name: 'Fixture Council DCP 2000',
  categories: [{
    controls: [
      control({ control_type: 'front_setback', control_label: 'Front setback', value_min: 7.25, section_ref: '3.1.2', pdf_page: 41, pdf_url: 'https://example.test/dcp.pdf#page=41', source_text: 'Fixture words about the front boundary.' }),
      control({ control_type: 'side_setback', control_label: 'Side setback', value_min: 1.5, section_ref: '3.1.3', pdf_page: 42, pdf_url: 'https://example.test/dcp.pdf#page=42', source_text: 'Fixture words about side boundaries.', condition: 'One side only' }),
      control({ control_type: 'side_setback', control_label: 'Side setback', value_min: 2.5, section_ref: '3.1.3', pdf_page: 42, pdf_url: 'https://example.test/dcp.pdf#page=42', condition: 'Both sides' }),
      control({ control_type: 'max_site_coverage', control_label: 'Maximum site coverage', direction: 'max', value_min: 55.5, unit: '%', section_ref: '4.2', pdf_page: 60, pdf_url: 'https://example.test/dcp.pdf#page=60', source_text: 'Fixture words about coverage.' }),
      control({ control_type: 'rear_setback', control_label: 'Rear setback', value_min: null, unit: null, plain_summary: "Worked out from neighbours' setbacks", section_ref: '3.1.4', pdf_page: 43, pdf_url: 'https://example.test/dcp.pdf#page=43' }),
      control({ control_type: 'car_parking', control_label: 'Car parking', value_min: 2, unit: 'spaces', value_max: 4, pdf_page: 70, pdf_url: 'https://example.test/dcp.pdf#page=70' }),
    ],
  }],
};

const LEP = { maxHeight: 9.5, maxFsr: 0.65, minLotSize: 480.5, lepName: 'Fixture Local Environmental Plan 2000', legislationUrl: 'https://example.test/lep' };

function renderView(over: Partial<React.ComponentProps<typeof YourProjectSummaryView>> = {}) {
  return render(
    <YourProjectSummaryView
      projectType="new_dwelling"
      onProjectTypeChange={() => {}}
      lepRows={buildLepRows(LEP)}
      dcpRows={buildDcpRows(FIXTURE)}
      unmapped={false}
      flags={{ flags: [], unchecked: [] }}
      {...over}
    />,
  );
}

describe('pass-through: displayed value, page, words and link equal the source', () => {
  it('every DCP fixture control appears with its own figure, clause and page, words and link', () => {
    renderView();
    const front = screen.getAllByTestId('row-front')[0];
    expect(within(front).getByTestId('figure').textContent).toContain('≥ 7.25 m');
    expect(within(front).getByTestId('place').textContent).toBe('Fixture Council DCP 2000, 3.1.2, p. 41');
    expect(within(front).getByTestId('words').textContent).toBe('Fixture words about the front boundary.');
    expect(within(front).getByTestId('link').getAttribute('href')).toBe('https://example.test/dcp.pdf#page=41');

    const cover = screen.getAllByTestId('row-coverage')[0];
    expect(within(cover).getByTestId('figure').textContent).toContain('≤ 55.5 %');
    expect(within(cover).getByTestId('place').textContent).toBe('Fixture Council DCP 2000, 4.2, p. 60');
    expect(within(cover).getByTestId('words').textContent).toBe('Fixture words about coverage.');
    expect(within(cover).getByTestId('link').getAttribute('href')).toBe('https://example.test/dcp.pdf#page=60');
  });

  it('LEP rows show the map figure unchanged with the LEP name and link', () => {
    renderView();
    expect(within(screen.getAllByTestId('row-height')[0]).getByTestId('figure').textContent).toContain('9.5 m');
    expect(within(screen.getAllByTestId('row-fsr')[0]).getByTestId('figure').textContent).toContain('0.65:1');
    const lot = screen.getAllByTestId('row-minlot')[0];
    expect(within(lot).getByTestId('figure').textContent).toContain('480.5 m²');
    expect(within(lot).getByTestId('place').textContent).toBe('Fixture Local Environmental Plan 2000');
    expect(within(lot).getByTestId('link').getAttribute('href')).toBe('https://example.test/lep');
  });

  it('a control with no number shows the source plain wording, with no comparison box', () => {
    renderView();
    const rear = screen.getAllByTestId('row-rear')[0];
    expect(within(rear).getByTestId('figure').textContent).toContain("Worked out from neighbours' setbacks");
    expect(screen.queryByTestId('proposal-rear')).toBeNull();
  });

  it('a range is shown as the source gives it and is not compared', () => {
    renderView();
    expect(within(screen.getAllByTestId('row-parking')[0]).getByTestId('figure').textContent).toContain('2–4 spaces');
    expect(screen.queryByTestId('proposal-parking')).toBeNull();
  });

  it('several rows for one control are all shown with their conditions, none compared', () => {
    renderView();
    const side = screen.getAllByTestId('row-side');
    expect(side).toHaveLength(2);
    expect(side[0].textContent).toContain('≥ 1.5 m');
    expect(side[0].textContent).toContain('One side only');
    expect(side[1].textContent).toContain('≥ 2.5 m');
    expect(side[1].textContent).toContain('Both sides');
    expect(screen.queryByTestId('proposal-side')).toBeNull();
  });
});

describe('maximum and minimum come from the source marker', () => {
  it('says maximum for the ceiling and minimum for the floor', () => {
    renderView();
    expect(within(screen.getAllByTestId('row-coverage')[0]).getByText("The plan's figure is a maximum.")).toBeTruthy();
    expect(within(screen.getAllByTestId('row-front')[0]).getByText("The plan's figure is a minimum.")).toBeTruthy();
  });
});

describe('comparison arithmetic', () => {
  it('above / below / equal', () => {
    expect(compareFigure(7.25, '8')).toEqual({ kind: 'result', relation: 'above', text: "Your figure is above the plan's figure." });
    expect(compareFigure(7.25, '7')).toMatchObject({ relation: 'below' });
    expect(compareFigure(7.25, ' 7.25 ')).toMatchObject({ relation: 'equal', text: "Your figure is equal to the plan's figure." });
  });
  it('no number, empty or invalid input', () => {
    expect(compareFigure(null, '5')).toEqual({ kind: 'none' });
    expect(compareFigure(5, '')).toEqual({ kind: 'none' });
    expect(compareFigure(5, 'abc')).toEqual({ kind: 'invalid' });
  });
  it('typing in the box shows the result text', () => {
    renderView();
    fireEvent.change(screen.getByTestId('proposal-front'), { target: { value: '9' } });
    expect(screen.getByTestId('result-front').textContent).toBe("Your figure is above the plan's figure.");
    fireEvent.change(screen.getByTestId('proposal-height'), { target: { value: '9.5' } });
    expect(screen.getByTestId('result-height').textContent).toBe("Your figure is equal to the plan's figure.");
  });
});

describe('missing values', () => {
  it('a value not in our data says so and links to the plan', () => {
    renderView({ lepRows: buildLepRows({ ...LEP, maxHeight: null }) });
    const row = screen.getAllByTestId('row-height')[0];
    expect(within(row).getByTestId('not-found').textContent).toContain(NOT_FOUND_TEXT);
    expect(within(row).getByTestId('plan-link').getAttribute('href')).toBe('https://example.test/lep');
  });
  it('DCP controls the plan data lacks say so, linking to the plan we do have', () => {
    renderView();
    const row = screen.getAllByTestId('row-solar')[0];
    expect(within(row).getByTestId('not-found').textContent).toContain(NOT_FOUND_TEXT);
    expect(within(row).getByTestId('plan-link').getAttribute('href')).toBe('https://example.test/dcp.pdf#page=41');
  });
  it('no controls payload at all: every DCP row says not found', () => {
    const rows = buildDcpRows(null);
    expect(rows.every((r) => r.entries.length === 0)).toBe(true);
  });
});

describe('project type mapping', () => {
  it('every DEV_TYPE_OPTIONS value is present in the table (mapped or explicitly null)', () => {
    for (const o of DEV_TYPE_OPTIONS) {
      expect(Object.prototype.hasOwnProperty.call(PROJECT_TYPE_TO_CONTROLS_DEV_TYPE, o.value)).toBe(true);
    }
    expect(Object.keys(PROJECT_TYPE_TO_CONTROLS_DEV_TYPE).sort()).toEqual(DEV_TYPE_OPTIONS.map((o) => o.value).sort());
  });
  it('an unknown type is unmapped, never guessed', () => {
    expect(projectTypeToControlsDevType('not_a_type')).toBeNull();
    expect(projectTypeToControlsDevType('toString')).toBeNull();
  });
  it('an unmapped type shows the no-controls message and no DCP rows', () => {
    renderView({ projectType: 'subdivision', unmapped: true });
    expect(screen.getByTestId('unmapped').textContent).toBe(NO_CONTROLS_FOR_TYPE_TEXT);
    expect(screen.queryByTestId('row-front')).toBeNull();
  });
});

describe('site flags', () => {
  it('lists only the flags present, each with its source; absent flags are not listed', () => {
    const flags = buildSiteFlags({
      floodProne: false, heritage: true, heritageItemName: 'Fixture House', heritageLegislativeClause: 'cl 5.10',
      heritageLegislationUrl: 'https://example.test/heritage', bushfireProne: false,
      classifiedRoad: { state: true, classified: false, roads: [{ roadNumber: 'A9', roadName: 'Fixture Road', roadClass: 'State' }] },
      railOrBusyRoadUnchecked: 'The busy road check could not run.',
    });
    expect(flags.flags.map((f) => f.key)).toEqual(['heritage', 'classified']);
    renderView({ flags });
    expect(screen.getByTestId('flag-heritage').textContent).toContain('Fixture House — cl 5.10');
    expect(screen.queryByTestId('flag-flood')).toBeNull();
    expect(screen.getByTestId('flag-unchecked').textContent).toBe('The busy road check could not run.');
  });
  it('nothing is rendered when there are no flags', () => {
    renderView();
    expect(screen.queryByTestId('site-flags')).toBeNull();
  });
});

describe('language', () => {
  // The words come from the list the liability hook enforces (scripts/liability_language_check.py), read at test
  // time: one source, and no copy of the words in this file. "complies" is added: it is a verdict too.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const fs = require('fs') as typeof import('fs');
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const path = require('path') as typeof import('path');
  const hook = fs.readFileSync(path.join(__dirname, '../../../scripts/liability_language_check.py'), 'utf8');
  const start = hook.indexOf('FLAGGED_TERMS = re.compile(');
  const block = hook.slice(start, hook.indexOf("r'as[", start)); // up to the phrase entry
  const words = Array.from(new Set((block.match(/[a-z]{4,}/g) ?? []).filter((w) => !['compile', 'should_'].includes(w))));
  const LIABILITY = new RegExp(`\\b(${[...words, 'complies'].join('|')})\\b`, 'i');
  it('reads a real word list from the hook', () => {
    expect(words.length).toBeGreaterThanOrEqual(15);
  });
  it('rendered text (including the not-found, unmapped and comparison text) has no liability words', () => {
    const { container, unmount } = renderView({
      flags: buildSiteFlags({ heritage: true, heritageItemName: 'Fixture House', bushfireProne: true, acidSulfateSoils: 'Class 5' }),
    });
    fireEvent.change(screen.getByTestId('proposal-front'), { target: { value: '3' } });
    expect(container.textContent).not.toMatch(LIABILITY);
    unmount();
    const second = renderView({ projectType: 'other', unmapped: true, lepRows: buildLepRows({ ...LEP, maxHeight: null, maxFsr: null, minLotSize: null }) });
    expect(second.container.textContent).not.toMatch(LIABILITY);
    expect(NOT_FOUND_TEXT).not.toMatch(LIABILITY);
    expect(NO_CONTROLS_FOR_TYPE_TEXT).not.toMatch(LIABILITY);
  });
});

describe('summary and DCP tab read the same mapped type', () => {
  it('both call resolveControlsDevType: default, mapped and unmapped picks', () => {
    expect(resolveControlsDevType(null)).toBe(projectTypeToControlsDevType(DEV_TYPE_OPTIONS[0].value));
    for (const o of DEV_TYPE_OPTIONS) {
      expect(resolveControlsDevType(o.value)).toBe(PROJECT_TYPE_TO_CONTROLS_DEV_TYPE[o.value]);
    }
    expect(resolveControlsDevType('subdivision')).toBeNull();
  });
  it('both call sites use the shared function (source check)', () => {
    const fs = require('fs');
    const tab = fs.readFileSync(require('path').join(__dirname, '../../components/compliance/ProvisionsByTocStructure.tsx'), 'utf8');
    const sum = fs.readFileSync(require('path').join(__dirname, '../../components/compliance/YourProjectSummary.tsx'), 'utf8');
    expect(tab).toContain('resolveControlsDevType(sharedProjectType)');
    expect(sum).toContain('resolveControlsDevType(shared)');
    expect((tab.match(/devType=\{controlsDevType\}/g) || []).length).toBe(2);
  });
});

describe('pass-through, every row: each row shows exactly its own source controls', () => {
  // Generated fixture: every control type the table reads gets a unique figure, page and words, so a row that
  // reads the wrong type (or drops/merges one) shows a figure or page that is not its own and fails here.
  // Mutation that motivated it (2026-10-21): pointing 'Private open space' at landscaping_min passed all 20 tests.
  it('every DCP_ROW_SPECS row, every type: own figure, own page, own words, own link; no other type leaks in', () => {
    // The expected row -> control types table is written HERE, independently of the code under test: a test that
    // imports the code's own table agrees with any mistake in it (it passed the mutation above).
    const DCP_ROW_SPECS = [
      { key: 'front', types: ['front_setback'] },
      { key: 'side', types: ['side_setback'] },
      { key: 'rear', types: ['rear_setback'] },
      { key: 'coverage', types: ['max_site_coverage'] },
      { key: 'landscape', types: ['landscaped_area_min', 'landscaping_min', 'deep_soil_min'] },
      { key: 'pos', types: ['private_open_space'] },
      { key: 'parking', types: ['car_parking'] },
      { key: 'solar', types: ['solar_access_hours'] },
    ];
    const all: Array<{ type: string; value: number; page: number; words: string }> = [];
    (DCP_ROW_SPECS as Array<{ key: string; types: string[] }>).forEach((spec, i) =>
      spec.types.forEach((t, j) => all.push({ type: t, value: 101 + i * 10 + j, page: 201 + i * 10 + j, words: `Words for ${t}.` })),
    );
    const payload: ControlsPayload = {
      has_controls: true,
      dcp_name: 'Fixture Council DCP 2000',
      categories: [{
        controls: all.map((c) =>
          control({ control_type: c.type, control_label: c.type, value_min: c.value, unit: 'm', direction: 'min',
            section_ref: `S-${c.type}`, pdf_page: c.page, pdf_url: `https://example.test/dcp.pdf#page=${c.page}`, source_text: c.words })),
      }],
    };
    renderView({ dcpRows: buildDcpRows(payload) });
    for (const spec of DCP_ROW_SPECS as Array<{ key: string; types: string[] }>) {
      const rows = screen.getAllByTestId(`row-${spec.key}`);
      const text = rows.map((r) => r.textContent ?? '').join(' | ');
      const mine = all.filter((c) => spec.types.includes(c.type));
      const others = all.filter((c) => !spec.types.includes(c.type));
      for (const c of mine) {
        expect([spec.key, c.type, text.includes(String(c.value))]).toEqual([spec.key, c.type, true]);
        expect([spec.key, c.type, text.includes(`p. ${c.page}`)]).toEqual([spec.key, c.type, true]);
        const hrefs = rows.flatMap((r) => within(r).queryAllByTestId('link').map((a) => a.getAttribute('href')));
        expect([spec.key, c.type, hrefs.includes(`https://example.test/dcp.pdf#page=${c.page}`)]).toEqual([spec.key, c.type, true]);
        const words = rows.flatMap((r) => within(r).queryAllByTestId('words').map((w) => w.textContent));
        expect([spec.key, c.type, words.includes(c.words)]).toEqual([spec.key, c.type, true]);
      }
      for (const o of others) {
        expect([spec.key, o.type, text.includes(String(o.value)) || text.includes(`p. ${o.page}`)]).toEqual([spec.key, o.type, false]);
      }
    }
  });
});
