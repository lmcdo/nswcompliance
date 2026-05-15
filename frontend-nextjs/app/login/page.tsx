'use client';

import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback?next=/reports`,
      },
    });

    if (error) {
      setError(error.message);
    } else {
      setSent(true);
    }
    setLoading(false);
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <span className="font-semibold text-gray-900 text-xl">Plot<span className="text-teal-600">Detect</span></span>
          <p className="mt-1 text-sm text-gray-500">Sign in to your reports</p>
        </div>

        {sent ? (
          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
            <div className="text-2xl mb-3">&#9993;</div>
            <h2 className="font-semibold text-gray-900 mb-2">Check your email</h2>
            <p className="text-sm text-gray-500">
              We sent a sign-in link to <strong>{email}</strong>. Click it to access your reports.
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 p-8">
            <h1 className="font-semibold text-gray-900 mb-1">Sign in</h1>
            <p className="text-sm text-gray-500 mb-6">
              Enter your email and we&apos;ll send a sign-in link.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
                />
              </div>

              {error && (
                <p className="text-sm text-red-600">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading || !email}
                className="w-full bg-gray-900 text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Sending...' : 'Send sign-in link'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
