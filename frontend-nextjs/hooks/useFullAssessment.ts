'use client';

/**
 * useFullAssessment Hook
 *
 * Fetches ALL assessment data through the consolidated BFF endpoint.
 * Provides progressive loading states for smooth UX:
 * - isLoadingProperty: Initial property fetch
 * - isLoadingDetails: Parallel fetch of capacity/SEPP/DCP
 * - isReady: All data loaded, AI Assistant can be enabled
 *
 * Uses the BFF pattern to prevent multiple simultaneous API calls.
 */

import { useState, useCallback, useRef } from 'react';
import { detectDevTypeFromZone } from '@/lib/requirement-prioritization';

// ============================================================================
// Types
// ============================================================================

export interface PropertyData {
  address: string;
  propertyArea?: string;
  lotDimensions?: {
    area: number;
    frontage: number;
    depth: number;
    confidence?: number;
  };
  constraints?: {
    zone?: string;
    zoneDescription?: string;
    lga?: string;
    formerCouncil?: string;
    precinctId?: string;
    todPrecinct?: any;
    acceleratedTOD?: any;
    hiaArea?: any;
  };
  heritage?: {
    isHeritage?: boolean;
    heritageType?: string;
    heritageItemName?: string;
    heritageItemNumber?: string;
  };
  planningLayers?: any[];
}

export interface CapacityData {
  maxHeight?: number;
  approxStoreys?: number;
  maxFSR?: number;
  maxGFA?: number;
  lotArea?: number;
  setbacks?: any;
  parking?: any[];
  landscaping?: any[];
  lepClauses?: any[];
}

export interface AssessmentData {
  property: PropertyData | null;
  capacity: CapacityData | null;
  sepp: any | null;
  dcp: any | null;
}

export interface LoadingState {
  isLoadingProperty: boolean;  // Phase 1: Property basics
  isLoadingDetails: boolean;   // Phase 2: Capacity, SEPP, DCP
  isReady: boolean;            // All done - AI can activate
}

export interface AssessmentErrors {
  property: string | null;
  capacity: string | null;
  sepp: string | null;
  dcp: string | null;
}

export interface TimingInfo {
  property: number;
  capacity: number;
  sepp: number;
  dcp: number;
  total: number;
}

export interface UseFullAssessmentReturn {
  // Data
  data: AssessmentData;
  developmentType: string;
  coordinates: { lat: number; lng: number } | null;

  // Loading states
  loading: LoadingState;
  isLoading: boolean;  // Convenience: any loading happening
  isReady: boolean;    // Convenience: all data ready

  // Errors
  errors: AssessmentErrors;
  hasErrors: boolean;

  // Timing (for debugging)
  timing: TimingInfo | null;

  // Actions
  loadAssessment: (address: string, coords?: { lat: number; lng: number }) => Promise<void>;
  setDevelopmentType: (devType: string) => void;
  reset: () => void;
}

// ============================================================================
// Initial state
// ============================================================================

const initialData: AssessmentData = {
  property: null,
  capacity: null,
  sepp: null,
  dcp: null,
};

const initialLoading: LoadingState = {
  isLoadingProperty: false,
  isLoadingDetails: false,
  isReady: false,
};

const initialErrors: AssessmentErrors = {
  property: null,
  capacity: null,
  sepp: null,
  dcp: null,
};

// ============================================================================
// Hook
// ============================================================================

export function useFullAssessment(): UseFullAssessmentReturn {
  const [data, setData] = useState<AssessmentData>(initialData);
  const [loading, setLoading] = useState<LoadingState>(initialLoading);
  const [errors, setErrors] = useState<AssessmentErrors>(initialErrors);
  const [timing, setTiming] = useState<TimingInfo | null>(null);
  const [developmentType, setDevelopmentType] = useState('dwelling_house');
  const [coordinates, setCoordinates] = useState<{ lat: number; lng: number } | null>(null);

  // Abort controller for cancelling in-flight requests
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Load full assessment data for an address
   */
  const loadAssessment = useCallback(async (
    address: string,
    coords?: { lat: number; lng: number }
  ) => {
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    // Reset state
    setData(initialData);
    setErrors(initialErrors);
    setTiming(null);
    setCoordinates(coords || null);

    // Start loading
    setLoading({
      isLoadingProperty: true,
      isLoadingDetails: false,
      isReady: false,
    });

    try {
      const response = await fetch('/api/assessment/full', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address,
          coordinates: coords,
          developmentType,
        }),
        signal: abortControllerRef.current.signal,
      });

      const result = await response.json();

      if (!result.success) {
        setErrors({
          property: result.error || 'Failed to load assessment',
          capacity: null,
          sepp: null,
          dcp: null,
        });
        setLoading({ isLoadingProperty: false, isLoadingDetails: false, isReady: false });
        return;
      }

      // Update data
      setData({
        property: result.data.property,
        capacity: result.data.capacity,
        sepp: result.data.sepp,
        dcp: result.data.dcp,
      });

      // Update errors if any
      if (result.errors) {
        setErrors({
          property: null,
          capacity: result.errors.capacity || null,
          sepp: result.errors.sepp || null,
          dcp: result.errors.dcp || null,
        });
      }

      // Update timing
      if (result.timing) {
        setTiming(result.timing);
      }

      // Auto-detect development type from zone
      const zone = result.data.property?.constraints?.zone;
      if (zone) {
        const detectedDevType = detectDevTypeFromZone(zone);
        setDevelopmentType(detectedDevType);
      }

      // All done
      setLoading({
        isLoadingProperty: false,
        isLoadingDetails: false,
        isReady: true,
      });

    } catch (error) {
      // Ignore abort errors
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }

      console.error('[useFullAssessment] Error:', error);
      setErrors({
        property: 'Failed to load assessment',
        capacity: null,
        sepp: null,
        dcp: null,
      });
      setLoading({ isLoadingProperty: false, isLoadingDetails: false, isReady: false });
    }
  }, [developmentType]);

  /**
   * Reset all state
   */
  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setData(initialData);
    setLoading(initialLoading);
    setErrors(initialErrors);
    setTiming(null);
    setCoordinates(null);
    setDevelopmentType('dwelling_house');
  }, []);

  // Convenience computed values
  const isLoading = loading.isLoadingProperty || loading.isLoadingDetails;
  const isReady = loading.isReady;
  const hasErrors = !!(errors.property || errors.capacity || errors.sepp || errors.dcp);

  return {
    data,
    developmentType,
    coordinates,
    loading,
    isLoading,
    isReady,
    errors,
    hasErrors,
    timing,
    loadAssessment,
    setDevelopmentType,
    reset,
  };
}

export default useFullAssessment;
