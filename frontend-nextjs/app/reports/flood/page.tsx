import type { Metadata } from 'next'
import { FloodTool } from '@/components/tools/FloodTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'

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
    <div>
      <ProductLandingV2 product="flood" />
      <div className="max-w-2xl mx-auto px-4">
        <FloodTool />
      </div>
    </div>
  )
}
