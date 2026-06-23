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
  'satellite.granny_flat': { label: 'Secondary Dwelling', description: 'Granny-flat feasibility — buildings on the lot + eligibility' },
  'satellite.pre_da_history': { label: 'Pre-DA Site History', description: 'Historical development activity timeline' },
  'satellite.terrain': { label: 'Terrain Analysis', description: 'Slope, aspect and drainage from elevation' },
};

// Bento spans — the headline (development capacity) and the field-heavy sections
// get two columns; everything else is a single tile. Driving the layout off the
// section key keeps it stable as cards stream in at uneven heights.
const WIDE_SECTIONS = new Set(['constraint_arithmetic', 'planning_controls', 'environmental_constraints']);
// DCP controls carries a long PDF URL — give it the full row so it reads cleanly.
const FULL_ROW_SECTIONS = new Set(['dcp_controls']);
function spanFor(section: string): string {
  if (FULL_ROW_SECTIONS.has(section)) return 'col-span-1 md:col-span-2 xl:col-span-3';
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

function describeUnavailable(reason?: string | null, section?: string, satelliteRan = false): Unavailable {
  const r = (reason ?? '').toLowerCase();
  const isSatellite = !!section && (SATELLITE_SECTIONS.has(section) || section === 'satellite.bushfire');
  // What this layer actually assesses, so a "no" explains itself (e.g.
  // "bushfire attack level and vegetation category") rather than a bare "none".
  const what = (section && SECTION_LABELS[section]?.description
    ? SECTION_LABELS[section].description.toLowerCase()
    : '');

  // Satellite opt-in layers.
  if (isSatellite) {
    // If satellite analysis WAS requested but this layer is empty, it couldn't be
    // produced for this property — say that plainly, don't blame the user's tickbox
    // and don't imply a false finding ("no structures" on a clearly built lot).
    if (satelliteRan) {
      // Surface the real failure reason (e.g. a missing model or a DEM/raster
      // error) so the cause is diagnosable, not hidden behind a generic line.
      const why = reason && !r.includes('not requested') ? ` (${String(reason).slice(0, 180)})` : '';
      return {
        label: 'Couldn’t complete',
        detail: `We couldn’t complete ${what ? `the ${what} analysis` : 'this analysis'} for this property${why}. Try running the brief again.`,
        tone: 'pending',
      };
    }
    return {
      label: 'Not run',
      detail: `Tick “Include satellite analysis” above and re-run to add ${what || 'this layer'}.`,
      tone: 'optional',
    };
  }
  // Pre-DA site history. Distinguish "not requested" (tick the box) from
  // "requested but didn't finish" (it ran and timed out / failed) — don't tell a
  // user who already ticked the box to tick it again.
  if (section === 'satellite.pre_da_history' || r.includes('premium') || r.includes('site history')) {
    if (r.includes('not requested')) {
      return {
        label: 'Not run',
        detail: 'Tick “Include site history (slower)” above and run the brief again to add this.',
        tone: 'optional',
      };
    }
    // A genuine timeout — it ran out of time. Tell the user to retry.
    if (r.includes('timeout') || r.includes("didn't finish") || r.includes('did not finish')) {
      return {
        label: 'Couldn’t complete',
        detail: 'The site-history analysis didn’t finish in time for this property — please run the brief again.',
        tone: 'pending',
      };
    }
    // It errored fast (e.g. a backend model/service issue) — surface the real
    // reason so it can be diagnosed, rather than pretending it timed out.
    const why = reason ? String(reason).slice(0, 160) : '';
    return {
      label: 'Couldn’t complete',
      detail: `The site-history analysis couldn’t run for this property — this is a backend issue, not your input${why ? ` (${why})` : ''}.`,
      tone: 'pending',
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
      detail: `${what ? `This council's ${what} isn't in our dataset yet` : 'This layer is not yet mapped for this council'} — confirm directly with the council or the NSW Planning Portal.`,
      tone: 'pending',
    };
  }
  if (r.startsWith('no ') || r.includes('none found') || r.includes('at this location')) {
    return {
      label: 'None here',
      detail: `Checked${what ? ` for ${what}` : ''} — none recorded at this property. For a constrained site that's good news.`,
      tone: 'clear',
    };
  }
  if (r.includes('not requested')) {
    return { label: 'Not run', detail: 'An optional add-on, not part of this brief.', tone: 'neutral' };
  }
  if (r.includes('fail') || r.includes('unavailable') || r.includes('error')) {
    return {
      label: 'Unavailable',
      detail: `The source for ${what || 'this layer'} did not respond — run the brief again to retry.`,
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
  da: 'DA', das: 'DAs', cdc: 'CDC', url: 'URL', ahd: 'AHD', bal: 'BAL', id: 'ID',
  m2: 'm²', pct: '%', postgis: '',
};

// ---------------------------------------------------------------------------
// Section card — renders one brief section progressively
// ---------------------------------------------------------------------------

function SectionCard({ section, data, satelliteRan = false }: { section: string; data: Record<string, unknown>; satelliteRan?: boolean }) {
  const meta = SECTION_LABELS[section] ?? { label: section, description: '' };

  // DataField-wrapped sections have value/confidence/source at top level
  const isDataField = 'confidence' in data && 'source' in data;
  const confidence = isDataField ? (data.confidence as string) : null;
  const reason = isDataField ? (data.reason as string | null) : null;
  const source = isDataField ? (data.source as string) : null;
  const value = isDataField ? (data.value as Record<string, unknown> | null) : data;
  // A bushfire prescreen that RAN but found no Bushfire Attack Level is good news
  // ("not bushfire-prone"), not an un-ticked add-on — the value object is present.
  const bushfireNotProne =
    section === 'satellite.bushfire' && confidence === 'not_available' &&
    !!value && typeof value === 'object' && !Array.isArray(value) &&
    (value as Record<string, unknown>).category == null;
  const unavail = confidence === 'not_available'
    ? (bushfireNotProne
        ? {
            label: 'Not bushfire-prone',
            detail: 'Checked the RFS Bushfire Prone Land map — this property is not designated bushfire-prone.',
            tone: 'clear' as UnavailableTone,
          }
        : describeUnavailable(reason, section, satelliteRan))
    : null;

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
          <SectionData data={value} section={section} satelliteRan={satelliteRan} />
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

// Render a field value — if it's a URL, show a readable clickable link instead of
// a raw, overflowing address.
function FieldValue({ display, raw, fieldKey }: { display: string; raw: unknown; fieldKey: string }) {
  if (typeof raw === 'string' && /^https?:\/\//i.test(raw)) {
    const label = /dcp/i.test(fieldKey) ? 'Open the DCP document (PDF)'
      : /legislation/i.test(fieldKey) ? 'Open the legislation'
      : 'Open the document';
    return (
      <a href={raw} target="_blank" rel="noopener noreferrer"
         className="text-teal-600 hover:text-teal-800 underline font-medium">
        {label} ↗
      </a>
    );
  }
  return <>{display}</>;
}

function SectionData({ data, section, satelliteRan = false }: { data: Record<string, unknown>; section?: string; satelliteRan?: boolean }) {
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
            const u = describeUnavailable(df.reason, section, satelliteRan);
            return (
              <div key={key} className="flex flex-col">
                <FieldLabel fieldKey={key} />
                <dd className={`text-sm mt-0.5 ${UNAVAILABLE_TEXT_STYLES[u.tone]}`}>{u.label}</dd>
              </div>
            );
          }
          // Heritage dict -> one plain sentence, not a raw object dump.
          if (key === 'heritage_postgis' && df.value && typeof df.value === 'object' && !Array.isArray(df.value)) {
            return (
              <div key={key} className="flex flex-col sm:col-span-2">
                <dt className="text-xs font-medium text-slate-500">Heritage</dt>
                <dd className="text-sm text-slate-900 mt-0.5">{humanizeHeritage(df.value as Record<string, unknown>)}</dd>
              </div>
            );
          }
          // Shadow is a nested overshadowing result — render a readable summary,
          // not "6 fields".
          if (key === 'shadow' && df.value && typeof df.value === 'object' && !Array.isArray(df.value)) {
            return (
              <div key={key} className="flex flex-col sm:col-span-2">
                <FieldLabel fieldKey={key} />
                <dd className="mt-0.5"><ShadowDisplay data={df.value as ShadowData} /></dd>
              </div>
            );
          }
          // Heritage items / HCA arrive as a list of "<name> Significance: <level>"
          // strings — render each on its own line with the significance as a badge,
          // not a comma run-on.
          if ((key === 'heritage_items' || key === 'heritage_hca') && Array.isArray(df.value)) {
            return (
              <div key={key} className="flex flex-col sm:col-span-2">
                <FieldLabel fieldKey={key} />
                <dd className="mt-0.5"><HeritageList items={df.value as string[]} /></dd>
              </div>
            );
          }
          // Planning overlays are a list of {layer_type, value} — render them as
          // a readable list with units, not "2 items".
          if (key === 'overlays' && Array.isArray(df.value)) {
            return (
              <div key={key} className="flex flex-col sm:col-span-2">
                <dt className="text-xs font-medium text-slate-500">{formatKey(key)}</dt>
                <dd className="mt-0.5"><OverlayList overlays={df.value as OverlayItem[]} /></dd>
              </div>
            );
          }
          // The coastal_hazards field wraps the SEPP "land application" layer — a
          // jurisdictional area covering much of NSW, not a hazard finding. Render
          // one clean line rather than a doubled "Coastal Management Area: ...".
          if (key === 'coastal_hazards' && df.value && typeof df.value === 'object' && !Array.isArray(df.value)) {
            const within = Object.keys(df.value as Record<string, unknown>).length > 0;
            return (
              <div key={key} className="flex flex-col sm:col-span-2">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  {within
                    ? 'Within the Coastal Management SEPP land-application area (jurisdictional — not a coastal-hazard finding).'
                    : 'Not in a coastal management area.'}
                </dd>
              </div>
            );
          }
          // An authoritative null is a checked "nothing here" (e.g. not
          // bushfire-designated, no heritage listing) — show "None", not a dash.
          const display = df.value == null && df.confidence === 'authoritative'
            ? 'None'
            : valueWithUnit(key, df.value, unitFor[key]);
          return (
            <div key={key} className="flex flex-col">
              <FieldLabel fieldKey={key} />
              <dd className="text-sm text-slate-900 mt-0.5 break-words [overflow-wrap:anywhere]"><FieldValue display={display} raw={df.value} fieldKey={key} /></dd>
            </div>
          );
        }

        // Flood raster/remote reads return 0 for a genuine "no water" and null only
        // when the read FAILED — so a null here means "couldn't retrieve", not zero.
        // Say that plainly rather than showing an ambiguous dash.
        if (FLOOD_RETRIEVAL_KEYS.has(key) && (val === null || val === undefined)) {
          return (
            <div key={key} className="flex flex-col">
              <FieldLabel fieldKey={key} />
              <dd className="text-sm mt-0.5 text-amber-700">Couldn’t retrieve — run the brief again to retry.</dd>
            </div>
          );
        }
        return (
          <div key={key} className="flex flex-col">
            <FieldLabel fieldKey={key} />
            <dd className="text-sm text-slate-900 mt-0.5 break-words [overflow-wrap:anywhere]"><FieldValue display={valueWithUnit(key, val, unitFor[key])} raw={val} fieldKey={key} /></dd>
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
// Fields that read as currency — prefix "$" rather than appending a unit.
const CURRENCY_FIELDS = new Set(['land_value', 'land_value_aud', 'capital_value', 'unimproved_land_value']);

function valueWithUnit(key: string, raw: unknown, unit?: string): string {
  const s = formatValue(stripDimArea(key, raw));
  if (s === '—') return s;
  if (CURRENCY_FIELDS.has(key) && typeof raw === 'number') return `$${s}`;
  return unit ? `${s} ${unit}` : s;
}

// Field/overlay labels whose word-by-word title-case is misleading. The coastal
// SEPP "land application" layer marks where the Coastal Management SEPP *applies*
// (jurisdictional, much of NSW) — it is NOT a coastal-hazard finding, so label it
// as the management area, not "Coastal Hazards"/"Coastal Land Application".
const FIELD_LABEL_OVERRIDES: Record<string, string> = {
  coastal_land_application: 'Coastal Management Area',
  coastal_hazards: 'Coastal Management Area',
};

function formatKey(key: string): string {
  if (key in FIELD_LABEL_OVERRIDES) return FIELD_LABEL_OVERRIDES[key];
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

// Plain-English descriptions for fields whose labels are opaque on their own
// (satellite/flood acronyms, neighbourhood counts). Shown as a muted line under
// the field label so a dash or a number has meaning. Factual, no advice.
// Flood fields whose source returns 0 for a genuine "no water" reading, so a
// null specifically means the satellite/raster read failed (not a real zero).
const FLOOD_RETRIEVAL_KEYS = new Set(['jrc_occurrence_pct', 'wofs_frequency_pct', 'epi_flood']);

const FIELD_HINTS: Record<string, string> = {
  jrc_occurrence_pct:
    'How often satellites saw surface water on this spot over 1984–2021 (EC Joint Research Centre). 0% means no water was observed in ~37 years.',
  wofs_frequency_pct:
    'Share of clear satellite passes where water was visible here (Geoscience Australia, Water Observations from Space).',
  bom_gauge_distance_km:
    'Straight-line distance to the nearest Bureau of Meteorology river gauge.',
  flood_studies: 'Council or agency flood studies that cover this location.',
  epi_flood: 'Whether the lot falls in a flood-planning area mapped in the council’s LEP.',
  flood_epi: 'Whether the lot falls in a flood-planning area mapped in the council’s LEP.',
  nearby_das:
    'Development applications lodged on nearby properties (within 500 m) in the last 12 months.',
  da_count: 'Number of development applications within 500 m in the last 12 months.',
};

// Field label + an optional one-line description underneath.
function FieldLabel({ fieldKey }: { fieldKey: string }) {
  const hint = FIELD_HINTS[fieldKey];
  return (
    <dt className="text-xs font-medium text-slate-500">
      {formatKey(fieldKey)}
      {hint && (
        <span className="block text-[10px] font-normal text-slate-400 mt-0.5 leading-snug">{hint}</span>
      )}
    </dt>
  );
}

// Units to append to a planning-overlay value when it's a bare number/string.
const OVERLAY_UNIT: Record<string, string> = {
  lot_size: 'm²', minimum_lot_size: 'm²', height: 'm', height_of_building: 'm',
  floor_space_ratio: ':1', fsr: ':1',
};

// The PostGIS heritage field is a {has_heritage, hca, items, raw} dict — turn it
// into one plain sentence instead of dumping "HCA:…, Has Heritage: Yes, Raw: 2 items".
function humanizeHeritage(v: Record<string, unknown>): string {
  if (!v || !v.has_heritage) return 'No heritage listing recorded at this property.';
  // v.hca / v.items already read like "Heritage Conservation Area (Inner West LEP 2022)"
  // — render them as-is (they carry the instrument), don't re-prefix and double up.
  const parts: string[] = [];
  if (v.hca) parts.push(String(v.hca));
  if (v.items) parts.push(String(v.items));
  return parts.length
    ? `This property is heritage-affected: ${parts.join('; ')}.`
    : 'A heritage listing applies to this property.';
}

// Heritage items/HCA arrive as a list of "<name> Significance: <level>" strings.
// Render each on its own line with the significance as a small badge instead of a
// comma run-on; split on " Significance: " to separate the name from the level.
function HeritageList({ items }: { items: string[] }) {
  const rows = (items || []).map((s) => String(s).trim()).filter(Boolean);
  if (rows.length === 0) {
    return <span className="text-sm text-emerald-700">No heritage listing recorded at this property.</span>;
  }
  return (
    <ul className="text-sm text-slate-900 space-y-1.5">
      {rows.map((raw, i) => {
        const m = raw.match(/^(.*?)\s*significance:\s*(.+)$/i);
        const name = m ? m[1].trim().replace(/[;,]\s*$/, '') : raw;
        const sig = m ? m[2].trim() : null;
        return (
          <li key={i} className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:gap-2">
            <span className="leading-snug">{name}</span>
            {sig && (
              <span className="inline-flex w-fit shrink-0 items-center rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-700 ring-1 ring-amber-200">
                {sig} significance
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

interface ShadowScenario { date_label?: string; time_label?: string; shadow_length_m?: number | null; overlap_pct?: number | null; }
interface ShadowData {
  height_m?: number | null; height_source?: string | null; adg_compliant?: boolean | null;
  scenarios?: ShadowScenario[]; worst_case_scenario?: string | null; temporal_caveat?: string | null;
}

// The shadow field is a nested object — render the overshadowing summary
// (height, solar-access compliance, worst-case shadow), not a bare "6 fields".
function ShadowDisplay({ data }: { data: ShadowData }) {
  const worst = (data.scenarios || []).find((s) => `${s.date_label} ${s.time_label}`.trim() === (data.worst_case_scenario || '').trim())
    || (data.scenarios || [])[0];
  return (
    <div className="text-sm text-slate-900 space-y-1.5">
      {data.height_m != null && (
        <div>Modelled building height: <span className="font-medium">{data.height_m} m</span>{data.height_source ? ` (${data.height_source})` : ''}</div>
      )}
      {data.adg_compliant != null && (
        <div>
          ADG solar access:{' '}
          <span className={cn('inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium ring-1',
            data.adg_compliant ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-amber-50 text-amber-700 ring-amber-200')}>
            {data.adg_compliant ? 'meets the 3-hour guideline' : 'below the 3-hour guideline'}
          </span>
        </div>
      )}
      {worst && (worst.shadow_length_m != null || worst.overlap_pct != null) && (
        <div className="text-slate-700">
          Worst case ({[worst.date_label, worst.time_label].filter(Boolean).join(' ')}):{' '}
          {worst.shadow_length_m != null ? `${worst.shadow_length_m} m shadow` : ''}
          {worst.shadow_length_m != null && worst.overlap_pct != null ? ', ' : ''}
          {worst.overlap_pct != null ? `${worst.overlap_pct}% overlap on neighbours` : ''}
        </div>
      )}
      {data.temporal_caveat && <div className="text-[11px] text-slate-400 leading-snug mt-1">{data.temporal_caveat}</div>}
    </div>
  );
}

interface OverlayItem { layer_type?: string; value?: unknown; instrument?: string | null; lga?: string | null; }

// Planning overlays arrive as a list of {layer_type, value} — render them as a
// readable list ("Acid sulfate: Class 5", "Lot size: 450 m²"), not "2 items".
function OverlayList({ overlays }: { overlays: OverlayItem[] }) {
  const rows = overlays.filter((o) => o && o.layer_type && o.value != null && o.value !== '');
  if (rows.length === 0) return <span className="text-sm text-emerald-700">Checked the NSW planning overlays (flood, heritage, biodiversity, acid sulfate, coastal) — none apply at this property.</span>;
  return (
    <ul className="text-sm text-slate-900 space-y-0.5">
      {rows.map((o, i) => {
        const unit = OVERLAY_UNIT[o.layer_type as string];
        const v = formatValue(o.value);
        // The additional_permitted_uses overlay returns a bare LEP Schedule-1
        // reference code (e.g. "51"), not a count — render it as a reference
        // pointing back to the LEP, not a meaningless number.
        const display = o.layer_type === 'additional_permitted_uses' && v !== '—'
          ? `Applies (ref ${v}) — see LEP`
          : (unit && v !== '—' ? `${v} ${unit}` : v);
        return (
          <li key={i}>
            <span className="text-slate-500">{formatKey(o.layer_type as string)}:</span>{' '}
            {display}
          </li>
        );
      })}
    </ul>
  );
}

interface ClimateFinding { hazard?: string; value?: number; unit?: string; data_date?: string; confidence?: string; }

// Turn a raw climate empirical finding into one plain-English line, e.g.
// "Urban heat: +7.3 °C above surrounding areas (2016 data — most recent available)".
function humanizeClimateFinding(f: ClimateFinding): { label: string; detail: string } | null {
  if (!f || f.value == null) return null;
  const yr = f.data_date ? f.data_date.slice(0, 4) : '';
  const stale = f.confidence === 'stale';
  if (f.hazard === 'urban_heat_island') {
    return {
      label: 'Urban heat',
      detail: `+${f.value.toFixed(1)} °C above surrounding areas${yr ? ` (${yr} data${stale ? ' — most recent available' : ''})` : ''}`,
    };
  }
  if (f.hazard === 'extreme_rainfall') {
    return {
      label: 'Extreme rainfall',
      detail: `${f.value.toFixed(1)} mm in 60 min (1% annual chance)${yr ? ` (${yr})` : ''}`,
    };
  }
  // Fallback: humanise the hazard name + value, drop the snake_case unit jargon.
  return {
    label: formatKey(f.hazard ?? 'Hazard'),
    detail: `${f.value}${f.unit ? ` ${f.unit.replace(/_/g, ' ')}` : ''}${yr ? ` (${yr})` : ''}`,
  };
}

function ClimateCard({ data }: { data: Record<string, unknown> }) {
  const empirical = (data.empirical_findings as ClimateFinding[] | undefined) ?? [];
  const lines = empirical.map(humanizeClimateFinding).filter(Boolean) as { label: string; detail: string }[];
  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Climate Disclosure</h3>
          <p className="text-xs text-slate-500 mt-0.5">Heat island, rainfall intensity</p>
        </div>
        <span className="px-2 py-0.5 text-xs font-medium rounded bg-amber-100 text-amber-800">Estimated</span>
      </div>
      <div className="px-5 py-4">
        {lines.length === 0 ? (
          <div className="text-sm text-slate-400">No climate hazards recorded at this property.</div>
        ) : (
          <dl className="space-y-2">
            {lines.map((l, i) => (
              <div key={i} className="flex flex-col">
                <dt className="text-xs font-medium text-slate-500">{l.label}</dt>
                <dd className="text-sm text-slate-900 mt-0.5">{l.detail}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </div>
  );
}

// Internal source slugs -> the real-world data source, so the brief can list
// "every figure traced to its source" honestly at the bottom.
const SOURCE_LABELS: Record<string, string> = {
  postgis_overlays: 'NSW planning overlays (PostGIS)',
  live_protection_overlay: 'NSW Planning Portal — Protection layers',
  planning_portal_protection: 'NSW Planning Portal — Protection layers',
  cadastre_strata: 'NSW cadastre (strata/lot)',
  postgis_heritage: 'NSW heritage (PostGIS)',
  anef_zones: 'ANEF aircraft-noise contours',
  planning_portal: 'NSW Planning Portal',
  bushfire_prescreen: 'NSW RFS Bushfire Prone Land map',
  flood_truth: 'Flood screening (JRC / WOfS / BoM)',
  housing_sepp_standards: 'SEPP (Housing) 2021 standards',
  constraint_arithmetic_engine: 'Computed — constraint engine',
  terrain_analysis: 'Computed — 5 m DEM terrain',
  granny_flat_detect: 'Satellite imagery + structure detection',
  vg_valuation: 'NSW Valuer General',
  nsw_spatial_services: 'NSW Spatial Services',
  epa_contaminated_sites: 'NSW EPA contaminated-land register',
};

function humanizeSource(slug: string): string {
  if (slug in SOURCE_LABELS) return SOURCE_LABELS[slug];
  return slug.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// Walk the streamed sections and collect every distinct data source + any
// legislation/source URL, so the brief footer can list provenance.
function collectSources(sections: { data: { data: unknown } }[]): {
  sources: { label: string; asAt?: string }[];
  links: { label: string; url: string }[];
} {
  const srcMap = new Map<string, string | undefined>();
  const linkMap = new Map<string, string>();
  const walk = (v: unknown) => {
    if (!v || typeof v !== 'object') return;
    if (Array.isArray(v)) { v.forEach(walk); return; }
    const o = v as Record<string, unknown>;
    if (typeof o.source === 'string' && o.source && !srcMap.has(o.source)) {
      srcMap.set(o.source, typeof o.as_at === 'string' ? o.as_at : undefined);
    }
    for (const [k, val] of Object.entries(o)) {
      if (/url$/i.test(k) && typeof val === 'string' && val.startsWith('http')) {
        if (!linkMap.has(val)) linkMap.set(val, formatKey(k.replace(/_url$/i, '')) || 'Source');
      }
      walk(val);
    }
  };
  sections.forEach((s) => walk(s.data.data));
  return {
    sources: [...srcMap.entries()].map(([s, asAt]) => ({ label: humanizeSource(s), asAt }))
      .sort((a, b) => a.label.localeCompare(b.label)),
    links: [...linkMap.entries()].map(([url, label]) => ({ label, url })),
  };
}

// Cross-section planning context, so a "doesn't apply" card can explain WHY using
// the lot's real zone, instrument and lot size — not a curt one-liner.
interface PlanningContext {
  zone?: string; zoneFull?: string; zoneEpi?: string; legislationUrl?: string; lotAreaM2?: number;
}
function getPlanningContext(sections: { data: { section: string; data: unknown } }[]): PlanningContext {
  const unwrap = (v: unknown): unknown => (isDataField(v) ? v.value : v);
  const ctx: PlanningContext = {};
  for (const s of sections) {
    const d = s.data.data as Record<string, unknown> | null;
    const v = (d && isDataField(d) ? (d.value as Record<string, unknown>) : d) || {};
    if (s.data.section === 'planning_controls') {
      ctx.zone = (unwrap(v.zone) as string) ?? ctx.zone;
      ctx.zoneFull = (unwrap(v.zone_full) as string) ?? ctx.zoneFull;
      ctx.zoneEpi = (unwrap(v.zone_epi) as string) ?? ctx.zoneEpi;
      ctx.legislationUrl = (unwrap(v.legislation_url) as string) ?? ctx.legislationUrl;
    }
    if (s.data.section === 'economics') {
      const la = unwrap(v.lot_area_m2);
      if (typeof la === 'number') ctx.lotAreaM2 = la;
    }
  }
  return ctx;
}

// Is this a residential zone where the Housing-SEPP residential forms can apply?
function isResidentialZone(zone?: string): boolean {
  return /^(R1|R2|R3|R4|R5|RU5)\b/.test((zone || '').trim());
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'boolean') return val ? 'Yes' : 'No';
  if (typeof val === 'number') {
    if (Number.isInteger(val)) return val.toLocaleString();
    return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  if (typeof val === 'string') {
    const t = val.trim();
    // Serialised empties read as data, not a value — collapse to an em dash.
    if (t === '' || /^(none|null|nan|undefined)$/i.test(t)) return '—';
    // Lowercase snake_case values are enums (e.g. "not_strata") — humanise them.
    if (/^[a-z0-9]+(_[a-z0-9]+)+$/.test(t)) {
      const s = t.replace(/_/g, ' ');
      return s.charAt(0).toUpperCase() + s.slice(1);
    }
    return val;
  }
  if (Array.isArray(val)) {
    if (val.length === 0) return '—';
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

// When the Housing-SEPP residential forms don't apply, don't say "doesn't apply" —
// explain WHY with the lot's real zone + instrument, and what it means for housing
// on this land. A "no" carrying context is the product's value.
function SeppContextCard({ ctx }: { ctx: PlanningContext }) {
  const zoneLabel = ctx.zone
    ? `${ctx.zone}${ctx.zoneFull ? ` (${ctx.zoneFull})` : ''}`
    : 'this zone';
  const instrument = ctx.zoneEpi || 'the Local Environmental Plan';
  const residential = isResidentialZone(ctx.zone);
  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100">
        <h3 className="text-sm font-semibold text-slate-900">Housing SEPP — Low &amp; Mid-Rise</h3>
        <p className="text-xs text-slate-500 mt-0.5">Denser housing forms the policy permits, and whether they reach this lot</p>
      </div>
      <div className="px-5 py-4 text-sm text-slate-700 leading-relaxed space-y-2">
        {residential ? (
          <p>
            This lot sits in <span className="font-medium text-slate-900">{zoneLabel}</span> under{' '}
            {ctx.legislationUrl
              ? <a href={ctx.legislationUrl} target="_blank" rel="noopener noreferrer" className="text-teal-600 underline [overflow-wrap:anywhere]">{instrument}</a>
              : instrument}. It&apos;s a residential zone, but the Low &amp; Mid-Rise Housing standards
            (terraces, townhouses, manor houses and residential flats) couldn&apos;t be loaded for
            it — re-run the brief, or check the standards directly in the instrument above.
          </p>
        ) : (
          <>
            <p>
              This lot is zoned <span className="font-medium text-slate-900">{zoneLabel}</span> under{' '}
              {ctx.legislationUrl
                ? <a href={ctx.legislationUrl} target="_blank" rel="noopener noreferrer" className="text-teal-600 underline [overflow-wrap:anywhere]">{instrument}</a>
                : instrument} — not a residential zone.
            </p>
            <p>
              The Low &amp; Mid-Rise Housing reforms (terraces, townhouses, manor houses, residential
              flats) reach only the residential zones <span className="font-medium">R1–R4</span>, so they
              don&apos;t apply here. On a centre/business zone like this, housing is delivered through the
              zone&apos;s own permitted uses — typically <span className="font-medium">shop-top housing</span>{' '}
              above ground-floor retail — rather than the low-and-mid-rise pathway.
            </p>
            <p className="text-slate-500">
              See the land use table in the instrument above for what this specific lot permits, and the
              Development Capacity card for the buildable envelope.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

// Granny Flat — decoupled to the working async pipeline. The brief fires the same
// gated /api/satellite/granny-flat route the standalone tool uses (which gates on
// SEPP cl 50/53 BEFORE the GPU scan, so an ineligible lot costs nothing), then polls
// granny_flat_reports and renders a rich, cited card.
type GfState =
  | { kind: 'loading' }
  | { kind: 'ineligible'; reason: string; evidence?: string }
  | { kind: 'result'; count: number | null; seppEligible: boolean; ineligibleReason?: string; lotAreaM2?: number }
  | { kind: 'error'; message: string };

function GrannyFlatCard({ address, active }: { address?: string; active: boolean }) {
  const [state, setState] = useState<GfState | null>(null);
  useEffect(() => {
    if (!active || !address) { setState(null); return; }
    let cancelled = false;
    setState({ kind: 'loading' });

    const poll = async (jobId: string) => {
      for (let attempts = 0; !cancelled && attempts < 90; attempts++) {
        await new Promise((r) => setTimeout(r, 2000));
        if (cancelled) return;
        try {
          const r = await fetch(`/api/satellite/granny-flat?jobId=${encodeURIComponent(jobId)}`);
          const d = await r.json();
          if (d.status === 'detected' || d.status === 'completed') {
            const o = (d.data || {}) as Record<string, unknown>;
            setState({
              kind: 'result',
              count: (o.confirmed_structure_count as number) ?? (o.samgeo_structure_count as number) ?? null,
              seppEligible: !!o.sepp_eligible,
              ineligibleReason: (o.sepp_ineligible_reason as string) || undefined,
              lotAreaM2: (o.lot_area_m2 as number) || undefined,
            });
            return;
          }
          if (d.status === 'error') { setState({ kind: 'error', message: d.message || d.error || 'Detection failed — try again.' }); return; }
        } catch { /* transient — keep polling */ }
      }
      if (!cancelled) setState({ kind: 'error', message: 'The building scan timed out — try running the brief again.' });
    };

    fetch('/api/satellite/granny-flat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address, action: 'detect' }),
    })
      .then(async (r) => {
        const d = await r.json();
        if (cancelled) return;
        if (d.ineligible) { setState({ kind: 'ineligible', reason: d.error, evidence: d.evidence }); return; }
        if (!r.ok || !d.jobId) { setState({ kind: 'error', message: d.error || 'Couldn’t start the building scan.' }); return; }
        poll(d.jobId as string);
      })
      .catch(() => { if (!cancelled) setState({ kind: 'error', message: 'Couldn’t start the building scan.' }); });

    return () => { cancelled = true; };
  }, [active, address]);

  const Shell = ({ badge, badgeClass, children }: { badge: string; badgeClass: string; children: ReactNode }) => (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Secondary Dwelling</h3>
          <p className="text-xs text-slate-500 mt-0.5">Granny-flat feasibility — buildings on the lot + eligibility</p>
        </div>
        <span className={`px-2 py-0.5 text-xs font-medium rounded ${badgeClass}`}>{badge}</span>
      </div>
      <div className="px-5 py-4 text-sm leading-relaxed">{children}</div>
    </div>
  );

  if (!active) return <Shell badge="Not run" badgeClass="bg-teal-50 text-teal-700"><span className="text-slate-500">Tick “Include satellite analysis” above and re-run to scan the lot’s buildings and check granny-flat eligibility.</span></Shell>;
  if (!state || state.kind === 'loading') return <Shell badge="Analysing…" badgeClass="bg-slate-100 text-slate-500"><span className="text-slate-500 animate-pulse">Scanning the aerial image for buildings and checking secondary-dwelling eligibility… (up to ~90s)</span></Shell>;
  if (state.kind === 'ineligible') return (
    <Shell badge="Not available here" badgeClass="bg-amber-50 text-amber-700">
      <p className="text-slate-700">{state.reason}</p>
      {state.evidence && <p className="text-slate-500 mt-1">{state.evidence}</p>}
    </Shell>
  );
  if (state.kind === 'error') return <Shell badge="Couldn’t complete" badgeClass="bg-slate-100 text-slate-500"><span className="text-slate-500">{state.message}</span></Shell>;
  return (
    <Shell badge="Estimated" badgeClass="bg-amber-100 text-amber-800">
      <p className="text-slate-900">
        {state.count != null
          ? <><span className="font-medium">{state.count}</span> existing building{state.count === 1 ? '' : 's'} detected on the lot from the aerial image.</>
          : 'Building scan complete.'}
      </p>
      <p className="mt-1 text-slate-700">
        {state.seppEligible
          ? <>This lot <span className="font-medium">meets</span> the SEPP (Housing) 2021 secondary-dwelling lot standard{state.lotAreaM2 ? ` (lot ${Math.round(state.lotAreaM2)} m²)` : ''} — a granny flat is a permissible form, subject to the detailed controls.</>
          : (state.ineligibleReason || 'This lot does not meet the SEPP secondary-dwelling lot standard.')}
      </p>
      <p className="mt-2 text-xs text-slate-400">Confirm the detected building count in the Granny Flat tool before relying on the figure.</p>
    </Shell>
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
  hillshade_png_b64?: string | null;
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
      {data.hillshade_png_b64 && (
        <div className="px-5 pt-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={data.hillshade_png_b64}
            alt="Shaded-relief terrain diagram of the lot"
            className="w-full rounded-md border border-slate-200 bg-slate-50"
            style={{ maxHeight: 220, objectFit: 'cover' }}
          />
          <p className="text-[11px] text-slate-400 mt-1">
            Shaded relief from the 5&nbsp;m elevation model — lighter is higher ground, shadows show the slope. Indicative.
          </p>
        </div>
      )}
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
  'satellite.granny_flat', 'satellite.terrain',
  // 'satellite.pre_da_history' soft-dropped — see the sectionEvents filter below.
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

function CompleteSummary({ data, hiddenGapFields }: { data: BriefComplete; hiddenGapFields: Set<string> }) {
  const { confidence_summary: cs, compound_constraints, gaps: allGaps, data_currency_warnings, elapsed_seconds } = data;
  // Hide gaps resolved elsewhere (pre_da soft-dropped; bushfire that resolved to
  // "not bushfire-prone") so the list doesn't contradict the cards above.
  const gaps = allGaps.filter((g) => !hiddenGapFields.has(g.field));

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
          <div><span className="text-slate-500">Not available:</span> <span className="font-medium">{cs.not_available}</span></div>
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

// Plain-English definitions of the confidence labels stamped on each figure.
const CONFIDENCE_LEGEND: { label: string; color: string; meaning: string }[] = [
  { label: 'Authoritative', color: 'text-emerald-600', meaning: 'Taken directly from an official government source (the LEP, the cadastre, the Valuer General) — treat as fact.' },
  { label: 'Estimated', color: 'text-amber-600', meaning: 'A modelled or screening figure from satellite/statistical data — a guide to investigate, not a measured value.' },
  { label: 'Derived', color: 'text-blue-600', meaning: 'Computed by us from authoritative inputs (e.g. the buildable GFA from the FSR × lot area).' },
  { label: 'Extracted', color: 'text-purple-600', meaning: 'Pulled from a source document (e.g. a DCP clause) by our extraction pipeline.' },
];

// Data sources + a confidence legend. Rendered from the section cards already on
// the client, so it appears even when the stream's final 'complete' event is dropped.
function DataSourcesCard({ provenance }: {
  provenance: { sources: { label: string; asAt?: string }[]; links: { label: string; url: string }[] };
}) {
  if (provenance.sources.length === 0 && provenance.links.length === 0) return null;
  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-5">
      <h3 className="text-sm font-semibold text-slate-900 mb-3">Data sources</h3>
      {provenance.sources.length > 0 && (
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
          {provenance.sources.map((s, i) => (
            <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
              <span className="text-slate-300 mt-0.5 flex-shrink-0">&#9679;</span>
              <span>{s.label}{s.asAt ? <span className="text-slate-400"> — as at {s.asAt}</span> : null}</span>
            </li>
          ))}
        </ul>
      )}
      {provenance.links.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap gap-x-4 gap-y-1">
          {provenance.links.map((l, i) => (
            <a key={i} href={l.url} target="_blank" rel="noopener noreferrer"
               className="text-xs text-teal-600 hover:text-teal-800 underline [overflow-wrap:anywhere]">
              {l.label} ↗
            </a>
          ))}
        </div>
      )}
      <p className="text-xs text-slate-400 mt-3">
        Each figure above is drawn from these government, satellite and computed sources.
      </p>
      <div className="mt-4 pt-4 border-t border-slate-100">
        <h4 className="text-xs font-semibold text-slate-700 mb-2">What the confidence labels mean</h4>
        <dl className="space-y-1.5">
          {CONFIDENCE_LEGEND.map((c) => (
            <div key={c.label} className="text-xs flex gap-2">
              <dt className={`font-medium flex-shrink-0 ${c.color}`}>{c.label}</dt>
              <dd className="text-slate-500">{c.meaning}</dd>
            </div>
          ))}
        </dl>
      </div>
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
  const [ranWithSatellite, setRanWithSatellite] = useState(false);
  const [lotPolygon, setLotPolygon] = useState<{ type: 'Polygon'; coordinates: number[][][] } | null>(null);
  const [publicAccessToken, setPublicAccessToken] = useState<string | null>(null);
  const [parts, setParts] = useState<BriefEvent[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const stateRef = useRef<PageState>(state);
  stateRef.current = state;
  // Whether the realtime stream has delivered any real brief data (vs only
  // keepalive pings). Distinguishes "stream closed after streaming data" from
  // "stream closed while the run is still queued / never started by a worker".
  const receivedDataRef = useRef(false);

  // Elapsed timer — starts on trigger, stops on complete/error
  const timerRunning = state === 'triggering' || state === 'streaming';
  const elapsed = useElapsedSeconds(timerRunning);

  // Derive state from parts
  const metadataEvent = parts.find((p): p is Extract<BriefEvent, { event: 'metadata' }> => p.event === 'metadata');
  const sectionEvents = parts
    .filter((p): p is Extract<BriefEvent, { event: 'section' }> => p.event === 'section')
    // Pre-DA Site History soft-dropped (2026-06): it needs a heavy ML dependency
    // (torch/Tessera) the web container can't host, so it always errored. Hide the card
    // until it's decoupled to a worker. Backend code retained — re-enable by removing
    // this filter, restoring the toggle, and re-adding it to EXPECTED_SECTIONS_SAT.
    .filter((p) => p.data.section !== 'satellite.pre_da_history');
  const completeEvent = parts.find((p): p is Extract<BriefEvent, { event: 'complete' }> => p.event === 'complete');
  const planningCtx = getPlanningContext(sectionEvents);

  // Gaps to hide from the Data Gaps list because they're resolved elsewhere:
  // pre_da is soft-dropped, and a bushfire prescreen that resolved to "not
  // bushfire-prone" (value present, category null) must not also surface as a
  // "returned no data" gap — the card already shows the answer, so a gap line
  // reads as a direct contradiction. A genuine failure (value absent) still gaps.
  const hiddenGapFields = new Set<string>(['satellite.pre_da_history']);
  const bfEvent = sectionEvents.find((p) => p.data.section === 'satellite.bushfire');
  const bfData = bfEvent?.data.data as { value?: { category?: unknown } } | null | undefined;
  if (bfData?.value && typeof bfData.value === 'object' && bfData.value.category == null) {
    hiddenGapFields.add('satellite.bushfire');
  }

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
                  receivedDataRef.current = true;
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

          // Stream ended without a 'complete' event. Two very different cases:
          if (stateRef.current !== 'complete' && stateRef.current !== 'error') {
            if (receivedDataRef.current) {
              // Real data arrived — the stream just closed without a clean
              // 'complete' terminator. Treat as done (preserves the trailing-
              // event flush fix).
              setState('complete');
              return;
            }
            // Zero data: the run hasn't streamed anything yet. Trigger.dev
            // closes idle streams (~60s) before a queued run gets a worker, so
            // this close does NOT mean the brief finished. Reconnect and keep
            // showing "generating" rather than painting a false "Complete".
            retries++;
            if (retries >= maxRetries) {
              setState('error');
              setErrorMsg('The brief is still queued — no worker picked it up in time. Please try again in a moment.');
              return;
            }
            await new Promise(r => setTimeout(r, 2000));
            continue;
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
    receivedDataRef.current = false;
    // Record whether satellite analysis was requested for THIS run, so an empty
    // satellite section reads honestly ("no result") instead of "tick the box".
    setRanWithSatellite(includeSatellite);

    try {
      const res = await fetch('/api/intelligence-brief', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: selectedAddress,
          lat: selectedLat,
          lng: selectedLng,
          include_satellite: includeSatellite,
          // Pre-DA site history soft-dropped (heavy ML dep can't run in the web
          // container); keep premium off until it's decoupled to a worker.
          include_premium: false,
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
  }, [selectedAddress, selectedLat, selectedLng, includeSatellite]);

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
              if (section === 'satellite.granny_flat') {
                // Decoupled: the card fires the gated async route itself (gate +
                // real Modal scan), rather than the brief's timed-out inline run.
                card = <GrannyFlatCard address={metadataEvent?.data.address ?? selectedAddress} active={ranWithSatellite} />;
              }
              if (section === 'constraint_arithmetic') {
                const ca = (event.data.data?.value ?? null) as ConstraintArithmeticResult | null;
                if (ca) {
                  card = (
                    <ConstraintArithmeticCard
                      briefData={ca}
                      lotArea={ca.lot_area_m2}
                      devType={ca.dev_type}
                      zone={planningCtx.zone}
                    />
                  );
                }
              }
              if (section === 'sepp_housing') {
                const standards = (event.data.data?.value ?? null) as SeppStandard[] | null;
                if (standards && standards.length) {
                  card = <SeppHousingCard standards={standards} />;
                } else {
                  card = <SeppContextCard ctx={planningCtx} />;
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
              if (section === 'satellite.climate_disclosure') {
                const raw = event.data.data as Record<string, unknown> | null;
                const cd = (raw && typeof raw === 'object'
                  ? ((raw.value as Record<string, unknown>) ?? raw)
                  : null);
                if (cd && Array.isArray(cd.empirical_findings)) {
                  card = <ClimateCard data={cd} />;
                }
              }
              if (section === 'dcp_controls' && planningCtx.zone && !isResidentialZone(planningCtx.zone)) {
                // The extracted DCP controls in the brief are residential development
                // controls (setbacks, landscaping for dwellings). On a non-residential
                // zone they may not apply — caveat rather than present them as binding.
                card = (
                  <div className="space-y-2">
                    <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
                      These are residential development controls. {planningCtx.zone} is a non-residential zone, so they may not apply to development here — see the DCP document below for the controls specific to this zone.
                    </div>
                    <SectionCard section={section} data={event.data.data} satelliteRan={ranWithSatellite} />
                  </div>
                );
              }
              if (!card) {
                card = <SectionCard section={section} data={event.data.data} satelliteRan={ranWithSatellite} />;
              }
              return (
                <div key={`${section}-${i}`} className={cn('min-w-0', spanFor(section))}>
                  {card}
                </div>
              );
            })}
          </div>

          {/* Complete summary */}
          {completeEvent && <CompleteSummary data={completeEvent.data} hiddenGapFields={hiddenGapFields} />}
          {/* Data sources + confidence legend — built from the section cards, so it
              shows even when the stream's final 'complete' event is dropped. */}
          {state === 'complete' && sectionEvents.length > 0 && (
            <DataSourcesCard provenance={collectSources(sectionEvents)} />
          )}
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
