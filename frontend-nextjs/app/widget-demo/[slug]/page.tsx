import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { DuplexCheckWidget } from '@/components/tools/DuplexCheckWidget';
import { WIDGET_PARTNERS, getWidgetPartner } from '@/lib/widget-partners';

/**
 * /widget-demo/[slug] — per-builder demo of the white-label duplex checker.
 *
 * prior-art-checked: presentation shell around DuplexCheckWidget (the shared
 * embed component) driven by lib/widget-partners.ts; exists so an outreach
 * email can show a builder the checker carrying THEIR name before any code
 * touches their site. Not linked from navigation, noindexed — reached only
 * via outreach links.
 */

export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export function generateStaticParams() {
  return WIDGET_PARTNERS.map((p) => ({ slug: p.slug }));
}

export default function WidgetDemoPage({ params }: { params: { slug: string } }) {
  const partner = getWidgetPartner(params.slug);
  if (!partner) notFound();

  const iframeSnippet = `<iframe src="https://verify.plotdetect.com.au/embed/upzoning?ref=${partner.slug}" style="width:100%;height:760px;border:0;" title="Duplex eligibility checker"></iframe>`;
  const siteHost = new URL(partner.site).host;

  return (
    <main className="min-h-screen bg-gray-100">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <p className="text-xs font-semibold uppercase tracking-widest text-teal-600 mb-2">
          Live demo — nothing is installed anywhere yet
        </p>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          The {partner.name} duplex checker
        </h1>
        <p className="text-gray-600 mb-3 max-w-xl">
          You already run a free site assessment on every enquiry — zone,
          minimum lot size, frontage, heritage, overlays, checked by hand,
          including on the blocks that were never going to work. This does the
          regulatory half of that check in about ten seconds, on your own site,
          before the enquiry reaches you.
        </p>
        <p className="text-gray-600 mb-8 max-w-xl">
          This is how the checker will look on your site, carrying{' '}
          {partner.name}&apos;s name. Run any Sydney address — every check queries live NSW Government
          planning maps, and an enquiry from an eligible result goes to{' '}
          {partner.name}&apos;s own contact page, nowhere else.
        </p>

        {/* Mock browser frame — "this is your website" */}
        <div className="rounded-2xl overflow-hidden shadow-xl border border-gray-200 bg-white">
          <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-50 border-b border-gray-200">
            <span className="w-2.5 h-2.5 rounded-full bg-red-400" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span className="w-2.5 h-2.5 rounded-full bg-green-400" />
            <span className="ml-3 flex-1 text-xs text-gray-400 bg-white border border-gray-200 rounded-md px-3 py-1 truncate">
              {siteHost}/duplex-checker
            </span>
          </div>
          <div className="px-4 py-8 sm:px-8">
            <DuplexCheckWidget
              partnerName={partner.name}
              ctaUrl={partner.ctaUrl}
              refSlug={`demo-${partner.slug}`}
            />
          </div>
        </div>

        {/* Boundary caption — a skimming builder must never read the panels
            below as part of what their customer sees */}
        <p className="mt-3 text-center text-xs text-gray-500">
          Everything inside the frame above is what your visitor sees on your
          site. Everything below this line is for you only.
        </p>

        {/* How it works on their site */}
        <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-gray-500">
          For you — how the pilot works
        </h2>
        <div className="mt-3 grid sm:grid-cols-2 gap-4">
          {[
            ['It sorts enquiries three ways, not two', 'Blocks that meet the mapped standard. Blocks that plainly don’t — declined before anyone drives out. And NEEDS-CHECKING: the maps alone can’t settle it, so it needs a survey or a set of eyes. That third bucket is where your expertise is worth paying for, and it’s handed to you as a site-assessment conversation.'],
            ['The enquiry is yours', `Every enquiry button points at ${siteHost} — not a shared lead list, no middleman in the conversation.`],
            ['Honest by design', 'Every figure names its source — a planning control carries the clause it was read from, a mapping result names its dataset — and where the mapping can’t answer, it says so instead of guessing. The result is never bent to flatter a block — that’s what makes an enquiry off the back of it worth having.'],
            ['You see the numbers', 'Checks run and enquiry-button clicks, split into eligible and needs-checking blocks, reported to you weekly during the pilot. Counted in the visitor’s browser, so it may undercount where analytics are blocked — never over. A click is an enquiry started, not yet a submitted form.'],
            ['What it does not cover', 'Sewer mains, easements and title covenants are real duplex killers and this doesn’t touch them — it checks the planning layer, not the title or the services.'],
            ['Council by council', 'Minimum frontage and lot size vary sharply between councils, and the checker reads each one’s own controls rather than a single rule of thumb. Try a block in a council you build in often.'],
          ].map(([title, body]) => (
            <div key={title} className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm font-semibold text-gray-900 mb-1">{title}</p>
              <p className="text-xs text-gray-500 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>

        {/* Install snippet */}
        <div className="mt-8 bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-sm font-semibold text-gray-900 mb-1">
            Installing it is one line
          </p>
          <p className="text-xs text-gray-500 mb-3">
            Paste this where the checker goes — Wix, WordPress, Squarespace, or
            plain HTML. We do the install with you during the pilot.
          </p>
          <pre className="text-[11px] bg-gray-900 text-gray-100 rounded-lg p-3 overflow-x-auto">
            {iframeSnippet}
          </pre>
        </div>

        <div className="mt-8 text-center">
          <p className="text-sm text-gray-600">
            30-day pilot on your site, free — you keep every enquiry.
          </p>
          <a
            href={`mailto:info@plotdetect.com.au?subject=${encodeURIComponent(`Duplex checker pilot — ${partner.name}`)}`}
            className="mt-3 inline-block px-5 py-2.5 rounded-xl bg-teal-600 text-white text-sm font-semibold hover:bg-teal-500 transition-colors"
          >
            Start the pilot
          </a>
          <p className="mt-6 text-[11px] text-gray-400 leading-relaxed max-w-lg mx-auto">
            The checker reports mapped planning data and extracted Housing SEPP
            standards with their source clauses — not planning advice.
            Development consent depends on a development application and
            site-specific assessment by the consent authority. Powered by
            PlotDetect · Data: NSW Planning Portal, Spatial Services NSW.
          </p>
        </div>
      </div>
    </main>
  );
}
