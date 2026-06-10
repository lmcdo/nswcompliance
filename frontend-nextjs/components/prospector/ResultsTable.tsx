'use client';

/**
 * Prospector results table — sortable columns, expandable rows, pagination.
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp } from 'lucide-react';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  LotResult,
  OrderCol,
  OrderDir,
  PAGE_SIZE,
} from '@/lib/prospector/filter-params';

interface ResultsTableProps {
  lots: LotResult[];
  totalCount: number;
  page: number;
  orderBy: OrderCol;
  orderDir: OrderDir;
  isLoading: boolean;
  queryMs: number | null;
  onSort: (col: OrderCol) => void;
  onPageChange: (page: number) => void;
}

function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—';
  return value.toLocaleString('en-AU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

function formatGaps(gaps: unknown): string {
  if (gaps == null) return 'None recorded';
  if (Array.isArray(gaps)) return gaps.length > 0 ? gaps.join(', ') : 'None recorded';
  if (typeof gaps === 'string') return gaps;
  return JSON.stringify(gaps);
}

const SORTABLE_COLUMNS: Array<{ col: OrderCol; label: string; align: 'left' | 'right' }> = [
  { col: 'lot_area_m2', label: 'Area (m²)', align: 'right' },
  { col: 'lep_fsr', label: 'FSR', align: 'right' },
  { col: 'lep_height_m', label: 'Height (m)', align: 'right' },
  { col: 'ca_realistic_gfa_m2', label: 'GFA (m²)', align: 'right' },
  { col: 'ca_realistic_dwellings', label: 'Dwellings', align: 'right' },
];

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm text-gray-900">{value}</p>
    </div>
  );
}

function ExpandedRow({ lot }: { lot: LotResult }) {
  return (
    <tr className="bg-gray-50 border-b" data-testid={`expanded-${lot.lotidstring}`}>
      <td colSpan={10} className="px-4 py-3">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-3">
          <DetailItem label="Development type" value={lot.ca_dev_type ?? '—'} />
          <DetailItem
            label="Effective height"
            value={lot.ca_effective_height_m != null ? `${formatNumber(lot.ca_effective_height_m, 1)} m` : '—'}
          />
          <DetailItem
            label="Effective FSR"
            value={lot.ca_effective_fsr != null ? formatNumber(lot.ca_effective_fsr, 2) : '—'}
          />
          <DetailItem
            label="Buildable footprint"
            value={
              lot.ca_buildable_footprint_m2 != null
                ? `${formatNumber(lot.ca_buildable_footprint_m2, 1)} m²`
                : '—'
            }
          />
          <DetailItem
            label="Front setback"
            value={lot.ca_setback_front_m != null ? `${formatNumber(lot.ca_setback_front_m, 1)} m` : '—'}
          />
          <DetailItem
            label="Rear setback"
            value={lot.ca_setback_rear_m != null ? `${formatNumber(lot.ca_setback_rear_m, 1)} m` : '—'}
          />
          <DetailItem
            label="Side setback"
            value={lot.ca_setback_side_m != null ? `${formatNumber(lot.ca_setback_side_m, 1)} m` : '—'}
          />
          <DetailItem
            label="Bushfire category"
            value={lot.bushfire_category ?? '—'}
          />
          <div className="col-span-2 sm:col-span-4">
            <DetailItem label="Data gaps" value={formatGaps(lot.ca_gaps)} />
          </div>
        </div>
      </td>
    </tr>
  );
}

export function ResultsTable({
  lots,
  totalCount,
  page,
  orderBy,
  orderDir,
  isLoading,
  queryMs,
  onSort,
  onPageChange,
}: ResultsTableProps) {
  const [expandedLot, setExpandedLot] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const rangeStart = totalCount === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(page * PAGE_SIZE, totalCount);

  const sortIndicator = (col: OrderCol) => {
    if (col !== orderBy) return null;
    return orderDir === 'asc' ? (
      <ChevronUp size={14} className="inline ml-0.5" />
    ) : (
      <ChevronDown size={14} className="inline ml-0.5" />
    );
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8" />
            <TableHead>Lot ID</TableHead>
            <TableHead>Zone</TableHead>
            {SORTABLE_COLUMNS.map(({ col, label, align }) => (
              <TableHead key={col} className={align === 'right' ? 'text-right' : ''}>
                <button
                  type="button"
                  onClick={() => onSort(col)}
                  className="hover:text-teal-700 font-medium"
                  aria-label={`Sort by ${label}`}
                >
                  {label}
                  {sortIndicator(col)}
                </button>
              </TableHead>
            ))}
            <TableHead>Binding constraint</TableHead>
            <TableHead>Confidence</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            Array.from({ length: 10 }).map((_, i) => (
              <TableRow key={i} data-testid="skeleton-row">
                {Array.from({ length: 10 }).map((__, j) => (
                  <TableCell key={j}>
                    <div className="h-4 bg-gray-100 rounded animate-pulse" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : lots.length === 0 ? (
            <TableRow>
              <TableCell colSpan={10} className="text-center text-sm text-gray-500 py-8">
                No lots match the current filters
              </TableCell>
            </TableRow>
          ) : (
            lots.map((lot) => (
              <React.Fragment key={lot.lotidstring}>
                <TableRow
                  onClick={() =>
                    setExpandedLot(expandedLot === lot.lotidstring ? null : lot.lotidstring)
                  }
                  className="cursor-pointer"
                  data-testid={`lot-row-${lot.lotidstring}`}
                >
                  <TableCell className="text-gray-400">
                    {expandedLot === lot.lotidstring ? (
                      <ChevronUp size={14} />
                    ) : (
                      <ChevronDown size={14} />
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{lot.lotidstring}</TableCell>
                  <TableCell>{lot.zone_code ?? '—'}</TableCell>
                  <TableCell className="text-right">{formatNumber(lot.lot_area_m2)}</TableCell>
                  <TableCell className="text-right">{formatNumber(lot.lep_fsr, 2)}</TableCell>
                  <TableCell className="text-right">{formatNumber(lot.lep_height_m, 1)}</TableCell>
                  <TableCell className="text-right">
                    {formatNumber(lot.ca_realistic_gfa_m2)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(lot.ca_realistic_dwellings)}
                  </TableCell>
                  <TableCell className="text-xs">{lot.ca_binding_constraint ?? '—'}</TableCell>
                  <TableCell>
                    {lot.ca_confidence ? (
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          lot.ca_confidence === 'high'
                            ? 'bg-teal-50 text-teal-700'
                            : lot.ca_confidence === 'medium'
                              ? 'bg-amber-50 text-amber-700'
                              : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {lot.ca_confidence}
                      </span>
                    ) : (
                      '—'
                    )}
                  </TableCell>
                </TableRow>
                {expandedLot === lot.lotidstring && <ExpandedRow lot={lot} />}
              </React.Fragment>
            ))
          )}
        </TableBody>
      </Table>

      {/* Pagination */}
      <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
        <p className="text-sm text-gray-600">
          {totalCount === 0
            ? 'No results'
            : rangeStart > totalCount
              ? `No results on this page — ${totalCount.toLocaleString('en-AU')} lots match`
              : `${rangeStart.toLocaleString('en-AU')}–${rangeEnd.toLocaleString('en-AU')} of ${totalCount.toLocaleString('en-AU')} lots`}
          {queryMs != null && <span className="text-gray-400"> · {queryMs} ms</span>}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1 || isLoading}
            aria-label="Previous page"
            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={14} /> Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {page.toLocaleString('en-AU')} of {totalPages.toLocaleString('en-AU')}
          </span>
          <button
            type="button"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || isLoading}
            aria-label="Next page"
            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
