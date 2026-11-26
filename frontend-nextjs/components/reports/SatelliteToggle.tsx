"use client"

import { Satellite } from "lucide-react"

interface SatelliteToggleProps {
  checked: boolean
  onChange: (next: boolean) => void
}

/** The site facts report's satellite option: a visible on/off button, not a small checkbox. Satellite analysis adds the climate and terrain sections. */
export function SatelliteToggle({ checked, onChange }: SatelliteToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`flex w-full items-center justify-between gap-3 rounded-xl px-4 py-3 text-left shadow-md ring-1 transition-all sm:w-auto ${
        checked ? "bg-teal-50 text-teal-900 ring-teal-500" : "bg-card text-foreground ring-border/50 hover:ring-primary/50"
      }`}
    >
      <span className="flex flex-col">
        <span className="inline-flex items-center gap-2 text-sm font-semibold">
          <Satellite className="h-4 w-4" aria-hidden="true" />
          Satellite analysis
        </span>
        <span className="text-xs font-normal text-muted-foreground">Adds climate and terrain from satellite data</span>
      </span>
      <span
        aria-hidden="true"
        className={`rounded-full px-3 py-1 text-xs font-semibold ${checked ? "bg-teal-600 text-white" : "bg-muted text-muted-foreground"}`}
      >
        {checked ? "On" : "Off"}
      </span>
    </button>
  )
}
