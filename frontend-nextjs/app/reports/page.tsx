import Link from 'next/link';

const PRODUCTS = [
  {
    href: '/reports/solar-yield',
    title: 'Rooftop Solar Yield',
    description: 'Detect existing panels, estimate usable roof area, and calculate annual kWh yield from 10cm aerial imagery.',
    badge: 'Live',
    badgeColor: 'bg-green-100 text-green-800',
  },
  {
    href: '/reports/shadow',
    title: 'Construction Shadow',
    description: 'Model shadow cast by a maximum-permissible building on an adjacent lot across the five ADG solar access scenarios.',
    badge: 'Coming soon',
    badgeColor: 'bg-gray-100 text-gray-600',
  },
  {
    href: '/reports/threat-radar',
    title: 'Neighbour Development Threat Radar',
    description: 'Monitor nearby DA and CDC activity. Subscribe for weekly alerts when new applications are lodged within 200m.',
    badge: 'Coming soon',
    badgeColor: 'bg-gray-100 text-gray-600',
  },
  {
    href: '/reports/flood',
    title: 'Wet Season Flood Truth',
    description: 'Cross-reference Sentinel-1 SAR flood detection with NSW EPI statutory overlays for any NSW parcel.',
    badge: 'Coming soon',
    badgeColor: 'bg-gray-100 text-gray-600',
  },
  {
    href: '/reports/granny-flat',
    title: 'Granny Flat Yield Predictor',
    description: 'Detect existing structures from aerial imagery, calculate buildable envelope under SEPP Housing 2021, and estimate rental yield.',
    badge: 'Coming soon',
    badgeColor: 'bg-gray-100 text-gray-600',
  },
];

export default function ReportsLanding() {
  return (
    <div>
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-gray-900">Property Intelligence Reports</h1>
        <p className="mt-2 text-gray-500 max-w-xl">
          Data-driven reports for NSW properties — solar potential, shadow risk, development activity, flood history, and secondary dwelling feasibility.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {PRODUCTS.map(({ href, title, description, badge, badgeColor }) => (
          <Link
            key={href}
            href={href}
            className="group block bg-white rounded-xl border border-gray-200 p-6 hover:border-gray-300 hover:shadow-sm transition-all"
          >
            <div className="flex items-start justify-between gap-4 mb-3">
              <h2 className="font-semibold text-gray-900 group-hover:text-teal-700 transition-colors">
                {title}
              </h2>
              <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${badgeColor}`}>
                {badge}
              </span>
            </div>
            <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
