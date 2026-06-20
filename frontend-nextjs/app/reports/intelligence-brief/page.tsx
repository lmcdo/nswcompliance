'use client';

import { useState, useCallback, useEffect, useRef, Suspense, type ReactNode } from 'react';
import { useSearchParams } from 'next/navigation';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { ConstraintArithmeticCard, type ConstraintArithmeticResult } from '@/components/compliance/ConstraintArithmeticCard';
import { cn } from '@/lib/utils';
import AerialTile from '@/components/reports/AerialTile';

// ---------------------------------------------------------------------------
// Types — match SSE events from Trigger.dev task (plotdetect-agents)
// ---------------------------------------------------------------------------

interface BriefMetadata {
  address: string;
  lat: number;
  lng: number;
  prop_id: number | null;
  run_date: string;
  include_satellite: boolean;
  include_premium: boolean;
}

interface BriefSection {
  section: string;
  data: Record<string, unknown>;
  progress: number;
  brief_type?: string;
}

interface BriefComplete {
  compound_constraints: Record<string, unknown>[];
  data_currency_warnings: string[];
  gaps: Array<{ field: string; reason?: string; verify_url?: string }>;
  confidence_summary: {
    total: number;
    authoritative: number;
    estimated: number;
    derived: number;
    not_available: number;
    extracted: number;
  };
  brief_type: string;
  elapsed_seconds: number;
  progress: number;
}

type BriefEvent =
  | { event: 'metadata'; data: BriefMetadata }
  | { event: 'section'; data: BriefSection }
  | { event: 'complete'; data: BriefComplete }
  | { event: 'error'; data: { message: string } };

type PageState = 'idle' | 'triggering' | 'streaming' | 'complete' | 'error';

// Section display metadata
const SECTION_LABELS: Record<string, { label: string; description: string }> = {
  economics: { label: 'Economics', description: 'Land value, lot area, valuation history' },
  strata: { label: 'Strata & Cadastre', description: 'Lot type, strata plan, ownership structure' },
  environmental_constraints: { label: 'Environmental Constraints', description: 'Overlays, heritage, contamination, mine subsidence' },
  planning_controls: { label: 'Planning Controls', description: 'Zoning, height, FSR, lot size, heritage items' },
  dcp_controls: { label: 'DCP Controls', description: 'Development control plan provisions' },
  sepp_housing: { label: 'SEPP Housing', description: 'State policy housing standards' },
  neighbourhood: { label: 'Neighbourhood', description: 'Nearby DAs, shadow analysis' },
  constraint_arithmetic: { label: 'Development Capacity', description: 'Indicative yield and the binding planning constraint' },
  'satellite.bushfire': { label: 'Bushfire Risk', description: 'Bushfire attack level, vegetation category' },
  'satellite.flood': { label: 'Flood Analysis', description: 'Multi-source flood occurrence screening' },
  'satellite.climate_disclosure': { label: 'Climate Disclosure', description: 'Heat island, rainfall intensity, fire hotspots' },
  'satellite.granny_flat': { label: 'Granny Flat Detection', description: 'Structure detection, SEPP eligibility' },
  'satellite.pre_da_history': { label: 'Pre-DA Site History', description: 'Historical development activity timeline' },
  'satellite.terrain': { label: 'Terrain Analysis', description: 'Slope, aspect and drainage from elevation' },
};

// Bento spans — the headline (development capacity) and the field-heavy sections
// get two columns; everything else is a single tile. Driving the layout off the
// section key keeps it stable as cards stream in at uneven heights.
const WIDE_SECTIONS = new Set(['constraint_arithmetic', 'planning_controls', 'environmental_constraints']);
function spanFor(section: string): string {
  return WIDE_SECTIONS.has(section) ? 'md:col-span-2' : 'col-span-1';
}

// Confidence level styling
function confidenceBadge(confidence: string) {
  switch (confidence) {
    case 'authoritative':
      return <span className="px-2 py-0.5 text-xs font-medium rounded bg-emerald-100 text-emerald-800">Authoritative</span>;
    case 'estimated':
      return <span className="px-2 py-0.5 text-xs font-medium rounded bg-amber-100 text-amber-800">Estimated</span>;
    case 'derived':
      return <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-800">Derived</span>;
    case 'extracted':
      return <span className="px-2 py-0.5 text-xs font-medium rounded bg-purple-100 text-purple-800">Extracted</span>;
    case 'not_available':
      return <span className="px-2 py-0.5 text-xs font-medium rounded bg-red-100 text-red-800">Not Available</span>;
    default:
      return <span className="px-2 py-0.5 text-xs font-medium rounded bg-slate-100 text-slate-600">{confidence}</span>;
  }
}

// ---------------------------------------------------------------------------
// Honest "why is this empty" mapping. NEVER show the raw internal reason
// string ("Layer not ingested for this LGA", "Premium data not requested") to
// a user — translate it into one of five plain states with an honest tone:
//   clear    — we checked, there's nothing here (good news for the owner)
//   optional — an add-on that wasn't requested
//   pending  — we haven't assessed this for this area yet (an honest gap)
//   error    — a genuine retrieval failure
//   neutral  — simply not part of this report
// ---------------------------------------------------------------------------
type UnavailableTone = 'clear' | 'optional' | 'pending' | 'error' | 'neutral';

// Satellite layers are opt-in behind the "Include satellite analysis" checkbox —
// so the real reason they're blank is that the box wasn't ticked, and the real
// path is to tick it and re-run. (Verified against include_satellite gating.)
const SATELLITE_SECTIONS = new Set([
  'satellite.bushfire', 'satellite.flood', 'satellite.climate_disclosure',
  'satellite.granny_flat', 'satellite.terrain',
]);

interface Unavailable { label: string; detail: string; tone: UnavailableTone; }

function describeUnavailable(reason?: string | null, section?: string): Unavailable {
  const r = (reason ?? '').toLowerCase();
  const isSatellite = !!section && (SATELLITE_SECTIONS.has(section) || section === 'satellite.bushfire');

  // Satellite opt-in layers — the box wasn't ticked. Real, actionable path.
  if (isSatellite) {
    return {
      label: 'Not run',
      detail: 'Tick “Include satellite analysis” above and run the brief again to add this.',
      tone: 'optional',
    };
  }
  // Pre-DA history needs the premium flag, which this page does not expose — so
  // there is no path here. Don't invent one.
  if (section === 'satellite.pre_da_history' || r.includes('premium')) {
    return {
      label: 'Not run',
      detail: 'Tick “Include site history (slower)” above and run the brief again to add this.',
      tone: 'optional',
    };
  }
  if (!r) return { label: 'Not included', detail: 'Not part of this brief.', tone: 'neutral' };
  if (r.includes('prop_id') || r.includes('could not') || r.includes('couldn')) {
    return {
      label: 'Address not matched',
      detail: 'We could not match this address to a property in the NSW register — check the address.',
      tone: 'error',
    };
  }
  if (r.includes('not ingested') || r.includes('not yet') || r.includes('not onboarded')) {
    return {
      label: 'Not assessed',
      detail: 'This layer is not yet mapped for this council — confirm with the council or the NSW Planning Portal.',
      tone: 'pending',
    };
  }
  if (r.startsWith('no ') || r.includes('none found') || r.includes('at this location')) {
    return {
      label: 'None here',
      detail: 'Checked — nothing recorded at this property.',
      tone: 'clear',
    };
  }
  if (r.includes('not requested')) {
    return { label: 'Not run', detail: 'An optional add-on, not part of this brief.', tone: 'neutral' };
  }
  if (r.includes('fail') || r.includes('unavailable') || r.includes('error')) {
    return {
      label: 'Unavailable',
      detail: 'The data source did not respond — run the brief again to retry.',
      tone: 'error',
    };
  }
  return { label: 'Not included', detail: 'Not part of this brief.', tone: 'neutral' };
}

const UNAVAILABLE_TONE_STYLES: Record<UnavailableTone, string> = {
  clear: 'bg-emerald-50 text-emerald-700',
  optional: 'bg-teal-50 text-teal-700',
  pending: 'bg-slate-100 text-slate-500',
  error: 'bg-amber-50 text-amber-700',
  neutral: 'bg-slate-100 text-slate-500',
};

const UNAVAILABLE_TEXT_STYLES: Record<UnavailableTone, string> = {
  clear: 'text-emerald-700',
  optional: 'text-teal-700',
  pending: 'text-slate-400',
  error: 'text-amber-700',
  neutral: 'text-slate-400',
};

// Acronyms + units expanded in field labels; '' drops the word (internal terms).
const KEY_WORDS: Record<string, string> = {
  jrc: 'JRC', wofs: 'WOfS', bom: 'BoM', epi: 'EPI', anef: 'ANEF', gfa: 'GFA',
  fsr: 'FSR', lep: 'LEP', dcp: 'DCP', sepp: 'SEPP', hca: 'HCA', tod: 'TOD',
  da: 'DA', cdc: 'CDC', url: 'URL', ahd: 'AHD', bal: 'BAL', id: 'ID',
  m2: 'm²', pct: '%', postgis: '',
};

// ---------------------------------------------------------------------------
// Section card — renders one brief section progressively
// ---------------------------------------------------------------------------

function SectionCard({ section, data }: { section: string; data: Record<string, unknown> }) {
  const meta = SECTION_LABELS[section] ?? { label: section, description: '' };

  // DataField-wrapped sections have value/confidence/source at top level
  const isDataField = 'confidence' in data && 'source' in data;
  const confidence = isDataField ? (data.confidence as string) : null;
  const reason = isDataField ? (data.reason as string | null) : null;
  const source = isDataField ? (data.source as string) : null;
  const value = isDataField ? (data.value as Record<string, unknown> | null) : data;
  const unavail = confidence === 'not_available' ? describeUnavailable(reason, section) : null;

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{meta.label}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{meta.description}</p>
        </div>
        <div className="flex items-center gap-2">
          {unavail ? (
            <span className={`px-2 py-0.5 text-xs font-medium rounded ${UNAVAILABLE_TONE_STYLES[unavail.tone]}`}>
              {unavail.label}
            </span>
          ) : confidence ? confidenceBadge(confidence) : null}
          {source && <span className="text-xs text-slate-400">{source.replace(/_/g, ' ')}</span>}
        </div>
      </div>
      <div className="px-5 py-4">
        {unavail ? (
          <div className={`text-sm ${UNAVAILABLE_TEXT_STYLES[unavail.tone]}`}>
            {unavail.detail}
          </div>
        ) : value ? (
          <SectionData data={value} section={section} />
        ) : (
          <div className="text-sm text-slate-400 italic">No data</div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Generic data renderer — flattens nested objects into readable key-value
// ---------------------------------------------------------------------------

// Detect DataField wrapper: { value, confidence, source, as_at, reason }
function isDataField(val: unknown): val is { value: unknown; confidence: string; source: string; as_at?: string; reason?: string | null } {
  return typeof val === 'object' && val !== null && !Array.isArray(val) && 'confidence' in val && 'source' in val;
}

function SectionData({ data, section }: { data: Record<string, unknown>; section?: string }) {
  // Merge "<field>_units" into "<field>" so e.g. Height reads "7 m", not a
  // separate "Height Units: m" row.
  const unitFor: Record<string, string> = {};
  for (const [k, v] of Object.entries(data)) {
    if (!k.endsWith('_units')) continue;
    const u = isDataField(v) ? v.value : v;
    if (typeof u === 'string' && u) unitFor[k.slice(0, -6)] = u;
  }
  // Hide: internal QA fields; standalone units rows (merged above); the duplicate
  // lot area (kept in Economics); and empty "...reason" rows (e.g. an ineligible
  // reason when the lot is actually eligible).
  const entries = Object.entries(data).filter(
    ([key, val]) =>
      !['confidence', 'source', 'as_at', 'reason', 'overlay_coverage'].includes(key) &&
      !key.endsWith('_units') &&
      !(key === 'lot_area_m2' && section !== 'economics') &&
      !(/reason/i.test(key) && (val === null || val === undefined || val === '')),
  );

  if (entries.length === 0) {
    return <span className="text-sm text-slate-400">No data fields</span>;
  }

  return (
    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
      {entries.map(([key, val]) => {
        // Unwrap DataField: extract .value and show confidence badge
        if (isDataField(val)) {
          const df = val;
          if (df.confidence === 'not_available') {
            const u = describeUnavailable(df.reason, section);
            return (
              <div key={key} className="flex flex-col">
                <dt className="text-xs font-medium text-slate-500">{formatKey(key)}</dt>
                <dd className={`text-sm mt-0.5 ${UNAVAILABLE_TEXT_STYLES[u.tone]}`}>{u.label}</dd>
              </div>
            );
          }
          return (
            <div key={key} className="flex flex-col">
              <dt className="text-xs font-medium text-slate-500">{formatKey(key)}</dt>
              <dd className="text-sm text-slate-900 mt-0.5 break-words">{valueWithUnit(key, df.value, unitFor[key])}</dd>
            </div>
          );
        }

        return (
          <div key={key} className="flex flex-col">
            <dt className="text-xs font-medium text-slate-500">{formatKey(key)}</dt>
            <dd className="text-sm text-slate-900 mt-0.5 break-words">{valueWithUnit(key, val, unitFor[key])}</dd>
          </div>
        );
      })}
    </dl>
  );
}

// The lot-dimensions composite implies area (shown standalone in Economics) — strip
// it so it reads as frontage/depth/corner, not the lot area a third time.
function stripDimArea(key: string, value: unknown): unknown {
  if (key !== 'lot_dimensions' || !value || typeof value !== 'object' || Array.isArray(value)) return value;
  const obj = value as Record<string, unknown>;
  return Object.fromEntries(Object.entries(obj).filter(([k]) => k !== 'area_m2' && k !== 'lot_area_m2'));
}

// Format a field value (dimensions-area stripped) and append its unit — "7 m",
// "500 m²" — but never onto an empty/dash value.
function valueWithUnit(key: string, raw: unknown, unit?: string): string {
  const s = formatValue(stripDimArea(key, raw));
  return unit && s !== '—' ? `${s} ${unit}` : s;
}

function formatKey(key: string): string {
  return key
    .split('_')
    .map((w) => {
      const k = w.toLowerCase();
      if (k in KEY_WORDS) return KEY_WORDS[k];
      return w.charAt(0).toUpperCase() + w.slice(1);
    })
    .filter(Boolean)
    .join(' ');
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'boolean') return val ? 'Yes' : 'No';
  if (typeof val === 'number') {
    if (Number.isInteger(val)) return val.toLocaleString();
    return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  if (typeof val === 'string') return val;
  if (Array.isArray(val)) {
    if (val.length === 0) return 'None';
    // Array of primitives — join them
    if (val.every(v => typeof v === 'string' || typeof v === 'number')) {
      return val.join(', ');
    }
    return `${val.length} item${val.length === 1 ? '' : 's'}`;
  }
  if (typeof val === 'object') {
    // Render simple key-value objects inline
    const obj = val as Record<string, unknown>;
    const keys = Object.keys(obj);
    if (keys.length <= 4) {
      return keys.map(k => `${formatKey(k)}: ${formatValue(obj[k])}`).join(', ');
    }
    return `${keys.length} fields`;
  }
  return String(val);
}

// ---------------------------------------------------------------------------
// Housing SEPP (Low & Mid-Rise) standards — the denser forms the policy permits
// and whether this lot qualifies. Rendered as a table, not a raw object dump.
// ---------------------------------------------------------------------------

interface SeppStandard {
  dev_type: string;
  eligible: boolean;
  min_lot_area_m2?: number | null;
  min_lot_width_m?: number | null;
  max_fsr?: number | null;
  max_height_m?: number | null;
  reason_ineligible?: string | null;
}

function SeppHousingCard({ standards }: { standards: SeppStandard[] }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Housing SEPP — Low &amp; Mid-Rise</h3>
          <p className="text-xs text-slate-500 mt-0.5">Denser forms the policy permits, and whether this lot qualifies</p>
        </div>
        <span className="px-2 py-0.5 text-xs font-medium rounded bg-emerald-100 text-emerald-800">Authoritative</span>
      </div>
      <div className="px-5 py-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-500 text-left">
              <th className="font-medium pb-2 pr-3">Form</th>
              <th className="font-medium pb-2 pr-3">Eligible</th>
              <th className="font-medium pb-2 pr-3">Min lot</th>
              <th className="font-medium pb-2 pr-3">Min width</th>
              <th className="font-medium pb-2">Max FSR / height</th>
            </tr>
          </thead>
          <tbody>
            {standards.map((s, i) => (
              <tr key={i} className="border-t border-slate-100 align-top">
                <td className="py-1.5 pr-3 text-slate-900">{formatKey(s.dev_type)}</td>
                <td className="py-1.5 pr-3">
                  {s.eligible
                    ? <span className="text-emerald-700">Yes</span>
                    : <span className="text-slate-400" title={s.reason_ineligible ?? undefined}>No</span>}
                </td>
                <td className="py-1.5 pr-3 text-slate-600">{s.min_lot_area_m2 ? `${s.min_lot_area_m2} m²` : '—'}</td>
                <td className="py-1.5 pr-3 text-slate-600">{s.min_lot_width_m ? `${s.min_lot_width_m} m` : '—'}</td>
                <td className="py-1.5 text-slate-600">
                  {s.max_fsr ? `${s.max_fsr}:1` : s.max_height_m ? `${s.max_height_m} m` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Terrain — slope/aspect/drainage as a compass + plain-English summary, not a
// raw number dump.
// ---------------------------------------------------------------------------

interface TerrainData {
  slope_mean_deg?: number | null;
  slope_max_deg?: number | null;
  aspect_dominant_deg?: number | null;
  aspect_direction?: string | null;
  elevation_range_m?: number | null;
  drainage_direction?: string | null;
  landform_type?: string | null;
}

function slopeWord(d?: number | null): string {
  if (d == null) return 'Slope';
  if (d < 1) return 'Flat';
  if (d < 3) return 'Gently sloping';
  if (d < 6) return 'Moderately sloping';
  if (d < 12) return 'Noticeably sloping';
  if (d < 20) return 'Steep';
  return 'Very steep';
}

function AspectCompass({ deg }: { deg?: number | null }) {
  const r = 28, cx = 34, cy = 34;
  const rad = ((deg ?? 0) * Math.PI) / 180;
  const x = cx + r * Math.sin(rad);
  const y = cy - r * Math.cos(rad);
  return (
    <svg width="68" height="68" viewBox="0 0 68 68" className="flex-shrink-0">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e2e8f0" strokeWidth="1.5" />
      <text x={cx} y="11" textAnchor="middle" fontSize="9" fill="#94a3b8">N</text>
      <text x="61" y={cy + 3} textAnchor="middle" fontSize="9" fill="#94a3b8">E</text>
      <text x={cx} y="65" textAnchor="middle" fontSize="9" fill="#94a3b8">S</text>
      <text x="7" y={cy + 3} textAnchor="middle" fontSize="9" fill="#94a3b8">W</text>
      {deg != null && <line x1={cx} y1={cy} x2={x} y2={y} stroke="#0d9488" strokeWidth="2.5" strokeLinecap="round" />}
      <circle cx={cx} cy={cy} r="2.5" fill="#0d9488" />
    </svg>
  );
}

function TerrainCard({ data }: { data: TerrainData }) {
  const parts: string[] = [];
  if (data.slope_mean_deg != null) {
    const w = slopeWord(data.slope_mean_deg).toLowerCase();
    parts.push(`${w} (≈${data.slope_mean_deg.toFixed(1)}°${data.slope_max_deg != null ? `, up to ${Math.round(data.slope_max_deg)}°` : ''})`);
  }
  if (data.aspect_direction) parts.push(`faces ${data.aspect_direction}`);
  if (data.elevation_range_m != null) parts.push(`~${Math.round(data.elevation_range_m)} m of fall across the lot`);
  if (data.drainage_direction) parts.push(`drains ${data.drainage_direction}`);
  const joined = parts.join(', ');
  const summary = joined ? joined.charAt(0).toUpperCase() + joined.slice(1) + '.' : 'Terrain measured for this lot.';

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Terrain</h3>
          <p className="text-xs text-slate-500 mt-0.5">Slope, aspect and drainage from elevation</p>
        </div>
        <span className="px-2 py-0.5 text-xs font-medium rounded bg-amber-100 text-amber-800">Estimated</span>
      </div>
      <div className="px-5 py-4 flex items-start gap-4">
        <div className="flex flex-col items-center flex-shrink-0">
          <AspectCompass deg={data.aspect_dominant_deg} />
          <span className="text-xs text-slate-400 mt-0.5">{data.aspect_direction ?? '—'} aspect</span>
        </div>
        <div className="min-w-0">
          <p className="text-sm text-slate-900">{summary}</p>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-1.5 mt-3 text-xs">
            <div><dt className="text-slate-400">Slope</dt><dd className="text-slate-700">{data.slope_mean_deg != null ? `${data.slope_mean_deg.toFixed(1)}° avg${data.slope_max_deg != null ? ` · ${Math.round(data.slope_max_deg)}° max` : ''}` : '—'}</dd></div>
            <div><dt className="text-slate-400">Fall</dt><dd className="text-slate-700">{data.elevation_range_m != null ? `${data.elevation_range_m.toFixed(1)} m` : '—'}</dd></div>
            <div><dt className="text-slate-400">Drains to</dt><dd className="text-slate-700">{data.drainage_direction ?? '—'}</dd></div>
            <div><dt className="text-slate-400">Landform</dt><dd className="text-slate-700">{data.landform_type ?? '—'}</dd></div>
          </dl>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Elapsed timer hook
// ---------------------------------------------------------------------------

function useElapsedSeconds(running: boolean): number {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (running) {
      startRef.current = Date.now();
      setElapsed(0);
      const interval = setInterval(() => {
        if (startRef.current) {
          setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
        }
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [running]);

  return elapsed;
}

function formatElapsed(seconds: number): string {
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

// ---------------------------------------------------------------------------
// Live status panel — shows elapsed time, section timeline, progress
// ---------------------------------------------------------------------------

// Expected section order for the timeline
const EXPECTED_SECTIONS_BASE = [
  'economics', 'strata', 'environmental_constraints', 'planning_controls',
];
const EXPECTED_SECTIONS_DEV = ['dcp_controls', 'sepp_housing', 'constraint_arithmetic', 'neighbourhood'];
const EXPECTED_SECTIONS_SAT = [
  'satellite.bushfire', 'satellite.flood', 'satellite.climate_disclosure',
  'satellite.granny_flat', 'satellite.pre_da_history',
];

function LiveStatusPanel({
  elapsed,
  progress,
  receivedSections,
  briefType,
  includeSatellite,
  state,
}: {
  elapsed: number; // integer seconds from timer, or float from server on complete
  progress: number;
  receivedSections: string[];
  briefType: string | null;
  includeSatellite: boolean;
  state: PageState;
}) {
  // Build expected section list — show development sections by default
  // (most properties are houses, not apartments). Remove them if
  // brief_type confirms renovation.
  const expectedSections = [
    ...EXPECTED_SECTIONS_BASE,
    ...(briefType === 'renovation' ? [] : EXPECTED_SECTIONS_DEV),
    ...(includeSatellite ? EXPECTED_SECTIONS_SAT : []),
  ];

  const receivedSet = new Set(receivedSections);

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-5">
      {/* Header with elapsed time and progress */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {state !== 'complete' && (
            <div className="h-2 w-2 rounded-full bg-teal-500 animate-pulse" />
          )}
          <span className="text-sm font-medium text-slate-900">
            {state === 'triggering' ? 'Starting...' : state === 'complete' ? 'Complete' : 'Generating brief'}
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-slate-500 tabular-nums">{formatElapsed(elapsed)}</span>
          <span className="font-medium text-slate-700 tabular-nums">{progress}%</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden mb-4">
        <div
          className="h-full bg-teal-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Section timeline */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
        {expectedSections.map((section) => {
          const received = receivedSet.has(section);
          const label = SECTION_LABELS[section]?.label ?? section;
          const isSatellite = section.startsWith('satellite.');

          return (
            <div
              key={section}
              className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs ${
                received
                  ? 'bg-teal-50 text-teal-800'
                  : 'bg-slate-50 text-slate-400'
              }`}
            >
              <span className="flex-shrink-0">
                {received ? (
                  <svg className="w-3 h-3 text-teal-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : state !== 'complete' ? (
                  <div className={`w-3 h-3 rounded-full border ${isSatellite ? 'border-slate-300' : 'border-slate-300'}`} />
                ) : (
                  <svg className="w-3 h-3 text-slate-300" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                )}
              </span>
              <span className="truncate">{label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Complete summary card
// ---------------------------------------------------------------------------

function CompleteSummary({ data }: { data: BriefComplete }) {
  const { confidence_summary: cs, compound_constraints, gaps, data_currency_warnings, elapsed_seconds } = data;

  return (
    <div className="space-y-4">
      {/* Confidence summary */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-5">
        <h3 className="text-sm font-semibold text-slate-900 mb-3">Confidence Summary</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
          <div><span className="text-slate-500">Total fields:</span> <span className="font-medium">{cs.total}</span></div>
          <div><span className="text-emerald-600">Authoritative:</span> <span className="font-medium">{cs.authoritative}</span></div>
          <div><span className="text-amber-600">Estimated:</span> <span className="font-medium">{cs.estimated}</span></div>
          <div><span className="text-blue-600">Derived:</span> <span className="font-medium">{cs.derived}</span></div>
          <div><span className="text-purple-600">Extracted:</span> <span className="font-medium">{cs.extracted}</span></div>
          <div><span className="text-red-600">Not available:</span> <span className="font-medium">{cs.not_available}</span></div>
        </div>
        <p className="text-xs text-slate-400 mt-3">
          Generated in {elapsed_seconds}s — {cs.total - cs.not_available} of {cs.total} fields populated
        </p>
      </div>

      {/* Compound constraints */}
      {compound_constraints.length > 0 && (
        <div className="bg-white rounded-lg border border-amber-200 shadow-sm p-5">
          <h3 className="text-sm font-semibold text-amber-900 mb-3">
            Compound Constraints ({compound_constraints.length})
          </h3>
          <ul className="space-y-2">
            {compound_constraints.map((c, i) => (
              <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                <span className="text-amber-500 mt-0.5 flex-shrink-0">&#9679;</span>
                <span>{(c.description as string) || (c.constraint_type as string) || JSON.stringify(c)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Gaps */}
      {gaps.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">
            Data Gaps ({gaps.length})
          </h3>
          <ul className="space-y-2">
            {gaps.map((g, i) => (
              <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                <span className="text-slate-400 mt-0.5 flex-shrink-0">&#9679;</span>
                <div>
                  <span className="font-medium">{formatKey(g.field.replace(/^satellite\./, ''))}</span>
                  <span className="text-slate-500"> — {describeUnavailable(g.reason, g.field).detail}</span>
                  {g.verify_url && (
                    <a
                      href={g.verify_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-2 text-teal-600 hover:text-teal-800 text-xs underline"
                    >
                      Verify
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Data currency warnings */}
      {data_currency_warnings.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-2">Data Currency Warnings</h3>
          <ul className="space-y-1">
            {data_currency_warnings.map((w, i) => (
              <li key={i} className="text-sm text-slate-600">{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

function IntelligenceBriefInner() {
  const searchParams = useSearchParams();

  const [inputAddress, setInputAddress] = useState('');
  const [selectedAddress, setSelectedAddress] = useState('');
  const [selectedLat, setSelectedLat] = useState<number | null>(null);
  const [selectedLng, setSelectedLng] = useState<number | null>(null);
  const [state, setState] = useState<PageState>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [runId, setRunId] = useState<string | null>(null);
  const [briefType, setBriefType] = useState<string | null>(null);
  const [includeSatellite, setIncludeSatellite] = useState(false);
  const [includeSiteHistory, setIncludeSiteHistory] = useState(false);
  const [lotPolygon, setLotPolygon] = useState<{ type: 'Polygon'; coordinates: number[][][] } | null>(null);
  const [publicAccessToken, setPublicAccessToken] = useState<string | null>(null);
  const [parts, setParts] = useState<BriefEvent[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const stateRef = useRef<PageState>(state);
  stateRef.current = state;

  // Elapsed timer — starts on trigger, stops on complete/error
  const timerRunning = state === 'triggering' || state === 'streaming';
  const elapsed = useElapsedSeconds(timerRunning);

  // Derive state from parts
  const metadataEvent = parts.find((p): p is Extract<BriefEvent, { event: 'metadata' }> => p.event === 'metadata');
  const sectionEvents = parts.filter((p): p is Extract<BriefEvent, { event: 'section' }> => p.event === 'section');
  const completeEvent = parts.find((p): p is Extract<BriefEvent, { event: 'complete' }> => p.event === 'complete');

  // Track progress — complete event overrides to 100
  const latestProgress = completeEvent
    ? 100
    : sectionEvents.length > 0
      ? sectionEvents[sectionEvents.length - 1].data.progress
      : 0;

  // Extract brief_type from section events
  useEffect(() => {
    if (!briefType) {
      const strataSection = sectionEvents.find((s) => s.data.brief_type);
      if (strataSection?.data.brief_type) {
        setBriefType(strataSection.data.brief_type);
      }
    }
  }, [sectionEvents, briefType]);

  // Fetch the lot boundary (WGS84 GeoJSON) to overlay on the aerial — reuses the
  // /api/property/profile route (the same source PropertyProfile uses).
  useEffect(() => {
    const addr = metadataEvent?.data.address ?? selectedAddress;
    if (!addr || (state !== 'streaming' && state !== 'complete')) return;
    let cancelled = false;
    fetch(`/api/property/profile?address=${encodeURIComponent(addr)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (!cancelled && d?.lotPolygon) setLotPolygon(d.lotPolygon); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [metadataEvent?.data.address, selectedAddress, state]);

  // Connect directly to Trigger.dev Realtime stream when we have a runId + token
  useEffect(() => {
    if (!runId || !publicAccessToken || state === 'idle' || state === 'complete' || state === 'error') return;

    const ac = new AbortController();
    abortRef.current = ac;

    const connectStream = async () => {
      const streamUrl = `https://api.trigger.dev/realtime/v1/streams/${runId}/intelligence-brief`;
      let retries = 0;
      const maxRetries = 30;

      while (!ac.signal.aborted && retries < maxRetries) {
        try {
          const resp = await fetch(streamUrl, {
            headers: { Authorization: `Bearer ${publicAccessToken}` },
            signal: ac.signal,
          });

          if (!resp.ok) {
            if (resp.status === 404 || resp.status === 400) {
              retries++;
              await new Promise(r => setTimeout(r, 2000));
              continue;
            }
            setState('error');
            setErrorMsg(`Stream error: HTTP ${resp.status}`);
            return;
          }

          setState('streaming');
          const reader = resp.body!.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          const seenIds = new Set<string>();

          while (true) {
            const { done, value } = await reader.read();

            if (value) buffer += decoder.decode(value, { stream: true });

            // On end-of-stream, flush the ENTIRE remaining buffer as the final
            // chunk(s). Otherwise a trailing 'complete' event that arrived
            // without a closing blank line stays stuck in `buffer` and is
            // discarded when we break — which is what silently dropped the
            // confidence-summary and gaps cards (and froze the progress bar).
            let chunks: string[];
            if (done) {
              buffer += decoder.decode();
              chunks = buffer.split('\n\n');
              buffer = '';
            } else {
              chunks = buffer.split('\n\n');
              buffer = chunks.pop() ?? '';
            }

            for (const chunk of chunks) {
              if (!chunk.trim()) continue;

              // Extract SSE id and data fields
              let eventId = '';
              let eventData = '';
              for (const line of chunk.split('\n')) {
                if (line.startsWith('id:')) eventId = line.slice(3).trim();
                if (line.startsWith('data:')) eventData += line.slice(5).trim();
              }
              if (!eventData) continue;

              // Deduplicate — Trigger.dev replays all events on each connection
              if (eventId && seenIds.has(eventId)) continue;
              if (eventId) seenIds.add(eventId);

              try {
                let parsed = JSON.parse(eventData);
                if (typeof parsed === 'string') parsed = JSON.parse(parsed);

                // Handle v2 batch format
                const events: BriefEvent[] = [];
                if (parsed.records) {
                  for (const record of parsed.records) {
                    let body = typeof record.body === 'string' ? JSON.parse(record.body) : record.body;
                    if (typeof body === 'string') body = JSON.parse(body);
                    events.push(body);
                  }
                } else {
                  events.push(parsed);
                }

                for (const briefEvent of events) {
                  setParts(prev => [...prev, briefEvent]);
                  if (briefEvent.event === 'complete') {
                    setState('complete');
                    return;
                  }
                  if (briefEvent.event === 'error') {
                    setState('error');
                    setErrorMsg(briefEvent.data.message);
                    return;
                  }
                }
              } catch {
                // Skip unparseable (keepalive pings)
              }
            }

            if (done) break;
          }

          // Stream ended without complete event — task may have finished
          if (stateRef.current !== 'complete' && stateRef.current !== 'error') {
            setState('complete');
          }
          return;
        } catch (err: unknown) {
          if (ac.signal.aborted) return;
          retries++;
          if (retries >= maxRetries) {
            setState('error');
            setErrorMsg('Could not connect to stream after 60 seconds.');
            return;
          }
          await new Promise(r => setTimeout(r, 2000));
        }
      }
    };

    connectStream();

    return () => { ac.abort(); };
  }, [runId, publicAccessToken]);

  const handleGenerate = useCallback(async () => {
    if (!selectedAddress.trim()) return;

    setState('triggering');
    setErrorMsg('');
    setRunId(null);
    setBriefType(null);
    setParts([]);

    try {
      const res = await fetch('/api/intelligence-brief', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: selectedAddress,
          lat: selectedLat,
          lng: selectedLng,
          // Site history needs both flags; ticking it implies satellite too.
          include_satellite: includeSatellite || includeSiteHistory,
          include_premium: includeSiteHistory,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(err.error || `HTTP ${res.status}`);
      }

      const data = await res.json();
      console.log('[ib] triggered run %s', data.runId);
      setPublicAccessToken(data.publicAccessToken);
      setRunId(data.runId);
    } catch (err) {
      setState('error');
      setErrorMsg(err instanceof Error ? err.message : 'Failed to start intelligence brief');
    }
  }, [selectedAddress, selectedLat, selectedLng, includeSatellite, includeSiteHistory]);

  const handleReset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setState('idle');
    setRunId(null);
    setPublicAccessToken(null);
    setErrorMsg('');
    setBriefType(null);
    setLotPolygon(null);
    setParts([]);
    setInputAddress('');
    setSelectedAddress('');
    setSelectedLat(null);
    setSelectedLng(null);
  }, []);

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Intelligence Brief</h1>
        <p className="text-sm text-slate-500 mt-1 max-w-3xl">
          For a single NSW property: what the rules allow, what physically constrains the site,
          what environmental risk applies, what it&apos;s worth, and what&apos;s happening
          next door — fifteen-plus government, satellite and computed layers fused into one brief,
          every figure traced to its source.
        </p>
      </div>

      {/* Address input */}
      {state === 'idle' && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-4 max-w-2xl">
          <AddressAutocomplete
            value={inputAddress}
            onChange={setInputAddress}
            onSelect={(address, lat, lng) => {
              setSelectedAddress(address);
              setSelectedLat(lat);
              setSelectedLng(lng);
              setInputAddress(address);
            }}
            placeholder="Enter a NSW property address..."
          />

          <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={includeSatellite}
              onChange={(e) => setIncludeSatellite(e.target.checked)}
              className="rounded border-slate-300 text-teal-600 focus:ring-teal-500"
            />
            Include satellite analysis (bushfire, flood, climate, granny flat detection)
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={includeSiteHistory}
              onChange={(e) => setIncludeSiteHistory(e.target.checked)}
              className="rounded border-slate-300 text-teal-600 focus:ring-teal-500"
            />
            Include site history (slower — adds ~1 min)
          </label>

          <button
            onClick={handleGenerate}
            disabled={!selectedAddress.trim()}
            className="w-full py-2.5 px-4 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Generate Intelligence Brief
          </button>
        </div>
      )}

      {/* Error state */}
      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-5 space-y-3 max-w-2xl">
          <p className="text-sm text-red-800 font-medium">Brief generation failed</p>
          <p className="text-sm text-red-700">{errorMsg}</p>
          <button
            onClick={handleReset}
            className="text-sm text-red-600 hover:text-red-800 underline"
          >
            Try another address
          </button>
        </div>
      )}

      {/* Streaming / complete states */}
      {(state === 'triggering' || state === 'streaming' || state === 'complete') && (
        <div className="space-y-4">
          {/* Address header */}
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm px-5 py-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-900">
                {metadataEvent?.data.address ?? selectedAddress}
              </p>
              {briefType && (
                <p className="text-xs text-slate-500 mt-0.5">
                  {briefType === 'renovation' ? 'Renovation Brief (apartment/strata)' : 'Development Brief (house/land)'}
                </p>
              )}
            </div>
            {state === 'complete' && (
              <button
                onClick={handleReset}
                className="text-sm text-teal-600 hover:text-teal-800"
              >
                New brief
              </button>
            )}
          </div>

          {/* Aerial — NSW SIX Maps 10cm imagery for the lot (reuses AerialTile). */}
          {(metadataEvent?.data.lat ?? selectedLat) != null && (metadataEvent?.data.lng ?? selectedLng) != null && (
            <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
              <AerialTile
                lat={(metadataEvent?.data.lat ?? selectedLat) as number}
                lng={(metadataEvent?.data.lng ?? selectedLng) as number}
                height={260}
                lotPolygon={lotPolygon}
              />
              <p className="px-4 py-2 text-xs text-slate-400">
                NSW SIX Maps aerial imagery &middot; &copy; NSW Government CC BY 4.0
              </p>
            </div>
          )}

          {/* Live status panel — elapsed time, section timeline, progress */}
          <LiveStatusPanel
            elapsed={state === 'complete' && completeEvent ? completeEvent.data.elapsed_seconds : elapsed}
            progress={state === 'triggering' ? 0 : state === 'complete' ? 100 : latestProgress}
            receivedSections={sectionEvents.map((e) => e.data.section)}
            briefType={briefType}
            includeSatellite={includeSatellite}
            state={state}
          />

          {/* Section cards — bento grid; appear as they arrive. The headline and
              field-heavy sections span two columns; the rest are single tiles, and
              grid-auto-flow:dense packs gaps as cards stream in at uneven heights. */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 [grid-auto-flow:dense] items-start">
            {sectionEvents.map((event, i) => {
              const section = event.data.section;
              // Development Capacity renders via the dedicated card (carries its
              // own binding-constraint breakdown + disclaimer). Falls back to the
              // generic SectionCard when the value is absent (not computed).
              let card: ReactNode = null;
              if (section === 'constraint_arithmetic') {
                const ca = (event.data.data?.value ?? null) as ConstraintArithmeticResult | null;
                if (ca) {
                  card = (
                    <ConstraintArithmeticCard
                      briefData={ca}
                      lotArea={ca.lot_area_m2}
                      devType={ca.dev_type}
                    />
                  );
                }
              }
              if (section === 'sepp_housing') {
                const standards = (event.data.data?.value ?? null) as SeppStandard[] | null;
                if (standards && standards.length) {
                  card = <SeppHousingCard standards={standards} />;
                }
              }
              if (section === 'satellite.terrain') {
                // Terrain may arrive as a plain dict or a DataField wrapping it in .value.
                const raw = event.data.data as Record<string, unknown> | null;
                const t = (raw && typeof raw === 'object'
                  ? ((raw.value as TerrainData) ?? (raw as unknown as TerrainData))
                  : null);
                if (t && typeof t === 'object' && t.slope_mean_deg != null) {
                  card = <TerrainCard data={t} />;
                }
              }
              if (!card) {
                card = <SectionCard section={section} data={event.data.data} />;
              }
              return (
                <div key={`${section}-${i}`} className={cn('min-w-0', spanFor(section))}>
                  {card}
                </div>
              );
            })}
          </div>

          {/* Complete summary */}
          {completeEvent && <CompleteSummary data={completeEvent.data} />}
        </div>
      )}
    </div>
  );
}

export default function IntelligenceBriefPage() {
  return (
    <Suspense fallback={<div className="text-center py-20 text-slate-400">Loading...</div>}>
      <IntelligenceBriefInner />
    </Suspense>
  );
}
