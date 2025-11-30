// components/property/PropertySearch.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Search, MapPin, Loader2, X, AlertCircle } from 'lucide-react';

interface PropertySearchProps {
  onAddressSelect: (address: string, coordinates?: google.maps.LatLngLiteral) => void;
  loading?: boolean;
  selectedAddress?: string;
}

// Inner West LGA bounding box (approximate)
const INNER_WEST_BOUNDS = {
  south: -33.92,  // Southern boundary
  west: 151.12,   // Western boundary
  north: -33.85,  // Northern boundary
  east: 151.19    // Eastern boundary
};

export function PropertySearch({ onAddressSelect, loading, selectedAddress }: PropertySearchProps) {
  const [inputValue, setInputValue] = useState('');
  const [lgaError, setLgaError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);

  // Don't auto-fill from selectedAddress - let user control the input
  // useEffect(() => {
  // if (selectedAddress && selectedAddress !== inputValue) {
  // setInputValue(selectedAddress);
  // }
  // }, [selectedAddress, inputValue]);

  useEffect(() => {
    let dropdownObserver: MutationObserver | null = null;

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
            // Bias results toward Inner West LGA (but don't hard-restrict)
            bounds: new window.google.maps.LatLngBounds(
              new window.google.maps.LatLng(INNER_WEST_BOUNDS.south, INNER_WEST_BOUNDS.west),
              new window.google.maps.LatLng(INNER_WEST_BOUNDS.north, INNER_WEST_BOUNDS.east)
            )
          }
        );

        // Fix dropdown display: Add comma+space between street and suburb
        // Use MutationObserver to watch for Google's dropdown appearing
        dropdownObserver = new MutationObserver(() => {
          const pacContainer = document.querySelector('.pac-container');
          if (pacContainer) {
            const items = pacContainer.querySelectorAll('.pac-item');
            items.forEach((item) => {
              // Find the span with no class (contains suburb like "Leichhardt NSW, Australia")
              const spans = item.querySelectorAll('span');
              spans.forEach((span) => {
                if (!span.className && span.textContent) {
                  const text = span.textContent;
                  // Add comma+space before suburb: "Leichhardt NSW" becomes ", Leichhardt NSW"
                  // Only if it doesn't already have leading comma/space
                  if (text.trim() && !text.trim().startsWith(',') && text.match(/^[A-Z]/)) {
                    span.textContent = ', ' + text.trim();
                  }
                }
              });
            });
          }
        });

        // Observe the document body for dropdown appearing
        dropdownObserver.observe(document.body, {
          childList: true,
          subtree: true
        });

        autocompleteRef.current.addListener('place_changed', () => {
          const place = autocompleteRef.current?.getPlace();
          setLgaError(null); // Clear any previous error

          if (place?.formatted_address) {
            let address = place.formatted_address;

            const coordinates = place.geometry?.location ? {
              lat: place.geometry.location.lat(),
              lng: place.geometry.location.lng()
            } : undefined;

            setInputValue(address);

            // Check LGA from address_components
            const lgaComponent = place.address_components?.find(component =>
              component.types.includes('administrative_area_level_2')
            );
            const lga = lgaComponent?.long_name || '';

            // Validate: Only allow Inner West addresses
            const isInnerWest = lga.toLowerCase().includes('inner west');

            if (isInnerWest) {
              onAddressSelect(address, coordinates);
            } else {
              // Show error for non-Inner West addresses
              const lgaDisplay = lga || 'unknown area';
              setLgaError(`This address is in ${lgaDisplay}. Only Inner West LGA addresses are currently supported.`);
              console.warn(`Address rejected: ${address} is in ${lgaDisplay}, not Inner West`);
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
        if (dropdownObserver) {
          dropdownObserver.disconnect();
        }
      };
    }

    // Cleanup on unmount
    return () => {
      if (dropdownObserver) {
        dropdownObserver.disconnect();
      }
      if (autocompleteRef.current) {
        window.google?.maps.event.clearInstanceListeners(autocompleteRef.current);
      }
    };
  }, [onAddressSelect]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLgaError(null);
    if (inputValue.trim()) {
      // Allow manual entry - just pass the address through
      // Note: Manual entries bypass LGA validation (validated server-side)
      onAddressSelect(inputValue.trim());
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
    setLgaError(null); // Clear error when user types
  };

  const handleClearInput = (e?: React.MouseEvent) => {
    e?.preventDefault(); // Prevent form submission
    e?.stopPropagation(); // Stop event bubbling

    setInputValue('');
    if (inputRef.current) {
      inputRef.current.value = ''; // Also clear the actual input element value
      inputRef.current.focus();
    }
    // Clear any Google Places autocomplete selection
    if (autocompleteRef.current) {
      autocompleteRef.current.set('place', null);
    }
  };

  return (
    <div className="w-full">
      <div className="mb-6 text-center">
        <h2 className="text-xl font-semibold text-gray-800 mb-2">
          Property Address
        </h2>
        <p className="text-gray-600 text-sm">
          Enter an Inner West address to analyze
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="flex flex-col sm:flex-row gap-2 mb-4">
          <div className="relative flex-1">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={handleInputChange}
              placeholder="Start typing an address..."
              className="w-full h-12 sm:h-10 px-3 pr-16 text-base sm:text-sm border border-gray-300 rounded-lg bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all disabled:bg-gray-50"
              disabled={loading}
            />
            {inputValue && (
              <button
                type="button"
                onClick={handleClearInput}
                className="absolute right-10 top-1/2 transform -translate-y-1/2 p-2 hover:bg-gray-100 rounded-full transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center -mr-1"
                title="Clear search"
              >
                <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
              </button>
            )}
            <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          </div>

          <button
            type="submit"
            disabled={loading || !inputValue.trim()}
            className="h-12 sm:h-10 px-6 bg-teal-600 hover:bg-teal-700 active:bg-teal-800 text-white font-medium text-base sm:text-sm rounded-lg transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed shadow-sm whitespace-nowrap"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin inline" />
                Analyzing...
              </>
            ) : (
              'Analyze Property'
            )}
          </button>
        </div>
      </form>

      {/* LGA validation error message */}
      {lgaError && (
        <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-800 font-medium">Address not supported</p>
            <p className="text-sm text-amber-700">{lgaError}</p>
          </div>
        </div>
      )}
    </div>
  );
}