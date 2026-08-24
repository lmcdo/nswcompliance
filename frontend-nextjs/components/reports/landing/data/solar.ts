import { Sun, Building2, Compass, Landmark } from "lucide-react"
import type { ProductLandingConfig } from "../types"

export const solarConfig: ProductLandingConfig = {
  badge: "Satellite roof analysis",
  badgeIcon: Sun,
  title: "Rooftop Solar Yield Estimate",
  subtitle: "How much could solar earn on this roof?",
  ctaLabel: "Check Yield",
  heroImage: "/images/landing/hero-solar.png",
  heroStats: [
    { value: "A–F", label: "Suitability grade" },
    { value: "kWh", label: "Annual estimate" },
    { value: "60s", label: "Analysis time" },
  ],

  // SOURCES AS QUERIED, not as imagined. This strip previously credited NSW Gov
  // building footprints, Bureau of Meteorology climate records and Heritage NSW,
  // and did not name Google at all. The service makes exactly ONE external call
  // — Google's Solar API buildingInsights — plus a local heritage overlay check.
  // The Bureau of Meteorology is never queried by this product.
  dataSources: [
    { icon: Sun, name: "Google Solar API", description: "Roof geometry and annual yield" },
    { icon: Building2, name: "NREL PVWatts", description: "Published system loss factors" },
    { icon: Landmark, name: "NSW heritage overlay", description: "Conservation areas" },
  ],

  featuresTitle: "What This Report Checks",
  featuresSubtitle: "Roof geometry and annual generation figures relayed from Google's Solar API, with published system losses applied.",
  features: [
    {
      icon: Compass,
      title: "Roof Geometry and Orientation",
      description: "Roof area, pitch angle and compass orientation as returned by Google's Solar API for the building nearest your address. The best-performing roof plane is identified from that response — we do not derive the geometry ourselves.",
    },
    {
      icon: Sun,
      title: "Annual Sunshine Hours",
      description: "Sunshine hours for the building, as reported by Google's Solar API alongside the roof geometry. Not a separate climate lookup.",
    },
    {
      icon: Building2,
      title: "Annual Generation Estimate",
      description: "Google's annual DC figure for the roof, then reduced by NREL PVWatts published defaults — 14.08% system losses plus inverter efficiency — to give a delivered figure. Graded A through F. The estimate is Google's; the loss adjustment is ours and is stated on the report.",
    },
    {
      icon: Landmark,
      title: "Heritage and Planning Constraints",
      description: "Flags heritage-listed properties where visible solar panels may require council approval. Prevents wasted site visits to properties that need a DA before installation.",
    },
  ],

  pricingTitle: "Free Check vs Full Report",
  pricingSubtitle: "Get an instant suitability grade, or unlock system sizing and financials for $19.",
  price: "$19",
  comparison: [
    { name: "Suitability grade (A–F)", free: true, paid: true },
    { name: "Best roof orientation", free: true, paid: true },
    { name: "Annual kWh estimate", free: true, paid: true },
    { name: "Heritage flag", free: true, paid: true },
    { name: "System sizing (kW and panel count)", free: false, paid: true },
    { name: "Installed cost estimate", free: false, paid: true },
    { name: "Annual savings and feed-in contribution", free: false, paid: true },
    { name: "Payback period", free: false, paid: true },
    { name: "Downloadable PDF report", free: false, paid: true },
  ],
  // The previous text described a method this product does not run: matching NSW
  // Government footprints, deriving pitch from footprint geometry, and computing
  // irradiance from Bureau of Meteorology records. None of that happens. One
  // call goes to Google; the only arithmetic of ours is the PVWatts loss
  // reduction. Describing a pipeline we do not execute is the defect
  // scripts/dq_probe_pvlib_claim.py exists to catch, and it could not see this
  // one because it scans *.py only and this file is TypeScript.
  methodology: "Your address is sent to Google's Solar API, which returns the nearest building's roof segments, usable area, pitch, compass orientation, sunshine hours and an annual DC generation figure. Those values are relayed as Google reports them — we do not model the roof or the irradiance. The one adjustment we make is to reduce Google's DC figure by NREL PVWatts published defaults, 14.08% system losses and inverter efficiency, to give a delivered figure; both numbers appear on the report so the difference is visible. A heritage flag is added from NSW heritage overlay data.",
}
