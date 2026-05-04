import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Can I Build a Granny Flat? — Free NSW Eligibility Check',
  description: 'Instant granny flat eligibility check for any NSW property. Redirects to the full tool.',
};

export default function CanIBuildItLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
