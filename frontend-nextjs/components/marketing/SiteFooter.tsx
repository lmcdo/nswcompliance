'use client';

import Link from 'next/link';

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

export function SiteFooter() {
  return (
    <footer className="bg-slate-950 border-t border-slate-800/50">
      <div className="max-w-5xl mx-auto px-6 py-12 grid grid-cols-2 sm:grid-cols-4 gap-8">
        {/* Brand */}
        <div className="col-span-2">
          <Link href="/" className="text-base font-bold tracking-tight text-white mb-3 block">
            Plot<span className="text-teal-400">Detect</span>
          </Link>
          <p className="text-xs text-slate-500 leading-relaxed">
            NSW planning information for a single address: the council&apos;s own rules and the
            mapped facts about the property.
          </p>
        </div>

        {/* Products */}
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Products
          </p>
          <ul className="space-y-2">
            {PRODUCT_LINKS.map(({ label, href }) => (
              <li key={href}>
                <Link
                  href={href}
                  className="text-sm text-slate-400 hover:text-white transition-colors"
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Company */}
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Company
          </p>
          <ul className="space-y-2">
            {COMPANY_LINKS.map(({ label, href }) => (
              <li key={href}>
                <Link
                  href={href}
                  className="text-sm text-slate-400 hover:text-white transition-colors"
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Copyright */}
      <div className="border-t border-slate-800/50">
        <div className="max-w-5xl mx-auto px-6 py-6">
          <p className="text-xs text-slate-600">
            &copy; {new Date().getFullYear()} PlotDetect &mdash; NSW planning information
          </p>
        </div>
      </div>
    </footer>
  );
}
