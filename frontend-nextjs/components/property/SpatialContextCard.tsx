'use client';

import { ExternalLink } from 'lucide-react';
import type { SpatialContextState, AmenityData, AmenityCategory, StreetContextData } from '@/hooks/useSpatialContext';
import { useFeatureFlag } from '@/hooks/useFeatureFlag';

interface SpatialContextCardProps {
  state: SpatialContextState;
  onFetch: () => void;
  lat?: number | null;
  lng?: number | null;
}

const AMENITY_LABELS: Record<string, string> = {
  schools: 'Schools',
  transport: 'Transport',
  parks: 'Parks',
  shops: 'Shops',
  medical: 'Medical',
};

const AMENITY_ORDER = ['schools', 'transport', 'parks', 'shops', 'medical'] as const;

const HIERARCHY_BADGE: Record<string, string> = {
  local:      'bg-green-100 text-green-800',
  collector:  'bg-amber-100 text-amber-800',
  arterial:   'bg-red-100 text-red-700',
};

function formatWalk(m: number): string {
  if (m < 1000) return `${Math.round(m)}m`;
  return `${(m / 1000).toFixed(1)}km`;
}

function WalkabilityDots({ score }: { score: number }) {
  return (
    <span className="flex gap-1" aria-label={`Walkability ${score} of 5`}>
      {[1, 2, 3, 4, 5].map(i => (
        <span
          key={i}
          className={`inline-block w-2.5 h-2.5 rounded-full ${i <= score ? 'bg-teal-500' : 'bg-gray-200'}`}
        />
      ))}
    </span>
  );
}

function AmenityRow({ label, item }: { label: string; item: AmenityCategory | undefined }) {
  return (
    <div className="flex items-center justify-between text-xs py-1">
      <span className="text-stone-500 w-20 flex-shrink-0">{label}</span>
      {item ? (
        <span className="text-stone-700 text-right truncate max-w-[130px]">
          {item.name} <span className="text-stone-400">— {formatWalk(item.walking_m)}</span>
        </span>
      ) : (
        <span className="text-stone-300">—</span>
      )}
    </div>
  );
}

function StreetRow({ ctx }: { ctx: StreetContextData }) {
  const badgeCls = HIERARCHY_BADGE[ctx.street_hierarchy] ?? 'bg-gray-100 text-gray-600';
  const solar = ctx.solar_orientation?.lot_facing?.replace('_', '–') ?? null;
  return (
    <div className="flex items-center justify-between text-xs py-1 border-t border-stone-100 mt-1">
      <span className="text-stone-500 w-20 flex-shrink-0">Street</span>
      <span className="flex items-center gap-1.5 text-right">
        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${badgeCls}`}>
          {ctx.street_hierarchy}
        </span>
        {solar && <span className="text-stone-400">{solar}</span>}
      </span>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="animate-pulse space-y-2 py-1">
      <div className="flex gap-1">
        {[1,2,3,4,5].map(i => <div key={i} className="w-2.5 h-2.5 rounded-full bg-gray-200" />)}
      </div>
      {[1,2,3,4,5,6].map(i => (
        <div key={i} className="flex justify-between items-center py-0.5">
          <div className="h-3 bg-gray-200 rounded w-16" />
          <div className="h-3 bg-gray-200 rounded w-28" />
        </div>
      ))}
    </div>
  );
}

function LoadedCard({ amenity, streetContext }: { amenity: AmenityData | null; streetContext: StreetContextData | null }) {
  return (
    <div>
      {amenity && (
        <>
          <div className="flex items-center gap-2 mb-2">
            <WalkabilityDots score={amenity.walkability_score} />
            <span className="text-xs text-stone-500">{amenity.walkability_score_label}</span>
          </div>
          <div>
            {AMENITY_ORDER.map(key => (
              <AmenityRow key={key} label={AMENITY_LABELS[key]} item={amenity[key]} />
            ))}
          </div>
        </>
      )}
      {streetContext && <StreetRow ctx={streetContext} />}
      {!amenity && !streetContext && (
        <p className="text-xs text-stone-400">No spatial data available for this location.</p>
      )}
    </div>
  );
}

export function SpatialContextCard({ state, onFetch, lat, lng }: SpatialContextCardProps) {
  const cardEnabled = useFeatureFlag('spatial_context_card');
  if (!cardEnabled) return null;

  const osmUrl = lat && lng
    ? `https://www.openstreetmap.org/#map=17/${lat.toFixed(5)}/${lng.toFixed(5)}`
    : 'https://www.openstreetmap.org';

  return (
    <div className="bg-stone-50 border border-stone-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-medium text-stone-500 uppercase tracking-wide">Site Context</p>
        {state.status === 'success' && (
          <a
            href={osmUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-stone-400 hover:text-stone-600"
            title="Verify on OpenStreetMap"
          >
            OSM <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>

      <div className="min-h-[196px]">
        {(state.status === 'idle' || state.status === 'error') && (
          <div className="flex flex-col justify-between h-full">
            <p className="text-xs text-stone-500 mb-3">
              Walkability · Street type · Solar orientation
            </p>
            <button
              onClick={onFetch}
              className="w-full mt-2 px-3 py-2 text-sm font-medium text-teal-700 bg-teal-50 border border-teal-200 rounded hover:bg-teal-100 transition-colors"
            >
              Analyse location →
            </button>
          </div>
        )}
        {state.status === 'loading' && <SkeletonCard />}
        {state.status === 'success' && (
          <LoadedCard amenity={state.data.amenity} streetContext={state.data.street_context} />
        )}
      </div>
    </div>
  );
}
