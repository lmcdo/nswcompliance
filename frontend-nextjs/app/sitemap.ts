import type { MetadataRoute } from 'next'
import { FLOOD_LGAS } from '@/lib/lga-data/flood-lgas'
import { SOLAR_LGAS } from '@/lib/lga-data/solar-lgas'
import { GRANNY_FLAT_LGAS } from '@/lib/lga-data/granny-flat-lgas'
import { THREAT_RADAR_LGAS } from '@/lib/lga-data/threat-radar-lgas'
import { SHADOW_LGAS } from '@/lib/lga-data/shadow-lgas'

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

  const grannyFlatPages = GRANNY_FLAT_LGAS.map(lga => ({
    url: `${base}/granny-flat/${lga.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.9,
  }))

  const threatRadarPages = THREAT_RADAR_LGAS.map(lga => ({
    url: `${base}/threat-radar/${lga.slug}`,
    lastModified: now,
    changeFrequency: 'daily' as const,
    priority: 0.85,
  }))

  const shadowPages = SHADOW_LGAS.map(lga => ({
    url: `${base}/shadow/${lga.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.85,
  }))

  return [...staticPages, ...grannyFlatPages, ...floodPages, ...solarPages, ...threatRadarPages, ...shadowPages]
}
