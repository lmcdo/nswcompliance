// prior-art-checked: extends the existing ProductLandingV2 config pattern
// (components/reports/landing/data/conveyancing.ts); no brief landing config existed.
import {
  Building2, FileText, Map, Satellite, Shield, Home, Scale, Layers, LineChart,
} from "lucide-react"
import type { ProductLandingConfig } from "../types"

export const intelligenceBriefConfig: ProductLandingConfig = {
  badge: "Live government data + satellite + computed analysis",
  badgeIcon: FileText,
  title: "Property Intelligence Brief",
  subtitle:
    "One address — planning controls, hazards, valuation, nearby applications and computed development capacity, with every figure traced to its source.",
  ctaLabel: "Generate Brief",
  heroImage: undefined,
  heroStats: [
    { value: "15+", label: "Data layers" },
    { value: "~40 sec", label: "Typical brief" },
    { value: "Live", label: "NSW Planning Portal" },
  ],

  dataSources: [
    { icon: Building2, name: "NSW Planning Portal", description: "LEP controls & zones" },
    { icon: Map, name: "Spatial Services NSW", description: "Lot area & valuation" },
    { icon: Satellite, name: "ePlanning MapServer", description: "Environmental overlays" },
    { icon: Layers, name: "NSW Strata Hub", description: "Ownership structure" },
    { icon: Scale, name: "ePlanning DA API", description: "Nearby applications" },
    { icon: Shield, name: "Satellite imagery", description: "Structures & land cover" },
  ],

  featuresTitle: "What the Brief Covers",
  featuresSubtitle:
    "The full picture for a single property — streamed section by section from authoritative sources while you watch.",
  features: [
    {
      icon: Scale,
      title: "Development Capacity",
      description:
        "Indicative floor space and dwelling yield computed from the published LEP, SEPP and DCP controls — with the specific control that limits the site named and cited.",
    },
    {
      icon: Building2,
      title: "Planning Controls",
      description:
        "Zone, maximum building height, floor space ratio, minimum lot size, heritage items and the applicable LEP instrument — queried live from the NSW Planning Portal.",
    },
    {
      icon: FileText,
      title: "DCP Development Controls",
      description:
        "Structured development control plan provisions — front, side and rear setbacks, site coverage, landscaping minimums and parking — with clause citations and a link to the source document.",
    },
    {
      icon: Map,
      title: "Environmental & Hazard Overlays",
      description:
        "Biodiversity sensitivity, riparian corridors, wetlands, landslide risk, flood planning area, bushfire prone land, acid sulfate soils, and ANEF noise contours.",
    },
    {
      icon: Home,
      title: "SEPP Housing Standards",
      description:
        "State policy standards that apply to the site — secondary dwellings, dual occupancy, low- and mid-rise housing — with SEPP Housing 2021 clause references.",
    },
    {
      icon: LineChart,
      title: "Economics & Valuation",
      description:
        "Land value and valuation history from the NSW Valuation Service, with lot area cross-checked against the cadastre.",
    },
    {
      icon: Layers,
      title: "Strata & Cadastre",
      description:
        "Lot type and ownership structure — whether the address is a Torrens lot, community title, or part of a strata scheme, and what that means for the brief.",
    },
    {
      icon: Building2,
      title: "Neighbourhood Activity",
      description:
        "DAs and CDCs near the property — type, status and determination date — plus geometric shadow modelling of a maximum-height neighbour at the winter solstice.",
    },
    {
      icon: Satellite,
      title: "Satellite Analysis (optional)",
      description:
        "Bushfire attack screening, multi-source flood occurrence, climate exposure, terrain from elevation data, and detection of existing structures on the lot.",
    },
  ],

  // The brief is free while in open testing — no pricing table; the methodology
  // block below renders in its place.
  methodology:
    "The brief runs as a background job and streams each section as it completes — a typical run takes about 40 seconds. Data is queried in real time from the NSW Planning Portal layerintersect API, the NSW Valuation Service, spatial overlays sourced from ePlanning ArcGIS MapServer services, the NSW ePlanning DA API and NSW Strata Hub, with optional satellite analysis. Every figure carries a confidence level (authoritative, derived, estimated) and traces to its source. Results are indicative only and do not constitute planning or legal advice.",
}
