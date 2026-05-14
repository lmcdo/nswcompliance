import type { MetadataRoute } from 'next'
import { FLOOD_LGAS } from '@/lib/lga-data/flood-lgas'
import { SOLAR_LGAS } from '@/lib/lga-data/solar-lgas'
import { GRANNY_FLAT_LGAS } from '@/lib/lga-data/granny-flat-lgas'
import { THREAT_RADAR_LGAS } from '@/lib/lga-data/threat-radar-lgas'
import { SHADOW_LGAS } from '@/lib/lga-data/shadow-lgas'
import { BUSHFIRE_LGAS } from '@/lib/lga-data/bushfire-lgas'
import { PRE_DA_HISTORY_LGAS } from '@/lib/lga-data/pre-da-history-lgas'

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
    { url: `${base}/`,                priority: 1.0,  changeFrequency: 'weekly' as const,  lastModified: now },
    { url: `${base}/granny-flat`,     priority: 0.95, changeFrequency: 'weekly' as const,  lastModified: now },
    { url: `${base}/flood-risk`,      priority: 0.9,  changeFrequency: 'weekly' as const,  lastModified: now },
    { url: `${base}/solar-potential`, priority: 0.9,  changeFrequency: 'weekly' as const,  lastModified: now },
    { url: `${base}/shadow`,          priority: 0.9,  changeFrequency: 'weekly' as const,  lastModified: now },
    { url: `${base}/threat-radar`,    priority: 0.9,  changeFrequency: 'weekly' as const,  lastModified: now },
    { url: `${base}/pricing`,         priority: 0.7,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/how-it-works`,    priority: 0.7,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/partner`,         priority: 0.6,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/contact`,         priority: 0.5,  changeFrequency: 'monthly' as const, lastModified: now },
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

  const bushfirePages = BUSHFIRE_LGAS.map(lga => ({
    url: `${base}/bushfire/${lga.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.85,
  }))

  const preDaHistoryPages = PRE_DA_HISTORY_LGAS.map(lga => ({
    url: `${base}/pre-da-history/${lga.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.8,
  }))

  return [
    ...staticPages,
    { url: `${base}/browse`, lastModified: now, changeFrequency: 'weekly' as const, priority: 0.7 },
    ...grannyFlatPages, ...floodPages, ...solarPages, ...threatRadarPages,
    ...shadowPages, ...bushfirePages, ...preDaHistoryPages,
  ]
}
