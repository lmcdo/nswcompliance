'use client';

import { useEffect, useState } from 'react';

// prior-art-checked: no existing hook calls /api/housing-sepp/area-check (grep hooks/ components/, 2026-11-07); modelled on hooks/useLmrGates.ts.

export type AreaAnswer = 'yes' | 'no' | 'borderline' | 'cant_tell';

export interface AreaFigures {
  limit_m?: number | null;
  walk_low_m?: number | null;
  walk_high_m?: number | null;
  anchor?: string | null;
  [k: string]: unknown;
}

export interface AreaRule { rule: string; clause: string; page: number; outcome: string; detail: string }

export interface AreaAnswerBlock {
  answer: AreaAnswer;
  reason_code?: string;
  clause?: string;
  page?: number;
  detail?: string;
  figures?: AreaFigures;
  share_of_range_inside?: number;
  heuristic?: string;
  rules?: AreaRule[];
  warnings?: { clause: string; page: number; detail: string }[];
  standards?: Record<string, { value: number | string; clause: string; page: number; law_version_date: string }>;
}

/** The area check's answer for one lot. Field names are the server's (services/lmr_area_decision.py). */
export interface AreaCheck {
  pathway: 'tod' | 'lmr' | 'borderline' | 'neither' | 'unknown';
  headline: string;
  lmr: AreaAnswerBlock;
  tod: AreaAnswerBlock;
  warnings: { clause: string; page: number; detail: string }[];
  not_checked: { para: string; what: string; clause: string; page: number }[];
  notes: string[];
  law_version_date: string | null;
}

const ANSWERS: readonly string[] = ['yes', 'no', 'borderline', 'cant_tell'];
const isBlock = (b: unknown): boolean => !!b && typeof b === 'object' && ANSWERS.includes((b as { answer?: unknown }).answer as string);

/** True only for a payload with every field the card and the flags read. A partial or mismatched payload is a failure, never an answer. */
export function isAreaCheck(x: unknown): x is AreaCheck {
  const r = x as Partial<AreaCheck> | null;
  return !!r && typeof r === 'object' && typeof r.headline === 'string' && isBlock(r.lmr) && isBlock(r.tod)
    && Array.isArray(r.warnings) && Array.isArray(r.not_checked) && Array.isArray(r.notes);
}

export interface UseAreaCheckResult {
  result: AreaCheck | null;
  loading: boolean;
  failed: boolean;
}

/** The two values the rest of the page already understands: true / false, or null when the area is not decided (never a guess). */
export function lmrFlags(result: AreaCheck | null): { inLmrArea: boolean | null; lmrExcluded: boolean | null } {
  if (!result || !result.lmr) return { inLmrArea: null, lmrExcluded: null };
  const a = result.lmr.answer;
  // A yes that still carries a warning has an exclusion the check could not rule out (flood extent, pipeline). The card shows the
  // warning beside the yes; every other panel gets null (not decided), the same as a borderline lot.
  const unresolved = (result.warnings?.length ?? 0) > 0 || (result.lmr.warnings?.length ?? 0) > 0;
  return {
    inLmrArea: a === 'yes' ? (unresolved ? null : true) : a === 'no' ? false : null,
    lmrExcluded: a === 'no' && result.lmr.reason_code === 'exclusion_map' ? true : null,
  };
}

export function areaKey(lat: number | undefined, lng: number | undefined): string | null {
  return lat == null || lng == null || !Number.isFinite(lat) || !Number.isFinite(lng) ? null : `${lat},${lng}`;
}

/** Fetches the area check once per coordinate pair. On failure `result` stays null and `failed` is true. */
export function useAreaCheck(coordinates: { lat: number; lng: number } | null): UseAreaCheckResult {
  const lat = coordinates?.lat;
  const lng = coordinates?.lng;
  const key = areaKey(lat, lng);
  const [state, setState] = useState<UseAreaCheckResult & { key: string | null }>({
    result: null, loading: false, failed: false, key: null,
  });

  useEffect(() => {
    if (key == null || lat == null || lng == null) {
      setState({ result: null, loading: false, failed: false, key: null });
      return;
    }
    const controller = new AbortController();
    setState({ result: null, loading: true, failed: false, key });
    fetch(`/api/housing-sepp/area-check?lat=${encodeURIComponent(String(lat))}&lng=${encodeURIComponent(String(lng))}`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`area-check ${res.status}`);
        const body: unknown = await res.json();
        if (!isAreaCheck(body)) throw new Error('area-check answer has the wrong shape');
        return body;
      })
      .then((result) => setState({ result, loading: false, failed: false, key }))
      .catch((err) => {
        if (controller.signal.aborted) return;
        console.warn('[useAreaCheck] area check failed:', err);
        setState({ result: null, loading: false, failed: true, key });
      });
    return () => controller.abort();
  }, [key, lat, lng]);

  // Never show the previous lot's answer for a new lot during the render before the new fetch starts.
  if (key == null) return { result: null, loading: false, failed: false };
  if (state.key !== key) return { result: null, loading: true, failed: false };
  return { result: state.result, loading: state.loading, failed: state.failed };
}
