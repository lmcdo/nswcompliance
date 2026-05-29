import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'User Guide — How to Use PlotDetect',
  description: 'Step-by-step guide to using PlotDetect for property intelligence, planning controls, flood risk, and compliance checks across NSW.',
  openGraph: {
    title: 'PlotDetect User Guide',
    description: 'Learn how to use PlotDetect for property intelligence and planning compliance in NSW.',
    url: '/user-guide',
  },
};

export default function UserGuideLayout({ children }: { children: React.ReactNode }) {
  return children;
}
