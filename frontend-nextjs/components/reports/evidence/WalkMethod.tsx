// prior-art-checked: 2026-11-24. The evidence page had one 'How it is measured' sentence in app/reports/evidence-statement/EvidenceStatement.tsx and the 'How this was measured' box in ProofSection.tsx (what the
// tool read and when); neither says in plain words how the walk is calculated or how sure it is. Wording only: every statement describes what services/lmr_walk_surface.py does; the only figure shown
// (the unmapped-entrance allowance) is read from the payload and left out when it is absent or zero.
import React from 'react';
import type { Evidence } from '@/lib/evidence-statement';
import { fmtNum } from '@/lib/evidence-summary';

/** A plain-English box under the walk: how the number is worked out, how sure it is, and what to do before relying on it. */
export default function WalkMethod({ walk }: { walk: Evidence['walk'] }) {
  const extra = typeof walk.entrance_unmapped_extra_m === 'number' && Number.isFinite(walk.entrance_unmapped_extra_m) && walk.entrance_unmapped_extra_m > 0 ? walk.entrance_unmapped_extra_m : null;
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-gray-200 bg-gray-50 p-5 text-sm leading-relaxed text-gray-800">
      <div>
        <p className="font-semibold">How the walk is calculated</p>
        <ol className="mt-2 flex list-decimal flex-col gap-1 pl-5">
          <li><strong>The route.</strong> Footpaths from OpenStreetMap, the open map of the world. The route may cross a road wherever the map shows a crossing or a junction. The crossings-only walk shown below limits busy-road crossings to traffic lights, zebra and marked crossings.</li>
          <li><strong>The start.</strong> The nearest part of the lot. The law counts a lot if any part of it is within the distance, so the walk starts from the point on the lot&apos;s boundary that is closest to the station entrance or town centre.</li>
          <li><strong>The finish.</strong> The nearest station entrance, or the edge of a town centre.</li>
          <li><strong>The distance.</strong> The shortest walk along those footpaths, added up in metres. It is not a straight line.</li>
          <li><strong>Checks.</strong> The tool refuses impossible answers, such as a walk shorter than the straight line or a lot with no footpath nearby. It says it cannot tell instead of guessing.</li>
        </ol>
      </div>
      <div>
        <p className="font-semibold">How sure is this?</p>
        <p>It is a measurement on a map, not a survey. It can be wrong where a footpath or crossing is missing from the map, or where the map shows one the street does not have. The closer the walk is to the limit, the more it is worth checking.{extra !== null ? ` The station entrance is not on the map, so the walk is measured to the station building: the real walk could be up to ${fmtNum(extra)} m longer.` : ''}</p>
      </div>
      <div>
        <p className="font-semibold">Before relying on it</p>
        <p>Walk the route, or check the lot on the NSW Planning Portal Spatial Viewer, or ask the council for a planning certificate.</p>
      </div>
    </div>
  );
}
