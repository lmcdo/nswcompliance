import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { HomeNav } from '@/components/marketing/HomeNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { HeroAddressSearch } from '@/components/marketing/HeroAddressSearch';
import { PILOT_COUNCIL_LABELS } from '@/lib/pilot-focus';

const STEPS = [
  { n: '1', title: 'Enter an address', body: 'Any NSW address. No account needed.' },
  { n: '2', title: 'Say what you want to build', body: 'For the pilot, a house (dwelling house) in a residential R2 zone.' },
  { n: '3', title: "Read the council's own rules", body: 'Each rule is quoted in the council\'s words with the clause and the page, or the row says "not found".' },
];

const LIMITS = [
  'It is a preliminary reading of council documents. It is not planning advice and not legal advice.',
  "Check the council's own document before relying on any rule shown.",
  'The clauses listed under each topic cover only a house (dwelling house) in a residential R2 zone.',
  'Outside the pilot councils, the page shows a pilot notice instead of rules.',
];

const MAILTO = 'mailto:hello@plotdetect.com.au?subject=Pilot access';

export default function HomePage() {
  const councils = PILOT_COUNCIL_LABELS;
  return (
    <main className="min-h-screen">
      <HomeNav />

      {/* Hero */}
      <section className="relative bg-slate-950 overflow-hidden">
        <div className="absolute inset-0 dot-pattern" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-teal-500/8 rounded-full blur-[120px]" />

        <div className="relative px-6 pt-32 pb-24 max-w-3xl mx-auto text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-teal-400 mb-4">
            Private pilot
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold leading-[1.1] text-white mb-6 tracking-tight">
            The council&apos;s own planning rules for your address and project
          </h1>
          <p className="text-slate-400 text-lg mb-10 max-w-xl mx-auto leading-relaxed">
            Enter a NSW address and what you want to build. You get the council&apos;s own rules for it, each with the clause and the page, or a plain &quot;not found&quot;.
          </p>

          <HeroAddressSearch />

          <div className="flex flex-wrap justify-center gap-3">
            <TrackedLink
              href="/assessment"
              page="home"
              cta="hero_open_council_rules"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
            >
              Open Council Rules
              <ArrowRight className="w-3.5 h-3.5" />
            </TrackedLink>
            <Link
              href="/how-it-works"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-slate-300 bg-slate-800/50 border border-slate-700/50 rounded-lg hover:border-slate-600 hover:text-white transition-all"
            >
              How it works
            </Link>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-10">How it works</h2>
          <ol className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {STEPS.map(({ n, title, body }) => (
              <li key={n} className="rounded-2xl bg-white border border-slate-200 p-6">
                <span className="text-sm font-bold text-teal-600">Step {n}</span>
                <h3 className="font-semibold text-slate-900 mt-1 mb-2">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Who it is for */}
      <section className="py-20 px-6 bg-slate-50">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-4">Who it is for</h2>
          <p className="text-slate-600 leading-relaxed">
            Planners, certifiers, designers and builders working on houses (dwelling house, zone R2) in the pilot councils.
          </p>
        </div>
      </section>

      {/* Pilot councils */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-6">The pilot councils</h2>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {councils.map((name) => (
              <li key={name} className="flex gap-3 text-slate-700 text-sm">
                <span className="mt-2 w-1.5 h-1.5 rounded-full bg-teal-500 flex-shrink-0" />
                {name}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* What it does not do */}
      <section className="py-20 px-6 bg-slate-950">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-white tracking-tight mb-8">What it does not do</h2>
          <ul className="space-y-3">
            {LIMITS.map((line) => (
              <li key={line} className="flex gap-3 text-slate-300 text-sm leading-relaxed">
                <span className="mt-2 w-1.5 h-1.5 rounded-full bg-teal-400 flex-shrink-0" />
                {line}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Join the pilot */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-4">Join the pilot</h2>
          <p className="text-slate-600 mb-8">
            Free while we test it with chosen professionals. Email us to ask for access.
          </p>
          <a
            href={MAILTO}
            className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-500 transition-colors"
          >
            Join the pilot
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
