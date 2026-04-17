import Link from 'next/link';

const PRODUCTS = [
  {
    href: '/reports/solar-yield',
    title: 'Rooftop Solar Yield',
    description: 'Detect existing panels, estimate usable roof area, and calculate annual kWh yield from 10cm aerial imagery.',
  },
  {
    href: '/reports/shadow',
    title: 'Construction Shadow',
    description: 'Model shadow cast by a maximum-permissible building on an adjacent lot across the five ADG solar access scenarios.',
  },
  {
    href: '/reports/threat-radar',
    title: 'Neighbour Development Threat Radar',
    description: 'Monitor nearby DA and CDC activity. Get alerts when new applications are lodged within 200m.',
  },
  {
    href: '/reports/flood',
    title: 'Flood History',
    description: 'Cross-reference Sentinel-1 SAR flood detection with NSW statutory overlays for any NSW parcel.',
  },
  {
    href: '/reports/granny-flat',
    title: 'Granny Flat Feasibility',
    description: 'Detect existing structures from aerial imagery, calculate buildable envelope under SEPP Housing 2021, and estimate rental yield.',
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
        {PRODUCTS.map(({ href, title, description }) => (
          <Link
            key={href}
            href={href}
            className="group block bg-white rounded-xl border border-gray-200 p-6 hover:border-gray-300 hover:shadow-sm transition-all"
          >
            <h2 className="font-semibold text-gray-900 group-hover:text-teal-700 transition-colors mb-3">
              {title}
            </h2>
            <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
