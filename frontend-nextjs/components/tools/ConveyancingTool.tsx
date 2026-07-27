'use client';

import { useState, useEffect, useCallback } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';
import { WaitlistButton } from '@/components/reports/WaitlistButton';
import { DATA_PROVENANCE } from '@/lib/disclaimers';
import { posthog } from '@/components/providers/PostHogProvider';
import { OperationalTransparency, type TransparencyStep } from '@/components/tools/OperationalTransparency';

const CONVEYANCING_STEPS: TransparencyStep[] = [
  { label: 'Querying NSW Planning Portal…',           ms: 0 },
  { label: 'Loading spatial overlays and zoning…',    ms: 2000 },
  { label: 'Checking heritage registers…',            ms: 5000 },
  { label: 'Reading environmental planning layers…',  ms: 8000 },
  { label: 'Pulling valuation and lot dimensions…',   ms: 12000 },
  { label: 'Assembling disclosure data…',             ms: 16000 },
];

interface FeasibilityItem {
  question: string;
  answer: string;
  flag: 'ok' | 'warn' | 'alert';
  basis: string;
}

interface ConveyancingOutputs {
  zone: string | null;
  zone_full: string | null;
  zone_epi: string | null;
  legislation_url: string | null;
  height: string | null;
  height_units: string;
  fsr: string | null;
  lot_size: string | null;
  lot_size_units: string;
  ass_class: string | null;
  heritage_items: string[];
  heritage_hca: string[];
  sepp_overlays: { name: string; type: string; label?: string }[];
  housing_sepp: boolean;
  tod_area: boolean;
  flood_epi: boolean;
  riparian_epi: boolean;
  unique_overlays: { layer_type: string; value: string | null; note?: string }[];
  covered_layers: string[];
  strata_info: {
    is_strata: boolean;
    strata_plan?: string;
    source?: string;
    parent_has_strata?: boolean;
    plan_label?: string;
    plan_type?: string | null;
  } | null;
  valuation: {
    lot_area_m2: number | null;
    land_value: number | null;
    val_base_date: string | null;
  };
  headroom: {
    lot_area_m2?: number;
    lot_area_display?: string;
    max_gfa_m2?: number;
    max_gfa_display?: string;
    fsr_numeric?: number;
    subdivision_feasible?: boolean;
    subdivision_note?: string;
    land_value?: number;
    land_value_display?: string;
    land_value_per_m2?: number;
    land_value_per_m2_display?: string;
  };
  feasibility: FeasibilityItem[];
  // null = the nearby-DA check could not run (not "0 found"); da_fetch_failed
  // is the explicit signal. See services/conveyancing.py _nearby_da_count.
  da_count: number | null;
  da_fetch_failed?: boolean;
  dcp_available: boolean;
}

interface ConveyancingResult {
  address: string;
  lat: number;
  lng: number;
  prop_id: number | null;
  run_date: string;
  outputs: ConveyancingOutputs;
  confidence: string;
  data_sources: string[];
  report_id?: string;
  report_token?: string;
}

type PageState = 'idle' | 'running' | 'complete' | 'error';

const FLAG_META: Record<string, { icon: string; bg: string; text: string }> = {
  ok:    { icon: '\u2713', bg: 'bg-green-50',  text: 'text-green-700' },
  warn:  { icon: '\u26A0', bg: 'bg-amber-50',  text: 'text-amber-700' },
  alert: { icon: '\u2717', bg: 'bg-red-50',    text: 'text-red-700' },
};

// The API returns one row per portal map sheet, so the same SEPP repeats with
// different labels ("2576", "WINGECARRIBEE"). Collapse to one row per SEPP,
// keeping the distinct labels. Mirrors the (name, type) dedup in the PDF report.
function dedupeSeppOverlays(
  rows: { name: string; type: string; label?: string }[],
): { name: string; labels: string[] }[] {
  const byName = new Map<string, { name: string; labels: string[] }>();
  for (const row of rows) {
    const name = row.name || row.type;
    if (!name) continue;
    const entry = byName.get(name) ?? { name, labels: [] };
    const label = (row.label || '').trim();
    if (label && !entry.labels.includes(label)) entry.labels.push(label);
    byName.set(name, entry);
  }
  return [...byName.values()];
}

export function ConveyancingTool({ lgaSlug }: { lgaSlug?: string }) {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<ConveyancingResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const [paidReportId, setPaidReportId] = useState<string | null>(null);
  // Named early-access grant (?access=<code>) — validated server-side against
  // CONVEYANCING_ACCESS_CODES; unlocks the full-PDF CTA without checkout.
  const [accessGranted, setAccessGranted] = useState(false);

  const runCheck = useCallback(async (addr: string) => {
    if (!addr.trim()) return;
    setState('running');
    setResult(null);
    setErrorMsg('');
    try {
      const res = await fetch('/api/satellite/conveyancing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr }),
      });
      const json = await res.json();
      // Surface the backend's plain-language reason. FastAPI HTTPException returns
      // `detail` as a STRING ("...temporarily unavailable; please retry." on 503,
      // "Could not resolve address to a parcel: ..." on 422). Request-validation
      // errors return `detail` as an array of objects — ignore those (they would
      // stringify to "[object Object]") and fall back to a generic message.
      if (!res.ok) {
        const obj = json && typeof json === 'object' ? json : {};
        const error = typeof obj.error === 'string' ? obj.error.trim() : '';
        const detail = typeof obj.detail === 'string' ? obj.detail.trim() : '';
        // `||` (not `??`) so an empty/whitespace field falls through to the next.
        throw new Error(error || detail || 'Analysis failed');
      }
      setResult(json);
      setState('complete');
      posthog.capture('tool_run', {
        tool: 'conveyancing',
        source: lgaSlug ? 'lga_page' : 'direct',
        lga_slug: lgaSlug ?? null,
        zone: json.outputs?.zone ?? null,
      });
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  }, [lgaSlug]);

  useEffect(() => {
    const handler = (e: Event) => {
      const addr = (e as CustomEvent).detail?.address;
      if (addr) {
        setAddress(addr);
        runCheck(addr);
      }
    };
    window.addEventListener('landing-search', handler);
    return () => window.removeEventListener('landing-search', handler);
  }, [runCheck]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    const addrParam = params.get('address')?.trim();
    if (addrParam && !params.get('payment')) {
      setAddress(addrParam);
      runCheck(addrParam);
      window.history.replaceState({}, '', window.location.pathname);
    }

    if (params.get('payment') === 'success') {
      const rid = params.get('report_id')?.trim();
      if (rid) setPaidReportId(rid);
      // Re-run analysis so user sees results alongside download CTA
      if (addrParam) {
        setAddress(addrParam);
        runCheck(addrParam);
      }
      window.history.replaceState({}, '', window.location.pathname);
    }

    const accessParam = params.get('access')?.trim();
    if (accessParam) {
      sessionStorage.setItem('conveyancing_access_code', accessParam);
      window.history.replaceState({}, '', window.location.pathname);
    }
    const grantCode = accessParam || sessionStorage.getItem('conveyancing_access_code');
    if (!grantCode) return;

    let ignore = false;
    fetch('/api/reports/conveyancing/access', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: grantCode }),
    })
      .then((res) => res.json())
      .then((json) => {
        if (ignore) return;
        if (json?.valid) {
          setAccessGranted(true);
          posthog.capture('conveyancing_access_grant', { code: grantCode });
        } else {
          // Invalid or revoked code: drop it so the page behaves as normal free tier.
          sessionStorage.removeItem('conveyancing_access_code');
        }
      })
      .catch(() => {
        // Network failure leaves the page in the normal free state.
      });
    return () => {
      ignore = true;
    };
  }, [runCheck]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runCheck(address);
  };

  const handleReset = () => {
    setAddress('');
    setState('idle');
    setResult(null);
    setErrorMsg('');
    window.dispatchEvent(new CustomEvent('landing-reset'));
  };

  // lot_size is fetched as a data fallback for the Min Lot Size field — it is a
  // planning control, not a hazard, so keep it out of the hazard overlay section.
  const hazardOverlays = (result?.outputs.unique_overlays ?? []).filter(
    (ov) => ov.layer_type !== 'lot_size',
  );
  const seppOverlays = dedupeSeppOverlays(result?.outputs.sepp_overlays ?? []);

  // A report is unlocked either by Stripe redirect (paidReportId) or by a
  // validated named grant plus the free check's own report_id.
  const unlockedReportId =
    paidReportId ?? (accessGranted ? result?.report_id ?? null : null);

  return (
    <div className="mb-8">
      {state === 'idle' || state === 'error' ? (
        <form id="tool-input" onSubmit={handleSubmit} className="flex gap-3 mb-8">
          <AddressAutocomplete
            value={address}
            onChange={setAddress}
            onSelect={(addr) => setAddress(addr)}
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
            placeholder="Enter any NSW address..."
          />
          <button
            type="submit"
            className="px-6 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
          >
            Analyse
          </button>
        </form>
      ) : null}

      {state === 'error' && (
        <div className="bg-red-50 text-red-700 text-sm p-4 rounded-lg mb-6">
          {errorMsg}
        </div>
      )}

      {state === 'running' && (
        <div className="py-8">
          <OperationalTransparency
            steps={CONVEYANCING_STEPS}
            active={state === 'running'}
            address={address}
            note="This usually takes 10–20 seconds."
          />
        </div>
      )}

      {state === 'complete' && result && (
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{result.address}</h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Report generated {result.run_date} &middot; Confidence: {result.confidence}
              </p>
            </div>
            <button
              onClick={handleReset}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              Check another address
            </button>
          </div>

          {/* Full-report download CTA — Stripe redirect or named early-access grant */}
          {unlockedReportId && result && (
            <ConveyancingPaidDownloadCTA
              reportId={unlockedReportId}
              address={result.address}
              lat={result.lat}
              lng={result.lng}
              propId={result.prop_id ? String(result.prop_id) : undefined}
              grant={!paidReportId}
            />
          )}

          {/* LEP Controls summary */}
          <Section title="LEP Planning Controls">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard label="Zone" value={result.outputs.zone} />
              <StatCard label="Max Height" value={result.outputs.height ? `${result.outputs.height} ${result.outputs.height_units}` : null} />
              <StatCard label="FSR" value={result.outputs.fsr ? `${result.outputs.fsr}:1` : null} />
              <StatCard label="Min Lot Size" value={result.outputs.lot_size ? `${result.outputs.lot_size} ${result.outputs.lot_size_units}` : null} />
            </div>
            {result.outputs.legislation_url && (
              <a
                href={result.outputs.legislation_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block text-xs text-teal-600 hover:text-teal-700 mt-2"
              >
                View LEP instrument on legislation.nsw.gov.au &rarr;
              </a>
            )}
          </Section>

          {/* Valuation & lot */}
          <Section title="Lot and Valuation">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <StatCard label="Lot Area" value={result.outputs.headroom.lot_area_display ?? null} />
              <StatCard label="Land Value" value={result.outputs.headroom.land_value_display ?? null} />
              <StatCard label="Value per m\u00b2" value={result.outputs.headroom.land_value_per_m2_display ?? null} />
            </div>
            {result.outputs.headroom.max_gfa_display && (
              <p className="text-xs text-gray-500 mt-2">
                Maximum GFA: {result.outputs.headroom.max_gfa_display} (FSR {result.outputs.headroom.fsr_numeric}:1 applied to lot area)
              </p>
            )}
          </Section>

          {/* Title type */}
          {result.outputs.strata_info && (
            <Section title="Title Type">
              <div className={`p-3 rounded-lg text-sm ${result.outputs.strata_info.is_strata ? 'bg-amber-50 text-amber-700' : 'bg-green-50 text-green-700'}`}>
                {result.outputs.strata_info.is_strata ? (
                  <span>Strata title {result.outputs.strata_info.strata_plan ? `(${result.outputs.strata_info.strata_plan})` : ''} &mdash; secondary dwelling and subdivision not applicable</span>
                ) : (
                  <span>Torrens title {result.outputs.strata_info.plan_label ? `(${result.outputs.strata_info.plan_label})` : ''}</span>
                )}
              </div>
            </Section>
          )}

          {/* Heritage */}
          {(result.outputs.heritage_items.length > 0 || result.outputs.heritage_hca.length > 0) && (
            <Section title="Heritage">
              <div className="bg-amber-50 p-3 rounded-lg">
                {result.outputs.heritage_hca.length > 0 && (
                  <p className="text-sm text-amber-700 font-medium mb-1">
                    Heritage Conservation Area
                  </p>
                )}
                <ul className="text-sm text-amber-700 space-y-1">
                  {result.outputs.heritage_items.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            </Section>
          )}

          {/* Environmental overlays */}
          {hazardOverlays.length > 0 && (
            <Section title="Environmental and Hazard Overlays">
              <div className="space-y-2">
                {hazardOverlays.map((ov, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <span className="shrink-0 w-2 h-2 mt-1.5 rounded-full bg-amber-500" />
                    <div>
                      <p className="text-sm font-medium text-gray-900 capitalize">
                        {ov.layer_type.replace(/_/g, ' ')}
                        {ov.value && <span className="text-gray-500 font-normal"> &mdash; {ov.value}</span>}
                      </p>
                      {ov.note && <p className="text-xs text-gray-500 mt-0.5">{ov.note}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* SEPP overlays */}
          {seppOverlays.length > 0 && (
            <Section title="SEPP Overlays">
              <div className="space-y-1">
                {seppOverlays.map((sepp) => (
                  <div key={sepp.name} className="text-sm text-gray-700 p-2 bg-gray-50 rounded">
                    <span className="font-medium">{sepp.name}</span>
                    {sepp.labels.length > 0 && (
                      <span className="text-gray-500"> &mdash; {sepp.labels.join(', ')}</span>
                    )}
                  </div>
                ))}
              </div>
              {result.outputs.housing_sepp && (
                <p className="text-xs text-teal-600 mt-2">SEPP (Housing) 2021 applies to this property</p>
              )}
              {result.outputs.tod_area && (
                <p className="text-xs text-teal-600 mt-1">Transport Oriented Development precinct &mdash; height and density uplift may be available</p>
              )}
            </Section>
          )}

          {/* EPI flags */}
          {(result.outputs.flood_epi || result.outputs.riparian_epi || result.outputs.ass_class) && (
            <Section title="EPI Flags">
              <div className="space-y-2">
                {result.outputs.flood_epi && (
                  <Flag type="warn" text="Property is within an EPI flood planning area" />
                )}
                {result.outputs.riparian_epi && (
                  <Flag type="warn" text="Riparian land &mdash; waterway corridor setbacks apply" />
                )}
                {result.outputs.ass_class && (
                  <Flag type="warn" text={`Acid sulfate soils: ${result.outputs.ass_class}`} />
                )}
              </div>
            </Section>
          )}

          {/* Feasibility assessment */}
          {result.outputs.feasibility.length > 0 && (
            <Section title="Development Feasibility">
              <div className="space-y-3">
                {result.outputs.feasibility.map((item, i) => {
                  const meta = FLAG_META[item.flag] || FLAG_META.warn;
                  return (
                    <div key={i} className={`p-4 rounded-lg ${meta.bg}`}>
                      <div className="flex items-start gap-2">
                        <span className={`text-sm font-bold ${meta.text}`}>{meta.icon}</span>
                        <div className="flex-1">
                          <div className="flex items-baseline justify-between">
                            <p className={`text-sm font-medium ${meta.text}`}>{item.question}</p>
                            <span className={`text-xs font-semibold ${meta.text}`}>{item.answer}</span>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">{item.basis}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Section>
          )}

          {/* Nearby DAs summary — three-state: not assessed / found / none.
              "could not be checked" must never render as a false "none nearby". */}
          {(result.outputs.da_fetch_failed || result.outputs.da_count == null) ? (
            <Section title="Nearby Development Activity">
              <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
                We couldn&rsquo;t complete the nearby development-application check for this
                address. This does <span className="font-medium">not</span> mean there are none
                nearby &mdash; it means the check didn&rsquo;t run, so we&rsquo;re not showing a
                count either way. Try again shortly, or check another address.
              </div>
            </Section>
          ) : result.outputs.da_count > 0 ? (
            <Section title="Nearby Development Activity">
              <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
                {result.outputs.da_count} development application{result.outputs.da_count !== 1 ? 's' : ''} found within 200m of this property.
                <a
                  href={`/reports/threat-radar?address=${encodeURIComponent(result.address)}`}
                  className="ml-1 underline hover:text-blue-900"
                >
                  View full DA details &rarr;
                </a>
              </div>
            </Section>
          ) : (
            <Section title="Nearby Development Activity">
              <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
                No development applications found within 200m of this property.
              </div>
            </Section>
          )}

          {/* PDF upsell */}
          <div className="border border-gray-200 rounded-xl p-6 bg-white">
            <h3 className="text-base font-semibold text-gray-900 mb-2">
              Full Conveyancing Planning Disclosure Report
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              A 10-15 page PDF report suitable for conveyancing due diligence,
              including DCP setback controls, shadow risk analysis, heritage detail,
              nearby DA summaries, and development headroom calculations with clause citations.
            </p>

            <FreePaidComparison
              free={[
                'LEP zone, height, FSR, lot size',
                'Environmental and hazard overlays',
                'SEPP overlay identification',
                'Title type detection',
                'Heritage status',
                'Development feasibility screening',
              ]}
              paid={[
                'DCP setback controls with clause references',
                'Shadow risk analysis (ADG compliance)',
                'Full nearby DA summary with descriptions',
                'LEP key sites clause interpretation',
                'PostGIS heritage conservation area detail',
                'Land value history (5 years)',
                'Development headroom calculations',
                'Professional-grade PDF with data citations',
              ]}
            />

            <div className="mt-5">
              {unlockedReportId ? (
                <p className="text-xs text-teal-700">
                  Early access — the full PDF report is unlocked in the panel above.
                </p>
              ) : (
                <WaitlistButton interestType="conveyancing" address={result.address} />
              )}
            </div>
          </div>

          {/* Data sources */}
          <div className="text-center pt-4">
            <p className="text-xs text-gray-400">
              Data: {result.data_sources.join(' · ')}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Results are indicative only and do not constitute planning or legal advice.
              Always engage a registered town planner or conveyancer.
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {DATA_PROVENANCE.conveyancing}
            </p>
          </div>

          {/* Cross-sell */}
          <ToolCrossSell currentTool="conveyancing" address={result.address} />
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-900 mb-2">{title}</h3>
      {children}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="p-3 bg-gray-50 rounded-lg">
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className="text-sm font-medium text-gray-900">{value ?? 'Not available'}</p>
    </div>
  );
}

function Flag({ type, text }: { type: 'ok' | 'warn' | 'alert'; text: string }) {
  const meta = FLAG_META[type] || FLAG_META.warn;
  return (
    <div className={`flex items-center gap-2 p-2 rounded ${meta.bg}`}>
      <span className={`text-sm ${meta.text}`}>{meta.icon}</span>
      <p className={`text-sm ${meta.text}`}>{text}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ConveyancingPaidDownloadCTA — shown after Stripe payment=success redirect
// or when a named early-access grant code (?access=) validated
// ---------------------------------------------------------------------------

function ConveyancingPaidDownloadCTA({
  reportId,
  address,
  lat,
  lng,
  propId,
  grant,
}: {
  reportId: string;
  address: string;
  lat: number;
  lng: number;
  propId?: string;
  /** true when unlocked by a named early-access grant rather than payment */
  grant?: boolean;
}) {
  const [generating, setGenerating] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [dlError, setDlError] = useState('');

  const handleGenerate = async () => {
    setGenerating(true);
    setDlError('');
    try {
      const res = await fetch('/api/reports/conveyancing/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId, address, lat, lng, prop_id: propId }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const json = await res.json();
      if (!json.pdf_url) throw new Error('No PDF URL returned');
      setPdfUrl(json.pdf_url);
      window.open(json.pdf_url, '_blank');
    } catch (err: unknown) {
      setDlError(err instanceof Error ? err.message : 'Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="rounded-xl border border-teal-200 bg-teal-50 p-5">
      <p className="text-sm font-semibold text-teal-900 mb-1">
        {grant ? 'Early access — your report is ready.' : 'Payment received — your report is ready.'}
      </p>
      <p className="text-xs text-teal-700 mb-3">Click below to generate and download the full PDF report.</p>
      {pdfUrl ? (
        <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full py-2.5 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 text-center transition-colors"
        >
          Open PDF report →
        </a>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="w-full py-2.5 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {generating ? 'Generating PDF...' : 'Generate and download PDF →'}
        </button>
      )}
      {dlError && <p className="text-xs text-red-600 mt-2">{dlError}</p>}
    </div>
  );
}

function FreePaidComparison({ free, paid }: { free: string[]; paid: string[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Free instant check</p>
        <ul className="space-y-1.5">
          {free.map((item) => (
            <li key={item} className="flex items-start gap-1.5 text-xs text-gray-600">
              <span className="text-green-500 mt-0.5">&#10003;</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <p className="text-xs font-semibold text-teal-600 uppercase tracking-wider mb-2">Full PDF report</p>
        <ul className="space-y-1.5">
          {paid.map((item) => (
            <li key={item} className="flex items-start gap-1.5 text-xs text-gray-600">
              <span className="text-teal-500 mt-0.5">&#10003;</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
