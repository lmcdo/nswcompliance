import 'maplibre-gl/dist/maplibre-gl.css';
import type { Metadata } from 'next';
import { Fraunces } from 'next/font/google';
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { REPORTS_LAYOUT_FOOTER } from '@/lib/disclaimers';

// Display face for report/section titles — a characterful serif that gives the
// reports the read of a produced dossier rather than default UI chrome. Exposed
// as a CSS variable so pages opt in per element (body text stays the app sans).
const fraunces = Fraunces({
  subsets: ['latin'],
  weight: ['500', '600'],
  style: ['normal'],
  variable: '--font-display',
});

export const metadata: Metadata = {
  title: 'NSW Property Intelligence — PlotDetect',
  description: 'NSW property intelligence reports: granny flat eligibility, flood risk, solar yield, shadow analysis, DA activity.',
};

const NAV_ITEMS = [
  { href: '/reports/intelligence-brief', label: 'Intelligence Brief' },
  { href: '/reports/solar-yield', label: 'Solar Yield' },
  { href: '/reports/shadow', label: 'Shadow' },
  { href: '/reports/threat-radar', label: 'Development Monitoring' },
  { href: '/reports/flood', label: 'Flood Screening' },
  { href: '/reports/granny-flat', label: 'Granny Flat' },
  { href: '/reports/pre-da-history', label: 'Site History' },
  { href: '/reports/bushfire', label: 'Bushfire' },
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
    <div className={`min-h-screen bg-slate-50 ${fraunces.variable}`}>
      <header className="bg-slate-950 border-b border-slate-800/50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Brand home is the info site (Option B domain split) — the logo must
              lead out of the app, not loop back into it. */}
          <a href="https://plotdetect.com.au" className="flex items-center gap-2">
            <span className="font-semibold text-white text-base tracking-tight">
              Plot<span className="text-teal-400">Detect</span>
            </span>
          </a>
          <nav className="flex items-center gap-1 overflow-x-auto">
            {NAV_ITEMS.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className="px-3 py-1.5 text-sm text-slate-400 rounded-md hover:bg-slate-800 hover:text-white transition-colors"
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-10">{children}</main>
      <footer className="bg-slate-950 border-t border-slate-800/50 mt-16">
        <div className="max-w-5xl mx-auto px-6 py-6 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
          <span>&copy; {new Date().getFullYear()} PlotDetect &mdash; NSW property intelligence</span>
          <div className="flex flex-wrap gap-4">
            <Link href="/how-it-works" className="hover:text-slate-300 transition-colors">How it works</Link>
            <Link href="/pricing" className="hover:text-slate-600 transition-colors">Pricing</Link>
            <Link href="/for/builders" className="hover:text-slate-300 transition-colors">Embed program</Link>
            <Link href="/site-directory" className="hover:text-slate-300 transition-colors">Site directory</Link>
            <Link href="/privacy" className="hover:text-slate-300 transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-slate-300 transition-colors">Terms</Link>
          </div>
        </div>
        <div className="max-w-5xl mx-auto px-6 pb-6">
          <p className="text-xs text-slate-600">
            {REPORTS_LAYOUT_FOOTER}
          </p>
        </div>
      </footer>
    </div>
  );
}
