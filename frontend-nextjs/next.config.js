/** @type {import('next').NextConfig} */
const nextConfig = {
 experimental: {
 serverComponentsExternalPackages: ['better-sqlite3', 'isomorphic-dompurify']
 },
 // Rewrite /pdf-pages/* to Cloudflare R2 in production
 async redirects() {
   return [
     // Legacy domains → plotdetect.com.au
     {
       source: '/:path*',
       has: [{ type: 'host', value: 'www.canibuildit.com.au' }],
       destination: 'https://plotdetect.com.au/:path*',
       permanent: true,
     },
     {
       source: '/:path*',
       has: [{ type: 'host', value: 'canibuildit.com.au' }],
       destination: 'https://plotdetect.com.au/:path*',
       permanent: true,
     },
     {
       source: '/:path*',
       has: [{ type: 'host', value: 'whatcanibuildhere.com.au' }],
       destination: 'https://plotdetect.com.au/:path*',
       permanent: true,
     },
     // Clean distribution URLs — for builder emails, QR cards, social links
     // Note: /granny-flat is now the tool itself — no redirect needed
     { source: '/flood-risk', destination: '/reports/flood', permanent: false },
     { source: '/solar-yield', destination: '/reports/solar-yield', permanent: false },
     { source: '/shadow-check', destination: '/reports/shadow', permanent: false },
     { source: '/threat-radar', destination: '/reports/threat-radar', permanent: false },
     // /partner retired — embed program moved to /for/builders
     { source: '/partner', destination: '/for/builders', permanent: true },
   ];
 },
 async rewrites() {
   // Only rewrite to R2 in production (Vercel sets VERCEL=1)
   if (process.env.VERCEL === '1') {
     return [
       {
         source: '/pdf-pages/:path*',
         destination: 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/:path*',
       },
     ];
   }
   // In development, serve from local public folder (default behavior)
   return [];
 },
 reactStrictMode: process.env.NODE_ENV === 'production',
 swcMinify: process.env.NODE_ENV === 'production',
 // Strip all console.* except console.error in production builds (SWC compile-time transform)
 compiler: {
   ...(process.env.NODE_ENV === 'production' && {
     removeConsole: {
       exclude: ['error'],
     },
   }),
 },
 typescript: {
 ignoreBuildErrors: false
 },
 eslint: {
 ignoreDuringBuilds: false
 },
 webpack: (config, { dev, isServer }) => {
 // Disable file watching that causes zombie processes
 if (dev && !isServer) {
 config.watchOptions = {
 poll: false,
 ignored: /node_modules/
 };
 }
 if (isServer) {
 // Fix for better-sqlite3 in serverless environments
 config.externals.push('better-sqlite3');
 }
 return config;
 },
 images: {
 domains: ['maps.googleapis.com', 'pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev']
 },
 env: {
 NSW_PLANNING_API_BASE_URL: process.env.NSW_PLANNING_API_BASE_URL || 'https://api.apps1.nsw.gov.au/planning',
 GOOGLE_PLACES_API_KEY: process.env.GOOGLE_PLACES_API_KEY || '',
 DATABASE_PATH: process.env.DATABASE_PATH || '../nsw_planning.db'
 }
};

module.exports = nextConfig;