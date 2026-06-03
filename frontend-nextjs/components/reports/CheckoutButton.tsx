'use client';

import { useState } from 'react';
import { PaymentTermsNotice } from './PaymentTermsNotice';

interface CheckoutButtonProps {
  /** Stripe checkout API route, e.g. '/api/stripe/checkout/flood-truth' */
  checkoutPath: string;
  /** POST body sent to the checkout route (shape varies per product) */
  body: Record<string, string>;
  /** Price shown on the button, e.g. "$49" or "$9.99/mo" */
  priceLabel: string;
  /** Override the default CTA label */
  label?: string;
  /** When true, renders an email input — required for subscriptions */
  requiresEmail?: boolean;
  className?: string;
}

/**
 * Redirects to Stripe Checkout for a satellite-product report or subscription.
 * Each tool provides its own checkout path and body shape.
 */
export function CheckoutButton({
  checkoutPath,
  body,
  priceLabel,
  label,
  requiresEmail = false,
  className = '',
}: CheckoutButtonProps) {
  const [email, setEmail] = useState('');
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const handleCheckout = async () => {
    if (requiresEmail) {
      const trimmed = email.trim();
      if (!trimmed || !trimmed.includes('@')) {
        setErrorMsg('Enter a valid email address.');
        return;
      }
    }
    setState('loading');
    setErrorMsg('');
    try {
      const finalBody = requiresEmail
        ? { ...body, email: email.trim() }
        : body;
      const res = await fetch(checkoutPath, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(finalBody),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(json.error || 'Failed to start checkout');
      }
      const { checkout_url } = await res.json();
      if (checkout_url) {
        window.location.href = checkout_url;
      } else {
        throw new Error('No checkout URL returned');
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong');
      setState('error');
    }
  };

  const buttonLabel = label ?? `Buy report — ${priceLabel}`;

  return (
    <div className={`space-y-2 ${className}`}>
      {requiresEmail && (
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="your@email.com"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
          disabled={state === 'loading'}
          autoComplete="email"
        />
      )}
      <button
        onClick={handleCheckout}
        disabled={state === 'loading'}
        className="w-full px-5 py-3 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {state === 'loading' ? 'Redirecting to checkout…' : buttonLabel}
      </button>
      {errorMsg && <p className="text-xs text-red-600">{errorMsg}</p>}
      <PaymentTermsNotice />
    </div>
  );
}
