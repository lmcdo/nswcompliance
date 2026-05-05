import { LucideIcon } from "lucide-react"

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

export interface DataSource {
  icon: LucideIcon
  name: string
  description: string
}

export interface StatItem {
  value: string
  label: string
}

export interface Testimonial {
  quote: string
  author: string
  role: string
}

export interface ComparisonCard {
  problem: string
  limitation: string
  solution: string
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

  // Data sources (optional)
  dataSources?: DataSource[]

  // Features
  featuresTitle: string
  featuresSubtitle: string
  features: FeatureItem[]

  // Pricing
  pricingTitle: string
  pricingSubtitle: string
  price: string
  comparison: ComparisonRow[]
  methodology: string

  // Coverage (optional)
  coverageTitle?: string
  coverageSubtitle?: string
  coverageStats?: StatItem[]
  coverageRegions?: CoverageRegion[]
  coverageNote?: string

  // WhyThisMatters (optional)
  comparisons?: ComparisonCard[]
  whatYouGet?: FeatureItem[]

  // Social proof (optional)
  stats?: StatItem[]
  testimonials?: Testimonial[]
}
