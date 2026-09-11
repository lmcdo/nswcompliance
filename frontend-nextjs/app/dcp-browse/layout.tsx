import type { Metadata } from 'next';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

export const metadata: Metadata = {
  title: 'Browse DCP Provisions — NSW Development Control Plans',
  description: `Navigate NSW Development Control Plan provisions by council, section, and topic. Setbacks, height limits, landscaping, parking, and heritage controls for ${COVERAGE_DISPLAY.dcpNumericCouncils} NSW council areas.`,
  openGraph: {
    title: 'Browse DCP Provisions — PlotDetect',
    description: `Search and navigate Development Control Plan provisions across ${COVERAGE_DISPLAY.dcpNumericCouncils} NSW council areas.`,
    url: '/dcp-browse',
  },
};

export default function DCPBrowseLayout({ children }: { children: React.ReactNode }) {
  return children;
}
