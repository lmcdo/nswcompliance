'use client';

import { useState, useCallback } from 'react';
import { detectDevTypeFromZone } from '@/lib/requirement-prioritization';
import type {
  PropertyContext,
  LepCapacityData,
  SeppData,
  DcpData,
  RegulatoryLoadingProgress,
  LoadingState,
} from '@/types/regulatory';

interface LotDimensions {
  area: number;
  frontage: number;
  depth: number;
  confidence?: number;
}

interface PropertyApiResponse {
  success: boolean;
  data?: {
    address: string;
    propId?: number;
    gurasid?: number;
    propertyArea?: string;
    lotDimensions?: LotDimensions;
    constraints?: {
      zone?: string;
      zoneDescription?: string;
      lga?: string;
      formerCouncil?: string;
      precinctId?: string;
      maxHeight?: number;
      maxFsr?: number;
    };
    heritage?: {
      isHeritage?: boolean;
      heritageType?: string;
      hcaCode?: string;
    };
  };
  error?: string;
}

interface UseFullPropertyDataReturn {
  // Property context
  property: PropertyContext | null;
  developmentType: string;
  coordinates: google.maps.LatLngLiteral | null;

  // Regulatory data
  lepData: LepCapacityData | null;
  seppData: SeppData | null;
  dcpData: DcpData | null;

  // Loading states
  isLoading: boolean;
  isAllDataReady: boolean;
  loadingProgress: RegulatoryLoadingProgress;

  // Errors
  errors: {
    property: string | null;
    lep: string | null;
    sepp: string | null;
    dcp: string | null;
  };

  // Actions
  analyzeProperty: (address: string, coordinates?: google.maps.LatLngLiteral) => Promise<void>;
  setDevelopmentType: (devType: string) => void;
  clearData: () => void;
}

/**
 * Hook for fetching ALL regulatory data (Property, LEP, SEPP, DCP) in parallel.
 * Used by AI integration to have complete context immediately.
 *
 * Data flow:
 * 1. Fetch property first (needed for context)
 * 2. Parallel fetch LEP, SEPP, DCP using property context
 * 3. Track loading progress for each source
 */
export function useFullPropertyData(): UseFullPropertyDataReturn {
  // Property state
  const [property, setProperty] = useState<PropertyContext | null>(null);
  const [developmentType, setDevelopmentType] = useState('dwelling_house');
  const [coordinates, setCoordinates] = useState<google.maps.LatLngLiteral | null>(null);

  // Regulatory data
  const [lepData, setLepData] = useState<LepCapacityData | null>(null);
  const [seppData, setSeppData] = useState<SeppData | null>(null);
  const [dcpData, setDcpData] = useState<DcpData | null>(null);

  // Loading progress
  const [loadingProgress, setLoadingProgress] = useState<RegulatoryLoadingProgress>({
    property: 'pending',
    lep: 'pending',
    sepp: 'pending',
    dcp: 'pending',
  });

  // Errors
  const [errors, setErrors] = useState({
    property: null as string | null,
    lep: null as string | null,
    sepp: null as string | null,
    dcp: null as string | null,
  });

  // Helper to update loading state
  const updateLoading = useCallback((key: keyof RegulatoryLoadingProgress, state: LoadingState) => {
    setLoadingProgress(prev => ({ ...prev, [key]: state }));
  }, []);

  // Helper to update error state
  const updateError = useCallback((key: keyof typeof errors, error: string | null) => {
    setErrors(prev => ({ ...prev, [key]: error }));
  }, []);

  // Fetch LEP capacity data
  const fetchLepData = useCallback(async (
    propertyContext: PropertyContext,
    coords: google.maps.LatLngLiteral | null,
    devType: string
  ): Promise<LepCapacityData | null> => {
    try {
      updateLoading('lep', 'loading');
      updateError('lep', null);

      const response = await fetch('/api/capacity/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: propertyContext.address,
          coordinates: coords,
          developmentType: devType,
          lotArea: propertyContext.lotArea || 0,
          zone: propertyContext.zone,
          lga: propertyContext.lga,
          formerCouncil: propertyContext.formerCouncil,
        }),
      });

      if (!response.ok) {
        throw new Error(`LEP API error: ${response.status}`);
      }

      const data = await response.json();
      if (!data.success) {
        throw new Error(data.error || 'LEP data fetch failed');
      }

      updateLoading('lep', 'done');
      return data as LepCapacityData;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown LEP error';
      updateError('lep', message);
      updateLoading('lep', 'error');
      console.error('[useFullPropertyData] LEP fetch error:', error);
      return null;
    }
  }, [updateLoading, updateError]);

  // Fetch SEPP data
  const fetchSeppData = useCallback(async (
    zone: string,
    devType: string
  ): Promise<SeppData | null> => {
    try {
      updateLoading('sepp', 'loading');
      updateError('sepp', null);

      // Determine which SEPPs apply based on zone and dev type
      const seppIds = ['housing_2021']; // Primary SEPP for residential

      // Fetch structured requirements for primary SEPP
      const response = await fetch('/api/sepp/structured-requirements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          seppId: seppIds[0],
          developmentType: devType,
        }),
      });

      if (!response.ok) {
        throw new Error(`SEPP API error: ${response.status}`);
      }

      const data = await response.json();
      if (!data.success) {
        throw new Error(data.error || 'SEPP data fetch failed');
      }

      updateLoading('sepp', 'done');
      return data.data as SeppData;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown SEPP error';
      updateError('sepp', message);
      updateLoading('sepp', 'error');
      console.error('[useFullPropertyData] SEPP fetch error:', error);
      return null;
    }
  }, [updateLoading, updateError]);

  // Fetch DCP data
  const fetchDcpData = useCallback(async (
    propertyContext: PropertyContext
  ): Promise<DcpData | null> => {
    try {
      updateLoading('dcp', 'loading');
      updateError('dcp', null);

      const params = new URLSearchParams({
        lga: propertyContext.lga,
        zone: propertyContext.zone,
        heritage: String(propertyContext.heritage?.isHeritage || false),
        groupBy: 'toc',
      });

      if (propertyContext.formerCouncil) {
        params.set('former_council', propertyContext.formerCouncil);
      }
      if (propertyContext.precinctId) {
        params.set('precinct_id', propertyContext.precinctId);
      }
      if (propertyContext.heritage?.hcaCode) {
        params.set('hca', propertyContext.heritage.hcaCode);
      }

      const response = await fetch(`/api/provisions/for-property?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`DCP API error: ${response.status}`);
      }

      const data = await response.json();
      if (!data.success) {
        throw new Error(data.error || 'DCP data fetch failed');
      }

      updateLoading('dcp', 'done');
      return data.data as DcpData;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown DCP error';
      updateError('dcp', message);
      updateLoading('dcp', 'error');
      console.error('[useFullPropertyData] DCP fetch error:', error);
      return null;
    }
  }, [updateLoading, updateError]);

  // Main analyze function
  const analyzeProperty = useCallback(async (
    address: string,
    coords?: google.maps.LatLngLiteral
  ) => {
    console.log('[useFullPropertyData] Analyzing:', address);

    // Reset state
    setProperty(null);
    setLepData(null);
    setSeppData(null);
    setDcpData(null);
    setCoordinates(coords || null);
    setLoadingProgress({
      property: 'loading',
      lep: 'pending',
      sepp: 'pending',
      dcp: 'pending',
    });
    setErrors({
      property: null,
      lep: null,
      sepp: null,
      dcp: null,
    });

    try {
      // Step 1: Fetch property (needed for context)
      const propertyResponse = await fetch(`/api/property?address=${encodeURIComponent(address)}`);

      if (!propertyResponse.ok) {
        throw new Error(`Property API error: ${propertyResponse.status}`);
      }

      const propertyResult: PropertyApiResponse = await propertyResponse.json();

      if (!propertyResult.success || !propertyResult.data) {
        throw new Error(propertyResult.error || 'Property not found');
      }

      // Build property context - prefer cadastre-calculated area (legally authoritative)
      const lotArea = propertyResult.data.lotDimensions?.area
        ?? (propertyResult.data.propertyArea
          ? parseFloat(propertyResult.data.propertyArea.replace(/[^\d.]/g, ''))
          : undefined);

      const propertyContext: PropertyContext = {
        address: propertyResult.data.address,
        zone: propertyResult.data.constraints?.zone || '',
        lga: propertyResult.data.constraints?.lga || '',
        formerCouncil: propertyResult.data.constraints?.formerCouncil || '',
        precinctId: propertyResult.data.constraints?.precinctId,
        heritage: propertyResult.data.heritage ? {
          isHeritage: propertyResult.data.heritage.isHeritage || false,
          heritageType: propertyResult.data.heritage.heritageType,
          hcaCode: propertyResult.data.heritage.hcaCode,
        } : undefined,
        lotArea,
        coordinates: coords,
      };

      setProperty(propertyContext);
      updateLoading('property', 'done');

      // Auto-detect development type from zone
      const detectedDevType = detectDevTypeFromZone(propertyContext.zone);
      setDevelopmentType(detectedDevType);

      console.log('[useFullPropertyData] Property loaded:', {
        zone: propertyContext.zone,
        lga: propertyContext.lga,
        formerCouncil: propertyContext.formerCouncil,
        devType: detectedDevType,
      });

      // Step 2: Fetch LEP, SEPP, DCP in PARALLEL
      const [lepResult, seppResult, dcpResult] = await Promise.all([
        fetchLepData(propertyContext, coords || null, detectedDevType),
        fetchSeppData(propertyContext.zone, detectedDevType),
        fetchDcpData(propertyContext),
      ]);

      setLepData(lepResult);
      setSeppData(seppResult);
      setDcpData(dcpResult);

      console.log('[useFullPropertyData] All data loaded:', {
        hasLep: !!lepResult,
        hasSepp: !!seppResult,
        hasDcp: !!dcpResult,
        dcpProvisions: dcpResult?.summary?.total_provisions,
      });

    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      updateError('property', message);
      updateLoading('property', 'error');
      console.error('[useFullPropertyData] Property fetch error:', error);
    }
  }, [fetchLepData, fetchSeppData, fetchDcpData, updateLoading, updateError]);

  // Clear all data
  const clearData = useCallback(() => {
    setProperty(null);
    setLepData(null);
    setSeppData(null);
    setDcpData(null);
    setCoordinates(null);
    setDevelopmentType('dwelling_house');
    setLoadingProgress({
      property: 'pending',
      lep: 'pending',
      sepp: 'pending',
      dcp: 'pending',
    });
    setErrors({
      property: null,
      lep: null,
      sepp: null,
      dcp: null,
    });
  }, []);

  // Compute derived state
  const isLoading = Object.values(loadingProgress).some(s => s === 'loading');
  const isAllDataReady =
    loadingProgress.property === 'done' &&
    loadingProgress.lep === 'done' &&
    loadingProgress.sepp === 'done' &&
    loadingProgress.dcp === 'done';

  return {
    property,
    developmentType,
    coordinates,
    lepData,
    seppData,
    dcpData,
    isLoading,
    isAllDataReady,
    loadingProgress,
    errors,
    analyzeProperty,
    setDevelopmentType,
    clearData,
  };
}
