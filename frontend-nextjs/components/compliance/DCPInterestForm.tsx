'use client';

import { useState, useEffect } from 'react';
import { MapPin } from 'lucide-react';

interface DCPInterestFormProps {
  councilName: string;
  address: string;
}

export function DCPInterestForm({ councilName, address }: DCPInterestFormProps) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');
  const [showCoverage, setShowCoverage] = useState(false);
  const [structuredCouncils, setStructuredCouncils] = useState<string[]>([]);

  useEffect(() => {
    if (!showCoverage || structuredCouncils.length > 0) return;
    fetch('/api/dcp/coverage')
      .then(r => r.json())
      .then(d => setStructuredCouncils(d.councils ?? []))
      .catch(() => {});
  }, [showCoverage, structuredCouncils.length]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || status === 'submitting') return;
    setStatus('submitting');
    try {
      const res = await fetch('/api/dcp-interest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), council_name: councilName, address }),
      });
      if (!res.ok) throw new Error();
      setStatus('done');
    } catch {
      setStatus('error');
    }
  };

  return (
    <div className="space-y-4">
      {/* Interest form */}
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        <div className="max-w-md mx-auto text-center">
          <div className="w-12 h-12 bg-teal-50 border border-teal-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <MapPin className="w-5 h-5 text-teal-500" />
          </div>

          <h3 className="text-base font-semibold text-gray-900 mb-1">
            {councilName} DCP not yet processed
          </h3>
          <p className="text-sm text-gray-500 mb-1">
            SEPP and LEP controls are available now for this address.
          </p>
          <p className="text-sm text-gray-500 mb-5">
            Register below and we&apos;ll notify you when {councilName} DCP provisions go live.
          </p>

          {status === 'done' ? (
            <p className="text-sm font-medium text-teal-600">
              You&apos;re on the list — we&apos;ll email you when {councilName} DCP is ready.
            </p>
          ) : (
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="your@email.com"
                required
                className="flex-1 text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-teal-400 bg-white placeholder:text-gray-400"
              />
              <button
                type="submit"
                disabled={status === 'submitting'}
                className="text-sm px-4 py-2 rounded bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-60 transition-colors flex-shrink-0"
              >
                {status === 'submitting' ? 'Saving\u2026' : 'Notify me'}
              </button>
            </form>
          )}

          {status === 'error' && (
            <p className="text-xs text-red-500 mt-2">Something went wrong — try again.</p>
          )}
        </div>
      </div>

      {/* Coverage summary */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <button
          onClick={() => setShowCoverage(!showCoverage)}
          className="w-full px-5 py-3 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
        >
          <span className="text-sm font-medium text-gray-700">
            Which councils have DCP data?
          </span>
          <span className="text-xs text-gray-400">
            {showCoverage ? 'Hide' : 'Show'} coverage
          </span>
        </button>

        {showCoverage && (
          <div className="px-5 pb-5 border-t border-gray-100 pt-4 space-y-4">
            {/* Full structured DCP */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-teal-500" />
                <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Full structured DCP
                </span>
              </div>
              <p className="text-xs text-gray-500 mb-2">
                Complete provision text with TOC browser, PDF page images, topic filters, and precinct-specific controls.
              </p>
              <span className="text-xs px-2.5 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
                Inner West (Ashfield, Marrickville, Leichhardt)
              </span>
            </div>

            {/* Numeric controls */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Numeric DCP controls
                </span>
              </div>
              <p className="text-xs text-gray-500 mb-2">
                Setbacks, parking rates, landscaping, height, and site coverage with DCP clause citations.
              </p>
              <div className="flex flex-wrap gap-1.5">
                {structuredCouncils.length > 0 ? (
                  structuredCouncils.map(c => (
                    <span key={c} className="text-xs px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                      {c}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-gray-400">Loading coverage...</span>
                )}
              </div>
            </div>

            {/* All NSW */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-gray-400" />
                <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  All NSW addresses
                </span>
              </div>
              <p className="text-xs text-gray-500">
                SEPP and LEP controls are available for every NSW address — zoning, height limits, floor space ratio,
                heritage, minimum lot size, and spatial overlays. DCP provisions are being added council by council.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
