import type { Metadata } from 'next'
import { SolarYieldTool } from '@/components/tools/SolarYieldTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'
import { LandingVisibility } from '@/components/reports/landing/LandingVisibility'
import { ProductJsonLd } from '@/lib/json-ld'

export const metadata: Metadata = {
  title: 'Rooftop Solar Potential Estimate — PlotDetect',
  description: "How much solar can this NSW roof generate? Roof geometry and an annual kWh estimate relayed from Google's Solar API — free for any address.",
  openGraph: {
    title: 'Rooftop Solar Potential — Free for any NSW address',
    description: "Google's roof geometry and annual yield figure for your address, with published system losses applied. Takes 60 seconds.",
    url: 'https://verify.plotdetect.com.au/reports/solar-yield',
    siteName: 'plotdetect.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Rooftop Solar Potential Estimate — PlotDetect',
    description: 'Annual solar yield estimate for any NSW address. Free, instant.',
  },
}

interface Props {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export default async function SolarYieldPage({ searchParams }: Props) {
  const params = await searchParams
  const hasAddress = !!params.address

  return (
    <div>
      <ProductJsonLd
        name="Rooftop Solar Potential Estimate"
        description="How much solar can this NSW roof generate? Roof geometry and an annual kWh estimate relayed from Google's Solar API — free for any address."
        url="/reports/solar-yield"
        price="39"
      />
      {!hasAddress && <LandingVisibility><ProductLandingV2 product="solar" /></LandingVisibility>}
      <div className="max-w-2xl mx-auto px-4">
        <SolarYieldTool />
      </div>
    </div>
  )
}
