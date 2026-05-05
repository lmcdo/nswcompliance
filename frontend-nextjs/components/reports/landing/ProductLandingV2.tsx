"use client"

import { LandingHero } from "./LandingHero"
import { DataSourceStrip } from "./DataSourceStrip"
import { FeatureGrid } from "./FeatureGrid"
import { PricingTable } from "./PricingTable"
import { CoverageSection } from "./CoverageSection"
import { WhyThisMatters } from "./WhyThisMatters"
import { SocialProof } from "./SocialProof"
import type { ProductLandingConfig } from "./types"
import { floodConfig } from "./data/flood"
import { shadowConfig } from "./data/shadow"
import { solarConfig } from "./data/solar"
import { threatRadarConfig } from "./data/threat-radar"
import { preDAConfig } from "./data/pre-da"

const configs: Record<string, ProductLandingConfig> = {
  flood: floodConfig,
  shadow: shadowConfig,
  solar: solarConfig,
  "threat-radar": threatRadarConfig,
  "pre-da": preDAConfig,
}

interface ProductLandingV2Props {
  product: string
}

export function ProductLandingV2({ product }: ProductLandingV2Props) {
  const config = configs[product]
  if (!config) return null

  return (
    <div>
      <LandingHero
        badge={config.badge}
        badgeIcon={config.badgeIcon}
        title={config.title}
        subtitle={config.subtitle}
        ctaLabel={config.ctaLabel}
        stats={config.heroStats}
      />

      {config.dataSources && config.dataSources.length > 0 && (
        <DataSourceStrip sources={config.dataSources} />
      )}

      {config.comparisons && config.comparisons.length > 0 && (
        <WhyThisMatters
          comparisons={config.comparisons}
          whatYouGet={config.whatYouGet}
        />
      )}

      <FeatureGrid
        title={config.featuresTitle}
        subtitle={config.featuresSubtitle}
        features={config.features}
      />

      <PricingTable
        title={config.pricingTitle}
        subtitle={config.pricingSubtitle}
        price={config.price}
        comparison={config.comparison}
        methodology={config.methodology}
      />

      {config.coverageRegions && config.coverageRegions.length > 0 && (
        <CoverageSection
          title={config.coverageTitle || "Coverage"}
          subtitle={config.coverageSubtitle || ""}
          stats={config.coverageStats || []}
          regions={config.coverageRegions}
          note={config.coverageNote}
        />
      )}

      {config.stats && config.testimonials && (
        <SocialProof
          stats={config.stats}
          testimonials={config.testimonials}
        />
      )}
    </div>
  )
}
