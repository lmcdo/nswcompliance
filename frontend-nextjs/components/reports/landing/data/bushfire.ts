import {
  Flame, Shield, MapPin, Satellite, TreePine, FileCheck, AlertTriangle, Building2
} from "lucide-react"
import type { ProductLandingConfig } from "../types"

export const bushfireConfig: ProductLandingConfig = {
  badge: "RFS data + satellite imagery",
  badgeIcon: Flame,
  title: "Bushfire Pre-Screen",
  subtitle: "Know your BAL band, RFS referral triggers, and 10/50 clearing entitlements — before your planner does.",
  ctaLabel: "Check Risk",
  heroImage: "/images/landing/hero-pre-da.png",
  heroStats: [
    { value: "100%", label: "NSW coverage" },
    { value: "6", label: "BAL bands assessed" },
    { value: "<15s", label: "Result time" },
  ],

  dataSources: [
    { icon: Flame, name: "NSW Rural Fire Service", description: "Bush Fire Prone Land map" },
    { icon: MapPin, name: "NSW Planning Portal", description: "Zoning + lot boundary" },
    { icon: Satellite, name: "Spatial Services NSW", description: "Vegetation mapping" },
    { icon: Shield, name: "AS 3959-2018", description: "BAL assessment standard" },
  ],

  featuresTitle: "What This Check Covers",
  featuresSubtitle: "Every bushfire planning constraint checked at your exact property coordinates — in one place.",
  features: [
    {
      icon: Flame,
      title: "Bush Fire Prone Land Category",
      description: "Whether the property is mapped on the RFS Bush Fire Prone Land map, and which category — Vegetation Category 1, Category 2, Category 3, or Vegetation Buffer.",
    },
    {
      icon: Shield,
      title: "BAL Band Estimate",
      description: "Estimated Bushfire Attack Level under AS 3959-2018 — from BAL-LOW through to BAL-FZ (Flame Zone). Determines construction requirements and insurance costs.",
    },
    {
      icon: FileCheck,
      title: "Section 4.14 RFS Referral",
      description: "Whether your development must be referred to the Rural Fire Service under the EP&A Act. Affects timeline, cost, and the conditions council can impose.",
    },
    {
      icon: TreePine,
      title: "10/50 Vegetation Clearing",
      description: "Whether the property qualifies for 10/50 entitlement — allowing removal of trees within 10m and understorey within 50m of a dwelling without council approval.",
    },
    {
      icon: AlertTriangle,
      title: "CDC Pathway Gating",
      description: "Whether the bushfire classification allows a Complying Development Certificate or requires the full DA pathway. BAL-40 and BAL-FZ properties cannot use CDC.",
    },
    {
      icon: Building2,
      title: "Construction Standard Requirements",
      description: "The AS 3959 construction level required for your BAL band — from standard construction at BAL-LOW to full bushfire-specific construction at BAL-40 and above.",
    },
  ],

  pricingTitle: "Free Instant Check",
  pricingSubtitle: "The bushfire pre-screen is completely free — no account or payment required.",
  price: "Free",
  comparison: [
    { name: "Bush Fire Prone Land status", free: true, paid: true },
    { name: "BFPL vegetation category", free: true, paid: true },
    { name: "Estimated BAL band", free: true, paid: true },
    { name: "RFS referral requirement", free: true, paid: true },
    { name: "10/50 clearing entitlement", free: true, paid: true },
    { name: "CDC pathway eligibility", free: true, paid: true },
    { name: "Construction standard level", free: true, paid: true },
  ],
  methodology: "Your address is resolved to precise coordinates via the NSW Planning Portal, then queried against the NSW Rural Fire Service Bush Fire Prone Land map. The BFPL category determines the estimated BAL band under AS 3959-2018, which in turn determines RFS referral requirements, CDC eligibility, 10/50 clearing entitlements, and minimum construction standards. This is a pre-screen — a formal BAL assessment by a qualified bushfire consultant is required for DA submission.",
}
