/**
 * Granny-flat ConfirmationPanel — the confirm step is wired end-to-end.
 *
 * Calibration Lane 1, item 4. `onCountChange` was passed to this component
 * from the day it was written and never invoked, so
 * `confirmed_structure_count` could only ever echo `samgeo_structure_count`.
 * Production measurement on 2026-08-06: 16 rows carried both counts, 13
 * "agreed", and ZERO carried a human judgement — the 2 apparent
 * disagreements were the page's `: 1` fallback when detection found nothing.
 *
 * These tests fail if the count control is ever disconnected again, or if the
 * per-structure answers stop being lifted out of the component.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmationPanel } from '@/app/reports/granny-flat/page';

// The aerial canvas is irrelevant here and pulls in maplibre.
jest.mock('react-map-gl/maplibre', () => ({
  __esModule: true,
  default: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  Source: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  Layer: () => null,
  NavigationControl: () => null,
}));

jest.mock('@/components/providers/PostHogProvider', () => ({ posthog: null }));

const DETECT = {
  detect_id: 'det-1',
  address: '1 Test St, Sydney NSW 2000',
  lat: -33.87,
  lng: 151.21,
  prop_id: '1',
  lot_area_m2: 620,
  sepp_eligible: true,
  sepp_ineligible_reason: null,
  detected_structures: [
    { index: 0, area_m2: 150, bbox_pixel: [0, 0, 40, 40], matched_prompt: 'building', is_main_dwelling: true },
    { index: 1, area_m2: 30, bbox_pixel: [50, 50, 70, 70], matched_prompt: 'shed', is_main_dwelling: false },
    { index: 2, area_m2: 25, bbox_pixel: [80, 80, 95, 95], matched_prompt: 'garage', is_main_dwelling: false },
  ],
  samgeo_structure_count: 3,
  detection_failed: false,
  samgeo_validated: true,
  confirmation_required: true,
  tile_licence: 'CC-BY NSW',
  tile_b64: null,
  tile_width: 512,
  tile_height: 512,
  tile_bbox: { min_lat: -33.88, max_lat: -33.86, min_lng: 151.2, max_lng: 151.22 },
  lot_polygon_wgs84: null,
  is_heritage: false,
  warnings: [],
};

function renderPanel(overrides: Record<string, unknown> = {}) {
  const onCountChange = jest.fn();
  const onStructureTypesChange = jest.fn();
  const onExistingSecondaryDwellingChange = jest.fn();
  render(
    <ConfirmationPanel
      detectResult={DETECT as never}
      inputAddress={DETECT.address}
      confirmedCount={3}
      onCountChange={onCountChange}
      structureTypes={{}}
      onStructureTypesChange={onStructureTypesChange}
      existingSecondaryDwelling={null}
      onExistingSecondaryDwellingChange={onExistingSecondaryDwellingChange}
      onConfirm={jest.fn()}
      onBack={jest.fn()}
      {...overrides}
    />,
  );
  return { onCountChange, onStructureTypesChange, onExistingSecondaryDwellingChange };
}

describe('ConfirmationPanel — count control is connected', () => {
  it('invokes onCountChange when a structure is classified', () => {
    const { onCountChange } = renderPanel();
    // "Part of main house" on the first secondary structure
    fireEvent.click(screen.getAllByRole('button', { name: /^Part of main house/ })[0]);
    expect(onCountChange).toHaveBeenCalled();
  });

  it('a detection marked part of the main dwelling leaves the structure count', () => {
    const { onCountChange } = renderPanel();
    fireEvent.click(screen.getAllByRole('button', { name: /^Part of main house/ })[0]);
    // 3 detected − 1 that is not a separate building
    expect(onCountChange).toHaveBeenLastCalledWith(2);
  });

  it('classifying a structure as a garage keeps it in the count', () => {
    const { onCountChange } = renderPanel();
    fireEvent.click(screen.getAllByRole('button', { name: /^Garage \/ outbuilding/ })[0]);
    expect(onCountChange).toHaveBeenLastCalledWith(3);
  });

  it('lifts the per-structure answer out of the component', () => {
    const { onStructureTypesChange } = renderPanel();
    fireEvent.click(screen.getAllByRole('button', { name: /^Garage \/ outbuilding/ })[0]);
    expect(onStructureTypesChange).toHaveBeenCalledWith(
      expect.objectContaining({ 1: expect.any(String) }),
    );
  });

  it('retracts the existing-granny-flat answer when that classification is changed away', () => {
    // Sol finding: marking a structure 'Existing granny flat' set the flag
    // true, and changing it to something else left it stuck true while other
    // structures were still unanswered — serving an ineligible verdict off a
    // retracted answer.
    // Structure 1 is already answered 'existing granny flat'; structure 2 is
    // still unanswered. Change structure 1 to a garage.
    const { onExistingSecondaryDwellingChange } = renderPanel({
      structureTypes: { 1: 'existing_gf' },
    });
    fireEvent.click(screen.getAllByRole('button', { name: /^Garage \/ outbuilding/ })[0]);

    // No answer now says there is one, and not everything is answered — so
    // the honest state is unknown, not "yes".
    expect(onExistingSecondaryDwellingChange).toHaveBeenLastCalledWith(null);
  });

  it('still reports an existing granny flat while one is selected', () => {
    const { onExistingSecondaryDwellingChange } = renderPanel();
    fireEvent.click(screen.getAllByRole('button', { name: /^Existing granny flat/ })[0]);
    expect(onExistingSecondaryDwellingChange).toHaveBeenLastCalledWith(true);
  });

  it('says the count is the detector own figure until every structure is answered', () => {
    renderPanel();
    expect(
      screen.getByText(/the detector's own figure/i),
    ).toBeInTheDocument();
  });

  it('says the count reflects the review once every structure is answered', () => {
    renderPanel({
      structureTypes: { 1: 'garage', 2: 'garage' },
      confirmedCount: 3,
    });
    expect(screen.getByText(/based on your answers below/i)).toBeInTheDocument();
    expect(screen.queryByText(/the detector's own figure/i)).toBeNull();
  });
});

describe('ConfirmationPanel — a zero/unvalidated detection cannot silently calculate', () => {
  // Recall is measured at 0.368 against a 0.70 floor (2026-08-12): detection
  // misses roughly two of every three real structures. When it finds nothing,
  // or was never validated, the submitted count silently defaulted to 1 with
  // nothing forcing a human check first — this is exactly the "2 apparent
  // disagreements were the page's `: 1` fallback" this file's header already
  // documented as measured, but did not yet gate against.

  it('disables Calculate yield when detection found zero structures, until the checkbox is ticked', () => {
    renderPanel({
      detectResult: { ...DETECT, detected_structures: [] } as never,
    });
    const button = screen.getByRole('button', { name: /Calculate yield/i });
    expect(button).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox'));
    expect(button).not.toBeDisabled();
  });

  it('disables Calculate yield when detection was never validated, until the checkbox is ticked', () => {
    renderPanel({
      detectResult: { ...DETECT, samgeo_validated: false } as never,
    });
    const button = screen.getByRole('button', { name: /Calculate yield/i });
    expect(button).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox'));
    expect(button).not.toBeDisabled();
  });

  it('leaves Calculate yield enabled by default when detection succeeded normally', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /Calculate yield/i })).not.toBeDisabled();
    expect(screen.queryByRole('checkbox')).toBeNull();
  });
});
