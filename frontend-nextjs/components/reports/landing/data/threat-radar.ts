import { Radar, Building2, FileText, MapPin, Clock } from "lucide-react"
import type { ProductLandingConfig } from "../types"

export const threatRadarConfig: ProductLandingConfig = {
  badge: "NSW ePlanning Portal data",
  badgeIcon: Radar,
  title: "Neighbour Development Threat Radar",
  subtitle: "Know before your neighbour breaks ground.",
  ctaLabel: "Scan Area",
  heroImage: "/images/landing/hero-threat-radar.png",
  heroStats: [
    { value: "500m", label: "Scan radius" },
    { value: "180d", label: "Lookback period" },
    { value: "NSW", label: "Full coverage" },
  ],

  dataSources: [
    { icon: Building2, name: "NSW ePlanning", description: "DA register" },
    { icon: FileText, name: "CDC Register", description: "Complying development" },
    { icon: MapPin, name: "Geocoding", description: "Distance calculation" },
  ],

  featuresTitle: "What This Report Checks",
  featuresSubtitle: "Every DA and CDC lodged within 500m of your address in the last 6 months.",
  features: [
    {
      icon: Building2,
      title: "Active Development Applications",
      description: "Every DA lodged within 500m of your property in the last 6 months — including the development description, estimated cost, and how many new dwellings are proposed.",
    },
    {
      icon: FileText,
      title: "Complying Development Certificates",
      description: "CDCs bypass council notification entirely — your neighbour can start building without you knowing. This scan catches CDCs that would otherwise be invisible until construction begins.",
    },
    {
      icon: MapPin,
      title: "Distance From Your Property",
      description: "Each application is ranked by proximity to your address so you can focus on the ones that matter most. Applications directly next door are flagged separately from those down the street.",
    },
    {
      icon: Clock,
      title: "Determination Status",
      description: "Whether each application is still being assessed, has been approved, refused, or withdrawn. For applications under assessment, you still have time to lodge a submission.",
    },
  ],

  pricingTitle: "Free Scan vs Monitoring",
  pricingSubtitle: "Get an instant scan for free, or subscribe for weekly alerts when new applications are lodged.",
  price: "$9.99/mo",
  comparison: [
    { name: "Nearby DA and CDC scan (500m)", free: true, paid: true },
    { name: "First 3 applications visible", free: true, paid: true },
    { name: "All applications visible", free: false, paid: true },
    { name: "Weekly email alerts (new lodgements)", free: false, paid: true },
    { name: "Ongoing monitoring", free: false, paid: true },
  ],
  methodology: "Your address is geocoded and we scan the NSW Government planning system for every DA and CDC lodged within 500m in the past 180 days. Distance is calculated from the applicant site to your property. Subscribers receive a weekly digest every Monday at 7am with any new applications detected since the last scan.",
}
