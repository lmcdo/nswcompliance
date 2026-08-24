'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

/* ------------------------------------------------------------------ */
/*  Who's asking — the persona filter                                  */
/* ------------------------------------------------------------------ */

type PersonaKey = 'owner' | 'conveyancer' | 'agent' | 'planner' | 'builder';

const PERSONAS: { key: PersonaKey; label: string }[] = [
  { key: 'owner', label: 'Buying or building' },
  { key: 'conveyancer', label: 'Conveyancer' },
  { key: 'agent', label: 'Buyers agent' },
  { key: 'planner', label: 'Planner' },
  { key: 'builder', label: 'Builder / developer' },
];

const ALL: PersonaKey[] = ['owner', 'conveyancer', 'agent', 'planner', 'builder'];

/* ------------------------------------------------------------------ */
/*  What data exists × what you can do with it                         */
/*  coverage strings come from lib/coverage.ts (single source of truth)*/
/* ------------------------------------------------------------------ */

interface Capability {
  title: string;
  data: string;        // what the data is
  youCanDo: string;    // what you can do with it
  coverage: string;    // how much of NSW it covers
  source: string;      // where it comes from
  href: string;
  personas: PersonaKey[];
}

const DOMAINS: { domain: string; items: Capability[] }[] = [
  {
    domain: 'Planning & zoning',
    items: [
      {
        title: 'Zone & permitted uses',
        data: 'Zone code plus the full permitted and prohibited land-use table for the lot.',
        youCanDo: 'See what the land is allowed to be used for before you bid or design.',
        coverage: `${COVERAGE_DISPLAY.totalNswCouncils} councils (statewide)`,
        source: 'NSW Planning Portal',
        href: '/assessment',
        personas: ALL,
      },
      {
        title: 'LEP numeric controls',
        data: 'Height of buildings, floor space ratio, minimum lot size and heritage listing per lot.',
        youCanDo: 'Know the hard limits on what can be built before spending on a design.',
        coverage: `${COVERAGE_DISPLAY.totalNswCouncils} councils (statewide)`,
        source: 'NSW Planning Portal',
        href: '/assessment',
        personas: ['owner', 'conveyancer', 'agent', 'planner', 'builder'],
      },
      {
        title: 'DCP controls',
        data: 'Setbacks, parking rates, landscaping and site coverage as numeric fields with clause citations.',
        youCanDo: 'Design to the actual council controls before lodging a DA.',
        coverage: `${COVERAGE_DISPLAY.dcpNumericCouncils} councils numeric · ${COVERAGE_DISPLAY.dcpFullCouncils} full structured`,
        source: 'Council Development Control Plans',
        href: '/assessment',
        personas: ['conveyancer', 'planner', 'builder'],
      },
      {
        title: 'SEPP & exempt / complying',
        data: 'Which state planning policies apply, and whether work is exempt or complying development.',
        youCanDo: 'Check whether you can skip a full DA before you start.',
        coverage: 'Statewide',
        source: 'State Environmental Planning Policies',
        href: '/check',
        personas: ['owner', 'planner', 'builder'],
      },
    ],
  },
  {
    domain: 'Hazard & climate',
    items: [
      {
        title: 'Flood depth',
        data: 'Modelled flood depth at different return periods — not just a flood-zone yes/no.',
        youCanDo: 'See how deep it floods before you commit.',
        coverage: `${COVERAGE_DISPLAY.floodStudies} council flood studies`,
        source: 'Council flood studies + satellite',
        href: '/reports/flood',
        personas: ['owner', 'conveyancer', 'agent'],
      },
      {
        title: 'Bushfire',
        data: 'Bush Fire Prone Land category and an estimated BAL band.',
        youCanDo: 'Know if a bushfire report and construction upgrades will be needed.',
        coverage: 'Statewide',
        source: 'NSW Rural Fire Service',
        href: '/reports/bushfire',
        personas: ['owner', 'conveyancer', 'builder'],
      },
      {
        title: 'Spatial overlays',
        data: '27 constraint layers — heritage, biodiversity, acid sulfate, riparian, foreshore and more.',
        youCanDo: 'Find every mapped constraint on the lot in a single pass.',
        coverage: 'Statewide',
        source: 'NSW Government spatial data',
        href: '/assessment',
        personas: ALL,
      },
      {
        title: 'Climate projections',
        data: 'Heat-stress and rainfall trajectories to 2099 with composite hazard scoring.',
        youCanDo: 'Understand how the risk profile changes over the years you will hold it.',
        coverage: 'Statewide',
        source: 'NARCliM 2.0',
        href: '/climate-risk',
        personas: ['owner', 'conveyancer'],
      },
    ],
  },
  {
    domain: 'Satellite & imagery',
    items: [
      {
        title: 'Structures & granny-flat yield',
        data: 'Buildings detected from aerial imagery plus SEPP granny-flat eligibility and a rental estimate.',
        youCanDo: 'See what is on the block and what a second dwelling could return.',
        coverage: 'Statewide',
        source: 'Satellite imagery + Planning Portal',
        href: '/reports/granny-flat',
        personas: ['owner', 'agent'],
      },
      {
        title: 'Solar potential',
        data: 'Roof geometry and orientation resolved into an estimated annual generation.',
        youCanDo: 'Size up rooftop solar before getting a quote.',
        coverage: 'Statewide',
        source: 'Satellite imagery + Bureau of Meteorology',
        href: '/reports/solar-yield',
        personas: ['owner'],
      },
      {
        title: 'Overshadowing',
        data: 'Shadow modelled from the maximum-height building envelope on the ADG solar-access test dates.',
        youCanDo: 'Check the solar-access impact of a design or a neighbour proposal.',
        coverage: 'Statewide',
        source: 'Terrain + envelope model',
        href: '/reports/shadow',
        personas: ['owner', 'planner'],
      },
      {
        title: 'Site change history',
        data: 'Eight years of satellite change detection cross-referenced with DA records and heritage.',
        youCanDo: 'See what was built, cleared or applied for on the site before buying.',
        coverage: 'Statewide',
        source: 'Satellite imagery + DA records',
        href: '/reports/pre-da-history',
        personas: ['owner', 'agent', 'conveyancer'],
      },
    ],
  },
  {
    domain: 'Development activity',
    items: [
      {
        title: 'Nearby DAs & alerts',
        data: 'Every DA and CDC within 500m, with optional weekly email alerts on new lodgements.',
        youCanDo: 'Track what is being built around a property.',
        coverage: `${COVERAGE_DISPLAY.totalNswCouncils} councils`,
        source: 'NSW ePlanning Portal',
        href: '/reports/threat-radar',
        personas: ['owner', 'agent'],
      },
      {
        title: 'DA analytics',
        data: 'Approval rates, processing times and common refusal reasons by council.',
        youCanDo: 'Set expectations before you lodge or advise a client.',
        coverage: `${COVERAGE_DISPLAY.totalNswCouncils} councils`,
        source: 'NSW ePlanning Portal',
        href: '/validate',
        personas: ['agent', 'planner', 'builder'],
      },
    ],
  },
  {
    domain: 'Reference data',
    items: [
      {
        title: 'Extracted provisions corpus',
        data: 'The full body of indexed planning provisions behind every check.',
        youCanDo: 'Filter thousands of provisions down to the ones that apply to one site.',
        coverage: `${COVERAGE_DISPLAY.provisionsTotal} provisions`,
        source: 'LEP / DCP / SEPP instruments',
        href: '/assessment',
        personas: ['planner'],
      },
      {
        title: 'Planning definitions',
        data: 'Plain-language definitions of planning terms, each with its source clause.',
        youCanDo: 'Look up what a planning term actually means.',
        coverage: `${COVERAGE_DISPLAY.regulatoryDefinitions} definitions`,
        source: 'LEP / DCP / SEPP instruments',
        href: '/glossary',
        personas: ALL,
      },
    ],
  },
];

export function CapabilityExplorer() {
  const [persona, setPersona] = useState<PersonaKey | 'all'>('all');

  const visibleDomains = DOMAINS
    .map(({ domain, items }) => ({
      domain,
      items: persona === 'all' ? items : items.filter((c) => c.personas.includes(persona)),
    }))
    .filter(({ items }) => items.length > 0);

  return (
    <section className="py-14 px-6 bg-white">
      <div className="max-w-5xl mx-auto">
        {/* Persona filter */}
        <div className="flex flex-wrap items-center gap-2 mb-10">
          <span className="text-sm font-medium text-slate-500 mr-1">I&apos;m a…</span>
          <button
            type="button"
            onClick={() => setPersona('all')}
            aria-pressed={persona === 'all'}
            className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
              persona === 'all'
                ? 'bg-teal-600 text-white border-teal-600'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
            }`}
          >
            Everyone
          </button>
          {PERSONAS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setPersona(key)}
              aria-pressed={persona === key}
              className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
                persona === key
                  ? 'bg-teal-600 text-white border-teal-600'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Capability grid, grouped by data domain */}
        <div className="space-y-12">
          {visibleDomains.map(({ domain, items }) => (
            <div key={domain}>
              <h2 className="text-lg font-bold text-slate-900 tracking-tight mb-4">{domain}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {items.map((c) => (
                  <Link
                    key={c.title}
                    href={c.href}
                    className="group rounded-2xl border border-slate-200 p-6 hover:border-teal-400/50 hover:shadow-md transition-all"
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h3 className="font-semibold text-slate-900 group-hover:text-teal-700 transition-colors">
                        {c.title}
                      </h3>
                      <ArrowRight className="shrink-0 w-4 h-4 text-slate-300 mt-1 group-hover:text-teal-500 group-hover:translate-x-0.5 transition-all" />
                    </div>
                    <p className="text-sm text-slate-500 leading-relaxed mb-3">{c.data}</p>
                    <p className="text-sm text-slate-700 leading-relaxed mb-4">
                      <span className="font-medium text-teal-700">You can: </span>
                      {c.youCanDo}
                    </p>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400 border-t border-slate-100 pt-3">
                      <span><span className="font-medium text-slate-500">Coverage:</span> {c.coverage}</span>
                      <span><span className="font-medium text-slate-500">Source:</span> {c.source}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
