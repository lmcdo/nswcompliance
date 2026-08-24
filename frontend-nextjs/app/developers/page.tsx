import type { Metadata } from 'next';
import Link from 'next/link';
import { Code2, Database, Zap, Lock, ArrowRight, FileJson, Building2, Scale } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

export const metadata: Metadata = {
  title: 'Property Data API — Structured NSW Planning Controls | PlotDetect',
  description:
    'API access to DCP numeric controls, LEP provisions, zoning data, flood risk, and planning constraints for every NSW address. Built for conveyancing platforms, PropTech, and property analytics.',
  keywords: [
    'property data api',
    'nsw planning data api',
    'planning data api',
    'property intelligence api',
    'conveyancing platform api',
    'dcp controls api',
    'zoning data api australia',
    'property analytics api',
  ],
};

const USE_CASES = [
  {
    icon: Scale,
    iconColor: 'text-teal-600',
    title: 'Conveyancing platforms',
    description:
      'Add structured planning controls to pre-exchange reports. DCP setbacks, heritage status, flood depth, and spatial overlays — data that s10.7 certificates miss.',
    example: 'InfoTrack, GlobalX, or bespoke conveyancing software',
  },
  {
    icon: Building2,
    iconColor: 'text-blue-600',
    title: 'PropTech & property portals',
    description:
      'Enrich listings with development potential, zoning permissibility, and key constraints. Turn "R2 Low Density Residential" into actionable intelligence.',
    example: 'Property portals, investment platforms, lending tech',
  },
  {
    icon: Database,
    iconColor: 'text-purple-600',
    title: 'Planning & development tools',
    description:
      'Feed structured numeric controls into feasibility models. Setbacks, FSR, height limits, landscaping requirements, and parking rates — with clause citations.',
    example: 'Feasibility calculators, planning consultancy tools, DA preparation',
  },
];

const DATA_POINTS = [
  {
    label: 'Zoning & permissibility',
    detail: 'Zone code, zone name, permitted/prohibited land uses for every NSW lot',
  },
  {
    label: 'LEP numeric controls',
    detail: 'FSR, height of buildings, minimum lot size, heritage listings, acid sulfate soil class',
  },
  {
    label: 'DCP numeric controls',
    detail: `Setbacks, parking rates, landscaping, site coverage, building separation — ${COVERAGE_DISPLAY.dcpSetbackRows} rows across ${COVERAGE_DISPLAY.dcpNumericCouncils} LGAs. Full structured provisions for ${COVERAGE_DISPLAY.dcpFullCouncils} councils.`,
  },
  {
    label: 'SEPP requirements',
    detail: 'Housing SEPP, Exempt & Complying, Transport & Infrastructure, Resilience & Hazards — per-address applicability',
  },
  {
    label: 'Spatial overlays',
    detail: 'Flood prone land, bushfire prone land, heritage conservation areas, riparian corridors, foreshore building lines',
  },
  {
    label: 'Flood depth modelling',
    detail: `Modelled flood depth at ARI return periods where a council flood study has been ingested — ${COVERAGE_DISPLAY.floodStudies} studies; the mapped flood planning area elsewhere`,
  },
];

const DIFFERENTIATORS = [
  {
    icon: FileJson,
    title: 'Structured, not scraped',
    description:
      'DCP controls extracted into typed numeric fields with clause citations — not raw PDF text. Query by control type, development type, or precinct.',
  },
  {
    icon: Zap,
    title: 'Single-address lookup',
    description:
      'One API call, one address → complete planning profile. Zone, LEP, DCP, SEPP, spatial overlays, flood, bushfire. No spatial joins on your end.',
  },
  {
    icon: Lock,
    title: 'Live government data',
    description:
      'Sourced from NSW Planning Portal, council flood studies, RFS bushfire layers, and Spatial Services NSW. Updated when instruments change.',
  },
];

export default function DevelopersPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-12">
        <div className="flex items-center gap-2 mb-4">
          <Code2 className="w-5 h-5 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">
            For developers
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
          NSW planning data, structured and queryable
        </h1>
        <p className="text-gray-500 text-lg max-w-xl">
          Zoning, LEP controls, DCP numeric requirements, SEPP provisions, flood depth, and spatial
          overlays — for any NSW address. One API call. JSON response. Clause citations included.
        </p>
        <div className="flex flex-wrap gap-3 mt-8">
          <TrackedLink
            href="/contact?ref=api"
            page="developers"
            cta="hero_request_api"
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
          >
            Request API access <ArrowRight className="w-4 h-4" />
          </TrackedLink>
          <TrackedLink
            href="/assessment"
            page="developers"
            cta="hero_see_demo"
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            See it in action
          </TrackedLink>
        </div>
      </section>

      {/* Example response */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Example response</h2>
        <div className="bg-slate-950 rounded-xl p-6 overflow-x-auto">
          <pre className="text-sm text-slate-300 leading-relaxed">
{`GET /api/v1/property?address=10+Smith+St+Marrickville+NSW

{
  "address": "10 Smith Street, Marrickville NSW 2204",
  "lga": "Inner West",
  "zone": {
    "code": "R2",
    "name": "Low Density Residential",
    "permitted": ["dwelling houses", "secondary dwellings", ...],
    "prohibited": ["industries", "warehouse distribution", ...]
  },
  "lep_controls": {
    "fsr": 0.5,
    "height_m": 8.5,
    "min_lot_size_sqm": 450,
    "heritage_item": false,
    "heritage_conservation_area": true
  },
  "dcp_controls": [
    {
      "type": "front_setback",
      "value_m": 5.0,
      "source_ref": "Part C, Section 3.2.1",
      "applies_to": ["dwelling houses", "dual occupancy"]
    },
    {
      "type": "rear_setback",
      "value_m": 8.0,
      "source_ref": "Part C, Section 3.2.3"
    }
  ],
  "flood": {
    "in_flood_zone": true,
    "depth_1pct_ari_m": 0.3,
    "source": "Marrickville Valley Flood Study 2020"
  },
  "spatial_overlays": {
    "bushfire_prone": false,
    "acid_sulfate_soil": 5,
    "riparian_corridor": false
  }
}`}
          </pre>
        </div>
        <p className="text-xs text-gray-400 mt-3">
          Illustrative response. Actual schema and field availability vary by LGA and data coverage.
        </p>
      </section>

      {/* What data is available */}
      <section className="bg-gray-50 border-y border-gray-100 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Available data</h2>
          <div className="space-y-4">
            {DATA_POINTS.map(({ label, detail }) => (
              <div key={label} className="flex gap-3">
                <div className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-teal-500 mt-2" />
                <div>
                  <p className="font-medium text-gray-900 text-sm">{label}</p>
                  <p className="text-sm text-gray-500">{detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use cases */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <h2 className="text-xl font-bold text-gray-900 mb-6">Built for</h2>
        <div className="grid grid-cols-1 gap-6">
          {USE_CASES.map(({ icon: Icon, iconColor, title, description, example }) => (
            <div key={title} className="rounded-xl border border-gray-200 p-6">
              <div className="flex items-start gap-4">
                <Icon className={`w-5 h-5 ${iconColor} mt-0.5 flex-shrink-0`} />
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed mb-2">{description}</p>
                  <p className="text-xs text-gray-400">e.g. {example}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Why this data doesn't exist elsewhere */}
      <section className="bg-gray-50 border-y border-gray-100 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Why this data is hard to get</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {DIFFERENTIATORS.map(({ icon: Icon, title, description }) => (
              <div key={title} className="bg-white rounded-xl border border-gray-200 p-5">
                <Icon className="w-5 h-5 text-teal-600 mb-3" />
                <h3 className="font-semibold text-gray-900 text-sm mb-1">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Coverage */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Coverage</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { stat: COVERAGE_DISPLAY.totalNswCouncils, label: 'NSW councils', sub: 'Zone + LEP controls' },
            { stat: COVERAGE_DISPLAY.dcpNumericCouncils, label: 'LGAs', sub: 'DCP numeric controls' },
            { stat: COVERAGE_DISPLAY.floodStudies, label: 'council flood studies', sub: 'Flood depth modelling' },
            { stat: COVERAGE_DISPLAY.provisionsTotal, label: 'Provisions', sub: 'Extracted & classified' },
          ].map(({ stat, label, sub }) => (
            <div key={label + sub} className="text-center p-4 rounded-xl border border-gray-200">
              <p className="text-2xl font-bold text-gray-900">{stat}</p>
              <p className="text-sm text-gray-600">{label}</p>
              <p className="text-xs text-gray-400">{sub}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-slate-950 py-12 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-xl font-bold text-white mb-3">Get API access</h2>
          <p className="text-slate-400 text-sm mb-6 max-w-md mx-auto">
            We&apos;re onboarding integration partners. Tell us what you&apos;re building and we&apos;ll set up
            a sandbox with your target LGAs.
          </p>
          <TrackedLink
            href="/contact?ref=api"
            page="developers"
            cta="bottom_request_api"
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-500 transition-colors"
          >
            Request access <ArrowRight className="w-4 h-4" />
          </TrackedLink>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
