import type { Metadata } from 'next'
import { SolarYieldTool } from '@/components/tools/SolarYieldTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'
import { solarConfig } from '@/components/reports/landing/data/solar'

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
    <div>
      <ProductLandingV2 config={solarConfig} />
      <div className="max-w-2xl mx-auto px-4">
        <SolarYieldTool />
      </div>
    </div>
  )
}
