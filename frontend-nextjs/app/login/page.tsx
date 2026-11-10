'use client';

import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { safeNext } from '@/lib/auth/safe-next';

/**
 * Sign in by a 6-digit code typed on this page, with the emailed link as a second way in.
 *
 * Why a code: a magic link is single-use, and an email link scanner opens it before the person
 * does. Measured 2026-11-10 in auth.flow_state: both of the owner's links were used 15 and 26
 * seconds after sending, a login code was issued, and no session ever reached the browser — the
 * owner's own click then got "otp_expired". A code cannot be used up by something reading the email.
 */
export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function nextPath(): string {
    return safeNext(new URLSearchParams(window.location.search).get('next'));
  }

  async function sendCode(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(nextPath())}`,
        },
      });
      if (error) setError(error.message);
      else setSent(true);
    } catch {
      setError('Could not reach the sign-in service. Check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }

  async function verifyCode(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.verifyOtp({ email, token: code.trim(), type: 'email' });
      if (error) {
        setError(
          error.message.toLowerCase().includes('expired')
            ? 'That code has expired or was already used. Send a new one.'
            : error.message,
        );
        setLoading(false);
        return;
      }
      window.location.assign(nextPath());
    } catch {
      setError('Could not reach the sign-in service. Check your connection and try again.');
      setLoading(false);
    }
  }

  const input =
    'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent';
  const button =
    'w-full bg-gray-900 text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors';

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <span className="font-semibold text-gray-900 text-xl">Plot<span className="text-teal-600">Detect</span></span>
          <p className="mt-1 text-sm text-gray-500">Sign in</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-8">
          {sent ? (
            <form onSubmit={verifyCode} className="space-y-4">
              <h1 className="font-semibold text-gray-900 mb-1">Check your email</h1>
              <p className="text-sm text-gray-500">
                We sent a sign-in code to <strong>{email}</strong>. Type it below.
              </p>
              <div>
                <label htmlFor="code" className="block text-sm font-medium text-gray-700 mb-1">
                  Sign-in code
                </label>
                <input
                  id="code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="123456"
                  className={input}
                />
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <button type="submit" disabled={loading || code.trim().length < 6} className={button}>
                {loading ? 'Checking...' : 'Sign in'}
              </button>
              <button
                type="button"
                onClick={() => { setSent(false); setCode(''); setError(null); }}
                className="w-full text-sm text-gray-500 hover:text-gray-900"
              >
                Send a new code
              </button>
            </form>
          ) : (
            <form onSubmit={sendCode} className="space-y-4">
              <h1 className="font-semibold text-gray-900 mb-1">Sign in</h1>
              <p className="text-sm text-gray-500 mb-2">
                Enter your email and we&apos;ll send a sign-in code.
              </p>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className={input}
                />
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <button type="submit" disabled={loading || !email} className={button}>
                {loading ? 'Sending...' : 'Send sign-in code'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
