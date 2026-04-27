import type { Metadata } from 'next'
import { FloodTool } from '@/components/tools/FloodTool'

export const metadata: Metadata = {
  title: 'Flood Risk Check — canibuildit.com.au',
  description: 'Is this NSW property in a flood zone? Get modelled ARI flood depth and LEP flood control lot status for any NSW address — free.',
  openGraph: {
    title: 'NSW Flood Risk Check — Free for any address',
    description: 'Modelled ARI flood depth and LEP flood control lot status. Takes 30 seconds. No login required.',
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
      <FloodTool />
    </div>
  )
}
