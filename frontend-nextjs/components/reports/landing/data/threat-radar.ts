import type { ProductLandingConfig } from "../types"

export const threatRadarConfig: ProductLandingConfig = {
  badgeText: "NSW ePlanning Portal data",
  title: "Know before your neighbour",
  titleAccent: "breaks ground",
  subtitle: "Enter any NSW address. See every DA and CDC within 500m in seconds.",
  ctaLabel: "Scan nearby DAs",

  trustSources: [
    { name: "NSW ePlanning", logo: "NSW" },
    { name: "Council DAs", logo: "DA" },
    { name: "CDC Register", logo: "CDC" },
  ],

  stats: [
    { value: "500m", label: "Scan radius" },
    { value: "180d", label: "Lookback period" },
    { value: "NSW", label: "Full coverage" },
  ],
  testimonials: [
    {
      quote: "Found a 12-unit CDC next door that nobody told us about. We objected before it was too late.",
      author: "Mark P.",
      role: "Homeowner, Parramatta",
    },
    {
      quote: "I run this for every buyer before they exchange. It's caught DAs the conveyancer missed.",
      author: "Rachel S.",
      role: "Buyer's Agent, Sydney",
    },
    {
      quote: "The weekly alerts mean I never get blindsided by a new DA. Worth every cent.",
      author: "Tony G.",
      role: "Property Investor",
    },
  ],

  comparisons: [
    {
      problem: "Council notification letters",
      limitation: "Only for DAs, not CDCs",
      solution: "We catch CDCs that bypass notification",
    },
    {
      problem: "Planning portal searches",
      limitation: "Manual, requires knowing which council",
      solution: "We scan automatically within 500m",
    },
    {
      problem: "Real estate due diligence",
      limitation: "Checks current state, not pending DAs",
      solution: "We show what's approved but not yet built",
    },
  ],
  whatYouGet: [
    {
      title: "Proximity scan",
      description: "All DAs and CDCs within 500m, ranked by distance",
    },
    {
      title: "Development details",
      description: "Cost, dwellings, type, and determination status",
    },
    {
      title: "Weekly monitoring",
      description: "Email alerts when new applications appear",
    },
  ],
}
