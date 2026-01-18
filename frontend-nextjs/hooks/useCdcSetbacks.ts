/**
 * useCdcSetbacks Hook
 *
 * Hook for checking proposed setbacks against SEPP Housing 2021 CDC standards.
 * Used in CDC eligibility flow to verify setback compliance.
 */

import { useState, useCallback } from 'react';

export interface SetbackInput {
  front?: number;
  side?: number;
  side_left?: number;
  side_right?: number;
  rear?: number;
}

export interface SetbackCheckResult {
  boundary: string;
  proposed: number;
  required: number;
  compliant: boolean;
  margin: number;
  reference: string;
  note?: string;
}

export interface CdcSetbackCheckResponse {
  success: boolean;
  overallCompliant: boolean;
  results: SetbackCheckResult[];
  summary: string;
  disclaimer: string;
  meta?: {
    timestamp: string;
    standardsApplied: string;
    note?: string;
  };
}

export interface CdcSetbackStandards {
  front: { minimum: number; description: string; reference: string };
  side: { minimum: number; description: string; reference: string };
  rear: { minimum: number; minimumUpperFloor: number; description: string; reference: string };
}

interface UseCdcSetbacksOptions {
  hasUpperFloorWindows?: boolean;
}

interface UseCdcSetbacksReturn {
  checkSetbacks: (setbacks: SetbackInput) => Promise<void>;
  result: CdcSetbackCheckResponse | null;
  standards: CdcSetbackStandards | null;
  isLoading: boolean;
  error: string | null;
  reset: () => void;
}

// Default SEPP Housing 2021 standards (used before API call)
const DEFAULT_STANDARDS: CdcSetbackStandards = {
  front: {
    minimum: 6.0,
    description: 'Front setback to street boundary',
    reference: 'SEPP Housing 2021, Clause 22(a)'
  },
  side: {
    minimum: 0.9,
    description: 'Side setback to side boundary',
    reference: 'SEPP Housing 2021, Clause 22(b)'
  },
  rear: {
    minimum: 3.0,
    minimumUpperFloor: 6.0,
    description: 'Rear setback to rear boundary',
    reference: 'SEPP Housing 2021, Clause 22(c)'
  }
};

export function useCdcSetbacks(
  options: UseCdcSetbacksOptions = {}
): UseCdcSetbacksReturn {
  const [result, setResult] = useState<CdcSetbackCheckResponse | null>(null);
  const [standards, setStandards] = useState<CdcSetbackStandards | null>(DEFAULT_STANDARDS);
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
          hasUpperFloorWindows: options.hasUpperFloorWindows ?? false
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
  }, [options.hasUpperFloorWindows]);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    checkSetbacks,
    result,
    standards,
    isLoading,
    error,
    reset
  };
}

/**
 * Quick validation function for use without API call
 * Useful for real-time form validation
 */
export function quickValidateSetback(
  boundary: 'front' | 'side' | 'rear',
  proposed: number,
  hasUpperFloorWindows: boolean = false
): { compliant: boolean; required: number; margin: number } {
  let required: number;

  switch (boundary) {
    case 'front':
      required = 6.0;
      break;
    case 'side':
      required = 0.9;
      break;
    case 'rear':
      required = hasUpperFloorWindows ? 6.0 : 3.0;
      break;
    default:
      required = 0;
  }

  return {
    compliant: proposed >= required,
    required,
    margin: Math.round((proposed - required) * 100) / 100
  };
}
