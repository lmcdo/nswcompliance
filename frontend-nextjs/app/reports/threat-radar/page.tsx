import type { Metadata } from 'next'
import { ThreatRadarTool } from '@/components/tools/ThreatRadarTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'

export const metadata: Metadata = {
  title: 'Neighbour Development Threat Radar — canibuildit.com.au',
  description: 'See active development applications and CDCs within 500m of any NSW address. Subscribe for weekly alerts when new applications are lodged.',
  openGraph: {
    title: 'What\'s being built near you in NSW?',
    description: 'Active DAs and CDCs within 500m of your address. Free check + $9.99/month monitoring alerts.',
    url: 'https://canibuildit.com.au/reports/threat-radar',
    siteName: 'canibuildit.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Neighbour Development Threat Radar — canibuildit.com.au',
    description: 'Scan for active development applications within 500m of any NSW address. Free.',
  },
}

export default function ThreatRadarPage() {
  return (
    <div>
      <ProductLandingV2 product="threat-radar" />
      <div className="max-w-2xl mx-auto px-4">
        <ThreatRadarTool />
      </div>
    </div>
  )
}
