import {
  Satellite, History, FileText, Landmark, TreePine, Flame, Clock, BarChart3
} from "lucide-react"
import type { ProductLandingConfig } from "../types"

export const preDAConfig: ProductLandingConfig = {
  badge: "8 years of satellite imagery",
  badgeIcon: Satellite,
  title: "Pre-DA Site History Report",
  subtitle: "What happened on this land before you got here?",
  ctaLabel: "Check History",
  heroImage: "/images/landing/hero-pre-da.png",
  heroStats: [
    { value: "8yr", label: "Satellite history" },
    { value: "ESA", label: "Sentinel imagery" },
    { value: "NSW", label: "Full coverage" },
  ],

  dataSources: [
    { icon: Satellite, name: "ESA Sentinel", description: "Optical + radar imagery" },
    { icon: FileText, name: "NSW ePlanning", description: "DA & certificate records" },
    { icon: Landmark, name: "Heritage NSW", description: "Conservation areas" },
    { icon: Flame, name: "RFS / SES", description: "Disaster event records" },
    { icon: TreePine, name: "Spectral NDVI", description: "Vegetation density" },
  ],

  featuresTitle: "What This Report Checks",
  featuresSubtitle: "Eight years of satellite imagery cross-referenced with planning records and disaster events.",
  features: [
    {
      icon: Satellite,
      title: "Satellite Change Detection (2017–2025)",
      description: "European Space Agency satellite embeddings compared year-on-year to detect physical changes on the lot — new structures, demolitions, vegetation removal, or surface hardening.",
    },
    {
      icon: TreePine,
      title: "Vegetation and Built-Up Indices",
      description: "Spectral analysis from ESA optical imagery measures vegetation density (NDVI) and built-up surface area (NDBI) each year. Distinguishes construction from natural events like drought.",
    },
    {
      icon: FileText,
      title: "DA and CDC Event History",
      description: "Every development application and complying development certificate lodged with council for this address, fetched from the NSW ePlanning Portal. Shows what was approved, refused, or withdrawn.",
    },
    {
      icon: History,
      title: "Construction and Occupation Certificates",
      description: "Post-consent certificates from the NSW ePlanning Portal — confirms whether approved works were actually completed and signed off by council.",
    },
    {
      icon: Landmark,
      title: "Heritage Overlay",
      description: "Point-in-polygon check against NSW Government heritage conservation area boundaries. Heritage listings require a Statement of Heritage Impact with any DA.",
    },
    {
      icon: BarChart3,
      title: "Neighbourhood Normalisation",
      description: "Compares your lot against the surrounding neighbourhood to filter out area-wide events — drought, bushfire haze, or seasonal variation — that affect satellite readings but are not site-specific changes.",
    },
    {
      icon: Flame,
      title: "Flood and Bushfire Annotations",
      description: "Cross-references detected changes against known flood and bushfire events. A 2019 vegetation drop in the Blue Mountains is bushfire damage, not clearing — the report distinguishes the two.",
    },
    {
      icon: Clock,
      title: "Annotated Year-by-Year Timeline",
      description: "Each year classified as stable, minor, moderate, or major change — with DA cross-references, spectral disambiguation, and natural event annotations. The full picture in one table.",
    },
  ],

  pricingTitle: "Free Check vs Full Report",
  pricingSubtitle: "Get an instant timeline for free, or unlock spectral analysis and DA detail for $49.",
  price: "$49",
  comparison: [
    { name: "Year-by-year change level (stable / minor / moderate / major)", free: true, paid: true },
    { name: "Heritage overlay status", free: true, paid: true },
    { name: "DA event count and application numbers", free: true, paid: true },
    { name: "Summary statistics (years analysed, notable years)", free: true, paid: true },
    { name: "Full annotated timeline with explanations", free: true, paid: true },
    { name: "NDVI/NDBI spectral analysis per year", free: false, paid: true },
    { name: "DA event detail (type, status, dates)", free: false, paid: true },
    { name: "Flood and bushfire event cross-references", free: false, paid: true },
    { name: "Methodology and data quality notes", free: false, paid: true },
    { name: "Downloadable PDF report", free: false, paid: true },
  ],
  methodology: "Your address is resolved to precise coordinates via the NSW Planning Portal, then queried against eight years of European Space Agency satellite imagery. Each year's image embedding is compared to the previous year and to the surrounding neighbourhood — isolating lot-specific changes from area-wide events. Vegetation and built-up spectral indices provide a second independent signal to distinguish construction from natural change. DA and certificate records from the NSW ePlanning Portal are cross-referenced by year. Heritage status is checked against NSW Government spatial boundaries.",
}
