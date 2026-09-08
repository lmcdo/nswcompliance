import Link from 'next/link';
import {
  Droplets, Flame, FileCheck, Building2, Radar, Sun, Moon, Satellite,
  ShieldCheck, Map, BarChart3, Thermometer, ArrowRight,
} from 'lucide-react';
import { HomeNav } from '@/components/marketing/HomeNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { HeroAddressSearch } from '@/components/marketing/HeroAddressSearch';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

/* ------------------------------------------------------------------ */
/*  Tool card data                                                     */
/* ------------------------------------------------------------------ */

const TOOLS = [
  {
    href: '/reports/flood',
    title: 'Flood Screening',
    question: 'stop',
    tagline: 'How deep does it flood — not just whether it floods.',
    badge: 'Free + $49',
    icon: Droplets,
    iconColor: 'text-blue-600',
    iconBg: 'bg-blue-500/10',
  },
  {
    href: '/reports/bushfire',
    title: 'Bushfire Pre-Screen',
    question: 'stop',
    tagline: 'Bush Fire Prone Land status, BAL band estimate, and CDC pathway.',
    badge: 'Free + $39',
    icon: Flame,
    iconColor: 'text-orange-600',
    iconBg: 'bg-orange-500/10',
  },
  {
    href: '/reports/conveyancing',
    title: 'Conveyancing Disclosure',
    question: 'buy',
    tagline: 'LEP controls, overlays, heritage, SEPP — the planning check your conveyancer should do.',
    badge: 'Free + $49',
    icon: FileCheck,
    iconColor: 'text-emerald-600',
    iconBg: 'bg-emerald-500/10',
  },
  {
    href: '/reports/granny-flat',
    title: 'Granny Flat Check',
    question: 'build',
    tagline: 'SEPP eligibility, structure detection from imagery, and rental estimate.',
    badge: 'Free + $49',
    icon: Building2,
    iconColor: 'text-teal-600',
    iconBg: 'bg-teal-500/10',
  },
  {
    href: '/reports/threat-radar',
    title: 'Development Monitoring',
    question: 'near',
    tagline: 'Every DA and CDC within 500m — with weekly email alerts for new lodgements.',
    badge: 'Free + $9/mo',
    icon: Radar,
    iconColor: 'text-violet-600',
    iconBg: 'bg-violet-500/10',
  },
  {
    href: '/reports/shadow',
    title: 'Overshadowing Check',
    question: 'stop',
    tagline: 'Shadow modelled from the maximum-height building envelope on ADG solar access test dates.',
    badge: '$39',
    icon: Moon,
    iconColor: 'text-slate-400',
    iconBg: 'bg-slate-500/10',
  },
  {
    href: '/reports/solar-yield',
    title: 'Solar Potential',
    question: 'worth',
    tagline: 'Roof geometry, orientation, and estimated annual generation from satellite and BoM data.',
    badge: '$39',
    icon: Sun,
    iconColor: 'text-amber-500',
    iconBg: 'bg-amber-500/10',
  },
  {
    href: '/reports/pre-da-history',
    title: 'Site History Check',
    question: 'buy',
    tagline: 'Eight years of satellite change detection cross-referenced with DA records and heritage overlays.',
    badge: '$49',
    icon: Satellite,
    iconColor: 'text-indigo-600',
    iconBg: 'bg-indigo-500/10',
  },
];

/* ------------------------------------------------------------------ */
/*  The five questions — the engine frame; checks group under the      */
/*  question they answer (mirrors the PlotDetect engine sheet)         */
/* ------------------------------------------------------------------ */

const QUESTIONS = [
  { key: 'build', label: 'What can you build here?', colour: '#E8837B' },
  { key: 'stop', label: 'What could stop you?', colour: '#D98E2B' },
  { key: 'buy', label: 'What are you actually buying?', colour: '#3B6FA0' },
  { key: 'worth', label: "What's it worth?", colour: '#5E9C4E' },
  { key: 'near', label: "What's happening around it?", colour: '#8A5FA8' },
];

/* ------------------------------------------------------------------ */
/*  Stats                                                              */
/* ------------------------------------------------------------------ */

const STATS = [
  { value: COVERAGE_DISPLAY.provisionsTotal, label: 'Provisions indexed' },
  { value: COVERAGE_DISPLAY.lgasCovered, label: 'LGAs covered' },
  { value: COVERAGE_DISPLAY.riskLayers, label: 'Risk layers' },
  { value: COVERAGE_DISPLAY.govDataSources, label: 'Gov data sources' },
];

/* ------------------------------------------------------------------ */
/*  Data sources                                                       */
/* ------------------------------------------------------------------ */

const DATA_SOURCES = [
  'NSW Planning Portal',
  'Bureau of Meteorology',
  'European Space Agency',
  'NSW Rural Fire Service',
  'Copernicus EMS',
  'NARCliM 2.0',
  'Spatial Services NSW',
];

/* ------------------------------------------------------------------ */
/*  Climate hazards                                                    */
/* ------------------------------------------------------------------ */

const CLIMATE_HAZARDS = [
  {
    title: 'Flood',
    description: 'Modelled depth at ARI return periods — not just "flood zone."',
    source: 'NSW SES + council flood studies',
  },
  {
    title: 'Bushfire',
    description: 'BAL band estimation, CDC pathway assessment, and 10/50 vegetation clearing.',
    source: 'NSW Rural Fire Service',
  },
  {
    title: 'Climate Projections',
    description: 'Heat stress and precipitation change trajectories to 2099.',
    source: 'NARCliM 2.0 (SSP2.45 + SSP3.70)',
  },
  {
    title: 'Compound Hazards',
    description: 'Bushfire + heat, flood + coastal — interaction scoring for combined risk.',
    source: 'Composite hazard model',
  },
];

/* ------------------------------------------------------------------ */
/*  Personas                                                           */
/* ------------------------------------------------------------------ */

const PERSONAS = [
  {
    title: 'Homeowners & buyers',
    description: 'Check hazards before you bid, and what you can build before you plan. Free instant checks; detailed reports for shortlisted properties.',
    href: '/for/homebuyers',
    cta: 'See homeowner tools',
  },
  {
    title: 'Conveyancers',
    description: 'Pre-exchange planning disclosure in 30 seconds. LEP, DCP, heritage, flood, bushfire — one report.',
    href: '/for/conveyancers',
    cta: 'See conveyancing tools',
  },
  {
    title: 'Buyers Agents',
    description: 'Satellite hazard screening for shortlists. Development monitoring across your portfolio.',
    href: '/for/buyers-agents',
    cta: 'Professional tools',
  },
  {
    title: 'Builders & Planners',
    description: 'Check the source controls with Site Controls. Free embed program for your website.',
    href: '/for/builders',
    cta: 'Embed program',
  },
];

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <HomeNav />

      {/* ── Hero ── */}
      <section className="relative bg-slate-950 overflow-hidden">
        {/* Texture */}
        <div className="absolute inset-0 dot-pattern" />
        {/* Radial glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-teal-500/8 rounded-full blur-[120px]" />

        <div className="relative px-6 pt-32 pb-24 max-w-3xl mx-auto text-center">
          <h1 className="text-5xl sm:text-6xl font-bold leading-[1.08] text-white mb-6 tracking-tight">
            Five questions decide a property.{' '}
            <span className="bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
              Check yours free.
            </span>
          </h1>
          <p className="text-slate-400 text-lg mb-10 max-w-xl mx-auto leading-relaxed">
            What can you build? What could stop you? What are you actually buying?
            What&apos;s it worth? What&apos;s happening around it? Instant checks for any
            NSW address — every figure names the source it came from, and where a source
            could not be consulted it says so rather than answering.
            Free checks; detailed reports from $39.
          </p>

          {/* Search-bar — a real, typeable address search that carries the
              address into the reports hub (each tool card threads it through). */}
          <HeroAddressSearch />

          {/* Tool pills */}
          <div className="flex flex-wrap justify-center gap-2">
            {TOOLS.slice(0, 5).map(({ href, title, icon: Icon, iconColor }) => (
              <Link
                key={href}
                href={href}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-slate-300 bg-slate-800/50 border border-slate-700/50 rounded-lg hover:border-slate-600 hover:text-white hover:bg-slate-800 transition-all backdrop-blur-sm"
              >
                <Icon className={`w-4 h-4 ${iconColor}`} />
                {title}
              </Link>
            ))}
            <Link
              href="/reports"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-teal-400 bg-teal-500/10 border border-teal-500/20 rounded-lg hover:bg-teal-500/20 transition-colors"
            >
              All tools
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <p className="mt-8 text-xs text-slate-600">
            Every check runs on the{' '}
            <a
              href="https://plotdetect.com.au"
              className="text-slate-500 underline decoration-slate-700 underline-offset-2 hover:text-teal-400 transition-colors"
            >
              PlotDetect engine
            </a>
            {' '}— one address in, every figure traced to its source.
          </p>
        </div>
      </section>

      {/* ── Stats strip ── */}
      <section className="bg-slate-950 border-t border-slate-800/50 py-10 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-8">
          {STATS.map(({ value, label }) => (
            <div key={label} className="text-center">
              <div className="text-3xl font-bold text-white tracking-tight">{value}</div>
              <div className="text-sm text-slate-500 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Tools bento grid ── */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-end justify-between mb-10">
            <div>
              <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-2">
                Every check, grouped by your question
              </h2>
              <p className="text-slate-500 max-w-lg">
                Eight instant checks on one engine — find the question you&apos;re asking.
                Free checks first; detailed reports resolve what they find. No account required.
              </p>
            </div>
            <Link
              href="/reports"
              className="hidden sm:inline-flex text-sm text-teal-600 font-medium hover:text-teal-500 transition-colors"
            >
              View all →
            </Link>
          </div>

          <div className="space-y-10">
            {QUESTIONS.map(({ key, label, colour }) => (
              <div key={key}>
                <div className="flex items-center gap-2.5 mb-4">
                  <span className="w-3 h-3 border border-slate-900" style={{ background: colour }} />
                  <h3 className="text-lg font-bold text-slate-900 tracking-tight">{label}</h3>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {TOOLS.filter((tool) => tool.question === key).map((tool) => {
                    const Icon = tool.icon;
                    return (
                      <Link
                        key={tool.href}
                        href={tool.href}
                        className="group rounded-2xl border border-slate-200 p-6 hover:border-teal-500/40 hover:shadow-lg hover:shadow-teal-500/5 transition-all"
                      >
                        <div className={`w-10 h-10 rounded-xl ${tool.iconBg} flex items-center justify-center mb-4`}>
                          <Icon className={`w-5 h-5 ${tool.iconColor}`} />
                        </div>
                        <div className="flex items-center gap-2 mb-1.5">
                          <h4 className="font-semibold text-slate-900 group-hover:text-teal-700 transition-colors">
                            {tool.title}
                          </h4>
                          <span
                            className={`shrink-0 text-[11px] font-medium px-2 py-0.5 rounded-full ${
                              tool.badge.startsWith('Free')
                                ? 'bg-teal-50 text-teal-700'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {tool.badge}
                          </span>
                        </div>
                        <p className="text-sm text-slate-500 leading-relaxed">{tool.tagline}</p>
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Verify — compliance engine ── */}
      <section className="py-20 px-6 bg-slate-50">
        <div className="max-w-5xl mx-auto">
          <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white p-8 md:p-12">
            {/* Gradient accent bar */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-teal-500 via-emerald-500 to-teal-500" />

            <div className="flex items-center gap-2 mb-4">
              <ShieldCheck className="w-5 h-5 text-teal-600" />
              <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
                Site Controls — the source rules
              </span>
            </div>
            <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-3">
              Every provision. Every clause. Every PDF page.
            </h2>
            <p className="text-slate-500 max-w-2xl mb-8">
              Design compliant from the start. Verify extracts the exact DCP provisions,
              SEPP standards, and LEP controls that apply to your property and development type
              — with clause citations and PDF page references.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              {/* Inner West tier */}
              <div className="rounded-2xl border border-teal-200 bg-teal-50/30 p-6">
                <span className="inline-block text-xs font-semibold px-2.5 py-1 rounded-full bg-teal-100 text-teal-700 mb-3">
                  Full DCP coverage
                </span>
                <h3 className="font-semibold text-slate-900 mb-3">Inner West Council</h3>
                <ul className="space-y-1.5 text-sm text-slate-600">
                  <li>~11,000 provisions across 3 former councils</li>
                  <li>Precinct-specific filtering</li>
                  <li>DA Mode with triage and annotation</li>
                  <li>SEE scaffold export</li>
                  <li>Development type filtering</li>
                  <li>PDF page citations for every clause</li>
                </ul>
              </div>

              {/* Numeric-controls tier — council count from lib/coverage.ts */}
              <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6">
                <span className="inline-block text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 mb-3">
                  Numeric controls
                </span>
                <h3 className="font-semibold text-slate-900 mb-3">{COVERAGE_DISPLAY.dcpNumericCouncils} NSW councils</h3>
                <ul className="space-y-1.5 text-sm text-slate-600">
                  <li>Setbacks, parking rates, landscaping standards</li>
                  <li>Clause citations from source DCP</li>
                  <li>Useful for pre-DA checks and CDC screening</li>
                  <li>Coverage expanding with each LGA onboarding</li>
                </ul>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/assessment"
                page="home"
                cta="verify_section_try_free"
                className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
              >
                Open Site Controls — free
                <ArrowRight className="w-4 h-4" />
              </TrackedLink>
              <Link
                href="/how-it-works"
                className="inline-flex items-center gap-2 px-6 py-3 text-slate-600 text-sm font-medium rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all"
              >
                How the data works
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Climate Risk Intelligence ── */}
      <section className="relative bg-slate-950 py-20 px-6 overflow-hidden">
        {/* Subtle glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-teal-500/5 rounded-full blur-[100px]" />

        <div className="relative max-w-5xl mx-auto">
          <div className="flex items-center gap-2 mb-4">
            <Thermometer className="w-5 h-5 text-teal-400" />
            <span className="text-xs font-semibold uppercase tracking-widest text-teal-400">
              Climate Risk Intelligence
            </span>
          </div>
          <h2 className="text-3xl font-bold text-white tracking-tight mb-3">
            Property risk is changing. We measure it.
          </h2>
          <p className="text-slate-400 max-w-2xl mb-10">
            NARCliM 2.0 climate projections combined with statutory planning overlays
            and satellite hazard detection. Deterministic composite scoring — no AI interpretation.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {CLIMATE_HAZARDS.map(({ title, description, source }) => (
              <div
                key={title}
                className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm p-6"
              >
                {/* Gradient top edge */}
                <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-teal-500/50 to-transparent" />
                <h3 className="font-semibold text-white mb-2">{title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed mb-3">{description}</p>
                <p className="text-xs text-slate-600">{source}</p>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-4 mt-8">
            <TrackedLink
              href="/climate-risk"
              page="home"
              cta="climate_section_check"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
            >
              Free climate risk check
              <ArrowRight className="w-4 h-4" />
            </TrackedLink>
            <Link
              href="/blog/uninsurable-property-climate-risk"
              className="text-sm text-slate-400 hover:text-teal-400 transition-colors"
            >
              How climate risk is repricing real estate →
            </Link>
          </div>
          <p className="text-xs text-slate-600 mt-4">
            Climate Risk Report ($99) available after PlotDetect Pty Ltd incorporation and professional indemnity insurance.
          </p>
        </div>
      </section>

      {/* ── Scout + Validate ── */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link
            href="/scout"
            className="group relative overflow-hidden rounded-2xl border border-slate-200 p-8 hover:shadow-lg hover:border-blue-500/30 transition-all"
          >
            {/* Decorative blob */}
            <div className="absolute -top-10 -right-10 w-40 h-40 bg-blue-50 rounded-full opacity-60" />
            <div className="relative">
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mb-4">
                <Map className="w-6 h-6 text-blue-600" />
              </div>
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600 mb-2 block">
                Scout
              </span>
              <h3 className="text-xl font-semibold text-slate-900 mb-2">
                Click any property in NSW
              </h3>
              <p className="text-sm text-slate-500 leading-relaxed mb-4">
                Interactive map explorer with zone overlays, lot boundaries, heritage overlays,
                and planning controls. Free, no account required.
              </p>
              <span className="inline-flex items-center gap-1 text-sm text-blue-600 font-medium group-hover:text-blue-500 transition-colors">
                Open Scout
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </span>
            </div>
          </Link>

          <Link
            href="/validate"
            className="group relative overflow-hidden rounded-2xl border border-slate-200 p-8 hover:shadow-lg hover:border-violet-500/30 transition-all"
          >
            {/* Decorative blob */}
            <div className="absolute -top-10 -right-10 w-40 h-40 bg-violet-50 rounded-full opacity-60" />
            <div className="relative">
              <div className="w-12 h-12 rounded-xl bg-violet-500/10 flex items-center justify-center mb-4">
                <BarChart3 className="w-6 h-6 text-violet-600" />
              </div>
              <span className="text-xs font-semibold uppercase tracking-widest text-violet-600 mb-2 block">
                Validate
              </span>
              <h3 className="text-xl font-semibold text-slate-900 mb-2">
                Track DA patterns and approval rates
              </h3>
              <p className="text-sm text-slate-500 leading-relaxed mb-4">
                DA analytics across {COVERAGE_DISPLAY.totalNswCouncils} NSW councils — approval rates, processing times,
                common refusal reasons, and trend analysis.
              </p>
              <span className="inline-flex items-center gap-1 text-sm text-violet-600 font-medium group-hover:text-violet-500 transition-colors">
                Open Validate
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </span>
            </div>
          </Link>
        </div>
      </section>

      {/* ── Personas ── */}
      <section className="py-20 px-6 bg-slate-50">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-10 text-center">
            Built for how you actually work
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {PERSONAS.map(({ title, description, href, cta }) => (
              <Link
                key={title}
                href={href}
                className="group rounded-2xl bg-white border border-slate-200 p-6 hover:shadow-lg hover:border-teal-500/30 transition-all"
              >
                <h3 className="font-semibold text-slate-900 mb-2">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed mb-4">{description}</p>
                <span className="inline-flex items-center gap-1 text-sm text-teal-600 font-medium group-hover:text-teal-500 transition-colors">
                  {cta}
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>


      <SiteFooter />
    </main>
  );
}
