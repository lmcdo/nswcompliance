// hooks/useSetbackCalculation.ts
import { useState, useCallback } from 'react';
import type { 
  SetbackCalculationRequest, 
  SetbackResult, 
  BuildableAreaAnalysis,
  SetbackCalculationResponse 
} from '@/types/setback';

interface UseSetbackCalculationReturn {
  results: SetbackResult[];
  buildableArea: BuildableAreaAnalysis | null;
  calculating: boolean;
  error: string | null;
  calculateSetbacks: (request: SetbackCalculationRequest) => Promise<void>;
  clearResults: () => void;
}

export function useSetbackCalculation(): UseSetbackCalculationReturn {
  const [results, setResults] = useState<SetbackResult[]>([]);
  const [buildableArea, setBuildableArea] = useState<BuildableAreaAnalysis | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculateSetbacks = useCallback(async (request: SetbackCalculationRequest) => {
    setCalculating(true);
    setError(null);

    try {
      console.log('[Hook] Starting setback calculation for property:', request.property_id);

      const response = await fetch('/api/setbacks/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0'
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: SetbackCalculationResponse = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Setback calculation failed');
      }

      console.log(`[Hook] Setback calculation successful:`, {
        resultCount: data.setback_results.length,
        buildableArea: data.buildable_area_analysis.buildable_area,
        processingTime: data.processing_time_ms
      });

      setResults(data.setback_results);
      setBuildableArea(data.buildable_area_analysis);

    } catch (err) {
      console.error('[Hook] Setback calculation error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      
      // Clear results on error
      setResults([]);
      setBuildableArea(null);
    } finally {
      setCalculating(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setResults([]);
    setBuildableArea(null);
    setError(null);
    setCalculating(false);
  }, []);

  return {
    results,
    buildableArea,
    calculating,
    error,
    calculateSetbacks,
    clearResults
  };
}