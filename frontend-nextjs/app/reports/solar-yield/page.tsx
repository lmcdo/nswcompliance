import type { Metadata } from 'next'
import { SolarYieldTool } from '@/components/tools/SolarYieldTool'

export const metadata: Metadata = {
  title: 'Solar Yield Estimate — canibuildit.com.au',
  description: 'How much solar can this NSW roof generate? Get an estimated annual kWh yield from satellite roof geometry and orientation — free.',
  openGraph: {
    title: 'Solar Yield Estimate — Free for any NSW address',
    description: 'Satellite-derived roof geometry + BOM solar irradiance = your estimated annual yield. Takes 60 seconds.',
    url: 'https://canibuildit.com.au/reports/solar-yield',
    siteName: 'canibuildit.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Solar Yield Estimate — canibuildit.com.au',
    description: 'Annual solar yield estimate for any NSW address. Free, instant.',
  },
}

export default function SolarYieldPage() {
  return (
    <div className="max-w-2xl">
      <SolarYieldTool />
    </div>
  )
}
