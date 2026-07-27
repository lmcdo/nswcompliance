import type { Metadata } from 'next';
import Link from 'next/link';
import { FLOOD_LGAS } from '@/lib/lga-data/flood-lgas';
import { SOLAR_LGAS } from '@/lib/lga-data/solar-lgas';
import { GRANNY_FLAT_LGAS } from '@/lib/lga-data/granny-flat-lgas';
import { THREAT_RADAR_LGAS } from '@/lib/lga-data/threat-radar-lgas';
import { SHADOW_LGAS } from '@/lib/lga-data/shadow-lgas';
import { BUSHFIRE_LGAS } from '@/lib/lga-data/bushfire-lgas';
import { PRE_DA_HISTORY_LGAS } from '@/lib/lga-data/pre-da-history-lgas';
import { VERIFY_LGAS } from '@/lib/lga-data/verify-lgas';
import { CONVEYANCING_LGAS } from '@/lib/lga-data/conveyancing-lgas';

export const metadata: Metadata = {
  title: 'Site directory — every tool, report and page | PlotDetect',
  description:
    'A complete, grouped index of every tool, report and page on the site — property reports, free instant checks, planning controls, data and guides.',
  alternates: { canonical: '/site-directory' },
};

// Grouped index of the site's user-facing pages. Links only to routes that
// resolve (verified against app/ page.tsx routes); the per-address tools have
// per-council pages reached from their report hub or /browse. Council counts are
// read live from the same lib/lga-data arrays the sitemap uses, so they never
// drift from actual coverage.
interface DirItem {
  href: string;
  label: string;
  desc: string;
  badge?: string;
  external?: boolean;
}
interface DirGroup {
  title: string;
  blurb?: string;
  items: DirItem[];
}

const GROUPS: DirGroup[] = [
  {
    title: 'Property reports',
    blurb: 'Per-address reports. Enter an address and get a written result.',
    items: [
      { href: '/reports', label: 'All reports', desc: 'Pick a report type to run for an address.' },
      { href: '/reports/flood', label: 'Flood risk', desc: 'Flood exposure screening for a property.', badge: `${FLOOD_LGAS.length} councils` },
      { href: '/reports/bushfire', label: 'Bushfire pre-screen', desc: 'Bushfire-prone-land indication for a lot.', badge: `${BUSHFIRE_LGAS.length} councils` },
      { href: '/reports/granny-flat', label: 'Granny flat feasibility', desc: 'Secondary-dwelling potential and yield.', badge: `${GRANNY_FLAT_LGAS.length} councils` },
      { href: '/reports/solar-yield', label: 'Solar potential', desc: 'Rooftop solar exposure and yield estimate.', badge: `${SOLAR_LGAS.length} councils` },
      { href: '/reports/shadow', label: 'Shadow analysis', desc: 'Overshadowing from nearby development.', badge: `${SHADOW_LGAS.length} councils` },
      { href: '/reports/threat-radar', label: 'Development monitoring', desc: 'Track nearby development applications.', badge: `${THREAT_RADAR_LGAS.length} councils` },
      { href: '/reports/pre-da-history', label: 'Site history', desc: "A lot's past development-application history.", badge: `${PRE_DA_HISTORY_LGAS.length} councils` },
      { href: '/reports/conveyancing', label: 'Conveyancing disclosure', desc: 'Planning-disclosure report for a transaction.', badge: `${CONVEYANCING_LGAS.length} councils` },
      { href: '/reports/intelligence-brief', label: 'Site Report', desc: 'The full property planning report.' },
    ],
  },
  {
    title: 'Free instant checks',
    blurb: 'Quick eligibility answers, no report needed.',
    items: [
      { href: '/check', label: 'CDC / exempt & complying', desc: 'Whether a fast-track approval pathway may apply.' },
      { href: '/tools/zoning-check', label: 'Zoning check', desc: 'Zone and the uses it permits.' },
      { href: '/tools/upzoning-check', label: 'Upzoning check', desc: 'Recent zoning uplift affecting a lot.' },
      { href: '/tools/subdivision-check', label: 'Subdivision check', desc: 'Minimum-lot-size subdivision indication.' },
      { href: '/duplex-check', label: 'Duplex check', desc: 'Dual-occupancy eligibility for a block.' },
    ],
  },
  {
    title: 'Planning controls & compliance',
    blurb: 'The LEP / DCP / SEPP controls behind the answers.',
    items: [
      { href: '/assessment', label: 'Site Controls', desc: 'LEP, DCP and SEPP controls for an address.' },
      { href: '/browse', label: 'Browse councils', desc: 'Find a council and its planning coverage.' },
      { href: '/dcp-browse', label: 'Browse DCP provisions', desc: 'Development control plan provisions by council.' },
      { href: '/planning-standards', label: 'SEPP Housing standards', desc: 'State housing-policy development standards.' },
      { href: '/glossary', label: 'Planning glossary', desc: 'Plain-English NSW planning terms.' },
    ],
  },
  {
    title: 'Data & developers',
    items: [
      { href: '/open-data', label: 'Open data', desc: 'Published datasets and the data dictionary.' },
      { href: '/climate-risk', label: 'Climate risk', desc: 'NSW climate-projection indicators.' },
      { href: '/developers', label: 'Developers / API', desc: 'Programmatic access to the data.' },
    ],
  },
  {
    title: 'By profession',
    items: [
      { href: '/for/conveyancers', label: 'For conveyancers', desc: 'Planning disclosure for transactions.' },
      { href: '/for/buyers-agents', label: 'For buyers agents', desc: 'Due diligence before an offer.' },
      { href: '/for/builders', label: 'For builders', desc: 'Feasibility and eligibility for a site.' },
      { href: '/for/planners', label: 'For planners', desc: 'Controls, SEE support and DA context.' },
      { href: '/for/councils', label: 'For councils', desc: 'How PlotDetect uses council planning data.' },
    ],
  },
  {
    title: 'Company & help',
    items: [
      { href: '/about', label: 'About', desc: 'What PlotDetect is and who builds it.' },
      { href: '/how-it-works', label: 'How it works', desc: 'How an address becomes an answer.' },
      { href: '/pricing', label: 'Pricing', desc: 'Report and subscription pricing.' },
      { href: '/user-guide', label: 'User guide', desc: 'Detailed how-to for each tool.' },
      { href: '/quick-guide', label: 'Quick guide', desc: 'One-page getting-started.' },
      { href: '/blog', label: 'Insights', desc: 'Articles on NSW planning and property.' },
      { href: '/contact', label: 'Contact', desc: 'Get in touch.' },
      { href: '/privacy', label: 'Privacy', desc: 'Privacy policy.' },
      { href: '/terms', label: 'Terms', desc: 'Terms of use.' },
    ],
  },
];

export default function DirectoryPage() {
  return (
    <main className="max-w-5xl mx-auto px-6 py-12">
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Site directory</h1>
        <p className="mt-2 text-slate-600 max-w-2xl leading-relaxed">
          Every tool, report and page on the site, grouped. The per-address tools
          (flood, bushfire, granny flat, solar, shadow, monitoring, planning
          controls and conveyancing) also have a page for each covered council —
          reach those from the report or via <Link href="/browse" className="text-teal-700 underline hover:text-teal-900">Browse councils</Link>.
        </p>
      </header>

      <div className="space-y-10">
        {GROUPS.map((group) => (
          <section key={group.title}>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              {group.title}
            </h2>
            {group.blurb && <p className="text-sm text-slate-500 mb-4">{group.blurb}</p>}
            <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {group.items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="block h-full rounded-lg border border-slate-200 bg-white p-3 hover:border-teal-400 hover:shadow-sm transition-colors"
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-sm font-medium text-slate-900">{item.label}</span>
                      {item.badge && (
                        <span className="text-[10px] font-medium text-teal-700 bg-teal-50 rounded px-1.5 py-0.5 whitespace-nowrap">
                          {item.badge}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-slate-500 leading-snug">{item.desc}</p>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {/* Cross-link to the info site (deliberately separate brand — see Option B). */}
      <div className="mt-12 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-sm text-slate-700">
          Looking for the company and product overview, methodology and articles?
          Visit the PlotDetect info site at{' '}
          <a
            href="https://plotdetect.com.au"
            className="text-teal-700 font-medium underline hover:text-teal-900"
          >
            plotdetect.com.au
          </a>
          .
        </p>
      </div>
    </main>
  );
}
