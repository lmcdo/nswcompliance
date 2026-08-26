import type { Metadata } from 'next'
import { BushfireTool } from '@/components/tools/BushfireTool'
import { ProductLandingV2 } from '@/components/reports/landing/ProductLandingV2'
import { LandingVisibility } from '@/components/reports/landing/LandingVisibility'
import { SoftwareAppJsonLd } from '@/lib/json-ld'

export const metadata: Metadata = {
  title: 'Bushfire Pre-Screen — PlotDetect',
  description: 'Is this NSW property on bushfire prone land? Check BFPL category, estimated BAL band, RFS referral requirements, and 10/50 clearing entitlements for any NSW address — free.',
  openGraph: {
    title: 'NSW Bushfire Pre-Screen — Free for any address',
    description: 'BFPL category, BAL band estimate, and development implications. Takes 15 seconds. No login required.',
    url: 'https://verify.plotdetect.com.au/reports/bushfire',
    siteName: 'plotdetect.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NSW Bushfire Pre-Screen — PlotDetect',
    description: 'Bushfire prone land status and planning implications for any NSW address. Free, instant.',
  },
}

interface Props {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export default async function BushfirePage({ searchParams }: Props) {
  const params = await searchParams
  const hasAddress = !!params.address

  return (
    <div>
      <SoftwareAppJsonLd
        name="Bushfire Pre-Screen"
        description="Is this NSW property on bushfire prone land? Check BFPL category, estimated BAL band, RFS referral requirements, and 10/50 clearing entitlements for any NSW address — free."
        url="/reports/bushfire"
      />
      {!hasAddress && <LandingVisibility><ProductLandingV2 product="bushfire" /></LandingVisibility>}
      <div className="max-w-2xl mx-auto px-4">
        <BushfireTool />
      </div>
    </div>
  )
}
