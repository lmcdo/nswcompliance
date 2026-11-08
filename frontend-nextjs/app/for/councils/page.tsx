import { PLAN_BRIEF_ON } from '@/lib/site-report';
import type { Metadata } from 'next';
import { ShieldCheck, ArrowRight } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'For Councils — PlotDetect',
  description: 'Pre-DA compliance checking for NSW councils. Zero integration required — embed as an iframe.',
};

export default function CouncilsPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-12">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="w-5 h-5 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
            For councils
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
          Let applicants find the right council rules before they lodge
        </h1>
        <p className="text-gray-500 text-lg max-w-xl">
          PlotDetect Council Rules sets out the SEPP, LEP, and DCP rules for any property
          and development type — before the applicant lodges. Zero integration with
          your systems. No IT project. Embed as an iframe on your council website.
        </p>
      </section>

      {/* Benefits */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {[
            {
              title: 'Applicants see the plan first',
              description: PLAN_BRIEF_ON
                ? "Applicants see the DCP rules for their lot and project, in your plan's words with the page, before they lodge."
                : "Applicants see the DCP chapters that may apply to their lot, with links to your own pages, before they lodge.",
            },
            {
              title: 'Zero integration required',
              description: 'Site Controls runs as an iframe embed. No API integration, no data export, no IT procurement process. Add one line of HTML to your pre-DA guidance page.',
            },
            {
              title: 'No access to council systems',
              description: 'Site Controls reads the NSW Planning Portal and the planning documents your council has already published. Nothing is installed on, or connected to, council systems.',
            },
            {
              title: 'Queried live, or dated',
              description: 'Zone, height, FSR and overlay controls are queried live from the NSW Planning Portal on every request. DCP provisions are extracted from the published instrument and carry the version and date they were read from, so what is a live lookup and what is a dated extract is never in doubt. No manual database maintenance.',
            },
          ].map(({ title, description }) => (
            <div key={title} className="rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-1">{title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-gray-50 border-y border-gray-100 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-6">How it works</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {[
              { step: '1', title: 'Embed on your website', body: 'Add the Council Rules iframe to your pre-DA guidance page. No IT project, no procurement.' },
              { step: '2', title: 'Applicant enters address', body: 'They get the SEPP, LEP, and DCP rules for their property and development type, each linked to its source.' },
              { step: '3', title: 'Applicants arrive informed', body: 'Applicants who have read Council Rules can see the constraints before they lodge.' },
            ].map(({ step, title, body }) => (
              <div key={step} className="space-y-2">
                <div className="w-8 h-8 rounded-full bg-teal-600 text-white text-sm font-bold flex items-center justify-center">
                  {step}
                </div>
                <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
                <p className="text-sm text-gray-500">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <div className="rounded-xl border border-teal-200 bg-teal-50 p-8 text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Request a council demo
          </h2>
          <p className="text-sm text-gray-600 mb-6 max-w-md mx-auto">
            See Council Rules running against your council area. We will show you exactly
            what applicants see — with your plan's rules and planning controls.
          </p>
          <a
            href="mailto:hello@plotdetect.com.au?subject=Council%20demo%20request"
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
          >
            Request demo
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
