// app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Script from 'next/script';
import { Analytics } from '@vercel/analytics/next';
import './globals.css';
import { FeatureFlagProvider } from '@/components/providers/FeatureFlagProvider';
import { FeatureFlagDebugPanel } from '@/components/debug/FeatureFlagDebugPanel';
import { PostHogProvider } from '@/components/providers/PostHogProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Can I Build It? — Free NSW Planning Tools',
  description: 'Nine NSW planning tools: planning controls assessment, granny flat eligibility, flood risk, solar yield, shadow analysis, nearby development radar, bushfire pre-screen, conveyancing disclosure, and pre-DA site history. Real answers from live Planning Portal data.',
  keywords: 'NSW planning, granny flat check, flood risk NSW, solar yield, secondary dwelling, SEPP Housing 2021, can I build a granny flat',
  icons: {
    icon: '/plotdetect-logo.png',
    apple: '/plotdetect-logo.png',
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
 <PostHogProvider>
 <FeatureFlagProvider>
 <div id="root">
 {children}
 </div>
 <div id="portal-root" />
 <FeatureFlagDebugPanel />
 </FeatureFlagProvider>
 </PostHogProvider>
 <Analytics />
 
 {/* Google Maps API with optimized loading strategy */}
 <Script
 src={`https://maps.googleapis.com/maps/api/js?key=${process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY}&libraries=places`}
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