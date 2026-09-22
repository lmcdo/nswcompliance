import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import PipelineStatus from './PipelineStatus';

export const metadata: Metadata = {
  title: 'Pipeline status — internal',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function PipelineStatusPage() {
  // Same auth gate as the rest of /internal.
  if (process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true') {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      redirect('/login');
    }
  }
  return <PipelineStatus />;
}
