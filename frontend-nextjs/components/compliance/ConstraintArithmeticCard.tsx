'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Calculator, ChevronDown, ChevronUp, AlertTriangle, TrendingDown } from 'lucide-react';
import { zoneFamily } from '@/lib/regulatory-constants';
import { DcpRequestCta } from '@/components/compliance/DcpRequestCta';

// ---------------------------------------------------------------------------
// Types matching Python ConstraintArithmeticResult
// ---------------------------------------------------------------------------

interface ConstraintStep {
  constraint: string;
  label: string;
  phase?: string | null;
  input_gfa_m2: number | null;
  reduction_m2: number | null;
  output_gfa_m2: number | null;
  footprint_m2: number | null;
  note: string;
}

interface SeppOverrideRow { dev_type?: string; control?: string; lep_value?: number; sepp_value?: number; source_clause?: string | null; }

export interface ConstraintArithmeticResult {
  sepp_overrides_applied?: SeppOverrideRow[];
  lot_area_m2: number;
  dev_type: string;
  lep_height_m: number | null;
  lep_fsr: number | null;
  lep_max_gfa_from_fsr_m2: number | null;
  lep_max_storeys: number | null;
  lep_max_gfa_from_height_m2: number | null;
  lep_envelope_gfa_m2: number | null;
  buildable_footprint_m2: number | null;
  setback_front_m: number | null;
  setback_rear_m: number | null;
  setback_side_m: number | null;
  site_coverage_cap_m2: number | null;
  landscaping_reduction_m2: number | null;
  effective_height_m: number | null;
  effective_fsr: number | null;
  shadow_storey_reduction: number;
  parking_spaces_required: number | null;
  parking_gfa_consumed_m2: number | null;
  realistic_gfa_m2: number | null;
  dcp_adjusted_gfa_m2: number | null;
  realistic_dwellings: number | null;
  // Dwelling-yield range: as-of-right floor + permitted ceiling (subject to a DA).
  // Optional — older API responses omit them; the card falls back to a single figure.
  as_of_right_form?: string | null;
  as_of_right_dwellings?: number | null;
  max_permitted_form?: string | null;
  max_permitted_dwellings?: number | null;
  // True when the ceiling was raised by the Low & Mid-Rise Housing reforms.
  ceiling_from_lmr?: boolean | null;
  // Citation for that LMR uplift — present only when a real clause backs it.
  lmr_source_clause?: string | null;
  lmr_source_document?: string | null;
  lmr_legislation_url?: string | null;
  lmr_effective_date?: string | null;
  binding_constraint: string | null;
  binding_constraint_label: string;
  steps: ConstraintStep[];
  gaps: string[];
  confidence: string;
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Constraint label → colour mapping
// ---------------------------------------------------------------------------

const CONSTRAINT_COLORS: Record<string, string> = {
  lep_height: 'bg-blue-100 text-blue-800',
  lep_fsr: 'bg-blue-100 text-blue-800',
  dcp_setbacks: 'bg-teal-100 text-teal-800',
  dcp_site_coverage: 'bg-teal-100 text-teal-800',
  dcp_landscaping: 'bg-teal-100 text-teal-800',
  dcp_deep_soil: 'bg-teal-100 text-teal-800',
  shadow_access: 'bg-amber-100 text-amber-800',
  parking: 'bg-gray-100 text-gray-800',
  lot_size: 'bg-red-100 text-red-800',
  sepp_override: 'bg-purple-100 text-purple-800',
};

const CONFIDENCE_COLORS: Record<string, string> = {
  high: 'bg-green-100 text-green-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-red-100 text-red-800',
};

// The backend tier is a ratio of available calculation inputs (height, FSR,
// three setbacks, lot dimensions, SEPP overrides — constraint_arithmetic.py).
// "low confidence" read as doubt about the arithmetic; instead state the actual
// measure: how many planning controls went into this calculation, and which.
// The tier key still drives the colour.
const YIELD_INPUTS: Array<{ label: string; has: (r: ConstraintArithmeticResult) => boolean }> = [
  { label: 'height of buildings', has: (r) => r.lep_height_m != null },
  { label: 'floor space ratio', has: (r) => r.lep_fsr != null },
  { label: 'front setback', has: (r) => r.setback_front_m != null },
  { label: 'rear setback', has: (r) => r.setback_rear_m != null },
  { label: 'side setback', has: (r) => r.setback_side_m != null },
  { label: 'SEPP standards', has: (r) => (r.sepp_overrides_applied?.length ?? 0) > 0 },
];

function yieldInputsBadge(result: ConstraintArithmeticResult): { text: string; sentence: string } {
  const used = YIELD_INPUTS.filter((i) => i.has(result));
  const missing = YIELD_INPUTS.filter((i) => !i.has(result));
  const joinLabels = (items: typeof YIELD_INPUTS) => {
    const labels = items.map((i) => i.label);
    return labels.length > 1
      ? `${labels.slice(0, -1).join(', ')} and ${labels[labels.length - 1]}`
      : labels[0];
  };
  return {
    text: `Calculated from ${used.length} of ${YIELD_INPUTS.length} planning controls`,
    sentence: [
      used.length ? `This estimate is computed from the ${joinLabels(used)}.` : '',
      missing.length
        ? `No ${joinLabels(missing)} ${missing.length > 1 ? 'are' : 'is'} mapped for this lot, so ${missing.length > 1 ? 'those controls' : 'that control'} could not narrow the estimate.`
        : '',
    ].filter(Boolean).join(' '),
  };
}

/** Engine dev_type slug → readable built-form label (e.g. "multi-dwelling housing"). */
function humanizeForm(form?: string | null): string {
  if (!form) return 'dwelling';
  return form
    .replace(/multi_dwelling/, 'multi-dwelling')
    .replace(/_/g, ' ')
    .trim();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/** One row of the inputs ledger: what went into the arithmetic, its value, and
 * where that value came from (source + currency date). */
export interface InputLedgerRow {
  label: string;
  value: string;
  source: string;
  asAt?: string | null;
}

/** Why the LEP envelope could not be computed: which principal development
 * standards are missing, from which instrument, and whether the council's DCP
 * (the document that then sets the built form) is in our dataset. */
export interface EnvelopeGap {
  missing: string[]; // e.g. ['floor space ratio', 'height of buildings']
  instrument?: string | null; // e.g. 'Wingecarribee Local Environmental Plan 2010'
  dcpOnboarded?: boolean;
  dcpName?: string | null;
}

interface ConstraintArithmeticCardProps {
  lotArea: number;
  devType: string;
  zone?: string;
  formerCouncil?: string;
  lga?: string;
  maxHeight?: number | null;
  maxFsr?: number | null;
  frontage?: number | null;
  depth?: number | null;
  /** Pre-computed result from intelligence brief — skips independent fetch when provided. */
  briefData?: ConstraintArithmeticResult | null;
  /** Inputs ledger (value + source per input) — composed by the brief page from
   * the sections' provenance; absent in the assessment UI. */
  inputProvenance?: InputLedgerRow[] | null;
  /** Named-missing-control context, shown when the envelope could not compute. */
  envelopeGap?: EnvelopeGap | null;
  /** Subject address, threaded into the missing-DCP request for alert context. */
  address?: string | null;
}

export function ConstraintArithmeticCard({
  lotArea,
  devType,
  zone,
  formerCouncil,
  lga,
  maxHeight,
  maxFsr,
  frontage,
  depth,
  briefData,
  inputProvenance,
  envelopeGap,
  address,
}: ConstraintArithmeticCardProps) {
  const [result, setResult] = useState<ConstraintArithmeticResult | null>(briefData ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSteps, setShowSteps] = useState(false);

  // If briefData is provided, use it directly — no fetch needed
  useEffect(() => {
    if (briefData) {
      setResult(briefData);
      setLoading(false);
      setError(null);
      return;
    }

    if (!lotArea || lotArea <= 0) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch('/api/constraint-arithmetic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lot_area_m2: lotArea,
        dev_type: devType,
        zone,
        formerCouncil,
        lga,
        maxHeight: maxHeight ?? null,
        maxFsr: maxFsr ?? null,
        frontage: frontage ?? null,
        depth: depth ?? null,
      }),
    })
      .then(async (resp) => {
        if (cancelled) return;
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(`HTTP ${resp.status}: ${text}`);
        }
        const json = await resp.json();
        if (json.success) {
          setResult(json.data);
        } else {
          throw new Error(json.error || 'Computation failed');
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [lotArea, devType, zone, formerCouncil, lga, maxHeight, maxFsr, frontage, depth, briefData]);

  if (loading) {
    return (
      <Card className="border-blue-200 bg-blue-50/30">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 animate-pulse">
            <Calculator className="h-4 w-4 text-blue-400" />
            <span className="text-sm text-blue-400">Computing development yield...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-amber-200 bg-amber-50/30">
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            <span className="text-sm text-amber-700">
              Development yield computation unavailable
            </span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!result) return null;

  // Dwelling-yield range. Floor = the conservative as-of-right baseline (falls back to
  // realistic_dwellings for older API responses); ceiling = the densest permitted form,
  // shown only when it genuinely exceeds the floor.
  const floorDwellings = result.as_of_right_dwellings ?? result.realistic_dwellings ?? 0;
  const ceilingDwellings = result.max_permitted_dwellings ?? null;
  // The dwelling-yield + DCP-setback model only covers residential zones (R1–R5). On
  // centre/employment/special-use zones a detached-dwelling yield and residential
  // setbacks are wrong (e.g. E1 delivers housing as shop-top housing; a dwelling house
  // is prohibited), so suppress those and show only the LEP envelope + a note.
  const zoneModelled = !zone || /^(R[1-5]|RU5)\b/i.test(zone.trim());
  const hasYield = floorDwellings > 0 && zoneModelled;
  const inputsBadge = yieldInputsBadge(result);

  return (
    <Card className="border-blue-200 bg-blue-50/30">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calculator className="h-5 w-5 text-blue-700" />
            <CardTitle className="text-lg text-blue-900">
              Development Yield Estimate
            </CardTitle>
          </div>
          <Badge
            className={CONFIDENCE_COLORS[result.confidence] || 'bg-gray-100 text-gray-800'}
          >
            {inputsBadge.text}
          </Badge>
        </div>
        {inputsBadge.sentence && (
          <p className="text-xs text-gray-600 mt-1.5 leading-relaxed">
            {inputsBadge.sentence}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* The envelope could not be computed — name the exact missing control
            and where the buildable form is set instead, rather than showing an
            empty card. Rendered only when the caller supplies the context. */}
        {result.realistic_gfa_m2 == null && envelopeGap && envelopeGap.missing.length > 0 && (
          <div className="bg-white border border-amber-200 rounded-lg p-3 text-sm text-gray-700 leading-relaxed">
            <div className="text-xs font-medium text-amber-700 mb-1">Why there is no computed envelope</div>
            No {envelopeGap.missing.join(' or ')} control is mapped in{' '}
            {envelopeGap.instrument || 'the LEP'} for this lot, so a maximum GFA
            envelope cannot be computed from the LEP. The built form here is set
            by the council&rsquo;s development control plan
            {envelopeGap.dcpOnboarded
              ? envelopeGap.dcpName
                ? <> — see the DCP Controls card ({envelopeGap.dcpName}).</>
                : <> — see the DCP Controls card.</>
              : <>, which is not in our structured dataset for this council yet — check the DCP on the council&rsquo;s website.</>}
            {/* Point-of-pain CTA: when the DCP isn't loaded, let the user ask us to
                prioritise it (records demand + pings ops). Reuses /api/dcp-interest. */}
            {!envelopeGap.dcpOnboarded && (
              <DcpRequestCta council={lga || formerCouncil || ''} address={address} />
            )}
          </div>
        )}

        {/* Inputs ledger — each input, its value, and its source. */}
        {inputProvenance && inputProvenance.length > 0 && (
          <div className="bg-white border border-blue-100 rounded-lg overflow-hidden">
            <div className="bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700">
              Inputs used by this calculation
            </div>
            <table className="w-full text-xs">
              <tbody className="divide-y divide-blue-50">
                {inputProvenance.map((row) => (
                  <tr key={row.label} className="hover:bg-blue-50/50">
                    <td className="px-3 py-1.5 text-gray-500">{row.label}</td>
                    <td className="px-3 py-1.5 font-medium text-gray-900">{row.value}</td>
                    <td className="px-3 py-1.5 text-right text-gray-400">
                      {row.source}{row.asAt ? ` · as at ${row.asAt}` : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Key metrics row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Maximum GFA — the clean LEP envelope (headline) */}
          {result.realistic_gfa_m2 != null && (
            <div className="bg-white border border-blue-200 rounded-lg p-3">
              <div className="text-xs font-medium text-blue-600 mb-1">Maximum GFA</div>
              <div className="text-xl font-bold text-gray-900">
                {Math.round(result.realistic_gfa_m2).toLocaleString()}m²
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                LEP envelope (FSR / height)
              </div>
            </div>
          )}

          {/* After council DCP — secondary, only when lot geometry resolved */}
          {zoneModelled && result.dcp_adjusted_gfa_m2 != null && (
            <div className="bg-white border border-teal-200 rounded-lg p-3">
              <div className="text-xs font-medium text-teal-700 mb-1">After council DCP</div>
              <div className="text-xl font-bold text-gray-900">
                {Math.round(result.dcp_adjusted_gfa_m2).toLocaleString()}m²
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                indicative — after setbacks &amp; landscaping
              </div>
            </div>
          )}

          {/* Dwelling yield — a RANGE: as-of-right floor to permitted ceiling (subject
              to a DA). The count is an illustration of the GFA envelope, not a promise. */}
          {hasYield && (
            <div className="bg-white border border-blue-200 rounded-lg p-3">
              <div className="text-xs font-medium text-blue-600 mb-1">Homes you could build</div>
              {ceilingDwellings != null && ceilingDwellings > floorDwellings ? (
                <>
                  <div className="text-xl font-bold text-gray-900">
                    {floorDwellings}&ndash;{ceilingDwellings}
                  </div>
                  <div className="text-xs text-gray-600 mt-1 leading-relaxed">
                    <span className="font-medium text-gray-900">{floorDwellings}</span> as-of-right (subject to a DA),
                    {' '}up to <span className="font-medium text-gray-900">{ceilingDwellings}</span>{' '}
                    ({humanizeForm(result.max_permitted_form)}) with council approval.
                  </div>
                  {/* #745 D6: the two ceilings rest on different legal pathways.
                      Without a label, "up to 3 (multi-dwelling)" reads as a
                      contradiction of the SEPP card's "Not eligible" above. */}
                  {!result.ceiling_from_lmr && (
                    <div className="text-xs text-gray-500 mt-1">
                      The higher figure rests on the LEP land use table for this
                      zone (a merit-assessed development application) — it is a
                      separate pathway from the SEPP Housing standards shown above.
                    </div>
                  )}
                  {/* LMR note — shown ONLY when a real clause backs it (no citation, no claim). */}
                  {result.ceiling_from_lmr && result.lmr_source_clause && (
                    <div className="text-xs text-teal-700 mt-1">
                      Higher limit under{' '}
                      {result.lmr_legislation_url ? (
                        <a
                          href={result.lmr_legislation_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="underline hover:text-teal-900"
                        >
                          {result.lmr_source_document || 'SEPP (Housing) 2021'} cl {result.lmr_source_clause}
                        </a>
                      ) : (
                        <>{result.lmr_source_document || 'SEPP (Housing) 2021'} cl {result.lmr_source_clause}</>
                      )}
                      {result.lmr_effective_date ? ` (from ${result.lmr_effective_date})` : ''}.
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="text-xl font-bold text-gray-900">{floorDwellings}</div>
                  <div className="text-xs text-gray-600 mt-1 leading-relaxed">
                    {humanizeForm(result.as_of_right_form)} — as-of-right yield, subject to a development application.
                  </div>
                </>
              )}
            </div>
          )}

          {/* Non-residential zone — dwelling yield/setbacks aren't modelled; explain, don't
              assert. Copy branches by zone FAMILY: "shop-top housing above retail" is true
              on a centres/business zone and wrong on a conservation or rural one. */}
          {!zoneModelled && (
            <div className="bg-white border border-amber-200 rounded-lg p-3 col-span-2">
              <div className="text-xs font-medium text-amber-700 mb-1">Dwelling yield</div>
              <div className="text-sm text-gray-700 leading-snug">
                {zoneFamily(zone || '') === 'centres'
                  ? <>Not modelled for {zone || 'this zone'} — a non-residential zone. Housing here is delivered through the zone&rsquo;s permitted uses (e.g. shop-top housing above retail), not a detached dwelling. The GFA envelope above still applies; see the land use table for the permitted forms.</>
                  : <>Dwelling yield is not modelled for {zone || 'this zone'} — outside the residential zones the permitted housing forms are set by the zone&rsquo;s land-use table, and yield modelling assumes a residential development form. The GFA envelope above still applies.</>}
              </div>
            </div>
          )}

          {/* Binding constraint */}
          {result.binding_constraint && (
            <div className="bg-white border border-blue-200 rounded-lg p-3">
              <div className="text-xs font-medium text-blue-600 mb-1">Binding Constraint</div>
              <Badge className={`text-xs ${CONSTRAINT_COLORS[result.binding_constraint] || 'bg-gray-100 text-gray-800'}`}>
                {result.binding_constraint_label || result.binding_constraint.replace(/_/g, ' ')}
              </Badge>
            </div>
          )}

          {/* Max storeys */}
          {result.lep_max_storeys != null && (
            <div className="bg-white border border-blue-200 rounded-lg p-3">
              <div className="text-xs font-medium text-blue-600 mb-1">Max Storeys</div>
              <div className="text-xl font-bold text-gray-900">
                {result.lep_max_storeys - result.shadow_storey_reduction}
                {result.shadow_storey_reduction > 0 && (
                  <span className="text-sm font-normal text-amber-600 ml-1">
                    (-{result.shadow_storey_reduction} shadow)
                  </span>
                )}
              </div>
              {result.effective_height_m != null && (
                <div className="text-xs text-gray-500 mt-0.5">
                  {result.effective_height_m}m height limit
                </div>
              )}
            </div>
          )}
        </div>

        {/* SEPP overrides applied */}
        {result.effective_height_m != null && result.lep_height_m != null &&
         result.effective_height_m > result.lep_height_m && (
          <div className="bg-purple-50 border border-purple-200 rounded-lg px-3 py-2 text-xs text-purple-800">
            SEPP override: height increased from {result.lep_height_m}m to {result.effective_height_m}m
            {(() => {
              const ov = (result.sepp_overrides_applied ?? []).find((o) => o.control === 'height' && o.source_clause);
              return ov ? <> — cl {ov.source_clause}, SEPP (Housing) 2021</> : null;
            })()}
          </div>
        )}
        {result.effective_fsr != null && result.lep_fsr != null &&
         result.effective_fsr > result.lep_fsr && (
          <div className="bg-purple-50 border border-purple-200 rounded-lg px-3 py-2 text-xs text-purple-800">
            SEPP override: FSR increased from {result.lep_fsr}:1 to {result.effective_fsr}:1
            {(() => {
              const ov = (result.sepp_overrides_applied ?? []).find((o) => o.control === 'fsr' && o.source_clause);
              return ov ? <> — cl {ov.source_clause}, SEPP (Housing) 2021</> : null;
            })()}
          </div>
        )}

        {/* Setbacks summary — residential DCP controls; suppress on non-residential zones. */}
        {zoneModelled && (result.setback_front_m != null || result.setback_side_m != null || result.setback_rear_m != null) && (
          <div className="bg-white border border-blue-100 rounded-lg p-3">
            <div className="text-xs font-medium text-blue-600 mb-2">DCP Setbacks Applied</div>
            <div className="flex gap-4 text-sm">
              {result.setback_front_m != null && (
                <span className="text-gray-700">Front: <span className="font-semibold">{result.setback_front_m}m</span></span>
              )}
              {result.setback_side_m != null && (
                <span className="text-gray-700">Side: <span className="font-semibold">{result.setback_side_m}m</span></span>
              )}
              {result.setback_rear_m != null && (
                <span className="text-gray-700">Rear: <span className="font-semibold">{result.setback_rear_m}m</span></span>
              )}
            </div>
            {result.buildable_footprint_m2 != null && (
              <div className="text-xs text-gray-500 mt-1">
                Buildable footprint: {Math.round(result.buildable_footprint_m2).toLocaleString()}m²
                {result.lot_area_m2 > 0 && (
                  <> ({Math.round((result.buildable_footprint_m2 / result.lot_area_m2) * 100)}% of lot)</>
                )}
              </div>
            )}
          </div>
        )}

        {/* Data gaps */}
        {result.gaps.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              <span className="text-xs font-medium text-amber-800">Data gaps</span>
            </div>
            <ul className="text-xs text-amber-700 space-y-0.5">
              {result.gaps.map((gap, i) => (
                <li key={i}>- {gap}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Computation steps (collapsible) */}
        {result.steps.length > 0 && (
          <div>
            <button
              onClick={() => setShowSteps(!showSteps)}
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 transition-colors"
            >
              {showSteps ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {showSteps ? 'Hide' : 'Show'} computation chain ({result.steps.length} steps)
            </button>

            {showSteps && (() => {
              const lepSteps = result.steps.filter((s) => s.phase !== 'dcp');
              const dcpSteps = result.steps.filter((s) => s.phase === 'dcp');
              const m2 = (n: number) => `${Math.round(n).toLocaleString()}m²`;
              return (
                <div className="mt-2 space-y-3">
                  {/* Phase 1 — LEP envelope: FSR vs height are ALTERNATIVES, the
                      smaller caps the maximum. Not a subtraction chain. */}
                  {lepSteps.length > 0 && (
                    <div className="bg-white border border-blue-100 rounded-lg overflow-hidden">
                      <div className="bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700">
                        Maximum envelope (LEP) — the smaller of the FSR and height caps
                      </div>
                      <table className="w-full text-xs">
                        <tbody className="divide-y divide-blue-50">
                          {lepSteps.map((step, i) => (
                            <tr key={i} className="hover:bg-blue-50/50">
                              <td className="px-3 py-1.5 text-gray-700">{step.label}</td>
                              <td className="px-3 py-1.5 text-right font-medium text-gray-900">
                                {step.output_gfa_m2 != null ? m2(step.output_gfa_m2) : '—'}
                              </td>
                            </tr>
                          ))}
                          {result.lep_envelope_gfa_m2 != null && (
                            <tr className="bg-blue-50/40 font-medium">
                              <td className="px-3 py-1.5 text-blue-800">
                                Maximum GFA{result.binding_constraint_label ? ` — ${result.binding_constraint_label}` : ''}
                              </td>
                              <td className="px-3 py-1.5 text-right text-blue-900">{m2(result.lep_envelope_gfa_m2)}</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Phase 2 — indicative DCP erosion: a reconciling chain
                      (output = input − change), shown separately, never summed
                      with the LEP maximum above. */}
                  {dcpSteps.length > 0 && (
                    <div className="bg-white border border-amber-100 rounded-lg overflow-hidden">
                      <div className="bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700">
                        After council DCP (indicative) — setbacks, landscaping, parking, shadow
                      </div>
                      <table className="w-full text-xs">
                        <thead className="bg-amber-50/60">
                          <tr>
                            <th className="text-left px-3 py-1.5 text-amber-700">Step</th>
                            <th className="text-right px-3 py-1.5 text-amber-700">Input</th>
                            <th className="text-right px-3 py-1.5 text-amber-700">Change</th>
                            <th className="text-right px-3 py-1.5 text-amber-700">Output</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-amber-50">
                          {dcpSteps.map((step, i) => (
                            <tr key={i} className="hover:bg-amber-50/50">
                              <td className="px-3 py-1.5 text-gray-700">{step.label}</td>
                              <td className="px-3 py-1.5 text-right text-gray-500">
                                {step.input_gfa_m2 != null
                                  ? m2(step.input_gfa_m2)
                                  : step.footprint_m2 != null
                                    ? `${m2(step.footprint_m2)} footprint`
                                    : '—'}
                              </td>
                              <td className="px-3 py-1.5 text-right">
                                {step.reduction_m2 != null && step.reduction_m2 !== 0 ? (
                                  <span className="text-red-600">
                                    <TrendingDown className="h-3 w-3 inline mr-0.5" />
                                    -{Math.round(step.reduction_m2).toLocaleString()}m²
                                  </span>
                                ) : (
                                  <span className="text-gray-400">—</span>
                                )}
                              </td>
                              <td className="px-3 py-1.5 text-right font-medium text-gray-900">
                                {step.output_gfa_m2 != null ? m2(step.output_gfa_m2) : '—'}
                              </td>
                            </tr>
                          ))}
                          {result.dcp_adjusted_gfa_m2 != null && (
                            <tr className="bg-amber-50/40 font-medium">
                              <td className="px-3 py-1.5 text-amber-800">Indicative after-DCP GFA</td>
                              <td className="px-3 py-1.5" colSpan={2} />
                              <td className="px-3 py-1.5 text-right text-amber-900">{m2(result.dcp_adjusted_gfa_m2)}</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                      <p className="px-3 py-1.5 text-[11px] text-amber-600/80">
                        Indicative only — a separate erosion from the LEP maximum above, not subtracted from it.
                      </p>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}

        {/* Disclaimer */}
        <p className="text-xs text-gray-400 leading-relaxed">
          {result.disclaimer}
        </p>
      </CardContent>
    </Card>
  );
}
