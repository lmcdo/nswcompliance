/** The site facts search bar gives the address field the whole row on a phone, and the satellite option is a visible switch. */
import React from "react"
import { fireEvent, render, screen } from "@testing-library/react"

jest.mock("@/components/reports/AddressAutocomplete", () => ({
  AddressAutocomplete: ({ className }: { className?: string }) => <input aria-label="address" className={className} />,
}))

import { LandingHero } from "@/components/reports/landing/LandingHero"
import { SatelliteToggle } from "@/components/reports/SatelliteToggle"
import { MapPin } from "lucide-react"

function hero() {
  return render(<LandingHero badge="b" badgeIcon={MapPin} title="Site Facts" subtitle="s" ctaLabel="Generate Site Facts" />)
}

describe("LandingHero search bar on a phone", () => {
  it("stacks the button under the address field below the sm breakpoint", () => {
    hero()
    const row = screen.getByLabelText("address").closest("form")!.firstElementChild as HTMLElement
    expect(row.className).toContain("flex-col")
    expect(row.className).toContain("sm:flex-row")
  })

  it("makes the button full width on a phone and automatic width from sm up", () => {
    hero()
    const button = screen.getByRole("button", { name: /generate site facts/i })
    expect(button.className).toContain("w-full")
    expect(button.className).toContain("sm:w-auto")
  })

  it("lets the address field shrink instead of being pushed out by the button", () => {
    hero()
    expect(screen.getByLabelText("address").className).toContain("min-w-0")
  })
})

describe("SatelliteToggle", () => {
  it("is a switch that starts off and reports what the person chose", () => {
    const onChange = jest.fn()
    render(<SatelliteToggle checked={false} onChange={onChange} />)
    const toggle = screen.getByRole("switch", { name: /satellite analysis/i })
    expect(toggle).toHaveAttribute("aria-checked", "false")
    fireEvent.click(toggle)
    expect(onChange).toHaveBeenCalledWith(true)
  })

  it("turns off when it is on and is clicked", () => {
    const onChange = jest.fn()
    render(<SatelliteToggle checked={true} onChange={onChange} />)
    fireEvent.click(screen.getByRole("switch"))
    expect(onChange).toHaveBeenCalledWith(false)
  })

  it("does not submit the search form when clicked", () => {
    const onSubmit = jest.fn((e: React.FormEvent) => e.preventDefault())
    render(<form onSubmit={onSubmit}><SatelliteToggle checked={false} onChange={() => {}} /></form>)
    fireEvent.click(screen.getByRole("switch"))
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
