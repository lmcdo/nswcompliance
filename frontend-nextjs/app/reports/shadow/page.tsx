import type { Metadata } from 'next'
import { ShadowTool } from '@/components/tools/ShadowTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'

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

interface Props {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export default async function ShadowPage({ searchParams }: Props) {
  const params = await searchParams
  const hasAddress = !!params.address

  return (
    <div>
      {!hasAddress && <ProductLandingV2 product="shadow" />}
      <div className="max-w-2xl mx-auto px-4">
        <ShadowTool />
      </div>
    </div>
  )
}
