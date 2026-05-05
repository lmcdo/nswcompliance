"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp, MapPin } from "lucide-react"

export interface CoverageRegion {
  name: string
  councils: string[]
}

export interface CoverageStat {
  value: string
  label: string
}

interface CoverageSectionProps {
  title: string
  subtitle: string
  stats: CoverageStat[]
  regions: CoverageRegion[]
  note?: string
}

export function CoverageSection({ title, subtitle, stats, regions, note }: CoverageSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <section className="py-20">
      <div className="mx-auto max-w-4xl px-4">
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-accent/10 px-4 py-1.5 text-sm font-medium text-accent">
            <MapPin className="h-4 w-4" />
            <span>NSW Coverage</span>
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {title}
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            {subtitle}
          </p>
        </div>

        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          {stats.map((stat) => (
            <div key={stat.label} className="rounded-xl bg-card p-6 text-center ring-1 ring-border/50">
              <div className="text-3xl font-bold text-primary">{stat.value}</div>
              <div className="mt-1 text-sm text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </div>

        <div className="rounded-2xl bg-card ring-1 ring-border/50">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex w-full items-center justify-between p-6 text-left transition-colors hover:bg-muted/30"
          >
            <span className="font-semibold text-foreground">
              {isExpanded ? "Hide covered councils" : "See all covered councils"}
            </span>
            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            )}
          </button>

          {isExpanded && (
            <div className="border-t border-border/50 p-6">
              {regions.map((region) => (
                <div key={region.name} className="mb-6 last:mb-0">
                  <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-primary">
                    {region.name}
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {region.councils.map((council) => (
                      <span
                        key={council}
                        className="rounded-full bg-primary/10 px-3 py-1 text-sm text-foreground"
                      >
                        {council}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {note && (
          <p className="mt-8 text-center text-sm text-muted-foreground">
            {note}
          </p>
        )}
      </div>
    </section>
  )
}
