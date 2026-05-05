import type { Metadata } from 'next'
import { PreDAHistoryTool } from '@/components/tools/PreDAHistoryTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'

export const metadata: Metadata = {
  title: 'Pre-DA Site History Report — canibuildit.com.au',
  description: 'What happened on this land before you got here? Satellite change detection, DA history, heritage overlay, and flood/fire annotations for any NSW address.',
  openGraph: {
    title: 'Pre-DA Site History — Satellite change detection for any NSW address',
    description: 'Eight years of satellite imagery analysed for physical changes, cross-referenced with DA records, heritage overlays, and natural disaster events. Free to run.',
    url: 'https://canibuildit.com.au/reports/pre-da-history',
    siteName: 'canibuildit.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Pre-DA Site History — canibuildit.com.au',
    description: 'Satellite change detection + DA history for any NSW address. Free, instant.',
  },
}

export default function PreDAHistoryPage() {
  return (
    <div>
      <ProductLandingV2 product="pre-da" />
      <div className="max-w-2xl mx-auto px-4">
        <PreDAHistoryTool />
      </div>
    </div>
  )
}
