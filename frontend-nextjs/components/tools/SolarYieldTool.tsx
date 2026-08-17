'use client';

import { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { WaitlistButton } from '@/components/reports/WaitlistButton';
import { DATA_PROVENANCE } from '@/lib/disclaimers';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';
import { posthog } from '@/components/providers/PostHogProvider';
import { OperationalTransparency, type TransparencyStep } from '@/components/tools/OperationalTransparency';
import { deliveredKwhFrom, deliveryBasisText } from '@/lib/solar/delivered';

const SOLAR_STEPS: TransparencyStep[] = [
  { label: 'Detecting roof geometry from satellite imagery…', ms: 0 },
  { label: 'Calculating optimal panel layout…',              ms: 2000 },
  { label: 'Modelling annual solar irradiance…',             ms: 4000 },
  { label: 'Estimating energy yield and savings…',           ms: 7000 },
];

const AerialTile = dynamic(
  () => import('@/components/reports/AerialTile').then(m => m.AerialTile),
  { ssr: false, loading: () => <div className="w-full bg-gray-100 animate-pulse" style={{ height: 220 }} /> }
);

interface SolarYieldOutputs {
  max_panels: number;
  max_panel_area_m2: number;
  annual_kwh_estimate: number;             // DC at the panel, as Google reports it
  annual_kwh_delivered?: number | null;    // after system losses — monetise THIS
  delivery_basis?: string | null;
  sunshine_hours_per_year: number;
  best_pitch_deg: number;
  best_azimuth_deg: number;
  roof_area_m2: number;
  is_heritage: boolean;
  is_commercial_scale: boolean;
  imagery_date: string;
  coverage_available: boolean;
}

interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

interface ReportData {
  product: string;
  address: string;
  lat: number;
  lng: number;
  lot_polygon: GeoJSONPolygon | null;
  run_date: string;
  outputs: SolarYieldOutputs;
  confidence: string;
  data_sources: string[];
  report_token?: string;
  report_id?: string;
}

type PageState = 'idle' | 'running' | 'complete' | 'error' | 'ineligible';

const PANEL_WATTS        = 400;
const RETAIL_RATE        = 0.32;   // $/kWh — matches solar-yield generate route
const FEED_IN_TARIFF     = 0.06;   // $/kWh
const SELF_CONSUME_RATIO = 0.30;
const COST_PER_WATT      = 1.00;   // $/W installed

function solarGrade(pitch: number, azimuth: number, sunshineHours: number): {
  grade: string; colour: string; reason: string;
  pitchLabel: string; azLabel: string; sunLabel: string;
} {
  const pitchScore =
    pitch >= 15 && pitch <= 30 ? 3 :
    pitch >= 8  && pitch < 15  ? 2 :
    pitch >= 30 && pitch <= 40 ? 2 : 1;

  const pitchLabel =
    pitchScore === 3 ? 'ideal' :
    pitchScore === 2 ? 'acceptable' : 'flat/steep';

  const northDev = Math.min(azimuth, 360 - azimuth);
  const azScore =
    northDev <= 30  ? 3 :
    northDev <= 60  ? 2 :
    northDev <= 90  ? 1 : 0;

  const azLabel =
    azScore === 3 ? 'north-facing' :
    azScore === 2 ? 'partial north' :
    azScore === 1 ? 'east/west'    : 'south-facing';

  const sunScore =
    sunshineHours >= 1700 ? 3 :
    sunshineHours >= 1500 ? 2 :
    sunshineHours >= 1300 ? 1 : 0;

  const sunLabel =
    sunScore === 3 ? 'high' :
    sunScore === 2 ? 'good' :
    sunScore === 1 ? 'moderate' : 'low';

  const total = pitchScore + azScore + sunScore;

  if (total >= 8) return { grade: 'A', colour: 'text-emerald-700 bg-emerald-50', reason: 'Excellent solar potential', pitchLabel, azLabel, sunLabel };
  if (total >= 6) return { grade: 'B', colour: 'text-teal-700 bg-teal-50',       reason: 'Good solar potential',      pitchLabel, azLabel, sunLabel };
  if (total >= 4) return { grade: 'C', colour: 'text-yellow-700 bg-yellow-50',   reason: 'Moderate solar potential',  pitchLabel, azLabel, sunLabel };
  if (total >= 2) return { grade: 'D', colour: 'text-orange-700 bg-orange-50',   reason: 'Below-average solar potential', pitchLabel, azLabel, sunLabel };
  return           { grade: 'F', colour: 'text-red-700 bg-red-50',               reason: 'Poor solar potential',      pitchLabel, azLabel, sunLabel };
}

function azimuthLabel(deg: number): string {
  if (deg >= 337.5 || deg < 22.5) return 'N';
  if (deg < 67.5) return 'NE';
  if (deg < 112.5) return 'E';
  if (deg < 157.5) return 'SE';
  if (deg < 202.5) return 'S';
  if (deg < 247.5) return 'SW';
  if (deg < 292.5) return 'W';
  return 'NW';
}

export function SolarYieldTool({ lgaSlug, embedRef }: { lgaSlug?: string; embedRef?: string }) {
  const [address, setAddress] = useState('');
  const [inputAddress, setInputAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [report, setReport] = useState<ReportData | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [ineligible, setIneligible] = useState<{ error: string; evidence?: string; evidence_label?: string } | null>(null);

  const [paidReportId, setPaidReportId] = useState<string | null>(null);

  const runCheck = useCallback(async (addr: string) => {
    if (!addr.trim()) return;
    setInputAddress(addr.trim());
    setState('running');
    setReport(null);
    setErrorMsg('');
    setIneligible(null);

    try {
      const res = await fetch('/api/satellite/solar-yield', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr }),
      });
      const json = await res.json();
      if (!res.ok) {
        if (json.ineligible) {
          setIneligible({ error: json.error, evidence: json.evidence, evidence_label: json.evidence_label });
          setState('ineligible');
          return;
        }
        throw new Error(json.error || 'Failed to run report');
      }
      setReport(json.data);
      setState('complete');
      posthog.capture('tool_run', {
        tool: 'solar-yield',
        source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
        embed_ref: embedRef ?? null,
        lga_slug: lgaSlug ?? null,
        result: json.data?.outputs?.coverage_available ? 'coverage_available' : 'no_coverage',
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(msg);
      setState('error');
    }
  }, [embedRef, lgaSlug]);

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
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [runCheck]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runCheck(address);
  };

  const handleReset = () => {
    setAddress('');
    setInputAddress('');
    setState('idle');
    setReport(null);
    setErrorMsg('');
    setIneligible(null);
    setPaidReportId(null);
    window.dispatchEvent(new CustomEvent('landing-reset'));
  };

  return (
    <div className="mb-8">
      {state === 'idle' || state === 'error' ? (
        <form id="tool-input" onSubmit={handleSubmit} className="flex gap-3 mb-8">
          <AddressAutocomplete
            value={address}
            onChange={setAddress}
            onSelect={(addr) => setAddress(addr)}
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={!address.trim()}
            className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Run Report
          </button>
        </form>
      ) : (
        <div className="mb-6">
          <p className="text-sm text-gray-500">{inputAddress || address}</p>
          <button
            type="button"
            onClick={handleReset}
            className="text-sm text-teal-600 hover:text-teal-700 font-medium mt-1"
          >
            Search new address
          </button>
        </div>
      )}

      <OperationalTransparency
        steps={SOLAR_STEPS}
        active={state === 'running'}
        address={address}
        note="Usually completes in 5–10 seconds."
      />

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {state === 'ineligible' && ineligible && (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          <div className="p-6 flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-gray-900">{inputAddress}</p>
              <button
                type="button"
                onClick={() => { setState('idle'); setIneligible(null); setAddress(''); }}
                className="text-xs text-teal-600 hover:text-teal-700 underline mt-1"
              >
                Check another address
              </button>
            </div>
            <span className="shrink-0 text-xs font-medium px-2 py-1 rounded-full bg-amber-100 text-amber-800">
              Not assessable
            </span>
          </div>
          <div className="p-6">
            <p className="text-sm text-gray-700">{ineligible.error}</p>
          </div>
          {ineligible.evidence && (
            <div className="px-6 py-3 bg-gray-50">
              <p className="text-xs text-gray-400 mb-0.5">{ineligible.evidence_label || 'Source'}</p>
              <p className="text-xs font-mono text-gray-600">{ineligible.evidence}</p>
            </div>
          )}
        </div>
      )}

      {/* Payment return — show download CTA even without report in state */}
      {paidReportId && state !== 'complete' && (
        <PaidDownloadCTA reportId={paidReportId} />
      )}

      {state === 'complete' && report && (
        <>
          <ReportCard report={report} />
          {report.outputs.coverage_available && (
            <FreePaidComparison
              free={[
                'Solar suitability grade (A–F)',
                'Roof orientation + pitch analysis',
                'Annual kWh output estimate',
                'Sunshine hours assessment',
                'Heritage overlay check',
              ]}
              paid={[
                'Annual electricity savings ($)',
                'Payback period calculation',
                'System size + panel count',
                'Installed cost estimate',
                'Feed-in tariff contribution',
                'Full PDF report for installer quotes',
              ]}
            />
          )}
          {report.outputs.coverage_available && report.report_id ? (
            paidReportId ? (
              <PaidDownloadCTA reportId={paidReportId} />
            ) : (
              <SolarLockedPreviewCard outputs={report.outputs} />
            )
          ) : null}
          <ToolCrossSell currentTool="solar-yield" address={report.address} />
        </>
      )}
    </div>
  );
}

function ReportCard({ report }: { report: ReportData }) {
  const o = report.outputs;

  if (!o.coverage_available) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        <div className="p-6">
          <h2 className="font-semibold text-gray-900">{report.address}</h2>
          <p className="text-xs text-gray-400 mt-0.5">Run {report.run_date}</p>
        </div>
        <div className="p-6">
          <p className="text-sm font-medium text-gray-700 mb-1">Building data not available for this address</p>
          <p className="text-sm text-gray-500 leading-relaxed">
            Google Solar building data covers Sydney metro and major NSW cities.
            Precise roof area, panel count, and yield figures aren&apos;t available here yet.
          </p>
        </div>
        <CoverageInterestForm address={report.address} lat={report.lat} lng={report.lng} />
      </div>
    );
  }

  const systemKw = (o.max_panels * PANEL_WATTS) / 1000;
  const grade    = solarGrade(o.best_pitch_deg, o.best_azimuth_deg, o.sunshine_hours_per_year);

  // Build findings
  const findings: { label: string; value: string; detail: string; severity: 'green' | 'amber' | 'red' }[] = [];

  // Solar suitability grade
  const gradeDetail: Record<string, string> = {
    A: 'This roof has strong solar potential based on available data. North-facing with ideal pitch and strong sunshine hours — typically considered a premium site by installers.',
    B: 'Good solar potential based on available data. Minor compromises in orientation or pitch, but still a strong candidate for solar installation.',
    C: 'Moderate solar potential. The roof geometry or orientation reduces output compared to ideal. Still viable, but payback period will be longer — multiple installer quotes are advisable.',
    D: 'Below-average solar potential. Significant orientation or pitch issues will reduce output. The investment case at current panel prices may be marginal.',
    F: 'Poor solar potential. The roof geometry makes solar panels unlikely to deliver a reasonable return at current prices. A ground-mounted system or different roof face may be worth exploring.',
  };

  findings.push({
    label: 'Solar suitability assessment',
    value: `Grade ${grade.grade} — ${grade.reason.toLowerCase()}`,
    detail: gradeDetail[grade.grade] ?? gradeDetail.C,
    severity: grade.grade <= 'B' ? 'green' : grade.grade === 'C' ? 'amber' : 'red',
  });

  // Roof orientation
  const northDev = Math.min(o.best_azimuth_deg, 360 - o.best_azimuth_deg);
  if (northDev <= 30) {
    findings.push({
      label: 'Roof orientation analysis',
      value: `${azimuthLabel(o.best_azimuth_deg)}-facing at ${o.best_pitch_deg}° pitch`,
      detail: 'North-facing is ideal for solar in the Southern Hemisphere. Your panels will capture maximum sunlight throughout the day, especially in winter when the sun is lower.',
      severity: 'green',
    });
  } else if (northDev <= 90) {
    findings.push({
      label: 'Roof orientation analysis',
      value: `${azimuthLabel(o.best_azimuth_deg)}-facing at ${o.best_pitch_deg}° pitch`,
      detail: northDev <= 60
        ? 'Partially north-facing. You\'ll lose some output compared to true north, but this is still a viable orientation for solar. East-facing generates more in the morning, west in the afternoon.'
        : 'East or west-facing roof. You\'ll generate around 15–20% less than a north-facing roof. Still viable, but factor the lower yield into your payback calculations.',
      severity: 'amber',
    });
  } else {
    findings.push({
      label: 'Roof orientation analysis',
      value: `${azimuthLabel(o.best_azimuth_deg)}-facing at ${o.best_pitch_deg}° pitch`,
      detail: 'South-facing is the least productive orientation in the Southern Hemisphere. Output could be 30–40% lower than north-facing. Consider panels on a different roof face if available.',
      severity: 'red',
    });
  }

  // Annual output.
  // The headline is DELIVERED energy — what the meter records — because the
  // dollar figure beside it depends on it. Google's DC number is kept and
  // named rather than dropped, so the basis is visible instead of implied.
  const deliveredKwh = deliveredKwhFrom(o.annual_kwh_estimate, o.annual_kwh_delivered) ?? 0;
  findings.push({
    label: 'Google Solar building analysis',
    value: `${Math.round(deliveredKwh).toLocaleString('en-AU')} kWh/yr delivered from ${systemKw.toFixed(1)} kW system`,
    detail: `Your roof can fit ${o.max_panels} panels (${o.roof_area_m2.toLocaleString('en-AU')} m² usable area). ${deliveryBasisText(o.annual_kwh_estimate)} At current retail rates the delivered output is worth roughly $${Math.round(deliveredKwh * RETAIL_RATE).toLocaleString('en-AU')}/yr before feed-in adjustments. An installer's quote will state the figure for the specific hardware.`,
    severity: deliveredKwh > 5000 ? 'green' : deliveredKwh > 2000 ? 'amber' : 'red',
  });

  // Sunshine hours
  findings.push({
    label: 'Bureau of Meteorology — solar exposure data',
    value: `${o.sunshine_hours_per_year.toLocaleString('en-AU')} sunshine hours per year`,
    detail: o.sunshine_hours_per_year >= 1700
      // "at or above nameplate capacity for much of the year" was false and is
      // removed: a panel's nameplate rating is measured at 25°C cell
      // temperature, and NSW roof cells run well above that whenever the sun is
      // strong, so output sits BELOW nameplate in exactly the conditions the
      // sentence claimed it would exceed it.
      ? 'Above-average sunshine for NSW. More sunshine hours raise annual output. Nameplate ratings are measured at 25°C cell temperature, and NSW roof cells usually run hotter than that in strong sun, so sustained output typically sits below nameplate rather than above it.'
      : o.sunshine_hours_per_year >= 1500
      ? 'Typical sunshine hours for Sydney metro. Standard solar yield assumptions apply.'
      : 'Below-average sunshine hours. This could be due to local shading, coastal cloud, or valley fog. Factor this into your installer\'s yield estimate.',
    severity: o.sunshine_hours_per_year >= 1700 ? 'green' : o.sunshine_hours_per_year >= 1300 ? 'amber' : 'red',
  });

  // Heritage
  if (o.is_heritage) {
    findings.push({
      label: 'Heritage overlay (LEP cl 5.10)',
      value: 'Heritage item or conservation area',
      detail: 'Solar panels visible from a public place may require council approval. Panels on rear or concealed roof faces are generally approvable — street-facing primary facades are often refused. Check with council before signing an installer contract.',
      severity: 'amber',
    });
  }

  // Commercial scale
  if (o.is_commercial_scale) {
    findings.push({
      label: 'Roof scale classification',
      value: `Large-scale roof — ${o.roof_area_m2.toLocaleString('en-AU')} m²`,
      detail: 'This is a commercial-scale roof. Results reflect panels within this lot boundary only. For multi-tenancy or strata sites, get a commercial energy assessment — residential installer quotes won\'t cover the full opportunity.',
      severity: 'amber',
    });
  }

  const sevColor = { green: 'bg-green-500', amber: 'bg-amber-400', red: 'bg-red-500' };

  return (
    <div className="bg-white rounded-xl border border-gray-200">

      {/* Header */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <h2 className="font-semibold text-gray-900 text-base">{report.address}</h2>
          <div className={`flex flex-col items-center px-3 py-2 rounded-lg shrink-0 ${grade.colour}`}>
            <span className="text-[10px] font-semibold uppercase tracking-wide opacity-60 leading-none mb-1">Suitability</span>
            <span className="text-xl font-bold leading-none">{grade.grade}</span>
          </div>
        </div>
        <p className="text-sm text-gray-600">
          {grade.reason} — {systemKw.toFixed(1)} kW system potential across {o.max_panels} panels.
        </p>
      </div>

      {/* Findings */}
      <div className="border-t border-gray-100 divide-y divide-gray-50">
        {findings.map(({ label, value, detail, severity }) => (
          <div key={label} className="px-5 py-4">
            <div className="flex items-center gap-2.5 mb-1">
              <span className={`shrink-0 w-2.5 h-2.5 rounded-full ${sevColor[severity]}`} />
              <span className="text-sm font-medium text-gray-900">{value}</span>
            </div>
            <p className="text-xs text-gray-500 ml-5 leading-relaxed">{detail}</p>
            <p className="text-[11px] text-gray-400 ml-5 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Aerial tile */}
      <div className="border-t border-gray-100" style={{ height: 220 }}>
        <AerialTile lat={report.lat} lng={report.lng} lotPolygon={report.lot_polygon} />
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Screening tool — not financial advice. Actual savings depend on consumption, tariff, and system performance. Get installer quotes before committing.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          {DATA_PROVENANCE.solar}
        </p>
      </div>
    </div>
  );
}

function CoverageInterestForm({ address, lat, lng }: { address: string; lat: number; lng: number }) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');
  const [suburb, setSuburb] = useState('your area');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setStatus('submitting');
    try {
      const res = await fetch('/api/satellite/solar-coverage-interest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, address, lat, lng }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error);
      if (json.suburb) setSuburb(json.suburb);
      setStatus('done');
    } catch {
      setStatus('error');
    }
  };

  if (status === 'done') {
    return (
      <div className="px-6 py-5 bg-teal-50">
        <p className="text-sm font-medium text-teal-800">You&apos;re on the list.</p>
        <p className="text-xs text-teal-700 mt-0.5">
          We&apos;ll email you when full roof analysis reaches {suburb}.
        </p>
      </div>
    );
  }

  return (
    <div className="px-6 py-5 bg-gray-50">
      <p className="text-sm font-medium text-gray-700 mb-0.5">
        Get notified when we expand to {address.match(/,\s*([^,]+?)\s+NSW/i)?.[1] ?? 'your area'}
      </p>
      <p className="text-xs text-gray-500 mb-3">
        We&apos;re rolling out building-level analysis across NSW. One email when it&apos;s ready — no spam.
      </p>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="your@email.com"
          disabled={status === 'submitting'}
          className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent disabled:opacity-50"
          required
        />
        <button
          type="submit"
          disabled={status === 'submitting' || !email.trim()}
          className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          {status === 'submitting' ? 'Saving...' : 'Notify me'}
        </button>
      </form>
      {status === 'error' && (
        <p className="text-xs text-red-600 mt-1">Something went wrong. Please try again.</p>
      )}
    </div>
  );
}

function FreePaidComparison({ free, paid }: { free: string[]; paid: string[] }) {
  return (
    <div className="mt-4 bg-white rounded-xl border border-gray-200 p-5">
      <div className="grid grid-cols-2 gap-6">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Included free</p>
          <ul className="space-y-2">
            {free.map((item) => (
              <li key={item} className="flex items-start gap-2 text-xs text-gray-700">
                <span className="shrink-0 mt-0.5 w-4 h-4 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-[10px] font-bold">✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">In paid report</p>
          <ul className="space-y-2">
            {paid.map((item) => (
              <li key={item} className="flex items-start gap-2 text-xs text-gray-500">
                <span className="shrink-0 mt-0.5 w-4 h-4 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center text-[10px]">🔒</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SolarLockedPreviewCard — blur-to-reveal with real computed financial values
// ---------------------------------------------------------------------------

function SolarLockedPreviewCard({
  outputs,
}: {
  outputs: SolarYieldOutputs;
}) {
  const systemKw        = (outputs.max_panels * PANEL_WATTS) / 1000;
  // Savings and payback come from DELIVERED energy. Using Google's DC figure
  // here overstated the annual saving by 16% and understated payback by more
  // than a year.
  const annualKwh       = deliveredKwhFrom(outputs.annual_kwh_estimate,
                                           outputs.annual_kwh_delivered) ?? 0;
  const selfConsumed    = annualKwh * SELF_CONSUME_RATIO;
  const exported        = annualKwh * (1 - SELF_CONSUME_RATIO);
  const annualSavings   = (selfConsumed * RETAIL_RATE) + (exported * FEED_IN_TARIFF);
  const systemCost      = systemKw * 1000 * COST_PER_WATT;
  const paybackYears    = systemCost / annualSavings;

  const fmt = (n: number, prefix = '') =>
    prefix + Math.round(n).toLocaleString('en-AU');

  const rows = [
    { label: 'Annual electricity savings',  preview: `$${fmt(annualSavings)} / yr` },
    { label: 'Payback period',              preview: `${paybackYears.toFixed(1)} years` },
    { label: `System size — ${systemKw.toFixed(1)} kW`, preview: `${outputs.max_panels} panels` },
    { label: 'Installed cost estimate',     preview: `$${fmt(systemCost)}` },
    { label: 'Feed-in contribution',        preview: `$${fmt(exported * FEED_IN_TARIFF)} / yr` },
    { label: 'Full PDF report',             preview: 'solar-yield-report.pdf' },
  ];

  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden">
      <div className="bg-amber-50 border-b border-amber-100 px-5 py-4">
        <p className="text-sm font-semibold text-amber-900 leading-snug">
          {fmt(annualKwh)} kWh / yr delivered — see the full financial case
        </p>
        <p className="text-xs text-amber-700 mt-1 leading-relaxed">
          Your installer will ask for panel count, system size, and payback period before quoting.
          Your numbers are below — unlocked with one payment.
        </p>
      </div>

      <div className="bg-white px-5 pt-4 pb-3">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
          Your solar financials
        </p>
        <div className="space-y-2">
          {rows.map(({ label, preview }) => (
            <div key={label} className="flex items-center justify-between gap-4 text-sm">
              <span className="text-gray-700">{label}</span>
              <span className="blur-sm select-none pointer-events-none font-medium text-gray-900 tabular-nums">
                {preview}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white px-5 pb-5 pt-2">
        <WaitlistButton interestType="solar-yield" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PaidDownloadCTA — shown after Stripe redirects back with payment=success
// ---------------------------------------------------------------------------

function PaidDownloadCTA({ reportId }: { reportId: string }) {
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState('');

  const handleDownload = async () => {
    setDownloading(true);
    setDlError('');
    try {
      const res = await fetch('/api/reports/solar-yield/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `solar-yield-report-${reportId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setDlError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="mt-4 rounded-xl border border-teal-200 bg-teal-50 p-5">
      <p className="text-sm font-semibold text-teal-900 mb-1">Payment confirmed — your report is ready.</p>
      <p className="text-xs text-teal-700 mb-3">A copy is also on its way to your email.</p>
      <button
        onClick={handleDownload}
        disabled={downloading}
        className="w-full py-2.5 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {downloading ? 'Preparing download...' : 'Download PDF report →'}
      </button>
      {dlError && <p className="text-xs text-red-600 mt-2">{dlError}</p>}
    </div>
  );
}
