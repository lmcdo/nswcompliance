import type { Metadata } from 'next';
import { GraduationCap, ArrowRight, AlertTriangle } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'For Students & Lecturers — PlotDetect',
  description:
    'Free access to NSW planning controls for planning and property students. Every control cited to its clause, and what it has not been checked against stated up front.',
};

// Site Controls lives on its own subdomain — middleware.ts rewrites
// verify.plotdetect.com.au to /assessment. A class link is this plus
// ?cohort=<code>, which tags that cohort's feedback without anyone creating an
// account. See lib/cohort.ts.
const SITE_CONTROLS = 'https://verify.plotdetect.com.au/assessment';

export default function StudentsPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-12">
        <div className="flex items-center gap-2 mb-4">
          <GraduationCap className="w-5 h-5 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
            For students &amp; lecturers
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
          The planning controls for any NSW site, cited to the clause
        </h1>
        <p className="text-gray-500 text-lg max-w-xl">
          Type an address and get the zone, height limit, floor space ratio, minimum lot
          size, setbacks, heritage, flood and bushfire controls that apply — each cited to
          the clause it came from. It is the desktop-analysis step you would otherwise do
          by opening the LEP and the DCP and reading.
        </p>
        <p className="text-gray-500 mt-4 max-w-xl">
          Free for students. No account, no password, nothing to install.
        </p>
      </section>

      {/* What it is useful for */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {[
            {
              title: 'Site analysis for a feasibility',
              description:
                'The controls that bound what can be built — zone, height, FSR, minimum lot size, setbacks — for a real address, in one place.',
            },
            {
              title: 'Every number has a citation',
              description:
                'Each control names the instrument and clause it came from, so you can follow it to the source and cite the source in your own work.',
            },
            {
              title: 'Hazard and overlay layers',
              description:
                'Flood, bushfire, heritage and the other mapped overlays that apply to the site, read from the published layers.',
            },
            {
              title: 'Comparing sites quickly',
              description:
                'Running several candidate addresses takes minutes rather than an afternoon, which is where most of the time goes in a site-selection exercise.',
            },
          ].map(({ title, description }) => (
            <div key={title} className="rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-1">{title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* The honest section, deliberately BEFORE the call to action. A student
          who finds a limitation after being sold to trusts nothing afterwards. */}
      <section className="bg-amber-50 border-y border-amber-100 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-amber-700" />
            <h2 className="text-xl font-bold text-gray-900">
              What it has not been checked against
            </h2>
          </div>
          <p className="text-sm text-gray-700 mb-6 max-w-2xl">
            Stated here rather than buried, because you are being asked to test it and
            because some of you will put a number from it into marked work.
          </p>
          <ul className="space-y-3 text-sm text-gray-700 max-w-2xl list-disc pl-5">
            <li>
              <strong>Roughly one citation in thirteen does not resolve to a clause.</strong>{' '}
              Some name a whole instrument and no more. They now say so, but they still do
              not take you anywhere.
            </li>
            <li>
              <strong>Coverage is uneven.</strong> 28 councils have numeric controls
              extracted. Outside those you will get considerably less, and that is a gap
              rather than a fault.
            </li>
            <li>
              <strong>Wingecarribee controls are read from the Bowral town plan</strong> and
              served across the whole shire. The numbers are identical in the Mittagong and
              Moss Vale plans — that has been checked — but table numbers differ between
              them, so a citation may not match the plan you open.
            </li>
            <li>
              <strong>
                Nothing here has been tested against a council&rsquo;s own determination.
              </strong>{' '}
              It reads the published instruments. It does not know what a council would
              actually approve.
            </li>
          </ul>
          <p className="text-sm font-semibold text-gray-900 mt-6 max-w-2xl">
            None of it is planning advice, and none of it replaces reading the instrument.
            If you use a number in assessable work, check it against the source and cite
            the source — not this tool.
          </p>
        </div>
      </section>

      {/* Two doors */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="rounded-xl border border-teal-200 bg-teal-50 p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-2">I am a student</h2>
            <p className="text-sm text-gray-600 mb-5">
              If your lecturer gave you a link with a class code in it, use that one — it
              groups your feedback with your class. Otherwise start here.
            </p>
            <a
              href={SITE_CONTROLS}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
            >
              Open Site Controls
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>

          <div className="rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-2">I teach a class</h2>
            <p className="text-sm text-gray-600 mb-5">
              Free access for your cohort for the teaching period, and a guest session if
              it is useful. You get a link carrying your own class code, so feedback comes
              back grouped. No cost and nothing to sign.
            </p>
            <a
              href="mailto:hello@plotdetect.com.au?subject=Class%20access%20request"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
            >
              Get a class link
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      {/* What is wanted back */}
      <section className="bg-gray-50 border-t border-gray-100 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-3">
            What is actually wanted back
          </h2>
          <p className="text-sm text-gray-600 mb-6 max-w-2xl">
            Not &ldquo;it looks good&rdquo; — that cannot be acted on. Two things are worth
            more than everything else combined, and the feedback button already knows which
            address you were looking at.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-1">
                &ldquo;This control is missing.&rdquo;
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                You know from the DCP that a control applies to your site and it is not
                shown. Send the address, which control, and where you found it.
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-1">
                &ldquo;This number is wrong.&rdquo;
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                The tool says one thing and the DCP says another. Send the address, both
                numbers, and the clause. This is the single most useful thing you can send.
              </p>
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-6 max-w-2xl">
            A use nobody designed for is worth more than a bug. If you find yourself
            wanting it for something it was not built to do, say so.
          </p>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
