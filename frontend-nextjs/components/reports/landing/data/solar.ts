import { Sun, Building2, Compass, Landmark } from "lucide-react"
import type { ProductLandingConfig } from "../types"

export const solarConfig: ProductLandingConfig = {
  badge: "Satellite roof analysis",
  badgeIcon: Sun,
  title: "Rooftop Solar Yield Estimate",
  subtitle: "How much could solar earn on this roof?",
  ctaLabel: "Check Yield",
  heroStats: [
    { value: "A–F", label: "Suitability grade" },
    { value: "kWh", label: "Annual estimate" },
    { value: "60s", label: "Analysis time" },
  ],

  dataSources: [
    { icon: Building2, name: "NSW Gov", description: "Building footprints" },
    { icon: Sun, name: "Bureau of Met", description: "Climate records" },
    { icon: Landmark, name: "Heritage NSW", description: "Conservation areas" },
  ],

  featuresTitle: "What This Report Checks",
  featuresSubtitle: "Satellite-derived roof geometry combined with local irradiance data.",
  features: [
    {
      icon: Compass,
      title: "Roof Geometry and Orientation",
      description: "Roof area, pitch angle, and compass orientation derived from NSW Government building footprint data. The best-performing roof plane is identified automatically.",
    },
    {
      icon: Sun,
      title: "Local Solar Irradiance",
      description: "Annual sunshine hours and irradiance for your location, sourced from Bureau of Meteorology climate records. Accounts for latitude, cloud cover, and local climate patterns.",
    },
    {
      icon: Building2,
      title: "Annual Generation Estimate",
      description: "Estimated kWh output per year based on the roof geometry and local irradiance. Graded A through F — A-grade roofs have optimal north-facing orientation and minimal shading.",
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
  methodology: "Building footprints are matched to your address using NSW Government property boundary and structure data. Roof orientation and pitch are derived from the footprint geometry. Annual irradiance is calculated from Bureau of Meteorology climate records for your location. The generation estimate applies standard panel efficiency and system loss factors to the usable roof area and irradiance.",
}
