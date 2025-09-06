// hooks/usePropertyData.ts
import { useState, useCallback } from 'react';
import type { PropertyData, LotGeometry } from '@/types/property';

interface UsePropertyDataReturn {
  property: PropertyData | null;
  lotGeometry: LotGeometry | null;
  loading: {
    property: boolean;
    setbacks: boolean;
    heritage: boolean;
    pathways: boolean;
  };
  error: {
    property: string | null;
    setbacks: string | null;
    heritage: string | null;
    pathways: string | null;
  };
  analyzeProperty: (address: string, coordinates?: google.maps.LatLngLiteral) => Promise<void>;
  clearData: () => void;
}

export function usePropertyData(): UsePropertyDataReturn {
  const [property, setProperty] = useState<PropertyData | null>(null);
  const [lotGeometry, setLotGeometry] = useState<LotGeometry | null>(null);
  
  const [loading, setLoading] = useState({
    property: false,
    setbacks: false,
    heritage: false,
    pathways: false
  });
  
  const [error, setError] = useState({
    property: null as string | null,
    setbacks: null as string | null,
    heritage: null as string | null,
    pathways: null as string | null
  });

  const updateLoading = useCallback((key: keyof typeof loading, value: boolean) => {
    setLoading(prev => ({ ...prev, [key]: value }));
  }, []);

  const updateError = useCallback((key: keyof typeof error, value: string | null) => {
    setError(prev => ({ ...prev, [key]: value }));
  }, []);

  const analyzeProperty = useCallback(async (
    address: string, 
    coordinates?: google.maps.LatLngLiteral
  ) => {
    updateLoading('property', true);
    updateError('property', null);

    try {
      console.log(`[Hook] Analyzing property: ${address}`);
      
      // Build URL with address as query parameter (matching working API structure)
      const params = new URLSearchParams({
        address: address
      });
      if (coordinates) {
        params.set('lat', coordinates.lat.toString());
        params.set('lng', coordinates.lng.toString());
      }
      const url = `/api/property?${params.toString()}`;

      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Property analysis failed');
      }

      // Transform API response to match expected frontend structure
      const transformedProperty = data.data ? {
        address: data.data.address,
        prop_id: data.data.propId,
        gurasid: data.data.gurasid,
        zone: data.data.constraints?.zone || null,
        height_limit: data.data.constraints?.maxHeight || null,
        height_units: 'm',
        fsr_limit: data.data.constraints?.maxFsr || null,
        heritage_status: data.data.heritage?.isHeritage ? 'Heritage' : undefined,
        lga_name: data.data.constraints?.lga || undefined,
        coordinates: coordinates
      } : null;

      console.log(`[Hook] Property analysis successful:`, {
        propId: transformedProperty?.prop_id,
        zone: transformedProperty?.zone,
        hasGeometry: !!data.lotGeometry
      });

      setProperty(transformedProperty);
      setLotGeometry(data.lotGeometry || null);

    } catch (error) {
      console.error('[Hook] Property analysis error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      updateError('property', errorMessage);
      
      // Clear data on error
      setProperty(null);
      setLotGeometry(null);
    } finally {
      updateLoading('property', false);
    }
  }, [updateLoading, updateError]);

  const clearData = useCallback(() => {
    setProperty(null);
    setLotGeometry(null);
    setLoading({
      property: false,
      setbacks: false,
      heritage: false,
      pathways: false
    });
    setError({
      property: null,
      setbacks: null,
      heritage: null,
      pathways: null
    });
  }, []);

  return {
    property,
    lotGeometry,
    loading,
    error,
    analyzeProperty,
    clearData
  };
}