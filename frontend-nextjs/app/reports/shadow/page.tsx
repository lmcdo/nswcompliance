import type { Metadata } from 'next'
import { ShadowTool } from '@/components/tools/ShadowTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'
import { LandingVisibility } from '@/components/reports/landing/LandingVisibility'
import { ProductJsonLd } from '@/lib/json-ld'

export const metadata: Metadata = {
  title: 'Overshadowing Check — PlotDetect',
  description: 'Will a proposed development cast shadows on your property? Solar access analysis across the five ADG test scenarios for any NSW address.',
  openGraph: {
    title: 'Overshadowing Check — Will that development overshadow your home?',
    description: 'Winter solstice shadow analysis for any NSW address. Check the impact of a proposed building before you object.',
    url: 'https://verify.plotdetect.com.au/reports/shadow',
    siteName: 'plotdetect.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Overshadowing Check — PlotDetect',
    description: 'Shadow path analysis across 5 solar access test scenarios for any NSW address.',
  },
}

interface Props {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export default async function ShadowPage({ searchParams }: Props) {
  const params = await searchParams
  const hasAddress = !!params.address

  return (
    <div>
      <ProductJsonLd
        name="Overshadowing Check"
        description="Will a proposed development cast shadows on your property? Solar access analysis across the five ADG test scenarios for any NSW address."
        url="/reports/shadow"
        price="39"
      />
      {!hasAddress && <LandingVisibility><ProductLandingV2 product="shadow" /></LandingVisibility>}
      <div className="max-w-2xl mx-auto px-4">
        <ShadowTool />
      </div>
    </div>
  )
}
