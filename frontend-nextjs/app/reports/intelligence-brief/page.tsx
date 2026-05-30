'use client';

import { useState, useCallback, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { useRealtimeStream } from '@trigger.dev/react-hooks';

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
  'satellite.bushfire': { label: 'Bushfire Risk', description: 'Bushfire attack level, vegetation category' },
  'satellite.flood': { label: 'Flood Analysis', description: 'Multi-source flood occurrence screening' },
  'satellite.climate_disclosure': { label: 'Climate Disclosure', description: 'Heat island, rainfall intensity, fire hotspots' },
  'satellite.granny_flat': { label: 'Granny Flat Detection', description: 'Structure detection, SEPP eligibility' },
  'satellite.pre_da_history': { label: 'Pre-DA Site History', description: 'Historical development activity timeline' },
};

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

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{meta.label}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{meta.description}</p>
        </div>
        <div className="flex items-center gap-2">
          {confidence && confidenceBadge(confidence)}
          {source && <span className="text-xs text-slate-400">{source.replace(/_/g, ' ')}</span>}
        </div>
      </div>
      <div className="px-5 py-4">
        {confidence === 'not_available' ? (
          <div className="text-sm text-slate-500 italic">
            {reason || 'Data not available for this property'}
          </div>
        ) : value ? (
          <SectionData data={value} />
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

function SectionData({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(
    ([key]) => !['confidence', 'source', 'as_at', 'reason'].includes(key),
  );

  if (entries.length === 0) {
    return <span className="text-sm text-slate-400">No data fields</span>;
  }

  return (
    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
      {entries.map(([key, val]) => (
        <div key={key} className="flex flex-col">
          <dt className="text-xs font-medium text-slate-500">{formatKey(key)}</dt>
          <dd className="text-sm text-slate-900 mt-0.5">{formatValue(val)}</dd>
        </div>
      ))}
    </dl>
  );
}

function formatKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
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
    return `${val.length} item${val.length === 1 ? '' : 's'}`;
  }
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
}

// ---------------------------------------------------------------------------
// Progress bar
// ---------------------------------------------------------------------------

function ProgressBar({ progress, label }: { progress: number; label?: string }) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-500">{label ?? 'Generating brief...'}</span>
        <span className="text-xs font-medium text-slate-700">{progress}%</span>
      </div>
      <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-teal-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
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
                  <span className="font-medium">{formatKey(g.field)}</span>
                  {g.reason && <span className="text-slate-500"> — {g.reason}</span>}
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
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [briefType, setBriefType] = useState<string | null>(null);
  const [includeSatellite, setIncludeSatellite] = useState(false);

  // Stream subscription — only active when we have runId + accessToken
  const { parts, error: streamError } = useRealtimeStream<BriefEvent>(
    runId ?? '',
    'intelligence-brief',
    {
      accessToken: accessToken ?? undefined,
      enabled: !!runId && !!accessToken && (state === 'streaming' || state === 'triggering'),
    },
  );

  // Derive state from parts
  const metadataEvent = parts.find((p): p is Extract<BriefEvent, { event: 'metadata' }> => p.event === 'metadata');
  const sectionEvents = parts.filter((p): p is Extract<BriefEvent, { event: 'section' }> => p.event === 'section');
  const completeEvent = parts.find((p): p is Extract<BriefEvent, { event: 'complete' }> => p.event === 'complete');
  const errorEvent = parts.find((p): p is Extract<BriefEvent, { event: 'error' }> => p.event === 'error');

  // Track progress from latest section
  const latestProgress = sectionEvents.length > 0
    ? sectionEvents[sectionEvents.length - 1].data.progress
    : 0;

  // Update state based on stream events (in useEffect to avoid setState during render)
  useEffect(() => {
    if (metadataEvent && state === 'triggering') {
      setState('streaming');
    }
    if (completeEvent && state === 'streaming') {
      setState('complete');
    }
    if (errorEvent && state !== 'error') {
      setState('error');
      setErrorMsg(errorEvent.data.message);
    }
    if (streamError && state !== 'error') {
      setState('error');
      setErrorMsg(streamError.message);
    }
  }, [metadataEvent, completeEvent, errorEvent, streamError, state]);

  // Extract brief_type from strata section
  useEffect(() => {
    if (!briefType) {
      const strataSection = sectionEvents.find((s) => s.data.brief_type);
      if (strataSection?.data.brief_type) {
        setBriefType(strataSection.data.brief_type);
      }
    }
  }, [sectionEvents, briefType]);

  const handleGenerate = useCallback(async () => {
    if (!selectedAddress.trim()) return;

    setState('triggering');
    setErrorMsg('');
    setRunId(null);
    setAccessToken(null);
    setBriefType(null);

    try {
      const res = await fetch('/api/intelligence-brief', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: selectedAddress,
          lat: selectedLat,
          lng: selectedLng,
          include_satellite: includeSatellite,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(err.error || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setRunId(data.runId);
      setAccessToken(data.publicAccessToken);
    } catch (err) {
      setState('error');
      setErrorMsg(err instanceof Error ? err.message : 'Failed to start intelligence brief');
    }
  }, [selectedAddress, selectedLat, selectedLng, includeSatellite]);

  const handleReset = useCallback(() => {
    setState('idle');
    setRunId(null);
    setAccessToken(null);
    setErrorMsg('');
    setBriefType(null);
    setInputAddress('');
    setSelectedAddress('');
    setSelectedLat(null);
    setSelectedLng(null);
  }, []);

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Intelligence Brief</h1>
        <p className="text-sm text-slate-500 mt-1">
          Property intelligence report covering planning controls, environmental constraints,
          economics, and satellite analysis for any NSW property.
        </p>
      </div>

      {/* Address input */}
      {state === 'idle' && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-4">
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
        <div className="bg-red-50 border border-red-200 rounded-lg p-5 space-y-3">
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

          {/* Progress bar — show while streaming */}
          {state !== 'complete' && (
            <ProgressBar
              progress={state === 'triggering' ? 0 : latestProgress}
              label={
                state === 'triggering'
                  ? 'Starting brief generation...'
                  : sectionEvents.length > 0
                    ? `Received ${sectionEvents.length} sections — ${SECTION_LABELS[sectionEvents[sectionEvents.length - 1].data.section]?.label ?? sectionEvents[sectionEvents.length - 1].data.section}`
                    : 'Connecting to data sources...'
              }
            />
          )}

          {/* Section cards — appear as they arrive */}
          <div className="space-y-3">
            {sectionEvents.map((event, i) => (
              <SectionCard
                key={`${event.data.section}-${i}`}
                section={event.data.section}
                data={event.data.data}
              />
            ))}
          </div>

          {/* Loading skeleton for next section */}
          {state === 'streaming' && (
            <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-5 animate-pulse">
              <div className="h-4 bg-slate-200 rounded w-1/3 mb-3" />
              <div className="h-3 bg-slate-100 rounded w-2/3 mb-2" />
              <div className="h-3 bg-slate-100 rounded w-1/2" />
            </div>
          )}

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
