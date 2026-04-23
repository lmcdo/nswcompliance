'use client';

import { useRef, useEffect, useState } from 'react';

// NSW bounding box (WGS84)
const NSW_BOUNDS = { north: -28.157, south: -37.505, east: 153.638, west: 141.002 };

interface AddressAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSelect: (address: string, lat: number, lng: number, postcode?: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function AddressAutocomplete({
  value,
  onChange,
  onSelect,
  placeholder = 'Enter a NSW property address...',
  disabled = false,
  className = '',
}: AddressAutocompleteProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);
  const [regionError, setRegionError] = useState('');

  // Stable refs so the autocomplete listener always calls the latest callbacks
  // without needing to re-init on every render
  const onChangeRef = useRef(onChange);
  const onSelectRef = useRef(onSelect);
  useEffect(() => { onChangeRef.current = onChange; });
  useEffect(() => { onSelectRef.current = onSelect; });

  // Clear region error when user starts typing again
  useEffect(() => { if (value) setRegionError(''); }, [value]);

  // Init once — no callback deps, refs handle freshness
  useEffect(() => {
    const init = () => {
      if (!window.google?.maps?.places || !inputRef.current) return false;

      const bounds = new window.google.maps.LatLngBounds(
        { lat: NSW_BOUNDS.south, lng: NSW_BOUNDS.west },
        { lat: NSW_BOUNDS.north, lng: NSW_BOUNDS.east }
      );

      autocompleteRef.current = new window.google.maps.places.Autocomplete(inputRef.current, {
        types: ['address'],
        componentRestrictions: { country: 'AU' },
        bounds,
        strictBounds: true,
        fields: ['formatted_address', 'geometry', 'address_components'],
      });

      autocompleteRef.current.addListener('place_changed', () => {
        const place = autocompleteRef.current?.getPlace();
        if (!place?.formatted_address || !place.geometry?.location) return;

        // Post-selection NSW validation — strictBounds is best-effort, not guaranteed
        const isNSW = place.address_components?.some(
          c => c.types.includes('administrative_area_level_1') && c.short_name === 'NSW'
        );
        if (!isNSW) {
          onChangeRef.current('');
          setRegionError('This tool covers NSW properties only. Please enter a NSW address.');
          return;
        }

        setRegionError('');
        const address = place.formatted_address;
        const lat = place.geometry.location.lat();
        const lng = place.geometry.location.lng();
        const postcode = place.address_components?.find(
          (c: google.maps.GeocoderAddressComponent) => c.types.includes('postal_code')
        )?.short_name;
        onChangeRef.current(address);
        onSelectRef.current(address, lat, lng, postcode);
      });

      return true;
    };

    if (!init()) {
      let attempts = 0;
      const interval = setInterval(() => {
        attempts++;
        if (init() || attempts >= 50) clearInterval(interval);
      }, 100);
      return () => clearInterval(interval);
    }

    return () => {
      if (autocompleteRef.current) {
        window.google?.maps.event.clearInstanceListeners(autocompleteRef.current);
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex-1 flex flex-col gap-1">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') e.preventDefault(); }}
        placeholder={placeholder}
        disabled={disabled}
        className={`w-full ${className.replace('flex-1', '').trim()}`}
        autoComplete="off"
      />
      {regionError && (
        <p className="text-xs text-red-600 px-1">{regionError}</p>
      )}
    </div>
  );
}
