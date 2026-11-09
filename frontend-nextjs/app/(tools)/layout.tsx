'use client';

import Link from 'next/link';
import { TOOLS_LAYOUT_FOOTER } from '@/lib/disclaimers';

const PRODUCT_LINKS = [
  { label: 'Council Rules', href: '/assessment' },
  { label: 'Site Facts', href: '/reports/intelligence-brief' },
];

const COMPANY_LINKS = [
  { label: 'How it works', href: '/how-it-works' },
  { label: 'Contact', href: '/contact' },
  { label: 'Privacy', href: '/privacy' },
  { label: 'Terms', href: '/terms' },
];

export default function ToolsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white">
      <header className="bg-slate-950 border-b border-slate-800/50 relative z-20">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="font-bold text-white text-base tracking-tight">
            Plot<span className="text-teal-400">Detect</span>
          </Link>
          <Link
            href="/assessment"
            className="text-sm px-4 py-2 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-500 transition-colors"
          >
            Open Council Rules
          </Link>
        </div>
      </header>

      <main>{children}</main>

      <footer className="bg-slate-950 border-t border-slate-800/50 mt-24">
        <div className="max-w-5xl mx-auto px-6 py-12 grid grid-cols-2 sm:grid-cols-4 gap-8">

          {/* Brand */}
          <div className="col-span-2">
            <p className="font-bold text-white text-sm tracking-tight mb-2">
              Plot<span className="text-teal-400">Detect</span>
            </p>
            <p className="text-xs text-slate-500 leading-relaxed">
              NSW planning information for a single address: the council&apos;s own rules and the
              mapped facts about the property.
            </p>
          </div>

          {/* Products */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Products</p>
            <ul className="space-y-2">
              {PRODUCT_LINKS.map(({ label, href }) => (
                <li key={href}>
                  <Link href={href} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Company</p>
            <ul className="space-y-2">
              {COMPANY_LINKS.map(({ label, href }) => (
                <li key={href}>
                  <Link href={href} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="max-w-5xl mx-auto px-6 pb-8 border-t border-slate-800/50 pt-6">
          <p className="text-xs text-slate-600">
            {TOOLS_LAYOUT_FOOTER}
          </p>
        </div>
      </footer>
    </div>
  );
}
