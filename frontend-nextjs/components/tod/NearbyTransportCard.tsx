'use client';

/**
 * Nearby Transport Card
 * Auto-detects and displays transport options near a property
 * Shows distances and applicable TOD parking reductions
 */

import { useState, useEffect } from 'react';
import { Train, TrainFront, Bus, Ship, MapPin, AlertCircle } from 'lucide-react';

interface TransportStop {
  id: string;
  name: string;
  type: 'heavy_rail' | 'light_rail' | 'bus' | 'ferry';
  distance: number;
  frequency: 'high' | 'medium' | 'low';
}

interface NearbyTransportCardProps {
  lat?: number;
  lng?: number;
  preloadedStops?: TransportStop[];
  loading?: boolean;
  onTransportLoaded?: (stops: TransportStop[]) => void;
}

// Icon mapping for transport types
const transportIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  heavy_rail: Train,
  light_rail: TrainFront,
  bus: Bus,
  ferry: Ship,
};

// Friendly names for transport types
const transportLabels: Record<string, string> = {
  heavy_rail: 'Train',
  light_rail: 'Light Rail',
  bus: 'Bus',
  ferry: 'Ferry',
};

// Check if transport qualifies for TOD consideration (within regulatory thresholds)
// Parking reduction rates must be verified with council DCP
function qualifiesForTOD(type: string, distance: number, frequency: string): boolean {
  if (type === 'heavy_rail' && distance <= 800) return true;
  if (type === 'light_rail' && distance <= 600) return true;
  if (type === 'bus' && distance <= 400 && (frequency === 'high' || frequency === 'medium')) return true;
  return false;
}

export function NearbyTransportCard({
  lat,
  lng,
  preloadedStops,
  loading: externalLoading,
  onTransportLoaded
}: NearbyTransportCardProps) {
  const [internalStops, setInternalStops] = useState<TransportStop[]>([]);
  const [internalLoading, setInternalLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use preloaded stops if provided, otherwise fetch
  const stops = preloadedStops ?? internalStops;
  const loading = externalLoading ?? internalLoading;

  useEffect(() => {
    // Skip fetching if preloaded stops are provided
    if (preloadedStops !== undefined) {
      return;
    }

    if (!lat || !lng) {
      setInternalStops([]);
      return;
    }

    const fetchTransport = async () => {
      setInternalLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `/api/tod/transport-autocomplete?lat=${lat}&lng=${lng}&limit=15`
        );
        if (!response.ok) {
          throw new Error('Failed to fetch transport data');
        }
        const data = await response.json();

        // Filter to only include stops within 1km
        const nearbyStops = (data.suggestions || [])
          .filter((s: TransportStop) => s.distance <= 1000)
          .slice(0, 10);

        setInternalStops(nearbyStops);
        onTransportLoaded?.(nearbyStops);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load transport');
        setInternalStops([]);
      } finally {
        setInternalLoading(false);
      }
    };

    fetchTransport();
  }, [lat, lng, preloadedStops, onTransportLoaded]);

  // No coordinates provided
  if (!lat || !lng) {
    return (
      <div className="text-xs text-gray-500 italic">
        Select a property to view nearby transport
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-2">
        <div className="animate-pulse h-4 bg-emerald-200 rounded w-3/4"></div>
        <div className="animate-pulse h-4 bg-emerald-200 rounded w-1/2"></div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-red-600">
        <AlertCircle className="w-4 h-4" />
        {error}
      </div>
    );
  }

  // No nearby transport
  if (stops.length === 0) {
    return (
      <div className="text-xs text-gray-500 italic">
        No public transport within 1km of this property
      </div>
    );
  }

  // Group stops by type
  const groupedStops = stops.reduce((acc, stop) => {
    if (!acc[stop.type]) acc[stop.type] = [];
    acc[stop.type].push(stop);
    return acc;
  }, {} as Record<string, TransportStop[]>);

  // Note: Actual parking reduction rates come from council DCP provisions
  // See DCP Provisions tab for council-specific TOD parking requirements

  // Check if any transport qualifies for TOD
  const qualifyingCount = stops.filter(stop =>
    qualifiesForTOD(stop.type, stop.distance, stop.frequency)
  ).length;
  const hasQualifyingTransport = qualifyingCount > 0;
  const nonQualifyingCount = stops.length - qualifyingCount;

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-emerald-600" />
          <span className="text-sm font-medium text-gray-700">
            {hasQualifyingTransport
              ? <>
                  {qualifyingCount} within TOD threshold
                  {nonQualifyingCount > 0 && <span className="font-normal text-gray-500"> · {nonQualifyingCount} other nearby</span>}
                </>
              : <>{stops.length} transport option{stops.length !== 1 ? 's' : ''} nearby</>
            }
          </span>
        </div>
        {hasQualifyingTransport && (
          <div className="px-2 py-1 bg-emerald-100 text-emerald-800 rounded text-xs font-medium">
            TOD eligible
          </div>
        )}
      </div>

      {/* Grouped Transport List */}
      <div className="space-y-2">
        {Object.entries(groupedStops).map(([type, typeStops]) => {
          const Icon = transportIcons[type] || Train;
          const label = transportLabels[type] || type;

          return (
            <div key={type} className="border-l-2 border-emerald-200 pl-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Icon className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-xs font-medium text-gray-600">{label}</span>
              </div>
              <div className="space-y-1">
                {typeStops.slice(0, 3).map((stop) => {
                  const qualifies = qualifiesForTOD(stop.type, stop.distance, stop.frequency);
                  return (
                    <div
                      key={stop.id}
                      className="flex items-center justify-between text-xs"
                    >
                      <span className="text-gray-700 truncate pr-2">
                        {stop.name.replace(' Station', '').replace(' Light Rail', '')}
                      </span>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="text-gray-500">{stop.distance}m</span>
                        {qualifies && (
                          <span className="text-emerald-600 font-medium text-[10px]">
                            TOD
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
                {typeStops.length > 3 && (
                  <span className="text-xs text-gray-400">
                    +{typeStops.length - 3} more
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* DCP Reference Note */}
      {hasQualifyingTransport && (
        <p className="text-xs text-gray-500 italic">
          Refer to council DCP for parking reduction rates
        </p>
      )}
    </div>
  );
}
