// components/property/PropertySearch.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Search, MapPin, Loader2, X } from 'lucide-react';
// Force recompile to apply address formatting fix

interface PropertySearchProps {
  onAddressSelect: (address: string, coordinates?: google.maps.LatLngLiteral) => void;
  loading?: boolean;
  selectedAddress?: string;
}

export function PropertySearch({ onAddressSelect, loading, selectedAddress }: PropertySearchProps) {
  const [inputValue, setInputValue] = useState('');
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
            bounds: new window.google.maps.LatLngBounds(
              new window.google.maps.LatLng(-37.5, 140.9), // SW corner - NSW bounds like original
              new window.google.maps.LatLng(-28.1, 153.6) // NE corner - NSW bounds like original
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

          if (place?.formatted_address) {
            let address = place.formatted_address;

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
              // Still allow the selection but warn the user
              onAddressSelect(address, coordinates);
              console.warn('Address may not be in NSW');
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
    if (inputValue.trim()) {
      // Allow manual entry - just pass the address through
      onAddressSelect(inputValue.trim());
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
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
          Type any NSW address or select from suggestions
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="flex gap-2 mb-4">
          <div className="relative flex-1">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={handleInputChange}
              placeholder="Start typing an address..."
              className="w-full h-10 px-3 pr-16 text-sm border border-gray-300 rounded-lg bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all disabled:bg-gray-50"
              disabled={loading}
            />
            {inputValue && (
              <button
                type="button"
                onClick={handleClearInput}
                className="absolute right-10 top-1/2 transform -translate-y-1/2 p-1 hover:bg-gray-100 rounded-full transition-colors"
                title="Clear search"
              >
                <X className="h-3 w-3 text-gray-400 hover:text-gray-600" />
              </button>
            )}
            <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          </div>

          <button
            type="submit"
            disabled={loading || !inputValue.trim()}
            className="h-10 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-lg transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed shadow-sm whitespace-nowrap"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              'Analyze Property'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}