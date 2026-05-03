import type { Metadata } from 'next'
import { SolarYieldTool } from '@/components/tools/SolarYieldTool'
import { ProductLanding } from '@/components/reports/ProductLanding'

export const metadata: Metadata = {
  title: 'Rooftop Solar Yield Estimate — canibuildit.com.au',
  description: 'How much solar can this NSW roof generate? Satellite-derived roof geometry and local irradiance data for an estimated annual kWh yield — free for any address.',
  openGraph: {
    title: 'Rooftop Solar Yield — Free for any NSW address',
    description: 'Satellite roof geometry + local irradiance = your estimated annual yield. Takes 60 seconds.',
    url: 'https://canibuildit.com.au/reports/solar-yield',
    siteName: 'canibuildit.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Rooftop Solar Yield Estimate — canibuildit.com.au',
    description: 'Annual solar yield estimate for any NSW address. Free, instant.',
  },
}

export default function SolarYieldPage() {
  return (
    <div className="max-w-2xl">
      <ProductLanding
        title="Rooftop Solar Yield Estimate"
        subtitle="How much could solar earn on this roof?"
        hook="Before you quote a system, you need to know whether the roof is worth it. This tool analyses the actual roof geometry from satellite data, combines it with local irradiance measurements, and estimates annual generation — so you can size the system and price the job before you visit the site."
        checks={[
          {
            title: 'Roof geometry and orientation',
            description: 'Roof area, pitch angle, and compass orientation derived from NSW Government building footprint data. The best-performing roof plane is identified automatically.',
          },
          {
            title: 'Local solar irradiance',
            description: 'Annual sunshine hours and irradiance for your location, sourced from Bureau of Meteorology climate records. Accounts for latitude, cloud cover, and local climate patterns.',
          },
          {
            title: 'Annual generation estimate',
            description: 'Estimated kWh output per year based on the roof geometry and local irradiance. Graded A through F — A-grade roofs have optimal north-facing orientation and minimal shading.',
          },
          {
            title: 'Heritage and planning constraints',
            description: 'Flags heritage-listed properties where visible solar panels may require council approval. Prevents wasted site visits to properties that need a DA before installation.',
          },
        ]}
        comparison={[
          { feature: 'Suitability grade (A–F)', free: true, paid: true },
          { feature: 'Best roof orientation', free: true, paid: true },
          { feature: 'Annual kWh estimate', free: true, paid: true },
          { feature: 'Heritage flag', free: true, paid: true },
          { feature: 'System sizing (kW and panel count)', free: false, paid: true },
          { feature: 'Installed cost estimate', free: false, paid: true },
          { feature: 'Annual savings and feed-in contribution', free: false, paid: true },
          { feature: 'Payback period', free: false, paid: true },
          { feature: 'Downloadable PDF report', free: false, paid: true },
        ]}
        paidLabel="full report — $19"
        methodology="Building footprints are matched to your address using NSW Government property boundary and structure data. Roof orientation and pitch are derived from the footprint geometry. Annual irradiance is calculated from Bureau of Meteorology climate records for your location. The generation estimate applies standard panel efficiency and system loss factors to the usable roof area and irradiance."
        coverage="Sydney metropolitan area and major NSW regional centres. Properties in areas without building footprint coverage will show as unavailable — coverage is expanding."
      />
      <SolarYieldTool />
    </div>
  )
}
