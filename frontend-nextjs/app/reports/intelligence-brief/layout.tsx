// prior-art-checked: mirrors the metadata pattern of app/reports/conveyancing/page.tsx —
// the brief page is a client component, so route metadata lives in this layout.
import type { Metadata } from 'next';
import { SoftwareAppJsonLd } from '@/lib/json-ld';

export const metadata: Metadata = {
  title: 'Property Site Report — PlotDetect',
  description:
    'One NSW address — planning controls, environmental constraints, valuation, nearby applications and computed development capacity, with every figure traced to its source.',
  openGraph: {
    title: 'NSW Property Site Report — Live Government Data',
    description:
      'Planning controls, hazards, valuation, nearby DAs and computed development capacity for a single NSW address — streamed in about 40 seconds, every figure cited to its source.',
    url: 'https://brief.plotdetect.com.au',
    siteName: 'plotdetect.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NSW Property Site Report — PlotDetect',
    description:
      'One address, one brief: planning controls, hazards, valuation, nearby applications and computed development capacity.',
  },
};

export default function IntelligenceBriefLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SoftwareAppJsonLd
        name="Property Site Report"
        description="Planning controls, environmental constraints, valuation, nearby applications and computed development capacity for a single NSW address — every figure traced to its source."
        url="/reports/intelligence-brief"
      />
      {children}
    </>
  );
}
