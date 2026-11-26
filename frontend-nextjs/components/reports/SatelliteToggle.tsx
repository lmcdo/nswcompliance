"use client"

import { Satellite } from "lucide-react"

interface SatelliteToggleProps {
  checked: boolean
  onChange: (next: boolean) => void
}

/**
 * The site facts report's satellite option: a coloured card with a real switch, so it reads as a choice on every
 * screen. Off is a teal outline with a tinted fill (visible, not greyed out); On is solid teal with white text.
 * The words On and Off are shown as well as the colour, so the state does not depend on colour alone.
 * Satellite analysis adds the climate and terrain sections.
 */
export function SatelliteToggle({ checked, onChange }: SatelliteToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`flex min-h-[56px] w-full items-center gap-3 rounded-xl border-2 px-4 py-3 text-left shadow-md transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 sm:w-auto ${
        checked
          ? "border-teal-700 bg-teal-600 text-white hover:bg-teal-700"
          : "border-teal-500 bg-teal-50 text-teal-900 hover:bg-teal-100"
      }`}
    >
      <span
        aria-hidden="true"
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${checked ? "bg-white/20 text-white" : "bg-teal-600 text-white"}`}
      >
        <Satellite className="h-5 w-5" />
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-sm font-semibold">Satellite analysis</span>
        <span className={`text-xs ${checked ? "text-teal-50" : "text-teal-800"}`}>Adds climate and terrain from satellite data</span>
      </span>
      <span className="flex shrink-0 items-center gap-2" aria-hidden="true">
        <span className="text-xs font-bold uppercase tracking-wide">{checked ? "On" : "Off"}</span>
        <span className={`relative h-6 w-11 rounded-full transition-colors ${checked ? "bg-white/30" : "bg-teal-300"}`}>
          <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${checked ? "left-[22px]" : "left-0.5"}`} />
        </span>
      </span>
    </button>
  )
}
