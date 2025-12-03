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

// TOD reduction thresholds
function getReduction(type: string, distance: number, frequency: string): number | null {
  if (type === 'heavy_rail') {
    if (distance <= 400) return 30;
    if (distance <= 800) return 20;
  } else if (type === 'light_rail') {
    if (distance <= 400) return 25;
    if (distance <= 600) return 15;
  } else if (type === 'bus' && distance <= 400) {
    if (frequency === 'high') return 15;
    if (frequency === 'medium') return 10;
  }
  return null;
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

  // Calculate max reduction
  const reductions = stops
    .map(s => getReduction(s.type, s.distance, s.frequency))
    .filter((r): r is number => r !== null);
  const maxReduction = reductions.length > 0 ? Math.max(...reductions) : 0;

  // Bonus for multiple transport types within range
  const typesWithReduction = new Set(
    stops
      .filter(s => getReduction(s.type, s.distance, s.frequency) !== null)
      .map(s => s.type)
  );
  const multiTransportBonus = typesWithReduction.size > 1 ? 10 : 0;
  const totalReduction = Math.min(maxReduction + multiTransportBonus, 50);

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-emerald-600" />
          <span className="text-sm font-medium text-gray-700">
            {stops.length} transport option{stops.length !== 1 ? 's' : ''} nearby
          </span>
        </div>
        {totalReduction > 0 && (
          <div className="px-2 py-1 bg-emerald-100 text-emerald-800 rounded text-xs font-medium">
            Up to {totalReduction}% parking reduction
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
                  const reduction = getReduction(stop.type, stop.distance, stop.frequency);
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
                        {reduction && (
                          <span className="text-emerald-600 font-medium">
                            -{reduction}%
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

      {/* Bonus note */}
      {multiTransportBonus > 0 && (
        <p className="text-xs text-emerald-600 italic">
          +10% bonus for multiple transport types
        </p>
      )}
    </div>
  );
}
