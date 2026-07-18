import type { Metadata } from 'next';

// Ads landing page: noindex so it never competes with /tools/upzoning-check
// (the SEO surface) in search, and never ranks for the stripped experience.
export const metadata: Metadata = {
  title: 'Can your block take a duplex? Free 10-second check | PlotDetect',
  description:
    'Instant dual-occupancy check for any NSW address against the 2025 housing reforms — live NSW Government planning maps, source clause cited.',
  robots: { index: false, follow: false },
};

export default function DuplexCheckLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
