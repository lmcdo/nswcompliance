import Link from 'next/link';

export default function NotFound() {
  const TOOLS = [
    { emoji: '🏡', label: 'Granny Flat', href: '/granny-flat', color: 'border-teal-800 hover:border-teal-600' },
    { emoji: '🌊', label: 'Flood Screening',  href: '/reports/flood',        color: 'border-blue-800 hover:border-blue-600' },
    { emoji: '☀️', label: 'Solar Yield', href: '/reports/solar-yield',  color: 'border-amber-800 hover:border-amber-600' },
    { emoji: '🌑', label: 'Shadow',      href: '/reports/shadow',       color: 'border-slate-700 hover:border-slate-500' },
    { emoji: '📡', label: 'Threat Radar',href: '/reports/threat-radar', color: 'border-violet-800 hover:border-violet-600' },
  ];

  return (
    <main className="min-h-screen bg-[#0b1628] text-white flex flex-col items-center justify-center px-6 text-center">
      {/* Logo */}
      <Link href="/" className="text-lg font-bold tracking-tight mb-16 opacity-60 hover:opacity-100 transition-opacity">
        Plot<span className="text-[#00d9b8]">Detect</span>
      </Link>

      {/* Error */}
      <p className="text-8xl font-bold text-white/10 leading-none mb-4 select-none">404</p>
      <h1 className="text-xl font-semibold text-white mb-2">Page not found</h1>
      <p className="text-sm text-slate-400 mb-12 max-w-sm">
        That address doesn&apos;t exist — but your property address probably does. Try a tool.
      </p>

      {/* Tool grid */}
      <div className="flex flex-wrap justify-center gap-3 max-w-lg mb-12">
        {TOOLS.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border ${t.color} bg-white/5 text-sm font-medium text-white transition-colors`}
          >
            <span>{t.emoji}</span>
            <span>{t.label}</span>
          </Link>
        ))}
      </div>

      <Link href="/" className="text-xs text-slate-600 hover:text-slate-400 transition-colors">
        ← Back to home
      </Link>
    </main>
  );
}
