import type { Metadata } from 'next'
import { ThreatRadarTool } from '@/components/tools/ThreatRadarTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'
import { LandingVisibility } from '@/components/reports/landing/LandingVisibility'
import { SoftwareAppJsonLd } from '@/lib/json-ld'

export const metadata: Metadata = {
  title: 'Development Monitoring — PlotDetect',
  description: 'See active development applications and CDCs within 500m of any NSW address. Subscribe for weekly alerts when new applications are lodged.',
  openGraph: {
    title: 'What\'s being built near you in NSW?',
    description: 'Active DAs and CDCs within 500m of your address. Free check + $9.99/month monitoring alerts.',
    url: 'https://verify.plotdetect.com.au/reports/threat-radar',
    siteName: 'plotdetect.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Development Monitoring — PlotDetect',
    description: 'Scan for active development applications within 500m of any NSW address. Free.',
  },
}

interface Props {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export default async function ThreatRadarPage({ searchParams }: Props) {
  const params = await searchParams
  const hasAddress = !!params.address

  return (
    <div>
      <SoftwareAppJsonLd
        name="Development Monitoring"
        description="See active development applications and CDCs within 500m of any NSW address. Subscribe for weekly alerts when new applications are lodged."
        url="/reports/threat-radar"
      />
      {!hasAddress && <LandingVisibility><ProductLandingV2 product="threat-radar" /></LandingVisibility>}
      <div className="max-w-2xl mx-auto px-4">
        <ThreatRadarTool />
      </div>
    </div>
  )
}
