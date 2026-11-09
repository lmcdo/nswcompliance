'use client';

import Link from 'next/link';

interface SiteNavProps {
  maxWidth?: string;
}

export function SiteNav({ maxWidth = 'max-w-5xl' }: SiteNavProps) {
  return (
    <nav className="bg-slate-950 border-b border-slate-800/50">
      <div className={`flex items-center justify-between px-6 py-4 ${maxWidth} mx-auto`}>
        <Link href="/" className="text-base font-bold tracking-tight text-white">
          Plot<span className="text-teal-400">Detect</span>
        </Link>
        <div className="flex items-center gap-6">
          <Link
            href="/reports/intelligence-brief"
            className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block"
          >
            Site Facts
          </Link>
          <Link href="/how-it-works" className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block">
            How it works
          </Link>
          <Link
            href="/assessment"
            className="hidden sm:inline-flex items-center px-4 py-1.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
          >
            Open Council Rules
          </Link>
        </div>
      </div>
    </nav>
  );
}
