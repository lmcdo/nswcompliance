import type { Metadata } from 'next'
import { ShadowTool } from '@/components/tools/ShadowTool'

export const metadata: Metadata = {
  title: 'Shadow Detector — canibuildit.com.au',
  description: 'Will a proposed addition cast shadows on your property? Check shadow impact at 9am, noon, and 3pm on the winter solstice for any NSW address.',
  openGraph: {
    title: 'Shadow Detector — Will that development overshadow your home?',
    description: 'Winter solstice shadow analysis for any NSW address. Check the impact of a proposed building before you object.',
    url: 'https://canibuildit.com.au/reports/shadow',
    siteName: 'canibuildit.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Shadow Detector — canibuildit.com.au',
    description: 'Shadow path analysis at 9am, noon, and 3pm on June 21 for any NSW address.',
  },
}

export default function ShadowPage() {
  return <ShadowTool />
}
