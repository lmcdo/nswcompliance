'use client';

// prior-art-checked: this file IS the extraction of the existing inline GrannyFlatCard
// from app/reports/intelligence-brief/page.tsx (#752) — reuse of the standalone page
// (app/reports/granny-flat/page.tsx) is not viable because it is a full-page multi-step
// funnel (payment, email capture, maplibre map), while the brief needs an embeddable
// card; the confirm request shape below mirrors that page's runConfirm against the
// SAME /api/satellite/granny-flat route rather than re-implementing the API.

// Secondary Dwelling card for the Intelligence Brief — extracted from
// app/reports/intelligence-brief/page.tsx (#752) so the confirm/calculate step
// is independently testable. The detect flow is unchanged: the brief fires the
// same gated /api/satellite/granny-flat route the standalone tool uses (which
// gates on SEPP cl 50/53 BEFORE the GPU scan, so an ineligible lot costs
// nothing), then polls granny_flat_reports and renders a rich, cited card.
//
// New in #752: after a successful detect on a SEPP-eligible lot, the card
// offers the same human structure-selection step as the standalone tool
// (app/reports/granny-flat/page.tsx runConfirm) and, on explicit user action
// only, fires action:'confirm' against the same route to compute the yield
// block (floor area / weekly rent / annual yield / build cost). The confirm
// call never fires automatically — the human step is mandatory by design.
// Three-state throughout: detect failed → no selection step; confirm failed →
// visible error, never zeros.

import { useEffect, useState, type ReactNode } from 'react';
import { resolveGrannyReviewState } from '@/lib/granny-flat-review-state';

// Detected structure row from the granny-flat detection service.
export interface DetectedStructureRow {
  // services.granny_flat.DetectedStructure.index — the identity a
  // per-structure answer is stored against. Optional here because rows
  // written before the field was surfaced do not carry it.
  index?: number;
  matched_prompt?: string;
  area_m2?: number | null;
  is_main_dwelling?: boolean;
}

type GfState =
  | { kind: 'loading' }
  | { kind: 'ineligible'; reason: string; evidence?: string }
  | {
      kind: 'result';
      count: number | null;
      detectionFailed?: boolean;
      detectionWarnings?: string[];
      seppEligible: boolean;
      ineligibleReason?: string;
      lotAreaM2?: number;
      structures?: DetectedStructureRow[];
      detectId?: string;
      samgeoCount?: number | null;
    }
  | { kind: 'error'; message: string };

// Confirm/calculate response fields rendered in the yield block. All money
// fields are nullable at the contract — a null is rendered as "Not available",
// never as a zero.
export interface GfYieldResult {
  granny_flat_buildable?: boolean;
  max_floor_area_m2?: number | null;
  estimated_weekly_rent_aud?: number | null;
  rental_yield_annual_pct?: number | null;
  assumed_build_cost_aud?: number | null;
  confidence?: string | null;
  confidence_reason?: string | null;
  review_state?: string | null;
  review_state_label?: string | null;
  review_state_detail?: string | null;
}

type ConfirmState =
  | { kind: 'idle' }
  | { kind: 'submitting' }
  | { kind: 'done'; result: GfYieldResult }
  | { kind: 'error'; message: string };

function structureLabel(prompt: string): string {
  return prompt
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function Shell({ badge, badgeClass, children }: { badge: string; badgeClass: string; children: ReactNode }) {
  return (
    <div className="relative bg-white rounded-xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_32px_-18px_rgba(15,23,42,0.18)] overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-teal-500 before:via-teal-400/60 before:to-transparent">
      <div className="px-5 py-4 border-b border-slate-200/70 bg-gradient-to-r from-slate-50/90 via-white to-white flex items-center justify-between gap-3">
        <div>
          <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-slate-900 [text-wrap:balance]">Secondary Dwelling</h3>
          <p className="text-xs text-slate-500 mt-0.5">Granny-flat feasibility — buildings on the lot + eligibility</p>
        </div>
        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ring-slate-900/10 ${badgeClass}`}>{badge}</span>
      </div>
      <div className="px-5 py-4 text-sm leading-relaxed">{children}</div>
    </div>
  );
}

function money(v: number | null | undefined): string {
  return v != null ? `$${Math.round(v).toLocaleString('en-AU')}` : 'Not available';
}

// Yield block — the confirm/calculate outputs, labelled as computed estimates.
// The structure list carries its review STATE (what happened), not a grade.
function YieldBlock({ result }: { result: GfYieldResult }) {
  const reviewState = resolveGrannyReviewState(result as unknown as Record<string, unknown>);
  const rows: { label: string; value: string }[] = [
    {
      label: 'Buildable floor area',
      value: result.max_floor_area_m2 != null ? `${Math.round(result.max_floor_area_m2)} m²` : 'Not available',
    },
    {
      label: 'Indicative weekly rent',
      value: result.estimated_weekly_rent_aud != null ? `${money(result.estimated_weekly_rent_aud)}/wk` : 'Not available',
    },
    {
      label: 'Indicative annual yield',
      value: result.rental_yield_annual_pct != null ? `${result.rental_yield_annual_pct}% p.a.` : 'Not available',
    },
    {
      label: 'Assumed build cost',
      value: money(result.assumed_build_cost_aud),
    },
  ];
  return (
    <div className="mt-3 border-t border-slate-100 pt-3" data-testid="gf-yield-block">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400 mb-2">
        Indicative yield — computed from your structure selections
      </p>
      {result.granny_flat_buildable === false && (
        <p className="text-slate-700 mb-2">
          A complying-development secondary dwelling could not be computed for this lot from these selections.
        </p>
      )}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
        {rows.map(({ label, value }) => (
          <div key={label}>
            <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</dt>
            <dd className="mt-0.5 text-slate-900 tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      {/* What happened to the structure list, not a grade. "Confidence:
          medium" told someone whose scan found nothing that we were middlingly
          sure — when nothing had been checked against anything. */}
      <p className="mt-2 text-xs text-slate-500">
        <span className="font-medium text-slate-600">{reviewState.label}</span>
        {' — '}
        {reviewState.detail}
      </p>
      {result.confidence_reason && !reviewState.derived && (
        <p className="mt-1 text-xs text-slate-500">{result.confidence_reason}</p>
      )}
      <p className="mt-2 text-xs text-slate-400">
        Computed estimates from aerial detection, SEPP (Housing) 2021 standards and NSW rental bond data — indicative only, not advice.
      </p>
    </div>
  );
}

export function GrannyFlatBriefCard({ address, active, lotAreaM2 }: { address?: string; active: boolean; lotAreaM2?: number | null }) {
  const [state, setState] = useState<GfState | null>(null);
  const [confirm, setConfirm] = useState<ConfirmState>({ kind: 'idle' });
  // Which detected structures the user says match the aerial view (by array
  // position). Defaults to all detected — the user deselects mismatches.
  const [deselected, setDeselected] = useState<Record<number, boolean>>({});
  const [existingGf, setExistingGf] = useState<boolean | null>(null);

  useEffect(() => {
    if (!active || !address) { setState(null); return; }
    let cancelled = false;
    setState({ kind: 'loading' });
    setConfirm({ kind: 'idle' });
    setDeselected({});
    setExistingGf(null);

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
              detectionFailed: !!o.detection_failed,
              detectionWarnings: Array.isArray(o.warnings) ? (o.warnings as string[]) : [],
              count: (o.confirmed_structure_count as number) ?? (o.samgeo_structure_count as number) ?? null,
              seppEligible: !!o.sepp_eligible,
              ineligibleReason: (o.sepp_ineligible_reason as string) || undefined,
              lotAreaM2: (o.lot_area_m2 as number) || undefined,
              structures: Array.isArray(o.detected_structures)
                ? (o.detected_structures as DetectedStructureRow[])
                : undefined,
              detectId: typeof o.detect_id === 'string' ? o.detect_id : undefined,
              samgeoCount: typeof o.samgeo_structure_count === 'number' ? o.samgeo_structure_count : null,
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
      body: JSON.stringify({ address, action: 'detect', ...(lotAreaM2 != null ? { lot_area_m2: lotAreaM2 } : {}) }),
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
    // lotAreaM2 intentionally in deps: a late-arriving reconciled area re-runs detect with the right figure
  }, [active, address, lotAreaM2]);

  // Explicit user action only — mirrors the standalone tool's runConfirm
  // request shape (app/reports/granny-flat/page.tsx) against the same route.
  const runConfirm = async (detect: Extract<GfState, { kind: 'result' }>) => {
    if (!address || !detect.detectId || confirm.kind === 'submitting') return;
    const structures = detect.structures ?? [];
    const selectedCount = structures.length > 0
      ? structures.filter((_, i) => !deselected[i]).length
      : (detect.count ?? 0);
    // A deselect is a human saying "that is not a separate building" — the
    // judgement, bound to the structure it was made about. It used to
    // collapse into a bare count and the per-structure decision was lost.
    // `index` mirrors detected_structures[].index so the answer joins back to
    // the bbox the person was looking at; fall back to array position for the
    // (older) rows that carry no index field.
    //
    // Only structures the person actually TOUCHED are reported. Everything
    // arrives pre-selected, so emitting an answer for an untouched structure
    // would turn "did not interact" into "kept" — manufacturing the human
    // judgement this whole change exists to stop manufacturing.
    // 'kept', not a building type: this card only asks keep-or-reject, so
    // recording a type here would invent a classification nobody gave.
    const structureTypesPayload = structures
      .map((s, i) => ({ s, i }))
      .filter(({ i }) => i in deselected)
      .map(({ s, i }) => ({
        index: typeof s.index === 'number' ? s.index : i,
        answer: deselected[i] ? 'rejected' : 'kept',
      }));
    // …and 'secondary_detections_classified' is claimed only once every structure has
    // been touched. Clicking Calculate with the defaults untouched is silence,
    // not a judgement. The value is named for what this card can observe:
    // the person went through the detections. It cannot cover a building the
    // scan missed, because there is nothing here to click for one.
    // Only the SECONDARY structures need touching — the detector designates
    // the principal dwelling and the backend's coverage rule ignores it.
    // Requiring it too under-credited a genuine review: a lot with one shed,
    // properly classified, was recorded as machine_default because the
    // preselected main dwelling had not been clicked.
    const secondaryIdx = structures
      .map((s, i) => ({ s, i }))
      .filter(({ s }) => !s.is_main_dwelling)
      .map(({ i }) => i);
    const allTouched = secondaryIdx.length > 0 && secondaryIdx.every((i) => i in deselected);
    const countSource = allTouched ? 'secondary_detections_classified' : 'machine_default';
    setConfirm({ kind: 'submitting' });
    try {
      const res = await fetch('/api/satellite/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address,
          action: 'confirm',
          detect_id: detect.detectId,
          confirmed_structure_count: selectedCount,
          confirmed_count_source: countSource,
          structure_types: structureTypesPayload,
          samgeo_structure_count: detect.samgeoCount ?? null,
          postcode: address.match(/\b(\d{4})\b/)?.[1] || null,
          existing_secondary_dwelling: existingGf,
          main_dwelling_area_m2: structures.find((s) => s.is_main_dwelling)?.area_m2 ?? null,
          // #745 D3: keep the brief's reconciled lot area as the single figure
          ...(lotAreaM2 != null ? { lot_area_m2: lotAreaM2 } : {}),
        }),
      });
      const json = await res.json().catch(() => null);
      if (!res.ok || !json) {
        setConfirm({ kind: 'error', message: json?.error || `The yield calculation did not complete (HTTP ${res.status}).` });
        return;
      }
      setConfirm({ kind: 'done', result: json as GfYieldResult });
    } catch (err: unknown) {
      setConfirm({ kind: 'error', message: err instanceof Error ? err.message : 'The yield calculation did not complete.' });
    }
  };

  if (!active) return <Shell badge="Not run" badgeClass="bg-teal-50 text-teal-700"><span className="text-slate-500">Tick “Include satellite analysis” above and re-run to scan the lot’s buildings and check granny-flat eligibility.</span></Shell>;
  if (!state || state.kind === 'loading') return <Shell badge="Analysing…" badgeClass="bg-slate-100 text-slate-500"><span className="text-slate-500 animate-pulse">Scanning the aerial image for buildings and checking secondary-dwelling eligibility… (up to ~90s)</span></Shell>;
  if (state.kind === 'ineligible') return (
    <Shell badge="Not available here" badgeClass="bg-amber-50 text-amber-700">
      <p className="text-slate-700">{state.reason}</p>
      {state.evidence && <p className="text-slate-500 mt-1">{state.evidence}</p>}
    </Shell>
  );
  if (state.kind === 'error') return <Shell badge="Couldn’t complete" badgeClass="bg-slate-100 text-slate-500"><span className="text-slate-500">{state.message}</span></Shell>;

  // The selection + calculate step is only offered after a SUCCESSFUL detect
  // (three-state: a failed detection has an unknown count, so there is nothing
  // for a human to select against) on a SEPP-eligible lot with a detect_id.
  const canCalculate = !state.detectionFailed && state.seppEligible && !!state.detectId;
  const structures = state.structures ?? [];

  return (
    <Shell badge="Calculated" badgeClass="bg-amber-50 text-amber-800">
      <p className="text-slate-900">
        {state.detectionFailed
          ? <>The building scan did not complete — the building count is <span className="font-medium">unknown, not zero</span>. Confirm the structure count in the Granny Flat tool before relying on it.</>
          : state.count != null
            ? <><span className="font-medium">{state.count}</span> existing building{state.count === 1 ? '' : 's'} detected on the lot from the aerial image.</>
            : 'Building scan complete.'}
      </p>
      <p className="mt-1 text-slate-700">
        {state.seppEligible
          ? <>This lot <span className="font-medium">meets</span> the SEPP (Housing) 2021 secondary-dwelling lot standard{state.lotAreaM2 ? ` (lot ${Math.round(state.lotAreaM2)} m²)` : ''} — a granny flat is a permissible form, subject to the detailed controls.</>
          : (state.ineligibleReason || 'This lot does not meet the SEPP secondary-dwelling lot standard.')}
      </p>

      {!canCalculate ? (
        <>
          {/* Detected structures — display only what the detection service
              returned (AI-classified building type + measured footprint area). */}
          {structures.length > 0 && (
            <ul className="mt-2 text-xs text-slate-500 space-y-0.5">
              {structures.map((st, i) => (
                <li key={`${st.matched_prompt ?? 'structure'}-${i}`} className="tabular-nums">
                  {structureLabel(String(st.matched_prompt ?? 'structure'))}
                  {st.is_main_dwelling ? ' (main dwelling)' : ''}
                  {st.area_m2 != null ? ` — ~${Math.round(st.area_m2)} m² footprint` : ''}
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-slate-400">Confirm the detected building count in the Granny Flat tool before relying on the figure.</p>
        </>
      ) : confirm.kind === 'done' ? (
        <YieldBlock result={confirm.result} />
      ) : (
        <div className="mt-3 border-t border-slate-100 pt-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400 mb-1">Indicative yield</p>
          {structures.length > 0 ? (
            <>
              <p className="text-xs text-slate-500 mb-2">
                Select the structures that match the aerial view — deselect anything that is not a building on this lot.
              </p>
              <ul className="space-y-1.5 mb-3">
                {structures.map((st, i) => {
                  const selected = !deselected[i];
                  return (
                    <li key={`${st.matched_prompt ?? 'structure'}-${i}`}>
                      <button
                        type="button"
                        aria-pressed={selected}
                        onClick={() => setDeselected((prev) => ({ ...prev, [i]: !prev[i] }))}
                        className={`w-full text-left px-3 py-2 rounded-lg border text-xs transition-colors tabular-nums ${
                          selected ? 'border-teal-300 bg-teal-50/60 text-slate-700' : 'border-slate-200 bg-white text-slate-400'
                        }`}
                      >
                        <span className={`inline-block w-3.5 text-center mr-1.5 font-bold ${selected ? 'text-teal-600' : 'text-slate-300'}`}>{selected ? '✓' : '–'}</span>
                        {structureLabel(String(st.matched_prompt ?? 'structure'))}
                        {st.is_main_dwelling ? ' (main dwelling)' : ''}
                        {st.area_m2 != null ? ` — ~${Math.round(st.area_m2)} m² footprint` : ' — size unknown'}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <p className="text-xs text-slate-500 mb-2">
              No buildings were detected on the aerial image — the calculation will run on that basis.
            </p>
          )}
          <div className="mb-3">
            <p className="text-xs text-slate-500 mb-1.5">
              {structures.length > 0
                ? 'Is one of these already a secondary dwelling (granny flat)?'
                : 'Is there already a secondary dwelling (granny flat) on this lot?'}
            </p>
            <div className="flex gap-1.5">
              {([
                { label: 'Yes', value: true },
                { label: 'No', value: false },
                { label: 'Not sure', value: null },
              ] as { label: string; value: boolean | null }[]).map(({ label, value }) => (
                <button
                  key={label}
                  type="button"
                  aria-pressed={existingGf === value}
                  onClick={() => setExistingGf(value)}
                  className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                    existingGf === value ? 'bg-teal-600 text-white border-teal-600' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          {confirm.kind === 'error' && (
            <p className="mb-2 text-xs text-red-600" role="alert">
              The yield calculation did not complete — {confirm.message} No figures are shown; adjust the selections and try again.
            </p>
          )}
          <button
            type="button"
            onClick={() => runConfirm(state)}
            disabled={confirm.kind === 'submitting'}
            className="px-4 py-2 bg-teal-600 text-white text-xs font-medium rounded-lg hover:bg-teal-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {confirm.kind === 'submitting' ? 'Calculating…' : 'Calculate indicative yield'}
          </button>
          <p className="mt-2 text-xs text-slate-400">
            Runs only when you choose to — the figures are computed from your selections, SEPP (Housing) 2021 standards and NSW rental bond data.
          </p>
        </div>
      )}
    </Shell>
  );
}
