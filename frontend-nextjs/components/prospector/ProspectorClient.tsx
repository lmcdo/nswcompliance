'use client';

/**
 * Prospector page client — orchestrates filter state (URL-backed), SWR data
 * fetching for search + summary modes, and renders the three panels.
 */

import React, { useCallback, useMemo } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import useSWR from 'swr';
import { AlertCircle } from 'lucide-react';

import { trackProspectorSearch } from '@/lib/analytics';
import { FilterPanel } from '@/components/prospector/FilterPanel';
import { ResultsTable } from '@/components/prospector/ResultsTable';
import { SaveSearchCard } from '@/components/prospector/SaveSearchCard';
import { SummaryDashboard } from '@/components/prospector/SummaryDashboard';
import {
  DEFAULT_FILTERS,
  OrderCol,
  ProspectorFilters,
  SearchResponse,
  SummaryResponse,
  buildSearchBody,
  buildSummaryBody,
  parseFilters,
  serializeFilters,
} from '@/lib/prospector/filter-params';

// ---------------------------------------------------------------------------
// Fetcher — SWR key is [url, serialised body]
// ---------------------------------------------------------------------------

async function postFetcher<T>([url, bodyJson]: [string, string]): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: bodyJson,
  });
  if (!res.ok) {
    let message = `Request failed with status ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data?.error === 'string') message = data.error;
    } catch {
      // keep status-based message
    }
    throw new Error(message);
  }
  return res.json();
}

export default function ProspectorClient() {
  const router = useRouter();
  const pathname = usePathname() ?? '/prospector';
  const searchParams = useSearchParams();

  const filters = useMemo(
    () => parseFilters(new URLSearchParams(searchParams?.toString() ?? '')),
    [searchParams],
  );

  // -------------------------------------------------------------------------
  // URL state updates
  // -------------------------------------------------------------------------

  const applyFilters = useCallback(
    (next: ProspectorFilters) => {
      const qs = serializeFilters(next).toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [router, pathname],
  );

  const updateFilters = useCallback(
    (partial: Partial<ProspectorFilters>) => {
      // Any filter change other than pagination resets to page 1
      const isPageOnly = Object.keys(partial).length === 1 && 'page' in partial;
      applyFilters({ ...filters, ...partial, ...(isPageOnly ? {} : { page: 1 }) });
    },
    [filters, applyFilters],
  );

  const handleSort = useCallback(
    (col: OrderCol) => {
      if (filters.order_by === col) {
        updateFilters({ order_dir: filters.order_dir === 'asc' ? 'desc' : 'asc' });
      } else {
        updateFilters({ order_by: col, order_dir: 'desc' });
      }
    },
    [filters.order_by, filters.order_dir, updateFilters],
  );

  // -------------------------------------------------------------------------
  // Data fetching
  // -------------------------------------------------------------------------

  const searchKey: [string, string] = [
    '/api/lot-search',
    JSON.stringify(buildSearchBody(filters)),
  ];
  const summaryKey: [string, string] = [
    '/api/lot-search?summary=true',
    JSON.stringify(buildSummaryBody(filters)),
  ];
  // Filter options come from an unfiltered summary (LGA scope only) so the
  // zone and binding constraint lists do not shrink as filters are applied.
  const optionsKey: [string, string] = [
    '/api/lot-search?summary=true',
    JSON.stringify(buildSummaryBody({ ...DEFAULT_FILTERS, lga_name: filters.lga_name })),
  ];

  // shouldRetryOnError: false — the API is rate limited (20 req/60s); SWR's
  // default exponential-backoff retry would re-POST after a 429 and dig the
  // user deeper into the limit.
  const search = useSWR<SearchResponse>(searchKey, postFetcher, {
    keepPreviousData: true,
    revalidateOnFocus: false,
    shouldRetryOnError: false,
    // PostHog funnel step: pageview -> prospector_search -> (capture).
    // onSuccess fires once per completed search (landing + each filter change);
    // revalidateOnFocus is off so it does not double-fire on tab switches.
    onSuccess: (data) => {
      trackProspectorSearch({
        lga: filters.lga_name,
        zone_codes: filters.zone_codes,
        has_heritage_filter: filters.heritage !== null,
        has_flood_filter: filters.flood_prone !== null,
        result_count: data.total_count ?? 0,
        query_ms: data.query_ms ?? null,
        page: filters.page,
      });
    },
  });
  const summary = useSWR<SummaryResponse>(summaryKey, postFetcher, {
    keepPreviousData: true,
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });
  const options = useSWR<SummaryResponse>(optionsKey, postFetcher, {
    revalidateOnFocus: false,
    revalidateIfStale: false,
    shouldRetryOnError: false,
  });

  const zoneOptions = useMemo(
    () =>
      (options.data?.zone_distribution ?? [])
        .map((z) => z.zone_code)
        .filter((z): z is string => z != null)
        .sort(),
    [options.data],
  );
  const bindingOptions = useMemo(
    () =>
      (options.data?.binding_distribution ?? [])
        .map((b) => b.ca_binding_constraint)
        .filter((b): b is string => b != null)
        .sort(),
    [options.data],
  );

  const error = search.error ?? summary.error;

  return (
    <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Prospector</h1>
        <p className="mt-1 text-sm text-gray-500">
          Bulk lot search across the Inner West with pre-computed development envelope
          arithmetic. Figures are derived from LEP controls and mapped constraint layers —
          site-specific factors are not assessed.
        </p>
      </div>

      {error && (
        <div
          className="mb-4 flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
          role="alert"
        >
          <AlertCircle size={16} />
          {error instanceof Error ? error.message : 'Search request failed'}
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Filter sidebar */}
        <aside className="lg:w-72 shrink-0">
          <div className="lg:sticky lg:top-4 space-y-4">
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <FilterPanel
                filters={filters}
                zoneOptions={zoneOptions}
                bindingOptions={bindingOptions}
                onChange={updateFilters}
                onReset={() => applyFilters({ ...DEFAULT_FILTERS, lga_name: filters.lga_name })}
              />
            </div>
            <SaveSearchCard
              lgaName={filters.lga_name}
              filterQuery={serializeFilters(filters).toString()}
            />
          </div>
        </aside>

        {/* Main content */}
        <div className="flex-1 min-w-0 space-y-6">
          <SummaryDashboard summary={summary.data} isLoading={summary.isLoading} />
          <ResultsTable
            lots={search.data?.lots ?? []}
            totalCount={search.data?.total_count ?? 0}
            page={filters.page}
            orderBy={filters.order_by}
            orderDir={filters.order_dir}
            isLoading={search.isLoading}
            queryMs={search.data?.query_ms ?? null}
            onSort={handleSort}
            onPageChange={(page) => updateFilters({ page })}
          />
        </div>
      </div>
    </div>
  );
}
