import {
  Building2, Waves, Satellite, Clock, Gauge, Mountain, AlertTriangle
} from "lucide-react"
import type { ProductLandingConfig } from "../types"

// Every claim here is something the flood check actually does
// (services/flood_truth.py). Removed 2026-10-28: "know exactly how deep" (depths
// exist only where we hold a council flood study), ESA Sentinel radar (not
// built; services/CLAUDE.md), "100% statutory coverage" and the LGA/model
// counts (none measured), and the $49 table (figures are free after email).
export const floodConfig: ProductLandingConfig = {
  badge: "Government flood maps + satellite records",
  badgeIcon: Satellite,
  title: "Flood Screening",
  subtitle: "Which flood sources show flooding at your address, and which ones cover it at all.",
  ctaLabel: "Check Flooding",
  heroImage: "/images/landing/hero-flood.png",

  dataSources: [
    { icon: Building2, name: "NSW Government", description: "Flood planning overlay" },
    { icon: Waves, name: "Council flood studies", description: "Modelled depth, where we hold one" },
    { icon: AlertTriangle, name: "2022 flood maps", description: "Copernicus EMS and NSW" },
    { icon: Clock, name: "Satellite water history", description: "DEA and JRC, since the 1980s" },
    { icon: Gauge, name: "BOM river gauges", description: "Last major flood" },
    { icon: Mountain, name: "NSW elevation", description: "Ground height" },
  ],

  featuresTitle: "What This Check Looks At",
  featuresSubtitle: "Each source is checked at your exact point. A source that does not cover your area is reported as not covering it, never as clear.",
  features: [
    {
      icon: Building2,
      title: "Government flood planning overlay",
      description: "Whether the land is in a flood planning area on the NSW Government's planning flood layer. Not every council has published to it.",
    },
    {
      icon: Waves,
      title: "Council flood study depth",
      description: "Where we hold a council's flood study, the modelled water depth or level at your point in a 1-in-100-year flood. We hold a small number of these.",
    },
    {
      icon: AlertTriangle,
      title: "Mapped 2022 floods",
      description: "Whether your point was inside the flooded area mapped from satellite in the February-March, July or October 2022 floods. These maps cover only the areas mapped at the time.",
    },
    {
      icon: Clock,
      title: "Satellite water history",
      description: "How often surface water has been seen at your point in decades of Landsat satellite passes.",
    },
    {
      icon: Gauge,
      title: "River gauge history",
      description: "The nearest Bureau of Meteorology river gauge: how far away, and when it last recorded a major flood.",
    },
    {
      icon: Mountain,
      title: "Ground elevation",
      description: "Ground height from the NSW Government elevation model, used with a council study to turn a flood level into a depth.",
    },
  ],

  methodology: "Your address is turned into a point, then each source is checked at that point. The result is one of five levels: none, low, moderate, elevated, or not enough data. Not enough data means the planning overlay did not answer or does not cover the area and we hold no council study for it; that is never shown as clear. This is a screening check, not a flood certificate: ask your council for a Section 10.7 certificate.",
}
