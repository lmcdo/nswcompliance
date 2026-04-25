import Link from 'next/link';

const HERO_PRODUCT = {
  href: '/reports/granny-flat',
  title: 'Granny Flat Yield Predictor',
  tagline: 'Could this property earn an extra $280–$340/week?',
  description:
    'Aerial structure detection, SEPP Housing 2021 eligibility, and a rental yield estimate for any NSW address. Free check — detailed report $29.',
  cta: 'Check my property',
  badge: 'Most popular',
  free: true,
};

const OTHER_PRODUCTS = [
  {
    href: '/reports/threat-radar',
    title: 'Neighbour Threat Radar',
    tagline: 'Is something being built next door?',
    description:
      'Monitor DA and CDC activity within 200m. Know before your neighbour breaks ground.',
    badge: 'Free',
  },
  {
    href: '/reports/shadow',
    title: 'Shadow Risk Analyser',
    tagline: 'Will a new build block your sun?',
    description:
      'Model shadow cast by a maximum-permissible adjacent build across the five ADG solar access scenarios.',
    badge: '$29',
  },
  {
    href: '/reports/solar-yield',
    title: 'Rooftop Solar Yield',
    tagline: 'How much could solar earn on this roof?',
    description:
      'Detect existing panels, estimate usable roof area, and calculate annual kWh yield from 10 cm NSW aerial imagery.',
    badge: '$29',
  },
  {
    href: '/reports/flood',
    title: 'Flood History',
    tagline: 'Has this lot ever flooded?',
    description:
      'Cross-reference Sentinel-1 SAR satellite flood detection with NSW statutory overlays for any NSW parcel.',
    badge: 'Free',
  },
];

export default function ReportsLanding() {
  return (
    <div className="space-y-12">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 leading-tight">
          Know exactly what your property can do
        </h1>
        <p className="mt-2 text-gray-500 max-w-xl">
          Five data-driven tools for NSW property owners and investors — from granny flat yield to flood risk. No consultants, no waiting rooms.
        </p>
      </div>

      {/* Hero product — Granny Flat */}
      <Link
        href={HERO_PRODUCT.href}
        className="group block bg-teal-600 rounded-2xl p-8 hover:bg-teal-700 transition-colors"
      >
        <div className="flex items-start justify-between gap-4 mb-3">
          <span className="text-xs font-semibold text-teal-200 uppercase tracking-wide">
            {HERO_PRODUCT.badge}
          </span>
          <span className="text-xs text-teal-300">Free check · $29 detailed report</span>
        </div>
        <h2 className="text-2xl font-bold text-white mb-1">{HERO_PRODUCT.tagline}</h2>
        <p className="text-teal-100 text-sm mb-6 max-w-lg">{HERO_PRODUCT.description}</p>
        <span className="inline-flex items-center gap-2 bg-white text-teal-700 text-sm font-semibold px-5 py-2.5 rounded-lg group-hover:bg-teal-50 transition-colors">
          {HERO_PRODUCT.cta} →
        </span>
      </Link>

      {/* Other 4 tools */}
      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">More tools</p>
        <div className="grid gap-4 sm:grid-cols-2">
          {OTHER_PRODUCTS.map(({ href, title, tagline, description, badge }) => (
            <Link
              key={href}
              href={href}
              className="group block bg-white rounded-xl border border-gray-200 p-6 hover:border-gray-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <h2 className="font-semibold text-gray-900 group-hover:text-teal-700 transition-colors">
                  {title}
                </h2>
                <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${
                  badge === 'Free'
                    ? 'bg-teal-50 text-teal-700'
                    : 'bg-gray-100 text-gray-600'
                }`}>
                  {badge}
                </span>
              </div>
              <p className="text-sm font-medium text-gray-700 mb-1">{tagline}</p>
              <p className="text-sm text-gray-400 leading-relaxed">{description}</p>
            </Link>
          ))}
        </div>
      </div>

      {/* Trust line */}
      <p className="text-xs text-gray-400 text-center pb-4">
        Authoritative data only — NSW Planning Portal, NSW SIX Maps LPI Imagery, and Sentinel-1 SAR. No guesswork.
      </p>
    </div>
  );
}
