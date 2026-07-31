import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

export const metadata: Metadata = {
  title: 'About — PlotDetect',
  description: 'PlotDetect is built by a sole technical founder on live NSW Government data. No guesswork, no approximations.',
};

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      <article className="max-w-2xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">About PlotDetect</h1>

        <div className="prose prose-sm prose-gray max-w-none">
          <p className="text-gray-600 leading-relaxed">
            PlotDetect is a solo-built NSW property intelligence platform. One person,
            live government data, and satellite imagery — no guesswork, no approximations,
            no manually maintained databases.
          </p>

          <h2 className="text-lg font-semibold text-gray-900 mt-8 mb-3">What it does</h2>
          <p className="text-gray-600 leading-relaxed">
            PlotDetect connects to the NSW Planning Portal, Bureau of Meteorology,
            European Space Agency satellite imagery, NSW Rural Fire Service datasets,
            and NARCliM 2.0 climate projections. It extracts the planning controls,
            hazard data, and environmental overlays that apply to a specific property
            — and presents them in a way that is immediately useful for buyers,
            conveyancers, planners, and property professionals.
          </p>

          <h2 className="text-lg font-semibold text-gray-900 mt-8 mb-3">Why it exists</h2>
          <p className="text-gray-600 leading-relaxed">
            NSW planning data is fragmented across hundreds of councils, thousands of
            provisions, and documents that have not changed format since the 1990s.
            A single DA for a dwelling house touches LEP controls, SEPP instruments,
            and a DCP with hundreds of provisions. A planner must address all of them.
            No automated system covers the full stack from statutory compliance
            to climate risk — PlotDetect does.
          </p>

          <h2 className="text-lg font-semibold text-gray-900 mt-8 mb-3">How it works</h2>
          <p className="text-gray-600 leading-relaxed">
            Every result is deterministic. The same address, queried twice,
            produces the same output. There is no AI interpretation of regulations —
            PlotDetect extracts exact clauses, exact numbers, and exact PDF page
            references from source documents. When data is unavailable,
            it says so rather than approximating.
          </p>

          <h2 className="text-lg font-semibold text-gray-900 mt-8 mb-3">Data sources</h2>
          <ul className="text-gray-600 space-y-1">
            <li>NSW Planning Portal (layerintersect API, zone data, LEP controls)</li>
            <li>Spatial Services NSW (property boundaries, building footprints)</li>
            <li>Bureau of Meteorology (solar irradiance, flood history)</li>
            <li>European Space Agency (Sentinel-2 satellite imagery)</li>
            <li>NSW Rural Fire Service (Bush Fire Prone Land dataset)</li>
            <li>NARCliM 2.0 (regional climate model projections)</li>
            <li>NSW ePlanning Portal (DA and CDC records from {COVERAGE_DISPLAY.totalNswCouncils} councils)</li>
            <li>Copernicus EMS (emergency flood mapping)</li>
          </ul>

          <h2 className="text-lg font-semibold text-gray-900 mt-8 mb-3">Contact</h2>
          <p className="text-gray-600 leading-relaxed">
            <a href="mailto:hello@plotdetect.com.au" className="text-teal-600 hover:text-teal-700 transition-colors">
              hello@plotdetect.com.au
            </a>
          </p>
        </div>
      </article>

      <SiteFooter />
    </main>
  );
}
