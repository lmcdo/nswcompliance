"use client"

import { LandingHero } from "./LandingHero"
import { TrustBar } from "./TrustBar"
import { SocialProof } from "./SocialProof"
import { WhyThisMatters } from "./WhyThisMatters"
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
    <div className="mx-auto max-w-5xl px-4">
      <LandingHero
        badgeText={config.badgeText}
        title={config.title}
        titleAccent={config.titleAccent}
        subtitle={config.subtitle}
        ctaLabel={config.ctaLabel}
      />

      <TrustBar sources={config.trustSources} />

      <SocialProof
        stats={config.stats}
        testimonials={config.testimonials}
      />

      <WhyThisMatters
        comparisons={config.comparisons}
        whatYouGet={config.whatYouGet}
      />
    </div>
  )
}
