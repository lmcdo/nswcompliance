"use client"

import { useState } from "react"
import { Search, Shield, MapPin, Satellite } from "lucide-react"
import { AddressAutocomplete } from "@/components/reports/AddressAutocomplete"
import { Button } from "@/components/ui/button"
import type { LucideIcon } from "lucide-react"

interface HeroStat {
  value: string
  label: string
}

interface LandingHeroProps {
  badge: string
  badgeIcon: LucideIcon
  title: string
  subtitle: string
  ctaLabel: string
  stats?: HeroStat[]
  heroImage?: string
  /** Product-specific controls rendered under the search bar (e.g. the brief's
      satellite toggle) — options must be visible where the run starts, not
      buried in a second input further down the page. */
  searchExtras?: React.ReactNode
}

export function LandingHero({ badge, badgeIcon: BadgeIcon, title, subtitle, ctaLabel, stats, heroImage, searchExtras }: LandingHeroProps) {
  const [address, setAddress] = useState("")
  const [isFocused, setIsFocused] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (address.trim()) {
      window.dispatchEvent(new CustomEvent("landing-search", { detail: { address: address.trim() } }))
    }
  }

  return (
    <section className="relative overflow-hidden">
      {/* Aerial satellite background */}
      {heroImage && (
        <div
          className="absolute inset-0 bg-cover bg-center opacity-[0.08]"
          style={{ backgroundImage: `url(${heroImage})` }}
        />
      )}

      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-background to-background" />

      {/* Subtle grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />

      <div className="relative mx-auto max-w-4xl px-4 py-20 sm:py-28 lg:py-32">
        {/* Header badge */}
        <div className="mb-6 flex justify-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary">
            <BadgeIcon className="h-4 w-4" />
            <span>{badge}</span>
          </div>
        </div>

        {/* Main heading */}
        <h1 className="text-balance text-center text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
          {title}
        </h1>

        {/* Subheading */}
        <p className="mx-auto mt-4 max-w-2xl text-balance text-center text-lg text-muted-foreground sm:text-xl">
          {subtitle}
        </p>

        {/* Search Bar */}
        <form onSubmit={handleSubmit} className="relative mx-auto mt-10 max-w-2xl">
          <div
            className={`
              relative flex items-center rounded-2xl bg-card shadow-xl ring-1 transition-all duration-300
              ${isFocused
                ? "ring-primary shadow-primary/20 shadow-2xl"
                : "ring-border/50 shadow-lg"
              }
            `}
          >
            <div className="flex items-center pl-5">
              <MapPin className={`h-5 w-5 transition-colors ${isFocused ? "text-primary" : "text-muted-foreground"}`} />
            </div>

            <AddressAutocomplete
              value={address}
              onChange={setAddress}
              onSelect={(addr) => setAddress(addr)}
              placeholder="Enter a NSW property address..."
              className="flex-1 bg-transparent px-4 py-5 text-lg text-foreground placeholder:text-muted-foreground focus:outline-none"
            />

            <div className="pr-2">
              <Button
                type="submit"
                size="lg"
                className="rounded-xl px-6 py-6 text-base font-semibold"
                disabled={!address.trim()}
              >
                <Search className="mr-2 h-5 w-5" />
                {ctaLabel}
              </Button>
            </div>
          </div>

          {/* Product options directly under the search bar — above the helper
              text so they read as part of the input, not as fine print. */}
          {searchExtras}

          {/* Helper text */}
          <p className="mt-3 text-center text-sm text-muted-foreground">
            <Shield className="mr-1 inline-block h-4 w-4" />
            Free instant check · No signup required · Full NSW coverage
          </p>
        </form>

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
