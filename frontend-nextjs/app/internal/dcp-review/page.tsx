import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import DcpReviewQueue from './DcpReviewQueue';

export const metadata: Metadata = {
  title: 'DCP review queue — internal',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function DcpReviewPage() {
  // Same auth gate as the internal directory.
  if (process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true') {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      redirect('/login');
    }
  }
  return <DcpReviewQueue />;
}
