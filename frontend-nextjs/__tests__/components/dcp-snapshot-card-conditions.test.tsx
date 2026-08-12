/**
 * Guard: the snapshot card must show WHICH CASE each number is for, must not
 * hide rows silently, and must not collapse rows that share a control type.
 *
 * The defect this locks down (DQ-32, user ruling 2026-08-13 "show them all"):
 * a council can hold several parking rates for one development type, each
 * individually correct and separated by bedroom count or by visitor-vs-resident
 * -- Sutherland residential flat buildings carry 1, 1.5, 2 and 0.25. The card
 * rendered the label and the number only, so those four arrived as four
 * identical "Car parking" rows holding contradictory-looking figures with no
 * way to tell which one applied. Worse, the React key was
 * `control_type-section_ref`, which those rows SHARE, so React collapsed them
 * and only one was drawn.
 *
 * Every assertion here fails against the previous implementation.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { DcpSnapshotCard } from '@/components/tools/DcpSnapshotCard';

jest.mock('posthog-js', () => ({ __esModule: true, default: { capture: jest.fn() } }));

/** Four correct parking rates for one control type, as Sutherland actually holds them. */
// The zone codes below are VERBATIM `condition` text from four real
// dcp_setback_controls rows (sutherland_shire / residential_flat_building /
// car_parking, ids 246-249). They are fixture data reproducing what the
// database holds, not a regulatory lookup table this code reads from, so
// importing the shared taxonomy would defeat the fixture: the point is that the
// component renders whatever string the API sends.
const PARKING_ROWS = [
  { condition: '1 bedroom; zones R4, R3', value_min: 1 },          // noqa: zone-codes
  { condition: '2 bedrooms; zones R4, R3', value_min: 1.5 },       // noqa: zone-codes
  { condition: '3 or more bedrooms; zones R4, R3', value_min: 2 }, // noqa: zone-codes
  { condition: 'visitor parking; zones R4, R3', value_min: 0.25 }, // noqa: zone-codes
].map((r) => ({
  control_type: 'car_parking',
  control_label: 'Car parking',
  direction: 'min' as const,
  value_min: r.value_min,
  value_max: null,
  unit: 'spaces',
  section_ref: '4.2.1', // deliberately IDENTICAL across all four
  condition: r.condition,
  data_status: 'numeric' as const,
}));

function mockControls(controls: unknown[]) {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      has_controls: true,
      categories: [{ category: 'Parking', controls }],
    }),
  }) as unknown as typeof fetch;
}

describe('DcpSnapshotCard — show them all, with their conditions', () => {
  afterEach(() => jest.resetAllMocks());

  it('renders the condition beside every value, so the reader can tell which applies', async () => {
    mockControls(PARKING_ROWS);
    render(<DcpSnapshotCard lgaName="Sutherland Shire" councilSlug="sutherland_shire" />);

    await waitFor(() => expect(screen.getByText(/1 bedroom/)).toBeInTheDocument());
    // Each condition present: without these, four numbers read as contradictory.
    expect(screen.getByText(/2 bedrooms/)).toBeInTheDocument();
    expect(screen.getByText(/3 or more bedrooms/)).toBeInTheDocument();
    expect(screen.getByText(/visitor parking/)).toBeInTheDocument();
  });

  it('draws every row even when control_type and section_ref are identical', async () => {
    mockControls(PARKING_ROWS);
    render(<DcpSnapshotCard lgaName="Sutherland Shire" councilSlug="sutherland_shire" />);

    // The old key was `${control_type}-${section_ref}`, which all four share,
    // so React kept ONE. All four distinct values must appear.
    await waitFor(() => expect(screen.getByText(/≥ 1 spaces/)).toBeInTheDocument());
    expect(screen.getByText(/≥ 1.5 spaces/)).toBeInTheDocument();
    expect(screen.getByText(/≥ 2 spaces/)).toBeInTheDocument();
    expect(screen.getByText(/≥ 0.25 spaces/)).toBeInTheDocument();
  });

  it('says how many controls it is not showing rather than truncating silently', async () => {
    // Nine rows against a cap of six: three are hidden and the reader must be told.
    const nine = Array.from({ length: 9 }, (_, i) => ({
      ...PARKING_ROWS[0],
      value_min: i + 1,
      section_ref: `4.2.${i}`,
      condition: `case ${i}`,
    }));
    mockControls(nine);
    render(<DcpSnapshotCard lgaName="Sutherland Shire" councilSlug="sutherland_shire" />);

    await waitFor(() =>
      expect(screen.getByText(/Showing 6 of 9 controls/i)).toBeInTheDocument(),
    );
  });

  it('shows no truncation notice when everything fits', async () => {
    mockControls(PARKING_ROWS); // four rows, cap is six
    render(<DcpSnapshotCard lgaName="Sutherland Shire" councilSlug="sutherland_shire" />);

    await waitFor(() => expect(screen.getByText(/1 bedroom/)).toBeInTheDocument());
    expect(screen.queryByText(/Showing \d+ of \d+ controls/i)).not.toBeInTheDocument();
  });

  it('does not claim the numbers apply to any building when they carry conditions', async () => {
    mockControls(PARKING_ROWS);
    render(<DcpSnapshotCard lgaName="Sutherland Shire" councilSlug="sutherland_shire" />);

    await waitFor(() => expect(screen.getByText(/1 bedroom/)).toBeInTheDocument());
    // The old copy asserted these "apply to any residential building on this
    // block", which is false for a row gated on bedroom count.
    expect(
      screen.queryByText(/apply to any residential building on this block/i),
    ).not.toBeInTheDocument();
  });
});
