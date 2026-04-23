'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

const PLACEHOLDER_ADDRESSES = [
  '14 Rosebery Ave, Rosebery NSW 2018',
  '38 Cabarita Rd, Concord NSW 2137',
  '5 Griffith St, Balmain NSW 2041',
  '22 Livingstone Rd, Marrickville NSW 2204',
  '101 Terry Rd, Eastwood NSW 2122',
];

const TOOLS = [
  {
    emoji: '🏡',
    title: 'Granny Flat Check',
    subtitle: 'Can you build a second dwelling on this lot?',
    detail: 'Zone, lot size, strata, and SEPP Housing 2021 eligibility — instantly.',
    href: '/reports/granny-flat',
    cta: 'Check eligibility',
    accent: 'teal',
  },
  {
    emoji: '🌊',
    title: 'Flood Risk',
    subtitle: 'Is this property flood-affected under the LEP?',
    detail: 'Flood control lot status, ARI category, and planning implications.',
    href: '/reports/flood',
    cta: 'Check flood risk',
    accent: 'blue',
  },
  {
    emoji: '☀️',
    title: 'Solar Yield',
    subtitle: 'How much solar can this roof generate?',
    detail: 'Roof geometry, orientation, and estimated annual kWh yield.',
    href: '/reports/solar-yield',
    cta: 'Estimate yield',
    accent: 'amber',
  },
  {
    emoji: '🌑',
    title: 'Shadow Detector',
    subtitle: 'Will a proposed addition cause overshadowing?',
    detail: 'Shadow path analysis at 9am, noon, and 3pm on June 21.',
    href: '/reports/shadow',
    cta: 'Run analysis',
    accent: 'slate',
  },
  {
    emoji: '📡',
    title: 'Threat Radar',
    subtitle: 'What developments are planned nearby?',
    detail: 'Active DAs, CDCs, and rezoning proposals within 500m.',
    href: '/reports/threat-radar',
    cta: 'Scan area',
    accent: 'violet',
  },
];

const ACCENT: Record<string, { border: string; bg: string; cta: string; icon: string }> = {
  teal:   { border: 'border-teal-200',   bg: 'hover:bg-teal-50',   cta: 'bg-teal-600 hover:bg-teal-700',     icon: 'bg-teal-100' },
  blue:   { border: 'border-blue-200',   bg: 'hover:bg-blue-50',   cta: 'bg-blue-600 hover:bg-blue-700',     icon: 'bg-blue-100' },
  amber:  { border: 'border-amber-200',  bg: 'hover:bg-amber-50',  cta: 'bg-amber-500 hover:bg-amber-600',   icon: 'bg-amber-100' },
  slate:  { border: 'border-slate-200',  bg: 'hover:bg-slate-50',  cta: 'bg-slate-700 hover:bg-slate-800',   icon: 'bg-slate-100' },
  violet: { border: 'border-violet-200', bg: 'hover:bg-violet-50', cta: 'bg-violet-600 hover:bg-violet-700', icon: 'bg-violet-100' },
};

export default function HomePage() {
  const router = useRouter();
  const [address, setAddress] = useState('');
  const [placeholder, setPlaceholder] = useState(PLACEHOLDER_ADDRESSES[0]);
  const idxRef = useRef(0);

  useEffect(() => {
    const id = setInterval(() => {
      idxRef.current = (idxRef.current + 1) % PLACEHOLDER_ADDRESSES.length;
      setPlaceholder(PLACEHOLDER_ADDRESSES[idxRef.current]);
    }, 3000);
    return () => clearInterval(id);
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!address.trim()) return;
    router.push(`/reports/granny-flat?address=${encodeURIComponent(address.trim())}`);
  }

  return (
    <main className="min-h-screen bg-[#0b1628] text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <span className="text-lg font-bold tracking-tight">
          canibuildit<span className="text-[#00d9b8]">.com.au</span>
        </span>
        <a href="/reports/granny-flat" className="text-sm text-slate-400 hover:text-white transition-colors">
          Try the tools →
        </a>
      </nav>

      {/* Hero */}
      <section className="px-6 pt-16 pb-20 max-w-3xl mx-auto text-center">
        <h1 className="text-4xl sm:text-5xl font-bold leading-tight mb-4">
          Know what you can build
          <br />
          <span className="text-[#00d9b8]">before you spend a dollar.</span>
        </h1>
        <p className="text-slate-400 text-lg mb-10 max-w-xl mx-auto">
          Five free planning tools for NSW property owners, buyers, and builders.
          No sign-up. No jargon. Real answers.
        </p>

        <form onSubmit={handleSubmit} className="flex gap-2 max-w-xl mx-auto">
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder={placeholder}
            className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-[#00d9b8] focus:border-transparent transition-all"
          />
          <button
            type="submit"
            className="px-5 py-3 bg-[#00d9b8] text-[#0b1628] font-semibold text-sm rounded-xl hover:bg-[#00c4a7] transition-colors whitespace-nowrap"
          >
            Check →
          </button>
        </form>
        <p className="text-xs text-slate-600 mt-3">
          Starts the Granny Flat Check — pick any tool below for other questions.
        </p>
      </section>

      {/* Tool cards */}
      <section className="bg-white text-gray-900 py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-2">Five tools. One address.</h2>
          <p className="text-center text-gray-500 text-sm mb-10">
            Live data from the NSW Planning Portal — no stale PDFs, no guesswork.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
            {TOOLS.slice(0, 3).map((tool) => {
              const a = ACCENT[tool.accent];
              return (
                <a
                  key={tool.href}
                  href={tool.href}
                  className={`rounded-2xl border ${a.border} ${a.bg} p-6 flex flex-col gap-3 transition-colors`}
                >
                  <div className={`w-10 h-10 rounded-xl ${a.icon} flex items-center justify-center text-xl`}>
                    {tool.emoji}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{tool.title}</h3>
                    <p className="text-sm text-gray-500 mt-0.5">{tool.subtitle}</p>
                  </div>
                  <p className="text-xs text-gray-400 flex-1">{tool.detail}</p>
                  <span className={`inline-block self-start mt-auto px-4 py-1.5 ${a.cta} text-white text-xs font-medium rounded-lg transition-colors`}>
                    {tool.cta}
                  </span>
                </a>
              );
            })}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {TOOLS.slice(3).map((tool) => {
              const a = ACCENT[tool.accent];
              return (
                <a
                  key={tool.href}
                  href={tool.href}
                  className={`rounded-2xl border ${a.border} ${a.bg} p-6 flex flex-col gap-3 transition-colors`}
                >
                  <div className={`w-10 h-10 rounded-xl ${a.icon} flex items-center justify-center text-xl`}>
                    {tool.emoji}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{tool.title}</h3>
                    <p className="text-sm text-gray-500 mt-0.5">{tool.subtitle}</p>
                  </div>
                  <p className="text-xs text-gray-400 flex-1">{tool.detail}</p>
                  <span className={`inline-block self-start mt-auto px-4 py-1.5 ${a.cta} text-white text-xs font-medium rounded-lg transition-colors`}>
                    {tool.cta}
                  </span>
                </a>
              );
            })}
          </div>
        </div>
      </section>

      {/* Trust strip */}
      <section className="bg-slate-50 border-t border-slate-100 py-10 px-6">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-xs text-slate-500 uppercase tracking-widest mb-6 font-medium">
            Data sources
          </p>
          <div className="flex flex-wrap justify-center gap-x-8 gap-y-3 text-sm text-slate-500">
            {[
              { color: 'bg-teal-500',   label: 'NSW Planning Portal' },
              { color: 'bg-blue-500',   label: 'NSW Flood Data Service' },
              { color: 'bg-amber-500',  label: 'Google Earth Engine' },
              { color: 'bg-violet-500', label: 'NSW ePlanning Portal' },
              { color: 'bg-slate-400',  label: 'Spatial Services NSW' },
            ].map(({ color, label }) => (
              <span key={label} className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${color} inline-block`} />
                {label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#0b1628] py-8 px-6 text-center">
        <p className="text-sm text-slate-600">
          © 2026 canibuildit.com.au — NSW planning intelligence for property owners and builders.
        </p>
        <p className="text-xs text-slate-700 mt-2">
          Results are indicative only and do not constitute planning advice. Always consult a registered town planner or certifier.
        </p>
      </footer>
    </main>
  );
}
