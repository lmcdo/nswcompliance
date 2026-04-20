import type { MetadataRoute } from 'next'
import { FLOOD_LGAS } from '@/lib/lga-data/flood-lgas'
import { SOLAR_LGAS } from '@/lib/lga-data/solar-lgas'

export default function sitemap(): MetadataRoute.Sitemap {
  const base = 'https://canibuildit.com.au'
  const now = new Date()

  const floodPages = FLOOD_LGAS.map(lga => ({
    url: `${base}/flood-risk/${lga.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.9,
  }))

  const solarPages = SOLAR_LGAS.map(lga => ({
    url: `${base}/solar-potential/${lga.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.85,
  }))

  const staticPages = [
    { url: `${base}/`, priority: 1.0, changeFrequency: 'daily' as const, lastModified: now },
    { url: `${base}/canibuildit`, priority: 0.95, changeFrequency: 'daily' as const, lastModified: now },
  ]

  return [...staticPages, ...floodPages, ...solarPages]
}
