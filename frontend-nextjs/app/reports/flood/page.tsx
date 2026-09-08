import type { Metadata } from 'next'
import { FloodTool } from '@/components/tools/FloodTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'
import { LandingVisibility } from '@/components/reports/landing/LandingVisibility'
import { SoftwareAppJsonLd } from '@/lib/json-ld'

export const metadata: Metadata = {
  title: 'Flood Screening — PlotDetect',
  description: 'Is this NSW property in a flood zone? Cross-referenced flood assessment from government overlays, satellite imagery, river gauges, and council flood models — free for any address.',
  openGraph: {
    title: 'NSW Flood Screening — Free for any address',
    description: 'Government overlays, satellite detection, river gauges, and council flood model depths — cross-referenced for any NSW address. No login required.',
    url: 'https://verify.plotdetect.com.au/reports/flood',
    siteName: 'plotdetect.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NSW Flood Screening — PlotDetect',
    description: 'Flood depth and planning implications for any NSW address. Free, instant.',
  },
}

interface Props {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export default async function FloodPage({ searchParams }: Props) {
  const params = await searchParams
  const hasAddress = !!params.address

  return (
    <div>
      <SoftwareAppJsonLd
        name="Flood Screening"
        description="Is this NSW property in a flood zone? Cross-referenced flood assessment from government overlays, satellite imagery, river gauges, and council flood models — free for any address."
        url="/reports/flood"
      />
      {!hasAddress && <LandingVisibility><ProductLandingV2 product="flood" /></LandingVisibility>}
      <div className="max-w-2xl mx-auto px-4">
        <FloodTool />
      </div>
    </div>
  )
}
