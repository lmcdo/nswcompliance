'use client';

import { useState, useEffect, useCallback } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { BushfireResultCard, type BushfireResult } from '@/components/tools/BushfireResultCard';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';
import { posthog } from '@/components/providers/PostHogProvider';
import { OperationalTransparency, type TransparencyStep } from '@/components/tools/OperationalTransparency';

const BUSHFIRE_STEPS: TransparencyStep[] = [
  { label: 'Querying RFS bushfire prone land map…',      ms: 0 },
  { label: 'Checking vegetation category…',              ms: 2000 },
  { label: 'Estimating BAL band from setback distance…', ms: 4000 },
  { label: 'Assessing 10/50 vegetation clearing rules…', ms: 7000 },
  { label: 'Checking CDC pathway eligibility…',          ms: 10000 },
];

type PageState = 'idle' | 'running' | 'complete' | 'error';

export function BushfireTool({ lgaSlug, embedRef }: { lgaSlug?: string; embedRef?: string }) {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<BushfireResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const runCheck = useCallback(async (addr: string) => {
    if (!addr.trim()) return;
    setState('running');
    setResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/bushfire', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Bushfire check failed');
      setResult(json);
      setState('complete');
      posthog.capture('tool_run', {
        tool: 'bushfire',
        source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
        embed_ref: embedRef ?? null,
        lga_slug: lgaSlug ?? null,
        result: json.outputs?.fire_signal ?? null,
      });
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
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
            Run Bushfire Check
          </button>
        </form>
      ) : (
        <div className="mb-6">
          <p className="text-sm text-gray-500">{address}</p>
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
        steps={BUSHFIRE_STEPS}
        active={state === 'running'}
        address={address}
        note="Allow 5–15 seconds."
      />

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {state === 'complete' && result && (
        <>
          <BushfireShareActions result={result} />
          <BushfireResultCard result={result} />
          <ToolCrossSell currentTool="bushfire" address={result.address} />
        </>
      )}
    </div>
  );
}

function BushfireShareActions({ result }: { result: BushfireResult }) {
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const shareUrl = result.report_id
    ? `${window.location.origin}/reports/bushfire/${result.report_id}`
    : '';

  const handleCopy = async () => {
    if (!shareUrl) return;
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePdf = async () => {
    if (!result.report_id) return;
    setDownloading(true);
    try {
      const res = await fetch('/api/reports/bushfire/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: result.report_id }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bushfire-prescreen-${result.address.replace(/[^a-zA-Z0-9]/g, '-').slice(0, 50)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
    } finally {
      setDownloading(false);
    }
  };

  if (!result.report_id) return null;

  return (
    <div className="flex gap-2 mb-4">
      <button
        onClick={handleCopy}
        className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition-colors"
      >
        {copied ? 'Copied!' : 'Share link'}
      </button>
      <button
        onClick={handlePdf}
        disabled={downloading}
        className="px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
      >
        {downloading ? 'Generating...' : 'Download PDF'}
      </button>
    </div>
  );
}
