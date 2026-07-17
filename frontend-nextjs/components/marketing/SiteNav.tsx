'use client';

import Link from 'next/link';

interface SiteNavProps {
  maxWidth?: string;
}

export function SiteNav({ maxWidth = 'max-w-5xl' }: SiteNavProps) {
  return (
    <nav className="bg-slate-950 border-b border-slate-800/50">
      <div className={`flex items-center justify-between px-6 py-4 ${maxWidth} mx-auto`}>
        {/* Brand home = the info site (Option B) — not the app root. */}
        <a href="https://plotdetect.com.au" className="text-base font-bold tracking-tight text-white">
          Plot<span className="text-teal-400">Detect</span>
        </a>
        <div className="flex items-center gap-6">
          <Link href="/tools/zoning-check" className="text-sm text-slate-400 hover:text-white transition-colors">
            Free Tools
          </Link>
          <Link href="/reports" className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block">
            Reports
          </Link>
          <Link href="/browse" className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block">
            Browse Councils
          </Link>
          <Link href="/blog" className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block">
            Insights
          </Link>
          <Link href="/pricing" className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block">
            Pricing
          </Link>
          <Link
            href="/assessment"
            className="hidden sm:inline-flex items-center px-4 py-1.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
          >
            Open Site Controls
          </Link>
        </div>
      </div>
    </nav>
  );
}
