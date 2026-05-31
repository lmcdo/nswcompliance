import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://plotdetect.com.au'

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
    sitemap: `${siteUrl}/sitemap.xml`,
  }
}
