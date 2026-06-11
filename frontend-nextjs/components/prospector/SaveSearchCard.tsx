'use client';

/**
 * Email capture card for /prospector — the conversion step of the launch
 * funnel (pageview -> prospector_search -> email capture).
 *
 * Reuses the existing /api/verify-interest endpoint (verify_interest table,
 * (email, source) upsert) with source='prospector'. The current filter query
 * string is stored in the address field so the search context is kept with
 * the lead.
 */

import React, { useState } from 'react';
import { Mail } from 'lucide-react';

import { trackProspectorEmailCapture } from '@/lib/analytics';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Mirrors VALID_ROLES in app/api/verify-interest/route.ts
const ROLE_OPTIONS = [
  { value: 'developer', label: 'Developer' },
  { value: 'planner', label: 'Town planner' },
  { value: 'architect', label: 'Architect' },
  { value: 'agent', label: 'Buyers / real estate agent' },
  { value: 'conveyancer', label: 'Conveyancer' },
  { value: 'certifier', label: 'Certifier' },
  { value: 'other', label: 'Other' },
] as const;

type Status = 'idle' | 'submitting' | 'done' | 'error';

export function SaveSearchCard({
  lgaName,
  filterQuery,
}: {
  lgaName: string;
  filterQuery: string;
}) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!EMAIL_REGEX.test(trimmed)) {
      setErrorMsg('Enter a valid email address');
      setStatus('error');
      return;
    }
    setStatus('submitting');
    setErrorMsg(null);
    try {
      const res = await fetch('/api/verify-interest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: trimmed,
          role: role || null,
          source: 'prospector',
          council_name: lgaName,
          address: filterQuery ? `/prospector?${filterQuery}` : '/prospector',
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(
          typeof data?.error === 'string' ? data.error : 'Something went wrong — try again',
        );
      }
      setStatus('done');
      trackProspectorEmailCapture({
        lga: lgaName,
        has_filters: filterQuery.length > 0,
        role: role || null,
      });
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong — try again');
      setStatus('error');
    }
  };

  if (status === 'done') {
    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-sm text-emerald-800">
        Saved. We will email you when new areas and data layers go live for this search.
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-1">
        <Mail size={16} className="text-gray-400" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-gray-900">Save this search</h2>
      </div>
      <p className="text-xs text-gray-500 mb-3">
        Statewide coverage is rolling out. Leave your email and we will let you know when new
        council areas and data layers go live for these filters.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <label htmlFor="prospector-email" className="sr-only">
          Email address
        </label>
        <input
          id="prospector-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={status === 'submitting'}
        />
        <label htmlFor="prospector-role" className="sr-only">
          Your role
        </label>
        <select
          id="prospector-role"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={status === 'submitting'}
        >
          <option value="">Your role (optional)</option>
          {ROLE_OPTIONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={status === 'submitting'}
          className="w-full px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {status === 'submitting' ? 'Saving…' : 'Notify me'}
        </button>
        {status === 'error' && errorMsg && (
          <p className="text-xs text-red-600" role="alert">
            {errorMsg}
          </p>
        )}
      </form>
    </div>
  );
}
