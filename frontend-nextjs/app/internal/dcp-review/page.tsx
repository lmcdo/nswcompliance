import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { currentReviewer } from '@/lib/internal-reviewer';
import DcpReviewQueue from './DcpReviewQueue';

export const metadata: Metadata = {
  title: 'DCP review queue — internal',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function DcpReviewPage() {
  // Allowlisted reviewers only (lib/internal-reviewer.ts); the API routes check again.
  if (!(await currentReviewer())) {
    redirect('/login');
  }
  return <DcpReviewQueue />;
}
