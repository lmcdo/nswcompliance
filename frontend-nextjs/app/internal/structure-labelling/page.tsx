// prior-art-checked: reuse not viable — see the header of
// app/api/internal/structure-labels/route.ts for the four sweeps. The existing
// /internal queues (dcp-review, setback-review, leads) review rows that already
// hold a machine answer and show it; this surface must withhold one. The auth
// gate below is copied verbatim from setback-review/page.tsx so this sits
// inside the same internal surface rather than beside it.
import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import StructureLabeller from './StructureLabeller';

export const metadata: Metadata = {
  title: 'Structure labelling — internal',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function StructureLabellingPage() {
  // Same auth gate as the rest of the internal directory.
  if (process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true') {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      redirect('/login');
    }
  }
  return <StructureLabeller />;
}
