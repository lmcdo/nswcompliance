import { Suspense } from 'react';
import EvidenceStatement from './EvidenceStatement';

// prior-art-checked: no planner evidence page exists (grep app/ components/ hooks/ for evidence, 2026-11-20). AreaCheckCard shows the area check inside Site Facts;
// this page prints the same facts plus the law wording, council controls and council files held, from /api/housing-sepp/evidence.
export const metadata = { title: 'Site evidence statement' };

export default function Page() {
  return (
    <Suspense fallback={<p className="p-6 text-sm">Loading...</p>}>
      <EvidenceStatement />
    </Suspense>
  );
}
