"use client"

import { Search, Shield } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { StatItem } from "./types"

interface LandingHeroProps {
  badge: string
  badgeIcon: LucideIcon
  title: string
  subtitle: string
  ctaLabel: string
  stats?: StatItem[]
}

export function LandingHero({ badge, badgeIcon: BadgeIcon, title, subtitle, ctaLabel, stats }: LandingHeroProps) {
  const scrollToTool = () => {
    document.getElementById("tool-input")?.scrollIntoView({ behavior: "smooth", block: "center" })
  }

  return (
    <section className="relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-background to-background" />

      {/* Subtle grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />

      <div className="relative mx-auto max-w-4xl px-4 py-20 sm:py-28">
        {/* Header badge */}
        <div className="mb-6 flex justify-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary">
            <BadgeIcon className="h-4 w-4" />
            <span>{badge}</span>
          </div>
        </div>

        {/* Main heading */}
        <h1 className="text-center text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
          {title}
        </h1>

        {/* Subheading */}
        <p className="mx-auto mt-4 max-w-2xl text-center text-lg text-muted-foreground sm:text-xl">
          {subtitle}
        </p>

        {/* CTA Button */}
        <div className="mt-10 flex justify-center">
          <Button
            size="lg"
            className="rounded-xl px-8 py-6 text-base font-semibold"
            onClick={scrollToTool}
          >
            <Search className="mr-2 h-5 w-5" />
            {ctaLabel}
          </Button>
        </div>

        {/* Helper text */}
        <p className="mt-3 text-center text-sm text-muted-foreground">
          <Shield className="mr-1 inline-block h-4 w-4" />
          Free instant check · No signup required · Full NSW coverage
        </p>

        {/* Quick stats */}
        {stats && stats.length > 0 && (
          <div className="mt-12 flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
            {stats.map((stat, i) => (
              <div key={stat.label} className="flex items-center gap-x-10">
                {i > 0 && <div className="hidden h-8 w-px bg-border sm:block" />}
                <div className="text-center">
                  <div className="text-2xl font-bold text-foreground">{stat.value}</div>
                  <div className="text-sm text-muted-foreground">{stat.label}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
