import type { Metadata } from 'next'
import { ConveyancingTool } from '@/components/tools/ConveyancingTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'
import { LandingVisibility } from '@/components/reports/landing/LandingVisibility'
import { SoftwareAppJsonLd } from '@/lib/json-ld'

export const metadata: Metadata = {
  title: 'Conveyancing Planning Disclosure — PlotDetect',
  description: 'Instant planning disclosure for any NSW property. LEP controls, environmental overlays, heritage status, SEPP overlays, development feasibility, and DCP setbacks — from live government data.',
  openGraph: {
    title: 'NSW Conveyancing Planning Disclosure — Live Government Data',
    description: 'LEP zone, height, FSR, environmental overlays, heritage, SEPP overlays, development feasibility, and DCP setback controls — queried live from the NSW Planning Portal for any address.',
    url: 'https://verify.plotdetect.com.au/reports/conveyancing',
    siteName: 'plotdetect.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NSW Conveyancing Planning Disclosure — PlotDetect',
    description: 'Planning due diligence for any NSW property. Free instant check, $49 full PDF report.',
  },
}

interface Props {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export default async function ConveyancingPage({ searchParams }: Props) {
  const params = await searchParams
  const hasAddress = !!params.address

  return (
    <div>
      <SoftwareAppJsonLd
        name="Conveyancing Planning Disclosure"
        description="Instant planning disclosure for any NSW property. LEP controls, environmental overlays, heritage status, SEPP overlays, development feasibility, and DCP setbacks — from live government data."
        url="/reports/conveyancing"
      />
      {!hasAddress && <LandingVisibility><ProductLandingV2 product="conveyancing" /></LandingVisibility>}
      <div className="max-w-2xl mx-auto px-4">
        <ConveyancingTool />
      </div>
    </div>
  )
}
