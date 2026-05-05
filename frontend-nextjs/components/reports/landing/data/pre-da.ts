import type { ProductLandingConfig } from "../types"

export const preDAConfig: ProductLandingConfig = {
  badgeText: "8 years of satellite imagery",
  title: "What happened on this land",
  titleAccent: "before you got here?",
  subtitle: "Enter any NSW address. Get satellite change detection and DA history in seconds.",
  ctaLabel: "Check site history",

  trustSources: [
    { name: "ESA Sentinel", logo: "ESA" },
    { name: "NSW ePlanning", logo: "NSW" },
    { name: "Heritage NSW", logo: "HER" },
    { name: "RFS / SES", logo: "RFS" },
  ],

  stats: [
    { value: "8yr", label: "Satellite history" },
    { value: "ESA", label: "Sentinel imagery" },
    { value: "NSW", label: "Full coverage" },
  ],
  testimonials: [
    {
      quote: "Found unapproved clearing that the vendor didn't disclose. Saved us from a compliance nightmare.",
      author: "Andrew B.",
      role: "Property Developer",
    },
    {
      quote: "The satellite evidence showed construction activity two years before any DA was lodged. Red flag.",
      author: "Helen T.",
      role: "Conveyancer, Wollongong",
    },
    {
      quote: "Used this before lodging our DA. Council already knew about the 2020 vegetation clearing — glad we checked.",
      author: "Sam K.",
      role: "Architect, Inner West",
    },
  ],

  comparisons: [
    {
      problem: "Section 10.7 certificates",
      limitation: "Shows current overlays, not history",
      solution: "We show 8 years of physical changes",
    },
    {
      problem: "Council DA searches",
      limitation: "Lists approvals, not what actually happened",
      solution: "We cross-reference DAs with satellite evidence",
    },
    {
      problem: "Site inspections",
      limitation: "See today's state, not what was removed",
      solution: "We detect cleared vegetation and demolished structures",
    },
  ],
  whatYouGet: [
    {
      title: "Annotated timeline",
      description: "Year-by-year change classification with explanations",
    },
    {
      title: "Satellite evidence",
      description: "Physical change detection independent of council records",
    },
    {
      title: "DA cross-reference",
      description: "Every application and certificate for this address",
    },
  ],
}
