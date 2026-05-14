import Link from 'next/link';
import { BrowseByArea } from '@/components/BrowseByArea';

const BUYING = [
  {
    title: 'Flood Risk Check',
    detail: 'Statutory flood zone, council flood study depths, satellite water history — 71 LGAs.',
    href: '/reports/flood',
    badge: 'Free + $49 report',
    icon: '🌊',
  },
  {
    title: 'Bushfire Pre-Screen',
    detail: 'RFS Bush Fire Prone Land status and BAL band estimate for any NSW address.',
    href: '/reports/bushfire',
    badge: 'Free',
    icon: '🔥',
  },
  {
    title: 'Pre-DA Site History',
    detail: 'Eight years of satellite change detection cross-referenced with DA records and heritage overlays.',
    href: '/reports/pre-da-history',
    badge: '$49 report',
    icon: '📡',
  },
  {
    title: 'Conveyancing Disclosure',
    detail: 'LEP controls, overlays, heritage, SEPP, development feasibility — the planning check your conveyancer should do.',
    href: '/reports/conveyancing',
    badge: 'Free + $49 report',
    icon: '📋',
  },
];

const BUILDING = [
  {
    title: 'Planning Controls',
    detail: 'Full SEPP, LEP, and DCP controls for your property — setbacks, parking, height, landscaping with clause citations.',
    href: '/assessment',
    badge: 'Free',
    icon: '📐',
  },
  {
    title: 'Granny Flat Checker',
    detail: 'SEPP eligibility, satellite structure detection, and $280–$340/week rental yield estimate.',
    href: '/reports/granny-flat',
    badge: 'Free + $49 report',
    icon: '🏠',
  },
  {
    title: 'Shadow Detector',
    detail: 'Shadow path analysis at 9am, noon, and 3pm on the winter solstice — worst-case envelope.',
    href: '/reports/shadow',
    badge: '$29 report',
    icon: '🌑',
  },
  {
    title: 'Threat Radar',
    detail: 'Every DA and CDC within 500m — with weekly email alerts for new lodgements.',
    href: '/reports/threat-radar',
    badge: 'Free',
    icon: '📡',
  },
];

const YIELD = [
  {
    title: 'Solar Yield',
    detail: 'Roof geometry, orientation, and estimated annual kWh — sized before you visit the site.',
    href: '/reports/solar-yield',
    badge: '$19 report',
    icon: '☀️',
  },
  {
    title: 'Granny Flat Checker',
    detail: 'Could this property earn $280–$340/week extra? Zone, lot size, strata, SEPP rules — instantly.',
    href: '/reports/granny-flat',
    badge: 'Free + $49 report',
    icon: '🏠',
  },
];

const DATA_SOURCES = [
  { color: 'bg-teal-500', label: 'NSW Planning Portal' },
  { color: 'bg-blue-500', label: 'Bureau of Meteorology' },
  { color: 'bg-amber-500', label: 'European Space Agency' },
  { color: 'bg-violet-500', label: 'NSW ePlanning Portal' },
  { color: 'bg-slate-400', label: 'Spatial Services NSW' },
  { color: 'bg-red-400', label: 'NSW Rural Fire Service' },
  { color: 'bg-cyan-500', label: 'Copernicus EMS' },
];

const TESTIMONIALS = [
  {
    quote: 'Saved us from buying a property with 1.2m flood depth. The council flood map showed nothing.',
    author: 'Sarah T.',
    role: 'Homebuyer, Lismore',
    initials: 'ST',
    color: 'bg-teal-100 text-teal-700',
  },
  {
    quote: 'I use this for every valuation now. The satellite data catches things the paperwork misses.',
    author: 'James K.',
    role: 'Property Valuer',
    initials: 'JK',
    color: 'bg-blue-100 text-blue-700',
  },
  {
    quote: 'Client was about to proceed with a purchase. This report changed their mind — and saved them.',
    author: 'Michelle R.',
    role: 'Conveyancer, Sydney',
    initials: 'MR',
    color: 'bg-purple-100 text-purple-700',
  },
];

function ToolCard({ title, detail, href, badge, icon }: {
  title: string; detail: string; href: string; badge: string; icon: string;
}) {
  return (
    <Link
      href={href}
      className="block rounded-xl border border-gray-200 bg-white p-5 transition-all hover:border-gray-300 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-base">{icon}</span>
          <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
        </div>
        <span className="shrink-0 text-[11px] font-medium text-gray-500 bg-gray-50 px-2 py-0.5 rounded-full">
          {badge}
        </span>
      </div>
      <p className="text-xs text-gray-500 leading-relaxed">{detail}</p>
    </Link>
  );
}

export default function HomePage() {
  return (
    <main className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-gray-100">
        <div className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
          <Link href="/" className="text-lg font-bold tracking-tight text-gray-900">
            canibuildit<span className="text-teal-600">.com.au</span>
          </Link>
          <div className="flex items-center gap-6">
            <Link href="/reports" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
              All tools
            </Link>
            <Link href="/pricing" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
              Pricing
            </Link>
            <Link href="/how-it-works" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
              How it works
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero — no search bar, direct intent routing */}
      <section className="px-6 pt-20 pb-16 max-w-3xl mx-auto text-center">
        <div className="mb-6 flex justify-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 px-4 py-1.5 text-sm font-medium text-teal-700">
            <span className="w-2 h-2 rounded-full bg-teal-500" />
            Nine free checks for any NSW address
          </div>
        </div>

        <h1 className="text-4xl sm:text-5xl font-bold leading-tight text-gray-900 mb-4">
          What should you know{' '}
          <span className="text-teal-600">before you buy, build, or insure?</span>
        </h1>

        <p className="text-gray-500 text-lg mb-10 max-w-xl mx-auto">
          Live government data, satellite imagery, and Bureau of Meteorology records. Pick a tool below, enter any NSW address, and get results in seconds.
        </p>

        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/reports/flood" className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors">
            Flood Risk Check
          </Link>
          <Link href="/reports/bushfire" className="px-5 py-2.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all">
            Bushfire Pre-Screen
          </Link>
          <Link href="/reports/granny-flat" className="px-5 py-2.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all">
            Granny Flat Checker
          </Link>
          <Link href="/reports/threat-radar" className="px-5 py-2.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all">
            Threat Radar
          </Link>
          <Link href="/reports/shadow" className="px-5 py-2.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all">
            Shadow Detector
          </Link>
          <Link href="/reports/solar-yield" className="px-5 py-2.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all">
            Solar Yield
          </Link>
          <Link href="/reports/conveyancing" className="px-5 py-2.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all">
            Conveyancing Disclosure
          </Link>
          <Link href="/assessment" className="px-5 py-2.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all">
            Planning Controls
          </Link>
        </div>
      </section>

      {/* Data sources strip */}
      <section className="border-y border-gray-100 bg-gray-50 py-8 px-6">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-xs text-gray-400 uppercase tracking-widest mb-5 font-medium">
            Data sourced from
          </p>
          <div className="flex flex-wrap justify-center gap-x-6 gap-y-2.5 text-sm text-gray-500">
            {DATA_SOURCES.map(({ color, label }) => (
              <span key={label} className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${color} inline-block`} />
                {label}
              </span>
            ))}
          </div>
          <div className="flex justify-center gap-10 mt-6">
            <div className="text-center">
              <div className="text-xl font-bold text-gray-900">71 LGAs</div>
              <div className="text-xs text-gray-400">Council flood study areas</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-gray-900">8 years</div>
              <div className="text-xs text-gray-400">Of satellite imagery</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-gray-900">128 councils</div>
              <div className="text-xs text-gray-400">DA feed integrations</div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem-grouped tool cards */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto space-y-14">
          {/* Buying */}
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-1">Buying a property?</h2>
            <p className="text-sm text-gray-500 mb-5">
              Your conveyancer will ask for flood and bushfire status. Get the data before they do.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {BUYING.map((t) => <ToolCard key={t.href} {...t} />)}
            </div>
          </div>

          {/* Building */}
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-1">Planning to build?</h2>
            <p className="text-sm text-gray-500 mb-5">
              Check what&apos;s possible, what&apos;s planned nearby, and whether your build will create objections.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {BUILDING.map((t) => <ToolCard key={t.href + '-build'} {...t} />)}
            </div>
          </div>

          {/* Yield */}
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-1">Evaluating yield?</h2>
            <p className="text-sm text-gray-500 mb-5">
              Estimate income potential before you buy or before you quote.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-[calc(66.666%+0.375rem)]">
              {YIELD.map((t) => <ToolCard key={t.href + '-yield'} {...t} />)}
            </div>
          </div>
        </div>
      </section>

      {/* Social proof */}
      <section className="bg-gray-50 border-y border-gray-100 py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-xs text-gray-400 uppercase tracking-widest mb-2 font-medium">
            Trusted by professionals
          </p>
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-10">
            47,000+ properties checked
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {TESTIMONIALS.map((t) => (
              <div key={t.author} className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex gap-0.5 mb-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <span key={i} className="text-amber-400 text-sm">&#9733;</span>
                  ))}
                </div>
                <p className="text-sm text-gray-700 leading-relaxed mb-4">
                  &ldquo;{t.quote}&rdquo;
                </p>
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full ${t.color} flex items-center justify-center text-xs font-bold`}>
                    {t.initials}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{t.author}</p>
                    <p className="text-xs text-gray-400">{t.role}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Browse by area */}
      <BrowseByArea />

      {/* Data source footer strip */}
      <section className="border-t border-gray-100 bg-gray-50 py-8 px-6">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-xs text-gray-400 uppercase tracking-widest mb-4 font-medium">
            Data sources
          </p>
          <div className="flex flex-wrap justify-center gap-x-6 gap-y-2.5 text-sm text-gray-500">
            {DATA_SOURCES.map(({ color, label }) => (
              <span key={label} className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${color} inline-block`} />
                {label}
              </span>
            ))}
          </div>
          <p className="text-center text-xs text-gray-400 mt-3">
            71 council flood study areas · 8 years of satellite imagery · 128 council DA feeds
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm text-gray-500">
            &copy; 2026 canibuildit.com.au &mdash; NSW property intelligence for buyers, owners, and builders.
          </p>
          <p className="text-xs text-gray-400 mt-2">
            Results are indicative only and do not constitute planning advice. Always consult a registered town planner or certifier.
          </p>
          <p className="text-xs text-gray-500 mt-3">
            Questions?{' '}
            <a href="mailto:hello@canibuildit.com.au" className="text-gray-600 hover:text-gray-900 transition-colors underline underline-offset-2">
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
              <Link key={href} href={href} className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
                {label}
              </Link>
            ))}
          </div>
        </div>
      </footer>
    </main>
  );
}
