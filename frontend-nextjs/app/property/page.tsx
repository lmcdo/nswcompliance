import type { Metadata } from 'next';
import { Suspense } from 'react';
import { PropertyProfile } from '@/components/home/PropertyProfile';

export const metadata: Metadata = {
  title: 'Property Profile — PlotDetect',
  description: 'Instant property profile for any NSW address — zoning, height limits, heritage, flood status, and lot dimensions from government data.',
};

export default function PropertyPage() {
  return (
    <Suspense fallback={
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <PropertyProfile />
    </Suspense>
  );
}
