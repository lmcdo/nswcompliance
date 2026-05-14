import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://canibuildit.com.au'

  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/', '/assessment/'],
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
  }
}
