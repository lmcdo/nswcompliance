import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { HowToJsonLd } from '@/lib/json-ld';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

export const metadata: Metadata = {
  title: 'How It Works — PlotDetect',
  description: 'Where PlotDetect data comes from, how it is processed, and what the results mean.',
};

const TOOLS = [
  {
    name: 'Site Report',
    href: '/reports/intelligence-brief',
    sources: [
      { name: 'NSW Planning Portal (layerintersect + lot APIs)', use: 'Zone, height, FSR, lot size, heritage and environmental overlays, plus the cadastral lot geometry' },
      { name: 'NSW Valuer General', use: 'Land value with five-year history, comparable valuations and recent sales within 500 m' },
      { name: 'NSW cadastre (strata/lot)', use: 'Lot type, plan number and strata structure' },
      { name: 'SEPP (Housing) 2021 standards + live reform mapping', use: 'Per-form eligibility (dual occupancy, terraces, apartments) against the state standards, with the reform-area and TOD catchment checked on live government map layers' },
      { name: 'Council DCP setback controls', use: 'Setback, landscaping and parking numbers feeding the development capacity estimate' },
      { name: 'NSW ePlanning Portal (OnlineDA + tracking data)', use: 'Nearby applications, determination outcomes and council-wide refusal rates' },
      { name: 'Satellite and imagery layers', use: 'Aerial structure detection, solar yield (Google Solar), flood screening (JRC/WOfS/BoM), bushfire status (RFS), terrain (5 m DEM) and NARCliM 2.0 climate projections' },
    ],
    cadence: 'Government APIs are queried live when the brief runs (typically 1–2 minutes end to end). Satellite layers use each source’s own imagery cadence. DCP controls and land-use tables are updated as councils are onboarded and re-checked by weekly source monitoring.',
    limitations: 'The development capacity figure is a computed ceiling from mapped controls — not an approval outcome, and merit assessment can produce a different result. Eligibility outcomes are subject to a development application. Layers with no data for a property say so — absence of data is not clearance. Every figure carries its source and as-at date.',
  },
  {
    name: 'Granny Flat Eligibility',
    href: '/granny-flat',
    sources: [
      { name: 'NSW Planning Portal (lot API)', use: 'Zone, lot size, strata status, heritage, and LEP controls for the property' },
      { name: 'SEPP Housing 2021 criteria', use: 'State-wide eligibility rules: minimum 450 m² lot, permitted zones, not strata' },
      { name: 'NSW SIX Maps aerial imagery', use: 'High-resolution aerial tiles of the lot, shown with its boundary so you can see what is already built on it' },
      { name: 'Council DCP setback controls', use: 'Secondary dwelling setback, landscaping, and parking standards by LGA' },
    ],
    cadence: 'Planning Portal data is queried live at time of check. Aerial imagery is updated by NSW Spatial Services (typically annually). DCP controls are updated when new LGAs are onboarded.',
    // The figure below replaces "~85-90% for standard residential lots", which
    // was an estimate written from a single test address and was never
    // measured. It is published here because it was published wrong here.
    limitations: 'Structures already on the lot are identified by you from the aerial image, not found automatically. An automated scan was measured in August 2026 against human review of 56 lots across four councils: it located 14 of the 38 secondary structures a person could see, and reported a further 15 that were not there. It is not used to decide eligibility. Heritage overlays and strata restrictions may introduce exceptions. DCP setback data is available for councils with structured controls. Always confirm with a certifier before committing.',
  },
  {
    name: 'Flood Screening',
    href: '/reports/flood',
    sources: [
      { name: 'NSW SEED EPI Flood Planning overlay', use: 'Statutory flood zone classification from the state-wide EPI hazard layer (ArcGIS REST)' },
      { name: 'Council flood studies', use: 'Flood planning area extents and AEP tier classifications from council-published studies' },
      { name: 'Flood study rasters', use: 'Design flood depths and water levels at specific AEP events (1-in-5 through PMF)' },
      { name: 'Copernicus EMS flood activations', use: 'Satellite-confirmed historical flood event records' },
      { name: 'JRC Global Surface Water', use: '40-year surface water occurrence from Landsat imagery (1984–present)' },
      { name: 'DEA Water Observations (WOfS)', use: 'Australian surface water frequency from Landsat (1987–present, 25 m resolution)' },
      { name: 'BOM Water Data Online', use: 'Nearest river gauge, last major flood event, and flood event history' },
      { name: 'NSW 5 m DEM (SIX Maps)', use: 'Ground elevation to compute flood depth from water level surfaces' },
    ],
    cadence: 'EPI overlay and BOM gauge data are queried live. Council flood studies are updated when new studies are published (typically every 3–5 years per LGA). JRC and DEA datasets use multi-year composites.',
    limitations: 'EPI flood overlay coverage is limited to LGAs that have uploaded polygon data to the state portal (~11 LGAs). Council flood study rasters are available for 3 study areas (expanding). Where no data is available, the result shows "unavailable" — absence of data is not clearance.',
  },
  {
    name: 'Solar Potential',
    href: '/reports/solar-yield',
    sources: [
      { name: 'Google Solar API', use: 'Roof geometry, panel layout, segment orientation, and annual energy yield estimate' },
      { name: 'NSW Heritage Register', use: 'Heritage listing check — heritage properties may face additional approval requirements for solar installations' },
      { name: 'LEP Height of Buildings controls', use: 'Maximum permitted building height for neighbouring lots (shadow cross-sell context)' },
    ],
    cadence: 'Google Solar API data is queried live. Heritage and height data are queried live from spatial overlays.',
    limitations: 'Yield estimates are based on Google Solar API modelling and assume standard panel configurations. Heavily shaded roofs, unusual orientations, or multi-storey buildings may produce less accurate estimates. Results are indicative — a CEC-accredited solar installer assessment is required for system sizing.',
  },
  {
    name: 'Shadow Analysis',
    href: '/reports/shadow',
    sources: [
      { name: 'NSW Planning Portal (lot API)', use: 'Cadastral lot boundary for the subject property' },
      { name: 'pybdshadow shadow-casting model', use: 'Shadow geometry at 9 am, noon, and 3 pm on June 21 (winter solstice — worst case), with sun position derived from the modelled date and time' },
      { name: 'LEP height limit controls', use: 'Maximum permitted building height from LEP and DCP to model worst-case neighbour shadow' },
    ],
    cadence: 'Solar position calculations are deterministic. LEP height controls are queried live.',
    limitations: 'Shadow analysis is computed for the winter solstice as the worst-case scenario. Height estimates use LEP-permitted maximums, not actual building heights. Results are an estimate — council-submitted shadow diagrams require a licensed surveyor or certifier.',
  },
  {
    name: 'Pre-DA Site History',
    href: '/reports/pre-da-history',
    sources: [
      { name: 'ESA Sentinel-2 satellite imagery (via Element84)', use: 'Annual satellite composites for year-on-year physical change detection (2017–present)' },
      { name: 'Vegetation and built-up spectral indices', use: 'NDVI and NDBI indices to distinguish construction activity from natural vegetation changes' },
      { name: 'NSW ePlanning Portal (OnlineDA + OnlineCDC)', use: 'DA, CDC, construction certificate, and occupation certificate records for the address' },
      { name: 'NSW Government spatial overlays', use: 'Heritage conservation area boundary check' },
      { name: 'NSW Planning Portal (geocoder)', use: 'Address resolution to precise lot coordinates' },
    ],
    cadence: 'Satellite composites are based on annual dry-season imagery (June–September, lowest cloud cover). DA records are queried live from the ePlanning Portal. Heritage overlays are updated when councils publish new spatial data.',
    limitations: 'Satellite change detection has ~10 m resolution — small structures (sheds, fences) may not register. DA records depend on councils submitting to the ePlanning Portal. Heritage overlays cover conservation areas only, not all individual heritage items.',
  },
  {
    name: 'Development Monitor',
    href: '/reports/threat-radar',
    sources: [
      { name: 'NSW ePlanning Portal (OnlineDA + OnlineCDC)', use: 'All DA and CDC applications lodged across NSW' },
      { name: 'Automated daily ingestion', use: `Applications from ${COVERAGE_DISPLAY.totalNswCouncils} NSW councils indexed and geocoded daily` },
    ],
    cadence: 'DA data is refreshed daily from the NSW ePlanning Portal. There is typically a 24–48 hour lag from lodgement to appearance in results.',
    limitations: 'Coverage depends on councils submitting applications to the ePlanning Portal. Some councils may have incomplete records. Search radius is 500 m for the free check; monitoring alerts cover 200 m.',
  },
  {
    name: 'Bushfire Pre-Screen',
    href: '/reports/bushfire',
    sources: [
      { name: 'NSW Rural Fire Service (BFPL Map)', use: 'Bush Fire Prone Land classification — Category 1, 2, 3 and vegetation buffer zones (ArcGIS REST)' },
      { name: 'NSW Government spatial overlays', use: 'Flood, heritage, and zone overlay cross-checks for the property' },
    ],
    cadence: 'RFS BFPL dataset is updated annually. Spatial overlay data is queried live.',
    limitations: 'BAL band estimation is indicative and based on vegetation proximity, not a formal AS 3959 assessment. A certified BAL report from an accredited practitioner is required for DA lodgement in bushfire-prone areas.',
  },
  {
    name: 'Conveyancing Planning Disclosure',
    href: '/reports/conveyancing',
    sources: [
      { name: 'NSW Planning Portal (layerintersect API)', use: 'Zone, FSR, height, heritage, environmental overlays, LEP provisions' },
      { name: 'Council DCP provisions', use: `Setback controls, parking rates, and landscaping standards for ${COVERAGE_DISPLAY.dcpNumericCouncils} LGAs` },
      { name: 'NSW Rural Fire Service', use: 'Bushfire-prone land status' },
      { name: 'NSW Government spatial overlays', use: 'Flood control lot status from LEP and council flood studies' },
    ],
    cadence: 'Planning Portal data is queried live. DCP provisions are updated when new LGAs are onboarded or instruments are amended.',
    limitations: `DCP setback controls are available for ${COVERAGE_DISPLAY.dcpNumericCouncils} LGAs. Full DCP coverage (all provision types) is available for Inner West Council. The conveyancing disclosure does not replace a section 10.7 planning certificate.`,
  },
  {
    name: 'Climate Risk Score',
    href: '/climate-risk',
    sources: [
      { name: 'NARCliM 2.0', use: 'Regional climate projections — temperature and precipitation change to 2099 under SSP2.45 and SSP3.70 scenarios' },
      { name: 'NSW Rural Fire Service', use: 'Bush Fire Prone Land classification' },
      { name: 'NSW Planning Portal', use: 'EPI flood overlay data' },
      { name: 'SEPP (Resilience and Hazards) 2021', use: 'Coastal management zone mapping' },
      { name: 'NPWS fire history dataset', use: 'Historical fire scar polygons' },
    ],
    cadence: 'NARCliM projections are static (model outputs do not change). RFS and flood data are queried live. Fire history is updated when NPWS publishes new data.',
    limitations: 'The composite score is deterministic and based on publicly available hazard datasets. It does not account for property-level factors (construction type, elevation within lot, vegetation management). The Climate Risk Report (with full NARCliM trajectories) is not yet available — pending incorporation and professional indemnity insurance.',
  },
];

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      <HowToJsonLd
        name="How to check NSW planning controls and property constraints with PlotDetect"
        description="PlotDetect queries live NSW government data sources and satellite imagery to check zoning, flood risk, bushfire status, heritage overlays, and development controls for any NSW property address."
        steps={[
          { name: 'Enter a NSW property address', text: 'Type any NSW address into the search bar. PlotDetect resolves it to precise lot coordinates using the NSW Planning Portal geocoder.' },
          { name: 'Select a planning check', text: 'Choose from granny flat eligibility, flood risk, bushfire pre-screen, planning controls, shadow analysis, solar potential, or development monitoring.' },
          { name: 'Review live government data', text: 'Results are queried live from NSW Planning Portal, Rural Fire Service, spatial overlays, and council DCPs. Every data source is cited.' },
          { name: 'Check spatial overlays', text: 'Heritage items, flood planning areas, bushfire-prone land, biodiversity, acid sulfate soils, and coastal zones are checked against 27 spatial layers.' },
          { name: 'Read the limitations', text: 'Every result includes data source citations, update cadence, and limitations. Results are indicative — always verify with a qualified professional.' },
        ]}
      />
      <div className="max-w-3xl mx-auto px-6 py-14">
        <h1 className="text-3xl font-bold text-gray-900 mb-3">How it works</h1>
        <p className="text-gray-500 text-base mb-12 max-w-xl">
          Every result on plotdetect.com.au comes from live government data sources and satellite
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

        {/* --- How we check our work --- */}
        <div className="mt-16 space-y-10">
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">How we check our work</h2>
            <p className="text-sm text-gray-600 mb-5">
              Every data source listed above is monitored by automated checks that run daily.
              If a government API goes down, returns unexpected data, or stops responding entirely,
              our monitoring flags it before any report is affected.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">15</p>
                <p className="text-xs text-gray-500 mt-1">Data sources monitored daily</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">100%</p>
                <p className="text-xs text-gray-500 mt-1">Reports with full audit trail</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">&lt; 2 min</p>
                <p className="text-xs text-gray-500 mt-1">Alert time on source failure</p>
              </div>
            </div>
            <ul className="text-sm text-gray-600 space-y-2">
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span>Every report records the exact API endpoints queried, response timestamps, and data versions used.</li>
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span>Reports with missing audit data or empty outputs are flagged automatically and withheld until resolved.</li>
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span>Source health checks probe each API for expected response structure, not just HTTP 200 status.</li>
            </ul>
          </section>

          {/* --- How results are computed --- */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">How results are computed</h2>
            <p className="text-sm text-gray-600 mb-3">
              Every tool on this platform uses deterministic processing. Given the same property
              and the same source data, the result is identical every time. There is no AI
              interpretation, no language model inference, and no probabilistic scoring in the
              compliance pipeline.
            </p>
            <ul className="text-sm text-gray-600 space-y-2">
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span>Planning controls are extracted verbatim from government instruments — never paraphrased or summarised.</li>
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span>Satellite analysis uses published spectral indices with fixed thresholds, not trained classifiers.</li>
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span>Where multiple data sources cover the same property, all are shown independently — we do not blend or average conflicting values.</li>
            </ul>
          </section>

          {/* --- Where location-specific rules come from --- */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Where location-specific (precinct) rules come from</h2>
            <p className="text-sm text-gray-600 mb-3">
              Some council DCP chapters apply only inside mapped areas — town centres, beachfront
              character areas, named sites. The boundary of each area is defined by a map figure in
              the adopted DCP document itself, and that figure is the authority. Council online
              mapping services publish machine-readable copies of those figures, which councils
              label as a guide only.
            </p>
            <p className="text-sm text-gray-600 mb-3">
              Before a boundary is used to match addresses, it goes through a fixed set of checks:
            </p>
            <ul className="text-sm text-gray-600 space-y-2 mb-3">
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span>Geometry checks — the polygon must be valid, in the expected coordinate system, with area and location consistent with the adopted figure.</li>
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span>Point checks against the adopted figure — real addresses geocoded through the NSW Planning Portal, chosen from inside and outside the mapped area, must match or not match exactly as the DCP figure shows. Negative tests (addresses that must return no match) are part of the set.</li>
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span>Provenance recorded — each stored boundary records the DCP map figure it copies, the geometry source, and the date it was checked.</li>
            </ul>
            <p className="text-sm text-gray-600 mb-3">
              Where an area&apos;s boundary has not passed these checks, its location-specific rules are
              excluded from results and the report states that site-specific controls may exist for
              the property — a missing boundary is disclosed, never silently filled in. Where mapped
              areas overlap, the rules for every applicable area are returned. The per-property
              legal record of which controls apply remains a Section 10.7 planning certificate
              issued by the council.
            </p>
          </section>

          {/* --- What this is not --- */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">What this is not</h2>
            <ul className="text-sm text-gray-600 space-y-2">
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span><strong>Not a planning certificate.</strong> These results do not replace a Section 10.7 certificate issued by council.</li>
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span><strong>Not legal or financial advice.</strong> We present government data — interpretation requires a qualified professional.</li>
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span><strong>Not a substitute for site inspection.</strong> Satellite and spatial data cannot capture every on-ground condition.</li>
              <li className="flex gap-2"><span className="text-teal-600 shrink-0">-</span><strong>Not exhaustive.</strong> Where data is unavailable for a property, the result states &ldquo;unavailable&rdquo; — absence of data is not clearance.</li>
            </ul>
          </section>
        </div>

        <div className="mt-10 p-6 bg-teal-50 border border-teal-200 rounded-xl">
          <h3 className="font-semibold text-teal-900 mb-2">A note on accuracy</h3>
          <p className="text-sm text-teal-800 leading-relaxed">
            All results on this platform are <strong>indicative</strong> — they are starting points
            for due diligence, not formal planning determinations. NSW planning controls change
            frequently, and no automated system can substitute for a qualified town planner or
            building certifier reviewing your specific situation. We cite every data source so you
            can verify results directly.
          </p>
          <p className="text-sm text-teal-800 mt-3">
            <Link
              href="/blog/how-we-validate-property-data-nsw"
              className="font-medium text-teal-700 underline underline-offset-2 hover:text-teal-900 transition-colors"
            >
              Read how we validate data before it reaches you →
            </Link>
          </p>
        </div>
      </div>

      <SiteFooter />
    </main>
  );
}
