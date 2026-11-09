import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { PILOT_COUNCIL_LABELS } from '@/lib/pilot-focus';
import { PLAN_BRIEF_ON } from '@/lib/site-report';

export const metadata: Metadata = {
  title: 'How It Works — PlotDetect',
  description: "How the private pilot works: the council's own planning rules for an address and project, and the mapped facts about a property.",
};

const STEPS = [
  { n: '1', title: 'Enter an address', body: 'Any NSW address. No account needed.' },
  { n: '2', title: 'Say what you want to build', body: 'For the pilot, a house (dwelling house) in a residential R2 zone.' },
  {
    n: '3',
    title: "Read the council's own rules",
    // The clause lists are behind a flag (lib/site-report.ts). Without it only the numeric controls are shown, so say only that.
    body: PLAN_BRIEF_ON
      ? "Each rule is quoted in the council's words with the clause and the page, or the row says 'not found'."
      : "Each control is shown with the clause it comes from and a link to the council's plan.",
  },
];

const LIMITS = [
  'This is a private pilot.',
  `The pilot councils are ${PILOT_COUNCIL_LABELS.join(', ')}.`,
  'It is a preliminary reading of council documents. It is not planning advice and not legal advice.',
  "Check the council's own document before relying on any rule shown.",
  'Outside the pilot councils, or outside a residential R2 zone, the Council Rules page shows a pilot notice and the SEPP and Planning Controls tabs only.',
];

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      <article className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">How it works</h1>
        <p className="text-gray-600 leading-relaxed mb-12">
          PlotDetect is in a private pilot with two products: Council Rules and Site Facts.
        </p>

        <section className="mb-12">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Council Rules</h2>
          <ol className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {STEPS.map(({ n, title, body }) => (
              <li key={n} className="rounded-2xl border border-gray-200 p-5">
                <span className="text-sm font-bold text-teal-600">Step {n}</span>
                <h3 className="font-semibold text-gray-900 mt-1 mb-2">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{body}</p>
              </li>
            ))}
          </ol>
          <Link href="/assessment" className="text-teal-600 hover:text-teal-700 text-sm font-medium transition-colors">
            Open Council Rules
          </Link>
        </section>

        <section className="mb-12">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Site Facts</h2>
          <p className="text-gray-600 leading-relaxed mb-3">
            The mapped facts about a NSW property, each shown with its source.
          </p>
          <Link href="/reports/intelligence-brief" className="text-teal-600 hover:text-teal-700 text-sm font-medium transition-colors">
            Open Site Facts
          </Link>
        </section>

        <section className="mb-12">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Limits</h2>
          <ul className="space-y-3">
            {LIMITS.map((line) => (
              <li key={line} className="flex gap-3 text-gray-600 text-sm leading-relaxed">
                <span className="mt-2 w-1.5 h-1.5 rounded-full bg-teal-500 flex-shrink-0" />
                {line}
              </li>
            ))}
          </ul>
        </section>

        <p className="text-gray-600 text-sm">
          <a
            href="mailto:hello@plotdetect.com.au?subject=Wrong rule"
            className="text-teal-600 hover:text-teal-700 font-medium transition-colors"
          >
            Tell us about a wrong rule
          </a>
        </p>
      </article>

      <SiteFooter />
    </main>
  );
}
