/**
 * useCdcSetbacks Hook
 *
 * Hook for checking proposed setbacks against the stored Housing Code
 * standards (server-side; no figure is typed here). A setback with no
 * applicable stored standard comes back as status 'not_checked'.
 *
 * prior-art-checked: rewrite of the existing hook; typed defaults and quickValidateSetback removed.
 */

import { useState, useCallback } from 'react';
import type { CdcCheck } from '@/lib/cdc/housing-code-checks';

export interface SetbackInput {
  front?: number;
  side?: number;
  side_left?: number;
  side_right?: number;
  rear?: number;
}

export type SetbackCheckResult = CdcCheck;

export interface CdcSetbackCheckResponse {
  success: boolean;
  /** true only if every setback passed; false if any failed; null if any was not checked. */
  overallCompliant: boolean | null;
  results: CdcCheck[];
  summary: string;
  disclaimer: string;
  meta?: {
    timestamp: string;
    standardsApplied: string;
    standardsError?: string | null;
  };
}

interface UseCdcSetbacksOptions {
  hasUpperFloorWindows?: boolean;
  lotAreaM2?: number | null;
  lotWidthM?: number | null;
  buildingHeightM?: number | null;
}

interface UseCdcSetbacksReturn {
  checkSetbacks: (setbacks: SetbackInput) => Promise<void>;
  result: CdcSetbackCheckResponse | null;
  isLoading: boolean;
  error: string | null;
  reset: () => void;
}

export function useCdcSetbacks(
  options: UseCdcSetbacksOptions = {}
): UseCdcSetbacksReturn {
  const [result, setResult] = useState<CdcSetbackCheckResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkSetbacks = useCallback(async (setbacks: SetbackInput) => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/cdc/setback-check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          setbacks,
          hasUpperFloorWindows: options.hasUpperFloorWindows ?? false,
          lotAreaM2: options.lotAreaM2 ?? null,
          lotWidthM: options.lotWidthM ?? null,
          buildingHeightM: options.buildingHeightM ?? null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Request failed: ${response.status}`);
      }

      const data = await response.json() as CdcSetbackCheckResponse;
      setResult(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to check setbacks';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [options.hasUpperFloorWindows, options.lotAreaM2, options.lotWidthM, options.buildingHeightM]);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    checkSetbacks,
    result,
    isLoading,
    error,
    reset
  };
}
