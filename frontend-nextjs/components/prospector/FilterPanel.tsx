'use client';

/**
 * Prospector filter panel — left sidebar with all lot search filters.
 * Controlled component: receives filter state, emits partial updates.
 */

import React from 'react';

import {
  ProspectorFilters,
  TriState,
  ConfidenceFilter,
  OrderCol,
  ORDER_COLUMNS,
} from '@/lib/prospector/filter-params';

interface FilterPanelProps {
  filters: ProspectorFilters;
  zoneOptions: string[];
  bindingOptions: string[];
  onChange: (partial: Partial<ProspectorFilters>) => void;
  onReset: () => void;
}

const TRI_STATE_OPTIONS: Array<{ value: TriState; label: string }> = [
  { value: 'any', label: 'Any' },
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' },
];

function numberOrNull(raw: string): number | null {
  if (raw.trim() === '') return null;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}

/**
 * Number input that debounces commits — prevents a URL push and API request
 * on every keystroke (the search endpoint is rate limited to 20 req/min).
 * Commits after 400 ms idle, or immediately on blur.
 */
function DebouncedNumberInput({
  value,
  onCommit,
  integer = false,
  ...inputProps
}: {
  value: number | null;
  onCommit: (v: number | null) => void;
  integer?: boolean;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'onBlur' | 'type'>) {
  const [raw, setRaw] = React.useState<string>(value != null ? String(value) : '');
  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync from external state (URL navigation, reset)
  React.useEffect(() => {
    setRaw(value != null ? String(value) : '');
  }, [value]);

  const parse = React.useCallback(
    (s: string): number | null => {
      const n = numberOrNull(s);
      return n != null && integer ? Math.floor(n) : n;
    },
    [integer],
  );

  const commit = React.useCallback(
    (s: string) => {
      const parsed = parse(s);
      if (parsed !== value) onCommit(parsed);
    },
    [parse, value, onCommit],
  );

  React.useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return (
    <input
      type="number"
      value={raw}
      onChange={(e) => {
        const next = e.target.value;
        setRaw(next);
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => commit(next), 400);
      }}
      onBlur={() => {
        if (timerRef.current) clearTimeout(timerRef.current);
        commit(raw);
      }}
      {...inputProps}
    />
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
      {children}
    </p>
  );
}

function TriStateToggle({
  label,
  value,
  onChange,
}: {
  label: string;
  value: TriState;
  onChange: (v: TriState) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-sm text-gray-700">{label}</span>
      <div className="flex rounded-md border border-gray-300 overflow-hidden" role="group" aria-label={label}>
        {TRI_STATE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            aria-pressed={value === opt.value}
            className={`px-2.5 py-1 text-xs transition-colors ${
              value === opt.value
                ? 'bg-teal-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function RangeInputs({
  label,
  min,
  max,
  onMinChange,
  onMaxChange,
}: {
  label: string;
  min: number | null;
  max: number | null;
  onMinChange: (v: number | null) => void;
  onMaxChange: (v: number | null) => void;
}) {
  return (
    <div>
      <SectionLabel>{label}</SectionLabel>
      <div className="flex items-center gap-2">
        <DebouncedNumberInput
          min={0}
          placeholder="Min"
          aria-label={`${label} minimum`}
          value={min}
          onCommit={onMinChange}
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
        <span className="text-gray-400 text-sm">–</span>
        <DebouncedNumberInput
          min={0}
          placeholder="Max"
          aria-label={`${label} maximum`}
          value={max}
          onCommit={onMaxChange}
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
      </div>
    </div>
  );
}

function CheckboxList({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const toggle = (value: string) => {
    onChange(
      selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value],
    );
  };

  return (
    <div>
      <SectionLabel>{label}</SectionLabel>
      {options.length === 0 ? (
        <p className="text-xs text-gray-400">No options available</p>
      ) : (
        <div className="max-h-44 overflow-y-auto border border-gray-200 rounded-md p-2 space-y-1">
          {options.map((opt) => (
            <label key={opt} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={selected.includes(opt)}
                onChange={() => toggle(opt)}
                className="rounded border-gray-300 text-teal-600 focus:ring-teal-500"
              />
              {opt}
            </label>
          ))}
        </div>
      )}
      {selected.length > 0 && (
        <button
          type="button"
          onClick={() => onChange([])}
          className="text-xs text-teal-700 hover:text-teal-900 underline mt-1"
        >
          Clear {label.toLowerCase()} selection
        </button>
      )}
    </div>
  );
}

export function FilterPanel({
  filters,
  zoneOptions,
  bindingOptions,
  onChange,
  onReset,
}: FilterPanelProps) {
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Filters</h2>
        <button
          type="button"
          onClick={onReset}
          className="text-xs text-gray-500 hover:text-gray-700 underline"
        >
          Reset all filters
        </button>
      </div>

      {/* LGA — single option for now, expands as more LGAs are indexed */}
      <div>
        <SectionLabel>Council area</SectionLabel>
        <select
          value={filters.lga_name}
          onChange={(e) => onChange({ lga_name: e.target.value })}
          aria-label="Council area"
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="INNER WEST">Inner West</option>
        </select>
      </div>

      <CheckboxList
        label="Zones"
        options={zoneOptions}
        selected={filters.zone_codes}
        onChange={(zone_codes) => onChange({ zone_codes })}
      />

      <RangeInputs
        label="Lot area (m²)"
        min={filters.min_area_m2}
        max={filters.max_area_m2}
        onMinChange={(min_area_m2) => onChange({ min_area_m2 })}
        onMaxChange={(max_area_m2) => onChange({ max_area_m2 })}
      />

      <RangeInputs
        label="Indicative GFA (m²)"
        min={filters.min_gfa_m2}
        max={filters.max_gfa_m2}
        onMinChange={(min_gfa_m2) => onChange({ min_gfa_m2 })}
        onMaxChange={(max_gfa_m2) => onChange({ max_gfa_m2 })}
      />

      <div>
        <SectionLabel>Minimum dwellings</SectionLabel>
        <DebouncedNumberInput
          min={1}
          placeholder="Any"
          aria-label="Minimum dwellings"
          integer
          value={filters.min_dwellings}
          onCommit={(min_dwellings) => onChange({ min_dwellings })}
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
      </div>

      <div className="space-y-2">
        <SectionLabel>Constraints</SectionLabel>
        <TriStateToggle
          label="Heritage"
          value={filters.heritage}
          onChange={(heritage) => onChange({ heritage })}
        />
        <TriStateToggle
          label="Flood planning area"
          value={filters.flood_prone}
          onChange={(flood_prone) => onChange({ flood_prone })}
        />
        <TriStateToggle
          label="Bushfire prone land"
          value={filters.bushfire_prone}
          onChange={(bushfire_prone) => onChange({ bushfire_prone })}
        />
      </div>

      <div>
        <SectionLabel>Minimum confidence</SectionLabel>
        <select
          value={filters.min_confidence}
          onChange={(e) => onChange({ min_confidence: e.target.value as ConfidenceFilter })}
          aria-label="Minimum confidence"
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="any">Any confidence level</option>
          <option value="low">Low or above</option>
          <option value="medium">Medium or above</option>
          <option value="high">High only</option>
        </select>
      </div>

      <CheckboxList
        label="Binding constraint"
        options={bindingOptions}
        selected={filters.binding_constraint}
        onChange={(binding_constraint) => onChange({ binding_constraint })}
      />

      <div>
        <SectionLabel>Order results by</SectionLabel>
        <div className="flex gap-2">
          <select
            value={filters.order_by}
            onChange={(e) => onChange({ order_by: e.target.value as OrderCol })}
            aria-label="Order results by"
            className="flex-1 px-2.5 py-1.5 text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            {(Object.entries(ORDER_COLUMNS) as Array<[OrderCol, string]>).map(([col, label]) => (
              <option key={col} value={col}>
                {label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => onChange({ order_dir: filters.order_dir === 'asc' ? 'desc' : 'asc' })}
            aria-label={`Sort direction: ${filters.order_dir === 'asc' ? 'ascending' : 'descending'}`}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md bg-white text-gray-700 hover:bg-gray-50"
          >
            {filters.order_dir === 'asc' ? '↑ Ascending' : '↓ Descending'}
          </button>
        </div>
      </div>
    </div>
  );
}
