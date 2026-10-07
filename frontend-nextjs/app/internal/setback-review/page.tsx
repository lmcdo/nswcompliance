import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { currentReviewer } from '@/lib/internal-reviewer';
import SetbackReviewQueue from './SetbackReviewQueue';

export const metadata: Metadata = {
  title: 'Setback value review — internal',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function SetbackReviewPage() {
  // Allowlisted reviewers only (lib/internal-reviewer.ts); the API routes check again.
  if (!(await currentReviewer())) {
    redirect('/login');
  }
  return <SetbackReviewQueue />;
}
