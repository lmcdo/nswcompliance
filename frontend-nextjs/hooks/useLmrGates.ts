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

/** Which lot an answer belongs to. */
export function gatesKey(lat: number | undefined, lng: number | undefined): string | null {
  return lat == null || lng == null || !Number.isFinite(lat) || !Number.isFinite(lng) ? null : `${lat},${lng}`;
}

/**
 * The stored answer, but only if it belongs to the lot asked about. When the coordinates change, the
 * component renders once before the effect starts the new fetch; without this it would show the previous
 * lot's answer for the new lot during that render (Sol on #1352).
 */
export function gatesForKey(stored: UseLmrGatesResult & { key: string | null }, key: string | null): UseLmrGatesResult {
  if (key == null) return { gates: null, loading: false, failed: false };
  if (stored.key !== key) return { gates: null, loading: true, failed: false };
  return { gates: stored.gates, loading: stored.loading, failed: stored.failed };
}

/** Fetches the Low and Mid-Rise gates once per coordinate pair. On failure `gates` stays null. */
export function useLmrGates(coordinates: { lat: number; lng: number } | null): UseLmrGatesResult {
  const lat = coordinates?.lat;
  const lng = coordinates?.lng;
  const key = gatesKey(lat, lng);
  const [state, setState] = useState<UseLmrGatesResult & { key: string | null }>({
    gates: null, loading: false, failed: false, key: null,
  });

  useEffect(() => {
    if (key == null || lat == null || lng == null) {
      setState({ gates: null, loading: false, failed: false, key: null });
      return;
    }
    const controller = new AbortController();
    setState({ gates: null, loading: true, failed: false, key });
    fetch(`/api/housing-sepp/gates?lat=${encodeURIComponent(String(lat))}&lng=${encodeURIComponent(String(lng))}`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`gates ${res.status}`);
        return (await res.json()) as LmrGates;
      })
      .then((gates) => setState({ gates, loading: false, failed: false, key }))
      .catch((err) => {
        if (controller.signal.aborted) return;
        console.warn('[useLmrGates] gate check failed:', err);
        setState({ gates: null, loading: false, failed: true, key });
      });
    return () => controller.abort();
  }, [key, lat, lng]);

  return gatesForKey(state, key);
}
