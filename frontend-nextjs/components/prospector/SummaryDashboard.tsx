'use client';

/**
 * Prospector summary dashboard — aggregate statistics for the current filter set.
 * Data comes from POST /api/lot-search?summary=true.
 */

import React from 'react';

import { SummaryResponse } from '@/lib/prospector/filter-params';

interface SummaryDashboardProps {
  summary: SummaryResponse | undefined;
  isLoading: boolean;
}

function formatNumber(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('en-AU');
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-lg font-semibold text-gray-900 mt-0.5">{value}</p>
      {sub != null && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function DistributionBars({
  title,
  entries,
  total,
}: {
  title: string;
  entries: Array<{ label: string; count: number }>;
  total: number;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
      <p className="text-xs text-gray-500 mb-2">{title}</p>
      {entries.length === 0 ? (
        <p className="text-xs text-gray-400">No data for current filters</p>
      ) : (
        <div className="space-y-1.5">
          {entries.slice(0, 8).map(({ label, count }) => {
            const pct = total > 0 ? Math.round((count / total) * 100) : 0;
            return (
              <div key={label} className="flex items-center gap-2">
                <span className="w-28 shrink-0 text-xs text-gray-700 truncate" title={label}>
                  {label}
                </span>
                <div className="flex-1 h-3 bg-gray-100 rounded-sm overflow-hidden">
                  <div
                    className="h-full bg-teal-500"
                    style={{ width: `${Math.max(pct, count > 0 ? 1 : 0)}%` }}
                  />
                </div>
                <span className="w-16 shrink-0 text-right text-xs text-gray-500">
                  {formatNumber(count)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function SummaryDashboard({ summary, isLoading }: SummaryDashboardProps) {
  if (isLoading || !summary) {
    return (
      <div
        className="grid grid-cols-2 sm:grid-cols-4 gap-3 animate-pulse"
        data-testid="summary-skeleton"
      >
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="bg-gray-100 border border-gray-200 rounded-lg h-[72px]" />
        ))}
      </div>
    );
  }

  const caPct =
    summary.total_lots > 0
      ? Math.round((summary.lots_with_ca / summary.total_lots) * 100)
      : 0;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Lots matching filters" value={formatNumber(summary.total_lots)} />
        <StatCard
          label="Lots with constraint arithmetic"
          value={formatNumber(summary.lots_with_ca)}
          sub={`${caPct}% of matching lots`}
        />
        <StatCard
          label="Average indicative GFA"
          value={summary.avg_gfa_m2 != null ? `${formatNumber(summary.avg_gfa_m2)} m²` : '—'}
        />
        <StatCard
          label="Median indicative GFA"
          value={summary.median_gfa_m2 != null ? `${formatNumber(summary.median_gfa_m2)} m²` : '—'}
          sub={
            summary.p25_gfa_m2 != null && summary.p75_gfa_m2 != null
              ? `p25 ${formatNumber(summary.p25_gfa_m2)} · p75 ${formatNumber(summary.p75_gfa_m2)}`
              : undefined
          }
        />
        <StatCard label="Heritage lots" value={formatNumber(summary.heritage_count)} />
        <StatCard label="Flood planning area lots" value={formatNumber(summary.flood_count)} />
        <StatCard label="Bushfire prone lots" value={formatNumber(summary.bushfire_count)} />
        <StatCard
          label="Confidence breakdown"
          value={`${formatNumber(summary.confidence_high)} high`}
          sub={`${formatNumber(summary.confidence_medium)} medium · ${formatNumber(summary.confidence_low)} low`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <DistributionBars
          title="Zone distribution"
          entries={summary.zone_distribution.map((z) => ({ label: z.zone_code, count: z.count }))}
          total={summary.total_lots}
        />
        <DistributionBars
          title="Binding constraint distribution"
          entries={summary.binding_distribution.map((b) => ({
            label: b.ca_binding_constraint,
            count: b.count,
          }))}
          total={summary.lots_with_ca}
        />
      </div>

      <p className="text-xs text-gray-400 text-right">
        {summary.index_refreshed_at && (
          <>
            Index data refreshed{' '}
            {new Date(summary.index_refreshed_at).toLocaleDateString('en-AU', {
              day: 'numeric', month: 'short', year: 'numeric',
            })}
            {' · '}
          </>
        )}
        Summary query completed in {summary.query_ms} ms
      </p>
    </div>
  );
}
