import { Sun, Building2, Map } from "lucide-react"
import type { ProductLandingConfig } from "../types"

export const shadowConfig: ProductLandingConfig = {
  badge: "ADG solar access modelling",
  badgeIcon: Sun,
  title: "Shadow Risk Analyser",
  subtitle: "Will a new build next door block your sun?",
  ctaLabel: "Check Risk",
  heroImage: "/images/landing/hero-shadow.png",
  heroStats: [
    { value: "5", label: "ADG scenarios" },
    { value: "NSW", label: "Full coverage" },
    { value: "60s", label: "Analysis time" },
  ],

  dataSources: [
    { icon: Building2, name: "NSW Planning", description: "Height controls" },
    { icon: Sun, name: "ADG Standards", description: "Solar access tests" },
  ],

  featuresTitle: "What This Report Checks",
  featuresSubtitle: "Shadow modelling from a maximum-height building envelope placed immediately north of your lot.",
  features: [
    {
      icon: Sun,
      title: "Five ADG Solar Access Scenarios",
      description: "Shadow modelled at 9am, noon, and 3pm on the winter solstice (June 21), plus noon on the spring equinox (September 21) and summer solstice (December 21). These are the test dates NSW planning panels use.",
    },
    {
      icon: Building2,
      title: "Maximum-Height Building Envelope",
      description: "Shadow is cast from a building at the tallest height mapped at your location, modelled as a rectangle immediately north of your boundary. It is a hypothetical screening scenario, not a survey and not an upper bound: the neighbouring parcel's real shape, position and height control are not looked up, and its own control may allow more shadow than this model shows.",
    },
    {
      icon: Map,
      title: "Shadow Path and Overlap",
      description: "For each scenario, the shadow direction, length, and whether it crosses onto your property. Direction is calculated for your address from the sun's position at that date and time. Displayed on an interactive map showing which part of your lot is affected.",
    },
  ],

  pricingTitle: "Free Check vs Full Report",
  pricingSubtitle: "Get an instant ADG verdict, or unlock the full scenario analysis for $29.",
  price: "$29",
  comparison: [
    { name: "ADG compliance verdict", free: true, paid: true },
    { name: "Shadow map (interactive)", free: true, paid: true },
    { name: "Worst-case scenario summary", free: true, paid: true },
    { name: "All 5 scenario breakdowns", free: false, paid: true },
    { name: "Hourly shadow diagrams", free: false, paid: true },
    { name: "Objection-ready summary paragraph", free: false, paid: true },
    { name: "Downloadable PDF report", free: false, paid: true },
  ],
  methodology: "Solar position is calculated for your exact latitude and longitude at each test date and time, using local NSW wall-clock times with daylight saving applied where it is in force. Shadow length and direction are derived geometrically from the maximum permissible building height mapped at your location, sourced from NSW Government planning controls, modelled as a rectangle immediately north of your boundary — the neighbouring parcel itself is not retrieved. In place of any proposed design, the model assumes the full height envelope: the rectangle described above, at the height control mapped at your own property. The neighbouring parcel's own control, and any building actually proposed, may differ.",
}
