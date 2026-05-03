import type { Metadata } from 'next'
import { ThreatRadarTool } from '@/components/tools/ThreatRadarTool'
import { ProductLanding } from '@/components/reports/ProductLanding'

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
    <div className="max-w-2xl">
      <ProductLanding
        title="Neighbour Development Threat Radar"
        subtitle="Know before your neighbour breaks ground."
        hook="New development next door can block your sunlight, remove your views, increase traffic, and reduce your property value. Most homeowners find out too late — after construction has started. This tool monitors the NSW planning system so you find out first."
        checks={[
          {
            title: 'Active development applications',
            description: 'Every DA lodged within 500m of your property in the last 6 months — including the development description, estimated cost, and how many new dwellings are proposed.',
          },
          {
            title: 'Complying development certificates',
            description: 'CDCs bypass council notification entirely — your neighbour can start building without you knowing. This scan catches CDCs that would otherwise be invisible until construction begins.',
          },
          {
            title: 'Distance from your property',
            description: 'Each application is ranked by proximity to your address so you can focus on the ones that matter most. Applications directly next door are flagged separately from those down the street.',
          },
          {
            title: 'Determination status',
            description: 'Whether each application is still being assessed, has been approved, refused, or withdrawn. For applications under assessment, you still have time to lodge a submission.',
          },
        ]}
        comparison={[
          { feature: 'Nearby DA and CDC scan (500m)', free: true, paid: true },
          { feature: 'First 3 applications visible', free: true, paid: true },
          { feature: 'All applications visible', free: false, paid: true },
          { feature: 'Weekly email alerts (new lodgements)', free: false, paid: true },
          { feature: 'Ongoing monitoring', free: false, paid: true },
        ]}
        paidLabel="monitoring — $9.99/month"
        methodology="Your address is geocoded and we scan the NSW Government planning system for every DA and CDC lodged within 500m in the past 180 days. Distance is calculated from the applicant site to your property. Subscribers receive a weekly digest every Monday at 7am with any new applications detected since the last scan."
        coverage="All of NSW. Any council that publishes development applications through the state planning system is covered."
      />
      <ThreatRadarTool />
    </div>
  )
}
