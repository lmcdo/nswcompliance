'use client';

import { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useRouter } from 'next/navigation';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { posthog } from '@/components/providers/PostHogProvider';
import { SoftwareAppJsonLd } from '@/lib/json-ld';
import { NSW_STANDARD_ZONES } from '@/lib/regulatory-constants';
import { resolveGrannyReviewState } from '@/lib/granny-flat-review-state';
import Map, { Source, Layer, NavigationControl } from 'react-map-gl/maplibre';
import type { StyleSpecification } from 'maplibre-gl';

interface DetectedStructure {
  index: number;
  area_m2: number | null;
  bbox_pixel: number[];
  matched_prompt: string;
  is_main_dwelling: boolean;
}

interface DetectResult {
  detect_id: string;
  address: string;
  lat: number;
  lng: number;
  prop_id: string;
  lot_area_m2: number | null;
  sepp_eligible: boolean;
  sepp_ineligible_reason: string | null;
  detected_structures: DetectedStructure[];
  samgeo_structure_count: number;
  samgeo_validated: boolean;
  confirmation_required: boolean;
  tile_licence: string;
  tile_b64?: string;
  tile_width?: number;
  tile_height?: number;
  tile_bbox?: { min_lat: number; max_lat: number; min_lng: number; max_lng: number };
  lot_polygon_wgs84?: number[][][]; // [[lng, lat], ...] rings in WGS84
}

interface EplanningApplication {
  type: 'DA' | 'CDC';
  development_type: string;
  status: string;
  lodgement_date: string | null;
  reference: string;
}

interface EplanningHistory {
  found: boolean;
  applications: EplanningApplication[];
  source_note: string;
  error: 'timeout' | 'unavailable' | null;
}

interface ConfirmResult {
  report_id: string;
  address: string;
  granny_flat_buildable: boolean;
  max_floor_area_m2: number;
  estimated_weekly_rent_aud: number | null;
  rental_yield_annual_pct: number | null;
  assumed_build_cost_aud: number | null;
  confidence: string;
  confidence_reason: string;
  // What actually happened to the structure list. Optional: a report loaded
  // from a pre-2026-08-06 row has no stored state and is derived instead.
  review_state?: string;
  review_state_label?: string;
  review_state_detail?: string;
  detected_structures?: unknown[];
  samgeo_structure_count?: number | null;
  data_sources: string[];
  warnings: string[];
  eplanning_history?: EplanningHistory;
  // Present when loading a completed report directly (no detectResult available)
  lat?: number;
  lng?: number;
  lga_name?: string;
  tile_b64?: string;
}

type PageState = 'idle' | 'detecting' | 'confirming' | 'complete' | 'error' | 'ineligible';

// DQ-30 (.claude/DATA_QUALITY_TRACKER.md): consolidated onto
// NSW_STANDARD_ZONES.RESIDENTIAL — was independently declared in 4 files.
const ELIGIBLE_ZONE_PREFIXES = NSW_STANDARD_ZONES.RESIDENTIAL as readonly string[];

function deriveWhatToChange(reason: string | null, lotArea: number | null): string {
  if (lotArea != null && lotArea < 450) {
    const shortfall = Math.round(450 - lotArea);
    return `A boundary adjustment of ${shortfall} m² could unlock CDC eligibility. A DA pathway may also be available at council's discretion — a certifier or town planner can advise.`;
  }
  if (reason?.toLowerCase().includes('heritage')) {
    return 'Heritage exclusions apply to the CDC pathway only. A DA pathway remains available — contact a heritage-experienced town planner.';
  }
  if (reason?.toLowerCase().includes('flood')) {
    return 'Flood control lot exclusions apply to the CDC pathway only. A DA with a flood risk management report may still be available — consult a hydraulic engineer.';
  }
  if (reason?.toLowerCase().includes('zone') || reason?.toLowerCase().includes('zoning')) {
    return 'Zoning restrictions may be fixed unless a planning proposal is lodged. Check the applicable LEP with a town planner.';
  }
  return "A DA pathway may still be available at council's discretion — a town planner or certifier can advise on your options.";
}

// The high/medium/low grade is no longer shown. It graded a lot the scan
// never checked as "medium", which reads as a middling amount of confidence
// rather than an unverified result. Reports now say what happened instead —
// see lib/granny-flat-review-state.ts.

function GrannyFlatPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const isPaid = searchParams?.get('payment') === 'success';
  const [paramsChecked, setParamsChecked] = useState(false);
  const [address, setAddress] = useState('');
  const [postcode, setPostcode] = useState(''); // from Google Places address_components
  const [inputAddress, setInputAddress] = useState('');
  const [ineligibleEvidence, setIneligibleEvidence] = useState('');
  const [ineligibleEvidenceLabel, setIneligibleEvidenceLabel] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [detectResult, setDetectResult] = useState<DetectResult | null>(null);
  const [confirmedCount, setConfirmedCount] = useState(1);
  const [finalResult, setFinalResult] = useState<ConfirmResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [calcBuildCost, setCalcBuildCost] = useState(2500);
  const [calcWeeklyRent, setCalcWeeklyRent] = useState(450);
  const [email, setEmail] = useState('');
  const [emailSubmitted, setEmailSubmitted] = useState(false);      // confirming-state resume-link capture
  const [reportEmailCaptured, setReportEmailCaptured] = useState(false); // post-result CTA capture
  const [existingSecondaryDwelling, setExistingSecondaryDwelling] = useState<boolean | null>(null);
  // Per-structure answers. These used to live inside ConfirmationPanel and were
  // thrown away when it unmounted — the answer a person gave about each
  // building never reached the server. Lifted here so runConfirm can send them.
  const [structureTypes, setStructureTypes] = useState<Record<number, StructureTypeAnswer>>({});

  // Named step progress — driven by elapsed time during detect phase only
  const DETECT_STEPS = [
    { label: 'Resolving address with NSW Planning Portal', ms: 0 },
    { label: 'Retrieving aerial imagery', ms: 4000 },
    { label: 'Uploading tile to GPU inference engine', ms: 14000 },
    { label: 'Running AI structure segmentation', ms: 20000, estimate: '~60s' as const },
    { label: 'Filtering detections against lot boundary', ms: 82000 },
    { label: 'Cross-referencing SEPP Housing 2021 rules', ms: 92000 },
  ];
  const [detectStep, setDetectStep] = useState(0);
  const stepTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    // Only run step advancement during the detect phase (not confirm)
    if (state === 'detecting' && detectResult == null) {
      setDetectStep(0);
      stepTimersRef.current.forEach(clearTimeout);
      stepTimersRef.current = DETECT_STEPS.slice(1).map((s, i) =>
        setTimeout(() => setDetectStep(i + 1), s.ms)
      );
    } else {
      stepTimersRef.current.forEach(clearTimeout);
      stepTimersRef.current = [];
      if (state !== 'detecting') setDetectStep(0);
    }
    return () => { stepTimersRef.current.forEach(clearTimeout); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, detectResult]);

  // Resume poll from email link (?jobId=&address=)
  const resumePoll = useCallback(async (jobId: string, addr: string) => {
    setInputAddress(addr);
    setAddress(addr);
    setState('detecting');
    setDetectResult(null);
    setFinalResult(null);
    setErrorMsg('');

    const poll = async (attempts = 0): Promise<void> => {
      if (attempts >= 90) throw new Error('Detection timed out — please try again.');
      const res = await fetch(`/api/satellite/granny-flat?jobId=${jobId}`);
      const json = await res.json();
      if (json.status === 'error') throw new Error(json.error || 'Detection failed.');
      if (json.status === 'completed') {
        // Report already confirmed — jump straight to result
        setFinalResult(json.data);
        setState('complete');
        return;
      }
      if (json.status === 'detected') {
        const d = json.data;
        setDetectResult(d);
        setConfirmedCount(d.samgeo_validated && d.detected_structures?.length > 0 ? d.detected_structures.length : 1);
        setStructureTypes({});
        setState('confirming');
        return;
      }
      await new Promise((r) => setTimeout(r, 2000));
      return poll(attempts + 1);
    };

    try { await poll(); }
    catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  }, []);

  useEffect(() => {
    const jobId = searchParams?.get('jobId');
    const addr = searchParams?.get('address');
    const payment = searchParams?.get('payment');
    const emailParam = searchParams?.get('email');
    if (!jobId && payment !== 'success') {
      router.replace('/granny-flat');
      return;
    }
    setParamsChecked(true);
    // Restore email from success_url so auto-confirm can send results email
    if (emailParam) setEmail(decodeURIComponent(emailParam));
    if (jobId && addr) resumePoll(jobId, addr);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Confirming-state capture: "get result by email so you can close this tab"
  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    try {
      await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          address: detectResult?.address ?? inputAddress,
          eligible: null,
        }),
      });
    } catch { /* silent */ }
    posthog?.capture('granny_flat_email_capture', { address: detectResult?.address ?? inputAddress, stage: 'confirming' });
    setEmailSubmitted(true);
  };

  // Post-result capture: shown after pass/fail result is fully displayed
  const handleReportEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    try {
      await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          address: finalResult?.address ?? detectResult?.address ?? inputAddress,
          eligible: finalResult?.granny_flat_buildable ?? null,
        }),
      });
    } catch { /* silent */ }
    posthog?.capture('granny_flat_email_capture', {
      address: finalResult?.address ?? detectResult?.address ?? inputAddress,
      eligible: finalResult?.granny_flat_buildable ?? null,
      stage: 'post_result',
    });
    setReportEmailCaptured(true);
  };

  const handleDetect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setInputAddress(address.trim());
    setState('detecting');
    setDetectResult(null);
    setFinalResult(null);
    setErrorMsg('');
    setExistingSecondaryDwelling(null);
    posthog?.capture('granny_flat_detect_start', { address: address.trim() });

    try {
      // Step 1: enqueue detect job (returns immediately with jobId)
      const res = await fetch('/api/satellite/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, action: 'detect', notification_email: email.trim() || undefined }),
      });
      const json = await res.json();
      if (!res.ok) {
        if (json.ineligible) {
          posthog?.capture('granny_flat_ineligible', { address: address.trim(), reason: json.evidence_label ?? json.error });
          setErrorMsg(json.error ?? 'This property is not eligible.');
          setIneligibleEvidence(json.evidence ?? '');
          setIneligibleEvidenceLabel(json.evidence_label ?? '');
          setState('ineligible');
          return;
        }
        throw new Error(json.error || 'Detection failed');
      }

      const jobId: string = json.jobId;

      // If email was provided at idle state, register for resume-link delivery
      // NOTE: does NOT set emailSubmitted — that's reserved for the confirming-state strip
      // so the post-result ReportUnlockCTA always shows explicitly for the user to opt in
      if (email.trim()) {
        fetch('/api/canibuildit/lead', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email.trim(), address: address.trim(), eligible: null }),
        }).catch(() => {});
      }

      // Step 2: poll until detect result is written to DB (max 3 min)
      const poll = async (attempts = 0): Promise<void> => {
        if (attempts >= 90) {
          throw new Error('Detection timed out after 3 minutes. Please try again.');
        }
        const pollRes = await fetch(`/api/satellite/granny-flat?jobId=${jobId}`);
        const pollJson = await pollRes.json();

        if (pollJson.status === 'error') {
          throw new Error(pollJson.error || 'Detection failed — please try again.');
        }
        if (pollJson.status === 'detected') {
          const detectData = pollJson.data;
          posthog?.capture('granny_flat_detect_complete', {
            address: detectData.address,
            structure_count: detectData.detected_structures?.length ?? 0,
            samgeo_validated: detectData.samgeo_validated,
          });
          setDetectResult(detectData);
          if (detectData.samgeo_validated && detectData.detected_structures?.length > 0) {
            setConfirmedCount(detectData.detected_structures.length);
          } else {
            // Fallback default when detection found nothing. NOT a human
            // figure — both historical "user disagreed with the detector"
            // rows in the DB were this line, not a person.
            setConfirmedCount(1);
          }
          setStructureTypes({});   // answers belong to the detect run they were given for
          setState('confirming');
          return;
        }

        // Still pending — try again in 2s
        await new Promise((r) => setTimeout(r, 2000));
        return poll(attempts + 1);
      };

      await poll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      posthog?.capture('granny_flat_detect_error', { address: address.trim(), error: msg });
      setErrorMsg(msg);
      setState('error');
    }
  };

  const runConfirm = useCallback(async (
    detect: DetectResult,
    count: number,
    existingGF: boolean | null,
    pc: string,
    notifEmail: string,
    answers: Record<number, StructureTypeAnswer> = {},
  ) => {
    setState('detecting'); // reuse spinner
    setFinalResult(null);
    setErrorMsg('');

    // Provenance of the count, as a transmitted field rather than an
    // assumption at the far end. 'secondary_detections_classified' is claimed only when
    // a person answered for EVERY secondary structure they were shown; a
    // partial pass leaves it as the detector's own figure. Note what it does
    // NOT claim: this screen shows only what the detector found, so a person
    // cannot report a structure it missed, and the value is named for
    // classification coverage rather than for verifying the total.
    //
    // `count` arrives already adjusted — ConfirmationPanel.handleStructureType
    // is what moves it. Do not subtract again here.
    const secondary = detect.detected_structures.filter((s) => !s.is_main_dwelling);
    const allAnswered = secondary.length > 0 && secondary.every((s) => s.index in answers);
    const countSource = allAnswered ? 'secondary_detections_classified' : 'machine_default';
    const structureTypesPayload = secondary
      .filter((s) => s.index in answers)
      .map((s) => ({ index: s.index, answer: answers[s.index] }));

    posthog?.capture('granny_flat_confirm', {
      address: detect.address,
      confirmed_count: count,
      detected_count: detect.samgeo_structure_count,
      count_source: countSource,
      structures_answered: structureTypesPayload.length,
    });

    try {
      const res = await fetch('/api/satellite/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: detect.address,
          action: 'confirm',
          detect_id: detect.detect_id,
          confirmed_structure_count: count,
          confirmed_count_source: countSource,
          structure_types: structureTypesPayload,
          samgeo_structure_count: detect.samgeo_structure_count,
          postcode: pc || detect.address.match(/\b(\d{4})\b/)?.[1] || null,
          existing_secondary_dwelling: existingGF,
          main_dwelling_area_m2: detect.detected_structures.find(s => s.is_main_dwelling)?.area_m2 ?? null,
          ...(notifEmail.trim() ? { notification_email: notifEmail.trim() } : {}),
        }),
      });

      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Calculation failed');

      posthog?.capture('granny_flat_result', {
        address: detect.address,
        eligible: json.granny_flat_buildable,
        max_floor_area_m2: json.max_floor_area_m2 ?? null,
      });
      setFinalResult(json);
      setState('complete');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      posthog?.capture('granny_flat_confirm_error', { address: detect.address, error: msg });
      setErrorMsg(msg);
      setState('error');
    }
  }, []);

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detectResult) return;
    await runConfirm(detectResult, confirmedCount, existingSecondaryDwelling, postcode, email, structureTypes);
  };


  const isRunning = state === 'detecting';

  if (!paramsChecked) return null;

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 leading-tight">
          Could this property earn an extra $280–$340/week?
        </h1>
        <p className="mt-2 text-gray-500">
          Granny flat eligibility check for any NSW address — aerial structure detection, SEPP Housing 2021 analysis, and rental yield estimate.
        </p>
      </div>

      {/* Step 1: address entry — stays visible and disabled during detection */}
      {(state === 'idle' || state === 'error' || state === 'detecting') && (
        <form onSubmit={handleDetect} className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Property address</label>
            <AddressAutocomplete
              value={address}
              onChange={setAddress}
              onSelect={(addr, lat, lng, pc) => { setAddress(addr); if (pc) setPostcode(pc); }}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
              disabled={isRunning}
            />
          </div>
          {state === 'idle' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email <span className="text-gray-400 font-normal">(optional — get result by email so you can close this tab)</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
            </div>
          )}
          {state === 'error' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              {errorMsg}
            </div>
          )}

          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={isRunning || !address.trim()}
              className="flex items-center gap-2 px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {isRunning && (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              )}
              {isRunning ? 'Detecting structures...' : 'Detect structures'}
            </button>
          </div>
          {state === 'detecting' && detectResult === null && (
            <div className="mt-3 space-y-2">
              {DETECT_STEPS.map((step, i) => {
                const done = i < detectStep;
                const active = i === detectStep;
                return (
                  <div key={step.label} className="flex items-center gap-2.5 text-xs">
                    {done ? (
                      <svg className="w-3.5 h-3.5 text-teal-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                    ) : active ? (
                      <span className="w-3.5 h-3.5 shrink-0 border-2 border-teal-500 border-t-transparent rounded-full animate-spin inline-block" />
                    ) : (
                      <span className="w-3.5 h-3.5 shrink-0 rounded-full border border-gray-200 inline-block" />
                    )}
                    <span className={done ? 'text-gray-400 line-through' : active ? 'text-gray-700 font-medium' : 'text-gray-300'}>
                      {step.label}
                      {'estimate' in step && active && (
                        <span className="ml-1.5 font-normal text-gray-400">{(step as { estimate: string }).estimate}</span>
                      )}
                    </span>
                  </div>
                );
              })}
              <p className="text-xs text-gray-400 pt-1">
                Takes 1–3 minutes — we&apos;re running live satellite imagery through an ML model and cross-referencing your lot against the NSW Planning Portal in real time. A town planner would take days to do this manually.
              </p>
            </div>
          )}
          {state === 'detecting' && detectResult !== null && (
            <p className="text-xs text-gray-400 mt-2">Calculating eligibility and yield estimate…</p>
          )}
        </form>
      )}

      {/* Ineligible — permanent result, search another at top */}
      {state === 'ineligible' && (
        <>
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          <div className="p-6 flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-gray-900">{inputAddress}</p>
              <button
                type="button"
                onClick={() => { setState('idle'); setErrorMsg(''); setIneligibleEvidence(''); setIneligibleEvidenceLabel(''); setAddress(''); setPostcode(''); setReportEmailCaptured(false); }}
                className="text-xs text-teal-600 hover:text-teal-700 underline mt-1"
              >
                Search another address
              </button>
            </div>
            <span className="shrink-0 text-xs font-medium px-2 py-1 rounded-full bg-red-100 text-red-800">
              Not eligible
            </span>
          </div>
          <div className="p-6">
            <p className="text-sm text-gray-700">{errorMsg}</p>
          </div>
          {ineligibleEvidence && (
            <div className="px-6 py-3 bg-gray-50 border-t border-gray-100">
              <p className="text-xs text-gray-400 mb-0.5">{ineligibleEvidenceLabel || 'Source'}</p>
              <p className="text-xs font-mono text-gray-600">{ineligibleEvidence}</p>
            </div>
          )}
          <div className="p-6 border-t border-gray-100">
            <h3 className="font-semibold text-gray-900 mb-1">What could change this?</h3>
            <p className="text-sm text-gray-500 mb-4">
              {deriveWhatToChange(errorMsg, null)}
            </p>
            {!reportEmailCaptured ? (
              <form onSubmit={handleReportEmailSubmit} className="flex gap-2">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                />
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors whitespace-nowrap"
                >
                  Notify me
                </button>
              </form>
            ) : (
              <p className="text-sm text-teal-700 font-medium">Got it — we&apos;ll be in touch if anything changes for this address.</p>
            )}
          </div>
        </div>
        {/* "Eligible properties nearby" removed 2026-08-06. It rendered only
            on the INELIGIBLE result: a customer just told their lot fails was
            shown named third-party addresses with a weekly rent figure each,
            called "DA precedents". None had been through a DA, the rent was a
            postcode median presented per-address, and the eligibility claim
            was about someone else's land. No purpose survived: the reasons a
            lot fails (area, heritage, flood, zone) are facts about that lot,
            which a neighbour passing cannot change. See
            ~/.claude/plans/ce-conveyancer-brief-consolidation-2026-07.md §6 —
            named properties with money attached imply a valuation (ACL s18). */}
        <CrossSellCards buildable={false} address={inputAddress} />
        </>
      )}

      {/* Step 2: confirmation */}
      {state === 'confirming' && detectResult && (
        <>
          {isPaid && (
            <div className="mb-4 rounded-xl border border-teal-200 bg-teal-50 px-5 py-3 flex items-center gap-3">
              <span className="text-teal-600 font-bold text-lg">✓</span>
              <div>
                <p className="text-sm font-semibold text-teal-900">Payment confirmed — generating your eligibility screening report</p>
                <p className="text-xs text-teal-700">Our AI detected structures on your lot. Confirm the count below to complete your analysis.</p>
              </div>
            </div>
          )}
          <ConfirmationPanel
            detectResult={detectResult}
            inputAddress={inputAddress}
            confirmedCount={confirmedCount}
            onCountChange={setConfirmedCount}
            structureTypes={structureTypes}
            onStructureTypesChange={setStructureTypes}
            existingSecondaryDwelling={existingSecondaryDwelling}
            onExistingSecondaryDwellingChange={setExistingSecondaryDwelling}
            onConfirm={handleConfirm}
            onBack={() => { setState('idle'); setDetectResult(null); setPostcode(''); setExistingSecondaryDwelling(null); setStructureTypes({}); }}
          />
          {!emailSubmitted ? (
            <form
              onSubmit={handleEmailSubmit}
              className="flex items-center gap-2 mt-3 p-4 rounded-xl border border-gray-100 bg-gray-50"
            >
              <p className="text-xs text-gray-500 shrink-0 mr-1">Get result by email instead:</p>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="flex-1 min-w-0 px-3 py-1.5 rounded-lg border border-gray-200 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
              />
              <button
                type="submit"
                className="shrink-0 px-3 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-800 transition-colors"
              >
                Send
              </button>
            </form>
          ) : (
            <p className="text-xs text-teal-700 mt-3 px-1">
              Got it — result on its way to {email}.
            </p>
          )}
        </>
      )}

      {/* Step 3: result */}
      {state === 'complete' && finalResult && (
        <div className="space-y-5">
          <ResultCard result={finalResult} inputAddress={inputAddress} onReset={() => { setState('idle'); setDetectResult(null); setFinalResult(null); setAddress(''); setPostcode(''); setEmail(''); setEmailSubmitted(false); setReportEmailCaptured(false); setExistingSecondaryDwelling(null); window.scrollTo({ top: 0, behavior: 'smooth' }); }} />

          {/* Satellite image + structure bounding boxes */}
          {detectResult ? (
            <StructureMap
              lat={detectResult.lat}
              lng={detectResult.lng}
              tile_bbox={detectResult.tile_bbox}
              tile_width={detectResult.tile_width}
              tile_height={detectResult.tile_height}
              structures={detectResult.detected_structures}
              lot_polygon_wgs84={detectResult.lot_polygon_wgs84}
              licence={detectResult.tile_licence}
            />
          ) : finalResult.lat != null && finalResult.lng != null ? (
            <StructureMap
              lat={finalResult.lat}
              lng={finalResult.lng}
              structures={[]}
              licence="NSW Government — Six Maps LPI Imagery (CC-BY 4.0)"
            />
          ) : null}
          {/* Check another address — shown immediately after result, before other content */}
          <div className="text-center">
            <button
              onClick={() => { setState('idle'); setDetectResult(null); setFinalResult(null); setAddress(''); setPostcode(''); setEmail(''); setEmailSubmitted(false); setReportEmailCaptured(false); setExistingSecondaryDwelling(null); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              className="px-5 py-2.5 bg-white text-gray-600 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
            >
              Check another address
            </button>
          </div>
          {isPaid ? (
            <PaidDownloadCTA reportId={finalResult.report_id} address={finalResult.address ?? inputAddress} />
          ) : (
            <ReportUnlockCTA
              buildable={finalResult.granny_flat_buildable}
              sepp_ineligible_reason={detectResult?.sepp_ineligible_reason ?? null}
              lot_area_m2={detectResult?.lot_area_m2 ?? null}
              email={email}
              setEmail={setEmail}
              emailCaptured={reportEmailCaptured}
              onEmailSubmit={handleReportEmailSubmit}
              jobId={detectResult?.detect_id ?? ''}
              address={finalResult.address ?? inputAddress}
            />
          )}
          <YieldCalculator
            maxFloorAreaM2={finalResult.max_floor_area_m2}
            buildCost={calcBuildCost}
            weeklyRent={calcWeeklyRent}
            onBuildCostChange={setCalcBuildCost}
            onWeeklyRentChange={setCalcWeeklyRent}
          />
          <CrossSellCards
            buildable={finalResult.granny_flat_buildable}
            ineligibleReason={finalResult.granny_flat_buildable ? null : (detectResult?.sepp_ineligible_reason ?? null)}
            address={finalResult.address ?? inputAddress}
          />
        </div>
      )}

      {/* FAQs — always shown below the tool */}
      <GrannyFlatFAQs />
    </div>
  );
}

const SIX_MAPS_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    sixmaps: {
      type: 'raster',
      tiles: ['https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      attribution: '&copy; NSW Government — Six Maps LPI Imagery (CC BY 4.0)',
      maxzoom: 20,
    },
  },
  layers: [{ id: 'sixmaps-tiles', type: 'raster', source: 'sixmaps' }],
};

/** Convert a pixel bbox to a GeoJSON polygon using the tile's geographic bounds. */
function bboxToGeoJSON(
  bbox_pixel: number[],
  tile_bbox: { min_lat: number; max_lat: number; min_lng: number; max_lng: number },
  tile_w: number,
  tile_h: number,
): GeoJSON.Feature {
  const [px0, py0, px1, py1] = bbox_pixel;
  const lngAt = (px: number) => tile_bbox.min_lng + (px / tile_w) * (tile_bbox.max_lng - tile_bbox.min_lng);
  const latAt = (py: number) => tile_bbox.max_lat - (py / tile_h) * (tile_bbox.max_lat - tile_bbox.min_lat);
  return {
    type: 'Feature',
    properties: {},
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [lngAt(px0), latAt(py0)],
        [lngAt(px1), latAt(py0)],
        [lngAt(px1), latAt(py1)],
        [lngAt(px0), latAt(py1)],
        [lngAt(px0), latAt(py0)],
      ]],
    },
  };
}

function StructureMap({
  lat,
  lng,
  tile_bbox,
  tile_width,
  tile_height,
  structures,
  lot_polygon_wgs84,
  licence,
}: {
  lat: number;
  lng: number;
  tile_bbox?: { min_lat: number; max_lat: number; min_lng: number; max_lng: number };
  tile_width?: number;
  tile_height?: number;
  structures: DetectedStructure[];
  lot_polygon_wgs84?: number[][][];
  licence: string;
}) {
  const tw = tile_width ?? 512;
  const th = tile_height ?? 512;

  const mainFeatures: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };
  const otherFeatures: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };

  if (tile_bbox) {
    for (const s of structures) {
      const feat = bboxToGeoJSON(s.bbox_pixel, tile_bbox, tw, th);
      if (s.is_main_dwelling) mainFeatures.features.push(feat);
      else otherFeatures.features.push(feat);
    }
  }

  const lotFeature: GeoJSON.FeatureCollection | null = lot_polygon_wgs84
    ? {
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          properties: {},
          geometry: { type: 'Polygon', coordinates: lot_polygon_wgs84 },
        }],
      }
    : null;

  return (
    <div className="mb-4">
      <div className="rounded-lg overflow-hidden border border-gray-200" style={{ height: 380 }}>
        <Map
          initialViewState={{ latitude: lat, longitude: lng, zoom: 19 }}
          mapStyle={SIX_MAPS_STYLE}
          attributionControl={false}
        >
          <NavigationControl position="top-right" showCompass showZoom />
          {lotFeature && (
            <Source id="lot-boundary" type="geojson" data={lotFeature}>
              <Layer id="lot-boundary-line" type="line" paint={{ 'line-color': '#14b8a6', 'line-width': 2.5 }} />
            </Source>
          )}
          {tile_bbox && (
            <>
              <Source id="struct-main" type="geojson" data={mainFeatures}>
                <Layer id="struct-main-fill" type="fill" paint={{ 'fill-color': '#ef4444', 'fill-opacity': 0.15 }} />
                <Layer id="struct-main-line" type="line" paint={{ 'line-color': '#ef4444', 'line-width': 2 }} />
              </Source>
              <Source id="struct-other" type="geojson" data={otherFeatures}>
                <Layer id="struct-other-fill" type="fill" paint={{ 'fill-color': '#facc15', 'fill-opacity': 0.15 }} />
                <Layer id="struct-other-line" type="line" paint={{ 'line-color': '#facc15', 'line-width': 2 }} />
              </Source>
            </>
          )}
        </Map>
      </div>
      <p className="text-xs text-gray-400 mt-1">{licence}</p>
    </div>
  );
}

function YieldCalculator({
  maxFloorAreaM2,
  buildCost,
  weeklyRent,
  onBuildCostChange,
  onWeeklyRentChange,
}: {
  maxFloorAreaM2: number;
  buildCost: number;
  weeklyRent: number;
  onBuildCostChange: (v: number) => void;
  onWeeklyRentChange: (v: number) => void;
}) {
  const totalCost = buildCost * maxFloorAreaM2;
  const annualRent = weeklyRent * 52;
  const grossYield = (annualRent / totalCost * 100).toFixed(1);
  const payback = (totalCost / annualRent).toFixed(1);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Build &amp; profit calculator</p>
      <div className="grid grid-cols-2 gap-5 mb-5">
        <div>
          <label className="block text-xs text-gray-500 mb-2">Build cost per m²</label>
          <input
            type="range" min={1800} max={4500} step={100}
            value={buildCost}
            onChange={(e) => onBuildCostChange(Number(e.target.value))}
            className="w-full accent-teal-600"
          />
          <span className="text-sm font-medium text-gray-700">${buildCost.toLocaleString()}/m²</span>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-2">Weekly rent</label>
          <input
            type="range" min={250} max={750} step={25}
            value={weeklyRent}
            onChange={(e) => onWeeklyRentChange(Number(e.target.value))}
            className="w-full accent-teal-600"
          />
          <span className="text-sm font-medium text-gray-700">${weeklyRent}/wk</span>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-3 bg-gray-50 rounded-lg p-4">
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Build cost</p>
          <p className="text-base font-semibold text-gray-900">${(totalCost / 1000).toFixed(0)}k</p>
          <p className="text-xs text-gray-400">{maxFloorAreaM2} m² CDC max</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Annual rent</p>
          <p className="text-base font-semibold text-gray-900">${annualRent.toLocaleString()}</p>
          <p className="text-xs text-gray-400">gross</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Gross yield</p>
          <p className="text-base font-semibold text-teal-700">{grossYield}%</p>
          <p className="text-xs text-gray-400">p.a.</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Payback</p>
          <p className="text-base font-semibold text-gray-900">{payback} yrs</p>
          <p className="text-xs text-gray-400">undiscounted</p>
        </div>
      </div>
      <p className="text-xs text-gray-400 mt-3">
        Illustrative only. Excludes DA/CDC fees, finance, vacancy, and maintenance. Verify rent against NSW Fair Trading bond data.
      </p>
    </div>
  );
}

const GRANNY_FLAT_FAQS = [
  {
    q: 'What is the minimum lot size for a granny flat in NSW?',
    a: 'Under SEPP Housing 2021 (cl 53), a secondary dwelling approved as complying development requires a minimum site area of 450 m². A DA pathway may be available on smaller lots at council\'s discretion, subject to zone permissibility.',
  },
  {
    q: 'What is the maximum size of a granny flat under SEPP Housing 2021?',
    a: 'The maximum floor area for a secondary dwelling approved as complying development is 60 m² (SEPP Housing 2021 cl 4.18). A DA pathway allows larger floor areas subject to council DCP controls — typically up to 20–25% of the principal dwelling\'s floor area.',
  },
  {
    q: 'Do I need a DA or CDC to build a granny flat?',
    a: 'If the lot meets all SEPP Housing 2021 requirements (area, zoning, no heritage/flood/biodiversity exclusions), you can lodge a CDC — which is cheaper and faster than a DA. A CDC is approved by a private certifier in about 20 days. A DA goes to council and typically takes 60–90 days.',
  },
  {
    q: 'Can a granny flat be rented to anyone?',
    a: 'Yes. As of 2023, NSW removed the requirement that secondary dwellings be occupied by a family member. You can rent to any tenant at market rent.',
  },
  {
    q: 'What setbacks apply to a granny flat under the CDC pathway?',
    a: 'Under SEPP Housing 2021 Schedule 3 Subdivision 4: rear setback minimum 3 m, side setbacks 0.9 m for the first 8 m height and 1.5 m above that, minimum 3 m separation from the principal dwelling. Your council\'s DCP may impose stricter controls on the DA pathway.',
  },
  {
    q: 'Why does this tool use aerial imagery to detect structures?',
    a: 'SEPP Housing 2021 requires at most one secondary dwelling per lot. By detecting existing roofed structures on 10 cm NSW SIX Maps aerial imagery, this tool provides a buildability estimate that accounts for existing structures — garages, sheds, and ancillary buildings all affect the available building envelope. Aerial detection is indicative and may not identify all structures.',
  },
  {
    q: 'What does the yield calculator assume?',
    a: 'The calculator uses the actual CDC maximum floor area for this property (up to 60 m²), your selected build cost per m², and your selected weekly rent. Gross yield is annual rent divided by build cost. It excludes DA/CDC fees, finance costs, vacancy, and ongoing maintenance. Net yields are typically 1–2% lower.',
  },
];

function GrannyFlatFAQs() {
  return (
    <div className="mt-12 space-y-5 pb-12">
      <h2 className="text-xl font-semibold text-gray-900">Granny flats in NSW — common questions</h2>
      {GRANNY_FLAT_FAQS.map((faq, i) => (
        <div key={i} className="border-b border-gray-100 pb-4">
          <p className="font-medium text-gray-900 text-sm">{faq.q}</p>
          <p className="text-sm text-gray-500 mt-1">{faq.a}</p>
        </div>
      ))}

      {/* Legislative basis — trust references matching GrannyFlatTool */}
      <div className="text-xs text-gray-400 pt-4 space-y-1.5">
        <p className="font-medium text-gray-500">Legislative basis</p>
        <p><span className="text-gray-500">Lot area</span> — SEPP (Housing) 2021 cl 53(2)(a): detached secondary dwelling minimum site area 450 m² [complying development]; cl 52 [development consent].</p>
        <p><span className="text-gray-500">Zone</span> — SEPP (Housing) 2021 cl 50, read with definition of &ldquo;residential zone&rdquo; in cl 49: R1, R2, R3, R4, R5/RU5 where dwelling houses are permissible under the applicable LEP.</p>
        <p><span className="text-gray-500">Heritage</span> — CDC pathway: SEPP (Housing) 2021 cl 54(3)(c) excludes heritage items and draft heritage items; DA pathway: applicable LEP cl 5.10 (Standard Instrument). Heritage Map sourced from NSW Planning Portal.</p>
        <p><span className="text-gray-500">Flood control lot</span> — SEPP (Housing) 2021 cl 58: complying development must not be carried out on flood storage areas, floodways, flow paths, high hazard areas, or high risk areas. Spatial data: 12 LGAs covered — shown as unknown outside coverage.</p>
        <p><span className="text-gray-500">Biodiversity</span> — SEPP (Exempt and Complying Development Codes) 2008 cl 1.19(1) excludes land mapped on the NSW Biodiversity Values Map (Biodiversity Conservation Act 2016). Spatial data: NSW DCCEEW.</p>
        <p><span className="text-gray-500">Acid sulfate soils</span> — SEPP (Exempt and Complying Development Codes) 2008 cl 1.19(1) excludes Class 1 and Class 2 acid sulfate soils; DA pathway: applicable LEP cl 7.1 (Standard Instrument).</p>
        <p className="pt-1 border-t border-gray-100 mt-2">DCP setback, height, floor space ratio, and landscaping controls not assessed here. This tool is indicative only — verify with a qualified town planner before lodging a DA or CDC.</p>
      </div>
    </div>
  );
}

type StructureTypeAnswer = 'part_of_main' | 'garage' | 'existing_gf' | 'unsure';

const STRUCTURE_TYPE_OPTIONS: { label: string; value: StructureTypeAnswer; hint: string }[] = [
  { label: 'Part of main house', value: 'part_of_main', hint: 'e.g. rear extension, garage attached to house' },
  { label: 'Garage / outbuilding', value: 'garage', hint: 'separate shed, carport, workshop' },
  { label: 'Existing granny flat', value: 'existing_gf', hint: 'studio, secondary dwelling, converted garage' },
  { label: 'Not sure', value: 'unsure', hint: "unsure \u2014 we'll flag for certifier review" },
];

function getPositionLabel(bbox_pixel: number[], tileHeight: number | undefined): string {
  if (!tileHeight || !bbox_pixel || bbox_pixel.length < 4) return '';
  const cy = (bbox_pixel[1] + bbox_pixel[3]) / 2;
  const norm = cy / tileHeight;
  if (norm < 0.35) return 'front of lot';
  if (norm > 0.65) return 'rear of lot';
  return 'mid-lot';
}

// Sol HIGH 0.99: the manual-review checkbox next to this used to assert "no
// other structures" with no way to say otherwise — a person who genuinely
// found something extra on SIX Maps had to either tick a false statement to
// proceed, or stay stuck with no way to correct the number at all. This
// gives them an actual field to enter what they found; the checkbox beside
// it now just attests the number is accurate, true in either direction.
function ManualStructureCount({ confirmedCount, onCountChange }: { confirmedCount: number; onCountChange: (n: number) => void }) {
  return (
    <div className="flex items-center gap-2">
      <label htmlFor="manual-structure-count" className="text-xs text-gray-600">
        Total structures on this lot (including the main dwelling):
      </label>
      <input
        id="manual-structure-count"
        type="number"
        min={1}
        value={confirmedCount}
        onChange={(e) => onCountChange(Math.max(1, Number(e.target.value) || 1))}
        className="w-16 px-2 py-1 rounded border border-gray-300 text-xs"
      />
    </div>
  );
}

// Exported for test only. The regression this guards is specific: onCountChange
// was a prop this component accepted and never called, so the "user-confirmed"
// structure count could only repeat the detector for the tool's whole life.
export function ConfirmationPanel({
  detectResult,
  inputAddress,
  confirmedCount,
  onCountChange,
  structureTypes,
  onStructureTypesChange,
  existingSecondaryDwelling,
  onExistingSecondaryDwellingChange,
  onConfirm,
  onBack,
}: {
  detectResult: DetectResult;
  inputAddress: string;
  confirmedCount: number;
  onCountChange: (n: number) => void;
  structureTypes: Record<number, StructureTypeAnswer>;
  onStructureTypesChange: (v: Record<number, StructureTypeAnswer>) => void;
  existingSecondaryDwelling: boolean | null;
  onExistingSecondaryDwellingChange: (v: boolean | null) => void;
  onConfirm: (e: React.FormEvent) => void;
  onBack: () => void;
}) {
  // structureTypes is owned by the page, not this component. It was local
  // state until 2026-08-06, which meant every answer a person gave about a
  // building was discarded when this panel unmounted.

  const secondaryStructures = detectResult.detected_structures.filter(s => !s.is_main_dwelling);
  const usePerStructureQuestions = detectResult.samgeo_validated && secondaryStructures.length > 0;

  // Detection recall is measured at 0.368 against a 0.70 floor (2026-08-12) —
  // it misses roughly two of every three real structures. Sol HIGH 0.98: a
  // validated scan that finds ONLY the main dwelling (secondaryStructures
  // empty) is the single most likely shape for a missed granny flat or shed
  // to take, and it triggered neither this gate nor usePerStructureQuestions
  // (which needs secondaryStructures.length > 0) — so "found nothing extra"
  // and "missed something" were indistinguishable and both submitted
  // unreviewed. Gate on secondaryStructures, not the raw detected array:
  // this also subsumes the true zero-detection case (secondaryStructures is
  // empty whenever detected_structures is). When secondary structures WERE
  // found, the existing per-structure review (allSecondaryAnswered) is what
  // must be complete instead — it existed before this fix but nothing
  // enforced it either.
  const needsManualReview = !detectResult.samgeo_validated || secondaryStructures.length === 0;
  const [manualReviewConfirmed, setManualReviewConfirmed] = useState(false);

  const handleStructureType = (idx: number, type: StructureTypeAnswer) => {
    const next = { ...structureTypes, [idx]: type };
    const values = Object.values(next);
    if (values.some(t => t === 'existing_gf')) {
      onExistingSecondaryDwellingChange(true);
    } else if (secondaryStructures.every(s => s.index in next)) {
      // All answered — false if no GF, null if any unsure
      const anyUnsure = values.some(t => t === 'unsure');
      onExistingSecondaryDwellingChange(anyUnsure ? null : false);
    } else {
      // No existing_gf among the answers and not everything answered yet.
      // Without this branch, changing an 'existing_gf' answer to something
      // else left existingSecondaryDwelling stuck at true, and the request
      // then asserted an existing granny flat that no current answer says is
      // there — serving an ineligible verdict off a retracted answer.
      onExistingSecondaryDwellingChange(null);
    }
    onStructureTypesChange(next);
    // The count control, finally connected. `onCountChange` was passed to this
    // component from the day it was written and never called, so the
    // "user-confirmed structure count" could only ever repeat the detector's
    // own figure. A detection marked "part of the main dwelling" is not a
    // separate building, so it comes out of the count.
    const notSeparate = secondaryStructures.filter(
      s => next[s.index] === 'part_of_main',
    ).length;
    onCountChange(Math.max(0, detectResult.detected_structures.length - notSeparate));
  };

  const answeredCount = secondaryStructures.filter(s => s.index in structureTypes).length;
  const allSecondaryAnswered = secondaryStructures.length > 0 &&
    answeredCount === secondaryStructures.length;

  // needsManualReview false implies samgeo_validated AND
  // secondaryStructures.length > 0 (see its definition above) — exactly
  // usePerStructureQuestions — so these two branches are exhaustive.
  const calculateBlocked = needsManualReview ? !manualReviewConfirmed : !allSecondaryAnswered;

  const canonical = detectResult.address;
  const showCanonical = canonical && canonical.toLowerCase() !== inputAddress.toLowerCase();
  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div className="p-6">
        <h2 className="font-semibold text-gray-900">{inputAddress || canonical}</h2>
        {showCanonical && (
          <p className="text-xs text-gray-400 mt-0.5">Matched to: {canonical}</p>
        )}
        {detectResult.lot_area_m2 != null && (
          <p className="text-sm text-gray-500 mt-0.5">
            Lot area: {detectResult.lot_area_m2.toLocaleString('en-AU', { maximumFractionDigits: 0 })} m²
          </p>
        )}
        {detectResult.lot_area_m2 != null && detectResult.lot_area_m2 > 2000 && (
          <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
            <span className="font-medium">Large lot area</span> — {detectResult.lot_area_m2.toLocaleString('en-AU', { maximumFractionDigits: 0 })} m² is unusually large for a single dwelling house. If this is a strata parent lot or a multi-dwelling development site, SEPP Housing 2021 secondary dwelling provisions do not apply.
          </div>
        )}
        {!detectResult.sepp_eligible && detectResult.sepp_ineligible_reason && (
          <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
            {detectResult.sepp_ineligible_reason}
          </div>
        )}
      </div>

      <div className="p-6">
        <StructureMap
          lat={detectResult.lat}
          lng={detectResult.lng}
          tile_bbox={detectResult.tile_bbox}
          tile_width={detectResult.tile_width}
          tile_height={detectResult.tile_height}
          structures={detectResult.detected_structures}
          lot_polygon_wgs84={detectResult.lot_polygon_wgs84}
          licence={detectResult.tile_licence}
        />

        {!detectResult.samgeo_validated ? (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 mb-4 space-y-2">
            <p>Aerial detection is in pre-validation mode. Please verify the structure count manually using the SIX Maps viewer before proceeding.</p>
            <ManualStructureCount confirmedCount={confirmedCount} onCountChange={onCountChange} />
            <label className="flex items-start gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={manualReviewConfirmed}
                onChange={(e) => setManualReviewConfirmed(e.target.checked)}
                className="mt-0.5"
              />
              <span>I&apos;ve checked SIX Maps and the count above reflects what I found.</span>
            </label>
          </div>
        ) : detectResult.detected_structures.length > 0 ? (
          <div className="mb-4">
            {(() => {
              const valid = detectResult.detected_structures.filter(
                (s) => s.area_m2 == null || s.area_m2 < (detectResult.lot_area_m2 ?? Infinity) * 1.5
              );
              return (
                <>
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    AI detected {valid.length} structure{valid.length !== 1 ? 's' : ''} on lot
                  </p>
                  {/* The count that will actually be submitted, and whether a
                      person has stood behind it. Before this, the figure sent
                      to the server was always the detector's own and nothing
                      on screen said so. */}
                  {usePerStructureQuestions && (
                    <p className={`text-xs mb-2 ${allSecondaryAnswered ? 'text-teal-700' : 'text-gray-400'}`}>
                      {allSecondaryAnswered
                        ? `Count used for this check: ${confirmedCount} — based on your answers below. Only buildings the scan found are listed; if one is missing from the map, the count cannot account for it.`
                        : `Count used for this check: ${confirmedCount} — the detector's own figure. Answer for each structure below and it will reflect your review (${answeredCount} of ${secondaryStructures.length} answered).`}
                    </p>
                  )}
                  <div className="space-y-1.5">
                    {valid.map((s) => (
                      <div key={s.index} className="flex items-start gap-2 text-xs text-gray-600">
                        <span className="w-2 h-2 rounded-full bg-teal-400 shrink-0 mt-1" />
                        <div>
                          <span className="font-medium">{s.is_main_dwelling ? 'Main dwelling' : `Structure ${s.index + 1}`}</span>
                          {s.area_m2 != null && (
                            <span>
                              {` — ~${s.area_m2} m²`}
                              {!s.is_main_dwelling && s.area_m2 >= 100 && (
                                <span className="text-amber-600 ml-1">(unusually large for an outbuilding — verify type)</span>
                              )}
                              {!s.is_main_dwelling && s.area_m2 >= 60 && s.area_m2 < 100 && (
                                <span className="text-gray-400 ml-1">(~size of a double garage)</span>
                              )}
                            </span>
                          )}
                          {s.area_m2 == null && !s.is_main_dwelling && (
                            <span className="text-gray-400"> — size unknown</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  {/* Only the main dwelling was found — no secondary structure
                      to review against, but a real one may simply have been
                      missed (this is the shape a missed detection actually
                      takes). Same manual-review requirement as an empty
                      detection, not the per-structure flow, since there is
                      nothing here to answer questions about. */}
                  {secondaryStructures.length === 0 && (
                    <div className="mt-2 space-y-2">
                      <ManualStructureCount confirmedCount={confirmedCount} onCountChange={onCountChange} />
                      <label className="flex items-start gap-2 text-xs text-gray-600 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={manualReviewConfirmed}
                          onChange={(e) => setManualReviewConfirmed(e.target.checked)}
                          className="mt-0.5"
                        />
                        <span>I&apos;ve checked SIX Maps and the count above reflects what I found.</span>
                      </label>
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        ) : (
          <div className="mb-4 space-y-2">
            <p className="text-sm text-gray-500">No structures detected — enter count manually.</p>
            <ManualStructureCount confirmedCount={confirmedCount} onCountChange={onCountChange} />
            <label className="flex items-start gap-2 text-xs text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={manualReviewConfirmed}
                onChange={(e) => setManualReviewConfirmed(e.target.checked)}
                className="mt-0.5"
              />
              <span>I&apos;ve checked SIX Maps and the count above reflects what I found.</span>
            </label>
          </div>
        )}

        {/* Gate: if detect says ineligible, block confirm entirely */}
        {(() => {
          const mainDwelling = detectResult.detected_structures.find(s => s.is_main_dwelling);
          const mainDwellingArea = mainDwelling?.area_m2 ?? null;
          const otherStructuresArea = detectResult.detected_structures
            .filter(s => !s.is_main_dwelling && s.area_m2 != null)
            .reduce((sum, s) => sum + (s.area_m2 ?? 0), 0);
          const lotArea = detectResult.lot_area_m2;
          const residualArea = lotArea != null && mainDwellingArea != null
            ? lotArea - mainDwellingArea - otherStructuresArea
            : null;
          const proxyFails = residualArea != null && residualArea < 120;

          if (!detectResult.sepp_eligible || proxyFails) {
            return (
              <div className="space-y-4">
                {proxyFails && detectResult.sepp_eligible && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800 space-y-2">
                    <p className="font-medium">Insufficient space for a complying development granny flat</p>
                    <p>
                      The principal dwelling occupies ~{mainDwellingArea!.toFixed(0)} m²
                      {otherStructuresArea > 0 && ` and other detected structures occupy ~${otherStructuresArea.toFixed(0)} m²`}
                      {' '}of a {lotArea!.toFixed(0)} m² lot,
                      leaving ~{residualArea!.toFixed(0)} m² of residual space. A 60 m² secondary dwelling requires at least
                      120 m² of residual area to accommodate the structure plus mandatory SEPP Housing 2021 setbacks:
                      3 m from the rear boundary, 0.9 m from each side boundary, and 3 m separation from the principal dwelling.
                    </p>
                    <p className="text-red-700">
                      This is an estimate based on aerial detection. A DA pathway may allow a smaller or differently positioned
                      structure — consult a town planner or private certifier.
                    </p>
                  </div>
                )}
                {!detectResult.sepp_eligible && (
                  <p className="text-sm text-gray-500">
                    A granny flat cannot be approved on this lot via the complying development pathway.
                    A DA may still be available at council&apos;s discretion — consult a town planner.
                  </p>
                )}
                <button
                  type="button"
                  onClick={onBack}
                  className="px-5 py-2.5 bg-white text-gray-600 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
                >
                  Check another address
                </button>
              </div>
            );
          }

          return (
        <form onSubmit={onConfirm} className="space-y-5">
          {/* Structure type questions — per-structure when detection validated, binary fallback otherwise */}
          {usePerStructureQuestions ? (
            <div className="space-y-5">
              <p className="text-sm font-medium text-gray-700">Confirm each detected structure</p>
              <p className="text-xs text-gray-400 -mt-3">
                NSW rules allow only one secondary dwelling per lot. Identifying each structure correctly affects eligibility.
              </p>
              {secondaryStructures.map(s => {
                const posLabel = getPositionLabel(s.bbox_pixel, detectResult.tile_height);
                const sizeContext = s.area_m2 != null
                  ? `~${s.area_m2} m²`
                  : 'size unknown';
                const selected = structureTypes[s.index];
                return (
                  <div key={s.index} className="rounded-lg border border-gray-200 p-4 space-y-3">
                    <div>
                      <p className="text-sm font-medium text-gray-800">
                        Structure {s.index + 1} — {sizeContext}
                        {posLabel && <span className="ml-1 text-gray-400 font-normal">· {posLabel}</span>}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">What is this structure?</p>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {STRUCTURE_TYPE_OPTIONS.map(opt => (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => handleStructureType(s.index, opt.value)}
                          className={`text-left px-3 py-2.5 rounded-lg border text-xs transition-colors ${
                            selected === opt.value
                              ? 'bg-teal-600 text-white border-teal-600'
                              : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <span className="font-medium block">{opt.label}</span>
                          <span className={`block mt-0.5 ${selected === opt.value ? 'text-teal-100' : 'text-gray-400'}`}>{opt.hint}</span>
                        </button>
                      ))}
                    </div>
                    {selected === 'existing_gf' && (
                      <p className="text-xs text-red-600">A second granny flat cannot be approved on this lot under SEPP Housing 2021.</p>
                    )}
                    {selected === 'unsure' && (
                      <p className="text-xs text-amber-600">Confidence will be capped at Medium. Check on SIX Maps or ask the owner.</p>
                    )}
                  </div>
                );
              })}
              <p className="text-xs text-gray-400">
                Eligibility depends on the accuracy of your structure classifications. If you selected the wrong type,{' '}
                <button
                  type="button"
                  onClick={() => {
                    onStructureTypesChange({});
                    onExistingSecondaryDwellingChange(null);
                    // Back to the detector's own figure, and back to
                    // machine_default provenance with it.
                    onCountChange(detectResult.detected_structures.length);
                  }}
                  className="underline hover:no-underline"
                >reset answers</button>.
              </p>
            </div>
          ) : (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-1">
                Is there an existing secondary dwelling or granny flat on this property?
              </p>
              <p className="text-xs text-gray-400 mb-3">
                NSW planning rules only allow one secondary dwelling (granny flat) per lot. A converted garage, studio, or detached cabin counts as one.
              </p>
              <div className="flex gap-2">
                {([
                  { label: 'Yes', value: true },
                  { label: 'No', value: false },
                  { label: 'Not sure', value: null },
                ] as { label: string; value: boolean | null }[]).map(({ label, value }) => {
                  const active = existingSecondaryDwelling === value;
                  return (
                    <button
                      key={label}
                      type="button"
                      onClick={() => onExistingSecondaryDwellingChange(value)}
                      className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                        active
                          ? 'bg-teal-600 text-white border-teal-600'
                          : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
              {existingSecondaryDwelling === true && (
                <p className="mt-2 text-xs text-red-600">
                  If there&apos;s already a granny flat on this lot, a second one cannot be approved under NSW planning rules. This property would be ineligible.
                </p>
              )}
              {existingSecondaryDwelling === null && (
                <p className="mt-2 text-xs text-amber-600">
                  If you&apos;re not sure, we&apos;ll still run the analysis — but confidence will be capped at Medium until this is confirmed. Check the lot on the NSW Planning Portal or ask the owner.
                </p>
              )}
            </div>
          )}

          {/* Warn when SAM ran but couldn't size the main dwelling — envelope unverifiable */}
          {detectResult.samgeo_validated &&
           detectResult.detected_structures.length > 0 &&
           detectResult.detected_structures.find(s => s.is_main_dwelling)?.area_m2 == null && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
              The main dwelling footprint area could not be determined from aerial detection.
              Available building envelope could not be estimated — review the aerial map and check
              whether adequate rear yard space appears to exist.
            </div>
          )}

          {calculateBlocked && (
            <p className="text-xs text-amber-700">
              {needsManualReview
                ? 'Tick the box above to continue — detection here needs a human check before a yield can be calculated.'
                : 'Answer for every detected structure above to continue — a human check is needed before a yield can be calculated.'}
            </p>
          )}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={calculateBlocked}
              className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Calculate yield
            </button>
            <button
              type="button"
              onClick={onBack}
              className="px-5 py-2.5 bg-white text-gray-600 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
            >
              Back
            </button>
          </div>
        </form>
          );
        })()}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CrossSellCards — contextual upsell to related tools
// Pass variant: Development Monitoring + flood screening (pre-construction due diligence)
// Fail variant: Development Monitoring only (monitor for zone/DA changes)
// ---------------------------------------------------------------------------

function CrossSellCards({ buildable, address, ineligibleReason }: { buildable: boolean; address: string; ineligibleReason?: string | null }) {
  const encoded = encodeURIComponent(address);
  const reason = (ineligibleReason ?? '').toLowerCase();

  const passCards = [
    {
      title: 'Development Monitoring',
      body: 'Check whether nearby DAs could block sunlight or views once your granny flat is built.',
      href: `/reports/threat-radar?address=${encoded}`,
      label: 'Check nearby DAs →',
    },
    {
      title: 'Flood Screening',
      body: 'Verify flood risk before you build — required by certifiers for any new structure.',
      href: `/reports/flood?address=${encoded}`,
      label: 'Check flood risk →',
    },
  ];

  // Reason-specific fail cards — show the most relevant tool first
  let failCards;
  if (reason.includes('flood')) {
    failCards = [
      {
        title: 'Flood Screening Report',
        body: 'Your lot is in a flood control area. Get the full flood study overlay, BOM gauge history, and satellite water extent data — required for any DA on a flood-affected lot.',
        href: `/reports/flood?address=${encoded}`,
        label: 'Get flood report →',
      },
      {
        title: 'Development Monitoring',
        body: 'Monitor nearby DAs — a flood study amendment or rezoning could change your eligibility.',
        href: `/reports/threat-radar?address=${encoded}`,
        label: 'Monitor this area →',
      },
    ];
  } else if (reason.includes('heritage')) {
    failCards = [
      {
        title: 'Development Monitoring',
        body: 'Heritage exclusions apply to CDC only — a DA may still be viable. Monitor nearby approvals to understand what council is approving in your area.',
        href: `/reports/threat-radar?address=${encoded}`,
        label: 'Check nearby approvals →',
      },
      {
        title: 'Rooftop Solar Potential',
        body: 'Heritage restrictions limit new structures — but solar on an existing roof may still be viable. Check your annual kWh yield.',
        href: `/reports/solar-yield?address=${encoded}`,
        label: 'Check solar potential →',
      },
    ];
  } else if (reason.includes('zone') || reason.includes('zoning')) {
    failCards = [
      {
        title: 'Development Monitoring',
        body: 'Monitor nearby rezoning proposals — a zone change in your area could make your lot eligible in future.',
        href: `/reports/threat-radar?address=${encoded}`,
        label: 'Monitor rezoning activity →',
      },
    ];
  } else if (reason.includes('existing') || reason.includes('secondary dwelling') || reason.includes('granny flat')) {
    failCards = [
      {
        title: 'Rooftop Solar Potential',
        body: 'You already have a secondary dwelling — optimise what you have. Check solar yield on your existing structures.',
        href: `/reports/solar-yield?address=${encoded}`,
        label: 'Check solar potential →',
      },
      {
        title: 'Shadow Detector',
        body: 'Check whether a neighbour\'s development proposal would overshadow your existing structures.',
        href: `/reports/shadow?address=${encoded}`,
        label: 'Check shadow risk →',
      },
    ];
  } else {
    // Default ineligible (lot size, other) — DA may still be viable
    failCards = [
      {
        title: 'Development Monitoring',
        body: 'The CDC pathway isn\'t available — but a DA through council may still be possible. Monitor nearby secondary dwelling approvals to gauge what council is accepting.',
        href: `/reports/threat-radar?address=${encoded}`,
        label: 'Check nearby approvals →',
      },
      {
        title: 'Flood Screening',
        body: 'Verify flood risk before pursuing a DA — flood overlay is required in any development application.',
        href: `/reports/flood?address=${encoded}`,
        label: 'Check flood risk →',
      },
    ];
  }

  const cards = buildable ? passCards : failCards;

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Also check</p>
      <div className={`grid gap-3 ${buildable ? 'sm:grid-cols-2' : ''}`}>
        {cards.map((card) => (
          <a
            key={card.href}
            href={card.href}
            className="block rounded-xl border border-gray-200 bg-white p-4 hover:border-teal-300 hover:shadow-sm transition-all"
          >
            <p className="text-sm font-semibold text-gray-900 mb-1">{card.title}</p>
            <p className="text-xs text-gray-500 mb-3 leading-relaxed">{card.body}</p>
            <span className="text-xs font-medium text-teal-600">{card.label}</span>
          </a>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PaidDownloadCTA — shown after result when user arrives via payment=success
// ---------------------------------------------------------------------------

function PaidDownloadCTA({ reportId, address }: { reportId: string; address: string }) {
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState('');

  const handleDownload = async () => {
    setDownloading(true);
    setDlError('');
    try {
      const res = await fetch('/api/reports/granny-flat/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId }),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error((json as { error?: string }).error ?? 'Download failed');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const slug = address.slice(0, 30).replace(/[^a-z0-9]/gi, '-').toLowerCase();
      a.download = `granny-flat-report-${slug}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setDlError(err instanceof Error ? err.message : 'Download failed — please try again.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="rounded-xl border border-teal-200 bg-teal-50 p-6">
      <h3 className="font-semibold text-teal-900 mb-1">Download your report</h3>
      <p className="text-sm text-teal-700 mb-4">
        CDC pathway checklist, setback standards with SEPP clause citations, yield sensitivity table, and full data source log.
      </p>
      <button
        onClick={handleDownload}
        disabled={downloading}
        className="w-full py-2.5 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-60"
      >
        {downloading ? 'Generating PDF…' : 'Download PDF report →'}
      </button>
      {dlError && <p className="text-sm text-red-600 mt-2">{dlError}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ReportUnlockCTA — shown after result card
// Pass variant: email capture → Stripe link to unlock detailed PDF report
// Fail variant: "What could change this?" + notify-me email capture
// ---------------------------------------------------------------------------

function ReportUnlockCTA({
  buildable,
  sepp_ineligible_reason,
  lot_area_m2,
  email,
  setEmail,
  emailCaptured,
  onEmailSubmit,
  jobId,
  address,
}: {
  buildable: boolean;
  sepp_ineligible_reason: string | null;
  lot_area_m2: number | null;
  email: string;
  setEmail: (v: string) => void;
  emailCaptured: boolean;
  onEmailSubmit: (e: React.FormEvent) => void;
  jobId: string;
  address: string;
}) {
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [checkoutError, setCheckoutError] = useState('');

  const handleBuyReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !jobId) return;
    setCheckoutLoading(true);
    setCheckoutError('');
    try {
      const res = await fetch('/api/stripe/checkout/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, address, email: email.trim() }),
      });
      const data = await res.json();
      if (!res.ok || !data.checkout_url) throw new Error(data.error ?? 'Checkout failed');
      window.location.href = data.checkout_url;
    } catch (err) {
      setCheckoutError(err instanceof Error ? err.message : 'Something went wrong — try again.');
      setCheckoutLoading(false);
    }
  };

  if (buildable) {
    return (
      <div className="rounded-xl border border-teal-200 bg-teal-50 p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h3 className="font-semibold text-teal-900">Get the full report — $49</h3>
            <p className="text-sm text-teal-700 mt-1">
              CDC pathway checklist, setback standards with SEPP clause citations, yield sensitivity table, and a shareable PDF — emailed instantly after payment.
            </p>
          </div>
          <span className="shrink-0 text-sm font-bold text-teal-900">$49</span>
        </div>
        <form onSubmit={handleBuyReport} className="space-y-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            className="w-full px-4 py-2.5 rounded-lg border border-teal-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
          />
          <button
            type="submit"
            disabled={checkoutLoading}
            className="w-full py-2.5 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-60"
          >
            {checkoutLoading ? 'Redirecting to payment…' : 'Get full report — $49 →'}
          </button>
          {checkoutError && (
            <p className="text-sm text-red-600">{checkoutError}</p>
          )}
        </form>
      </div>
    );
  }

  // Fail variant
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6">
      <h3 className="font-semibold text-gray-900 mb-1">What could change this?</h3>
      <p className="text-sm text-gray-500 mb-4">
        {deriveWhatToChange(sepp_ineligible_reason, lot_area_m2)}
      </p>
      {!emailCaptured ? (
        <form onSubmit={onEmailSubmit} className="flex gap-2">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
          />
          <button
            type="submit"
            className="px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors whitespace-nowrap"
          >
            Notify me
          </button>
        </form>
      ) : (
        <p className="text-sm text-teal-700 font-medium">Got it — we&apos;ll be in touch if anything changes for this address.</p>
      )}
    </div>
  );
}

function ResultCard({ result, inputAddress, onReset }: { result: ConfirmResult; inputAddress: string; onReset: () => void }) {
  const weeklyRent = result.estimated_weekly_rent_aud;
  const annualRent = weeklyRent ? weeklyRent * 52 : null;
  const displayAddr = inputAddress || result.address;
  const reviewState = resolveGrannyReviewState(
    result as unknown as Record<string, unknown>,
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-gray-900">{displayAddr}</h2>
            <p className="text-xs font-medium text-gray-600 mt-0.5">
              {reviewState.label}
            </p>
            <p className="text-xs text-gray-500 mt-1 max-w-sm">{reviewState.detail}</p>
            {/* A stored reason on a pre-2026-08-06 row credits the reader
                with having personally checked the count ("counts agree") —
                which could not have happened: the count was seeded from the
                detector and the control that would change it was never
                wired. Rendering it beside the state above would contradict
                it in the next line. Measured 2026-08-06: 18 of 20 completed
                rows carry that phrasing. */}
            {result.confidence_reason && !reviewState.derived && (
              <p className="text-xs text-gray-500 mt-1 max-w-sm">{result.confidence_reason}</p>
            )}
            <button
              onClick={onReset}
              className="text-xs text-teal-600 hover:text-teal-700 underline mt-1"
            >
              New address
            </button>
          </div>
          <span
            className={`shrink-0 text-xs font-medium px-2 py-1 rounded-full ${
              result.granny_flat_buildable
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {result.granny_flat_buildable ? 'Eligible' : 'Not eligible'}
          </span>
        </div>
      </div>

      {result.granny_flat_buildable && (
        <div className="grid grid-cols-3 divide-x divide-gray-100">
          <div className="p-5">
            <p className="text-xs text-gray-400 mb-1">Max floor area</p>
            <p className="text-lg font-semibold text-gray-900">{result.max_floor_area_m2} m²</p>
          </div>
          <div className="p-5">
            <p className="text-xs text-gray-400 mb-1">Rental income potential</p>
            <p className="text-lg font-semibold text-teal-700">
              {weeklyRent ? `$${weeklyRent.toLocaleString('en-AU', { maximumFractionDigits: 0 })}/wk` : '$280–$340/wk'}
            </p>
          </div>
          <div className="p-5">
            <p className="text-xs text-gray-400 mb-1">Yield on build cost</p>
            <p className="text-lg font-semibold text-gray-900">
              {result.rental_yield_annual_pct ? `${result.rental_yield_annual_pct}%` : 'N/A'}
            </p>
            {result.assumed_build_cost_aud && (
              <p className="text-xs text-gray-400 mt-0.5">
                On ${result.assumed_build_cost_aud.toLocaleString('en-AU')} build cost
              </p>
            )}
          </div>
        </div>
      )}

      {result.warnings.length > 0 && (
        <div className="px-6 py-4 bg-amber-50 space-y-1">
          {result.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-800">{w}</p>
          ))}
        </div>
      )}

      {result.eplanning_history && (
        <div className="px-6 py-4 space-y-1.5">
          <p className="text-xs font-medium text-gray-600">NSW ePlanning Portal history</p>
          {result.eplanning_history.error ? (
            <p className="text-xs text-gray-400">{result.eplanning_history.source_note}</p>
          ) : result.eplanning_history.found ? (
            <>
              {result.eplanning_history.applications.map((app, i) => (
                <div key={i} className="flex items-baseline gap-2 text-xs text-gray-600">
                  <span className={`shrink-0 font-medium ${app.type === 'DA' ? 'text-blue-600' : 'text-teal-600'}`}>{app.type}</span>
                  <span>{app.development_type}</span>
                  <span className="text-gray-400">·</span>
                  <span className="text-gray-500">{app.status}</span>
                  {app.lodgement_date && (
                    <><span className="text-gray-400">·</span><span className="text-gray-400">{app.lodgement_date.slice(0, 10)}</span></>
                  )}
                  {app.reference && <span className="text-gray-400 ml-auto shrink-0">{app.reference}</span>}
                </div>
              ))}
              <p className="text-xs text-gray-400 mt-1">{result.eplanning_history.source_note}</p>
            </>
          ) : (
            <p className="text-xs text-gray-400">
              No secondary dwelling application found. {result.eplanning_history.source_note}
            </p>
          )}
        </div>
      )}

      <div className="px-6 py-4">
        <p className="text-xs text-gray-400">
          Data: {result.data_sources.join(' · ')}
        </p>
      </div>
    </div>
  );
}

export default function GrannyFlatPage() {
  return (
    <>
      <SoftwareAppJsonLd
        name="Granny Flat Eligibility Check"
        description="Can you build a granny flat on your NSW property? Aerial structure detection, SEPP Housing 2021 analysis, and rental yield estimate — free for any address."
        url="/reports/granny-flat"
      />
      <Suspense>
        <GrannyFlatPageInner />
      </Suspense>
    </>
  );
}
