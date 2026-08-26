/** @type {import('next').NextConfig} */
const nextConfig = {
 experimental: {
 serverComponentsExternalPackages: ['isomorphic-dompurify']
 },
 // Rewrite /pdf-pages/* to Cloudflare R2 in production
 async redirects() {
   return [
     // Legacy domains → plotdetect.com.au
     // canibuildit.com.au + www.canibuildit.com.au now serve the site directly
     // (redirect removed) — the public info site is served on both domains.
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
     // app/sitemap.ts advertises /shadow and /solar-potential, but the clean
     // URLs above are /shadow-check and /solar-yield - different slugs, so the
     // two the sitemap names 404'd. Measured 2026-08-26: both direct 404, while
     // /flood-risk and /threat-radar 307 correctly. A sitemap entry that 404s is
     // worse than an absent one: it spends crawl budget and reports a soft 404.
     // Redirecting rather than delisting keeps any value already accrued on the
     // advertised URL. __tests__/sitemap-urls-resolve.test.ts now fails if a
     // static sitemap URL has neither a page nor a redirect.
     { source: '/shadow', destination: '/reports/shadow', permanent: false },
     { source: '/solar-potential', destination: '/reports/solar-yield', permanent: false },
     // /partner retired — embed program moved to /for/builders
     { source: '/partner', destination: '/for/builders', permanent: true },
   ];
 },
 async rewrites() {
   // #929: app/sitemap.ts uses generateSitemaps(), which registers the metadata
   // route `/sitemap.xml[[...__metadata_id__]]`. A second handler sitting at
   // app/sitemap.xml/ claimed the same URL, and `next dev` refuses to start on
   // that collision while `next build` tolerates it — so a green build hid a
   // dead dev server for 20 days.
   //
   // robots.txt advertises BOTH /sitemap.xml (the index) and /sitemap/{0..7}.xml
   // (the clusters), so neither can simply be dropped. The index handler now
   // lives at /sitemap-index.xml and this rewrite serves it at the conventional
   // location. It must be `beforeFiles`: the default (afterFiles) runs only when
   // no filesystem route matched, and the metadata route matches /sitemap.xml,
   // so an afterFiles rewrite would never fire.
   const sitemapIndex = [
     { source: '/sitemap.xml', destination: '/sitemap-index.xml' },
   ];

   // Only rewrite to R2 in production (Vercel sets VERCEL=1)
   if (process.env.VERCEL === '1') {
     return {
       beforeFiles: sitemapIndex,
       afterFiles: [
         {
           source: '/pdf-pages/:path*',
           destination: 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/:path*',
         },
       ],
     };
   }
   // In development, serve pdf-pages from the local public folder (default).
   return { beforeFiles: sitemapIndex };
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
 return config;
 },
 images: {
 domains: ['maps.googleapis.com', 'pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev']
 },
 env: {
 NSW_PLANNING_API_BASE_URL: process.env.NSW_PLANNING_API_BASE_URL || 'https://api.apps1.nsw.gov.au/planning',
 GOOGLE_PLACES_API_KEY: process.env.GOOGLE_PLACES_API_KEY || ''
 }
};

module.exports = nextConfig;