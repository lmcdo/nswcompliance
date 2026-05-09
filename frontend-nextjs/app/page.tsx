import Link from 'next/link';

const BUYING = [
  {
    title: 'Flood Risk Check',
    detail: 'Statutory flood zone, council flood study depths, satellite water history — 71 LGAs.',
    href: '/reports/flood',
    badge: 'Free + $49 report',
    accent: 'border-blue-200 hover:border-blue-300',
  },
  {
    title: 'Bushfire Pre-Screen',
    detail: 'RFS Bush Fire Prone Land status and BAL band estimate for any NSW address.',
    href: '/reports/bushfire',
    badge: 'Free',
    accent: 'border-orange-200 hover:border-orange-300',
  },
  {
    title: 'Pre-DA Site History',
    detail: 'Eight years of satellite change detection cross-referenced with DA records and heritage overlays.',
    href: '/reports/pre-da-history',
    badge: '$49 report',
    accent: 'border-purple-200 hover:border-purple-300',
  },
];

const BUILDING = [
  {
    title: 'Granny Flat Checker',
    detail: 'SEPP eligibility, satellite structure detection, and $280–$340/week rental yield estimate.',
    href: '/reports/granny-flat',
    badge: 'Free + $49 report',
    accent: 'border-teal-200 hover:border-teal-300',
  },
  {
    title: 'Shadow Detector',
    detail: 'Shadow path analysis at 9am, noon, and 3pm on the winter solstice — worst-case envelope.',
    href: '/reports/shadow',
    badge: '$29 report',
    accent: 'border-slate-200 hover:border-slate-300',
  },
  {
    title: 'Threat Radar',
    detail: 'Every DA and CDC within 500m — with weekly email alerts for new lodgements.',
    href: '/reports/threat-radar',
    badge: 'Free',
    accent: 'border-violet-200 hover:border-violet-300',
  },
];

const YIELD = [
  {
    title: 'Solar Yield',
    detail: 'Roof geometry, orientation, and estimated annual kWh — sized before you visit the site.',
    href: '/reports/solar-yield',
    badge: '$19 report',
    accent: 'border-amber-200 hover:border-amber-300',
  },
  {
    title: 'Granny Flat Checker',
    detail: 'Could this property earn $280–$340/week extra? Zone, lot size, strata, SEPP rules — instantly.',
    href: '/reports/granny-flat',
    badge: 'Free + $49 report',
    accent: 'border-teal-200 hover:border-teal-300',
  },
];


function ToolCard({ title, detail, href, badge, accent }: {
  title: string; detail: string; href: string; badge: string; accent: string;
}) {
  return (
    <Link
      href={href}
      className={`block rounded-xl border ${accent} bg-white p-5 transition-all hover:shadow-sm`}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
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
    <main className="min-h-screen bg-[#0b1628] text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <span className="text-lg font-bold tracking-tight">
          canibuildit<span className="text-[#00d9b8]">.com.au</span>
        </span>
        <div className="flex items-center gap-6">
          <Link href="/reports" className="text-sm text-slate-400 hover:text-white transition-colors">
            All tools
          </Link>
          <Link href="/pricing" className="text-sm text-slate-400 hover:text-white transition-colors">
            Pricing
          </Link>
          <Link href="/how-it-works" className="text-sm text-slate-400 hover:text-white transition-colors">
            How it works
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-6 pt-16 pb-20 max-w-3xl mx-auto text-center">
        <h1 className="text-4xl sm:text-5xl font-bold leading-tight mb-4">
          What should you know
          <br />
          <span className="text-[#00d9b8]">before you buy, build, or insure?</span>
        </h1>
        <p className="text-slate-400 text-lg mb-6 max-w-xl mx-auto">
          Seven free property checks for any NSW address. Live government data,
          satellite imagery, and Bureau of Meteorology records. No account needed.
        </p>
        <Link
          href="/reports"
          className="inline-block px-6 py-3 bg-[#00d9b8] text-[#0b1628] font-semibold text-sm rounded-xl hover:bg-[#00c4a7] transition-colors"
        >
          Check a property →
        </Link>
      </section>

      {/* Problem-grouped tool cards */}
      <section className="bg-white text-gray-900 py-16 px-6">
        <div className="max-w-5xl mx-auto space-y-12">

          {/* Buying */}
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-1">Buying a property?</h2>
            <p className="text-sm text-gray-500 mb-4">
              Your conveyancer will ask for flood and bushfire status. Get the data before they do.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {BUYING.map((t) => <ToolCard key={t.href} {...t} />)}
            </div>
          </div>

          {/* Building */}
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-1">Planning to build?</h2>
            <p className="text-sm text-gray-500 mb-4">
              Check what&apos;s possible, what&apos;s planned nearby, and whether your build will create objections.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {BUILDING.map((t) => <ToolCard key={t.href + '-build'} {...t} />)}
            </div>
          </div>

          {/* Yield */}
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-1">Evaluating yield?</h2>
            <p className="text-sm text-gray-500 mb-4">
              Estimate income potential before you buy or before you quote.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {YIELD.map((t) => <ToolCard key={t.href + '-yield'} {...t} />)}
            </div>
          </div>

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
              { color: 'bg-blue-500',   label: 'Bureau of Meteorology' },
              { color: 'bg-amber-500',  label: 'European Space Agency' },
              { color: 'bg-violet-500', label: 'NSW ePlanning Portal' },
              { color: 'bg-slate-400',  label: 'Spatial Services NSW' },
              { color: 'bg-red-400',    label: 'NSW Rural Fire Service' },
              { color: 'bg-cyan-500',   label: 'Copernicus EMS' },
            ].map(({ color, label }) => (
              <span key={label} className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${color} inline-block`} />
                {label}
              </span>
            ))}
          </div>
          <p className="text-center text-xs text-slate-400 mt-4">
            71 council flood study areas · 8 years of satellite imagery · 128 council DA feeds
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#0b1628] py-8 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm text-slate-600">
            © 2026 canibuildit.com.au — NSW property intelligence for buyers, owners, and builders.
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
              <Link key={href} href={href} className="text-xs text-slate-600 hover:text-slate-400 transition-colors">
                {label}
              </Link>
            ))}
          </div>
        </div>
      </footer>
    </main>
  );
}
