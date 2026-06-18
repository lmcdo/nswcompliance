'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Calculator, ChevronDown, ChevronUp, AlertTriangle, TrendingDown } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types matching Python ConstraintArithmeticResult
// ---------------------------------------------------------------------------

interface ConstraintStep {
  constraint: string;
  label: string;
  input_gfa_m2: number | null;
  reduction_m2: number | null;
  output_gfa_m2: number | null;
  footprint_m2: number | null;
  note: string;
}

export interface ConstraintArithmeticResult {
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
  const hasYield = floorDwellings > 0;

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
          <Badge className={CONFIDENCE_COLORS[result.confidence] || 'bg-gray-100 text-gray-800'}>
            {result.confidence} confidence
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
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
          {result.dcp_adjusted_gfa_m2 != null && (
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
              <div className="text-xs font-medium text-blue-600 mb-1">Dwelling Yield</div>
              <div className="text-xl font-bold text-gray-900">
                {floorDwellings}
                {ceilingDwellings != null && ceilingDwellings > floorDwellings && (
                  <span>&ndash;{ceilingDwellings}</span>
                )}
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {ceilingDwellings != null && ceilingDwellings > floorDwellings ? (
                  <>
                    {floorDwellings} as-of-right &middot; up to {ceilingDwellings}{' '}
                    ({humanizeForm(result.max_permitted_form)}) subject to a DA
                  </>
                ) : (
                  <>{humanizeForm(result.as_of_right_form)}, as-of-right</>
                )}
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
          </div>
        )}
        {result.effective_fsr != null && result.lep_fsr != null &&
         result.effective_fsr > result.lep_fsr && (
          <div className="bg-purple-50 border border-purple-200 rounded-lg px-3 py-2 text-xs text-purple-800">
            SEPP override: FSR increased from {result.lep_fsr}:1 to {result.effective_fsr}:1
          </div>
        )}

        {/* Setbacks summary */}
        {(result.setback_front_m != null || result.setback_side_m != null || result.setback_rear_m != null) && (
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

            {showSteps && (
              <div className="mt-2 bg-white border border-blue-100 rounded-lg overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-blue-50">
                    <tr>
                      <th className="text-left px-3 py-1.5 text-blue-700">Step</th>
                      <th className="text-right px-3 py-1.5 text-blue-700">Input</th>
                      <th className="text-right px-3 py-1.5 text-blue-700">Change</th>
                      <th className="text-right px-3 py-1.5 text-blue-700">Output</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-blue-50">
                    {result.steps.map((step, i) => (
                      <tr key={i} className="hover:bg-blue-50/50">
                        <td className="px-3 py-1.5 text-gray-700">{step.label}</td>
                        <td className="px-3 py-1.5 text-right text-gray-500">
                          {step.input_gfa_m2 != null ? `${Math.round(step.input_gfa_m2).toLocaleString()}m²` : '-'}
                        </td>
                        <td className="px-3 py-1.5 text-right">
                          {step.reduction_m2 != null && step.reduction_m2 !== 0 ? (
                            <span className="text-red-600">
                              <TrendingDown className="h-3 w-3 inline mr-0.5" />
                              -{Math.round(step.reduction_m2).toLocaleString()}m²
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-3 py-1.5 text-right font-medium text-gray-900">
                          {step.output_gfa_m2 != null ? `${Math.round(step.output_gfa_m2).toLocaleString()}m²` : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
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
