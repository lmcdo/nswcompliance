import type { ProductLandingConfig } from "../types"

export const floodConfig: ProductLandingConfig = {
  badgeText: "Live data from 8 sources",
  title: "Know the flood depth,",
  titleAccent: "not just the zone",
  subtitle: "Enter any NSW address. Get the actual water depth in seconds.",
  ctaLabel: "Check flood risk",

  trustSources: [
    { name: "NSW Gov", logo: "NSW" },
    { name: "ESA Sentinel", logo: "ESA" },
    { name: "Bureau of Met", logo: "BOM" },
    { name: "Copernicus", logo: "EU" },
    { name: "JRC Water", logo: "JRC" },
  ],

  stats: [
    { value: "47,000+", label: "Properties checked" },
    { value: "71", label: "LGAs covered" },
    { value: "40 years", label: "Of satellite data" },
  ],
  testimonials: [
    {
      quote: "Saved us from buying a property with 1.2m flood depth. The council flood map showed nothing.",
      author: "Sarah T.",
      role: "Homebuyer, Lismore",
    },
    {
      quote: "I use this for every valuation now. The satellite data catches things the paperwork misses.",
      author: "James K.",
      role: "Property Valuer",
    },
    {
      quote: "Client was about to proceed with a purchase. This report changed their mind - and saved them.",
      author: "Michelle R.",
      role: "Conveyancer, Sydney",
    },
  ],

  comparisons: [
    {
      problem: "Council flood maps",
      limitation: "Shows zones, not depth",
      solution: "We show actual water levels in metres",
    },
    {
      problem: "Insurance quotes",
      limitation: "Binary yes/no flood risk",
      solution: "We show the full risk spectrum",
    },
    {
      problem: "Section 10.7 certificates",
      limitation: "Only shows notations, not severity",
      solution: "We cross-reference 8 data sources",
    },
  ],
  whatYouGet: [
    {
      title: "Estimated flood depth",
      description: "In metres, for 1 in 100 year flood events",
    },
    {
      title: "Historical flood events",
      description: "40 years of satellite-observed flooding",
    },
    {
      title: "Risk assessment",
      description: "Plain-English summary of what the data means",
    },
  ],
}
