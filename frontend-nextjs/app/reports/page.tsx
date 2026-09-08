import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Property Intelligence Reports — NSW',
  description: 'Seven data-driven property intelligence tools for NSW. Flood depth, bushfire BAL, shadow analysis, solar yield, granny flat eligibility, and development monitoring.',
  openGraph: {
    title: 'NSW Property Intelligence Reports — PlotDetect',
    description: 'Flood depth, bushfire BAL, shadow analysis, solar yield, granny flat eligibility, and development monitoring for any NSW address.',
    url: '/reports',
  },
};

// NOTE: Intelligence Brief and Conveyancing live on their own pro subdomains
// (brief./conveyance.plotdetect.com.au) under the Option B domain split, so they
// are intentionally NOT tiles in this consumer (canibuildit) grid. The pages still
// exist at /reports/intelligence-brief and /reports/conveyancing.
const TOOLS = [
  {
    href: '/reports/flood',
    title: 'Flood Screening',
    tagline: 'How deep does it flood — not just whether it floods.',
    description:
      'NSW Government overlays, ESA satellite radar, Bureau of Meteorology river gauges, and council flood model depths cross-referenced for any NSW address.',
    badge: 'Free + $49',
  },
  {
    href: '/reports/bushfire',
    title: 'Bushfire Pre-Screen',
    tagline: 'Is this address on Bush Fire Prone Land?',
    description:
      'RFS BFPL overlay status and estimated BAL band. Required for any new dwelling, addition, or change of use in a bushfire-prone area.',
    badge: 'Free',
  },
  {
    href: '/reports/granny-flat',
    title: 'Granny Flat Feasibility',
    tagline: 'Could this property earn an extra $280\u2013$340/week?',
    description:
      'NSW Government aerial imagery, AI structure detection, planning rule analysis, and rental yield estimate for any NSW address.',
    badge: 'Free + $49',
  },
  {
    href: '/reports/pre-da-history',
    title: 'Prior Development Activity',
    tagline: 'What happened on this land before you got here?',
    description:
      'Eight years of European Space Agency satellite imagery cross-referenced with DA records, heritage overlays, and natural disaster events.',
    badge: '$49',
  },
  {
    href: '/reports/threat-radar',
    title: 'Development Monitoring',
    tagline: 'Know before your neighbour breaks ground.',
    description:
      'Every DA and CDC within 500m of your property \u2014 with weekly email alerts for new lodgements.',
    badge: 'Free',
  },
  {
    href: '/reports/shadow',
    title: 'Overshadowing Check',
    tagline: 'Will a new build block your sun?',
    description:
      'Shadow modelled from the maximum-height building envelope across the five ADG solar access test dates used by NSW planning panels.',
    badge: '$39',
  },
  {
    href: '/reports/solar-yield',
    title: 'Rooftop Solar Potential',
    tagline: 'How much could solar earn on this roof?',
    description:
      'NSW Government building footprints and Bureau of Meteorology irradiance data combined to estimate annual generation.',
    badge: '$39',
  },
];

interface Props {
  searchParams: Promise<{ address?: string | string[] }>;
}

export default async function ReportsLanding({ searchParams }: Props) {
  // An address arrives from the homepage hero search (?address=). Thread it into
  // every tool card so the chosen tool auto-runs on that address instead of the
  // visitor having to re-type it. Empty/malformed param = the plain hub.
  const params = await searchParams;
  const address = typeof params.address === 'string' ? params.address.trim() : '';
  const hrefSuffix = address ? `?address=${encodeURIComponent(address)}` : '';

  return (
    <div className="space-y-12">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 leading-tight">
          Know exactly what your property can do
        </h1>
        <p className="mt-2 text-gray-500 max-w-xl">
          Seven property intelligence tools for NSW — from flood depth to solar yield. No consultants, no waiting rooms.
        </p>
      </div>

      {address && (
        <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">
          Showing tools for <span className="font-medium text-teal-900">{address}</span>. Pick a check below and your address carries through.
        </div>
      )}

      {/* Tool grid — all equal */}
      <div className="grid gap-4 sm:grid-cols-2">
        {TOOLS.map(({ href, title, tagline, description, badge }) => (
          <Link
            key={href}
            href={`${href}${hrefSuffix}`}
            className="group block bg-white rounded-xl border border-gray-200 p-6 hover:border-gray-300 hover:shadow-sm transition-all"
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <h2 className="font-semibold text-gray-900 group-hover:text-teal-700 transition-colors">
                {title}
              </h2>
              <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${
                badge.startsWith('Free')
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

      {/* Trust line */}
      <p className="text-xs text-gray-400 text-center pb-4">
        NSW Government planning data, European Space Agency satellite imagery, Bureau of Meteorology records, NSW Rural Fire Service, and council flood models. No guesswork.
      </p>
    </div>
  );
}
