import 'maplibre-gl/dist/maplibre-gl.css';
import type { Metadata } from 'next';
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';

export const metadata: Metadata = {
  title: 'Property Intelligence — PlotDetect',
  description: 'NSW property intelligence reports: solar yield, shadow analysis, flood risk, granny flat potential',
};

const NAV_ITEMS = [
  { href: '/reports/solar-yield', label: 'Solar Yield' },
  { href: '/reports/shadow', label: 'Shadow' },
  { href: '/reports/threat-radar', label: 'Threat Radar' },
  { href: '/reports/flood', label: 'Flood Truth' },
  { href: '/reports/granny-flat', label: 'Granny Flat' },
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
          <Link href="/reports" className="flex items-center gap-2">
            <span className="font-semibold text-gray-900 text-lg">PlotDetect</span>
            <span className="text-gray-400 text-sm font-normal">Property Intelligence</span>
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
            <form action="/auth/signout" method="post">
              <button
                type="submit"
                className="ml-3 px-3 py-1.5 text-sm text-gray-400 hover:text-gray-600 transition-colors"
              >
                Sign out
              </button>
            </form>
          </nav>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-10">{children}</main>
    </div>
  );
}
