'use client';

import { useState, useEffect, useCallback } from 'react';
import { flushSync } from 'react-dom';
import { detectDevTypeFromZone } from '@/lib/requirement-prioritization';

interface PropertyData {
  address: string;
  propertyArea?: string;
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
    heritageClause?: string;
    heritageSignificance?: string;
  };
  planningLayers?: any[];
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
    if (selectedProperty?.constraints?.zone) {
      const detectedDevType = detectDevTypeFromZone(selectedProperty.constraints.zone);
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

      const lotArea = selectedProperty.propertyArea
        ? parseFloat(selectedProperty.propertyArea.replace(/[^\d.]/g, ''))
        : null;
      if (!lotArea) return;

      try {
        const response = await fetch('/api/capacity/calculate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            address: selectedProperty.address,
            coordinates: selectedCoordinates,
            developmentType: developmentType,
            lotArea: lotArea,
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
    console.log('Address:', address);
    console.log('Coordinates:', coordinates);

    // Use flushSync to force immediate render of loading state
    flushSync(() => {
      setSelectedAddress(address);
      setSelectedCoordinates(coordinates || null);
      setLoading(true);
      setError(null);
    });

    // Track start time for minimum loading duration
    const startTime = Date.now();
    const MIN_LOADING_MS = 400; // Minimum loading time for UX feedback

    try {
      const url = `/api/property?address=${encodeURIComponent(address)}`;
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
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
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
