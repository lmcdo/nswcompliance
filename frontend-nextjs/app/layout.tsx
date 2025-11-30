// app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Script from 'next/script';
import { Analytics } from '@vercel/analytics/next';
import './globals.css';
import { FeatureFlagProvider } from '@/components/providers/FeatureFlagProvider';
import { FeatureFlagDebugPanel } from '@/components/debug/FeatureFlagDebugPanel';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
 title: 'NSW Planning Compliance Engine',
 description: 'Precision planning compliance analysis with intelligent reasoning',
 keywords: 'NSW planning, compliance, setbacks, development assessment, heritage, FSR',
 icons: {
 icon: '/favicon.ico',
 },
};

export const viewport = {
 width: 'device-width',
 initialScale: 1,
 themeColor: '#0d9488', // Teal-600
};

export default function RootLayout({
 children,
}: {
 children: React.ReactNode;
}) {
 return (
 <html lang="en">
 <body className={inter.className}>
 <FeatureFlagProvider>
 <div id="root">
 {children}
 </div>
 <div id="portal-root" />
 <FeatureFlagDebugPanel />
 </FeatureFlagProvider>
 <Analytics />
 
 {/* Google Maps API with optimized loading strategy */}
 <Script
 src="https://maps.googleapis.com/maps/api/js?key=AIzaSyCi5UBAg6X-k6W8v1vv9XEQaML9aQE-w60&libraries=places"
 strategy="afterInteractive"
 />

 {/* Autocomplete handled by PropertySearch component, not globally */}
 {/* <Script id="init-autocomplete" strategy="afterInteractive">
 {`
 function initAutocomplete() {
 console.log(' Attempting to initialize autocomplete...');
 const input = document.getElementById('header-address-search');

 if (input && window.google && window.google.maps && window.google.maps.places) {
 console.log(' Creating Google Maps autocomplete');

 try {
 const autocomplete = new window.google.maps.places.Autocomplete(input, {
 types: ['address'],
 componentRestrictions: { country: 'AU' },
 fields: ['formatted_address'],
 });

 autocomplete.addListener('place_changed', function() {
 const place = autocomplete.getPlace();
 console.log(' Place selected:', place?.formatted_address);

 if (place?.formatted_address) {
 // Update the input value
 input.value = place.formatted_address;

 // Trigger input change event so React picks up the change
 const changeEvent = new Event('input', { bubbles: true });
 input.dispatchEvent(changeEvent);

 // Trigger custom event for the PropertyCard to listen
 window.dispatchEvent(new CustomEvent('addressSelected', {
 detail: place.formatted_address
 }));

 console.log(' Dispatched events for address:', place.formatted_address);
 }
 });

 console.log(' Autocomplete created successfully!');
 } catch (error) {
 console.error(' Error creating autocomplete:', error);
 }
 } else {
 console.log('⏳ Google Maps not ready yet, retrying...');
 setTimeout(initAutocomplete, 500);
 }
 }

 // Start initialization after a short delay
 setTimeout(initAutocomplete, 1000);
 `}
 </Script> */}
 </body>
 </html>
 );
}