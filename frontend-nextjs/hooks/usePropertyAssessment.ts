'use client';

import { useState, useEffect, useCallback } from 'react';
import { detectDevTypeFromZone } from '@/lib/requirement-prioritization';

interface LotDimensions {
  area: number;
  frontage: number;
  depth: number;
  confidence: number;
  notes?: string[];
}

interface PropertyData {
  address: string;
  propertyArea?: string;
  constraints?: {
    zone?: string;
    zoneDescription?: string;
    lga?: string;
    formerCouncil?: string;
    precinctId?: string;
    precinctName?: string;
    todPrecinct?: any;
    acceleratedTOD?: any;
    hiaArea?: any;
  };
  heritage?: {
    isHeritage?: boolean;
    heritageType?: string;
    heritageItemName?: string;
    heritageItemNumber?: string;
    heritageClause?: string;
    heritageSignificance?: string;
  };
  planningLayers?: any[];
  lotDimensions?: LotDimensions;
  strataInfo?: {
    isStrata: boolean;
    source: string | null;
    strataUnit: string | null;
  };
}

interface UsePropertyAssessmentReturn {
  // Property state
  selectedAddress: string;
  selectedProperty: PropertyData | null;
  selectedCoordinates: google.maps.LatLngLiteral | null;
  loading: boolean;
  error: string | null;

  // Derived data
  lepClauseData: any;
  developmentType: string;

  // Actions
  handleAddressSelect: (address: string, coordinates?: google.maps.LatLngLiteral) => Promise<void>;
  setDevelopmentType: (devType: string) => void;
}

/**
 * Normalize address format for consistent API calls across platforms.
 * Google Places Autocomplete can return different formats on Windows vs Mac.
 */
function normalizeAddress(address: string): string {
  if (!address) return '';

  return address
    // Normalize whitespace (handles different platform line endings and multiple spaces)
    .replace(/\s+/g, ' ')
    // Remove trailing ", Australia" if present (NSW Portal doesn't need it)
    .replace(/,?\s*Australia$/i, '')
    // Normalize comma spacing
    .replace(/\s*,\s*/g, ', ')
    // Trim
    .trim();
}

/**
 * Hook for managing property assessment data fetching and state.
 * Handles address selection, property lookup, and LEP clause fetching.
 */
export function usePropertyAssessment(): UsePropertyAssessmentReturn {
  const [selectedAddress, setSelectedAddress] = useState('');
  const [selectedProperty, setSelectedProperty] = useState<PropertyData | null>(null);
  const [selectedCoordinates, setSelectedCoordinates] = useState<google.maps.LatLngLiteral | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [developmentType, setDevelopmentType] = useState('dwelling_house');
  const [lepClauseData, setLepClauseData] = useState<any>(null);

  // Auto-detect development type from zone when property loads
  useEffect(() => {
    const zone = selectedProperty?.constraints?.zone;
    console.log('🏠 Zone detection - zone:', zone);
    if (zone) {
      const detectedDevType = detectDevTypeFromZone(zone);
      console.log('🏠 Zone detection - detectedDevType:', detectedDevType);
      setDevelopmentType(detectedDevType);
    }
  }, [selectedProperty?.constraints?.zone]);

  // Fetch LEP clause data when property or dev type changes
  useEffect(() => {
    async function fetchLepClauses() {
      if (!selectedProperty) {
        setLepClauseData(null);
        return;
      }

      // Prefer cadastre-calculated area (legally authoritative)
      const lotArea = selectedProperty.lotDimensions?.area
        ?? (selectedProperty.propertyArea
          ? parseFloat(selectedProperty.propertyArea.replace(/[^\d.]/g, ''))
          : null);
      if (!lotArea) return;

      try {
        const estimatedFrontage = Math.sqrt(lotArea);
        const response = await fetch('/api/capacity/calculate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            address: selectedProperty.address,
            coordinates: selectedCoordinates,
            lotSize: lotArea,  // API expects 'lotSize', not 'lotArea'
            frontage: estimatedFrontage,  // Required by API
            zone: selectedProperty.constraints?.zone || '',
            lga: selectedProperty.constraints?.lga || '',
            formerCouncil: selectedProperty.constraints?.formerCouncil || ''
          })
        });

        if (response.ok) {
          const data = await response.json();
          setLepClauseData(data);
        }
      } catch (error) {
        console.error('Failed to fetch LEP clause data:', error);
      }
    }

    fetchLepClauses();
  }, [selectedProperty, developmentType, selectedCoordinates]);

  // Handle address selection and property fetch
  const handleAddressSelect = useCallback(async (
    address: string,
    coordinates?: google.maps.LatLngLiteral
  ) => {
    console.log('=== handleAddressSelect CALLED ===');
    console.log('Address (raw):', address);

    // Normalize address for consistent API calls across platforms
    const normalizedAddress = normalizeAddress(address);
    console.log('Address (normalized):', normalizedAddress);
    console.log('Coordinates:', coordinates);

    // Note: no flushSync here — React 18 auto-batches these inside async functions.
    // flushSync caused an 844ms synchronous blocking render (INP regression) when
    // ProvisionsByTocStructure was mounted with a large provision set.
    setSelectedAddress(normalizedAddress);
    setSelectedCoordinates(coordinates || null);
    setLoading(true);
    setError(null);

    // Track start time for minimum loading duration
    const startTime = Date.now();
    const MIN_LOADING_MS = 400; // Minimum loading time for UX feedback

    try {
      const url = `/api/property?address=${encodeURIComponent(normalizedAddress)}`;
      console.log('Fetching:', url);

      const response = await fetch(url);
      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);

      if (response.ok) {
        const apiResponse = await response.json();
        console.log('API Response:', apiResponse);

        if (apiResponse.success) {
          console.log('✅ Success! Property data:', apiResponse.data);
          setSelectedProperty(apiResponse.data);
        } else {
          console.error('❌ API returned error:', apiResponse.error);
          throw new Error(apiResponse.error || 'Failed to load property');
        }
      } else {
        const errorText = await response.text();
        console.error('❌ HTTP Error:', response.status, errorText);
        // Show the server's own message (e.g. the 404 naming the address that was not found).
        let serverMessage: string | null = null;
        try {
          const body = JSON.parse(errorText);
          serverMessage = typeof body?.error === 'string' ? body.error : null;
        } catch {
          serverMessage = null;
        }
        throw new Error(serverMessage ?? `HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      console.error('❌ Fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load property');
      setSelectedProperty(null);
    } finally {
      // Ensure minimum loading time for visible feedback
      const elapsed = Date.now() - startTime;
      if (elapsed < MIN_LOADING_MS) {
        await new Promise(resolve => setTimeout(resolve, MIN_LOADING_MS - elapsed));
      }
      setLoading(false);
      console.log('=== handleAddressSelect COMPLETE ===');
    }
  }, []);

  return {
    selectedAddress,
    selectedProperty,
    selectedCoordinates,
    loading,
    error,
    lepClauseData,
    developmentType,
    handleAddressSelect,
    setDevelopmentType,
  };
}
