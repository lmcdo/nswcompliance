import type { ProductLandingConfig } from "../types"

export const solarConfig: ProductLandingConfig = {
  badgeText: "Satellite roof analysis",
  title: "How much could solar",
  titleAccent: "earn on this roof?",
  subtitle: "Enter any NSW address. Get a suitability grade and yield estimate in seconds.",
  ctaLabel: "Check solar yield",

  trustSources: [
    { name: "NSW Gov", logo: "NSW" },
    { name: "Bureau of Met", logo: "BOM" },
    { name: "Heritage NSW", logo: "HER" },
  ],

  stats: [
    { value: "A–F", label: "Suitability grade" },
    { value: "kWh", label: "Annual estimate" },
    { value: "60s", label: "Analysis time" },
  ],
  testimonials: [
    {
      quote: "Saved me a wasted site visit. The heritage flag caught a listing I would have missed.",
      author: "Tom R.",
      role: "Solar Installer, Sydney",
    },
    {
      quote: "I run every address through this before quoting. The roof orientation data is spot on.",
      author: "Steve H.",
      role: "Solar Sales Manager",
    },
    {
      quote: "Helped us pick the right property for solar. The A-grade roof pays for itself in 4 years.",
      author: "Jenny L.",
      role: "Property Investor",
    },
  ],

  comparisons: [
    {
      problem: "Installer quotes",
      limitation: "Require a site visit before sizing",
      solution: "We size the system from satellite data",
    },
    {
      problem: "Online calculators",
      limitation: "Use suburb averages, not your roof",
      solution: "We analyse your actual roof geometry",
    },
    {
      problem: "Council heritage checks",
      limitation: "Discovered after paying for quotes",
      solution: "We flag heritage constraints upfront",
    },
  ],
  whatYouGet: [
    {
      title: "Suitability grade",
      description: "A–F rating based on your roof's solar potential",
    },
    {
      title: "Annual kWh estimate",
      description: "Expected generation from optimal panel placement",
    },
    {
      title: "System sizing",
      description: "Recommended kW capacity and panel count",
    },
  ],
}
