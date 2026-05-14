import 'maplibre-gl/dist/maplibre-gl.css';
import type { Metadata } from 'next';
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';

export const metadata: Metadata = {
  title: 'NSW Property Intelligence — canibuildit.com.au',
  description: 'NSW property intelligence reports: granny flat eligibility, flood risk, solar yield, shadow analysis, DA activity.',
};

const NAV_ITEMS = [
  { href: '/reports/solar-yield', label: 'Solar Yield' },
  { href: '/reports/shadow', label: 'Shadow' },
  { href: '/reports/threat-radar', label: 'Threat Radar' },
  { href: '/reports/flood', label: 'Flood Truth' },
  { href: '/reports/granny-flat', label: 'Granny Flat' },
  { href: '/reports/pre-da-history', label: 'Site History' },
  { href: '/reports/conveyancing', label: 'Conveyancing' },
];

export default async function ReportsLayout({ children }: { children: React.ReactNode }) {
  if (process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true') {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      redirect('/login');
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-semibold text-gray-900 text-base tracking-tight">
              canibuildit<span className="text-teal-600">.com.au</span>
            </span>
          </Link>
          <nav className="flex items-center gap-1">
            {NAV_ITEMS.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className="px-3 py-1.5 text-sm text-gray-600 rounded-md hover:bg-gray-100 hover:text-gray-900 transition-colors"
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-10">{children}</main>
      <footer className="border-t border-gray-100 mt-16">
        <div className="max-w-5xl mx-auto px-6 py-6 flex flex-wrap items-center justify-between gap-4 text-xs text-gray-400">
          <span>© 2026 canibuildit.com.au — NSW planning intelligence</span>
          <div className="flex flex-wrap gap-4">
            <Link href="/#browse-by-area" className="hover:text-gray-600 transition-colors">Browse by area</Link>
            <Link href="/how-it-works" className="hover:text-gray-600 transition-colors">How it works</Link>
            <Link href="/pricing" className="hover:text-gray-600 transition-colors">Pricing</Link>
            <Link href="/partner" className="hover:text-gray-600 transition-colors">Embed program</Link>
            <Link href="/privacy" className="hover:text-gray-600 transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-gray-600 transition-colors">Terms</Link>
          </div>
        </div>
        <div className="max-w-5xl mx-auto px-6 pb-6">
          <p className="text-xs text-gray-300">
            Results are indicative only and do not constitute planning advice. Always consult a registered town planner or certifier before making any planning or property decision.
          </p>
        </div>
      </footer>
    </div>
  );
}
