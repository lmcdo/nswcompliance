import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Browse DCP Provisions — NSW Development Control Plans',
  description: 'Navigate NSW Development Control Plan provisions by council, section, and topic. Setbacks, height limits, landscaping, parking, and heritage controls for 28+ councils.',
  openGraph: {
    title: 'Browse DCP Provisions — PlotDetect',
    description: 'Search and navigate Development Control Plan provisions across 28+ NSW councils.',
    url: '/dcp-browse',
  },
};

export default function DCPBrowseLayout({ children }: { children: React.ReactNode }) {
  return children;
}
