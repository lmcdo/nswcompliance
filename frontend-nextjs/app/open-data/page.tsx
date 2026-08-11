import type { Metadata } from 'next';
import Link from 'next/link';
import { DatasetJsonLd } from '@/lib/json-ld';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';
import { DATA_DICTIONARY_FIELDS } from '@/lib/data-dictionary';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

export const metadata: Metadata = {
  title: 'NSW Planning Open Data — Datasets Available on PlotDetect',
  description: `Structured NSW planning datasets available on PlotDetect: secondary dwelling statistics for ${COVERAGE_DISPLAY.secondaryDwellingCouncils} councils, ${COVERAGE_DISPLAY.regulatoryDefinitions} regulatory definitions, ${COVERAGE_DISPLAY.heritageAreas} heritage conservation areas, SEPP Housing numeric standards, ${COVERAGE_DISPLAY.dcpActionableProvisions} actionable DCP provisions, flood study peak levels to 1-in-5000 AEP, and estuarine tidal inundation extents.`,
  openGraph: {
    title: 'NSW Planning Open Data — PlotDetect Datasets',
    description:
      'Structured planning data for New South Wales with source citations and legislative references.',
    url: '/open-data',
    siteName: 'PlotDetect',
    type: 'website',
  },
};

const DATASETS = [
  {
    name: 'Secondary Dwelling Application Statistics',
    description:
      'DA and CDC application volumes, processing times, pathway ratios, and self-reported build costs for secondary dwellings across 102 NSW councils. Derived from the NSW Planning Portal open data API.',
    records: `${COVERAGE_DISPLAY.secondaryDwellingCouncils} councils`,
    currency: '2026-05-20',
    source: 'NSW Planning Portal open data API',
    sourceUrl: 'https://www.planningportal.nsw.gov.au/opendata/dataset/online-da-data-api',
    pageUrl: '/blog/granny-flat',
    pageLabel: 'Granny Flat Statistics',
    variableMeasured: [
      'Total applications',
      'CDC count',
      'DA count',
      'CDC pathway ratio',
      'Median CDC processing days',
      'Median build cost',
      'Year-over-year volumes',
    ],
    caveats:
      'Cost is self-reported at lodgement. DA status is "Determined" only — the portal does not distinguish between granted and refused outcomes.',
  },
  {
    name: 'NSW Planning Regulatory Definitions',
    description:
      'Definitions of planning terms extracted from NSW LEPs, DCPs, and SEPPs. Each definition includes the source document, clause reference, legislation type, and domain tags.',
    records: `${COVERAGE_DISPLAY.regulatoryDefinitions} definitions`,
    currency: 'Stable since January 2026',
    source: 'NSW LEP, DCP, and SEPP instruments',
    sourceUrl: 'https://legislation.nsw.gov.au',
    pageUrl: '/glossary',
    pageLabel: 'Planning Glossary',
    variableMeasured: [
      'Term',
      'Definition text',
      'Source document',
      'Source clause',
      'Legislation type',
      'Domain tags',
    ],
    caveats: null,
  },
  {
    name: 'Heritage Conservation Areas',
    description:
      'Heritage conservation areas across NSW with names, significance classifications, LGA assignments, and geographic boundaries. Sourced from council heritage studies and NSW Heritage databases.',
    records: `${COVERAGE_DISPLAY.heritageAreas} areas`,
    currency: 'Current',
    source: 'Council heritage studies and NSW Heritage databases',
    sourceUrl: null,
    pageUrl: '/assessment',
    pageLabel: 'Compliance Check (Heritage tab)',
    variableMeasured: [
      'Area name',
      'Significance classification',
      'LGA',
      'Geographic boundary',
      'Publication date',
    ],
    caveats: null,
  },
  {
    name: 'SEPP Housing 2021 Numeric Standards',
    description:
      'Structured numeric development standards from SEPP (Housing) 2021 and the NSW Apartment Design Guide. Covers height limits, lot sizes, floor areas, site coverage, parking rates, setbacks, and ADG design criteria — grouped by development type with clause references.',
    records: `${COVERAGE_DISPLAY.seppStandards} SEPP standards + ${COVERAGE_DISPLAY.adgCriteria} ADG design criteria`,
    currency: 'Legislative instruments — amended periodically',
    source: 'SEPP (Housing) 2021 and NSW Apartment Design Guide (March 2023)',
    sourceUrl: 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
    pageUrl: '/planning-standards',
    pageLabel: 'SEPP Housing Standards',
    variableMeasured: [
      'Maximum building height',
      'Minimum lot size',
      'Maximum floor area',
      'Maximum site coverage',
      'Parking rates',
      'Solar access hours',
      'Building separation distances',
    ],
    caveats: null,
  },
  {
    name: 'DCP Provisions (Actionable)',
    description:
      'Development Control Plan provisions extracted from council DCP documents, tagged by topic (parking, setbacks, heritage, waste, landscaping), precinct, applicable zones, and development types. Deep coverage for Inner West Council; shallower for other LGAs.',
    records: `${COVERAGE_DISPLAY.dcpActionableProvisions} actionable provisions`,
    currency: 'Varies by LGA — extracted from current DCP documents',
    source: 'Council DCP documents (PDF extraction)',
    sourceUrl: null,
    pageUrl: '/assessment',
    pageLabel: 'Compliance Check (DCP tab)',
    variableMeasured: [
      'Provision text',
      'Topic classification',
      'Precinct assignment',
      'Applicable zones',
      'Applicable development types',
      'Numeric values',
      'PDF page reference',
    ],
    caveats:
      'Coverage depth varies by council. Inner West has ~4,600 provisions; other councils have fewer. Provisions are extracted from DCP PDFs and may not capture all amendments.',
  },
  {
    name: 'Council Flood Study Peak Flood Levels',
    description:
      'Peak flood level and depth grids from published flood studies, sampled per property. Four studies: Hawkesbury FRMSP 2025, Tweed Valley 2024, Wollongong 2024, and Redbank Creek 2025 — with design events from 50% AEP down to 1-in-5000 AEP and PMF where the study publishes them, plus modelled historical events such as March 2022.',
    records: '4 studies · up to 11 design events each',
    currency: 'Study publications 2024–2025',
    source: 'NSW Flood Data Portal (NSW SES) and council flood studies',
    sourceUrl: 'https://flooddata.ses.nsw.gov.au',
    pageUrl: '/reports/flood',
    pageLabel: 'Flood Report',
    variableMeasured: [
      'Peak flood level (m AHD)',
      'Peak flood depth (m)',
      'AEP design event',
      'Modelled historical event levels',
      'Study name and publication',
    ],
    caveats:
      'Coverage is limited to each study’s modelled extent. Values are read from the published model grids; each study applies its own filtering criteria to shallow or low-hazard cells.',
  },
  {
    name: 'Estuarine Tidal Inundation Extents (2050 / 2100)',
    description:
      'NSW-wide mapped extents showing how often low-lying land near estuaries is under tidal water, modelled under the SSP3-7.0 emissions scenario at 2050 and 2100 across four inundation frequencies (1 to 182.5 days per year). Surfaced as a mapped-extent disclosure in conveyancing reports.',
    records: '1,415 mapped polygons',
    currency: 'Published 24 November 2025',
    source: 'NSW Estuarine Inundation 2025 — NSW DCCEEW (SEED portal, CC BY 4.0)',
    sourceUrl: 'https://www.seed.nsw.gov.au',
    pageUrl: '/conveyancing',
    pageLabel: 'Conveyancing Report',
    variableMeasured: [
      'Mapped inundation extent',
      'Scenario (SSP3-7.0)',
      'Projection year (2050, 2100)',
      'Inundation frequency (days/year)',
    ],
    caveats:
      'Estuarine tidal inundation only — does not cover open-coast or surf inundation, coastal erosion, or rainfall-driven river flooding.',
  },
] as const;

export default function OpenDataPage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      {/* One DatasetJsonLd per dataset */}
      {DATASETS.map(ds => (
        <DatasetJsonLd
          key={ds.name}
          name={ds.name}
          description={ds.description}
          url={`https://canibuildit.com.au${ds.pageUrl}`}
          spatialCoverage="New South Wales, Australia"
          variableMeasured={[...ds.variableMeasured]}
          license="Derived from NSW Government open data and legislative instruments"
        />
      ))}

      {/* Header */}
      <div className="mb-10">
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          NSW planning data on PlotDetect
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed max-w-2xl">
          Structured datasets sourced from NSW Government systems and legislative
          instruments. All data is surfaced through the pages linked below — we do
          not offer bulk downloads, because regulatory data changes frequently and
          downloaded files become stale.
        </p>
      </div>

      {/* Dataset cards */}
      <div className="space-y-6 mb-10">
        {DATASETS.map(ds => (
          <div
            key={ds.name}
            className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8"
          >
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">{ds.name}</h2>
                <p className="text-sm text-slate-600 mt-1 leading-relaxed max-w-xl">
                  {ds.description}
                </p>
              </div>
              <Link
                href={ds.pageUrl}
                className="shrink-0 inline-flex items-center rounded-lg border border-teal-200 bg-teal-50 px-4 py-2 text-sm font-medium text-teal-700 hover:bg-teal-100 transition-colors"
              >
                {ds.pageLabel}
              </Link>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">
                  Records
                </p>
                <p className="text-sm font-semibold text-slate-900 mt-0.5">
                  {ds.records}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">
                  Last updated
                </p>
                <p className="text-sm font-semibold text-slate-900 mt-0.5">
                  {ds.currency}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">
                  Source
                </p>
                <p className="text-sm text-slate-900 mt-0.5">
                  {ds.sourceUrl ? (
                    <a
                      href={ds.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-teal-600 hover:text-teal-800 underline underline-offset-2"
                    >
                      {ds.source}
                    </a>
                  ) : (
                    ds.source
                  )}
                </p>
              </div>
            </div>

            {/* Variables measured */}
            <div className="mt-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider font-medium mb-2">
                Fields
              </p>
              <div className="flex flex-wrap gap-1.5">
                {ds.variableMeasured.map(v => (
                  <span
                    key={v}
                    className="text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-600"
                  >
                    {v}
                  </span>
                ))}
              </div>
            </div>

            {ds.caveats && (
              <p className="text-xs text-slate-400 mt-4 leading-relaxed">
                {ds.caveats}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Data dictionary */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 mb-10">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-2">
          Data dictionary
        </h2>
        <p className="text-sm text-slate-600 leading-relaxed mb-4">
          Per-field documentation for the structured planning data PlotDetect
          serves: what each field is, the authoritative source it is read from,
          its licence and attribution, how current it is, and its limits.
        </p>
        <div className="flex flex-wrap gap-2">
          {DATA_DICTIONARY_FIELDS.map(f => (
            <Link
              key={f.slug}
              href={`/open-data/fields/${f.slug}`}
              className="inline-flex items-center rounded-lg border border-teal-200 bg-teal-50 px-4 py-2 text-sm font-medium text-teal-700 hover:bg-teal-100 transition-colors"
            >
              {f.name}
            </Link>
          ))}
        </div>
      </div>

      {/* Why no downloads */}
      <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8 mb-10">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-2">
          Why no bulk downloads?
        </h2>
        <p className="text-sm text-slate-600 leading-relaxed">
          NSW planning instruments (LEPs, DCPs, SEPPs) are amended regularly.
          Downloaded CSV or JSON files become stale the moment an instrument is
          updated. The pages above are revalidated daily so they reflect the current
          state of the data. If you need programmatic access for a specific use case,{' '}
          <Link
            href="/contact"
            className="text-teal-600 hover:text-teal-800 underline underline-offset-2"
          >
            get in touch
          </Link>
          .
        </p>
      </div>

      {/* Data sources */}
      <div className="mb-10">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4">
          Authoritative sources
        </h2>
        <ul className="space-y-2 text-sm text-slate-600">
          <li>
            <a
              href="https://www.planningportal.nsw.gov.au"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-600 hover:text-teal-800 underline underline-offset-2"
            >
              NSW Planning Portal
            </a>
            {' '}&mdash; zoning, overlays, LEP controls, DA/CDC data
          </li>
          <li>
            <a
              href="https://legislation.nsw.gov.au"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-600 hover:text-teal-800 underline underline-offset-2"
            >
              NSW Legislation
            </a>
            {' '}&mdash; EPIs, SEPPs, LEPs, Apartment Design Guide
          </li>
          <li>Council Development Control Plans (PDF documents)</li>
          <li>NSW Spatial Services &mdash; cadastral boundaries</li>
          <li>Bureau of Meteorology &mdash; climate and solar data</li>
          <li>NSW Rural Fire Service &mdash; bushfire-prone land mapping</li>
          <li>
            <a
              href="https://flooddata.ses.nsw.gov.au"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-600 hover:text-teal-800 underline underline-offset-2"
            >
              NSW Flood Data Portal (SES)
            </a>
            {' '}&mdash; council flood study model outputs
          </li>
          <li>
            <a
              href="https://www.seed.nsw.gov.au"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-600 hover:text-teal-800 underline underline-offset-2"
            >
              NSW SEED portal (DCCEEW)
            </a>
            {' '}&mdash; estuarine inundation mapping
          </li>
        </ul>
      </div>

      <BlogDisclaimer />
    </div>
  );
}
