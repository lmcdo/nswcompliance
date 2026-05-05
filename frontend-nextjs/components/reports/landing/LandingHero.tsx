"use client"

import { useState, useRef, useEffect } from "react"
import { AddressAutocomplete } from "@/components/reports/AddressAutocomplete"
import { Button } from "@/components/ui/button"
import type { LucideIcon } from "lucide-react"

interface LandingHeroProps {
  badgeText: string
  title: string
  titleAccent: string
  subtitle: string
  ctaLabel: string
}

export function LandingHero({ badgeText, title, titleAccent, subtitle, ctaLabel }: LandingHeroProps) {
  const [address, setAddress] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (address.trim()) {
      window.dispatchEvent(new CustomEvent("landing-search", { detail: { address: address.trim() } }))
      document.getElementById("tool-input")?.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }

  const handleSelect = (addr: string) => {
    setAddress(addr)
  }

  return (
    <section className="py-16 md:py-24">
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent/10 text-accent text-xs font-medium mb-6">
          <span className="size-1.5 rounded-full bg-accent animate-pulse" />
          {badgeText}
        </div>
        <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-foreground tracking-tight">
          {title}
          <br />
          <span className="text-primary">{titleAccent}</span>
        </h1>
        <p className="mt-4 text-muted-foreground text-lg">
          {subtitle}
        </p>
      </div>

      {/* Address search */}
      <form onSubmit={handleSubmit} className="relative max-w-2xl mx-auto">
        <div className="relative flex items-center gap-2 p-2 rounded-2xl bg-card border-2 border-border hover:border-muted-foreground/30 transition-all duration-200 focus-within:border-primary focus-within:shadow-lg focus-within:shadow-primary/10">
          <div className="pl-3">
            <svg
              className="size-5 text-muted-foreground"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
          </div>

          <AddressAutocomplete
            value={address}
            onChange={setAddress}
            onSelect={(addr) => handleSelect(addr)}
            placeholder="Enter any NSW property address..."
            className="flex-1 bg-transparent text-foreground placeholder:text-muted-foreground text-base md:text-lg outline-none py-2"
          />

          <Button
            type="submit"
            size="lg"
            disabled={!address.trim()}
            className="rounded-xl px-6 font-medium"
          >
            {ctaLabel}
          </Button>
        </div>
      </form>

      {/* Micro-trust below search */}
      <div className="flex items-center justify-center gap-6 mt-6 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
          </svg>
          Data never stored
        </span>
        <span className="flex items-center gap-1.5">
          <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Free preview included
        </span>
        <span className="flex items-center gap-1.5">
          <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Results in 8 seconds
        </span>
      </div>
    </section>
  )
}
