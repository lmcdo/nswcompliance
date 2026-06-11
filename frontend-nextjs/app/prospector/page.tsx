import { Suspense } from 'react';
import type { Metadata } from 'next';

import ProspectorClient from '@/components/prospector/ProspectorClient';

export const metadata: Metadata = {
  title: 'Prospector — Bulk Lot Search | PlotDetect',
  description:
    'Search Inner West lots by zone, area, GFA, dwellings, and constraint layers with pre-computed development envelope arithmetic.',
  robots: { index: false, follow: false },
};

export default function ProspectorPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-screen-2xl mx-auto px-6 py-8">
          <div className="h-8 w-48 bg-gray-100 rounded animate-pulse" />
        </div>
      }
    >
      <ProspectorClient />
    </Suspense>
  );
}
