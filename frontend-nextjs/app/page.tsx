import type { Metadata } from 'next';
import { AddressSearchForm } from '@/components/homepage/AddressSearchForm';
import { sanitizeHTML } from '@/lib/sanitize';

export const metadata: Metadata = {
  title: 'canibuildit — Free NSW Property Planning Tools',
  description: 'Check granny flat eligibility, flood risk, solar yield, shadow impact, and planning alerts for any NSW address. Free. Live data from the NSW Planning Portal.',
  openGraph: {
    title: 'canibuildit — Free NSW Property Planning Tools',
    description: 'Five free tools for any NSW address: granny flat eligibility, flood risk, solar yield, shadow analysis, and planning alerts.',
    url: 'https://canibuildit.com.au',
    siteName: 'canibuildit',
    type: 'website',
  },
  alternates: {
    canonical: 'https://canibuildit.com.au',
  },
};

const TOOLS = [
  {
    emoji: '🏡',
    title: 'Granny Flat Check',
    subtitle: 'Could this property earn $280–$340/week extra?',
    detail: 'Zone, lot size, strata, and SEPP Housing 2021 eligibility — instantly.',
    href: '/granny-flat',
    cta: 'Check eligibility',
    accent: 'teal',
  },
  {
    emoji: '🌊',
    title: 'Flood Risk',
    subtitle: 'Is this property flood-affected under the LEP?',
    detail: 'Flood control lot status, ARI category, and planning implications.',
    href: '/reports/flood',
    cta: 'Check flood risk',
    accent: 'blue',
  },
  {
    emoji: '☀️',
    title: 'Solar Yield',
    subtitle: 'How much solar can this roof generate?',
    detail: 'Roof geometry, orientation, and estimated annual kWh yield.',
    href: '/reports/solar-yield',
    cta: 'Estimate yield',
    accent: 'amber',
  },
  {
    emoji: '🌑',
    title: 'Shadow Detector',
    subtitle: 'Will a proposed addition cause overshadowing?',
    detail: 'Shadow path analysis at 9am, noon, and 3pm on June 21.',
    href: '/reports/shadow',
    cta: 'Run analysis',
    accent: 'slate',
  },
  {
    emoji: '📡',
    title: 'Threat Radar',
    subtitle: 'What developments are planned nearby?',
    detail: 'Active DAs, CDCs, and rezoning proposals within 500m.',
    href: '/reports/threat-radar',
    cta: 'Scan area',
    accent: 'violet',
  },
];

const ACCENT: Record<string, { border: string; bg: string; cta: string; icon: string }> = {
  teal:   { border: 'border-teal-200',   bg: 'hover:bg-teal-50',   cta: 'bg-teal-600 hover:bg-teal-700',     icon: 'bg-teal-100' },
  blue:   { border: 'border-blue-200',   bg: 'hover:bg-blue-50',   cta: 'bg-blue-600 hover:bg-blue-700',     icon: 'bg-blue-100' },
  amber:  { border: 'border-amber-200',  bg: 'hover:bg-amber-50',  cta: 'bg-amber-500 hover:bg-amber-600',   icon: 'bg-amber-100' },
  slate:  { border: 'border-slate-200',  bg: 'hover:bg-slate-50',  cta: 'bg-slate-700 hover:bg-slate-800',   icon: 'bg-slate-100' },
  violet: { border: 'border-violet-200', bg: 'hover:bg-violet-50', cta: 'bg-violet-600 hover:bg-violet-700', icon: 'bg-violet-100' },
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  name: 'canibuildit',
  url: 'https://canibuildit.com.au',
  description: 'Five free NSW property planning tools: granny flat eligibility, flood risk, solar yield, shadow analysis, and planning alerts.',
  applicationCategory: 'RealEstateApplication',
  operatingSystem: 'Web',
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'AUD',
  },
  areaServed: {
    '@type': 'State',
    name: 'New South Wales',
    addressCountry: 'AU',
  },
};

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#0b1628] text-white">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: sanitizeHTML(JSON.stringify(jsonLd)) }}
      />

      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <span className="text-lg font-bold tracking-tight">
          canibuildit<span className="text-[#00d9b8]">.com.au</span>
        </span>
        <div className="flex items-center gap-6">
          <a href="/pricing" className="text-sm text-slate-400 hover:text-white transition-colors">
            Pricing
          </a>
          <a href="/granny-flat" className="text-sm text-slate-400 hover:text-white transition-colors">
            Try the tools →
          </a>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-6 pt-16 pb-20 max-w-3xl mx-auto text-center">
        <h1 className="text-4xl sm:text-5xl font-bold leading-tight mb-4">
          Could this property earn
          <br />
          <span className="text-[#00d9b8]">an extra $280–$340/week?</span>
        </h1>
        <p className="text-slate-400 text-lg mb-10 max-w-xl mx-auto">
          Check granny flat eligibility for any NSW address — free. Plus flood risk,
          solar yield, shadow analysis, and planning alerts.
        </p>

        <AddressSearchForm />

        <p className="text-xs text-slate-600 mt-3">
          Starts the Granny Flat Check — pick any tool below for other questions.
        </p>
      </section>

      {/* Tool cards */}
      <section className="bg-white text-gray-900 py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-2">Five tools. One address.</h2>
          <p className="text-center text-gray-500 text-sm mb-10">
            Live data from the NSW Planning Portal — no stale PDFs, no guesswork.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
            {TOOLS.slice(0, 3).map((tool) => {
              const a = ACCENT[tool.accent];
              return (
                <a
                  key={tool.href}
                  href={tool.href}
                  className={`rounded-2xl border ${a.border} ${a.bg} p-6 flex flex-col gap-3 transition-colors`}
                >
                  <div className={`w-10 h-10 rounded-xl ${a.icon} flex items-center justify-center text-xl`}>
                    {tool.emoji}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{tool.title}</h3>
                    <p className="text-sm text-gray-500 mt-0.5">{tool.subtitle}</p>
                  </div>
                  <p className="text-xs text-gray-400 flex-1">{tool.detail}</p>
                  <span className={`inline-block self-start mt-auto px-4 py-1.5 ${a.cta} text-white text-xs font-medium rounded-lg transition-colors`}>
                    {tool.cta}
                  </span>
                </a>
              );
            })}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {TOOLS.slice(3).map((tool) => {
              const a = ACCENT[tool.accent];
              return (
                <a
                  key={tool.href}
                  href={tool.href}
                  className={`rounded-2xl border ${a.border} ${a.bg} p-6 flex flex-col gap-3 transition-colors`}
                >
                  <div className={`w-10 h-10 rounded-xl ${a.icon} flex items-center justify-center text-xl`}>
                    {tool.emoji}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{tool.title}</h3>
                    <p className="text-sm text-gray-500 mt-0.5">{tool.subtitle}</p>
                  </div>
                  <p className="text-xs text-gray-400 flex-1">{tool.detail}</p>
                  <span className={`inline-block self-start mt-auto px-4 py-1.5 ${a.cta} text-white text-xs font-medium rounded-lg transition-colors`}>
                    {tool.cta}
                  </span>
                </a>
              );
            })}
          </div>
        </div>
      </section>

      {/* Browse by area */}
      <section className="bg-gray-50 border-t border-gray-100 py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-1">Browse by council area</h2>
          <p className="text-sm text-gray-500 mb-8">
            Select an LGA to run any tool — results are instant, address-specific, and free.
          </p>

          <div className="space-y-8">
            {[
              {
                region: 'Greater Sydney — Inner & East',
                lgas: [
                  { name: 'Inner West', slug: 'inner-west' },
                  { name: 'Bayside', slug: 'bayside' },
                  { name: 'Randwick', slug: 'randwick' },
                  { name: 'Waverley', slug: 'waverley' },
                  { name: 'Woollahra', slug: 'woollahra' },
                ],
              },
              {
                region: 'Greater Sydney — North',
                lgas: [
                  { name: 'Northern Beaches', slug: 'northern-beaches' },
                  { name: 'Ku-ring-gai', slug: 'ku-ring-gai' },
                  { name: 'Hornsby', slug: 'hornsby' },
                  { name: 'Lane Cove', slug: 'lane-cove' },
                  { name: 'Ryde', slug: 'ryde' },
                ],
              },
              {
                region: 'Greater Sydney — West',
                lgas: [
                  { name: 'Parramatta', slug: 'parramatta' },
                  { name: 'Blacktown', slug: 'blacktown' },
                  { name: 'The Hills Shire', slug: 'the-hills-shire' },
                  { name: 'Penrith', slug: 'penrith' },
                  { name: 'Hawkesbury', slug: 'hawkesbury' },
                ],
              },
              {
                region: 'Greater Sydney — South & Southwest',
                lgas: [
                  { name: 'Campbelltown', slug: 'campbelltown' },
                  { name: 'Camden', slug: 'camden' },
                  { name: 'Liverpool', slug: 'liverpool' },
                  { name: 'Sutherland Shire', slug: 'sutherland-shire' },
                  { name: 'Georges River', slug: 'georges-river' },
                  { name: 'Canterbury-Bankstown', slug: 'canterbury-bankstown' },
                ],
              },
              {
                region: 'Regional NSW',
                lgas: [
                  { name: 'Wollongong', slug: 'wollongong' },
                  { name: 'Wingecarribee', slug: 'wingecarribee' },
                  { name: 'Clarence Valley', slug: 'clarence-valley' },
                  { name: 'Yass Valley', slug: 'yass-valley' },
                  { name: 'Bathurst Regional', slug: 'bathurst-regional' },
                  { name: 'Tamworth Regional', slug: 'tamworth-regional' },
                  { name: 'Forbes', slug: 'forbes' },
                ],
              },
            ].map(({ region, lgas }) => (
              <div key={region}>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">{region}</p>
                <div className="flex flex-wrap gap-2">
                  {lgas.map(({ name, slug }) => (
                    <a
                      key={slug}
                      href={`/granny-flat/${slug}`}
                      className="text-sm px-4 py-2 rounded-xl border border-gray-200 bg-white text-gray-700 hover:border-teal-400 hover:text-teal-700 transition-colors"
                    >
                      {name}
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <p className="mt-8 text-xs text-gray-400">
            Each page includes granny flat eligibility, solar yield, shadow check, and planning alerts for that council area.
          </p>
        </div>
      </section>

      {/* Trust strip */}
      <section className="bg-slate-50 border-t border-slate-100 py-10 px-6">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-xs text-slate-500 uppercase tracking-widest mb-6 font-medium">
            Data sources
          </p>
          <div className="flex flex-wrap justify-center gap-x-8 gap-y-3 text-sm text-slate-500">
            {[
              { color: 'bg-teal-500',   label: 'NSW Planning Portal' },
              { color: 'bg-blue-500',   label: 'NSW Flood Data Service' },
              { color: 'bg-amber-500',  label: 'Google Earth Engine' },
              { color: 'bg-violet-500', label: 'NSW ePlanning Portal' },
              { color: 'bg-slate-400',  label: 'Spatial Services NSW' },
            ].map(({ color, label }) => (
              <span key={label} className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${color} inline-block`} />
                {label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#0b1628] py-8 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm text-slate-600">
            © 2026 canibuildit.com.au — NSW planning intelligence for property owners and builders.
          </p>
          <p className="text-xs text-slate-700 mt-2">
            Results are indicative only and do not constitute planning advice. Always consult a registered town planner or certifier.
          </p>
          <p className="text-xs text-slate-600 mt-3">
            Questions?{' '}
            <a href="mailto:hello@canibuildit.com.au" className="text-slate-400 hover:text-slate-200 transition-colors underline underline-offset-2">
              hello@canibuildit.com.au
            </a>
          </p>
          <div className="flex flex-wrap justify-center gap-5 mt-4">
            {[
              { href: '/how-it-works', label: 'How it works' },
              { href: '/pricing', label: 'Pricing' },
              { href: '/partner', label: 'Embed program' },
              { href: '/contact', label: 'Contact' },
              { href: '/privacy', label: 'Privacy' },
              { href: '/terms', label: 'Terms' },
            ].map(({ href, label }) => (
              <a key={href} href={href} className="text-xs text-slate-600 hover:text-slate-400 transition-colors">
                {label}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </main>
  );
}
