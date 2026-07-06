import type { LucideIcon } from "lucide-react"

export interface StatItem {
  value: string
  label: string
}

export interface DataSourceItem {
  icon: LucideIcon
  name: string
  description: string
}

export interface FeatureItem {
  icon: LucideIcon
  title: string
  description: string
}

export interface ComparisonRow {
  name: string
  free: boolean
  paid: boolean
}

export interface CoverageRegion {
  name: string
  councils: string[]
}

export interface ProductLandingConfig {
  // Hero
  badge: string
  badgeIcon: LucideIcon
  title: string
  subtitle: string
  ctaLabel: string
  heroStats?: StatItem[]
  heroImage?: string

  // Data sources
  dataSources: DataSourceItem[]

  // Feature grid
  featuresTitle: string
  featuresSubtitle: string
  features: FeatureItem[]

  // Pricing (optional — free products render the methodology block alone)
  pricingTitle?: string
  pricingSubtitle?: string
  price?: string
  comparison?: ComparisonRow[]
  methodology: string

  // Coverage (optional)
  coverageTitle?: string
  coverageSubtitle?: string
  coverageStats?: StatItem[]
  coverageRegions?: CoverageRegion[]
  coverageNote?: string
}
