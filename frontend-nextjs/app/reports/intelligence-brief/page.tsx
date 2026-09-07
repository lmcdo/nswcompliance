'use client';

import { deliveredKwhFrom, deliveryBasisText } from '@/lib/solar/delivered';

import { useState, useCallback, useEffect, useMemo, useRef, Suspense, type ReactNode } from 'react';
import { useSearchParams } from 'next/navigation';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { PostResultEmailStrip } from '@/components/reports/PostResultEmailStrip';
import { ConstraintArithmeticCard, type ConstraintArithmeticResult, type EnvelopeGap, type InputLedgerRow } from '@/components/compliance/ConstraintArithmeticCard';
import { cn } from '@/lib/utils';
import AerialTile from '@/components/reports/AerialTile';
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2';
import { DAOutcomesDisplay, RefusalStatsSentence, type DAOutcomesPayload, type RefusalStatsRow } from '@/components/reports/DAOutcomes';
import { BriefIntentBar, BriefOverlayCard, assembleBriefPayload } from '@/components/reports/BriefIntentOverlay';
import { SeppContextCard } from '@/components/reports/SeppContextCard';
import { GrannyFlatBriefCard } from '@/components/reports/GrannyFlatBriefCard';
import { describeUnavailable, type UnavailableTone } from './unavailable';
import { ShadowDisplay, type ShadowData } from '@/components/reports/ShadowDetailDisplay';
import { floodSignalLine, emsLine, type EmsActivation } from './satellite-copy';
import { floodZoneUnavailableMessage } from '@/lib/not-assessed';
import { collectSources } from './provenance';

// Brief LLM overlay (flag-gated, default OFF; #742 engine). Both this build-time
// flag AND the Railway-side BRIEF_LLM_OVERLAY_ENABLED must be on for anything
// to show — turning either off restores today's page exactly.
const OVERLAY_UI_ENABLED = process.env.NEXT_PUBLIC_BRIEF_LLM_OVERLAY_ENABLED === 'true';

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
// Titles say what the reader GETS, not the instrument's acronym — the acronym
// rides in the description for the planners who want it.
const SECTION_LABELS: Record<string, { label: string; description: string }> = {
  economics: { label: 'Land Value & Economics', description: 'The Valuer General’s land value, lot area and five-year valuation history' },
  market_context: { label: 'Market Context', description: 'Comparable land valuations and recent sales nearby (NSW Valuer General)' },
  strata: { label: 'Title & Ownership', description: 'Lot type, plan number, strata structure from the NSW cadastre' },
  environmental_constraints: { label: 'Environmental Constraints', description: 'Flood, bushfire, heritage, contamination and other mapped overlays' },
  planning_controls: { label: 'Planning Controls', description: 'Zoning, height, FSR and lot-size standards from the LEP' },
  dcp_controls: { label: 'Council Development Controls', description: 'Setbacks, landscaping and built-form provisions from the DCP' },
  sepp_housing: { label: 'SEPP Housing', description: 'State policy housing standards' },
  neighbourhood: { label: 'Neighbourhood Activity', description: 'Development applications nearby, outcomes, and shadow analysis' },
  constraint_arithmetic: { label: 'Development Capacity', description: 'Indicative yield and the binding planning constraint' },
  'satellite.bushfire': { label: 'Bushfire Risk', description: 'Bushfire attack level, vegetation category' },
  'satellite.flood': { label: 'Flood Analysis', description: 'Multi-source flood occurrence screening' },
  'satellite.climate_disclosure': { label: 'Climate Hazards & Projections', description: 'Hazard screening, heat and rainfall calculations, climate-model projections' },
  'satellite.granny_flat': { label: 'Secondary Dwelling', description: 'Granny-flat feasibility — buildings on the lot + eligibility' },
  'satellite.pre_da_history': { label: 'Prior Development Activity', description: 'Historical development activity timeline' },
  'satellite.terrain': { label: 'Terrain Analysis', description: 'Slope, aspect and drainage from elevation' },
  'satellite.solar': { label: 'Solar Potential', description: 'Roof capacity and yield from aerial imagery (Google Solar)' },
};

// Cards stack full-width, one per row — field-heavy sections were unreadable as
// narrow grid tiles (a <400px container forces every label/value pair into a
// tall tower; at full width the key-value grid inside each card spreads to 3-4
// columns instead). The anchor id lets the sticky section bar jump here.
function sectionAnchorId(section: string): string {
  return `brief-${section.replace(/\./g, '-')}`;
}

// Confidence level styling
// Ring-pill badge with a status dot. Display labels only — the enum values are
// unchanged. 'estimated' renders as "Calculated": these figures are exact
// calculations on satellite/statistical/model data, and "Estimated" read as
// guesswork; the legend spells out the distinction from on-site measurement.
const CONFIDENCE_BADGE_STYLES: Record<string, { label: string; pill: string; dot: string }> = {
  authoritative: { label: 'Authoritative', pill: 'bg-emerald-50 text-emerald-800 ring-emerald-600/20', dot: 'bg-emerald-500' },
  estimated: { label: 'Calculated', pill: 'bg-amber-50 text-amber-800 ring-amber-600/25', dot: 'bg-amber-500' },
  derived: { label: 'Derived', pill: 'bg-blue-50 text-blue-800 ring-blue-600/20', dot: 'bg-blue-500' },
  extracted: { label: 'Extracted', pill: 'bg-purple-50 text-purple-800 ring-purple-600/20', dot: 'bg-purple-500' },
  not_available: { label: 'Not Available', pill: 'bg-red-50 text-red-800 ring-red-600/20', dot: 'bg-red-500' },
};

function confidenceBadge(confidence: string) {
  const s = CONFIDENCE_BADGE_STYLES[confidence]
    ?? { label: confidence, pill: 'bg-slate-100 text-slate-600 ring-slate-400/20', dot: 'bg-slate-400' };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${s.pill}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} aria-hidden="true" />
      {s.label}
    </span>
  );
}

// SECTION_LABELS stays here (page-level copy); describeUnavailable takes the
// section's description as a parameter so the wording module has no page deps.
const sectionDesc = (s?: string): string | undefined =>
  s ? SECTION_LABELS[s]?.description : undefined;

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
  r3r4: 'R3/R4',
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
        : describeUnavailable(reason, section, satelliteRan, sectionDesc(section)))
    : null;

  return (
    <div id={`brief-section-${section.replace('.', '-')}`} className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
      <div className="px-5 py-4 border-b border-slate-200/70 bg-gradient-to-r from-slate-50/90 via-white to-white flex items-center justify-between gap-3">
        <div>
          <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-slate-900 [text-wrap:balance]">{meta.label}</h3>
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
        ) : value && section === 'strata' ? (
          <StrataDisplay data={value} />
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
// Title & Ownership (strata) — answer the question once, in prose
// ---------------------------------------------------------------------------

// Scheme-type wording for strata lots. The raw enum value "development" means
// a strata townhouse/villa scheme — rendering it verbatim would be opaque.
const STRATA_SCHEME_LABELS: Record<string, string> = {
  apartment: 'Apartment scheme',
  development: 'Townhouse / villa scheme (non-apartment strata)',
  ambiguous: 'Strata scheme (building type not determinable from the cadastre)',
};

function StrataDisplay({ data }: { data: Record<string, unknown> }) {
  const strataType = typeof data.strata_type === 'string' ? data.strata_type : '';
  const planLabel = typeof data.plan_label === 'string' && data.plan_label ? data.plan_label : null;
  const strataPlan = typeof data.strata_plan === 'string' && data.strata_plan ? data.strata_plan : null;
  const lotNumber = data.lot_number != null && data.lot_number !== '' ? String(data.lot_number) : null;
  const sectionNumber = data.section_number != null && data.section_number !== '' ? String(data.section_number) : null;
  // Treat as strata when EITHER signal says so (a contradictory record must
  // not hide the strata detail).
  const isStrata = data.is_strata === true || (strataType !== '' && strataType !== 'not_strata');

  // "Lot 5, Section 2, DP900454" — the legal title reference used on
  // contracts and 10.7 certificates.
  const legalRef = planLabel
    ? [lotNumber && `Lot ${lotNumber}`, sectionNumber && `Section ${sectionNumber}`, planLabel]
        .filter(Boolean)
        .join(', ')
    : null;

  if (!isStrata) {
    // A freehold house needs one sentence, not four rows repeating "not strata".
    return (
      <p className="text-sm text-slate-900">
        Freehold title — this lot is not part of a strata scheme.
        {legalRef && (
          <> The legal title reference from the NSW cadastre is{' '}
          <span className="font-medium">{legalRef}</span>.</>
        )}
      </p>
    );
  }

  const rows: Array<{ label: string; value: string; hint?: string }> = [
    { label: 'Title type', value: 'Strata' },
    { label: 'Scheme type', value: STRATA_SCHEME_LABELS[strataType] ?? formatValue(strataType) },
  ];
  const plan = strataPlan ?? planLabel;
  if (plan) rows.push({ label: 'Strata plan number', value: plan });
  if (lotNumber) {
    rows.push({ label: 'Lot in the scheme', value: `Lot ${lotNumber}`,
                hint: 'This property’s own lot within the strata plan (NSW cadastre).' });
  }
  if (data.lot_total != null) {
    rows.push({ label: 'Lots in the scheme', value: formatValue(data.lot_total),
                hint: 'Number of lots in the strata scheme (NSW Strata Hub).' });
  }
  if (typeof data.dwelling_type === 'string' && data.dwelling_type) {
    rows.push({ label: 'Building form', value: formatValue(data.dwelling_type),
                hint: 'Classified from the strata scheme’s lot count (NSW Strata Hub).' });
  }
  if (typeof data.registration_date === 'string' && data.registration_date) {
    rows.push({ label: 'Strata plan registered', value: data.registration_date });
  }

  return (
    <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-8 gap-y-3.5">
      {rows.map((row) => (
        <div key={row.label} className="flex flex-col">
          <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{row.label}</dt>
          <dd className="text-sm text-slate-900 mt-0.5">{row.value}</dd>
          {row.hint && <dd className="text-[11px] text-slate-400 mt-0.5">{row.hint}</dd>}
        </div>
      ))}
    </dl>
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
  // Measured nearest-feature distances (decorate the "No" rows below; the map
  // itself is not a row).
  const nearestRaw = (data.nearest_features as { value?: Record<string, number> | null } | undefined)?.value ?? null;

  // Hide: internal QA fields; standalone units rows (merged above); the duplicate
  // lot area (kept in Economics); empty "...reason" rows (e.g. an ineligible
  // reason when the lot is actually eligible); the nearest_features map
  // (rendered as decorations); and null detail rows whose host boolean already
  // answers (contaminated_detail etc.).
  const entries = Object.entries(data).filter(
    ([key, val]) =>
      !['confidence', 'source', 'as_at', 'reason', 'overlay_coverage', 'nearest_features'].includes(key) &&
      !key.endsWith('_units') &&
      !(key === 'lot_area_m2' && section !== 'economics') &&
      !(/reason/i.test(key) && (val === null || val === undefined || val === '')) &&
      !(HIDE_WHEN_NULL_KEYS.has(key) && (isDataField(val) ? val.value == null : val == null)),
  );

  if (entries.length === 0) {
    return <span className="text-sm text-slate-400">No data fields</span>;
  }

  return (
    <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-8 gap-y-3.5">
      {entries.map(([key, val]) => {
        // Unwrap DataField: extract .value and show confidence badge
        if (isDataField(val)) {
          const df = val;
          const dfValueEmpty = df.value == null ||
            (Array.isArray(df.value) && df.value.length === 0);
          if (df.confidence === 'not_available' && dfValueEmpty) {
            // #745 D7-2: only short-circuit when there is genuinely nothing to
            // show — a populated list (e.g. permitted uses) must render even if
            // the confidence badge is not_available.
            const u = describeUnavailable(df.reason, section, satelliteRan, sectionDesc(section));
            // describeUnavailable already writes the plain-English sentence; the
            // field used to render only u.label and throw u.detail away. A bare
            // "None here" or "Not assessed" cannot tell the reader whether
            // anything was checked — the same absence-vs-failure ambiguity the
            // section-level renderer (and every other call site) avoids by
            // showing the detail. Labels must be self-explanatory without
            // context, so show both.
            return (
              <div key={key} className="flex flex-col">
                <FieldLabel fieldKey={key} />
                <dd className={`text-sm mt-0.5 ${UNAVAILABLE_TEXT_STYLES[u.tone]}`}>{u.label}</dd>
                {u.detail && u.detail !== u.label && (
                  <p className="text-xs text-slate-500 mt-0.5 break-words [overflow-wrap:anywhere]">
                    {u.detail}
                  </p>
                )}
              </div>
            );
          }
          // #745 D7-3: lot dimensions rendered readably, not "8 fields".
          if (key === 'lot_dimensions' && df.value && typeof df.value === 'object' && !Array.isArray(df.value)) {
            const ld = df.value as Record<string, unknown>;
            const bits: string[] = [];
            if (typeof ld.frontage_m === 'number') bits.push(`${(ld.frontage_m as number).toFixed(1)} m frontage`);
            if (typeof ld.depth_m === 'number') bits.push(`${(ld.depth_m as number).toFixed(1)} m depth`);
            if (ld.is_corner === true) bits.push('corner lot');
            if (typeof ld.lot_type === 'string' && ld.lot_type && ld.lot_type !== 'standard') bits.push(formatKey(String(ld.lot_type)).toLowerCase());
            return (
              <div key={key} className="flex flex-col">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">{bits.length > 0 ? bits.join(' · ') : '—'}</dd>
              </div>
            );
          }
          // Heritage dict -> one plain sentence, not a raw object dump.
          if (key === 'heritage_postgis' && df.value && typeof df.value === 'object' && !Array.isArray(df.value)) {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-400">Heritage</dt>
                <dd className="text-sm text-slate-900 mt-0.5">{humanizeHeritage(df.value as Record<string, unknown>)}</dd>
              </div>
            );
          }
          // Shadow is a nested overshadowing result — render a readable summary,
          // not "6 fields".
          if (key === 'shadow' && df.value && typeof df.value === 'object' && !Array.isArray(df.value)) {
            return (
              <div key={key} className="flex flex-col col-span-full">
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
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="mt-0.5"><HeritageList items={df.value as string[]} /></dd>
              </div>
            );
          }
          // Determined DA outcomes — rows with recorded results, radius and
          // data window stated from the payload itself (never years_back arithmetic).
          if (key === 'da_outcomes' && df.value && typeof df.value === 'object') {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="mt-0.5"><DAOutcomesDisplay data={df.value as DAOutcomesPayload} formatLabel={formatKey} /></dd>
              </div>
            );
          }
          // LGA determination counts — counts and rate with the data-derived
          // window, nothing else.
          if (key === 'da_refusal_stats' && df.value && typeof df.value === 'object') {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  <RefusalStatsSentence stats={df.value as RefusalStatsRow} formatLabel={formatKey} />
                </dd>
              </div>
            );
          }
          // Bushfire cross-overlays — a list of {type,...} dicts; name the layers
          // rather than dumping objects.
          if (key === 'cross_overlays' && Array.isArray(df.value) && df.value.length > 0) {
            const names = (df.value as Array<{ type?: string }>)
              .flatMap((o) => (o?.type ? [formatKey(String(o.type))] : []));
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  Also intersects: {names.join(', ')}
                </dd>
              </div>
            );
          }
          // Nearby DAs — application rows with cost of development, not "5 items".
          if (key === 'nearby_das' && Array.isArray(df.value)) {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="mt-0.5"><NearbyDAList rows={df.value as NearbyDARow[]} /></dd>
              </div>
            );
          }
          // Valuation history — a year/value series, rendered as a trend with
          // per-year change, not "5 items".
          if (key === 'val_history' && Array.isArray(df.value)) {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="mt-0.5"><ValuationTrend history={df.value as ValuationYear[]} /></dd>
              </div>
            );
          }
          // LEP Land Use Table lists — collapsible so 600+ uses don't swamp the card.
          if ((key === 'permitted_uses' || key === 'prohibited_uses') && Array.isArray(df.value)) {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="mt-0.5">
                  <UseList kind={key === 'permitted_uses' ? 'permitted' : 'prohibited'} uses={df.value as string[]} />
                </dd>
              </div>
            );
          }
          // Planning overlays are a list of {layer_type, value} — render them as
          // a readable list with units, not "2 items".
          if (key === 'overlays' && Array.isArray(df.value)) {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{formatKey(key)}</dt>
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
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  {within
                    ? 'Within the Coastal Management SEPP land-application area (jurisdictional — not a coastal-hazard finding).'
                    : 'Not in a coastal management area.'}
                </dd>
              </div>
            );
          }
          // A "No" row with a measured distance to the nearest mapped feature —
          // "No — nearest mapped flood polygon 830 m away" says far more than a
          // bare "No". Distance shown only when PostGIS measured one.
          if (
            section === 'environmental_constraints' && key in NEAREST_FEATURE_ROWS &&
            df.value === false
          ) {
            const { layer, label } = NEAREST_FEATURE_ROWS[key];
            const dist = nearestRaw?.[layer];
            return (
              <div key={key} className="flex flex-col">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  No{typeof dist === 'number' ? (
                    <span className="text-slate-500"> — nearest {label} {formatDistance(dist)} away</span>
                  ) : null}
                </dd>
              </div>
            );
          }
          // Contaminated-land detail — the notified sites behind the "Yes",
          // straight from the EPA register (name, class, measured distance).
          if (key === 'contaminated_detail' && df.value && typeof df.value === 'object') {
            const d = df.value as { site_count?: number; nearest_site?: { name?: string; street?: string; suburb?: string; management_class?: string; distance_m?: number } };
            const site = d.nearest_site ?? {};
            const bits = [site.name, [site.street, site.suburb].filter(Boolean).join(' ')].filter(Boolean).join(', ');
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  {d.site_count ?? 1} notified site{(d.site_count ?? 1) === 1 ? '' : 's'} on the EPA register within 500 m
                  {bits ? <> — nearest: {bits}</> : null}
                  {site.management_class ? <span className="text-slate-500"> ({site.management_class})</span> : null}
                  {typeof site.distance_m === 'number' ? <span className="text-slate-500">, {formatDistance(site.distance_m)} away</span> : null}
                </dd>
              </div>
            );
          }
          // An LEP principal development standard the Portal genuinely returns
          // no layer for is "not mapped in this LEP for this lot" — a checked
          // answer, worded distinctly from a fetch failure ("not available").
          if (
            section === 'planning_controls' && UNMAPPED_LEP_CONTROLS.has(key) &&
            df.value == null && df.confidence === 'authoritative'
          ) {
            return (
              <div key={key} className="flex flex-col">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-500 mt-0.5">
                  No {UNMAPPED_LEP_CONTROLS.get(key)} mapped in this LEP for this lot.
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

        // ── Satellite pass-through rows (parity PR-B). FloodDetail/BushfireDetail
        // emit plain values (no DataField wrapper). Composite rows below fold
        // their companion fields (SATELLITE_FOLDED_KEYS) so nothing renders twice;
        // nulls are hidden by HIDE_WHEN_NULL_KEYS (three-state: None = not
        // checked, never a fabricated reading).
        if (section === 'satellite.flood') {
          if (SATELLITE_FOLDED_KEYS.has(key)) return null;
          if (key === 'flood_signal' && typeof val === 'string') {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <dd className="text-sm font-medium text-slate-900">{floodSignalLine(val)}</dd>
              </div>
            );
          }
          if (key === 'ems_flood_detected' && typeof val === 'boolean') {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  {emsLine(val, data.ems_activations as EmsActivation[] | null)}
                </dd>
              </div>
            );
          }
          if (key === 'sar_flood_detected' && typeof val === 'boolean') {
            const sarConf = data.sar_confidence;
            const sarDate = data.sar_analysis_date;
            const extras = [
              typeof sarConf === 'string' && sarConf ? `confidence ${sarConf}` : null,
              typeof sarDate === 'string' && sarDate ? `analysed ${sarDate}` : null,
            ].filter(Boolean).join(', ');
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  {val
                    ? 'Surface-water signal detected on the analysed radar passes'
                    : 'No surface-water signal on the analysed radar passes'}
                  {extras ? <span className="text-slate-500"> ({extras})</span> : null}
                </dd>
              </div>
            );
          }
          if (key === 'ses_in_flood_planning_area' && typeof val === 'boolean') {
            const sesClass = data.ses_flood_class;
            const sesStudy = data.ses_study_name;
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  {val ? (
                    <>
                      Yes — within a mapped flood-study extent
                      {typeof sesClass === 'string' && sesClass ? ` (${formatValue(sesClass)})` : ''}
                      {typeof sesStudy === 'string' && sesStudy ? (
                        <span className="text-slate-500"> — study: {formatValue(sesStudy)}</span>
                      ) : null}
                    </>
                  ) : (
                    'No — not within a council flood-study extent held in our dataset'
                  )}
                </dd>
              </div>
            );
          }
          if (key === 'bom_gauge_distance_km' && typeof val === 'number') {
            const gauge = data.bom_gauge_name;
            return (
              <div key={key} className="flex flex-col">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  {formatValue(val)} km
                  {typeof gauge === 'string' && gauge ? <span className="text-slate-500"> — {gauge}</span> : null}
                </dd>
              </div>
            );
          }
          if (key === 'bom_last_major_flood_date' && typeof val === 'string') {
            const peak = data.bom_last_major_flood_peak_m;
            return (
              <div key={key} className="flex flex-col">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  {val}
                  {typeof peak === 'number' ? <span className="text-slate-500"> — peak {formatValue(peak)} m</span> : null}
                </dd>
              </div>
            );
          }
          if (key === 'bom_flood_history' && Array.isArray(val)) {
            if (val.length === 0) return null;
            const history = val as Array<{ date?: string; peak_m?: number | null; ari_category?: string | null }>;
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="mt-0.5">
                  <ul className="text-sm text-slate-900 space-y-0.5">
                    {history.map((h, i) => (
                      <li key={i}>
                        {h.date ?? '—'}
                        {h.peak_m != null ? <span className="text-slate-500"> — peak {formatValue(h.peak_m)} m</span> : null}
                        {h.ari_category ? <span className="text-slate-500"> ({formatValue(h.ari_category)})</span> : null}
                      </li>
                    ))}
                  </ul>
                </dd>
              </div>
            );
          }
          if (key === 'in_100yr_flood_zone') {
            // Array.isArray + every-string, not a bare truthy/.length check:
            // `data` is an untyped JSON bag, so a contract regression or
            // malformed cached row could hand this a non-array or an array
            // of non-strings — either would otherwise reach
            // floodZoneUnavailableMessage's array methods or render a bogus
            // name (e.g. "[object Object]"). Mirrors the same guard on the
            // standalone flood tool (FloodTool.tsx).
            const rawUnconsulted = data.in_100yr_flood_zone_unconsulted;
            const unconsulted =
              Array.isArray(rawUnconsulted) &&
              rawUnconsulted.length > 0 &&
              rawUnconsulted.every((name): name is string => typeof name === 'string')
                ? rawUnconsulted
                : null;
            if (val === true) {
              // A positive finding stands on its own regardless of what else
              // was unreachable — matches the backend's own three-state rule
              // (only a NEGATIVE needs every source to have been asked).
              return (
                <div key={key} className="flex flex-col col-span-full">
                  <FieldLabel fieldKey={key} />
                  <dd className="text-sm text-slate-900 mt-0.5">
                    Yes — at least one source we checked places this location inside the 1% AEP flood extent
                  </dd>
                </div>
              );
            }
            if (val === false && !unconsulted) {
              return (
                <div key={key} className="flex flex-col col-span-full">
                  <FieldLabel fieldKey={key} />
                  <dd className="text-sm text-slate-900 mt-0.5">
                    No — none of the sources we checked place this location inside the 1% AEP flood extent
                  </dd>
                </div>
              );
            }
            // Either the verdict was never established (null), or the
            // backend sent an internally contradictory payload — a False
            // verdict alongside a named unconsulted study, which should
            // never happen given the backend's own rule (in_100yr_flood_zone
            // is only False when unconsulted is empty) but is treated as
            // "not assessed" here rather than trusted, so a future backend
            // regression degrades safely instead of rendering a
            // false-confidence clearance. Also: val === null with no named
            // study for this address's council has nothing worth telling the
            // reader beyond what the EPI/SES rows above already say.
            if (unconsulted) {
              return (
                <div key={key} className="flex flex-col col-span-full">
                  <FieldLabel fieldKey={key} />
                  <dd className="text-sm text-slate-900 mt-0.5">Not assessed</dd>
                  <dd className="text-xs text-slate-500 mt-1 leading-relaxed">
                    {floodZoneUnavailableMessage(unconsulted)}
                  </dd>
                </div>
              );
            }
            return null;
          }
          if (key === 's1_gap_warning' && typeof val === 'string') {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-[11px] text-slate-400 leading-snug mt-0.5">{val}</dd>
              </div>
            );
          }
          if (key === 'flood_studies') {
            // Named local flood study modelling (Hawkesbury, Redbank, Tweed,
            // Wollongong) — a real depth/level number specific to this
            // address. Previously fell through to the generic array
            // formatter, which rendered a bare "N items" with no figure.
            // Every read guards its own shape: this is an untyped JSON bag,
            // not runtime-validated against FloodDetail.
            if (!Array.isArray(val) || val.length === 0) return null;
            const rows = val.flatMap((raw) => {
              if (!raw || typeof raw !== 'object') return [];
              const study = raw as Record<string, unknown>;
              const studyKey = typeof study.study_key === 'string' && study.study_key ? study.study_key : null;
              // Fall back to a humanised study_key when study_name is
              // missing so a real, usable figure is never silently dropped
              // just because one string field on the entry didn't validate.
              const displayName = typeof study.study_name === 'string' && study.study_name
                ? study.study_name
                : studyKey
                  ? `${studyKey.charAt(0).toUpperCase()}${studyKey.slice(1)} flood study`
                  : null;
              const design = study.design && typeof study.design === 'object'
                ? (study.design as Record<string, unknown>)
                : null;
              const onePctRaw = design ? design['1pct'] : null;
              const onePct = onePctRaw && typeof onePctRaw === 'object'
                ? (onePctRaw as { depth_m?: unknown; level_m_ahd?: unknown })
                : null;
              if (!displayName || !onePct) return [];
              const depth = typeof onePct.depth_m === 'number' ? onePct.depth_m : null;
              const level = typeof onePct.level_m_ahd === 'number' ? onePct.level_m_ahd : null;
              if (depth == null && level == null) return [];
              const figure = depth != null
                ? `${depth.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}m deep`
                : `${(level as number).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}m AHD`;
              return [{ displayName, figure, depthBased: depth != null }];
            });
            if (rows.length === 0) return null;
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dl className="mt-0.5 space-y-1">
                  {rows.map((r) => (
                    <div key={r.displayName}>
                      <dd className="text-sm font-medium text-slate-900">{r.displayName}: {r.figure}</dd>
                      <dd className="text-xs text-slate-500">
                        {/* Source-neutral vs the EPI overlay: naming this "more
                            detailed than the standard overlay used elsewhere in
                            NSW" would be an unqualified statewide comparison
                            this component can't establish. */}
                        Modelled water {r.depthBased ? 'depth' : 'level'} at this location from {r.displayName}; the EPI overlay separately maps planning categories.
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            );
          }
        }
        if (section === 'satellite.bushfire') {
          if (SATELLITE_FOLDED_KEYS.has(key)) return null;
          if (key === 'bal_formal_assessment_cost_range' && typeof val === 'string') {
            const dir = data.bal_assessor_directory_url;
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">
                  {val} <span className="text-slate-500">— typical range for a formal BAL assessment, not a quote.</span>
                  {typeof dir === 'string' && /^https?:\/\//i.test(dir) ? (
                    <>
                      {' '}
                      <a href={dir} target="_blank" rel="noopener noreferrer"
                         className="text-teal-600 hover:text-teal-800 underline font-medium">
                        Find a BAL assessor (NSW RFS directory) ↗
                      </a>
                    </>
                  ) : null}
                </dd>
              </div>
            );
          }
          if (key === 'rfs_referral_note' && typeof val === 'string') {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">{val}</dd>
              </div>
            );
          }
          if (key === 'clearing_10_50_exceptions' && typeof val === 'string') {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">{val}</dd>
              </div>
            );
          }
          if ((key === 'estimated_consultant_costs' || key === 'state_legislation') && typeof val === 'string') {
            return (
              <div key={key} className="flex flex-col col-span-full">
                <FieldLabel fieldKey={key} />
                <dd className="text-sm text-slate-900 mt-0.5">{val}</dd>
              </div>
            );
          }
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
  // Battleaxe (flag) lot: the handle/head breakdown IS the measurement — say so
  // instead of the irregular-shape apology (the eligibility figures next to this
  // field use the head width, so the two must agree).
  if (obj.lot_type === 'battleaxe' && typeof obj.battleaxe_main_lot_width_m === 'number') {
    const handle = typeof obj.battleaxe_access_way_width_m === 'number'
      ? `${obj.battleaxe_access_way_width_m} m access handle, ` : '';
    const headArea = typeof obj.battleaxe_main_lot_area_m2 === 'number'
      ? ` (~${Math.round(obj.battleaxe_main_lot_area_m2)} m² main lot)` : '';
    return `Battleaxe (flag) lot — ${handle}${obj.battleaxe_main_lot_width_m} m wide main lot${headArea}`;
  }
  // Irregular polygon (fills <60% of its bounding box): frontage/depth are null
  // BY MEASUREMENT, not by failure — "Frontage: —, Depth: —" reads as broken.
  if (obj.irregular === true && obj.frontage_m == null && obj.depth_m == null) {
    return 'Irregular lot shape — frontage and depth can’t be measured from the cadastral polygon';
  }
  return Object.fromEntries(Object.entries(obj).filter(([k]) => k !== 'area_m2' && k !== 'lot_area_m2' && k !== 'irregular'));
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
  servicing: 'Water & Sewer Servicing',
  // Flood pass-through rows (PR-B) — plain-English labels for composite rows.
  ems_flood_detected: 'Copernicus emergency mapping',
  sar_flood_detected: 'Radar flood detection (Sentinel-1)',
  ses_in_flood_planning_area: 'Council flood study extent',
  bom_gauge_distance_km: 'Nearest BoM river gauge',
  bom_last_major_flood_date: 'Last major flood at the gauge',
  bom_flood_history: 'Major floods recorded at the gauge',
  in_100yr_flood_zone: '1% AEP (1-in-100-year) mapping',
  ground_elevation_m_ahd: 'Ground elevation (m AHD)',
  s1_gap_warning: 'Radar coverage note',
  jrc_data_year: 'JRC dataset year',
  // Bushfire pass-through rows (PR-B).
  bal_formal_assessment_cost_range: 'Formal BAL assessment cost',
  rfs_referral_note: 'RFS referral',
  clearing_10_50_exceptions: '10/50 vegetation clearing',
  estimated_consultant_costs: 'Consultant costs (guidance)',
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
  val_history:
    'The lot’s land value over the last five valuing years (NSW Valuer General). Land only — it excludes buildings.',
  land_value: 'The NSW Valuer General’s most recent land value for this lot. Land only — it excludes buildings.',
  permitted_uses:
    'Development types the LEP Land Use Table lists as permitted in this zone for this council.',
  prohibited_uses:
    'Development types the LEP Land Use Table lists as prohibited in this zone for this council.',
  anef_level:
    'Aircraft-noise exposure contour value (ANEF) published for this location.',
  contaminated_detail:
    'Sites on the EPA contaminated-land register within 500 m, with the nearest site’s details and measured distance.',
  mine_subsidence_district:
    'The proclaimed mine subsidence district this lot falls within.',
  servicing:
    'Sydney Water Growth Servicing Plan status for this lot (water & sewer). Guide only — trunk capacity is not service-readiness; confirm with Sydney Water.',
  lot_total: 'Number of lots in the strata scheme (NSW Strata Hub).',
  dwelling_type: 'Building form classified from the strata scheme’s lot count (NSW Strata Hub).',
  registration_date: 'Date the strata plan was registered (NSW Strata Hub).',
  bal_estimate: 'Indicative Bushfire Attack Level band from the RFS mapping category — a formal BAL assessment is a separate report.',
  rfs_referral_required: 'Whether a development application here triggers a referral to the NSW Rural Fire Service.',
  rfs_referral_triggers: 'Which conditions trigger the RFS referral.',
  cdc_pathway_available: 'Whether the complying-development (CDC) pathway remains open under the bushfire provisions.',
  cross_overlays: 'Other mapped constraint layers that intersect this lot alongside the bushfire mapping.',
  cost: 'Estimated cost of development stated on the application.',
  nearby_das_cost: 'Estimated cost of development stated on the application.',
  da_outcomes:
    'Applications near this lot that reached a determination, with their recorded results (NSW planning application tracking).',
  da_refusal_stats:
    'Counts of determined applications across the council area and the share refused, for the data window stated in the sentence.',
  // Flood pass-through rows (PR-B).
  ems_flood_detected:
    'Whether a Copernicus Emergency Management Service flood-extent map intersected this location during a recorded activation.',
  sar_flood_detected:
    'Sentinel-1 radar change detection against a dry-season baseline at this location.',
  ses_in_flood_planning_area:
    'Whether the lot falls within a council or SES flood-study extent held in our dataset.',
  in_100yr_flood_zone:
    'Whether any source we checked (EPI layer, council study, flood-study raster) places this location within a 1% annual exceedance probability extent.',
  ground_elevation_m_ahd:
    'Ground elevation from the NSW 5 m elevation model, in metres above the Australian Height Datum.',
  jrc_data_year:
    'Version year of the JRC surface-water dataset behind the occurrence figure.',
  // Bushfire pass-through rows (PR-B).
  bal_formal_assessment_cost_range:
    'Guidance figure — a typical range for engaging a practitioner, not a quote.',
  estimated_consultant_costs:
    'Guidance ranges for bushfire consultants where the pathway calls for them — not quotes.',
  bal_assessment_likely_required:
    'Whether the RFS mapping category typically triggers a formal BAL assessment at application stage.',
  data_currency: 'Date the RFS mapping was queried for this brief.',
};

// Field label + an optional one-line description underneath.
function FieldLabel({ fieldKey }: { fieldKey: string }) {
  const hint = FIELD_HINTS[fieldKey];
  return (
    <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
      {FIELD_LABEL_OVERRIDES[fieldKey] ?? formatKey(fieldKey)}
      {hint && (
        <span className="block text-[10px] font-normal text-slate-400 mt-0.5 leading-snug">{hint}</span>
      )}
    </dt>
  );
}

// Environmental "No" rows that carry a measured nearest-feature distance
// (PostGIS ST_Distance over the mapped polygons — measured, never estimated).
// key = the brief field; layer = the key inside nearest_features; label = the
// factual noun for the sentence ("nearest mapped flood polygon 830 m away").
const NEAREST_FEATURE_ROWS: Record<string, { layer: string; label: string }> = {
  flood_epi: { layer: 'flood', label: 'mapped flood polygon' },
  terrestrial_biodiversity: { layer: 'biodiversity', label: 'mapped biodiversity area' },
  riparian_land: { layer: 'riparian', label: 'mapped riparian land' },
  wetlands: { layer: 'wetlands', label: 'mapped wetland' },
};

function formatDistance(m: number): string {
  return m >= 1000 ? `${(m / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 })} km` : `${Math.round(m)} m`;
}

// Detail fields that only carry information when their host boolean is Yes —
// a null here is covered by the boolean row, so render nothing instead of a
// noise "None" row.
const HIDE_WHEN_NULL_KEYS = new Set([
  'contaminated_detail', 'mine_subsidence_district', 'anef_level',
  // StrataHub supplementary detail — only meaningful on strata lots.
  'lot_total', 'dwelling_type', 'registration_date',
  // Bushfire pathway detail — only meaningful on bushfire-prone lots.
  'rfs_referral_required', 'rfs_referral_triggers', 'cdc_pathway_available', 'cross_overlays',
  // Bushfire pass-through guidance (PR-B) — null = not applicable on this lot
  // or not produced this run; the prone/not-prone rows already answer.
  'designation_source', 'bal_assessment_likely_required', 'bal_formal_assessment_cost_range',
  'bal_assessor_directory_url', 'rfs_referral_note', 'clearing_10_50_entitled',
  'clearing_10_50_exceptions', 'estimated_consultant_costs', 'state_legislation',
  'legislation_url', 'data_currency',
  // Flood pass-through (PR-B) — three-state: null = that source was not
  // checked/available this run (never a fabricated clear reading).
  'flood_signal', 'ems_flood_detected', 'ems_activations', 'sar_flood_detected',
  'sar_confidence', 'sar_analysis_date', 'ses_in_flood_planning_area',
  'ses_flood_class', 'ses_study_name', 'bom_gauge_name', 'bom_last_major_flood_date',
  'bom_last_major_flood_peak_m', 'bom_flood_history',
  // in_100yr_flood_zone is NOT here (unlike its siblings above): a null value
  // can carry a named unconsulted study (Hawkesbury/Redbank/Tweed/Wollongong)
  // worth telling the reader about, so its own render branch below decides
  // whether to show something, rather than being filtered out before it runs.
  'ground_elevation_m_ahd', 's1_gap_warning', 'jrc_data_year',
  // LGA determination stats — null means the layer holds none for this council.
  'da_refusal_stats',
  // Sydney Water servicing — null = lookup failed/unavailable this run; the
  // summary row only shows when there's a real answer (found or not-in-precinct).
  'servicing',
]);

// Satellite fields folded into a neighbouring composite row (rendered inside
// that row's sentence) — never rendered as their own grid cell.
const SATELLITE_FOLDED_KEYS = new Set([
  // flood
  'ems_activations', 'ses_flood_class', 'ses_study_name', 'bom_gauge_name',
  'sar_confidence', 'sar_analysis_date', 'bom_last_major_flood_peak_m',
  // consumed by the in_100yr_flood_zone row above, not a row of its own
  'in_100yr_flood_zone_unconsulted',
  // bushfire
  'bal_assessor_directory_url',
]);

// LEP principal development standards that legitimately have no mapped layer on
// some lots (e.g. Wingecarribee maps no FSR for parts of Bowral). A checked
// null here means "no control mapped", NOT a retrieval failure.
const UNMAPPED_LEP_CONTROLS = new Map<string, string>([
  ['height', 'height of buildings control'],
  ['fsr', 'floor space ratio control'],
  ['lot_size', 'minimum lot size control'],
]);

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

// Shadow display (summary + full scenario table) lives in
// components/reports/ShadowDetailDisplay so the table is render-testable;
// imported at the top of this file.

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

// ---------------------------------------------------------------------------
// Nearby DAs — application rows (type, status, distance, stated cost), not a
// bare "5 items". Cost is the applicant's stated cost of development.
// ---------------------------------------------------------------------------

interface NearbyDARow {
  number?: string; address?: string | null; distance_m?: number | null;
  status?: string | null; dev_type?: string | null; lodgement_date?: string | null;
  cost?: number | null;
}

const NEARBY_DA_PREVIEW_COUNT = 6;

function nearbyDARow(d: NearbyDARow, i: number) {
  return (
    <tr key={d.number ?? i} className="border-t border-slate-100 align-top">
      <td className="py-1 pr-3 text-slate-700">
        {d.dev_type ? formatKey(String(d.dev_type)) : (d.number ?? '—')}
        {d.address ? <span className="block text-[11px] text-slate-400">{d.address}</span> : null}
      </td>
      <td className="py-1 pr-3 text-slate-500">{d.status ?? '—'}</td>
      <td className="py-1 pr-3 tabular-nums text-slate-500">{d.distance_m != null ? `${Math.round(d.distance_m)} m` : '—'}</td>
      <td className="py-1 pr-3 tabular-nums text-slate-700">{d.cost != null ? `$${Math.round(d.cost).toLocaleString()}` : '—'}</td>
      <td className="py-1 tabular-nums text-slate-500">{d.lodgement_date ?? '—'}</td>
    </tr>
  );
}

function NearbyDAList({ rows }: { rows: NearbyDARow[] }) {
  if (!rows || rows.length === 0) {
    return <span className="text-sm text-slate-500">No development applications within 500 m in the last 12 months.</span>;
  }
  const sorted = [...rows].sort((a, b) => String(b.lodgement_date ?? '').localeCompare(String(a.lodgement_date ?? '')));
  const preview = sorted.slice(0, NEARBY_DA_PREVIEW_COUNT);
  const rest = sorted.slice(NEARBY_DA_PREVIEW_COUNT);
  return (
    <div>
      <table className="w-full text-[13px]">
        <thead>
          <tr className="text-xs text-slate-500 text-left">
            <th className="font-medium pb-1 pr-3">Application</th>
            <th className="font-medium pb-1 pr-3">Status</th>
            <th className="font-medium pb-1 pr-3">Distance</th>
            <th className="font-medium pb-1 pr-3">Stated cost</th>
            <th className="font-medium pb-1">Lodged</th>
          </tr>
        </thead>
        <tbody>{preview.map(nearbyDARow)}</tbody>
      </table>
      {rest.length > 0 && (
        <details className="mt-1">
          <summary className="cursor-pointer select-none text-xs text-slate-500">Show {rest.length} more applications</summary>
          <table className="w-full text-[13px] mt-1"><tbody>{rest.map(nearbyDARow)}</tbody></table>
        </details>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Valuation history — render the 5-year series as a readable trend (year,
// value, change on the prior year), not "5 items". Factual figures only.
// ---------------------------------------------------------------------------

interface ValuationYear { year?: string | number; value?: number | null; }

function ValuationTrend({ history }: { history: ValuationYear[] }) {
  const rows = (history || [])
    .filter((h) => h && h.value != null)
    .sort((a, b) => String(a.year).localeCompare(String(b.year)));
  if (rows.length === 0) {
    return <span className="text-sm text-slate-400">No valuation history recorded.</span>;
  }
  return (
    <ul className="text-sm text-slate-900 space-y-0.5 tabular-nums">
      {rows.map((h, i) => {
        const prev = i > 0 ? rows[i - 1].value : null;
        const pct = prev && h.value ? ((h.value - prev) / prev) * 100 : null;
        return (
          <li key={String(h.year)} className="flex items-baseline gap-2">
            <span className="text-slate-500 w-12 shrink-0">{h.year}</span>
            <span>${h.value!.toLocaleString()}</span>
            {pct != null && Math.abs(pct) >= 0.05 && (
              <span className={`text-[11px] ${pct > 0 ? 'text-slate-500' : 'text-amber-700'}`}>
                {pct > 0 ? '+' : ''}{pct.toFixed(1)}% on prior year
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// LEP land-use lists — collapsible, so 600+ uses don't swamp the card. The
// counts are always visible; the full lists expand on demand.
// ---------------------------------------------------------------------------

function UseList({ kind, uses }: { kind: 'permitted' | 'prohibited'; uses: string[] }) {
  const label = kind === 'permitted' ? 'Permitted in the zone' : 'Prohibited in the zone';
  if (!uses || uses.length === 0) {
    return (
      <span className="text-sm text-slate-500">
        No {kind} uses listed for this zone in the LEP Land Use Table extract.
      </span>
    );
  }
  return (
    <details className="text-sm">
      <summary className="cursor-pointer select-none text-slate-900">
        <span className="font-medium">{uses.length}</span> {kind} land uses
        <span className="text-slate-400 text-xs ml-1.5">(click to expand the LEP Land Use Table list)</span>
      </summary>
      <ul className="mt-2 columns-1 sm:columns-2 gap-x-6 text-slate-700 text-[13px] leading-relaxed" aria-label={label}>
        {uses.map((u) => (
          <li key={u} className="break-inside-avoid">{formatKey(u)}</li>
        ))}
      </ul>
    </details>
  );
}

// ---------------------------------------------------------------------------
// Market context — VG comparables + recent sales. Wording contract: the
// percentile/band lines state the lot's factual position within the comparable
// set — never an over/under-valuation opinion or advice.
// ---------------------------------------------------------------------------

interface ComparableRow { propid?: number; address?: string; zone?: string; area_m2?: number; land_value?: number | null; valuation_date?: string | null; }
interface ComparablesData {
  subject_value?: number | null; subject_area_m2?: number; comparable_count?: number;
  median_value?: number | null; mean_value?: number | null; percentile_rank?: number | null;
  comparables?: ComparableRow[]; assessment_signal?: string | null;
}
interface SaleRow { propid?: number; address?: string; price?: number; area_m2?: number; sale_date?: string | null; price_per_m2?: number | null; is_strata?: boolean; }
interface MarketContextData {
  comparables?: { value?: ComparablesData | null; confidence?: string; reason?: string | null; as_at?: string | null };
  recent_sales?: { value?: SaleRow[] | null; confidence?: string; reason?: string | null; as_at?: string | null };
  radius_m?: number;
  sales_years_back?: number;
}

// assessment_signal -> a factual position within the comparable set.
const SIGNAL_POSITION: Record<string, string> = {
  potentially_over: 'in the upper band of',
  in_range: 'within the middle band of',
  potentially_under: 'in the lower band of',
};

function MarketContextCard({ data, satelliteRan }: { data: Record<string, unknown>; satelliteRan: boolean }) {
  const df = data as { value?: MarketContextData | null; confidence?: string; reason?: string | null; source?: string; as_at?: string | null };
  const mc = df.value ?? null;
  const radius = mc?.radius_m ?? 500;
  const yearsBack = mc?.sales_years_back ?? 3;

  const header = (
    <div className="px-5 py-4 border-b border-slate-200/70 bg-gradient-to-r from-slate-50/90 via-white to-white flex items-center justify-between gap-3">
      <div>
        <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-slate-900 [text-wrap:balance]">Market Context</h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Comparable land valuations and recent sales within {radius} m (NSW Valuer General{df.as_at ? `, as at ${df.as_at}` : ''})
        </p>
      </div>
      {df.confidence === 'not_available'
        ? <span className={`px-2 py-0.5 text-xs font-medium rounded ${UNAVAILABLE_TONE_STYLES.error}`}>Unavailable</span>
        : confidenceBadge(df.confidence ?? 'derived')}
    </div>
  );

  if (!mc) {
    const u = describeUnavailable(df.reason, 'market_context', satelliteRan, sectionDesc('market_context'));
    return (
      <div className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
        {header}
        <div className={`px-5 py-4 text-sm ${UNAVAILABLE_TEXT_STYLES[u.tone]}`}>{u.detail}</div>
      </div>
    );
  }

  const comps = mc.comparables?.value ?? null;
  const compsReason = mc.comparables?.reason;
  const sales = mc.recent_sales?.value ?? null;
  const salesReason = mc.recent_sales?.reason;
  const position = comps?.assessment_signal ? SIGNAL_POSITION[comps.assessment_signal] : null;

  return (
    <div className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
      {header}
      <div className="px-5 py-4 space-y-4">
        {/* Comparable valuations */}
        <div>
          <h4 className="text-xs font-medium text-slate-500 mb-1.5">Comparable land valuations
            <span className="block text-[10px] font-normal text-slate-400 mt-0.5 leading-snug">
              Lots in the same zone with a similar lot size within {radius} m. Land value only — it excludes buildings.
            </span>
          </h4>
          {comps ? (
            <div className="text-sm text-slate-900 space-y-1">
              <div className="flex flex-wrap gap-x-6 gap-y-1 tabular-nums">
                <span><span className="text-slate-500">Comparables:</span> {comps.comparable_count ?? 0}</span>
                {comps.median_value != null && <span><span className="text-slate-500">Median:</span> ${comps.median_value.toLocaleString()}</span>}
                {comps.mean_value != null && <span><span className="text-slate-500">Mean:</span> ${comps.mean_value.toLocaleString()}</span>}
                {comps.subject_value != null && <span><span className="text-slate-500">This lot:</span> ${comps.subject_value.toLocaleString()}</span>}
              </div>
              {comps.percentile_rank != null && (
                <p className="text-slate-700">
                  This lot&apos;s land value sits at the {ordinal(Math.round(comps.percentile_rank))} percentile of{' '}
                  {comps.comparable_count} comparable valuations{position ? ` — ${position} the comparable set` : ''}.
                </p>
              )}
              {(comps.comparables?.length ?? 0) > 0 && (
                <details className="mt-1">
                  <summary className="cursor-pointer select-none text-xs text-slate-500">
                    Show the {comps.comparables!.length} comparable lots
                  </summary>
                  <table className="w-full text-[13px] mt-2">
                    <thead>
                      <tr className="text-xs text-slate-500 text-left">
                        <th className="font-medium pb-1 pr-3">Address</th>
                        <th className="font-medium pb-1 pr-3">Lot</th>
                        <th className="font-medium pb-1">Land value</th>
                      </tr>
                    </thead>
                    <tbody className="tabular-nums">
                      {comps.comparables!.map((c, i) => (
                        <tr key={c.propid ?? `${c.address}-${i}`} className="border-t border-slate-100">
                          <td className="py-1 pr-3 text-slate-700">{c.address ?? '—'}</td>
                          <td className="py-1 pr-3 text-slate-500">{c.area_m2 != null ? `${Math.round(c.area_m2)} m²` : '—'}</td>
                          <td className="py-1 text-slate-700">{c.land_value != null ? `$${c.land_value.toLocaleString()}` : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </details>
              )}
            </div>
          ) : /resolved/i.test(compsReason ?? '') ? (
            <p className="text-sm text-slate-500">
              Comparable matching needs the lot&apos;s zone and area, which didn&apos;t resolve for this address.
            </p>
          ) : (
            <p className="text-sm text-amber-700">
              Couldn&apos;t retrieve comparable valuations — run the brief again to retry.
            </p>
          )}
        </div>

        {/* Recent sales */}
        <div>
          <h4 className="text-xs font-medium text-slate-500 mb-1.5">Recent sales
            <span className="block text-[10px] font-normal text-slate-400 mt-0.5 leading-snug">
              Sales recorded by the NSW Valuer General within {radius} m in the last {yearsBack} years. Sale prices include buildings.
            </span>
          </h4>
          {sales ? (
            sales.length === 0 ? (
              <p className="text-sm text-slate-500">No sales recorded within {radius} m in the last {yearsBack} years.</p>
            ) : (
              <SalesTable sales={sales} />
            )
          ) : (
            <p className="text-sm text-amber-700">Couldn&apos;t retrieve recent sales{salesReason ? '' : ''} — run the brief again to retry.</p>
          )}
        </div>
      </div>
    </div>
  );
}

const SALES_PREVIEW_COUNT = 6;

// Module scope: pure row renderer (no component state) — rebuilt-per-render
// closures waste work and break memoized children.
function saleRow(s: SaleRow, i: number) {
  return (
    <tr key={`${s.propid ?? s.address}-${s.sale_date ?? i}`} className="border-t border-slate-100">
      <td className="py-1 pr-3 text-slate-700">{s.address ?? '—'}{s.is_strata ? <span className="text-[10px] text-slate-400 ml-1">strata</span> : null}</td>
      <td className="py-1 pr-3 tabular-nums text-slate-700">{s.price != null ? `$${s.price.toLocaleString()}` : '—'}</td>
      <td className="py-1 pr-3 tabular-nums text-slate-500">{s.price_per_m2 != null ? `$${Math.round(s.price_per_m2).toLocaleString()}/m²` : '—'}</td>
      <td className="py-1 tabular-nums text-slate-500">{s.sale_date ?? '—'}</td>
    </tr>
  );
}

function SalesTable({ sales }: { sales: SaleRow[] }) {
  const sorted = [...sales].sort((a, b) => String(b.sale_date ?? '').localeCompare(String(a.sale_date ?? '')));
  const preview = sorted.slice(0, SALES_PREVIEW_COUNT);
  const rest = sorted.slice(SALES_PREVIEW_COUNT);
  return (
    <div>
      <table className="w-full text-[13px]">
        <thead>
          <tr className="text-xs text-slate-500 text-left">
            <th className="font-medium pb-1 pr-3">Address</th>
            <th className="font-medium pb-1 pr-3">Price</th>
            <th className="font-medium pb-1 pr-3">$/m² of land</th>
            <th className="font-medium pb-1">Date</th>
          </tr>
        </thead>
        <tbody>{preview.map(saleRow)}</tbody>
      </table>
      {rest.length > 0 && (
        <details className="mt-1">
          <summary className="cursor-pointer select-none text-xs text-slate-500">Show {rest.length} more sales</summary>
          <table className="w-full text-[13px] mt-1"><tbody>{rest.map(saleRow)}</tbody></table>
        </details>
      )}
    </div>
  );
}

function ordinal(n: number): string {
  const rem10 = n % 10, rem100 = n % 100;
  if (rem10 === 1 && rem100 !== 11) return `${n}st`;
  if (rem10 === 2 && rem100 !== 12) return `${n}nd`;
  if (rem10 === 3 && rem100 !== 13) return `${n}rd`;
  return `${n}th`;
}

interface ClimateFinding { hazard?: string; value?: number; unit?: string; data_date?: string; confidence?: string; source?: string; }
interface ClimateHazardRow { hazard?: string; present?: boolean; detail?: string; data_source?: string; available?: boolean; }
interface ClimateUnavailable { source?: string; reason?: string; }
interface ClimateManifest {
  sources_queried?: number; sources_successful?: number;
  sources_unavailable?: ClimateUnavailable[]; data_quality_notes?: string[];
}

// Internal source slugs -> what was actually checked, so a gap names the dataset
// rather than vanishing. Keep external-safe: no key/config talk in the label.
const CLIMATE_SOURCE_LABELS: Record<string, string> = {
  nsw_uhgc: 'Urban heat island (NSW urban heat meshblock dataset, 2016)',
  arr_data_hub: 'Design rainfall intensity (Bureau of Meteorology IFD via ARR Data Hub)',
  nasa_firms: 'Fire hotspot detections (NASA FIRMS satellite)',
  narclim_projections: 'Climate projections (NARCliM 2.0, AdaptNSW)',
};

// Turn a raw climate empirical finding into one plain-English line, e.g.
// "Urban heat: +7.3 °C above surrounding areas (2016 data — most recent available)".
function humanizeClimateFinding(f: ClimateFinding): { label: string; detail: string; source?: string } | null {
  if (!f || f.value == null) return null;
  const yr = f.data_date ? f.data_date.slice(0, 4) : '';
  const stale = f.confidence === 'stale';
  if (f.hazard === 'urban_heat_island') {
    return {
      label: 'Urban heat',
      detail: `+${f.value.toFixed(1)} °C above surrounding areas${yr ? ` (${yr} data${stale ? ' — most recent available' : ''})` : ''}`,
      source: f.source,
    };
  }
  if (f.hazard === 'extreme_rainfall') {
    return {
      label: 'Extreme rainfall',
      detail: `${f.value.toFixed(1)} mm in 60 min (1% annual chance)${yr ? ` (${yr})` : ''}`,
      source: f.source,
    };
  }
  // Fallback: humanise the hazard name + value, drop the snake_case unit jargon.
  return {
    label: formatKey(f.hazard ?? 'Hazard'),
    detail: `${f.value}${f.unit ? ` ${f.unit.replace(/_/g, ' ')}` : ''}${yr ? ` (${yr})` : ''}`,
    source: f.source,
  };
}

function ClimateCard({ data }: { data: Record<string, unknown> }) {
  const empirical = (data.empirical_findings as ClimateFinding[] | undefined) ?? [];
  const lines = empirical.flatMap((f) => {
    const line = humanizeClimateFinding(f);
    return line ? [line] : [];
  });
  // The six per-hazard screening rows (flood/bushfire/coastal/landslide/fire
  // history/heat) — previously computed by the backend and silently dropped here.
  const hazards = ((data.per_hazard_detail as ClimateHazardRow[] | undefined) ?? [])
    .filter((h) => h && h.available !== false);
  const manifest = (data.manifest as ClimateManifest | undefined) ?? {};
  const unavailable = manifest.sources_unavailable ?? [];
  const notes = manifest.data_quality_notes ?? [];
  return (
    <div className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
      <div className="px-5 py-4 border-b border-slate-200/70 bg-gradient-to-r from-slate-50/90 via-white to-white flex items-center justify-between gap-3">
        <div>
          <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-slate-900 [text-wrap:balance]">Climate Hazards &amp; Projections</h3>
          <p className="text-xs text-slate-500 mt-0.5">Hazard screening, heat and rainfall calculations, climate-model projections — each with its dataset</p>
        </div>
        <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-600/25">Calculated</span>
      </div>
      <div className="px-5 py-4 space-y-4">
        {lines.length > 0 && (
          <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-3">
            {lines.map((l, i) => (
              <div key={i} className="flex flex-col">
                <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{l.label}</dt>
                <dd className="text-sm text-slate-900 mt-0.5">{l.detail}</dd>
                {l.source && <dd className="text-[11px] text-slate-400 mt-0.5">{l.source}</dd>}
              </div>
            ))}
          </dl>
        )}
        {hazards.length > 0 && (
          <div className={lines.length > 0 ? 'border-t border-slate-100 pt-3' : ''}>
            <h4 className="text-xs font-medium text-slate-500 mb-2">Hazard screening
              <span className="block text-[10px] font-normal text-slate-400 mt-0.5 leading-snug">
                Each hazard checked against its government dataset — a &ldquo;not detected&rdquo; is a checked result, not missing data.
              </span>
            </h4>
            <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-3">
              {hazards.map((h, i) => (
                <div key={h.hazard ?? i} className="flex flex-col">
                  <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{formatKey(h.hazard ?? 'hazard')}</dt>
                  <dd className="text-sm text-slate-900 mt-0.5">
                    {h.detail || (h.present === false ? 'Not detected at this property' : h.present === true ? 'Detected' : '—')}
                  </dd>
                  {h.data_source && <dd className="text-[11px] text-slate-400 mt-0.5">{h.data_source}</dd>}
                </div>
              ))}
            </dl>
          </div>
        )}
        {lines.length === 0 && hazards.length === 0 && (
          <div className="text-sm text-slate-400">No climate hazard indicators could be calculated for this property on this run.</div>
        )}
        <ProjectedFindings rows={(data.projected_findings as ProjectedRow[] | undefined) ?? []} />
        {unavailable.length > 0 && (
          <div className="border-t border-slate-100 pt-3">
            <h4 className="text-xs font-medium text-slate-500 mb-1.5">Checked, not available for this location on this run</h4>
            <ul className="space-y-1">
              {unavailable.map((u, i) => (
                <li key={u.source ?? i} className="text-xs text-slate-500" title={u.reason ?? undefined}>
                  {CLIMATE_SOURCE_LABELS[u.source ?? ''] ?? formatKey(u.source ?? 'source')}
                </li>
              ))}
            </ul>
          </div>
        )}
        {notes.length > 0 && (
          <p className="text-[11px] text-slate-400">{notes.join(' · ')}</p>
        )}
      </div>
    </div>
  );
}

// NARCliM 2.0 projections — model outputs, always shown with their model,
// scenario and timeframe. Factual changes only, no advice.
interface ProjectedRow { hazard?: string; value?: number | null; model?: string | null; scenario?: string | null; timeframe?: string | null; }

const PROJECTED_LABELS: Record<string, { label: string; unit: string }> = {
  extreme_heat_days: { label: 'Days ≥35°C per year', unit: 'days' },
  mean_temperature: { label: 'Mean temperature', unit: '°C' },
  daily_precipitation: { label: 'Mean daily rainfall', unit: 'mm/day' },
};

function ProjectedFindings({ rows }: { rows: ProjectedRow[] }) {
  const usable = (rows || []).filter((r) => r && r.value != null && r.hazard);
  if (usable.length === 0) return null;
  const byHazard = new Map<string, ProjectedRow[]>();
  for (const r of usable) {
    const k = String(r.hazard);
    byHazard.set(k, [...(byHazard.get(k) ?? []), r]);
  }
  const model = usable[0].model ?? 'NARCliM 2.0';
  return (
    <div className="mt-3 border-t border-slate-100 pt-3">
      <div className="text-xs font-medium text-slate-500 mb-1.5">
        Projected change ({model})
        <span className="block text-[10px] font-normal text-slate-400 mt-0.5 leading-snug">
          Climate-model projections against the 2015–2024 baseline — modelled scenarios, not observations.
        </span>
      </div>
      <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-1.5 text-sm">
        {[...byHazard.entries()].map(([hazard, hz]) => {
          const meta = PROJECTED_LABELS[hazard] ?? { label: formatKey(hazard), unit: '' };
          const parts = hz
            .sort((a, b) => String(a.timeframe).localeCompare(String(b.timeframe)))
            .map((r) => `${r.value! > 0 ? '+' : ''}${r.value!.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${meta.unit} by ${r.timeframe}`);
          return (
            <div key={hazard} className="flex flex-col">
              <dt className="text-xs text-slate-500">{meta.label}</dt>
              <dd className="text-slate-900 tabular-nums">{parts.join(' · ')}</dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}

// Data-source provenance for the footer lives in ./provenance (pure, unit-
// tested): per-run derivation — a source is listed only when a populated
// DataField cites it — with case-insensitive label dedupe and latest as-at.

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

// ---------------------------------------------------------------------------
// Yield-card ledger context — each arithmetic input with its value and source,
// plus the named-missing-control explanation when the envelope can't compute.
// Composed entirely from data the stream already carries (no new fetches).
// ---------------------------------------------------------------------------

type SectionEvt = { data: { section: string; data: unknown } };

function _sectionValue(sections: SectionEvt[], name: string): Record<string, unknown> | null {
  const s = sections.find((e) => e.data.section === name);
  const d = s?.data.data as Record<string, unknown> | null | undefined;
  if (!d) return null;
  return (isDataField(d) ? (d.value as Record<string, unknown> | null) : d) ?? null;
}

function _df(obj: Record<string, unknown> | null, key: string): { value?: unknown; source?: string; as_at?: string | null; confidence?: string } | null {
  const v = obj?.[key];
  return v && isDataField(v) ? v : null;
}

function buildYieldLedgerContext(
  sections: SectionEvt[],
  ca: ConstraintArithmeticResult,
): { inputProvenance: InputLedgerRow[]; envelopeGap: EnvelopeGap | null } {
  const pc = _sectionValue(sections, 'planning_controls');
  const eco = _sectionValue(sections, 'economics');
  const dcpSection = _sectionValue(sections, 'dcp_controls');

  const src = (df: ReturnType<typeof _df>) => (df?.source ?? '').replace(/_/g, ' ');
  const rows: InputLedgerRow[] = [];

  const lotDf = _df(eco, 'lot_area_m2');
  if (ca.lot_area_m2 > 0) {
    rows.push({
      label: 'Lot area',
      value: `${Math.round(ca.lot_area_m2).toLocaleString()} m²`,
      source: src(lotDf) || 'nsw valuation service',
      asAt: lotDf?.as_at ?? null,
    });
  }
  const fsrDf = _df(pc, 'fsr');
  rows.push({
    label: 'Floor space ratio (LEP)',
    value: ca.lep_fsr != null ? `${ca.lep_fsr}:1` : 'no control mapped',
    source: src(fsrDf) || 'planning portal',
    asAt: fsrDf?.as_at ?? null,
  });
  const heightDf = _df(pc, 'height');
  rows.push({
    label: 'Height of buildings (LEP)',
    value: ca.lep_height_m != null ? `${ca.lep_height_m} m` : 'no control mapped',
    source: src(heightDf) || 'planning portal',
    asAt: heightDf?.as_at ?? null,
  });
  const dims = _df(pc, 'lot_dimensions')?.value as { frontage_m?: number | null; depth_m?: number | null } | null | undefined;
  if (dims?.frontage_m != null && dims?.depth_m != null) {
    rows.push({
      label: 'Lot dimensions',
      value: `${dims.frontage_m} m × ${dims.depth_m} m`,
      source: 'cadastral lot polygon',
    });
  }
  if (ca.dev_type) {
    rows.push({
      label: 'Development form basis',
      value: formatKey(ca.dev_type),
      source: 'zone tier + LEP land use table',
    });
  }
  const setbacks = [
    ca.setback_front_m != null ? `F ${ca.setback_front_m} m` : null,
    ca.setback_side_m != null ? `S ${ca.setback_side_m} m` : null,
    ca.setback_rear_m != null ? `R ${ca.setback_rear_m} m` : null,
  ].filter(Boolean);
  if (setbacks.length > 0) {
    const dcpName = _df(dcpSection, 'dcp_name')?.value as string | null | undefined;
    rows.push({
      label: 'DCP setbacks',
      value: setbacks.join(' · '),
      source: dcpName || 'extracted DCP controls',
      asAt: _df(dcpSection, 'controls')?.as_at ?? null,
    });
  }

  let envelopeGap: EnvelopeGap | null = null;
  if (ca.realistic_gfa_m2 == null) {
    const missing: string[] = [];
    if (ca.lep_fsr == null) missing.push('floor space ratio');
    if (ca.lep_height_m == null) missing.push('height of buildings');
    if (missing.length > 0) {
      const instrument = (_df(pc, 'zone_epi')?.value as string | null | undefined) ?? null;
      const dcpControls = _df(dcpSection, 'controls');
      envelopeGap = {
        missing,
        instrument,
        dcpOnboarded: dcpControls != null && dcpControls.confidence !== 'not_available',
        dcpName: (_df(dcpSection, 'dcp_name')?.value as string | null | undefined) ?? null,
      };
    }
  }
  return { inputProvenance: rows, envelopeGap };
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

// Per-form eligibility from the Housing-SEPP engine (the same run that drives
// the capacity ceiling), with the clause citation each outcome rests on.
interface EligibilityForm {
  development_type?: string; eligible?: boolean; reason?: string;
  // True when eligible=false only because the input to test the standard is
  // missing (lot width/area unmeasured, or the standard absent from the
  // dataset) — render as "Unconfirmed", never as a failed standard.
  unconfirmed?: boolean;
  requires_lmr_area?: boolean; min_lot_size_m2?: number | null; min_lot_width_m?: number | null;
  source_clause?: string | null; source_document?: string | null;
  legislation_url?: string | null; effective_date?: string | null;
}
interface EligibilityField { value?: EligibilityForm[] | null; confidence?: string; reason?: string | null; }

// "4,096 m² ≥ 600 m² min" / "310 m² < 600 m² min" — the lot's actual number
// against the standard's minimum, stated as the comparison it is.
function lotVsMin(actual: number | null | undefined, min: number | null | undefined, unit: string): string | null {
  if (min == null) return null;
  if (actual == null) return `${min.toLocaleString()} ${unit} min`;
  const cmp = actual >= min ? '≥' : '<';
  return `${Math.round(actual).toLocaleString()} ${unit} ${cmp} ${min.toLocaleString()} ${unit} min`;
}

function EligibilityRows({ forms, lotAreaM2, lotWidthM }: {
  forms: EligibilityForm[]; lotAreaM2?: number | null; lotWidthM?: number | null;
}) {
  return (
    <div className="border-t border-slate-100 pt-3 mt-1">
      <h4 className="text-xs font-medium text-slate-500 mb-2">
        Per-form eligibility for this lot
        <span className="block text-[10px] font-normal text-slate-400 mt-0.5 leading-snug">
          Each outcome cites the SEPP clause it rests on; the figures compare this lot&apos;s numbers to the standard&apos;s minimums.
        </span>
      </h4>
      <ul className="space-y-2 text-sm">
        {forms.map((f, i) => {
          const area = lotVsMin(lotAreaM2, f.min_lot_size_m2, 'm²');
          const width = lotVsMin(lotWidthM, f.min_lot_width_m, 'm');
          return (
            <li key={f.development_type ?? i} className="flex flex-col gap-0.5">
              <div className="flex items-baseline gap-2 flex-wrap">
                <span className="text-slate-900">{formatKey(f.development_type ?? '')}</span>
                {f.eligible
                  ? <span className="inline-flex items-center rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-emerald-200">Eligible</span>
                  : f.unconfirmed
                    ? <span className="inline-flex items-center rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 ring-1 ring-amber-200">Unconfirmed</span>
                    : <span className="inline-flex items-center rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500 ring-1 ring-slate-200">Not eligible</span>}
                {(area || width) && (
                  <span className="text-xs text-slate-500 tabular-nums">
                    {[area, width].filter(Boolean).join(' · ')}
                  </span>
                )}
              </div>
              {!f.eligible && f.reason && (
                <span className="text-xs text-slate-500">{f.reason}</span>
              )}
              {f.source_clause && (
                <span className="text-[11px] text-slate-400">
                  {f.legislation_url
                    ? <a href={f.legislation_url} target="_blank" rel="noopener noreferrer" className="text-teal-600 underline">{f.source_clause}</a>
                    : f.source_clause}
                  {f.source_document ? `, ${f.source_document}` : ''}
                  {f.effective_date ? ` (as at ${f.effective_date})` : ''}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SeppHousingCard({ standards, eligibility, lotAreaM2, lotWidthM }: {
  standards: SeppStandard[];
  eligibility?: EligibilityField | null;
  lotAreaM2?: number | null;
  lotWidthM?: number | null;
}) {
  const forms = eligibility?.value ?? null;
  return (
    <div className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
      <div className="px-5 py-4 border-b border-slate-200/70 bg-gradient-to-r from-slate-50/90 via-white to-white flex items-center justify-between gap-3">
        <div>
          <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-slate-900 [text-wrap:balance]">Housing SEPP — Low &amp; Mid-Rise</h3>
          <p className="text-xs text-slate-500 mt-0.5">Denser forms the policy permits, and whether this lot qualifies</p>
        </div>
        <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium bg-emerald-50 text-emerald-800 ring-1 ring-inset ring-emerald-600/20">Authoritative</span>
      </div>
      <div className="px-5 py-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-500 text-left">
              <th className="font-medium pb-2 pr-3">Form</th>
              {/* This column tests ONLY lot area against the form's minimum —
                  the full per-form verdict (width, TOD, LMR, heritage gates)
                  is in the rows below. Labelling it "Eligible" contradicted
                  them on lots that pass area but fail another gate. */}
              <th className="font-medium pb-2 pr-3">Lot area test</th>
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
                  {/* No minimum in the dataset, or no measured lot area →
                      nothing was tested; a green "Passes" here would be false. */}
                  {s.min_lot_area_m2 == null || lotAreaM2 == null
                    ? <span className="text-slate-400" title="No lot-size minimum to test for this form">—</span>
                    : s.eligible
                      ? <span className="text-emerald-700">Passes</span>
                      : <span className="text-slate-400" title={s.reason_ineligible ?? undefined}>Below minimum</span>}
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
        {forms && forms.length > 0 && (
          <EligibilityRows forms={forms} lotAreaM2={lotAreaM2} lotWidthM={lotWidthM} />
        )}
        {eligibility && eligibility.value == null && eligibility.confidence === 'not_available' && (
          <p className="text-xs text-slate-400 mt-3 border-t border-slate-100 pt-3">
            Per-form eligibility couldn&apos;t be assessed on this run — the standards above still apply; run the brief again to retry.
          </p>
        )}
      </div>
    </div>
  );
}

// The "why the SEPP forms don't reach this lot" explainer lives in
// components/reports/SeppContextCard.tsx (zone-family aware copy — a
// conservation or rural lot is never described as shop-top territory).

// Granny Flat — extracted to components/reports/GrannyFlatBriefCard.tsx (#752).
// The card fires the gated async /api/satellite/granny-flat route itself (detect +
// human structure-selection + explicit confirm/calculate — never automatic).

// ---------------------------------------------------------------------------
// Solar — fires the SAME rate-limited route the standalone solar tool uses
// (Google Solar API on Railway), once per satellite run. Figures are imagery-
// derived estimates; every number carries its imagery date.
// ---------------------------------------------------------------------------

interface SolarOutputs {
  max_panels?: number; max_panel_area_m2?: number; annual_kwh_estimate?: number;
  annual_kwh_delivered?: number | null; delivery_basis?: string | null;
  sunshine_hours_per_year?: number; roof_area_m2?: number; is_heritage?: boolean;
  imagery_date?: string; coverage_available?: boolean;
  best_pitch_deg?: number; best_azimuth_deg?: number; is_commercial_scale?: boolean;
}

// Compass bearing (0=N, 90=E, 180=S, 270=W) -> 8-wind direction word.
function compassDirection(deg: number): string {
  const dirs = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'];
  return dirs[Math.round((((deg % 360) + 360) % 360) / 45) % 8];
}
// null = not fetched yet (renders the loading shell while active)
type SolarState =
  | { kind: 'result'; o: SolarOutputs }
  | { kind: 'no_coverage' }
  | { kind: 'error'; message: string };

// Module scope (not nested) so React never remounts it mid-stream.
function SolarShell({ badge, badgeClass, children }: { badge: string; badgeClass: string; children: ReactNode }) {
  return (
    <div className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
      <div className="px-5 py-4 border-b border-slate-200/70 bg-gradient-to-r from-slate-50/90 via-white to-white flex items-center justify-between gap-3">
        <div>
          <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-slate-900 [text-wrap:balance]">Solar Potential</h3>
          <p className="text-xs text-slate-500 mt-0.5">Roof capacity and yield from aerial imagery (Google Solar)</p>
        </div>
        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ring-slate-900/10 ${badgeClass}`}>{badge}</span>
      </div>
      <div className="px-5 py-4 text-sm">{children}</div>
    </div>
  );
}

function SolarBriefCard({ address, active }: { address?: string; active: boolean }) {
  const [state, setState] = useState<SolarState | null>(null);
  useEffect(() => {
    if (!active || !address) return;  // inactive is derived at render, not stored
    let cancelled = false;
    fetch('/api/satellite/solar-yield', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address }),
    })
      .then(async (r) => {
        if (cancelled) return;
        const d = await r.json().catch(() => null);
        if (!r.ok || !d) {
          setState({ kind: 'error', message: d?.error || `Solar analysis did not complete (HTTP ${r.status}) — try again.` });
          return;
        }
        const o = (d.data?.outputs ?? {}) as SolarOutputs;
        if (o.coverage_available === false) { setState({ kind: 'no_coverage' }); return; }
        setState({ kind: 'result', o });
      })
      .catch(() => { if (!cancelled) setState({ kind: 'error', message: 'Solar analysis did not complete — try again.' }); });
    return () => { cancelled = true; };
  }, [address, active]);

  if (!active || !address) return (
    <SolarShell badge="Not run" badgeClass="bg-teal-50 text-teal-700">
      <span className="text-slate-500">Tick “Include satellite analysis” above and re-run to add the solar assessment.</span>
    </SolarShell>
  );
  if (!state) return (
    <SolarShell badge="Analysing…" badgeClass="bg-slate-100 text-slate-500">
      <span className="text-slate-500 animate-pulse">Reading the roof from aerial imagery… (up to ~50s)</span>
    </SolarShell>
  );
  if (state.kind === 'no_coverage') return (
    <SolarShell badge="No imagery here" badgeClass="bg-slate-100 text-slate-500">
      <span className="text-slate-500">Google Solar has no aerial coverage at this address — no solar figures are available from this source.</span>
    </SolarShell>
  );
  if (state.kind === 'error') return (
    <SolarShell badge="Couldn’t complete" badgeClass="bg-amber-50 text-amber-700">
      <span className="text-amber-700">{state.message}</span>
    </SolarShell>
  );
  const o = state.o;
  return (
    <SolarShell badge="Calculated" badgeClass="bg-amber-50 text-amber-800">
      <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-2">
        {o.max_panels != null && (
          <div><dt className="text-xs text-slate-500">Panel capacity</dt><dd className="text-slate-900 tabular-nums">{o.max_panels.toLocaleString()} panels{o.max_panel_area_m2 != null ? ` (~${Math.round(o.max_panel_area_m2)} m²)` : ''}</dd></div>
        )}
        {(o.annual_kwh_estimate != null || o.annual_kwh_delivered != null) && (
          /* Delivered energy leads, because that is what a meter records.
             Google Solar reports DC at the panel; showing that alone read as
             expected output and overstated it by about 16%. Both are shown so
             the basis is visible rather than implied. */
          <div>
            <dt className="text-xs text-slate-500">Calculated yield</dt>
            <dd className="text-slate-900 tabular-nums">
              {(deliveredKwhFrom(o.annual_kwh_estimate, o.annual_kwh_delivered) ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh/year delivered
            </dd>
            <dd className="text-xs text-slate-500 leading-snug mt-0.5">
              {deliveryBasisText(o.annual_kwh_estimate)}
            </dd>
          </div>
        )}
        {o.sunshine_hours_per_year != null && (
          <div><dt className="text-xs text-slate-500">Sunshine</dt><dd className="text-slate-900 tabular-nums">{Math.round(o.sunshine_hours_per_year).toLocaleString()} hours/year</dd></div>
        )}
        {o.roof_area_m2 != null && (
          <div><dt className="text-xs text-slate-500">Roof area (clipped to lot)</dt><dd className="text-slate-900 tabular-nums">{Math.round(o.roof_area_m2).toLocaleString()} m²</dd></div>
        )}
        {o.best_pitch_deg != null && o.best_azimuth_deg != null && (
          <div>
            <dt className="text-xs text-slate-500">Best roof segment</dt>
            <dd className="text-slate-900 tabular-nums">
              pitch {o.best_pitch_deg}°, facing {compassDirection(o.best_azimuth_deg)} ({Math.round(o.best_azimuth_deg)}°)
            </dd>
          </div>
        )}
      </dl>
      {o.is_commercial_scale && (
        <p className="mt-2 text-xs text-slate-500">Usable roof area exceeds 500 m² — this source classifies the roof as commercial-scale.</p>
      )}
      {o.is_heritage && (
        <p className="mt-2 text-xs text-amber-700">A heritage listing applies at this property — panel placement can be restricted; check with the council.</p>
      )}
      <p className="mt-2 text-xs text-slate-400">
        Imagery-derived estimate{o.imagery_date ? ` (imagery ${o.imagery_date})` : ''} — panel counts and yield are modelled from the roof geometry, not a system design.
      </p>
    </SolarShell>
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

interface TerrainFindingRow { title?: string; narrative?: string; severity?: string; classification?: string; }
interface TerrainInterpretationData { findings?: TerrainFindingRow[]; disclaimer?: string; }

const TERRAIN_SEVERITY_STYLES: Record<string, string> = {
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  amber: 'bg-amber-50 text-amber-700 ring-amber-200',
  red: 'bg-red-50 text-red-700 ring-red-200',
};

function TerrainCard({ data, interpretation }: { data: TerrainData; interpretation?: TerrainInterpretationData | null }) {
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
    <div className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
      <div className="px-5 py-4 border-b border-slate-200/70 bg-gradient-to-r from-slate-50/90 via-white to-white flex items-center justify-between gap-3">
        <div>
          <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-slate-900 [text-wrap:balance]">Terrain</h3>
          <p className="text-xs text-slate-500 mt-0.5">Slope, aspect and drainage from elevation</p>
        </div>
        <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-600/25">Calculated</span>
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
          <dl className="grid grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-1.5 mt-3 text-xs">
            <div><dt className="text-slate-400">Slope</dt><dd className="text-slate-700">{data.slope_mean_deg != null ? `${data.slope_mean_deg.toFixed(1)}° avg${data.slope_max_deg != null ? ` · ${Math.round(data.slope_max_deg)}° max` : ''}` : '—'}</dd></div>
            <div><dt className="text-slate-400">Fall</dt><dd className="text-slate-700">{data.elevation_range_m != null ? `${data.elevation_range_m.toFixed(1)} m` : '—'}</dd></div>
            <div><dt className="text-slate-400">Drains to</dt><dd className="text-slate-700">{data.drainage_direction ?? '—'}</dd></div>
            <div><dt className="text-slate-400">Landform</dt><dd className="text-slate-700">{data.landform_type ?? '—'}</dd></div>
          </dl>
        </div>
      </div>
      {/* Structured findings computed by the terrain service (gradient,
          landform, solar access) — each a factual reading with severity. */}
      {interpretation?.findings && interpretation.findings.length > 0 && (
        <div className="px-5 pb-4">
          <div className="text-xs font-medium text-slate-500 mb-1.5">What the terrain readings mean</div>
          <ul className="space-y-1.5">
            {interpretation.findings.map((f, i) => (
              <li key={f.title ?? i} className="text-sm text-slate-700 leading-snug">
                {f.severity && (
                  <span className={`inline-flex items-center rounded px-1.5 py-0.5 mr-1.5 text-[10px] font-medium ring-1 align-middle ${TERRAIN_SEVERITY_STYLES[f.severity] ?? 'bg-slate-100 text-slate-500 ring-slate-200'}`}>
                    {f.title ?? f.severity}
                  </span>
                )}
                {f.narrative}
              </li>
            ))}
          </ul>
          {interpretation.disclaimer && (
            <p className="text-[11px] text-slate-400 mt-2 leading-snug">{interpretation.disclaimer}</p>
          )}
        </div>
      )}
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
const EXPECTED_SECTIONS_DEV = ['dcp_controls', 'sepp_housing', 'constraint_arithmetic', 'neighbourhood', 'market_context'];
const EXPECTED_SECTIONS_SAT = [
  'satellite.bushfire', 'satellite.flood', 'satellite.climate_disclosure',
  'satellite.granny_flat', 'satellite.terrain', 'satellite.solar',
  // 'satellite.pre_da_history' soft-dropped — see the sectionEvents filter below.
];

// Sticky section jump bar — cards stack one per row, so a finished brief is a
// long page; the bar lists the sections that have streamed in, in order, and
// jumps to them. Hidden until there is something to jump between.
function SectionJumpBar({ sections }: { sections: string[] }) {
  const seen = new Set<string>();
  const ordered = sections.filter((s) => (seen.has(s) ? false : (seen.add(s), true)));
  if (ordered.length < 2) return null;
  return (
    <nav aria-label="Brief sections" className="sticky top-2 z-20">
      <div className="flex gap-1 overflow-x-auto rounded-full border border-slate-200 bg-white/85 backdrop-blur-md px-2 py-1.5 shadow-sm [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {ordered.map((s) => (
          <a
            key={s}
            href={`#${sectionAnchorId(s)}`}
            className="whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-teal-50 hover:text-teal-800"
          >
            {SECTION_LABELS[s]?.label ?? formatKey(s.replace(/^satellite\./, ''))}
          </a>
        ))}
      </div>
    </nav>
  );
}

// When satellite analysis wasn't requested, the backend emits NO events for the
// six opt-in layers — without this card the finished brief carries zero trace
// they exist (a silent absence, not an honest "not run").
function SatelliteLayersNotRunCard() {
  return (
    <div className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
      <div className="px-5 py-4 border-b border-slate-200/70 bg-gradient-to-r from-slate-50/90 via-white to-white flex items-center justify-between gap-3">
        <div>
          <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-slate-900 [text-wrap:balance]">Satellite analysis</h3>
          <p className="text-xs text-slate-500 mt-0.5">Six further layers were not part of this run</p>
        </div>
        <span className="px-2 py-0.5 text-xs font-medium rounded bg-teal-50 text-teal-700">Not run</span>
      </div>
      <div className="px-5 py-4">
        <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2 text-sm">
          {EXPECTED_SECTIONS_SAT.map((s) => (
            <li key={s} className="flex flex-col">
              <span className="text-slate-900">{SECTION_LABELS[s]?.label ?? formatKey(s.replace(/^satellite\./, ''))}</span>
              {SECTION_LABELS[s]?.description && (
                <span className="text-xs text-slate-500">{SECTION_LABELS[s].description}</span>
              )}
            </li>
          ))}
        </ul>
        <p className="text-xs text-slate-500 mt-3 border-t border-slate-100 pt-3">
          Tick &ldquo;Include satellite analysis&rdquo; above and run the brief again to add these layers.
        </p>
      </div>
    </div>
  );
}

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
        <div className="flex items-baseline gap-4">
          <span className="text-sm text-slate-500 tabular-nums">{formatElapsed(elapsed)}</span>
          <span
            className={`tabular-nums ${
              state === 'complete'
                ? 'text-sm font-medium text-slate-700'
                : 'text-lg font-semibold text-teal-600'
            }`}
          >
            {progress}%
          </span>
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
          <div><span className="text-amber-600">Calculated:</span> <span className="font-medium">{cs.estimated}</span></div>
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
                  {/* Literal space before the link — ml-2 is visual only, so without
                      it the copy-pasted text ran the sentence into "…retry.Verify". */}
                  {g.verify_url && ' '}
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
  { label: 'Authoritative', color: 'text-emerald-600', meaning: 'Taken directly from an official government source (the LEP, the cadastre, the Valuer General).' },
  { label: 'Calculated', color: 'text-amber-600', meaning: 'An exact calculation on satellite, statistical or climate-model data — the method and source are stated with each figure. Calculated from data, not measured on site.' },
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
    // Prior Development Activity soft-dropped (2026-06): it needs a heavy ML dependency
    // (torch/Tessera) the web container can't host, so it always errored. Hide the card
    // until it's decoupled to a worker. Backend code retained — re-enable by removing
    // this filter, restoring the toggle, and re-adding it to EXPECTED_SECTIONS_SAT.
    .filter((p) => p.data.section !== 'satellite.pre_da_history');
  const completeEvent = parts.find((p): p is Extract<BriefEvent, { event: 'complete' }> => p.event === 'complete');
  const planningCtx = getPlanningContext(sectionEvents);

  // Brief LLM overlay: user's intent (chip pick) + the assembled brief the
  // overlay endpoint needs. Payload is null until the brief completes, so the
  // card can't fetch early; data already lives in `parts` — no re-fetch.
  const [overlayIntent, setOverlayIntent] = useState<string | null>(null);
  const overlayPayload = useMemo(() => {
    if (!OVERLAY_UI_ENABLED || !completeEvent) return null;
    return assembleBriefPayload({
      metadata: metadataEvent ? (metadataEvent.data as unknown as Record<string, unknown>) : null,
      sections: sectionEvents.map((e) => ({ section: e.data.section, data: e.data.data })),
      complete: completeEvent.data as unknown as Record<string, unknown>,
      briefType,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completeEvent, metadataEvent, sectionEvents.length, briefType]);

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

  const startBrief = useCallback(async (address: string, lat: number | null, lng: number | null) => {
    if (!address.trim()) return;

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
          address,
          lat,
          lng,
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
  }, [includeSatellite]);

  const handleGenerate = useCallback(() => {
    startBrief(selectedAddress, selectedLat, selectedLng);
  }, [startBrief, selectedAddress, selectedLat, selectedLng]);

  // The landing hero (ProductLandingV2) dispatches a window 'landing-search'
  // CustomEvent carrying the typed address — the same contract the other report
  // landings use. Start a brief from it; lat/lng resolve server-side.
  useEffect(() => {
    const onLandingSearch = (e: Event) => {
      const address = (e as CustomEvent<{ address?: string }>).detail?.address?.trim();
      if (!address || stateRef.current !== 'idle') return;
      setInputAddress(address);
      setSelectedAddress(address);
      setSelectedLat(null);
      setSelectedLng(null);
      startBrief(address, null, null);
    };
    window.addEventListener('landing-search', onLandingSearch);
    return () => window.removeEventListener('landing-search', onLandingSearch);
  }, [startBrief]);

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
    setOverlayIntent(null);
  }, []);

  return (
    <div className="max-w-6xl mx-auto">
      {/* Landing — hero (with its own search), data sources, coverage and method.
          Idle only; the hero carries the page title, so the compact header below
          renders only once a brief is running. Mirrors /reports/conveyancing.
          The satellite toggle rides under the hero search: briefs started from
          the hero use it, so the option is visible where the run actually starts
          (not only in the secondary input card further down). */}
      {state === 'idle' && (
        <ProductLandingV2
          product="intelligence-brief"
          searchExtras={
            <div className="mt-4 flex justify-center">
              <label className="inline-flex items-center gap-2.5 rounded-xl bg-card px-4 py-2.5 text-sm font-medium text-foreground shadow-md ring-1 ring-border/50 cursor-pointer hover:ring-primary/50 transition-all">
                <input
                  type="checkbox"
                  checked={includeSatellite}
                  onChange={(e) => setIncludeSatellite(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                />
                Include satellite analysis
                <span className="font-normal text-muted-foreground">bushfire · flood · climate · granny flat detection</span>
              </label>
            </div>
          }
        />
      )}

      {/* Header */}
      {state !== 'idle' && (
        <div className="mb-8">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-teal-700 mb-1.5">PlotDetect · Property Dossier</div>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight text-slate-900">Site Report</h1>
          <p className="text-sm text-slate-500 mt-2 max-w-3xl leading-relaxed">
            For a single NSW property: what the rules allow, what physically constrains the site,
            what environmental risk applies, what it&apos;s worth, and what&apos;s happening
            next door — fifteen-plus government, satellite and computed layers fused into one brief,
            every figure traced to its source.
          </p>
        </div>
      )}

      {/* Address input — the functional entry point (carries the satellite toggle
          the landing hero doesn't have). Sits below the landing, like the tool
          input on the conveyancing page. */}
      {state === 'idle' && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-4 max-w-2xl mx-auto">
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
            Generate Site Report
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

          {/* Brief LLM overlay (flag-gated OFF by default): intent chips fill
              the stream wait; the card appears above the dossier once the
              brief completes. Purely additive — removing this block (or
              turning either flag off) leaves the page exactly as before. */}
          {OVERLAY_UI_ENABLED && (
            <BriefIntentBar
              intent={overlayIntent}
              onIntentChange={setOverlayIntent}
              briefReady={state === 'complete'}
            />
          )}
          {OVERLAY_UI_ENABLED && state === 'complete' && (
            <BriefOverlayCard briefPayload={overlayPayload} intent={overlayIntent} />
          )}

          {/* Optional lead capture — never gates the result; offers to email the
              brief so an interested visitor becomes a follow-up-able contact. */}
          {state === 'complete' && (
            <PostResultEmailStrip
              address={metadataEvent?.data.address ?? selectedAddress ?? ''}
              product="intelligence-brief"
              copy="Want this brief emailed to you? Drop your address and we'll send it over."
            />
          )}

          {/* Aerial — NSW SIX Maps 10cm imagery for the lot (reuses AerialTile). */}
          {(metadataEvent?.data.lat ?? selectedLat) != null && (metadataEvent?.data.lng ?? selectedLng) != null && (
            <div className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
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

          {/* Live status panel — elapsed time, section timeline, progress.
              #745 D7-1: hidden once complete — its section timeline duplicated
              the jump bar's list at the top of the finished report. */}
          {state !== 'complete' && (
          <LiveStatusPanel
            elapsed={elapsed}
            progress={state === 'triggering' ? 0 : latestProgress}
            receivedSections={sectionEvents.map((e) => e.data.section)}
            briefType={briefType}
            includeSatellite={includeSatellite}
            state={state}
          />
          )}

          {/* Sticky jump bar — one card per row makes the page long; this tracks
              the sections that have streamed in and jumps to them. */}
          <SectionJumpBar sections={sectionEvents.map((e) => e.data.section)} />

          {/* Section cards — stacked full-width, one per row, in stream order.
              Wide cards let each card's internal key-value grid run 3-4 columns;
              the old 3-column bento starved field-heavy sections into towers. */}
          <div id="brief-dossier" className="flex flex-col gap-4">
            {sectionEvents.map((event, i) => {
              const section = event.data.section;
              // Development Capacity renders via the dedicated card (carries its
              // own binding-constraint breakdown + disclaimer). Falls back to the
              // generic SectionCard when the value is absent (not computed).
              let card: ReactNode = null;
              if (section === 'satellite.solar') {
                card = <SolarBriefCard address={metadataEvent?.data.address ?? selectedAddress} active={ranWithSatellite} />;
              }
              if (section === 'satellite.granny_flat') {
                // Decoupled: the card fires the gated async route itself (gate +
                // real Modal scan), rather than the brief's timed-out inline run.
                card = <GrannyFlatBriefCard address={metadataEvent?.data.address ?? selectedAddress} active={ranWithSatellite} lotAreaM2={planningCtx.lotAreaM2 ?? null} />;
              }
              if (section === 'constraint_arithmetic') {
                const ca = (event.data.data?.value ?? null) as ConstraintArithmeticResult | null;
                if (ca) {
                  const ledger = buildYieldLedgerContext(sectionEvents, ca);
                  card = (
                    <ConstraintArithmeticCard
                      briefData={ca}
                      lotArea={ca.lot_area_m2}
                      devType={ca.dev_type}
                      zone={planningCtx.zone}
                      inputProvenance={ledger.inputProvenance}
                      envelopeGap={ledger.envelopeGap}
                    />
                  );
                }
              }
              if (section === 'sepp_housing') {
                const standards = (event.data.data?.value ?? null) as SeppStandard[] | null;
                const evData = event.data as unknown as {
                  eligibility_forms?: EligibilityField | null;
                  lot_area_m2?: number | null;
                  lot_width_m?: number | null;
                };
                if (standards && standards.length) {
                  card = (
                    <SeppHousingCard
                      standards={standards}
                      eligibility={evData.eligibility_forms}
                      lotAreaM2={evData.lot_area_m2}
                      lotWidthM={evData.lot_width_m}
                    />
                  );
                } else {
                  card = <SeppContextCard ctx={planningCtx} />;
                }
              }
              if (section === 'market_context') {
                card = <MarketContextCard data={event.data.data} satelliteRan={ranWithSatellite} />;
              }
              if (section === 'satellite.terrain') {
                // Terrain may arrive as a plain dict or a DataField wrapping it in .value.
                const raw = event.data.data as Record<string, unknown> | null;
                const t = (raw && typeof raw === 'object'
                  ? ((raw.value as TerrainData) ?? (raw as unknown as TerrainData))
                  : null);
                if (t && typeof t === 'object' && t.slope_mean_deg != null) {
                  const interp = (event.data as unknown as { interpretation?: TerrainInterpretationData | null }).interpretation ?? null;
                  card = <TerrainCard data={t} interpretation={interp} />;
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
                <div key={`${section}-${i}`} id={sectionAnchorId(section)} className="min-w-0 scroll-mt-20">
                  {card}
                </div>
              );
            })}
            {/* Satellite off → the stream carried no satellite events at all;
                name the absent layers rather than leave a silent gap. */}
            {state === 'complete' && !ranWithSatellite && sectionEvents.length > 0 && (
              <div className="min-w-0">
                <SatelliteLayersNotRunCard />
              </div>
            )}
          </div>

          {/* Complete summary */}
          {completeEvent && <CompleteSummary data={completeEvent.data} hiddenGapFields={hiddenGapFields} />}
          {/* Data sources + confidence legend — built from the section cards, so it
              shows even when the stream's final 'complete' event is dropped. */}
          {state === 'complete' && sectionEvents.length > 0 && (
            <DataSourcesCard provenance={collectSources(sectionEvents, formatKey)} />
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
