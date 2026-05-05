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

export interface WhatYouGetItem {
  title: string
  description: string
}

export interface TrustSource {
  name: string
  logo: string
}

export interface ProductLandingConfig {
  // Hero
  badgeText: string
  title: string
  titleAccent: string
  subtitle: string
  ctaLabel: string

  // Trust bar
  trustSources: TrustSource[]

  // Social proof
  stats: StatItem[]
  testimonials: Testimonial[]

  // Why this matters
  comparisons: ComparisonCard[]
  whatYouGet: WhatYouGetItem[]
}
