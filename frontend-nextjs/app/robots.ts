import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  // Hardcoded on purpose: NEXT_PUBLIC_SITE_URL is set to the plotdetect.com.au
  // info site in production, which sent crawlers to a sitemap on a domain this
  // app's content does not live on (found 2026-07-23 — zero pages indexed).
  // The canonical content host is the canibuildit apex: www 307s to it.
  const siteUrl = 'https://canibuildit.com.au'

  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/'],
      },
      // Explicitly allow AI crawlers for Generative Engine Optimization
      {
        userAgent: 'GPTBot',
        allow: '/',
        disallow: ['/api/'],
      },
      {
        userAgent: 'OAI-SearchBot',
        allow: '/',
        disallow: ['/api/'],
      },
      {
        userAgent: 'ChatGPT-User',
        allow: '/',
        disallow: ['/api/'],
      },
      {
        userAgent: 'ClaudeBot',
        allow: '/',
        disallow: ['/api/'],
      },
      {
        userAgent: 'PerplexityBot',
        allow: '/',
        disallow: ['/api/'],
      },
      {
        userAgent: 'Google-Extended',
        allow: '/',
        disallow: ['/api/'],
      },
      {
        userAgent: 'Bytespider',
        allow: '/',
        disallow: ['/api/'],
      },
    ],
    // /sitemap.xml is a route handler emitting a sitemap index over the eight
    // generateSitemaps() cluster files at /sitemap/{0..7}.xml. Both the index
    // and the cluster files are listed so crawlers that ignore index files
    // still discover every cluster.
    sitemap: [
      `${siteUrl}/sitemap.xml`,
      ...Array.from({ length: 8 }, (_, i) => `${siteUrl}/sitemap/${i}.xml`),
    ],
  }
}
