/**
 * useCdcEligibility Hook
 *
 * Fetches CDC (Complying Development Certificate) preliminary eligibility
 * for a property address.
 */

import { useState, useEffect, useCallback } from 'react';

export interface CdcExclusion {
  reason: string;
  constraint: string;
  severity: 'definite' | 'likely';
  source: string;
}

export interface CdcCheckResult {
  eligible: 'yes' | 'no' | 'maybe';
  exclusions: CdcExclusion[];
  warnings: string[];
  checksPerformed: string[];
  disclaimer: string;
}

interface UseCdcEligibilityOptions {
  /** Whether to auto-fetch on mount */
  enabled?: boolean;
}

interface UseCdcEligibilityReturn {
  /** The CDC eligibility data */
  data: CdcCheckResult | null;
  /** Loading state */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Manually trigger a check */
  check: () => Promise<void>;
}

export function useCdcEligibility(
  address: string | null,
  options: UseCdcEligibilityOptions = {}
): UseCdcEligibilityReturn {
  const { enabled = true } = options;

  const [data, setData] = useState<CdcCheckResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const performCheck = useCallback(async () => {
    if (!address || !enabled) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/cdc/preliminary-check?address=${encodeURIComponent(address)}`
      );

      if (!response.ok) {
        throw new Error(`Failed to check CDC eligibility: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        setData(result.data);
      } else {
        throw new Error(result.error || 'Unknown error');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to check CDC eligibility';
      setError(message);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [address, enabled]);

  useEffect(() => {
    if (address && enabled) {
      performCheck();
    }
  }, [address, enabled, performCheck]);

  return {
    data,
    isLoading,
    error,
    check: performCheck,
  };
}

/**
 * Get a summary status label for CDC eligibility
 */
export function getCdcStatusLabel(eligible: 'yes' | 'no' | 'maybe' | undefined): string {
  switch (eligible) {
    case 'no':
      return 'CDC Excluded';
    case 'maybe':
      return 'Possibly Eligible';
    case 'yes':
      return 'Likely Eligible';
    default:
      return 'Unknown';
  }
}

/**
 * Get the primary exclusion reason (first definite exclusion)
 */
export function getPrimaryExclusion(exclusions: CdcExclusion[]): string | null {
  const definite = exclusions.find(e => e.severity === 'definite');
  return definite?.reason || null;
}

export default useCdcEligibility;
