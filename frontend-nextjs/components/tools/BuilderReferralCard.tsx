'use client';

// Multi-step, qualify-first lead capture. Design is evidence-based (see
// ~/.claude/plans/ce-lead-qualifier-research-2026-07.md):
//   - Qualify BEFORE asking for contact details (CXL: +20% conversion, no
//     quality loss) — foot-in-the-door / sunk-cost carries the user to the end.
//   - One question per screen, tap-to-select buttons (no keyboard on mobile).
//   - Kept deliberately SHORT (2 questions + contact): timeline is the strongest
//     intent signal, ownership filters out renters/non-decision-makers. Finance
//     and budget are add-backs once funnel data shows completion holds up.
//   - Consent is UNBUNDLED, un-ticked, names the recipient, and is stored with
//     its exact wording/version as an audit record (OAIC burden of proof).
// The computed verdict is never altered by this card; it renders below it.

import { useEffect, useState } from 'react';
import posthog from 'posthog-js';
import { trackAdsConversion } from '@/lib/gtag';

type Verdict = 'eligible' | 'needs-checking';

interface Props {
  address: string;
  lgaName: string | null;
  /** Which result this card sits under — changes the copy, never the offer. */
  verdict?: Verdict;
}

interface Opt {
  v: string;
  l: string;
}

const TIMELINE: Opt[] = [
  { v: 'asap', l: 'As soon as possible' },
  { v: '1-3m', l: '1–3 months' },
  { v: '3-6m', l: '3–6 months' },
  { v: '6-12m', l: '6–12 months' },
  { v: 'researching', l: '12+ months / just researching' },
];
const OWNERSHIP: Opt[] = [
  { v: 'owner', l: 'I own it' },
  { v: 'buying', l: 'I’m buying it' },
  { v: 'other', l: 'Agent / someone else' },
];

// Bump when the consent wording below changes — stored with each lead so we can
// always show a regulator the exact statement a given person agreed to.
const CONSENT_VERSION = '2026-07-19';

const STEPS = ['timeline', 'ownership', 'contact'] as const;
const TOTAL = STEPS.length;

export function BuilderReferralCard({ address, lgaName, verdict = 'eligible' }: Props) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [firstName, setFirstName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [shareConsent, setShareConsent] = useState(false);
  const [status, setStatus] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    posthog.capture('referral_cta_view', { tool: 'upzoning-check', verdict });
  }, [verdict]);

  const recipient = verdict === 'eligible' ? 'duplex builder' : 'duplex specialist';
  const shareWording =
    `Share my name, contact details, this address and result with a ${recipient} ` +
    `in my area so they can contact me about this property. PlotDetect may receive a referral fee.`;

  const heading =
    verdict === 'eligible'
      ? 'Talk to a builder about what a duplex here would cost'
      : 'Get a specialist to check this block properly';
  const sub =
    verdict === 'eligible'
      ? `A couple of quick taps and we’ll line up a free, no-obligation chat with a ${recipient}${lgaName ? ` in ${lgaName}` : ''} about real numbers and next steps.`
      : `The automatic check couldn’t give a clear answer. A couple of quick taps and a ${recipient}${lgaName ? ` in ${lgaName}` : ''} can look at the property-specific issue — no cost, no obligation. It doesn’t change the result above.`;

  function pick(key: string, value: string) {
    setAnswers((a) => ({ ...a, [key]: value }));
    posthog.capture('referral_qualify_step', { step: STEPS[step], value, verdict });
    setStep((s) => Math.min(s + 1, TOTAL - 1));
  }

  function goBack() {
    setStatus('idle');
    setErrorMsg(null);
    setStep((s) => Math.max(s - 1, 0));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (status === 'submitting') return;
    if (!email.trim() || !shareConsent) {
      setErrorMsg(
        !shareConsent
          ? 'Please tick the box so we can pass your details to the builder.'
          : 'Please enter your email.',
      );
      setStatus('error');
      return;
    }
    setStatus('submitting');
    setErrorMsg(null);
    try {
      const res = await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          first_name: firstName.trim() || null,
          phone: phone.trim() || null,
          address,
          eligible: verdict === 'eligible',
          lga_name: lgaName,
          interest_type: 'dual-occ-referral',
          qualification: {
            timeline: answers.timeline ?? null,
            ownership: answers.ownership ?? null,
            finance: null,
            budget: null,
          },
          consent_version: CONSENT_VERSION,
          consent_wording: shareWording,
        }),
      });
      // A non-2xx must NOT read as success — that silently loses the lead.
      if (!res.ok) throw new Error('request failed');
    } catch {
      setErrorMsg('Something went wrong sending that — please try again.');
      setStatus('error');
      return;
    }
    posthog.capture('referral_lead_submitted', {
      tool: 'upzoning-check',
      lga: lgaName,
      verdict,
      timeline: answers.timeline ?? null,
      ownership: answers.ownership ?? null,
    });
    trackAdsConversion();
    setStatus('done');
  }

  if (status === 'done') {
    return (
      <div className="rounded-xl border border-teal-200 bg-teal-50 p-5">
        <p className="text-sm text-teal-800 font-medium">
          Thanks{firstName ? `, ${firstName}` : ''} — we’ve got your request.
          We’ll email {email} to arrange the {recipient} introduction.
        </p>
      </div>
    );
  }

  const stepName = STEPS[step];

  return (
    <div className="rounded-xl border-2 border-teal-500 bg-gradient-to-br from-teal-50 to-white p-5">
      <div className="flex items-center justify-between mb-1">
        <p className="text-base font-bold text-gray-900">{heading}</p>
        {step > 0 && (
          <button
            type="button"
            onClick={goBack}
            className="text-xs text-gray-500 hover:text-gray-700 flex-shrink-0 ml-3"
          >
            ← Back
          </button>
        )}
      </div>
      {step === 0 && <p className="text-sm text-gray-600 mt-1 mb-3">{sub}</p>}

      {/* Progress */}
      <div className="mt-2 mb-4">
        <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-teal-500 transition-all duration-300"
            style={{ width: `${((step + 1) / TOTAL) * 100}%` }}
          />
        </div>
        <p className="mt-1 text-[11px] text-gray-500">Step {step + 1} of {TOTAL}</p>
      </div>

      {stepName === 'timeline' && (
        <Question label="When are you thinking of building?" opts={TIMELINE} onPick={(v) => pick('timeline', v)} />
      )}
      {stepName === 'ownership' && (
        <Question label="Do you own this property?" opts={OWNERSHIP} onPick={(v) => pick('ownership', v)} />
      )}

      {stepName === 'contact' && (
        <form onSubmit={submit} className="space-y-3">
          <p className="text-sm font-semibold text-gray-800">
            Last step — where can the {recipient} reach you?
          </p>
          <input
            type="text"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            placeholder="First name"
            className="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
          />
          <input
            type="email"
            required
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (status === 'error') { setStatus('idle'); setErrorMsg(null); }
            }}
            placeholder="you@email.com"
            className="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
          />
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Phone (optional)"
            className="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
          />
          {/* Unbundled, un-ticked, recipient named. Required to submit. */}
          <label className="flex items-start gap-2 text-xs text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={shareConsent}
              onChange={(e) => {
                setShareConsent(e.target.checked);
                if (e.target.checked && status === 'error') { setStatus('idle'); setErrorMsg(null); }
              }}
              className="mt-0.5 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
            />
            <span>{shareWording}</span>
          </label>
          <button
            type="submit"
            disabled={status === 'submitting'}
            className="w-full px-5 py-3 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-60"
          >
            {status === 'submitting' ? 'Sending…' : `Request my ${recipient} intro`}
          </button>
          {status === 'error' && errorMsg && (
            <p className="text-xs text-red-600">{errorMsg}</p>
          )}
          <p className="text-[11px] text-gray-400">
            We only share your details after you tick the box above. See our{' '}
            <a href="/privacy" className="underline hover:text-gray-600">privacy policy</a>.
          </p>
        </form>
      )}
    </div>
  );
}

function Question({ label, opts, onPick }: { label: string; opts: Opt[]; onPick: (v: string) => void }) {
  return (
    <div>
      <p className="text-sm font-semibold text-gray-800 mb-2">{label}</p>
      <div className="space-y-2">
        {opts.map((o) => (
          <button
            key={o.v}
            type="button"
            onClick={() => onPick(o.v)}
            className="w-full text-left px-4 py-2.5 rounded-lg border border-gray-200 bg-white text-sm text-gray-800 hover:border-teal-500 hover:bg-teal-50 transition-colors"
          >
            {o.l}
          </button>
        ))}
      </div>
    </div>
  );
}
