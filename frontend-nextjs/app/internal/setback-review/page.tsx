import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import SetbackReviewQueue from './SetbackReviewQueue';

export const metadata: Metadata = {
  title: 'Setback value review — internal',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function SetbackReviewPage() {
  // Same auth gate as the rest of the internal directory.
  if (process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true') {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      redirect('/login');
    }
  }
  return <SetbackReviewQueue />;
}
