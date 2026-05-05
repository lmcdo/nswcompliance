import { Sun, Building2, Map, Satellite, Clock, Eye } from "lucide-react"
import type { ProductLandingConfig } from "../types"

export const shadowConfig: ProductLandingConfig = {
  badge: "ADG solar access modelling",
  badgeIcon: Sun,
  title: "Shadow Risk Analyser",
  subtitle: "Will a new build next door block your sun?",
  ctaLabel: "Check shadow risk",
  heroStats: [
    { value: "5", label: "ADG test scenarios" },
    { value: "NSW", label: "Full coverage" },
    { value: "60s", label: "Analysis time" },
  ],

  featuresTitle: "What This Report Checks",
  featuresSubtitle: "Shadow modelling from the maximum-height building envelope on the adjacent lot.",
  features: [
    {
      icon: Sun,
      title: "Five ADG Solar Access Scenarios",
      description: "Shadow modelled at 9am, noon, and 3pm on the winter solstice (June 21), plus noon on the spring equinox (September 21) and summer solstice (December 21). These are the test dates NSW planning panels use.",
    },
    {
      icon: Building2,
      title: "Maximum-Height Building Envelope",
      description: "Shadow is cast from the tallest building permitted on the adjacent lot under the applicable planning controls. This is the worst case — the actual development may be shorter.",
    },
    {
      icon: Map,
      title: "Shadow Path and Overlap",
      description: "For each scenario, the exact shadow direction, length, and whether it crosses onto your property. Displayed on an interactive map so you can see precisely which part of your lot is affected.",
    },
    {
      icon: Satellite,
      title: "Construction Activity Detection",
      description: "High-resolution satellite imagery analysis to check whether construction has already begun on the adjacent lot. If earthworks or building activity is detected, you may need to act faster.",
    },
  ],

  pricingTitle: "Free Check vs Full Report",
  pricingSubtitle: "Get an instant ADG verdict, or unlock the full scenario analysis for $29.",
  price: "$29",
  comparison: [
    { name: "ADG compliance verdict", free: true, paid: true },
    { name: "Shadow map (interactive)", free: true, paid: true },
    { name: "Worst-case scenario summary", free: true, paid: true },
    { name: "All 5 scenario breakdowns", free: false, paid: true },
    { name: "Hourly shadow diagrams", free: false, paid: true },
    { name: "Construction detection detail", free: false, paid: true },
    { name: "Objection-ready summary paragraph", free: false, paid: true },
    { name: "Downloadable PDF report", free: false, paid: true },
  ],
  methodology: "Solar position is calculated using astronomical algorithms for your exact latitude and longitude at each test date and time. Shadow length and direction are derived geometrically from the maximum permissible building height on the adjacent lot, sourced from NSW Government planning controls. No assumptions are made about the design — the model uses the full height envelope. Construction detection uses spectral analysis of high-resolution satellite imagery to identify disturbed ground.",
  coverageNote: "All of NSW. Shadow geometry works anywhere with planning height controls. Construction detection requires recent cloud-free satellite imagery over the site.",

  comparisons: [
    {
      problem: "Council notification letters",
      limitation: "Arrive after approval, too late to object",
      solution: "We model shadow before the DA is decided",
    },
    {
      problem: "Neighbour's architectural plans",
      limitation: "Shows design, not worst-case impact",
      solution: "We model the maximum permitted envelope",
    },
    {
      problem: "Planning panel hearings",
      limitation: "Requires expert shadow diagrams",
      solution: "We generate ADG-compliant scenarios automatically",
    },
  ],
  whatYouGet: [
    {
      icon: Sun,
      title: "ADG compliance verdict",
      description: "Pass/fail against all 5 ADG solar access scenarios",
    },
    {
      icon: Map,
      title: "Interactive shadow map",
      description: "See exactly where shadow falls on your lot",
    },
    {
      icon: Eye,
      title: "Construction detection",
      description: "Satellite check for earthworks on the adjacent lot",
    },
  ],
}
