'use client';

import Link from 'next/link';
import { useState } from 'react';

const TOOLS = [
  { label: 'Flood Risk', href: '/reports/flood', emoji: '🌊' },
  { label: 'Bushfire Pre-Screen', href: '/reports/bushfire', emoji: '🔥' },
  { label: 'Granny Flat Check', href: '/reports/granny-flat', emoji: '🏡' },
  { label: 'Pre-DA Site History', href: '/reports/pre-da-history', emoji: '🛰' },
  { label: 'Solar Yield', href: '/reports/solar-yield', emoji: '☀️' },
  { label: 'Shadow Detector', href: '/reports/shadow', emoji: '🌑' },
  { label: 'Threat Radar', href: '/reports/threat-radar', emoji: '📡' },
];

const TOP_LGAS = [
  { name: 'Inner West', slug: 'inner-west' },
  { name: 'Campbelltown', slug: 'campbelltown' },
  { name: 'Blacktown', slug: 'blacktown' },
  { name: 'Parramatta', slug: 'parramatta' },
  { name: 'Northern Beaches', slug: 'northern-beaches' },
  { name: 'Ku-ring-gai', slug: 'ku-ring-gai' },
  { name: 'Sutherland Shire', slug: 'sutherland-shire' },
  { name: 'Canterbury-Bankstown', slug: 'canterbury-bankstown' },
];

export default function ToolsLayout({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-100 relative z-20">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="font-bold text-gray-900 text-base tracking-tight">
            canibuildit<span className="text-teal-600">.com.au</span>
          </Link>

          <nav className="flex items-center gap-5">
            {/* Tools dropdown */}
            <div className="relative">
              <button
                onClick={() => setOpen(v => !v)}
                className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                Tools
                <svg className={`w-3.5 h-3.5 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {open && (
                <>
                  <div className="fixed inset-0" onClick={() => setOpen(false)} />
                  <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl border border-gray-200 shadow-lg py-1.5 z-30">
                    {TOOLS.map(tool => (
                      <Link
                        key={tool.href}
                        href={tool.href}
                        onClick={() => setOpen(false)}
                        className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <span className="text-base">{tool.emoji}</span>
                        {tool.label}
                      </Link>
                    ))}
                  </div>
                </>
              )}
            </div>

            <Link href="/pricing" className="text-sm text-gray-500 hover:text-gray-900 transition-colors hidden sm:block">
              Pricing
            </Link>
            <Link
              href="/reports"
              className="text-sm px-4 py-2 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-700 transition-colors"
            >
              All tools →
            </Link>
          </nav>
        </div>
      </header>

      <main>{children}</main>

      <footer className="border-t border-gray-100 mt-24 bg-white">
        <div className="max-w-5xl mx-auto px-6 py-12 grid grid-cols-2 sm:grid-cols-4 gap-8">

          {/* Brand */}
          <div className="col-span-2 sm:col-span-1">
            <p className="font-bold text-gray-900 text-sm tracking-tight mb-2">
              canibuildit<span className="text-teal-600">.com.au</span>
            </p>
            <p className="text-xs text-gray-400 leading-relaxed mb-3">
              NSW planning intelligence for property owners and investors.
            </p>
            <p className="text-xs text-gray-300">
              Data: NSW Planning Portal · Spatial Services NSW · Bureau of Meteorology · European Space Agency
            </p>
          </div>

          {/* Tools */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Tools</p>
            <ul className="space-y-2">
              {TOOLS.map(tool => (
                <li key={tool.href}>
                  <Link href={tool.href} className="text-xs text-gray-500 hover:text-gray-900 transition-colors">
                    {tool.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Top LGAs */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Popular areas</p>
            <ul className="space-y-2">
              {TOP_LGAS.map(lga => (
                <li key={lga.slug}>
                  <Link href={`/granny-flat/${lga.slug}`} className="text-xs text-gray-500 hover:text-gray-900 transition-colors">
                    {lga.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Company</p>
            <ul className="space-y-2">
              {[
                { label: 'How it works', href: '/how-it-works' },
                { label: 'Pricing', href: '/pricing' },
                { label: 'Embed program', href: '/partner' },
                { label: 'Contact', href: '/contact' },
                { label: 'Privacy', href: '/privacy' },
                { label: 'Terms', href: '/terms' },
              ].map(({ label, href }) => (
                <li key={href}>
                  <Link href={href} className="text-xs text-gray-500 hover:text-gray-900 transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="max-w-5xl mx-auto px-6 pb-8 border-t border-gray-50 pt-6">
          <p className="text-xs text-gray-300">
            © 2026 canibuildit.com.au — NSW planning data only. Results are indicative and do not constitute planning advice. Confirm with a registered certifier or town planner.
          </p>
        </div>
      </footer>
    </div>
  );
}
