// TypeScript declarations for Google Maps API
declare global {
 interface Window {
 google: {
 maps: {
 places: {
 Autocomplete: new (
 input: HTMLInputElement,
 options?: {
 types?: string[];
 componentRestrictions?: { country: string };
 fields?: string[];
 }
 ) => {
 addListener: (event: string, callback: () => void) => void;
 getPlace: () => {
 formatted_address?: string;
 address_components?: any[];
 geometry?: any;
 };
 };
 };
 [key: string]: any;
 };
 };
 }
}

// API key will be injected at build time by Next.js for NEXT_PUBLIC_ variables
const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';

/**
 * Loads a script dynamically and returns a promise
 */
const loadScript = (src: string): Promise<void> => {
 return new Promise((resolve, reject) => {
 // For callback-based scripts, don't check for existing script with same src
 // since the callback parameter makes each URL unique
 const script = document.createElement('script');
 script.src = src;
 script.async = true;
 
 // For callback-based Google Maps API, we don't use onload 
 // since the callback will handle success
 if (src.includes('callback=')) {
 // Don't attach onload listener, callback will handle it
 script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
 } else {
 script.onload = () => resolve();
 script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
 }
 
 document.head.appendChild(script);
 
 // For callback URLs, resolve immediately after adding to head
 // The callback will handle the actual loading
 if (src.includes('callback=')) {
 resolve();
 }
 });
};

export const loadGoogleMapsAPI = async (): Promise<void> => {
 console.log('Loading Google Maps API with key:', GOOGLE_MAPS_API_KEY ? `${GOOGLE_MAPS_API_KEY.substring(0, 10)}...` : 'NOT SET');
 
 if (!GOOGLE_MAPS_API_KEY) {
 console.warn('Google Maps API key is not configured. Set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY environment variable.');
 throw new Error('Google Maps API key not configured');
 }
 
 return new Promise<void>((resolve, reject) => {
 if (typeof window !== 'undefined' && window.google && window.google.maps && window.google.maps.places) {
 console.log('Google Maps already loaded');
 resolve();
 return;
 }
 
 // Add a global callback function name
 const callbackName = 'initGoogleMaps';
 (window as any)[callbackName] = () => {
 console.log('Google Maps callback fired');
 // Add extra wait for places library
 const checkPlaces = () => {
 if (window.google && window.google.maps && window.google.maps.places) {
 console.log('Google Maps API fully loaded and ready');
 delete (window as any)[callbackName]; // cleanup
 resolve();
 } else {
 console.log('Waiting for places library...');
 setTimeout(checkPlaces, 50);
 }
 };
 checkPlaces();
 };
 
 const apiUrl = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places&callback=${callbackName}`;
 console.log('Loading Google Maps script with callback:', apiUrl);
 
 loadScript(apiUrl)
 .catch((err) => {
 console.error('Failed to load Google Maps script:', err);
 delete (window as any)[callbackName]; // cleanup on error
 reject(err);
 });
 
 // Add timeout as fallback
 setTimeout(() => {
 if (!(window.google && window.google.maps && window.google.maps.places)) {
 console.error('Google Maps API load timeout');
 delete (window as any)[callbackName]; // cleanup
 reject(new Error('Google Maps API load timeout'));
 }
 }, 10000); // 10 second timeout
 });
};