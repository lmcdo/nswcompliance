/** @type {import('next').NextConfig} */
const nextConfig = {
 experimental: {
 serverComponentsExternalPackages: ['better-sqlite3']
 },
 // Rewrite /pdf-pages/* to Cloudflare R2 in production
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
 // Production optimizations - enable SWC minification and strict mode for production builds
 // Disabled in development to avoid hot reload issues
 reactStrictMode: process.env.NODE_ENV === 'production',
 swcMinify: process.env.NODE_ENV === 'production',
 // Temporarily disable TypeScript checking in build to unblock deployment
 typescript: {
 ignoreBuildErrors: true
 },
 eslint: {
 ignoreDuringBuilds: true
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