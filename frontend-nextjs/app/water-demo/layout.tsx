/**
 * Water Rights MVP - Demo Layout
 * Provides consistent navigation across demo pages
 */

import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'WaterRight - Water Allocation Management',
  description: 'Real-time water allocation tracking and compliance management for Australian farmers',
};

export default function WaterDemoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
