'use client';

import { useState } from 'react';
import { MapPin } from 'lucide-react';

interface DCPInterestFormProps {
  councilName: string;
  address: string;
}

export function DCPInterestForm({ councilName, address }: DCPInterestFormProps) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');

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
    <div className="bg-white border border-gray-200 rounded-lg p-8">
      <div className="max-w-md mx-auto text-center">
        <div className="w-12 h-12 bg-teal-50 border border-teal-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <MapPin className="w-5 h-5 text-teal-500" />
        </div>

        <h3 className="text-base font-semibold text-gray-900 mb-1">
          {councilName} DCP not yet processed
        </h3>
        <p className="text-sm text-gray-500 mb-1">
          SEPP and Planning Controls are available now for this address.
        </p>
        <p className="text-sm text-gray-500 mb-5">
          Register below and we'll notify you when {councilName} DCP provisions go live.
        </p>

        {status === 'done' ? (
          <p className="text-sm font-medium text-teal-600">
            You're on the list — we'll email you when {councilName} DCP is ready.
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
              {status === 'submitting' ? 'Saving…' : 'Notify me'}
            </button>
          </form>
        )}

        {status === 'error' && (
          <p className="text-xs text-red-500 mt-2">Something went wrong — try again.</p>
        )}
      </div>
    </div>
  );
}
