import type { ProductLandingConfig } from "../types"

export const shadowConfig: ProductLandingConfig = {
  badgeText: "ADG solar access modelling",
  title: "Will that development",
  titleAccent: "block your sun?",
  subtitle: "Enter any NSW address. Get worst-case shadow analysis in seconds.",
  ctaLabel: "Check shadow risk",

  trustSources: [
    { name: "NSW Planning", logo: "NSW" },
    { name: "ADG Standards", logo: "ADG" },
    { name: "ESA Sentinel", logo: "ESA" },
  ],

  stats: [
    { value: "5", label: "ADG test scenarios" },
    { value: "NSW", label: "Full coverage" },
    { value: "60s", label: "Analysis time" },
  ],
  testimonials: [
    {
      quote: "The shadow diagrams were exactly what I needed for my objection. Council took it seriously.",
      author: "David M.",
      role: "Homeowner, Marrickville",
    },
    {
      quote: "Ran this before the DA was decided. Showed my client the worst-case impact in minutes.",
      author: "Lisa C.",
      role: "Planning Consultant",
    },
    {
      quote: "Found out the neighbour's CDC would block our afternoon sun. Without this we'd have had no idea.",
      author: "Karen W.",
      role: "Homeowner, Dulwich Hill",
    },
  ],

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
      title: "ADG compliance verdict",
      description: "Pass/fail against all 5 ADG solar access scenarios",
    },
    {
      title: "Interactive shadow map",
      description: "See exactly where shadow falls on your lot",
    },
    {
      title: "Construction detection",
      description: "Satellite check for earthworks on the adjacent lot",
    },
  ],
}
