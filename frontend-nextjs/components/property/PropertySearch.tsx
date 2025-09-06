// components/property/PropertySearch.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Search, MapPin, Loader2 } from 'lucide-react';

interface PropertySearchProps {
  onAddressSelect: (address: string, coordinates?: google.maps.LatLngLiteral) => void;
  loading?: boolean;
  selectedAddress?: string;
}

export function PropertySearch({ onAddressSelect, loading, selectedAddress }: PropertySearchProps) {
  const [inputValue, setInputValue] = useState(selectedAddress || '');
  const inputRef = useRef<HTMLInputElement>(null);
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);

  useEffect(() => {
    if (selectedAddress && selectedAddress !== inputValue) {
      setInputValue(selectedAddress);
    }
  }, [selectedAddress, inputValue]);

  useEffect(() => {
    // No custom styles - let Google Maps use default styling

    const initializeAutocomplete = () => {
      // Clear any existing autocomplete first
      if (autocompleteRef.current) {
        window.google?.maps.event.clearInstanceListeners(autocompleteRef.current);
        autocompleteRef.current = null;
      }
      
      if (window.google && window.google.maps && window.google.maps.places && inputRef.current) {
        autocompleteRef.current = new window.google.maps.places.Autocomplete(
          inputRef.current,
          {
            types: ['address'],
            componentRestrictions: { country: 'AU' },
            fields: ['formatted_address', 'geometry', 'address_components'],
            bounds: new window.google.maps.LatLngBounds(
              new window.google.maps.LatLng(-37.5, 140.9), // SW corner - NSW bounds like original
              new window.google.maps.LatLng(-28.1, 153.6)  // NE corner - NSW bounds like original  
            )
          }
        );

        
        autocompleteRef.current.addListener('place_changed', () => {
          const place = autocompleteRef.current?.getPlace();
          
          if (place?.formatted_address) {
            const address = place.formatted_address;
            const coordinates = place.geometry?.location ? {
              lat: place.geometry.location.lat(),
              lng: place.geometry.location.lng()
            } : undefined;

            setInputValue(address);
            
            // Check if address is in NSW (simple validation like original)
            const isNSW = address.includes('NSW') || 
                         place.address_components?.some(component =>
                           component.types.includes('administrative_area_level_1') &&
                           component.short_name === 'NSW'
                         );

            if (isNSW) {
              onAddressSelect(address, coordinates);
            } else {
              alert('Please select an address in NSW');
            }
          }
        });
      }
    };

    // Wait for Google Maps to load with timeout
    const checkGoogleMaps = () => {
      if (window.google && window.google.maps && window.google.maps.places) {
        initializeAutocomplete();
        return true;
      }
      return false;
    };
    
    // Try immediately first
    if (!checkGoogleMaps()) {
      // If not available, keep checking with a timeout
      let attempts = 0;
      const maxAttempts = 50; // 5 seconds max wait
      
      const interval = setInterval(() => {
        attempts++;
        if (checkGoogleMaps()) {
          clearInterval(interval);
        } else if (attempts >= maxAttempts) {
          console.warn('Google Maps failed to load after 5 seconds');
          clearInterval(interval);
        }
      }, 100);

      return () => {
        clearInterval(interval);
        if (autocompleteRef.current) {
          window.google?.maps.event.clearInstanceListeners(autocompleteRef.current);
        }
      };
    }

    return () => {
      if (autocompleteRef.current) {
        window.google?.maps.event.clearInstanceListeners(autocompleteRef.current);
      }
    };
  }, [onAddressSelect]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onAddressSelect(inputValue.trim());
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  return (
    <div className="w-full">
      <div className="mb-4">
        <h2 className="text-2xl font-semibold text-gray-900 mb-2 flex items-center gap-2">
          <MapPin className="h-6 w-6 text-blue-600" />
          Property Address
        </h2>
        <p className="text-gray-600 text-sm">
          Enter a NSW property address to begin compliance analysis
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3">
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            placeholder="e.g. 15 Norton Street, Leichhardt NSW 2040"
            className="flex h-14 w-full rounded-md border border-input bg-background px-3 py-1 text-lg shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 pr-10 min-w-[600px] max-w-[800px]"
            disabled={loading}
          />
          <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        </div>
        
        <Button 
          type="submit" 
          disabled={loading || !inputValue.trim()}
          className="min-w-[120px]"
        >
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing
            </>
          ) : (
            <>
              <Search className="mr-2 h-4 w-4" />
              Analyze
            </>
          )}
        </Button>
      </form>

      <div className="mt-3 text-xs text-gray-500">
        <p>
          ✓ NSW addresses only • ✓ Google Places integration • ✓ Real-time property lookup
        </p>
      </div>
    </div>
  );
}