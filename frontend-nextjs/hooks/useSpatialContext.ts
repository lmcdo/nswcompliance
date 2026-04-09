'use client';

import { useState, useCallback, useRef } from 'react';

export interface AmenityCategory {
  name: string;
  walking_m: number;
  crow_flies_m: number;
}

export interface AmenityData {
  parks?: AmenityCategory;
  shops?: AmenityCategory;
  schools?: AmenityCategory;
  transport?: AmenityCategory;
  medical?: AmenityCategory;
  walkability_score: number;
  walkability_score_label: string;
  radius_searched_m: number;
}

export interface StreetContextData {
  street_hierarchy: 'local' | 'collector' | 'arterial';
  street_name?: string;
  highway_type?: string;
  solar_orientation?: {
    street_bearing_deg: number;
    lot_facing: string;
    solar_access: 'good' | 'moderate' | 'poor';
    note: string;
  };
  multiple_frontages?: boolean;
  frontage_streets?: string[];
  data_confidence: 'high' | 'medium' | 'low';
  data_note?: string;
}

export interface SpatialBriefData {
  amenity: AmenityData | null;
  street_context: StreetContextData | null;
  amenity_source: 'cache' | 'live' | null;
  amenity_computed_at: string | null;
}

export type SpatialContextState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: SpatialBriefData }
  | { status: 'error' };

export interface UseSpatialContext {
  state: SpatialContextState;
  fetch: () => void;
  reset: () => void;
}

export function useSpatialContext(
  lat: number | null,
  lng: number | null,
  precinctId: string | null,
): UseSpatialContext {
  const [state, setState] = useState<SpatialContextState>({ status: 'idle' });
  // Ref-based loading guard — avoids stale closure when reading state inside callback.
  const loadingRef = useRef(false);

  const fetch = useCallback(async () => {
    if (!lat || !lng) return;
    if (loadingRef.current) return;

    loadingRef.current = true;
    setState({ status: 'loading' });
    try {
      const resp = await window.fetch('/api/spatial/brief', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lng, precinct_id: precinctId ?? undefined }),
      });
      if (!resp.ok) {
        setState({ status: 'error' });
        return;
      }
      const data: SpatialBriefData = await resp.json();
      setState({ status: 'success', data });
    } catch {
      setState({ status: 'error' });
    } finally {
      loadingRef.current = false;
    }
  }, [lat, lng, precinctId]);

  const reset = useCallback(() => {
    loadingRef.current = false;
    setState({ status: 'idle' });
  }, []);

  return { state, fetch, reset };
}
