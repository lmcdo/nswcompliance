/**
 * ProspectorClient component tests — rendering, sorting, pagination, errors.
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { SWRConfig } from 'swr';

import ProspectorClient from '@/components/prospector/ProspectorClient';

// --- next/navigation mock with capturable push -----------------------------

const mockPush = jest.fn();
let mockSearch = '';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => '/prospector',
  useSearchParams: () => new URLSearchParams(mockSearch),
}));

// --- fetch mock -------------------------------------------------------------

const SAMPLE_LOT = {
  lotidstring: '1//DP111111',
  lga_name: 'INNER WEST',
  zone_code: 'R3',
  lot_area_m2: 800,
  lep_height_m: 11,
  lep_fsr: 0.8,
  heritage: false,
  flood_prone: false,
  bushfire_prone: false,
  bushfire_category: null,
  ca_dev_type: 'multi_dwelling',
  ca_realistic_gfa_m2: 480,
  ca_realistic_dwellings: 3,
  ca_binding_constraint: 'lep_fsr',
  ca_confidence: 'high',
  ca_effective_height_m: 11,
  ca_effective_fsr: 0.8,
  ca_buildable_footprint_m2: 500,
  ca_setback_front_m: 6,
  ca_setback_rear_m: 6,
  ca_setback_side_m: 0.9,
  ca_gaps: ['dcp_setbacks_missing'],
};

const SEARCH_RESPONSE = { lots: [SAMPLE_LOT], total_count: 120, query_ms: 42 };

const SUMMARY_RESPONSE = {
  total_lots: 120,
  lots_with_ca: 117,
  avg_area_m2: 512.3,
  avg_gfa_m2: 410.5,
  median_gfa_m2: 395.0,
  p25_gfa_m2: 250.1,
  p75_gfa_m2: 520.9,
  avg_dwellings: 2.4,
  heritage_count: 14,
  flood_count: 9,
  bushfire_count: 2,
  confidence_high: 80,
  confidence_medium: 30,
  confidence_low: 10,
  zone_distribution: [
    { zone_code: 'R2', count: 70 },
    { zone_code: 'R3', count: 50 },
  ],
  binding_distribution: [
    { ca_binding_constraint: 'lep_fsr', count: 90 },
    { ca_binding_constraint: 'lep_height', count: 27 },
  ],
  dev_type_distribution: [{ ca_dev_type: 'multi_dwelling', count: 60 }],
  query_ms: 17,
};

function mockFetchOk() {
  return jest.fn(async (url: string) => ({
    ok: true,
    json: async () => (String(url).includes('summary=true') ? SUMMARY_RESPONSE : SEARCH_RESPONSE),
  })) as unknown as typeof fetch;
}

function renderClient() {
  // Fresh SWR cache per render so tests don't share fetched state
  return render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <ProspectorClient />
    </SWRConfig>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  mockSearch = '';
  global.fetch = mockFetchOk();
});

describe('ProspectorClient', () => {
  test('renders lot rows and result range after fetch', async () => {
    renderClient();

    expect(await screen.findByText('1//DP111111')).toBeInTheDocument();
    expect(screen.getByText('1–50 of 120 lots')).toBeInTheDocument();
  });

  test('renders summary statistics', async () => {
    renderClient();

    expect(await screen.findByText('Lots matching filters')).toBeInTheDocument();
    // lots_with_ca = 117 → 98% of 120
    expect(screen.getByText('98% of matching lots')).toBeInTheDocument();
    expect(screen.getByText('Zone distribution')).toBeInTheDocument();
  });

  test('zone filter options derive from summary distribution', async () => {
    renderClient();

    expect(await screen.findByLabelText('R2')).toBeInTheDocument();
    expect(screen.getByLabelText('R3')).toBeInTheDocument();
  });

  test('clicking the active sort column toggles direction in URL', async () => {
    renderClient();
    await screen.findByText('1//DP111111');

    // Default order is GFA desc → clicking GFA toggles to asc
    fireEvent.click(screen.getByRole('button', { name: 'Sort by GFA (m²)' }));

    expect(mockPush).toHaveBeenCalledWith('/prospector?order_dir=asc', { scroll: false });
  });

  test('clicking a different sort column sets it with desc direction', async () => {
    renderClient();
    await screen.findByText('1//DP111111');

    fireEvent.click(screen.getByRole('button', { name: 'Sort by Area (m²)' }));

    expect(mockPush).toHaveBeenCalledWith('/prospector?order_by=lot_area_m2', { scroll: false });
  });

  test('next page pushes page=2 to URL', async () => {
    renderClient();
    await screen.findByText('1//DP111111');

    fireEvent.click(screen.getByRole('button', { name: 'Next page' }));

    expect(mockPush).toHaveBeenCalledWith('/prospector?page=2', { scroll: false });
  });

  test('changing a filter resets the page to 1', async () => {
    mockSearch = 'page=3';
    renderClient();
    await screen.findByText('1//DP111111');

    fireEvent.click(screen.getByRole('button', { name: 'Sort by Area (m²)' }));

    const pushedUrl: string = mockPush.mock.calls[0][0];
    expect(pushedUrl).toContain('order_by=lot_area_m2');
    expect(pushedUrl).not.toContain('page=');
  });

  test('filters from URL are sent in the search request body', async () => {
    mockSearch = 'zones=R3&min_area=400&heritage=no&page=2';
    renderClient();
    await screen.findByText('1//DP111111');

    const fetchMock = global.fetch as jest.Mock;
    const searchCall = fetchMock.mock.calls.find(
      ([url]: [string]) => !String(url).includes('summary=true'),
    );
    expect(searchCall).toBeDefined();
    const body = JSON.parse(searchCall[1].body);
    expect(body.zone_codes).toEqual(['R3']);
    expect(body.min_area_m2).toBe(400);
    expect(body.heritage).toBe(false);
    expect(body.offset).toBe(50);
    expect(body.limit).toBe(50);
  });

  test('clicking a row expands constraint detail', async () => {
    renderClient();
    await screen.findByText('1//DP111111');

    fireEvent.click(screen.getByTestId('lot-row-1//DP111111'));

    expect(await screen.findByTestId('expanded-1//DP111111')).toBeInTheDocument();
    expect(screen.getByText('Development type')).toBeInTheDocument();
    expect(screen.getByText('multi_dwelling')).toBeInTheDocument();
    expect(screen.getByText('dcp_setbacks_missing')).toBeInTheDocument();
  });

  test('API error renders an alert with the server message', async () => {
    global.fetch = jest.fn(async () => ({
      ok: false,
      status: 504,
      json: async () => ({ error: 'Query timed out — try narrowing your filters' }),
    })) as unknown as typeof fetch;

    renderClient();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Query timed out — try narrowing your filters');
  });

  test('numeric filter input debounces URL updates instead of pushing per keystroke', async () => {
    jest.useFakeTimers();
    try {
      renderClient();
      // findBy* uses real timers internally via waitFor — query directly after flushing microtasks
      const input = await screen.findByLabelText('Lot area (m²) minimum');

      fireEvent.change(input, { target: { value: '4' } });
      fireEvent.change(input, { target: { value: '45' } });
      fireEvent.change(input, { target: { value: '450' } });
      expect(mockPush).not.toHaveBeenCalled();

      jest.advanceTimersByTime(400);
      expect(mockPush).toHaveBeenCalledTimes(1);
      expect(mockPush).toHaveBeenCalledWith('/prospector?min_area=450', { scroll: false });
    } finally {
      jest.useRealTimers();
    }
  });

  test('numeric filter input commits immediately on blur', async () => {
    renderClient();
    const input = await screen.findByLabelText('Indicative GFA (m²) maximum');

    fireEvent.change(input, { target: { value: '600' } });
    fireEvent.blur(input);

    expect(mockPush).toHaveBeenCalledTimes(1);
    expect(mockPush).toHaveBeenCalledWith('/prospector?max_gfa=600', { scroll: false });
  });

  test('stale page beyond the result set shows a corrective message, not a bogus range', async () => {
    mockSearch = 'page=9';
    global.fetch = jest.fn(async (url: string) => ({
      ok: true,
      json: async () =>
        String(url).includes('summary=true')
          ? SUMMARY_RESPONSE
          : { lots: [], total_count: 120, query_ms: 5 },
    })) as unknown as typeof fetch;

    renderClient();

    expect(
      await screen.findByText('No results on this page — 120 lots match'),
    ).toBeInTheDocument();
  });

  test('empty result set shows the no-results row', async () => {
    global.fetch = jest.fn(async (url: string) => ({
      ok: true,
      json: async () =>
        String(url).includes('summary=true')
          ? { ...SUMMARY_RESPONSE, total_lots: 0, lots_with_ca: 0, zone_distribution: [], binding_distribution: [] }
          : { lots: [], total_count: 0, query_ms: 5 },
    })) as unknown as typeof fetch;

    renderClient();

    expect(
      await screen.findByText('No lots match the current filters'),
    ).toBeInTheDocument();
    expect(screen.getByText(/No results/)).toBeInTheDocument();
  });
});
