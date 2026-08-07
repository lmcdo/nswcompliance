'use client';

import { useState, useEffect, useCallback } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { ClimateRiskResultCard, type ClimateRiskResult } from '@/components/tools/ClimateRiskResultCard';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';
import { posthog } from '@/components/providers/PostHogProvider';
import { OperationalTransparency, type TransparencyStep } from '@/components/tools/OperationalTransparency';

const CLIMATE_STEPS: TransparencyStep[] = [
  { label: 'Checking flood overlays…',                   ms: 0 },
  { label: 'Querying bushfire prone land data…',          ms: 1500 },
  { label: 'Scanning coastal erosion hazard lines…',      ms: 3000 },
  { label: 'Loading NARCliM 2.0 climate projections…',    ms: 5000 },
  { label: 'Checking fire history (NPWS)…',               ms: 7000 },
  { label: 'Assembling hazard exposure summary…',         ms: 9000 },
];

type PageState = 'idle' | 'running' | 'complete' | 'error';

export function ClimateRiskTool() {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<ClimateRiskResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const runCheck = useCallback(async (addr: string) => {
    if (!addr.trim()) return;
    setState('running');
    setResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/climate-risk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Climate risk check failed');
      setResult(json);
      setState('complete');
      // No result_score / result_band. The composite is unvalidatable and #699
      // bars it from customer surfaces, so exporting it to a third-party
      // analytics service is the same claim by another route — and it is no
      // longer in the response, so both properties would now always be null.
      posthog.capture('tool_run', {
        tool: 'climate-risk',
        source: 'direct',
      });
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  }, []);

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
    if (addrParam) {
      setAddress(addrParam);
      runCheck(addrParam);
      window.history.replaceState({}, '', window.location.pathname);
    }
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

  return (
    <div>
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
            Run Climate Check
          </button>
        </form>
      ) : (
        <div className="mb-6">
          <button
            onClick={handleReset}
            className="text-sm text-teal-600 hover:text-teal-700 transition-colors mb-4"
          >
            ← Check another address
          </button>
        </div>
      )}

      {state === 'running' && (
        <div className="py-6">
          <OperationalTransparency
            steps={CLIMATE_STEPS}
            active={state === 'running'}
            address={address}
            note="Usually completes in 10–15 seconds."
          />
        </div>
      )}

      {state === 'error' && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700 mb-6">
          {errorMsg}
        </div>
      )}

      {state === 'complete' && result && (
        <>
          <ClimateRiskResultCard result={result} />
          <div className="mt-8">
            <ToolCrossSell
              currentTool="climate-risk"
              address={result.address}
            />
          </div>
        </>
      )}
    </div>
  );
}
