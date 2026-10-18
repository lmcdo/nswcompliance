'use client';

import { useEffect, useState } from 'react';

// prior-art-checked: no existing hook calls /api/housing-sepp/gates (grep hooks/ components/, 2026-10-18).

/** Each answer is true / false, or null when the planning map query did not answer. */
export interface LmrGates {
  in_lmr_area: boolean | null;
  in_tod: boolean | null;
  near_town_centre: boolean | null;
  town_centre: string | null;
  lmr_excluded: boolean | null;
  dual_occ_prohibited: boolean | null;
  source: string;
}

export interface UseLmrGatesResult {
  gates: LmrGates | null;
  loading: boolean;
  failed: boolean;
}

/** Fetches the Low and Mid-Rise gates once per coordinate pair. On failure `gates` stays null. */
export function useLmrGates(coordinates: { lat: number; lng: number } | null): UseLmrGatesResult {
  const [state, setState] = useState<UseLmrGatesResult>({ gates: null, loading: false, failed: false });
  const lat = coordinates?.lat;
  const lng = coordinates?.lng;

  useEffect(() => {
    if (lat == null || lng == null || !Number.isFinite(lat) || !Number.isFinite(lng)) {
      setState({ gates: null, loading: false, failed: false });
      return;
    }
    const controller = new AbortController();
    setState({ gates: null, loading: true, failed: false });
    fetch(`/api/housing-sepp/gates?lat=${encodeURIComponent(String(lat))}&lng=${encodeURIComponent(String(lng))}`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`gates ${res.status}`);
        return (await res.json()) as LmrGates;
      })
      .then((gates) => setState({ gates, loading: false, failed: false }))
      .catch((err) => {
        if (controller.signal.aborted) return;
        console.warn('[useLmrGates] gate check failed:', err);
        setState({ gates: null, loading: false, failed: true });
      });
    return () => controller.abort();
  }, [lat, lng]);

  return state;
}
