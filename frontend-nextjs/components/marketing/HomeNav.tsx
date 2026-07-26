'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

export function HomeNav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-slate-950/80 backdrop-blur-md border-b border-slate-800/50'
          : 'bg-transparent'
      }`}
    >
      <div className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <Link href="/" className="text-base font-bold tracking-tight text-white">
          Plot<span className="text-teal-400">Detect</span>
        </Link>
        <div className="flex items-center gap-6">
          <Link
            href="/reports"
            className="text-sm text-slate-400 hover:text-white transition-colors"
          >
            Tools
          </Link>
          <Link
            href="/what-you-get"
            className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block"
          >
            What you get
          </Link>
          <Link
            href="/browse"
            className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block"
          >
            Browse Councils
          </Link>
          <Link
            href="/blog"
            className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block"
          >
            Insights
          </Link>
          <Link
            href="/pricing"
            className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block"
          >
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
