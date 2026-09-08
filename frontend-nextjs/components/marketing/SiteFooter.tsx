'use client';

import Link from 'next/link';

const TOOL_LINKS = [
  { label: 'Flood Screening', href: '/reports/flood' },
  { label: 'Bushfire Pre-Screen', href: '/reports/bushfire' },
  { label: 'Conveyancing Disclosure', href: '/reports/conveyancing' },
  { label: 'Granny Flat Yield', href: '/reports/granny-flat' },
  { label: 'Shadow Analyser', href: '/reports/shadow' },
  { label: 'Solar Yield', href: '/reports/solar-yield' },
  { label: 'Threat Radar', href: '/reports/threat-radar' },
  { label: 'Pre-DA Site History', href: '/reports/pre-da-history' },
];

const FREE_TOOL_LINKS = [
  { label: 'Zoning Check', href: '/tools/zoning-check' },
  { label: 'Subdivision Check', href: '/tools/subdivision-check' },
  { label: 'CDC Eligibility', href: '/check' },
];

const PLATFORM_LINKS = [
  { label: 'What You Get', href: '/what-you-get' },
  { label: 'Site Controls', href: '/assessment' },
  { label: 'Scout (Map Explorer)', href: 'https://map.plotdetect.com.au' },
  { label: 'Validate (DA Analytics)', href: 'https://charts.plotdetect.com.au' },
  { label: 'Climate Risk', href: '/climate-risk' },
  { label: 'Browse Councils', href: '/browse' },
  { label: 'Planning Glossary', href: '/glossary' },
  { label: 'SEPP Housing Standards', href: '/planning-standards' },
  { label: 'Open Data', href: '/open-data' },
  { label: 'Insights', href: '/blog' },
];

const COMPANY_LINKS = [
  { label: 'How it works', href: '/how-it-works' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'For Homeowners', href: '/for/homebuyers' },
  { label: 'For Buyers Agents', href: '/for/buyers-agents' },
  { label: 'For Conveyancers', href: '/for/conveyancers' },
  { label: 'For Builders', href: '/for/builders' },
  { label: 'For Planners', href: '/for/planners' },
  { label: 'For Students', href: '/for/students' },
  { label: 'Developers / API', href: '/developers' },
  { label: 'Contact', href: '/contact' },
  { label: 'Site directory', href: '/site-directory' },
  { label: 'Privacy', href: '/privacy' },
  { label: 'Terms', href: '/terms' },
];

const DATA_SOURCES = [
  'NSW Planning Portal',
  'Bureau of Meteorology',
  'European Space Agency',
  'NSW Rural Fire Service',
  'Copernicus EMS',
  'NARCliM 2.0',
  'Spatial Services NSW',
];

export function SiteFooter() {
  return (
    <footer className="bg-slate-950 border-t border-slate-800/50">
      <div className="max-w-5xl mx-auto px-6 py-12 grid grid-cols-2 sm:grid-cols-4 gap-8">
        {/* Brand */}
        <div className="col-span-2 sm:col-span-1">
          <Link href="/" className="text-base font-bold tracking-tight text-white mb-3 block">
            Plot<span className="text-teal-400">Detect</span>
          </Link>
          <p className="text-xs text-slate-500 leading-relaxed">
            NSW property intelligence. Flood, bushfire, planning controls,
            and climate projections for any address.
          </p>
        </div>

        {/* Tools */}
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Tools
          </p>
          <ul className="space-y-2">
            {FREE_TOOL_LINKS.map(({ label, href }) => (
              <li key={href}>
                <Link
                  href={href}
                  className="text-sm text-slate-400 hover:text-white transition-colors"
                >
                  {label} <span className="text-teal-500 text-xs">Free</span>
                </Link>
              </li>
            ))}
            {TOOL_LINKS.map(({ label, href }) => (
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

        {/* Platform */}
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Platform
          </p>
          <ul className="space-y-2">
            {PLATFORM_LINKS.map(({ label, href }) => (
              <li key={href}>
                {href.startsWith('http') ? (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-slate-400 hover:text-white transition-colors"
                  >
                    {label}
                  </a>
                ) : (
                  <Link
                    href={href}
                    className="text-sm text-slate-400 hover:text-white transition-colors"
                  >
                    {label}
                  </Link>
                )}
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

      {/* Data sources + copyright */}
      <div className="border-t border-slate-800/50">
        <div className="max-w-5xl mx-auto px-6 py-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <p className="text-xs text-slate-600">
            &copy; {new Date().getFullYear()} PlotDetect &mdash; NSW property intelligence
          </p>
          <p className="text-xs text-slate-600">
            Data: {DATA_SOURCES.join(' \u00B7 ')}
          </p>
        </div>
      </div>
    </footer>
  );
}
