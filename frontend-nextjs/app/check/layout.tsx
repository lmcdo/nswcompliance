import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Pre-DA Check — CDC vs DA Pathway',
  description: 'Check if your deck, garage, or extension qualifies for Complying Development (CDC) or needs a full Development Application (DA). Free for any NSW address.',
  openGraph: {
    title: 'CDC vs DA Pathway Check — PlotDetect',
    description: 'Find out if your project qualifies for the faster CDC approval pathway or needs a full DA through council.',
    url: '/check',
  },
};

export default function CheckLayout({ children }: { children: React.ReactNode }) {
  return children;
}
