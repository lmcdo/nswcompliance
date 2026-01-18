/**
 * useCrossReferences Hook
 *
 * Fetches cross-references for a provision from the API.
 * Uses the existing /api/provisions/cross-references endpoint.
 */

import { useState, useEffect, useCallback } from 'react';

export interface CrossReference {
  id: number;
  referenceType: string;
  referenceNumber: string;
  referenceText: string;
  targetProvisionId: number | null;
  targetReference: string | null;
  targetText: string | null;
  resolutionStatus: 'resolved' | 'unresolved' | 'partial';
  resolutionConfidence: number;
  isMandatory: boolean;
  contextSnippet: string;
}

export interface CrossReferenceResult {
  provisionId: number;
  crossReferences: CrossReference[];
  totalCount: number;
  resolvedCount: number;
}

interface UseCrossReferencesOptions {
  /** Only fetch resolved references */
  resolvedOnly?: boolean;
  /** Filter by reference type (e.g., 'clause', 'part', 'schedule') */
  referenceType?: string;
  /** Whether to auto-fetch on mount */
  enabled?: boolean;
}

interface UseCrossReferencesReturn {
  /** The cross-references data */
  data: CrossReferenceResult | null;
  /** Loading state */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Manually trigger a refetch */
  refetch: () => Promise<void>;
}

export function useCrossReferences(
  provisionId: number | null,
  options: UseCrossReferencesOptions = {}
): UseCrossReferencesReturn {
  const { resolvedOnly = false, referenceType, enabled = true } = options;

  const [data, setData] = useState<CrossReferenceResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCrossReferences = useCallback(async () => {
    if (!provisionId || !enabled) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        provision_id: provisionId.toString(),
      });

      if (resolvedOnly) {
        params.append('resolved_only', 'true');
      }

      if (referenceType) {
        params.append('type', referenceType);
      }

      const response = await fetch(`/api/provisions/cross-references?${params}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch cross-references: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        setData(result.data);
      } else {
        throw new Error(result.error || 'Unknown error');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch cross-references';
      setError(message);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [provisionId, resolvedOnly, referenceType, enabled]);

  useEffect(() => {
    fetchCrossReferences();
  }, [fetchCrossReferences]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchCrossReferences,
  };
}

/**
 * Hook to batch-fetch cross-references for multiple provisions.
 * Useful when displaying a list of provisions with their cross-refs.
 */
export function useBatchCrossReferences(
  provisionIds: number[],
  options: UseCrossReferencesOptions = {}
): Record<number, CrossReferenceResult | null> {
  const [results, setResults] = useState<Record<number, CrossReferenceResult | null>>({});
  const { resolvedOnly = false, enabled = true } = options;

  useEffect(() => {
    if (!enabled || provisionIds.length === 0) {
      setResults({});
      return;
    }

    const fetchAll = async () => {
      const newResults: Record<number, CrossReferenceResult | null> = {};

      // Fetch in parallel with a concurrency limit
      const BATCH_SIZE = 5;
      for (let i = 0; i < provisionIds.length; i += BATCH_SIZE) {
        const batch = provisionIds.slice(i, i + BATCH_SIZE);
        const promises = batch.map(async (id) => {
          try {
            const params = new URLSearchParams({
              provision_id: id.toString(),
            });
            if (resolvedOnly) {
              params.append('resolved_only', 'true');
            }

            const response = await fetch(`/api/provisions/cross-references?${params}`);
            if (response.ok) {
              const result = await response.json();
              if (result.success) {
                return { id, data: result.data };
              }
            }
            return { id, data: null };
          } catch {
            return { id, data: null };
          }
        });

        const batchResults = await Promise.all(promises);
        batchResults.forEach(({ id, data }) => {
          newResults[id] = data;
        });
      }

      setResults(newResults);
    };

    fetchAll();
  }, [provisionIds.join(','), resolvedOnly, enabled]);

  return results;
}

export default useCrossReferences;
