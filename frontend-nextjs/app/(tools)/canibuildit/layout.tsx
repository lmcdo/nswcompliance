import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Granny Flat Income Calculator NSW — Free Eligibility & Yield Check',
  description: 'Could your NSW property support a granny flat worth $280–$340/week? Free instant check — lot size, zoning, heritage, flood rules — with a rental yield estimate. No signup.',
};

export default function CanIBuildItLayout({ children }: { children: React.ReactNode }) {
  return children;
}
