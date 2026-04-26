import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'How It Works — canibuildit.com.au',
  description: 'Where canibuildit.com.au data comes from, how it is processed, and what the results mean.',
};

const TOOLS = [
  {
    name: 'Granny Flat Eligibility',
    href: '/reports/granny-flat',
    sources: [
      { name: 'NSW Planning Portal (layerintersect API)', use: 'Zone, lot size, strata status, LEP controls' },
      { name: 'SEPP Housing 2021', use: 'Eligibility criteria: lot size ≥450m², not strata, correct zone' },
      { name: 'Google Earth Engine (Sentinel-2)', use: 'Satellite structure detection — identifies existing secondary dwellings' },
      { name: 'NSW Spatial Services geocoder', use: 'Address → coordinates' },
    ],
    cadence: 'Planning portal data is queried live at time of check. Satellite imagery is the most recent available (typically updated annually).',
    limitations: 'Structure detection accuracy is ~85–90% for standard residential lots. Heritage and strata overlays may introduce exceptions not captured here. Always confirm with a certifier before committing.',
  },
  {
    name: 'Flood Risk',
    href: '/reports/flood',
    sources: [
      { name: 'NSW Flood Data Service (SES)', use: 'ARI flood depth modelling (1-in-20 to 1-in-500 year events)' },
      { name: 'NSW Planning Portal', use: 'Flood control lot status from LEP flood overlays' },
      { name: 'PostGIS spatial database', use: 'Pre-processed flood study polygons for 12 LGAs with ARI data' },
    ],
    cadence: 'Flood study data is updated when NSW SES publishes new flood studies (infrequent — typically every 3–5 years per LGA). LEP overlay data is queried live.',
    limitations: 'ARI depth modelling is available for 12 NSW LGAs. Outside these areas, results show flood control lot status only (from the LEP), without depth data. Coverage is expanding.',
  },
  {
    name: 'Solar Yield',
    href: '/reports/solar-yield',
    sources: [
      { name: 'Google Earth Engine (Sentinel-2)', use: 'Roof geometry and orientation derived from satellite imagery' },
      { name: 'Bureau of Meteorology solar radiation data', use: 'Annual solar irradiance by location' },
      { name: 'NSW Spatial Services', use: 'Property boundary and building footprint' },
    ],
    cadence: 'Solar irradiance data is updated annually. Satellite roof detection uses the most recently available cloud-free imagery.',
    limitations: 'Yield estimates assume standard residential panel configurations. Heavily shaded roofs, unusual orientations, or multi-storey buildings may produce less accurate estimates. Results are indicative — a solar installer assessment is required for system sizing.',
  },
  {
    name: 'Shadow Detector',
    href: '/reports/shadow',
    sources: [
      { name: 'Google Earth Engine', use: 'Structure height and footprint estimation from satellite' },
      { name: 'Solar position algorithm', use: 'Sun angle at 9am, noon, and 3pm on June 21 (winter solstice — worst case)' },
      { name: 'NSW Spatial Services', use: 'Property boundaries' },
    ],
    cadence: 'Solar position calculations are deterministic. Structural data is based on available satellite imagery.',
    limitations: 'Shadow analysis is computed for the winter solstice as the worst-case scenario. Results are an estimate — council-submitted shadow diagrams require a licensed surveyor or certifier.',
  },
  {
    name: 'Threat Radar (DA Monitor)',
    href: '/reports/threat-radar',
    sources: [
      { name: 'NSW ePlanning Portal (OnlineDA + OnlineCDC APIs)', use: 'All DA and CDC applications lodged in NSW' },
      { name: 'ETL pipeline (daily)', use: 'Ingests and indexes applications from 128 NSW councils' },
      { name: 'PostGIS spatial index', use: 'Radius search from a geocoded address' },
    ],
    cadence: 'DA data is refreshed daily from the NSW ePlanning Portal. There is typically a 24–48 hour lag from lodgement to appearance in results.',
    limitations: 'Coverage depends on councils submitting applications to the ePlanning Portal. Some councils may have incomplete records. Search radius is 500m for the free check; monitoring alerts cover 200m.',
  },
];

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen bg-white">
      <nav className="flex items-center justify-between px-6 py-4 max-w-3xl mx-auto border-b border-gray-100">
        <Link href="/" className="text-base font-bold tracking-tight text-gray-900">
          canibuildit<span className="text-teal-600">.com.au</span>
        </Link>
        <Link href="/reports/granny-flat" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
          Try the tools →
        </Link>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-14">
        <h1 className="text-3xl font-bold text-gray-900 mb-3">How it works</h1>
        <p className="text-gray-500 text-base mb-12 max-w-xl">
          Every result on canibuildit.com.au comes from live government data sources and satellite
          imagery — not static PDFs or manually maintained databases. Here&apos;s exactly where each
          tool gets its data, how often it updates, and what the limitations are.
        </p>

        <div className="space-y-14">
          {TOOLS.map((tool) => (
            <section key={tool.name}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">{tool.name}</h2>
                <Link
                  href={tool.href}
                  className="text-sm text-teal-600 hover:text-teal-700 transition-colors"
                >
                  Try it →
                </Link>
              </div>

              <div className="mb-4">
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Data sources</p>
                <div className="space-y-2">
                  {tool.sources.map((s) => (
                    <div key={s.name} className="flex gap-3 text-sm">
                      <span className="font-medium text-gray-700 shrink-0 w-64">{s.name}</span>
                      <span className="text-gray-500">{s.use}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-gray-50 rounded-xl p-4 space-y-3">
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Update cadence</p>
                  <p className="text-sm text-gray-600">{tool.cadence}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Limitations</p>
                  <p className="text-sm text-gray-600">{tool.limitations}</p>
                </div>
              </div>
            </section>
          ))}
        </div>

        <div className="mt-16 p-6 bg-teal-50 border border-teal-200 rounded-xl">
          <h3 className="font-semibold text-teal-900 mb-2">A note on accuracy</h3>
          <p className="text-sm text-teal-800 leading-relaxed">
            All results on this platform are <strong>indicative</strong> — they are starting points
            for due diligence, not formal planning determinations. NSW planning controls change
            frequently, and no automated system can substitute for a qualified town planner or
            building certifier reviewing your specific situation. We cite every data source so you
            can verify results directly.
          </p>
        </div>
      </div>

      <footer className="border-t border-gray-100 py-6 px-6">
        <div className="max-w-3xl mx-auto flex flex-wrap gap-4 text-xs text-gray-400">
          <Link href="/" className="hover:text-gray-600">Home</Link>
          <Link href="/pricing" className="hover:text-gray-600">Pricing</Link>
          <Link href="/partner" className="hover:text-gray-600">Embed program</Link>
          <Link href="/privacy" className="hover:text-gray-600">Privacy</Link>
          <Link href="/terms" className="hover:text-gray-600">Terms</Link>
        </div>
      </footer>
    </main>
  );
}
