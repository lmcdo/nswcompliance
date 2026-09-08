import {
  Building2, Waves, Map, Satellite, Clock, Gauge, Mountain, AlertTriangle
} from "lucide-react"
import type { ProductLandingConfig } from "../types"

export const floodConfig: ProductLandingConfig = {
  badge: "Powered by satellite + government data",
  badgeIcon: Satellite,
  title: "Flood Screening",
  subtitle: "Know exactly how deep the water gets — not just whether it floods.",
  ctaLabel: "Check Flooding",
  heroImage: "/images/landing/hero-flood.png",
  heroStats: [
    { value: "71+", label: "LGAs covered" },
    { value: "8", label: "Data sources" },
    { value: "40yr", label: "Satellite history" },
  ],

  dataSources: [
    { icon: Building2, name: "NSW Government", description: "Flood planning overlay" },
    { icon: Waves, name: "Council Flood Models", description: "Engineering depth data" },
    { icon: Satellite, name: "ESA Sentinel", description: "Radar satellite imagery" },
    { icon: Clock, name: "JRC Surface Water", description: "40-year history" },
    { icon: Gauge, name: "BOM River Gauges", description: "Flood event records" },
    { icon: Mountain, name: "NSW Elevation", description: "High-res terrain model" },
    { icon: AlertTriangle, name: "Copernicus EMS", description: "Emergency activations" },
  ],

  featuresTitle: "What This Report Checks",
  featuresSubtitle: "Every available flood dataset — queried simultaneously at your exact property coordinates.",
  features: [
    {
      icon: Building2,
      title: "Government Flood Planning Overlay",
      description: "Whether council has formally classified this land under the NSW Government flood planning framework. The same data that appears on a Section 10.7 certificate.",
    },
    {
      icon: Waves,
      title: "Council Flood Model Depth",
      description: "Where council has published detailed engineering flood models, we query the actual modelled water depth at your property — for every severity level from minor to catastrophic.",
    },
    {
      icon: Map,
      title: "Flood Extent Mapping",
      description: "Point-in-polygon check against council and state flood extent boundaries. Over 100 local government areas covered, with per-event severity where available.",
    },
    {
      icon: Satellite,
      title: "Satellite Flood Detection",
      description: "European Space Agency radar satellite imagery that sees through cloud cover, compared against a dry-season baseline. Detects recent standing water independent of any government dataset.",
    },
    {
      icon: Clock,
      title: "Long-term Surface Water History",
      description: "Four decades of European and US satellite imagery analysed to calculate what percentage of time your property has had visible surface water.",
    },
    {
      icon: Gauge,
      title: "River Gauge Flood History",
      description: "The nearest Bureau of Meteorology river gauge — how far away, when it last recorded a major flood event, and the peak water height.",
    },
    {
      icon: Mountain,
      title: "Ground Elevation",
      description: "Terrain height above sea level from a high-resolution NSW Government elevation model. Flood depth is the difference between water level and ground elevation.",
    },
    {
      icon: AlertTriangle,
      title: "Emergency Service Activations",
      description: "International emergency management activations that have mapped flood extent at this location. Confirms whether this property was inside a formally mapped flood event.",
    },
  ],

  pricingTitle: "Free Check vs Full Report",
  pricingSubtitle: "Get instant free results, or unlock the complete dataset for $49.",
  price: "$49",
  comparison: [
    { name: "100-year flood zone status", free: true, paid: true },
    { name: "Ground elevation", free: true, paid: true },
    { name: "Government flood overlay", free: true, paid: true },
    { name: "Satellite flood detection", free: true, paid: true },
    { name: "1-in-100 year flood depth (single event)", free: true, paid: true },
    { name: "Historical flood event depths", free: true, paid: true },
    { name: "Full AEP depth table (all severity levels)", free: false, paid: true },
    { name: "River gauge flood event history", free: false, paid: true },
    { name: "Surface water occurrence data", free: false, paid: true },
    { name: "Emergency activation records", free: false, paid: true },
    { name: "Downloadable PDF report", free: false, paid: true },
  ],
  methodology: "Your address is resolved to precise coordinates, then queried against every available flood dataset simultaneously — NSW Government planning layers, council engineering flood models, European Space Agency radar satellites, Bureau of Meteorology river gauges, and international emergency management records. Where council has published flood model grids, we sample the actual raster cell at your property — giving you depth in metres, not just a binary yes or no.",

  coverageTitle: "Flood Data Summary",
  coverageSubtitle: "Check your property's statutory flood status and council flood study exposure. The NSW EPI statutory overlay check covers the full state.",
  coverageStats: [
    { value: "71+", label: "Local Government Areas" },
    { value: "100%", label: "NSW Statutory Coverage" },
    { value: "40+", label: "Regional Council Models" },
  ],
  coverageRegions: [
    {
      name: "Sydney Metro",
      councils: ["Inner West", "Parramatta", "Canterbury-Bankstown", "Georges River", "Woollahra", "Sutherland Shire", "Ryde", "Cumberland", "Campbelltown", "Randwick", "Waverley", "Canada Bay", "Bayside", "Sydney"],
    },
    {
      name: "Hunter & Coast",
      councils: ["Hawkesbury", "Lake Macquarie", "Maitland", "Shoalhaven", "MidCoast", "Dungog", "Singleton"],
    },
    {
      name: "Northern Rivers",
      councils: ["Tweed", "Byron", "Lismore", "Ballina", "Kyogle"],
    },
    {
      name: "Regional NSW",
      councils: ["Bathurst Regional", "Blayney", "Cabonne", "Clarence Valley", "Coolamon", "Cootamundra-Gundagai", "Cowra", "Dubbo Regional", "Edward River", "Federation", "Forbes", "Gilgandra", "Goulburn Mulwaree", "Gunnedah", "Hilltops", "Hornsby", "Junee", "Lachlan", "Leeton", "Lithgow", "Liverpool Plains", "Mid-Western Regional", "Murray River", "Narrabri", "Narrandera", "Narromine", "Orange", "Port Macquarie-Hastings", "Queanbeyan-Palerang", "Snowy Monaro", "Snowy Valleys", "Tamworth Regional", "Temora", "Upper Lachlan", "Uralla", "Walcha", "Warrumbungle", "Weddin", "Wentworth", "Wingecarribee", "Wollongong", "Yass Valley"],
    },
  ],
  coverageNote: "Council flood model depths are available for select areas where councils have published engineering flood study data — coverage is expanding as new studies are released.",
}
