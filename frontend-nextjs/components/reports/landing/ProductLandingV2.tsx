"use client"

import { LandingHero } from "./LandingHero"
import { DataSourceStrip } from "./DataSourceStrip"
import { FeatureGrid } from "./FeatureGrid"
import { PricingTable } from "./PricingTable"
import { CoverageSection } from "./CoverageSection"
import type { ProductLandingConfig } from "./types"
import { floodConfig } from "./data/flood"
import { shadowConfig } from "./data/shadow"
import { solarConfig } from "./data/solar"
import { threatRadarConfig } from "./data/threat-radar"
import { preDAConfig } from "./data/pre-da"
import { bushfireConfig } from "./data/bushfire"
import { conveyancingConfig } from "./data/conveyancing"
import { intelligenceBriefConfig } from "./data/intelligence-brief"

const configs: Record<string, ProductLandingConfig> = {
  flood: floodConfig,
  shadow: shadowConfig,
  solar: solarConfig,
  "threat-radar": threatRadarConfig,
  "pre-da": preDAConfig,
  bushfire: bushfireConfig,
  conveyancing: conveyancingConfig,
  "intelligence-brief": intelligenceBriefConfig,
}

interface ProductLandingV2Props {
  product: string
  /** Rendered under the hero search bar — see LandingHero.searchExtras. */
  searchExtras?: React.ReactNode
}

export function ProductLandingV2({ product, searchExtras }: ProductLandingV2Props) {
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
        heroImage={config.heroImage}
        searchExtras={searchExtras}
      />

      <DataSourceStrip sources={config.dataSources} />

      <FeatureGrid
        title={config.featuresTitle}
        subtitle={config.featuresSubtitle}
        features={config.features}
      />

      {config.price && config.comparison ? (
        <PricingTable
          title={config.pricingTitle ?? ""}
          subtitle={config.pricingSubtitle ?? ""}
          price={config.price}
          comparison={config.comparison}
          methodology={config.methodology}
        />
      ) : (
        // Free product — no pricing table, but the methodology block still renders
        <section className="bg-card/30 py-16">
          <div className="mx-auto max-w-4xl px-4">
            <div className="rounded-2xl bg-muted/50 p-6 sm:p-8">
              <h3 className="mb-4 text-lg font-semibold text-foreground">How It Works</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {config.methodology}
              </p>
            </div>
          </div>
        </section>
      )}

      {config.coverageRegions && config.coverageRegions.length > 0 && (
        <CoverageSection
          title={config.coverageTitle || "Coverage"}
          subtitle={config.coverageSubtitle || ""}
          stats={config.coverageStats || []}
          regions={config.coverageRegions}
          note={config.coverageNote}
        />
      )}
    </div>
  )
}
