'use client';

import { useState, useEffect } from 'react';
import { Mail } from 'lucide-react';

interface VerifyRegistrationPromptProps {
  councilName?: string;
  address?: string;
  source?: string;
}

const ROLES = [
  { value: 'planner', label: 'Town Planner' },
  { value: 'certifier', label: 'Certifier' },
  { value: 'architect', label: 'Architect' },
  { value: 'conveyancer', label: 'Conveyancer' },
  { value: 'agent', label: 'Buyers Agent' },
  { value: 'developer', label: 'Developer' },
  { value: 'other', label: 'Other' },
];

const STORAGE_KEY = 'verify_registered';

export function VerifyRegistrationPrompt({ councilName, address, source = 'assessment' }: VerifyRegistrationPromptProps) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');
  const [dismissed, setDismissed] = useState(true); // start hidden, check storage

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      setDismissed(stored === 'true');
    } catch {
      setDismissed(false);
    }
  }, []);

  if (dismissed || status === 'done') {
    if (status === 'done') {
      return (
        <div className="bg-teal-50 border border-teal-200 rounded-lg px-4 py-3 mb-4 flex items-center gap-2">
          <Mail className="w-4 h-4 text-teal-600 flex-shrink-0" />
          <p className="text-sm text-teal-800">
            Registered — we'll notify you when new councils and features go live.
          </p>
        </div>
      );
    }
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || status === 'submitting') return;
    setStatus('submitting');
    try {
      const res = await fetch('/api/verify-interest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          role: role || undefined,
          council_name: councilName,
          address,
          source,
        }),
      });
      if (!res.ok) throw new Error();
      setStatus('done');
      try { sessionStorage.setItem(STORAGE_KEY, 'true'); } catch {}
    } catch {
      setStatus('error');
    }
  };

  const handleDismiss = () => {
    setDismissed(true);
    try { sessionStorage.setItem(STORAGE_KEY, 'true'); } catch {}
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg px-4 py-4 mb-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          <div className="w-8 h-8 bg-teal-50 border border-teal-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
            <Mail className="w-4 h-4 text-teal-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900">
              Get notified when we add more councils and export features
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              We're expanding DCP coverage across NSW. Register to hear first.
            </p>

            <form onSubmit={handleSubmit} className="mt-3 flex flex-wrap items-center gap-2">
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="your@email.com"
                required
                className="text-sm border border-gray-200 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-teal-400 bg-white placeholder:text-gray-400 w-48"
              />
              <select
                value={role}
                onChange={e => setRole(e.target.value)}
                className="text-sm border border-gray-200 rounded px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-teal-400"
              >
                <option value="">Your role (optional)</option>
                {ROLES.map(r => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
              <button
                type="submit"
                disabled={status === 'submitting'}
                className="text-sm px-4 py-1.5 rounded bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-60 transition-colors flex-shrink-0"
              >
                {status === 'submitting' ? 'Saving...' : 'Register'}
              </button>
            </form>

            {status === 'error' && (
              <p className="text-xs text-red-500 mt-1.5">Something went wrong — try again.</p>
            )}
          </div>
        </div>

        <button
          onClick={handleDismiss}
          className="text-gray-400 hover:text-gray-600 p-1 flex-shrink-0"
          aria-label="Dismiss"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
