import type { Metadata } from 'next'
import { BushfireTool } from '@/components/tools/BushfireTool'

export const metadata: Metadata = {
  title: 'Bushfire Pre-Screen — canibuildit.com.au',
  description: 'Is this NSW property on bushfire prone land? Check BFPL category, estimated BAL band, RFS referral requirements, and 10/50 clearing entitlements for any NSW address — free.',
  openGraph: {
    title: 'NSW Bushfire Pre-Screen — Free for any address',
    description: 'BFPL category, BAL band estimate, and development implications. Takes 15 seconds. No login required.',
    url: 'https://canibuildit.com.au/reports/bushfire',
    siteName: 'canibuildit.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NSW Bushfire Pre-Screen — canibuildit.com.au',
    description: 'Bushfire prone land status and planning implications for any NSW address. Free, instant.',
  },
}

export default function BushfirePage() {
  return (
    <div className="max-w-2xl">
      <BushfireTool />
    </div>
  )
}
