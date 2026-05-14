import {
  Building2, FileText, Map, Satellite, Shield, TreeDeciduous, Home, Scale
} from "lucide-react"
import type { ProductLandingConfig } from "../types"

export const conveyancingConfig: ProductLandingConfig = {
  badge: "Live government data + spatial analysis",
  badgeIcon: FileText,
  title: "Conveyancing Planning Disclosure",
  subtitle: "Everything your conveyancer should check — queried from live government sources in seconds.",
  ctaLabel: "Analyse Property",
  heroImage: undefined,
  heroStats: [
    { value: "6", label: "Data sources" },
    { value: "28", label: "LGAs with DCP data" },
    { value: "Live", label: "NSW Planning Portal" },
  ],

  dataSources: [
    { icon: Building2, name: "NSW Planning Portal", description: "LEP controls & zones" },
    { icon: Map, name: "Spatial Services NSW", description: "Lot area & valuation" },
    { icon: Satellite, name: "ePlanning MapServer", description: "Environmental overlays" },
    { icon: Shield, name: "Heritage Register", description: "Items & conservation areas" },
    { icon: TreeDeciduous, name: "Biodiversity Maps", description: "Sensitivity overlays" },
    { icon: Scale, name: "ePlanning DA API", description: "Nearby applications" },
  ],

  featuresTitle: "What This Report Covers",
  featuresSubtitle: "The planning due diligence that should happen before exchange — automated from authoritative sources.",
  features: [
    {
      icon: Building2,
      title: "LEP Planning Controls",
      description: "Zone, maximum building height, floor space ratio, minimum lot size, and applicable LEP instrument — queried live from the NSW Planning Portal layerintersect API.",
    },
    {
      icon: Map,
      title: "Environmental & Hazard Overlays",
      description: "Biodiversity sensitivity, riparian corridors, wetlands, landslide risk, flood planning area, bushfire prone land, acid sulfate soils, and ANEF noise contours — from PostGIS spatial overlays.",
    },
    {
      icon: Shield,
      title: "Heritage Status",
      description: "Individual heritage items and Heritage Conservation Areas from both the NSW Planning Portal and PostGIS spatial data. HCA classification determines whether an HCA clause applies.",
    },
    {
      icon: FileText,
      title: "SEPP Overlays",
      description: "All State Environmental Planning Policy overlays affecting the property — Housing SEPP, Transport Oriented Development precincts, BASIX climate zones, and other special provisions.",
    },
    {
      icon: Home,
      title: "Development Feasibility",
      description: "Screening assessment for secondary dwelling (granny flat), Torrens title subdivision, and dual occupancy — with SEPP Housing 2021 clause references.",
    },
    {
      icon: Scale,
      title: "DCP Setback Controls",
      description: "Structured DCP controls for 28 Sydney LGAs — front, side, and rear setbacks, site coverage, landscaping minimums, and parking requirements with clause citations.",
    },
    {
      icon: Satellite,
      title: "Shadow Risk Analysis",
      description: "Geometric shadow modelling from the LEP maximum height envelope at the winter solstice — does a maximum-height neighbour development create ADG solar access concerns?",
    },
    {
      icon: Building2,
      title: "Nearby Development Applications",
      description: "All DAs and CDCs within 200m of the property — summarised by type, status, and determination date from the NSW ePlanning API.",
    },
  ],

  pricingTitle: "Free Check vs Full Report",
  pricingSubtitle: "Get instant structured results, or download the complete disclosure PDF for $49.",
  price: "$49",
  comparison: [
    { name: "LEP zone, height, FSR", free: true, paid: true },
    { name: "Environmental overlays", free: true, paid: true },
    { name: "Heritage status", free: true, paid: true },
    { name: "SEPP overlay identification", free: true, paid: true },
    { name: "Development feasibility screening", free: true, paid: true },
    { name: "Title type detection", free: true, paid: true },
    { name: "DCP setback controls", free: false, paid: true },
    { name: "Shadow risk analysis", free: false, paid: true },
    { name: "Nearby DA summary", free: false, paid: true },
    { name: "Land value history", free: false, paid: true },
    { name: "LEP clause interpretation", free: false, paid: true },
    { name: "Professional PDF with citations", free: false, paid: true },
  ],
  methodology: "Data is queried in real time from the NSW Planning Portal layerintersect API, NSW Valuation Service, PostGIS spatial overlays (sourced from ePlanning ArcGIS MapServer services), and the NSW ePlanning DA API. No data is cached or stale — every result reflects the current state of these government systems. Results are indicative only and do not constitute planning or legal advice.",
}
