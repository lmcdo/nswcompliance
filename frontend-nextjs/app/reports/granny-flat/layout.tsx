import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Granny Flat Yield Report — NSW',
  description: 'AI structure detection, planning rule analysis, and rental yield estimate for any NSW property. Aerial imagery, zoning, heritage, and flood checks included.',
  openGraph: {
    title: 'Granny Flat Yield Report — PlotDetect',
    description: 'Could this property earn an extra $280-$340/week? AI structure detection and planning analysis for any NSW address.',
    url: '/reports/granny-flat',
  },
};

export default function GrannyFlatReportLayout({ children }: { children: React.ReactNode }) {
  return children;
}
