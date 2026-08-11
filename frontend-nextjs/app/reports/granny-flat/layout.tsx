import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Granny Flat Yield Report — NSW',
  // "AI structure detection" is gone from both descriptions. The scan behind
  // that phrase was measured in August 2026 at 14 of 38 visible secondary
  // structures found, and is not what the report rests on — the planning
  // rules are. Advertising the weakest component as the headline feature was
  // backwards even when the number was unknown.
  description: 'Planning rule analysis and rental yield estimate for any NSW property. Aerial imagery, zoning, heritage, and flood checks included.',
  openGraph: {
    title: 'Granny Flat Yield Report — PlotDetect',
    description: 'Could this property earn an extra $280-$340/week? Planning rule analysis for any NSW address.',
    url: '/reports/granny-flat',
  },
};

export default function GrannyFlatReportLayout({ children }: { children: React.ReactNode }) {
  return children;
}
