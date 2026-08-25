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
import { ARTICLES } from '@/lib/blog-articles'
import { DATA_DICTIONARY_FIELDS } from '@/lib/data-dictionary'

/**
 * Topic-clustered sitemaps for GEO (Generative Engine Optimization).
 * AI crawlers parse topical clusters more effectively than a single flat sitemap.
 * Each ID produces a separate /sitemap/{id}.xml file, with a sitemap index at /sitemap.xml.
 */
export async function generateSitemaps() {
  return [
    { id: 0 },  // core — static pages + tools
    { id: 1 },  // granny-flat — LGA pages
    { id: 2 },  // flood — LGA pages
    { id: 3 },  // solar — LGA pages
    { id: 4 },  // hazards — bushfire + shadow LGA pages
    { id: 5 },  // monitoring — threat-radar + pre-da-history LGA pages
    { id: 6 },  // compliance — planning-controls + conveyancing LGA pages
    { id: 7 },  // blog — articles + council granny flat guides
  ]
}

export default function sitemap({ id }: { id: number }): MetadataRoute.Sitemap {
  // The app's canonical consumer domain (Option B). plotdetect.com.au is the
  // separate info-site project and 404s for app routes — advertising it here
  // sent search engines to dead URLs. APEX, not www: the edge 307s every www
  // URL to the apex, so www URLs in a sitemap register as "page with redirect"
  // and never index (found 2026-07-23).
  const base = 'https://canibuildit.com.au'
  const now = new Date()

  switch (id) {
    // Core: static pages, tools, hub landing pages
    case 0:
      return [
        { url: `${base}/`,                priority: 1.0,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/granny-flat`,     priority: 0.95, changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/flood-risk`,      priority: 0.9,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/solar-potential`, priority: 0.9,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/shadow`,          priority: 0.9,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/threat-radar`,    priority: 0.9,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/assessment`,       priority: 0.9,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/reports/conveyancing`, priority: 0.9, changeFrequency: 'weekly', lastModified: now },
        { url: `${base}/climate-risk`,    priority: 0.9,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/glossary`,        priority: 0.85, changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/planning-standards`, priority: 0.85, changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/open-data`,          priority: 0.8,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/site-directory`,     priority: 0.7,  changeFrequency: 'weekly',  lastModified: now },
        ...DATA_DICTIONARY_FIELDS.map(f => ({
          url: `${base}/open-data/fields/${f.slug}`,
          priority: 0.75,
          changeFrequency: 'monthly' as const,
          lastModified: now,
        })),
        { url: `${base}/tools/zoning-check`,      priority: 0.9,  changeFrequency: 'weekly', lastModified: now },
        { url: `${base}/tools/subdivision-check`, priority: 0.9,  changeFrequency: 'weekly', lastModified: now },
        { url: `${base}/tools/upzoning-check`,    priority: 0.9,  changeFrequency: 'weekly', lastModified: now },
        { url: `${base}/check`,           priority: 0.85, changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/reports`,          priority: 0.9,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/reports/flood`,   priority: 0.9,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/reports/bushfire`, priority: 0.9,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/reports/granny-flat`, priority: 0.9, changeFrequency: 'weekly', lastModified: now },
        { url: `${base}/reports/shadow`,  priority: 0.85, changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/reports/solar-yield`, priority: 0.85, changeFrequency: 'weekly', lastModified: now },
        { url: `${base}/reports/threat-radar`, priority: 0.85, changeFrequency: 'weekly', lastModified: now },
        { url: `${base}/reports/pre-da-history`, priority: 0.8, changeFrequency: 'weekly', lastModified: now },
        { url: `${base}/dcp-browse`,      priority: 0.8,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/browse`,          priority: 0.7,  changeFrequency: 'weekly',  lastModified: now },
        { url: `${base}/what-you-get`,    priority: 0.8,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/for/homebuyers`,  priority: 0.8,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/for/conveyancers`, priority: 0.8, changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/for/builders`,    priority: 0.7,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/for/buyers-agents`, priority: 0.7, changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/for/councils`,    priority: 0.7,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/for/planners`,    priority: 0.8,  changeFrequency: 'monthly', lastModified: now },
        // Live since it was built and absent from all 8 sitemap chunks until
        // 2026-08-25 — the page existed, nothing linked search engines to it.
        // __tests__/sitemap-covers-for-pages.test.ts now fails if a /for/ page
        // is added to disk without being listed here.
        { url: `${base}/for/students`,    priority: 0.7,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/developers`,      priority: 0.8,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/pricing`,         priority: 0.7,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/how-it-works`,    priority: 0.7,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/about`,           priority: 0.5,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/contact`,         priority: 0.5,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/user-guide`,      priority: 0.6,  changeFrequency: 'monthly', lastModified: now },
        { url: `${base}/quick-guide`,     priority: 0.6,  changeFrequency: 'monthly', lastModified: now },
      ]

    // Granny flat LGA pages
    case 1:
      return GRANNY_FLAT_LGAS.map(lga => ({
        url: `${base}/granny-flat/${lga.slug}`,
        lastModified: now,
        changeFrequency: 'weekly' as const,
        priority: 0.9,
      }))

    // Flood risk LGA pages
    case 2:
      return FLOOD_LGAS.map(lga => ({
        url: `${base}/flood-risk/${lga.slug}`,
        lastModified: now,
        changeFrequency: 'weekly' as const,
        priority: 0.9,
      }))

    // Solar potential LGA pages
    case 3:
      return SOLAR_LGAS.map(lga => ({
        url: `${base}/solar-potential/${lga.slug}`,
        lastModified: now,
        changeFrequency: 'weekly' as const,
        priority: 0.85,
      }))

    // Hazards: bushfire + shadow LGA pages
    case 4:
      return [
        ...BUSHFIRE_LGAS.map(lga => ({
          url: `${base}/bushfire/${lga.slug}`,
          lastModified: now,
          changeFrequency: 'weekly' as const,
          priority: 0.85,
        })),
        ...SHADOW_LGAS.map(lga => ({
          url: `${base}/shadow/${lga.slug}`,
          lastModified: now,
          changeFrequency: 'weekly' as const,
          priority: 0.85,
        })),
      ]

    // Monitoring: threat radar + pre-DA history LGA pages
    case 5:
      return [
        ...THREAT_RADAR_LGAS.map(lga => ({
          url: `${base}/threat-radar/${lga.slug}`,
          lastModified: now,
          changeFrequency: 'daily' as const,
          priority: 0.85,
        })),
        ...PRE_DA_HISTORY_LGAS.map(lga => ({
          url: `${base}/pre-da-history/${lga.slug}`,
          lastModified: now,
          changeFrequency: 'weekly' as const,
          priority: 0.8,
        })),
      ]

    // Compliance: planning controls + conveyancing LGA pages
    case 6:
      return [
        ...VERIFY_LGAS.map(lga => ({
          url: `${base}/planning-controls/${lga.slug}`,
          lastModified: now,
          changeFrequency: 'weekly' as const,
          priority: 0.85,
        })),
        ...CONVEYANCING_LGAS.map(lga => ({
          url: `${base}/conveyancing/${lga.slug}`,
          lastModified: now,
          changeFrequency: 'weekly' as const,
          priority: 0.85,
        })),
      ]

    // Blog: articles + council granny flat guides
    case 7:
      return [
        { url: `${base}/blog`,            priority: 0.8, changeFrequency: 'weekly' as const, lastModified: now },
        { url: `${base}/blog/granny-flat`, priority: 0.8, changeFrequency: 'weekly' as const, lastModified: now },
        ...ARTICLES.map(article => ({
          url: `${base}/blog/${article.slug}`,
          lastModified: new Date(article.date),
          changeFrequency: 'monthly' as const,
          priority: 0.7,
        })),
        ...COUNCIL_STATS.map(c => ({
          url: `${base}/blog/granny-flat/${c.slug}`,
          lastModified: now,
          changeFrequency: 'monthly' as const,
          priority: 0.7,
        })),
      ]

    default:
      return []
  }
}
