import type { Metadata } from 'next'
import { FloodTool } from '@/components/tools/FloodTool'
import { ProductLanding } from '@/components/reports/ProductLanding'

export const metadata: Metadata = {
  title: 'Flood Risk Check — canibuildit.com.au',
  description: 'Is this NSW property in a flood zone? Cross-referenced flood assessment from government overlays, satellite imagery, river gauges, and council flood models — free for any address.',
  openGraph: {
    title: 'NSW Flood Risk Check — Free for any address',
    description: 'Government overlays, satellite detection, river gauges, and council flood model depths — cross-referenced for any NSW address. No login required.',
    url: 'https://canibuildit.com.au/reports/flood',
    siteName: 'canibuildit.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NSW Flood Risk Check — canibuildit.com.au',
    description: 'Flood depth and planning implications for any NSW address. Free, instant.',
  },
}

export default function FloodPage() {
  return (
    <div className="max-w-2xl">
      <ProductLanding
        title="Flood Risk Check"
        subtitle="Know exactly how deep the water gets — not just whether it floods."
        hook="Most flood checks tell you in or out. This one cross-references multiple independent government, satellite, and engineering datasets to give you the flood depth at your property for different severity levels. The same data conveyancers, valuers, and insurers need before exchange."
        checks={[
          {
            title: 'Government flood planning overlay',
            description: 'Whether council has formally classified this land under the NSW Government flood planning framework. Covers the full state — the same data that appears on a Section 10.7 certificate.',
          },
          {
            title: 'Council flood model depth and level',
            description: 'Where council has published detailed engineering flood models, we query the actual modelled water depth and level at your property coordinates — for every severity level from minor to catastrophic.',
          },
          {
            title: 'Flood extent mapping',
            description: 'Point-in-polygon check against council and state flood extent boundaries. Over 100 local government areas covered, with per-event severity where available.',
          },
          {
            title: 'Satellite flood detection',
            description: 'European Space Agency radar satellite imagery that sees through cloud cover, compared against a dry-season baseline. Detects recent standing water independent of any government dataset.',
          },
          {
            title: 'Long-term surface water history',
            description: 'Four decades of European and US satellite imagery analysed to calculate what percentage of time your property has had visible surface water. Catches properties near creeks or drainage lines that regularly pool.',
          },
          {
            title: 'River gauge flood history',
            description: 'The nearest Bureau of Meteorology river gauge — how far away, when it last recorded a major flood event, and the peak water height. Shows whether the local catchment has a recent flood record.',
          },
          {
            title: 'Ground elevation',
            description: 'Terrain height above sea level from a high-resolution NSW Government elevation model. Flood depth is the difference between the modelled water level and this ground elevation.',
          },
          {
            title: 'Emergency service activations',
            description: 'International emergency management activations that have mapped flood extent at this location. Confirms whether this property was inside a formally mapped flood event.',
          },
        ]}
        comparison={[
          { feature: '100-year flood zone status', free: true, paid: true },
          { feature: 'Ground elevation', free: true, paid: true },
          { feature: 'Government flood overlay', free: true, paid: true },
          { feature: 'Satellite flood detection', free: true, paid: true },
          { feature: '1-in-100 year flood depth (single event)', free: true, paid: true },
          { feature: 'Historical flood event depths', free: true, paid: true },
          { feature: 'Full AEP depth table (all severity levels)', free: false, paid: true },
          { feature: 'River gauge flood event history', free: false, paid: true },
          { feature: 'Surface water occurrence data', free: false, paid: true },
          { feature: 'Emergency activation records', free: false, paid: true },
          { feature: 'Downloadable PDF report', free: false, paid: true },
        ]}
        paidLabel="full report — $49"
        methodology="Your address is resolved to precise coordinates, then queried against every available flood dataset simultaneously — NSW Government planning layers, council engineering flood models, European Space Agency radar satellites, Bureau of Meteorology river gauges, and international emergency management records. Where council has published flood model grids, we sample the actual raster cell at your property — giving you depth in metres, not just a binary yes or no. All sources are independent: a positive from one confirms or contradicts another."
        coverage="Government flood overlays cover all of NSW. Council flood model depths are available for select areas where councils have published engineering flood study data — coverage is expanding as new studies are released. Satellite and river gauge data cover the full state."
      />
      <FloodTool />
    </div>
  )
}
