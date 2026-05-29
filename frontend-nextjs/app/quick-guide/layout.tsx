import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Quick Reference Guide — PlotDetect',
  description: 'Quick reference for PlotDetect features: planning controls, DCP provisions, flood risk, bushfire BAL, and property intelligence tools.',
  openGraph: {
    title: 'PlotDetect Quick Guide',
    description: 'Quick reference for PlotDetect property intelligence features.',
    url: '/quick-guide',
  },
};

export default function QuickGuideLayout({ children }: { children: React.ReactNode }) {
  return children;
}
