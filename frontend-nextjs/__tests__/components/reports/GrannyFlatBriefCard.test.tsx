/**
 * GrannyFlatBriefCard (#752) — the brief's Secondary Dwelling card with the
 * human confirm/calculate step.
 *
 * Contract under test (three-state, from #748):
 *  (a) successful detect on a SEPP-eligible lot → the structure-selection
 *      affordance renders; the confirm call NEVER fires without a click;
 *  (b) detection_failed → "unknown, not zero" copy and NO selection affordance;
 *  (c) explicit confirm click → the four yield fields render with the
 *      response's confidence + confidence_reason verbatim;
 *  (d) confirm failure → a visible error, and no zeroed yield figures.
 *
 * Outcome words come from fixtures, not literals, so a contract change fails
 * here rather than silently drifting.
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { GrannyFlatBriefCard } from '@/components/reports/GrannyFlatBriefCard';

global.fetch = jest.fn();
const mockFetch = global.fetch as jest.Mock;

const ADDRESS = '14 STANLEY STREET CONCORD 2137';
const LOT_AREA = 612.4;

// Detect outputs as written to granny_flat_reports.outputs (pending_confirm).
const DETECT_OK = {
  detect_id: 'det-abc-123',
  sepp_eligible: true,
  detection_failed: false,
  samgeo_structure_count: 2,
  samgeo_validated: true,
  confirmation_required: true,
  lot_area_m2: LOT_AREA,
  detected_structures: [
    { matched_prompt: 'house', area_m2: 142.3, is_main_dwelling: true },
    { matched_prompt: 'shed', area_m2: 18.2, is_main_dwelling: false },
  ],
  warnings: [],
};

// #748 three-state: a failed detection is None/unknown — never zero.
const DETECT_FAILED = {
  detect_id: 'det-def-456',
  sepp_eligible: true,
  detection_failed: true,
  samgeo_structure_count: null,
  samgeo_validated: false,
  confirmation_required: true,
  lot_area_m2: LOT_AREA,
  detected_structures: [],
  warnings: ['structure detection failed'],
};

const CONFIRM_OK = {
  report_id: 'rep-1',
  address: ADDRESS,
  granny_flat_buildable: true,
  max_floor_area_m2: 60,
  estimated_weekly_rent_aud: 545,
  rental_yield_annual_pct: 8.9,
  assumed_build_cost_aud: 165000,
  confidence: 'medium',
  confidence_reason:
    'User selections matched the aerial detection; rent derived from postcode-level bond lodgement data.',
  data_sources: ['NSW SIX Maps', 'NSW Fair Trading rental bond data'],
  warnings: [],
};

const CONFIRM_ERROR = { error: 'Confirm error (502): rent service unavailable' };

const SELECT_COPY = /Select the structures that match the aerial view/;
const CALC_BUTTON = /Calculate indicative yield/;

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: async () => body };
}

/** Route the component's fetches: POST detect → jobId, GET poll → detect outputs, POST confirm → confirmResult. */
function routeFetch({
  detectOutputs,
  confirmResponse,
}: {
  detectOutputs: Record<string, unknown>;
  confirmResponse?: { body: unknown; ok: boolean; status?: number };
}) {
  const confirmBodies: Record<string, unknown>[] = [];
  mockFetch.mockImplementation(async (url: string, init?: { method?: string; body?: string }) => {
    if (init?.method === 'POST') {
      const body = JSON.parse(init.body ?? '{}');
      if (body.action === 'detect') return jsonResponse({ jobId: 'job-1' }, true, 202);
      if (body.action === 'confirm') {
        confirmBodies.push(body);
        const c = confirmResponse ?? { body: CONFIRM_OK, ok: true };
        return jsonResponse(c.body, c.ok, c.status ?? (c.ok ? 200 : 502));
      }
      throw new Error(`unexpected POST action: ${body.action}`);
    }
    if (typeof url === 'string' && url.includes('jobId=')) {
      return jsonResponse({ status: 'detected', data: detectOutputs });
    }
    throw new Error(`unexpected fetch: ${url}`);
  });
  return { confirmBodies };
}

async function flush() {
  await act(async () => { await Promise.resolve(); });
}

/** Render and drive the card through detect POST + one poll tick. */
async function renderThroughDetect(detectOutputs: Record<string, unknown>, confirmResponse?: { body: unknown; ok: boolean; status?: number }) {
  const routed = routeFetch({ detectOutputs, confirmResponse });
  render(<GrannyFlatBriefCard address={ADDRESS} active lotAreaM2={LOT_AREA} />);
  await flush();                                     // detect POST resolves → poll scheduled
  await act(async () => { jest.advanceTimersByTime(2000); }); // first poll tick
  await flush();
  await flush();
  return routed;
}

beforeEach(() => {
  jest.useFakeTimers();
  mockFetch.mockReset();
});

afterEach(() => {
  jest.useRealTimers();
});

// ---------------------------------------------------------------------------
// (a) successful detect → selection affordance, and confirm never auto-fires
// ---------------------------------------------------------------------------

describe('successful detect on a SEPP-eligible lot', () => {
  it('renders the structure-selection affordance and the calculate button', async () => {
    await renderThroughDetect(DETECT_OK);

    expect(screen.getByText(SELECT_COPY)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: CALC_BUTTON })).toBeInTheDocument();
    // Detected structures are listed as selectable rows, all selected by default
    expect(screen.getByRole('button', { name: /House \(main dwelling\)/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Shed/ })).toHaveAttribute('aria-pressed', 'true');
    // Count line still reports what detection returned
    expect(
      screen.getByText((_, el) => el?.textContent === `${DETECT_OK.samgeo_structure_count} existing buildings detected on the lot from the aerial image.`),
    ).toBeInTheDocument();
  });

  it('never fires the confirm action without an explicit click', async () => {
    const { confirmBodies } = await renderThroughDetect(DETECT_OK);
    // let any stray timers/microtasks run
    await act(async () => { jest.advanceTimersByTime(10_000); });
    await flush();
    expect(confirmBodies).toHaveLength(0);
    expect(screen.queryByTestId('gf-yield-block')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// (b) detection_failed → unknown-count copy, NO confirm affordance
// ---------------------------------------------------------------------------

describe('failed detection (three-state, #748)', () => {
  it('renders the unknown-not-zero copy and no selection affordance', async () => {
    await renderThroughDetect(DETECT_FAILED);

    expect(screen.getByText(/unknown, not zero/)).toBeInTheDocument();
    expect(screen.queryByText(SELECT_COPY)).toBeNull();
    expect(screen.queryByRole('button', { name: CALC_BUTTON })).toBeNull();
  });

  it('offers no selection affordance when the lot is not SEPP-eligible either', async () => {
    await renderThroughDetect({ ...DETECT_OK, sepp_eligible: false, sepp_ineligible_reason: 'Lot area below the 450 m² SEPP standard.' });

    expect(screen.getByText('Lot area below the 450 m² SEPP standard.')).toBeInTheDocument();
    expect(screen.queryByText(SELECT_COPY)).toBeNull();
    expect(screen.queryByRole('button', { name: CALC_BUTTON })).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// (c) confirm success → four yield fields + confidence_reason verbatim
// ---------------------------------------------------------------------------

describe('confirm success', () => {
  it('renders the four yield fields with confidence and confidence_reason verbatim', async () => {
    await renderThroughDetect(DETECT_OK);

    fireEvent.click(screen.getByRole('button', { name: CALC_BUTTON }));
    await flush();
    await flush();

    const block = screen.getByTestId('gf-yield-block');
    expect(block).toBeInTheDocument();
    expect(screen.getByText('Buildable floor area')).toBeInTheDocument();
    expect(screen.getByText(`${CONFIRM_OK.max_floor_area_m2} m²`)).toBeInTheDocument();
    expect(screen.getByText('Indicative weekly rent')).toBeInTheDocument();
    expect(screen.getByText(`$${CONFIRM_OK.estimated_weekly_rent_aud}/wk`)).toBeInTheDocument();
    expect(screen.getByText('Indicative annual yield')).toBeInTheDocument();
    expect(screen.getByText(`${CONFIRM_OK.rental_yield_annual_pct}% p.a.`)).toBeInTheDocument();
    expect(screen.getByText('Assumed build cost')).toBeInTheDocument();
    expect(screen.getByText(`$${CONFIRM_OK.assumed_build_cost_aud.toLocaleString('en-AU')}`)).toBeInTheDocument();
    // confidence + reason verbatim from the response fixture
    expect(screen.getByText(CONFIRM_OK.confidence)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(CONFIRM_OK.confidence_reason.slice(0, 40)))).toBeInTheDocument();
    // the selection affordance is replaced by the result
    expect(screen.queryByRole('button', { name: CALC_BUTTON })).toBeNull();
  });

  it('sends the standalone tool request shape — detect_id, selections, echoed count, reconciled lot area', async () => {
    const { confirmBodies } = await renderThroughDetect(DETECT_OK);

    // Deselect the shed — the user says it does not match the aerial view
    fireEvent.click(screen.getByRole('button', { name: /Shed/ }));
    // Answer the existing-secondary-dwelling question
    fireEvent.click(screen.getByRole('button', { name: 'No' }));
    fireEvent.click(screen.getByRole('button', { name: CALC_BUTTON }));
    await flush();

    expect(confirmBodies).toHaveLength(1);
    expect(confirmBodies[0]).toMatchObject({
      address: ADDRESS,
      action: 'confirm',
      detect_id: DETECT_OK.detect_id,
      confirmed_structure_count: 1, // 2 detected, shed deselected
      samgeo_structure_count: DETECT_OK.samgeo_structure_count,
      postcode: '2137',
      existing_secondary_dwelling: false,
      main_dwelling_area_m2: DETECT_OK.detected_structures[0].area_m2,
      lot_area_m2: LOT_AREA, // #745 D3 — the brief's reconciled figure
    });
  });

  it('transmits the per-structure decisions and the count provenance', async () => {
    // Lane 1 item 4: the deselect used to collapse into a bare count and the
    // per-structure judgement was discarded. This pins that it survives the
    // wire, bound to the structure index it was made about, and that the
    // count is labelled as human-reviewed rather than inferred downstream.
    const { confirmBodies } = await renderThroughDetect(DETECT_OK);

    fireEvent.click(screen.getByRole('button', { name: /Shed/ }));
    fireEvent.click(screen.getByRole('button', { name: 'No' }));
    fireEvent.click(screen.getByRole('button', { name: CALC_BUTTON }));
    await flush();

    // Only the structure the user actually touched is reported…
    expect(confirmBodies[0].structure_types).toEqual([
      { index: 1, answer: 'rejected' },  // shed deselected
    ]);
    // …and the count is not claimed as reviewed, because the main dwelling
    // was never touched (Sol finding 1: everything arrives pre-selected, so
    // an untouched default is silence, not a judgement).
    expect(confirmBodies[0].confirmed_count_source).toBe('machine_default');
  });

  it('claims a reviewed count only once every structure has been touched', async () => {
    const { confirmBodies } = await renderThroughDetect(DETECT_OK);

    fireEvent.click(screen.getByRole('button', { name: /House/ }));  // deselect
    fireEvent.click(screen.getByRole('button', { name: /House/ }));  // and back — still touched
    fireEvent.click(screen.getByRole('button', { name: /Shed/ }));
    fireEvent.click(screen.getByRole('button', { name: 'No' }));
    fireEvent.click(screen.getByRole('button', { name: CALC_BUTTON }));
    await flush();

    expect(confirmBodies[0].confirmed_count_source).toBe('secondary_detections_classified');
    expect(confirmBodies[0].structure_types).toEqual([
      { index: 0, answer: 'kept' },
      { index: 1, answer: 'rejected' },
    ]);
  });

  it('sends no answers and no review claim when the user touches nothing', async () => {
    // Clicking Calculate on untouched defaults must not become two human
    // "kept" judgements — that is manufacturing the label.
    const { confirmBodies } = await renderThroughDetect(DETECT_OK);
    fireEvent.click(screen.getByRole('button', { name: 'No' }));
    fireEvent.click(screen.getByRole('button', { name: CALC_BUTTON }));
    await flush();

    expect(confirmBodies[0].structure_types).toEqual([]);
    expect(confirmBodies[0].confirmed_count_source).toBe('machine_default');
  });

  it('never labels a structure with a type the brief card does not ask for', async () => {
    // The card only asks keep-or-reject. Emitting 'garage'/'part_of_main'
    // here would invent a classification the person never gave.
    const { confirmBodies } = await renderThroughDetect(DETECT_OK);
    // Deselect and re-select: touched, and left in the count.
    fireEvent.click(screen.getByRole('button', { name: /House/ }));
    fireEvent.click(screen.getByRole('button', { name: /House/ }));
    fireEvent.click(screen.getByRole('button', { name: 'No' }));
    fireEvent.click(screen.getByRole('button', { name: CALC_BUTTON }));
    await flush();

    const answers = (confirmBodies[0].structure_types as { answer: string }[]).map(s => s.answer);
    expect(new Set(answers)).toEqual(new Set(['kept']));
  });

  it('renders "Not available" for null money fields — never a zero', async () => {
    await renderThroughDetect(DETECT_OK, {
      body: {
        ...CONFIRM_OK,
        granny_flat_buildable: false,
        estimated_weekly_rent_aud: null,
        rental_yield_annual_pct: null,
        assumed_build_cost_aud: null,
      },
      ok: true,
    });
    fireEvent.click(screen.getByRole('button', { name: CALC_BUTTON }));
    await flush();
    await flush();

    expect(screen.getByTestId('gf-yield-block')).toBeInTheDocument();
    expect(screen.getAllByText('Not available')).toHaveLength(3);
    expect(screen.queryByText(/\$0\b/)).toBeNull();
    expect(screen.queryByText('0% p.a.')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// (d) confirm failure → visible error, never zeros
// ---------------------------------------------------------------------------

describe('confirm failure', () => {
  it('renders a visible error with the response message and no yield figures', async () => {
    await renderThroughDetect(DETECT_OK, { body: CONFIRM_ERROR, ok: false, status: 502 });

    fireEvent.click(screen.getByRole('button', { name: CALC_BUTTON }));
    await flush();
    await flush();

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent(CONFIRM_ERROR.error);
    expect(alert).toHaveTextContent(/did not complete/);
    // no yield block, no zeroed figures
    expect(screen.queryByTestId('gf-yield-block')).toBeNull();
    expect(screen.queryByText(/\$0\b/)).toBeNull();
    expect(screen.queryByText(/0% p\.a\./)).toBeNull();
    // the affordance is still there so the user can retry
    expect(screen.getByRole('button', { name: CALC_BUTTON })).toBeInTheDocument();
  });
});
