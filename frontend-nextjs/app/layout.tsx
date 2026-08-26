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
  // Apex, not www — the edge 307s www to the apex, so www-based canonicals
  // point at redirects and split indexing signals (found 2026-07-23).
  metadataBase: new URL('https://canibuildit.com.au'),
  title: {
    default: 'PlotDetect — NSW Property Intelligence',
    template: '%s | PlotDetect',
  },
  description: 'Property hazard checks, planning controls, climate risk scoring, and compliance verification for any NSW address. Flood depth, bushfire BAL, DCP provisions, and satellite analysis from live government data.',
  keywords: 'NSW property intelligence, flood risk NSW, bushfire BAL, climate risk, planning controls, DCP provisions, granny flat eligibility, property compliance',
  icons: {
    icon: '/plotdetect-logo.png',
    apple: '/plotdetect-logo.png',
  },
  openGraph: {
    type: 'website',
    siteName: 'PlotDetect',
    locale: 'en_AU',
    images: [{ url: '/plotdetect-logo.png', width: 512, height: 512, alt: 'PlotDetect' }],
  },
  twitter: {
    card: 'summary',
  },
  alternates: {
    // Self-referencing canonical on every page, resolved against metadataBase.
    // The same build serves 5+ hostnames (apex, www, verify/brief/conveyance
    // subdomains) — without this, engines see duplicates with no owner.
    canonical: './',
    types: {
      'application/rss+xml': '/blog/feed.xml',
    },
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
 <script
   type="application/ld+json"
   dangerouslySetInnerHTML={{
     __html: JSON.stringify({
       '@context': 'https://schema.org',
       '@type': 'Organization',
       name: 'PlotDetect',
       url: 'https://plotdetect.com.au',
       logo: 'https://verify.plotdetect.com.au/plotdetect-logo.png',
       description: 'NSW property intelligence platform. Planning controls, flood risk, bushfire screening, climate risk, and compliance verification from live government data.',
       areaServed: {
         '@type': 'State',
         name: 'New South Wales',
         containedInPlace: { '@type': 'Country', name: 'Australia' },
       },
     }),
   }}
 />
 <script
   type="application/ld+json"
   dangerouslySetInnerHTML={{
     __html: JSON.stringify({
       '@context': 'https://schema.org',
       '@type': 'WebSite',
       name: 'PlotDetect',
       url: 'https://plotdetect.com.au',
       potentialAction: {
         '@type': 'SearchAction',
         target: {
           '@type': 'EntryPoint',
           urlTemplate: 'https://verify.plotdetect.com.au/reports/flood?address={search_term_string}',
         },
         'query-input': 'required name=search_term_string',
       },
     }),
   }}
 />
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