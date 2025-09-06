import { setSelectedCoordinates } from './property-service.js';

let autocompleteInitialized = false;

// Initialize Google Places Autocomplete
export function initializeAutocomplete() {
    if (autocompleteInitialized || !window.google) {
        console.log('Autocomplete already initialized or Google Maps not loaded');
        return;
    }

    try {
        const addressInput = document.getElementById('address');
        if (!addressInput) {
            console.error('Address input element not found');
            return;
        }

        // Configure autocomplete for Australian addresses with bias towards NSW
        const autocomplete = new google.maps.places.Autocomplete(addressInput, {
            types: ['address'],
            componentRestrictions: { country: 'AU' },
            fields: ['formatted_address', 'geometry', 'address_components', 'place_id']
        });

        // Bias results towards NSW (around Sydney)
        const nswBounds = new google.maps.LatLngBounds(
            new google.maps.LatLng(-37.5, 140.9), // SW corner of NSW
            new google.maps.LatLng(-28.1, 153.6)  // NE corner of NSW
        );
        autocomplete.setBounds(nswBounds);

        // Handle place selection
        autocomplete.addListener('place_changed', function() {
            const place = autocomplete.getPlace();
            console.log('Google Places selected:', place);

            if (!place.geometry) {
                console.error('Place has no geometry');
                return;
            }

            // Extract coordinates
            const location = place.geometry.location;
            const coordinates = {
                lat: location.lat(),
                lng: location.lng()
            };
            
            console.log('Selected coordinates:', coordinates);
            setSelectedCoordinates(coordinates);

            // Store place info globally for property analysis
            window.selectedPlaceInfo = {
                originalAddress: place.formatted_address,
                placeId: place.place_id,
                coordinates: coordinates,
                addressComponents: place.address_components
            };

            console.log('Stored place info:', window.selectedPlaceInfo);
        });

        autocompleteInitialized = true;
        console.log('Google Places Autocomplete initialized successfully');

    } catch (error) {
        console.error('Error initializing autocomplete:', error);
    }
}

// Load Google Maps API
export function loadGoogleMapsAPI() {
    // Use the correct API key from .env.local
    const apiKey = 'AIzaSyCi5UBAg6X-k6W8v1vv9XEQaML9aQE-w60';
    
    if (!apiKey) {
        console.log('Google Maps API key not configured - using basic address input');
        enableBasicAddressInput();
        return;
    }

    // Check if already loaded
    if (window.google && window.google.maps) {
        console.log('Google Maps API already loaded');
        initializeAutocomplete();
        return;
    }

    // Check if script is already being loaded
    if (document.querySelector('script[src*="maps.googleapis.com"]')) {
        console.log('Google Maps API script already loading');
        return;
    }

    // Create script element
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
    script.async = true;
    script.defer = true;

    // Handle script load
    script.onload = function() {
        console.log('Google Maps API loaded successfully');
        initializeAutocomplete();
    };

    script.onerror = function() {
        console.error('Failed to load Google Maps API - falling back to basic input');
        enableBasicAddressInput();
    };

    // Add to document
    document.head.appendChild(script);
}

// Fallback for when Google Maps isn't available
function enableBasicAddressInput() {
    const addressInput = document.getElementById('address');
    if (addressInput) {
        addressInput.placeholder = 'Enter property address (e.g., 123 Main St, Sydney NSW 2000)';
        console.log('Address input enabled without autocomplete');
    }
}