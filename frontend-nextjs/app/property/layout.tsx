import 'maplibre-gl/dist/maplibre-gl.css';
// ^ must be imported in a server component to avoid dynamic chunk 404 (see AerialTile.tsx)
import Link from 'next/link';

export default function PropertyLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-slate-950 border-b border-slate-800/50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-semibold text-white text-base tracking-tight">
              Plot<span className="text-teal-400">Detect</span>
            </span>
          </Link>
          <nav className="flex items-center gap-6">
            <Link href="/reports" className="text-sm text-slate-400 hover:text-white transition-colors">
              All tools
            </Link>
            <Link href="/pricing" className="text-sm text-slate-400 hover:text-white transition-colors">
              Pricing
            </Link>
          </nav>
        </div>
      </header>
      <main>{children}</main>
      <footer className="bg-slate-950 border-t border-slate-800/50 mt-16">
        <div className="max-w-5xl mx-auto px-6 py-6 text-center">
          <p className="text-xs text-slate-500">
            Results are indicative only and do not constitute planning advice. Always consult a registered town planner or certifier.
          </p>
        </div>
      </footer>
    </div>
  );
}
