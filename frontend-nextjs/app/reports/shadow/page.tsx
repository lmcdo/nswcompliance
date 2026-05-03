import type { Metadata } from 'next'
import { ShadowTool } from '@/components/tools/ShadowTool'
import { ProductLanding } from '@/components/reports/ProductLanding'

export const metadata: Metadata = {
  title: 'Shadow Risk Analyser — canibuildit.com.au',
  description: 'Will a proposed development cast shadows on your property? Solar access analysis across the five ADG test scenarios for any NSW address.',
  openGraph: {
    title: 'Shadow Risk Analyser — Will that development overshadow your home?',
    description: 'Winter solstice shadow analysis for any NSW address. Check the impact of a proposed building before you object.',
    url: 'https://canibuildit.com.au/reports/shadow',
    siteName: 'canibuildit.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Shadow Risk Analyser — canibuildit.com.au',
    description: 'Shadow path analysis across 5 solar access test scenarios for any NSW address.',
  },
}

export default function ShadowPage() {
  return (
    <div className="max-w-2xl">
      <ProductLanding
        title="Shadow Risk Analyser"
        subtitle="Will a new build next door block your sun?"
        hook="When a neighbour proposes a new build or addition, the first thing that matters is shadow. NSW planning rules require solar access testing at specific dates and times. This tool models the worst-case shadow from a maximum-height building on the adjacent lot — so you know before you object whether there is a real solar access impact."
        checks={[
          {
            title: 'Five ADG solar access scenarios',
            description: 'Shadow modelled at 9am, noon, and 3pm on the winter solstice (June 21), plus noon on the spring equinox (September 21) and summer solstice (December 21). These are the test dates NSW planning panels use.',
          },
          {
            title: 'Maximum-height building envelope',
            description: 'Shadow is cast from the tallest building permitted on the adjacent lot under the applicable planning controls. This is the worst case — the actual development may be shorter.',
          },
          {
            title: 'Shadow path and overlap',
            description: 'For each scenario, the exact shadow direction, length, and whether it crosses onto your property. Displayed on an interactive map so you can see precisely which part of your lot is affected.',
          },
          {
            title: 'Construction activity detection',
            description: 'Satellite imagery analysis to check whether construction has already begun on the adjacent lot. If earthworks or building activity is detected, you may need to act faster.',
          },
        ]}
        comparison={[
          { feature: 'ADG compliance verdict', free: true, paid: true },
          { feature: 'Shadow map (interactive)', free: true, paid: true },
          { feature: 'Worst-case scenario summary', free: true, paid: true },
          { feature: 'All 5 scenario breakdowns', free: false, paid: true },
          { feature: 'Hourly shadow diagrams', free: false, paid: true },
          { feature: 'Construction detection detail', free: false, paid: true },
          { feature: 'Objection-ready summary paragraph', free: false, paid: true },
          { feature: 'Downloadable PDF report', free: false, paid: true },
        ]}
        paidLabel="full report — $29"
        methodology="Solar position is calculated using astronomical algorithms for your exact latitude and longitude at each test date and time. Shadow length and direction are derived geometrically from the maximum permissible building height on the adjacent lot, sourced from the applicable planning controls. No assumptions are made about the design — the model uses the full height envelope. Construction detection uses spectral analysis of satellite imagery to identify disturbed ground."
        coverage="All of NSW. Shadow geometry works anywhere with planning height controls. Construction detection requires recent cloud-free satellite imagery over the site."
      />
      <ShadowTool />
    </div>
  )
}
