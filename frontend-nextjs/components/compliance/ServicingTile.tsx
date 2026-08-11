'use client';

// prior-art-checked: no existing tile shows Sydney Water servicing. Fetches the new
// /api/servicing route (point-in-polygon over sydney_water_gsp_servicing). Mirrors the
// compact constraint-tile markup in LepControls; fails silent (renders nothing) on
// no-coords / failed / error so a lookup miss never reads as a false "clear".

import { useEffect, useState } from 'react';
import { Gauge, ExternalLink } from 'lucide-react';

const GSP_URL =
  'https://www.sydneywater.com.au/plumbing-building-developing/developing/growth-servicing-plan.html';

interface Product {
  status_code: string;
  constrained: boolean;
  timeframe: string | null;
  dsp_price_per_et: number | null;
}
interface ServicingResponse {
  status: 'found' | 'empty' | 'failed';
  ww?: Product | null;
  dw?: Product | null;
}

const STAGE_HUMAN: Record<string, string> = {
  IN_DELIVERY: 'servicing in delivery',
  PLANNED: 'servicing planned',
  NO_CURRENT_PROJECT: 'no current servicing project',
  UNKNOWN_STAGE: 'stage not stated',
};

function productLine(label: string, p?: Product | null): string | null {
  if (!p) return null;
  const stage = STAGE_HUMAN[p.status_code] ?? 'stage not stated';
  const tfLower = p.timeframe?.toLowerCase();
  const tf = tfLower && tfLower !== 'no timeframe noted.' ? ` (${p.timeframe})` : '';
  return `${label}: ${stage}${tf}`;
}

export function ServicingTile({ lat, lng }: { lat?: number | null; lng?: number | null }) {
  const [data, setData] = useState<ServicingResponse | null>(null);

  useEffect(() => {
    if (typeof lat !== 'number' || typeof lng !== 'number') return;
    let cancelled = false;
    fetch('/api/servicing', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng }),
    })
      .then((r) => r.json())
      .then((j) => {
        if (!cancelled) setData(j);
      })
      .catch(() => {
        /* silent — a failed lookup renders nothing, never a false clear */
      });
    return () => {
      cancelled = true;
    };
  }, [lat, lng]);

  // Render nothing until we have a real answer (found or not-in-precinct).
  if (!data || data.status === 'failed') return null;

  const constrained = !!(data.ww?.constrained || data.dw?.constrained);
  const inPrecinct = data.status === 'found';

  const label = !inPrecinct ? 'Section 73' : constrained ? 'Constrained' : 'In growth area';
  const tone = !inPrecinct
    ? 'bg-white border-gray-100'
    : constrained
      ? 'bg-amber-50 border-amber-200'
      : 'bg-sky-50 border-sky-200';
  const labelTone = !inPrecinct
    ? 'text-gray-400'
    : constrained
      ? 'text-amber-800'
      : 'text-sky-800';

  const detail = !inPrecinct
    ? 'Not in a Sydney Water growth-servicing precinct — capacity for an established-area site is set via a Section 73 application, not the GSP.'
    : [productLine('Wastewater', data.ww), productLine('Drinking water', data.dw)]
        .filter(Boolean)
        .join('; ') +
      (constrained ? '. Capacity/timescale constraints noted.' : '.') +
      ' Trunk capacity is not service-readiness — feasibility and connection works still required.';

  return (
    <div className={`flex items-center justify-between rounded px-2 py-1.5 border ${tone}`} title={detail}>
      <div className="flex items-center gap-1.5 min-w-0">
        <Gauge className={`h-3 w-3 flex-shrink-0 ${inPrecinct ? (constrained ? 'text-amber-600' : 'text-sky-600') : 'text-gray-400'}`} />
        <span className="text-xs text-gray-700 truncate">Water/Sewer Servicing</span>
        <a
          href={GSP_URL}
          target="_blank"
          rel="noopener noreferrer"
          title="Source: Sydney Water Growth Servicing Plan"
          className="text-gray-300 hover:text-gray-500 flex-shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink className="h-2.5 w-2.5" />
        </a>
      </div>
      <span className={`text-xs font-semibold ml-1 flex-shrink-0 ${labelTone}`}>{label}</span>
    </div>
  );
}
