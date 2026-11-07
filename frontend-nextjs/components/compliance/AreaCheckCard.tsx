'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { AreaCheck } from '@/hooks/useAreaCheck';
import { reformParkingRates, todAffordableParkingRates, type LawFacts } from '@/lib/law-facts';

// prior-art-checked: no component shows the state-law area answer with its range, warnings and what was not checked
// (grep components/compliance, 2026-11-07). HousingSEPPEligibilityCard decides eligibility per development type; this card shows the area.

interface Props {
  result: AreaCheck | null;
  loading: boolean;
  failed: boolean;
  /** The stored law figures; the parking rates are read from these. Without them no rate is shown. */
  lawFacts?: LawFacts | null;
}

/** One plain sentence for each answer. The server's own wording (clause, page, range) is shown beneath it. */
function lead(r: AreaCheck): string {
  if (r.pathway === 'tod') return 'This lot is in a Transport Oriented Development area (Chapter 5).';
  if (r.pathway === 'lmr') return 'This lot is within the low and mid-rise walking distance (Chapter 6).';
  if (r.pathway === 'borderline') return 'This lot is close to the low and mid-rise walking limit.';
  if (r.pathway === 'neither') return 'This lot is in neither the Chapter 5 nor the Chapter 6 area.';
  return 'We could not work out whether this lot is in a Chapter 5 or Chapter 6 area.';
}

export function AreaCheckCard({ result, loading, failed, lawFacts }: Props) {
  if (loading) {
    return (
      <Card className="border-gray-200">
        <CardContent className="py-3 text-sm text-gray-600" data-testid="area-check-loading">Checking the housing reform area for this lot…</CardContent>
      </Card>
    );
  }
  if (failed || !result) {
    return (
      <Card className="border-gray-200">
        <CardContent className="py-3 text-sm text-gray-700" data-testid="area-check-failed">
          We could not work out the area for this lot. Why: the area check did not respond. Check this lot on the NSW Planning Portal Spatial Viewer or ask the council
          for a planning certificate.
        </CardContent>
      </Card>
    );
  }

  const rates = result.lmr.answer === 'yes' || result.lmr.answer === 'borderline' ? reformParkingRates(lawFacts) : [];
  // TOD (Chapter 5) affordable-housing parking, from the stored law facts only (the same source as the Chapter 6 rates above):
  // with no facts there is no figure, never one taken from the Python answer.
  const todParking = result.tod.answer === 'yes' ? todAffordableParkingRates(lawFacts) : [];
  const f = result.lmr.figures;
  const showRange = (result.lmr.answer === 'yes' || result.lmr.answer === 'borderline') && f?.walk_low_m != null && f?.walk_high_m != null;
  return (
    <Card className="border-indigo-200" data-testid="area-check-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-base text-indigo-900">Housing reform area</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm text-gray-800">
        <p className="font-medium" data-testid="area-check-lead">{lead(result)}</p>
        <p data-testid="area-check-headline">{result.headline}</p>
        {showRange && (
          <p className="text-xs text-gray-700" data-testid="area-check-range">
            Walking distance to {f?.anchor ?? 'the nearest station or town centre'}: probably between {f?.walk_low_m} and {f?.walk_high_m} m;
            the law's limit is {f?.limit_m} m.
          </p>
        )}
        {result.lmr.heuristic && result.lmr.answer === 'borderline' && (
          <p className="text-xs text-gray-600" data-testid="area-check-method">{result.lmr.heuristic}</p>
        )}
        {rates.length > 0 && (
          <div className="text-xs text-gray-700" data-testid="area-check-parking">
            <p className="font-medium">Car parking in a low and mid-rise area (Chapter 6)</p>
            <p>
              The law sets these non-discretionary minimums per dwelling, but only if no environmental planning instrument or development control
              plan that applies to the land sets a maximum number of spaces.
            </p>
            <ul className="list-disc pl-5">
              {rates.map((r) => (
                <li key={r.key}>{r.label}: {r.rate} {r.rate === 1 ? 'space' : 'spaces'} per dwelling ({r.clause}, page {r.pdfPage})</li>
              ))}
            </ul>
          </div>
        )}
        {todParking.length > 0 && (
          <div className="text-xs text-gray-700" data-testid="area-check-tod-parking">
            <p className="font-medium">Parking for affordable housing in a Transport Oriented Development area (Chapter 5)</p>
            <ul className="list-disc pl-5">
              {todParking.map((p) => (
                <li key={p.key}>
                  {p.bedrooms}{p.orMore ? ' or more' : ''} {p.bedrooms === 1 && !p.orMore ? 'bedroom' : 'bedrooms'}: {p.rate} per dwelling ({p.clause}, page {p.pdfPage})
                </li>
              ))}
            </ul>
          </div>
        )}
        {result.warnings.length > 0 && (
          <ul className="list-disc pl-5 text-xs text-amber-800" data-testid="area-check-warnings">
            {result.warnings.map((w) => (
              <li key={w.clause}>{w.clause} (page {w.page}): {w.detail}</li>
            ))}
          </ul>
        )}
        {result.notes.map((n) => (
          <p key={n} className="text-xs text-gray-600">{n}</p>
        ))}
        {result.not_checked.length > 0 && (
          <p className="text-xs text-gray-600" data-testid="area-check-not-checked">
            Not checked: {result.not_checked.map((x) => `${x.what} (${x.clause}, page ${x.page})`).join('; ')}.
          </p>
        )}
        <p className="text-xs text-gray-500">
          Measured from public footpath data and NSW planning maps; law as at {result.law_version_date ?? 'an unknown date'}.
        </p>
      </CardContent>
    </Card>
  );
}
