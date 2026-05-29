import type { MetadataRoute } from 'next'
import { FLOOD_LGAS } from '@/lib/lga-data/flood-lgas'
import { SOLAR_LGAS } from '@/lib/lga-data/solar-lgas'
import { GRANNY_FLAT_LGAS } from '@/lib/lga-data/granny-flat-lgas'
import { THREAT_RADAR_LGAS } from '@/lib/lga-data/threat-radar-lgas'
import { SHADOW_LGAS } from '@/lib/lga-data/shadow-lgas'
import { BUSHFIRE_LGAS } from '@/lib/lga-data/bushfire-lgas'
import { PRE_DA_HISTORY_LGAS } from '@/lib/lga-data/pre-da-history-lgas'
import { VERIFY_LGAS } from '@/lib/lga-data/verify-lgas'
import { CONVEYANCING_LGAS } from '@/lib/lga-data/conveyancing-lgas'
import { COUNCIL_STATS } from '@/lib/lga-data/secondary-dwelling-stats'

export default function sitemap(): MetadataRoute.Sitemap {
  const base = 'https://plotdetect.com.au'
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
    { url: `${base}/assessment`,       priority: 0.9,  changeFrequency: 'weekly' as const,  lastModified: now },
    { url: `${base}/reports/conveyancing`, priority: 0.9, changeFrequency: 'weekly' as const, lastModified: now },
    { url: `${base}/pricing`,         priority: 0.7,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/how-it-works`,    priority: 0.7,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/contact`,         priority: 0.5,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/climate-risk`,    priority: 0.9,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/about`,           priority: 0.5,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/for/conveyancers`, priority: 0.8, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/for/builders`,    priority: 0.7,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/for/buyers-agents`, priority: 0.7, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/for/councils`,    priority: 0.7,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/for/planners`,    priority: 0.8,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/developers`,      priority: 0.8,  changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/tools/zoning-check`,      priority: 0.9,  changeFrequency: 'weekly' as const, lastModified: now },
    { url: `${base}/tools/subdivision-check`, priority: 0.9,  changeFrequency: 'weekly' as const, lastModified: now },
    { url: `${base}/blog`,            priority: 0.8,  changeFrequency: 'weekly' as const,  lastModified: now },
    { url: `${base}/blog/granny-flat`, priority: 0.8,  changeFrequency: 'weekly' as const,  lastModified: now },
    { url: `${base}/blog/aasb-s2-property-climate-data`,        priority: 0.7, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/blog/apra-cpg-229-property-assessment`,     priority: 0.7, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/blog/climate-risk-data-provider-australia`,  priority: 0.7, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/blog/uninsurable-property-climate-risk`,     priority: 0.7, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/blog/is-my-house-in-a-flood-zone-nsw`,      priority: 0.8, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/blog/nsw-planning-portal-gaps`,             priority: 0.8, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/blog/cdc-vs-da-which-approval-pathway`,     priority: 0.8, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/blog/setback-requirements-nsw`,             priority: 0.8, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/blog/development-control-plans-explained`,  priority: 0.8, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/blog/building-height-limits-nsw`,           priority: 0.8, changeFrequency: 'monthly' as const, lastModified: now },
    { url: `${base}/blog/site-analysis-report-explained`,       priority: 0.8, changeFrequency: 'monthly' as const, lastModified: now },
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

  const conveyancingPages = CONVEYANCING_LGAS.map(lga => ({
    url: `${base}/conveyancing/${lga.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.85,
  }))

  const planningControlsPages = VERIFY_LGAS.map(lga => ({
    url: `${base}/planning-controls/${lga.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.85,
  }))

  const grannyFlatBlogPages = COUNCIL_STATS.map(c => ({
    url: `${base}/blog/granny-flat/${c.slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }))

  return [
    ...staticPages,
    { url: `${base}/browse`, lastModified: now, changeFrequency: 'weekly' as const, priority: 0.7 },
    ...grannyFlatPages, ...floodPages, ...solarPages, ...threatRadarPages,
    ...shadowPages, ...bushfirePages, ...preDaHistoryPages, ...planningControlsPages,
    ...conveyancingPages, ...grannyFlatBlogPages,
  ]
}
